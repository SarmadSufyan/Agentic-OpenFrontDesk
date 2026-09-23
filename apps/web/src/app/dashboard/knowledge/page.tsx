"use client";

import { SearchIcon } from "lucide-react";
import { useState } from "react";

import { AddKnowledge } from "@/components/knowledge/add-knowledge";
import { DocList } from "@/components/knowledge/doc-list";
import { ErrorNote, PageHeader, Panel } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { SearchHit } from "@/lib/types";

export default function KnowledgePage() {
  return (
    <>
      <PageHeader
        eyebrow="Build"
        title="Knowledge"
        description="Everything your receptionist knows comes from here. It answers only from these sources and takes a message when it cannot find the answer."
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
        <Panel title="Add a source" description="Changes are live as soon as a source shows ready.">
          <AddKnowledge />
        </Panel>
        <div className="grid content-start gap-6">
          <Panel title="Sources">
            <DocList />
          </Panel>
          <RetrievalCheck />
        </div>
      </div>
    </>
  );
}

/** Shows exactly which passages the receptionist would read for a question. */
function RetrievalCheck() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <Panel title="Check what it would read" description="Type a customer question to see the passages it retrieves.">
      <form
        className="flex gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!q.trim()) return;
          setBusy(true);
          setError(null);
          try {
            setHits(await api.get<SearchHit[]>(`/knowledge/search?q=${encodeURIComponent(q.trim())}`));
          } catch (err) {
            setError(err);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="How much is a cleaning?" aria-label="Question" />
        <Button type="submit" variant="outline" disabled={busy}>
          <SearchIcon /> Search
        </Button>
      </form>
      <div className="mt-4 grid gap-2">
        <ErrorNote error={error} />
        {hits?.length === 0 && <p className="text-sm text-muted-foreground">Nothing relevant found. Add a source that covers this.</p>}
        {hits?.map((h, i) => (
          <div key={i} className="rounded-xl border bg-muted/40 p-3">
            <div className="mb-1.5 flex items-center justify-between gap-2 font-mono text-[0.7rem] text-muted-foreground">
              <span className="truncate text-primary">{h.source_title || "Source"}</span>
              <span>match {(h.score * 100).toFixed(0)}%</span>
            </div>
            <p className="line-clamp-4 text-sm">{h.text}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}
