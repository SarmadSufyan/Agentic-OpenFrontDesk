"use client";

import { CheckIcon, DownloadIcon, WorkflowIcon } from "lucide-react";
import { useState } from "react";
import useSWR, { useSWRConfig } from "swr";

import { CopyButton, ErrorNote, Field, Panel } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { N8nConnectResult, N8nTemplate } from "@/lib/types";
import { cn } from "@/lib/utils";

function downloadJson(filename: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Guided n8n setup: pick a template, give your n8n address, and get the webhook created plus a workflow
 * file with its secret already inside. The user then only imports it and connects their own accounts.
 */
export function ConnectN8n() {
  const { data: templates } = useSWR<N8nTemplate[]>("/integrations/n8n/templates");
  const { mutate } = useSWRConfig();
  const [choice, setChoice] = useState<string>("leads");
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<N8nConnectResult | null>(null);
  const chosen = templates?.find((t) => t.key === choice);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.post<N8nConnectResult>("/integrations/n8n/connect", { template: choice, n8n_url: url.trim() });
      setResult(r);
      downloadJson(r.filename, r.workflow);
      mutate("/integrations/webhooks");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <WorkflowIcon className="size-4 text-primary" /> Connect n8n
        </span>
      }
      description="Pick a ready-made workflow. We create the webhook and give you the workflow file with everything filled in."
    >
      {result ? (
        <div className="grid gap-4">
          <p className="flex items-center gap-2 text-sm font-medium">
            <CheckIcon className="size-4 text-primary" /> Webhook created and <span className="font-mono">{result.filename}</span> downloaded.
          </p>
          <ol className="grid list-decimal gap-2 pl-5 text-sm text-muted-foreground">
            <li>
              In n8n, open <span className="text-foreground">Workflows</span>, then <span className="text-foreground">Import from File</span>,
              and choose the downloaded file.
            </li>
            <li>Connect your own accounts in the nodes that ask for them ({chosen?.needs.join("; ") ?? "see the template"}).</li>
            <li>
              Click <span className="text-foreground">Publish</span> in n8n.
            </li>
            <li>
              Back here, press <span className="text-foreground">Test</span> on the new webhook below to check the connection.
            </li>
          </ol>
          <div className="grid gap-1.5 rounded-xl border bg-muted/40 p-3 text-sm">
            <p className="text-muted-foreground">
              The signing secret is already inside the file. It is shown here once, in case you need it again:
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <code className="rounded bg-background px-2 py-1 font-mono text-xs break-all">{result.webhook.secret}</code>
              <CopyButton value={result.webhook.secret ?? ""} />
            </div>
            <p className="text-muted-foreground">
              Events go to <span className="font-mono text-xs break-all text-foreground">{result.webhook_url}</span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => downloadJson(result.filename, result.workflow)}>
              <DownloadIcon /> Download again
            </Button>
            <Button variant="ghost" onClick={() => setResult(null)}>
              Connect another
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-4">
          <div className="grid gap-2 sm:grid-cols-2">
            {templates?.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setChoice(t.key)}
                aria-pressed={choice === t.key}
                className={cn(
                  "rounded-xl border p-3.5 text-left transition-colors",
                  choice === t.key ? "border-primary bg-accent/50" : "hover:border-primary/40",
                )}
              >
                <p className="text-sm font-medium">{t.name}</p>
                <p className="mt-1 text-xs text-muted-foreground">{t.description}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  You need: <span className="text-foreground">{t.needs.join("; ")}</span>
                </p>
              </button>
            ))}
          </div>
          <Field
            label="Your n8n address"
            htmlFor="n8n-url"
            hint={
              <>
                The address you open n8n at, for example https://n8n.yourbusiness.com. For the n8n that runs with the
                local setup, enter <span className="font-mono">http://n8n:5678</span>.
              </>
            }
          >
            <Input id="n8n-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://n8n.yourbusiness.com" />
          </Field>
          <ErrorNote error={error} />
          <div>
            <Button onClick={connect} disabled={busy || !url.trim() || !chosen}>
              <DownloadIcon /> {busy ? "Creating..." : "Create webhook and download workflow"}
            </Button>
          </div>
        </div>
      )}
    </Panel>
  );
}
