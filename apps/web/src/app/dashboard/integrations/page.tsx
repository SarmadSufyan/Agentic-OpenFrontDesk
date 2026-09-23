"use client";

import { KeyRoundIcon, PlusIcon, WebhookIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import useSWR from "swr";

import { CodeBlock, EmptyState, ErrorNote, Field, PageHeader, Panel, StatusPill } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { API_URL, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ago, when } from "@/lib/format";
import type { ApiKey, Delivery, EventType, Webhook } from "@/lib/types";

type Secret = { title: string; value: string; note: string };

export default function IntegrationsPage() {
  const { workspace } = useAuth();
  const canManage = workspace?.role === "owner" || workspace?.role === "admin";
  const [secret, setSecret] = useState<Secret | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Integrations"
        description="Connect your receptionist to n8n, Zapier, Make or your own code. Webhooks push events the moment they happen; API keys let your workflows act back."
      />
      {!canManage ? (
        <p className="text-sm text-muted-foreground">Only workspace owners and admins can manage integrations.</p>
      ) : (
        <div className="grid gap-6">
          <Webhooks onSecret={setSecret} />
          <ApiKeys onSecret={setSecret} />
          <Panel title="Quick start" description="Ask your receptionist a question from any tool that can make an HTTP request.">
            <CodeBlock
              code={`curl ${API_URL}/v1/chat \\\n  -H "X-API-Key: ofd_live_..." \\\n  -H "Content-Type: application/json" \\\n  -d '{"message": "What are your opening hours?"}'`}
            />
            <p className="mt-3 text-sm text-muted-foreground">
              Also available: leads, bookings, availability, calls and knowledge search.{" "}
              <a href={`${API_URL}/docs#/public-api`} target="_blank" rel="noreferrer" className="text-primary hover:underline">
                Full API reference
              </a>
            </p>
          </Panel>
        </div>
      )}

      <Dialog open={!!secret} onOpenChange={(o) => !o && setSecret(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{secret?.title}</DialogTitle>
            <DialogDescription>{secret?.note}</DialogDescription>
          </DialogHeader>
          {secret && <CodeBlock code={secret.value} />}
          <Button onClick={() => setSecret(null)}>I have saved it</Button>
        </DialogContent>
      </Dialog>
    </>
  );
}

function Webhooks({ onSecret }: { onSecret: (s: Secret) => void }) {
  const { data: hooks, mutate } = useSWR<Webhook[]>("/integrations/webhooks");
  const { data: events } = useSWR<EventType[]>("/integrations/events");
  const [adding, setAdding] = useState(false);
  const [chosen, setChosen] = useState<string[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [logFor, setLogFor] = useState<Webhook | null>(null);

  async function act(fn: () => Promise<unknown>, ok?: string) {
    try {
      await fn();
      if (ok) toast.success(ok);
      mutate();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <WebhookIcon className="size-4 text-primary" /> Webhooks
        </span>
      }
      description="Signed with HMAC-SHA256, retried on failure, and logged."
      actions={
        !adding && (
          <Button size="sm" onClick={() => setAdding(true)}>
            <PlusIcon /> Add webhook
          </Button>
        )
      }
    >
      {adding && (
        <form
          className="mb-5 grid gap-4 rounded-xl border bg-muted/30 p-4"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            setError(null);
            try {
              const created = await api.post<Webhook>("/integrations/webhooks", {
                url: String(f.get("url")).trim(),
                description: String(f.get("description")).trim() || null,
                events: chosen.length ? chosen : ["*"],
              });
              setAdding(false);
              setChosen([]);
              mutate();
              onSecret({
                title: "Webhook signing secret",
                value: created.secret ?? "",
                note: "Verify the X-OFD-Signature header with this secret. It is shown only once; rotate it to get a new one.",
              });
            } catch (err) {
              setError(err);
            }
          }}
        >
          <Field label="Endpoint URL" htmlFor="wh-url">
            <Input id="wh-url" name="url" type="url" required placeholder="https://your-n8n.example.com/webhook/openfrontdesk" />
          </Field>
          <Field label="Description (optional)" htmlFor="wh-desc">
            <Input id="wh-desc" name="description" placeholder="Leads to Google Sheets and Slack" />
          </Field>
          <fieldset className="grid gap-2">
            <legend className="mb-1 text-sm font-medium">Events (none selected sends all)</legend>
            {events?.map((ev) => (
              <label key={ev.type} className="flex items-start gap-2.5 text-sm">
                <Checkbox
                  checked={chosen.includes(ev.type)}
                  onCheckedChange={(c) => setChosen((cur) => (c ? [...cur, ev.type] : cur.filter((x) => x !== ev.type)))}
                  className="mt-0.5"
                />
                <span>
                  <code className="font-mono text-xs text-primary">{ev.type}</code>
                  <span className="block text-muted-foreground">{ev.description}</span>
                </span>
              </label>
            ))}
          </fieldset>
          <ErrorNote error={error} />
          <div className="flex gap-2">
            <Button type="submit">Save webhook</Button>
            <Button type="button" variant="ghost" onClick={() => setAdding(false)}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {!hooks ? null : hooks.length ? (
        <ul className="divide-y overflow-hidden rounded-xl border">
          {hooks.map((h) => (
            <li key={h.id} className="grid gap-3 bg-card p-4 sm:grid-cols-[1fr_auto] sm:items-center">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusPill status={h.is_active ? "active" : "disabled"} />
                  <p className="truncate font-mono text-sm">{h.url}</p>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {h.description ? `${h.description} · ` : ""}
                  {h.events.join(", ")} · last delivery {ago(h.last_delivery_at)}
                  {h.last_status ? ` (HTTP ${h.last_status})` : ""}
                  {h.failure_count ? ` · ${h.failure_count} failed in a row` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    act(async () => {
                      const d = await api.post<Delivery>(`/integrations/webhooks/${h.id}/test`);
                      if (d.success) toast.success(`Delivered (HTTP ${d.status_code}, ${d.duration_ms} ms)`);
                      else toast.error(`Failed: ${d.error || `HTTP ${d.status_code}`}`);
                    })
                  }
                >
                  Test
                </Button>
                <Button size="sm" variant="outline" onClick={() => setLogFor(h)}>
                  Log
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => act(() => api.patch(`/integrations/webhooks/${h.id}`, { is_active: !h.is_active }), h.is_active ? "Disabled" : "Enabled")}
                >
                  {h.is_active ? "Disable" : "Enable"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    act(async () => {
                      if (!window.confirm("Rotate the secret? Receivers using the old one will start rejecting events.")) return;
                      const r = await api.post<Webhook>(`/integrations/webhooks/${h.id}/rotate-secret`);
                      onSecret({ title: "New signing secret", value: r.secret ?? "", note: "Update your receiver with this secret. It is shown only once." });
                    })
                  }
                >
                  Rotate
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => window.confirm("Delete this webhook and its delivery log?") && act(() => api.del(`/integrations/webhooks/${h.id}`), "Deleted")}
                >
                  Delete
                </Button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        !adding && (
          <EmptyState icon={WebhookIcon} title="No webhooks yet">
            Add an n8n, Zapier or Make webhook URL to receive leads, bookings and call transcripts as they happen.
          </EmptyState>
        )
      )}

      <Sheet open={!!logFor} onOpenChange={(o) => !o && setLogFor(null)}>
        <SheetContent className="w-full sm:max-w-lg">
          <SheetHeader className="border-b">
            <SheetTitle>Recent deliveries</SheetTitle>
            <p className="truncate font-mono text-xs text-muted-foreground">{logFor?.url}</p>
          </SheetHeader>
          {logFor && <DeliveryLog id={logFor.id} />}
        </SheetContent>
      </Sheet>
    </Panel>
  );
}

function DeliveryLog({ id }: { id: string }) {
  const { data } = useSWR<Delivery[]>(`/integrations/webhooks/${id}/deliveries`);
  if (!data) return <p className="px-4 text-sm text-muted-foreground">Loading...</p>;
  if (!data.length) return <p className="px-4 text-sm text-muted-foreground">No deliveries yet. Press Test to send one.</p>;
  return (
    <ul className="flex-1 divide-y overflow-y-auto px-4 pb-6">
      {data.map((d) => (
        <li key={d.id} className="py-3 text-sm">
          <div className="flex items-center gap-2">
            <StatusPill status={d.success ? "ok" : "failed"} />
            <code className="font-mono text-xs">{d.event}</code>
            <span className="ml-auto text-xs text-muted-foreground">{when(d.created_at)}</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            HTTP {d.status_code ?? "—"} · {d.attempts} {d.attempts === 1 ? "attempt" : "attempts"} · {d.duration_ms ?? "—"} ms
            {d.error ? ` · ${d.error}` : ""}
          </p>
        </li>
      ))}
    </ul>
  );
}

function ApiKeys({ onSecret }: { onSecret: (s: Secret) => void }) {
  const { data: keys, mutate } = useSWR<ApiKey[]>("/integrations/api-keys");
  const [error, setError] = useState<unknown>(null);

  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <KeyRoundIcon className="size-4 text-primary" /> API keys
        </span>
      }
      description="Stored only as a hash and shown once. Send as the X-API-Key header."
    >
      <form
        className="mb-5 flex flex-wrap gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = e.currentTarget;
          const name = String(new FormData(f).get("name")).trim();
          setError(null);
          try {
            const k = await api.post<ApiKey>("/integrations/api-keys", { name });
            f.reset();
            mutate();
            onSecret({ title: "New API key", value: k.key ?? "", note: "Copy it now. It is shown only once and stored only as a hash." });
          } catch (err) {
            setError(err);
          }
        }}
      >
        <Input name="name" required placeholder="Key name, e.g. n8n production" className="max-w-xs" aria-label="Key name" />
        <Button type="submit">Create key</Button>
      </form>
      <div className="mb-3">
        <ErrorNote error={error} />
      </div>
      {keys?.length ? (
        <ul className="divide-y overflow-hidden rounded-xl border">
          {keys.map((k) => (
            <li key={k.id} className="flex flex-wrap items-center gap-3 bg-card px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{k.name}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {k.prefix}... · last used {ago(k.last_used_at)}
                </p>
              </div>
              <StatusPill status={k.revoked_at ? "revoked" : "active"} />
              {!k.revoked_at && (
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={async () => {
                    if (!window.confirm(`Revoke "${k.name}"? Workflows using it stop working immediately.`)) return;
                    try {
                      await api.del(`/integrations/api-keys/${k.id}`);
                      toast.success("Key revoked");
                      mutate();
                    } catch (err) {
                      toast.error((err as Error).message);
                    }
                  }}
                >
                  Revoke
                </Button>
              )}
            </li>
          ))}
        </ul>
      ) : (
        keys && <p className="text-sm text-muted-foreground">No keys yet.</p>
      )}
    </Panel>
  );
}
