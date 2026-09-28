"use client";

import { MessageCircleIcon, RefreshCwIcon, ShieldAlertIcon, UnplugIcon, ZapIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import useSWR from "swr";

import { EmptyState, ErrorNote, Field, PageHeader, Panel, StatusPill } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { GITHUB_URL } from "@/lib/constants";
import { ago, when } from "@/lib/format";
import type { ChannelMessage, WhatsAppStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const GUIDE_URL = `${GITHUB_URL}/blob/main/docs/21-whatsapp.md`;

export default function WhatsAppPage() {
  const { workspace } = useAuth();
  const canManage = workspace?.role === "owner" || workspace?.role === "admin";
  const { data: status, mutate } = useSWR<WhatsAppStatus>(canManage ? "/channels/whatsapp" : null);

  return (
    <>
      <PageHeader
        eyebrow="Build"
        title="WhatsApp"
        description="Your receptionist answers WhatsApp messages with the same knowledge, booking and lead capture as your website chat, and remembers each customer's conversation for a day."
      />
      {!canManage ? (
        <p className="text-sm text-muted-foreground">Only workspace owners and admins can manage WhatsApp.</p>
      ) : !status ? (
        <Skeleton className="h-72 rounded-2xl" />
      ) : status.connected ? (
        <Connected status={status} onChange={() => mutate()} />
      ) : (
        <Setup onConnected={(s) => mutate(s, { revalidate: false })} />
      )}
    </>
  );
}

function RiskNote() {
  return (
    <div className="flex gap-3 rounded-xl border border-signal/30 bg-signal/8 p-4 text-sm">
      <ShieldAlertIcon className="mt-0.5 size-4 shrink-0 text-signal" />
      <div>
        <p className="font-medium">This uses a self-hosted gateway (WA-AKG), not Meta&apos;s official API.</p>
        <p className="mt-1 text-muted-foreground">
          The gateway links a normal WhatsApp number the way WhatsApp Web does. It is free and quick, but it is
          unofficial, and WhatsApp can restrict numbers that send automated messages. Use a dedicated number, not
          your personal one. For high volumes, ask us about the official WhatsApp Business Platform.
        </p>
      </div>
    </div>
  );
}

function Setup({ onConnected }: { onConnected: (s: WhatsAppStatus) => void }) {
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
      <div className="grid content-start gap-4">
        <Panel title="How it works">
          <ol className="grid list-decimal gap-2.5 pl-5 text-sm text-muted-foreground">
            <li>
              Run <span className="text-foreground">WA-AKG</span>, an open-source WhatsApp gateway, on your server or
              computer.
            </li>
            <li>In WA-AKG, create a session and scan its QR code with the WhatsApp number you want to use.</li>
            <li>In WA-AKG, create an API key.</li>
            <li>Enter the gateway address, session ID and API key here. We connect everything else.</li>
          </ol>
          <a href={GUIDE_URL} target="_blank" rel="noreferrer" className="mt-4 inline-block text-sm text-primary hover:underline">
            Step-by-step setup guide
          </a>
        </Panel>
        <RiskNote />
      </div>
      <Panel title="Connect your gateway" description="We check the details, then register ourselves with the gateway.">
        <form
          className="grid gap-4"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            setBusy(true);
            setError(null);
            try {
              const s = await api.put<WhatsAppStatus>("/channels/whatsapp", {
                base_url: String(f.get("base_url")).trim(),
                session_id: String(f.get("session_id")).trim(),
                api_key: String(f.get("api_key")).trim(),
              });
              toast.success("WhatsApp connected");
              onConnected(s);
            } catch (err) {
              setError(err);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Field label="Gateway address" htmlFor="wa-url" hint="Where WA-AKG runs, for example https://wa.yourbusiness.com">
            <Input id="wa-url" name="base_url" required placeholder="https://wa.yourbusiness.com" />
          </Field>
          <Field label="Session ID" htmlFor="wa-session" hint="Shown in WA-AKG next to the linked number.">
            <Input id="wa-session" name="session_id" required placeholder="e.g. frontdesk" />
          </Field>
          <Field label="API key" htmlFor="wa-key" hint="Stored encrypted. We never show it again.">
            <Input id="wa-key" name="api_key" type="password" required autoComplete="off" />
          </Field>
          <ErrorNote error={error} />
          <div>
            <Button type="submit" disabled={busy}>
              {busy ? "Connecting..." : "Connect WhatsApp"}
            </Button>
          </div>
        </form>
      </Panel>
    </div>
  );
}

function Connected({ status, onChange }: { status: WhatsAppStatus; onChange: () => void }) {
  const live = status.session_status === "CONNECTED";
  const [busy, setBusy] = useState<"test" | "disconnect" | null>(null);

  async function test() {
    setBusy("test");
    try {
      const r = await api.post<{ success: boolean; status_code: number | null; error: string | null }>("/channels/whatsapp/test");
      if (r.success) toast.success("Both directions work: we reached the gateway, and it reached us with a valid signature.");
      else toast.error(`The gateway could not reach us: ${r.error || `HTTP ${r.status_code}`}`);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function disconnect() {
    if (!window.confirm("Disconnect WhatsApp? Your receptionist stops answering WhatsApp messages immediately.")) return;
    setBusy("disconnect");
    try {
      await api.del("/channels/whatsapp");
      toast.success("WhatsApp disconnected");
      onChange();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid gap-6">
      <Panel
        title={
          <span className="flex flex-wrap items-center gap-2">
            <MessageCircleIcon className="size-4 text-primary" />
            {status.phone ? `+${status.phone}` : "WhatsApp"}
            <StatusPill status={live ? "live" : status.session_status === "UNREACHABLE" ? "failed" : "pending"} />
          </span>
        }
        description={
          live
            ? "Connected. Your receptionist answers new messages on this number."
            : status.session_status === "UNREACHABLE"
              ? `We cannot reach the gateway: ${status.session_error ?? "unknown error"}`
              : `The gateway says this session is ${status.session_status?.toLowerCase() ?? "not ready"}. Open WA-AKG and scan the QR code again.`
        }
        actions={
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => onChange()}>
              <RefreshCwIcon /> Refresh
            </Button>
            <Button size="sm" variant="outline" onClick={test} disabled={busy !== null}>
              <ZapIcon /> {busy === "test" ? "Testing..." : "Test connection"}
            </Button>
            <Button size="sm" variant="destructive" onClick={disconnect} disabled={busy !== null}>
              <UnplugIcon /> Disconnect
            </Button>
          </div>
        }
      >
        <dl className="grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-[9rem_1fr]">
          <dt className="text-muted-foreground">Gateway</dt>
          <dd className="font-mono text-xs break-all">{status.base_url}</dd>
          <dt className="text-muted-foreground">Session</dt>
          <dd>{status.session_id}</dd>
          <dt className="text-muted-foreground">API key</dt>
          <dd className="font-mono text-xs">•••• {status.api_key_hint}</dd>
          <dt className="text-muted-foreground">Last message</dt>
          <dd>{ago(status.last_inbound_at)}</dd>
          <dt className="text-muted-foreground">Gateway sends to</dt>
          <dd className="font-mono text-xs break-all">{status.inbound_url}</dd>
        </dl>
        {status.last_error && (
          <p className="mt-3 rounded-lg border border-destructive/30 bg-destructive/8 px-3 py-2 text-sm text-destructive">
            {status.last_error}
          </p>
        )}
      </Panel>
      <Conversations />
      <RiskNote />
    </div>
  );
}

/** Messages grouped by customer, newest conversation first; refreshes every 10 seconds. */
function Conversations() {
  const { data: messages } = useSWR<ChannelMessage[]>("/channels/whatsapp/messages?limit=300", { refreshInterval: 10000 });
  const [selected, setSelected] = useState<string | null>(null);

  if (!messages) return <Skeleton className="h-80 rounded-2xl" />;
  if (!messages.length) {
    return (
      <EmptyState icon={MessageCircleIcon} title="No conversations yet">
        Send a WhatsApp message to the connected number from another phone. The conversation appears here.
      </EmptyState>
    );
  }

  const threads = new Map<string, ChannelMessage[]>();
  for (const m of messages) threads.set(m.contact, [...(threads.get(m.contact) ?? []), m]);
  const contacts = [...threads.entries()].map(([contact, list]) => ({ contact, list, latest: list[0] }));
  const active = selected && threads.has(selected) ? selected : contacts[0].contact;
  const thread = [...(threads.get(active) ?? [])].reverse();

  return (
    <section className="grid overflow-hidden rounded-2xl border bg-card md:grid-cols-[18rem_1fr]">
      <ul className="max-h-[520px] divide-y overflow-y-auto border-b md:border-r md:border-b-0">
        {contacts.map(({ contact, latest, list }) => (
          <li key={contact}>
            <button
              type="button"
              onClick={() => setSelected(contact)}
              className={cn("w-full px-4 py-3 text-left transition-colors hover:bg-muted/50", contact === active && "bg-muted")}
            >
              <span className="flex items-baseline justify-between gap-2">
                <span className="truncate text-sm font-medium">{list.find((m) => m.contact_name)?.contact_name ?? `+${contact}`}</span>
                <span className="shrink-0 text-xs text-muted-foreground">{ago(latest.created_at)}</span>
              </span>
              <span className="block truncate text-xs text-muted-foreground">
                {latest.direction === "out" ? "Receptionist: " : ""}
                {latest.text}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <div className="flex max-h-[520px] flex-col">
        <p className="border-b px-4 py-3 text-sm">
          <span className="font-medium">+{active}</span>
        </p>
        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {thread.map((m) => (
            <div key={m.id} className={cn("flex flex-col gap-1", m.direction === "out" ? "items-start" : "items-end")}>
              <p
                className={cn(
                  "max-w-[85%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap",
                  m.direction === "out" ? "rounded-tl-sm bg-secondary" : "rounded-tr-sm bg-primary text-primary-foreground",
                )}
              >
                {m.text}
              </p>
              <span className="text-[0.68rem] text-muted-foreground">
                {m.direction === "out" ? "Receptionist" : "Customer"} · {when(m.created_at)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
