"use client";

import { FileUpIcon, GlobeIcon, TypeIcon } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";

import { ErrorNote, Field } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { KnowledgeDoc } from "@/lib/types";

const MAX_FILE_MB = 15;

export function AddKnowledge({ onAdded, compact = false }: { onAdded?: (doc: KnowledgeDoc) => void; compact?: boolean }) {
  const { mutate } = useSWRConfig();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function run(work: () => Promise<KnowledgeDoc>, reset: () => void) {
    setBusy(true);
    setError(null);
    try {
      const doc = await work();
      reset();
      toast.success(`"${doc.title}" added. Indexing now.`);
      await mutate("/knowledge");
      onAdded?.(doc);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Tabs defaultValue="text" className="gap-4">
      <TabsList>
        <TabsTrigger value="text">
          <TypeIcon /> Paste text
        </TabsTrigger>
        <TabsTrigger value="url">
          <GlobeIcon /> Website
        </TabsTrigger>
        <TabsTrigger value="file">
          <FileUpIcon /> Upload
        </TabsTrigger>
      </TabsList>

      <TabsContent value="text">
        <form
          className="grid gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            const f = e.currentTarget;
            const data = new FormData(f);
            const text = String(data.get("text")).trim();
            if (text.length < 20) return setError(new Error("Add a little more detail (at least 20 characters)."));
            run(
              () => api.post<KnowledgeDoc>("/knowledge/text", { title: String(data.get("title")).trim() || "Notes", text }),
              () => f.reset(),
            );
          }}
        >
          <Field label="Title" htmlFor="k-title">
            <Input id="k-title" name="title" placeholder="Prices and opening hours" />
          </Field>
          <Field label="Content" htmlFor="k-text" hint="FAQs, prices, services, policies: anything a customer might ask.">
            <Textarea
              id="k-text"
              name="text"
              rows={compact ? 5 : 7}
              placeholder={"Q: Do you take walk-ins?\nA: Yes, Monday to Friday before noon.\n\nA routine cleaning costs $90..."}
            />
          </Field>
          <ErrorNote error={error} />
          <div>
            <Button type="submit" disabled={busy}>
              {busy ? "Adding..." : "Add and index"}
            </Button>
          </div>
        </form>
      </TabsContent>

      <TabsContent value="url">
        <form
          className="grid gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            const f = e.currentTarget;
            const data = new FormData(f);
            const url = String(data.get("url")).trim();
            if (!/^https?:\/\//i.test(url)) return setError(new Error("Enter a full address starting with https://"));
            run(
              () => api.post<KnowledgeDoc>("/knowledge/url", { url, title: String(data.get("title")).trim() || null }),
              () => f.reset(),
            );
          }}
        >
          <Field label="Page address" htmlFor="k-url" hint="We read the page text once. Add each important page separately.">
            <Input id="k-url" name="url" type="url" placeholder="https://yourbusiness.com/services" />
          </Field>
          <Field label="Title (optional)" htmlFor="k-url-title">
            <Input id="k-url-title" name="title" placeholder="Services page" />
          </Field>
          <ErrorNote error={error} />
          <div>
            <Button type="submit" disabled={busy}>
              {busy ? "Fetching..." : "Add page"}
            </Button>
          </div>
        </form>
      </TabsContent>

      <TabsContent value="file">
        <form
          className="grid gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            const file = fileRef.current?.files?.[0];
            if (!file) return setError(new Error("Choose a PDF, Word or text file first."));
            if (file.size > MAX_FILE_MB * 1024 * 1024)
              return setError(new Error(`Files up to ${MAX_FILE_MB} MB are supported.`));
            const form = new FormData();
            form.append("file", file);
            run(
              () => api.upload<KnowledgeDoc>("/knowledge/file", form),
              () => {
                if (fileRef.current) fileRef.current.value = "";
              },
            );
          }}
        >
          <Field label="Document" htmlFor="k-file" hint={`PDF, DOCX or TXT, up to ${MAX_FILE_MB} MB.`}>
            <Input id="k-file" ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" className="h-auto py-2" />
          </Field>
          <ErrorNote error={error} />
          <div>
            <Button type="submit" disabled={busy}>
              {busy ? "Uploading..." : "Upload and index"}
            </Button>
          </div>
        </form>
      </TabsContent>
    </Tabs>
  );
}
