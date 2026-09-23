"use client";

import { InboxIcon, SearchIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import useSWR from "swr";

import { EmptyState, ErrorNote, Field, NativeSelect, PageHeader, Panel, Stat, StatusPill } from "@/components/kit";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ago, when } from "@/lib/format";
import type {
  AllowlistEntry,
  ContactOptions,
  ContactPage,
  ContactRequest,
  ContactStatus,
  VoiceSessions,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUSES: ContactStatus[] = ["new", "contacted", "scheduled", "won", "lost", "spam"];

export default function AdminPage() {
  const { me } = useAuth();
  if (!me?.is_admin) {
    return (
      <EmptyState icon={InboxIcon} title="Admins only">
        This area is for platform admins listed in ADMIN_EMAILS.
      </EmptyState>
    );
  }
  return (
    <>
      <PageHeader eyebrow="Platform" title="Admin" description="Custom-solution requests and fair-use voice access." />
      <div className="grid gap-10">
        <Inbox />
        <VoiceAccess />
      </div>
    </>
  );
}

function Inbox() {
  const [status, setStatus] = useState<string>("");
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const qs = new URLSearchParams({ limit: "100" });
  if (status) qs.set("status", status);
  if (query) qs.set("q", query);
  const { data, mutate } = useSWR<ContactPage>(`/admin/contact-requests?${qs}`);
  const { data: options } = useSWR<ContactOptions>("/contact/options");
  const label = (n: string) => options?.needs[n] ?? n;

  return (
    <section>
      <h2 className="mb-4 font-display text-3xl">Custom-solution requests</h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="New" value={data?.counts.new ?? "—"} />
        <Stat label="Contacted" value={data?.counts.contacted ?? "—"} />
        <Stat label="Call scheduled" value={data?.counts.scheduled ?? "—"} />
        <Stat label="Won" value={data?.counts.won ?? "—"} />
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <NativeSelect value={status} onChange={(e) => setStatus(e.target.value)} className="w-44" aria-label="Status filter">
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s} ({data?.counts[s] ?? 0})
            </option>
          ))}
        </NativeSelect>
        <form
          className="relative"
          onSubmit={(e) => {
            e.preventDefault();
            setQuery(q.trim());
          }}
        >
          <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search and press Enter" className="w-64 pl-8" aria-label="Search requests" />
        </form>
      </div>
      <div className="mt-4">
        {!data ? null : data.items.length ? (
          <ul className="divide-y overflow-hidden rounded-2xl border">
            {data.items.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => setOpenId(r.id)}
                  className="grid w-full gap-1 bg-card px-5 py-4 text-left transition-colors hover:bg-muted/50 sm:grid-cols-[1fr_auto] sm:items-center"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">
                      {r.name}
                      {r.company ? <span className="text-muted-foreground"> · {r.company}</span> : null}
                    </span>
                    <span className="block truncate text-sm text-muted-foreground">
                      {r.needs.map(label).join(", ") || "General enquiry"} · {ago(r.created_at)}
                    </span>
                  </span>
                  <StatusPill status={r.status} />
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon={InboxIcon} title="No requests match">
            Requests from the contact page appear here.
          </EmptyState>
        )}
      </div>
      <Sheet open={!!openId} onOpenChange={(o) => !o && setOpenId(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
          {openId && (
            <RequestDetail
              id={openId}
              label={label}
              onChanged={() => mutate()}
              onDeleted={() => {
                setOpenId(null);
                mutate();
              }}
            />
          )}
        </SheetContent>
      </Sheet>
    </section>
  );
}

function RequestDetail({
  id,
  label,
  onChanged,
  onDeleted,
}: {
  id: string;
  label: (n: string) => string;
  onChanged: () => void;
  onDeleted: () => void;
}) {
  const { data: r, mutate } = useSWR<ContactRequest>(`/admin/contact-requests/${id}`);
  const [error, setError] = useState<unknown>(null);
  const [sending, setSending] = useState(false);
  if (!r) return <p className="p-6 text-sm text-muted-foreground">Loading...</p>;

  const toLocal = (iso: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    const p = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
  };

  return (
    <>
      <SheetHeader className="border-b">
        <SheetTitle className="font-display text-2xl font-normal">
          {r.name}
          {r.company ? ` · ${r.company}` : ""}
        </SheetTitle>
        <SheetDescription>
          Received {when(r.created_at)} · {r.source ?? "contact page"}
          {r.user_id ? " · signed-in user" : ""}
        </SheetDescription>
      </SheetHeader>
      <div className="grid gap-5 px-4 pb-8">
        <dl className="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1.5 text-sm">
          {(
            [
              ["Email", r.email],
              ["Phone", r.phone],
              ["Website", r.website],
              ["Team size", r.team_size],
              ["Budget", r.budget?.replace("_", " ")],
              ["Needs", r.needs.map(label).join(", ")],
              ["Handled by", r.handled_by],
              ["Last contacted", r.last_contacted_at ? when(r.last_contacted_at) : null],
            ] as const
          )
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-muted-foreground">{k}</dt>
                <dd className="break-words">{v}</dd>
              </div>
            ))}
        </dl>
        <p className="rounded-xl border bg-muted/40 p-3.5 text-sm whitespace-pre-wrap">{r.message}</p>
        <a href={`mailto:${r.email}`} className={cn(buttonVariants({ variant: "outline" }), "w-fit")}>
          Reply by email
        </a>

        <form
          className="grid gap-3 rounded-xl border p-4"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            const at = String(f.get("meeting_at"));
            setError(null);
            try {
              await api.patch(`/admin/contact-requests/${r.id}`, {
                status: String(f.get("status")),
                notes: String(f.get("notes")),
                meeting_link: String(f.get("meeting_link")).trim() || null,
                meeting_at: at ? new Date(at).toISOString() : null,
              });
              toast.success("Saved");
              mutate();
              onChanged();
            } catch (err) {
              setError(err);
            }
          }}
        >
          <p className="text-sm font-semibold">Track</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Status" htmlFor="cr-status">
              <NativeSelect id="cr-status" name="status" defaultValue={r.status}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <Field label="Meeting time" htmlFor="cr-at">
              <Input id="cr-at" name="meeting_at" type="datetime-local" defaultValue={toLocal(r.meeting_at)} />
            </Field>
          </div>
          <Field label="Meeting link" htmlFor="cr-link">
            <Input id="cr-link" name="meeting_link" defaultValue={r.meeting_link ?? ""} placeholder="https://meet..." />
          </Field>
          <Field label="Internal notes" htmlFor="cr-notes">
            <Textarea id="cr-notes" name="notes" rows={3} defaultValue={r.notes ?? ""} />
          </Field>
          <ErrorNote error={error} />
          <div>
            <Button type="submit">Save</Button>
          </div>
        </form>

        <form
          className="grid gap-3 rounded-xl border border-primary/25 bg-accent/30 p-4"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            setSending(true);
            try {
              await api.post(`/admin/contact-requests/${r.id}/scheduling-email`, {
                message: String(f.get("message")).trim() || null,
                link: String(f.get("link")).trim() || null,
              });
              toast.success(`Scheduling email sent to ${r.email}`);
              mutate();
              onChanged();
            } catch (err) {
              toast.error((err as Error).message);
            } finally {
              setSending(false);
            }
          }}
        >
          <p className="text-sm font-semibold">Send a scheduling email</p>
          <p className="text-xs text-muted-foreground">
            A personal note plus your booking link, prefilled with their name and email. Marks the request as contacted.
          </p>
          <Textarea name="message" rows={3} placeholder="Personal note (optional)" aria-label="Personal note" />
          <Input name="link" placeholder="Booking link (defaults to SCHEDULING_URL)" aria-label="Booking link" />
          <div>
            <Button type="submit" disabled={sending}>
              {sending ? "Sending..." : "Send email"}
            </Button>
          </div>
        </form>

        <Button
          variant="destructive"
          className="w-fit"
          onClick={async () => {
            if (!window.confirm("Permanently delete this request and the person's details?")) return;
            try {
              await api.del(`/admin/contact-requests/${r.id}`);
              toast.success("Deleted");
              onDeleted();
            } catch (err) {
              toast.error((err as Error).message);
            }
          }}
        >
          Delete request
        </Button>
      </div>
    </>
  );
}

function VoiceAccess() {
  const { data: sessions } = useSWR<VoiceSessions>("/admin/voice/sessions", { refreshInterval: 10000 });
  const { data: allow, mutate } = useSWR<AllowlistEntry[]>("/admin/allowlist");
  const [error, setError] = useState<unknown>(null);

  return (
    <section>
      <h2 className="mb-4 font-display text-3xl">Voice access</h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Stat label="Live sessions" value={sessions ? `${sessions.active.length} / ${sessions.capacity}` : "—"} />
        <Stat label="Waiting in queue" value={sessions?.queue.length ?? "—"} />
        <Stat label="Priority allowlist" value={allow?.length ?? "—"} />
      </div>
      <Panel className="mt-4" title="Priority allowlist" description="People on this list skip the voice queue, even when every line is busy.">
        <form
          className="flex flex-wrap gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = e.currentTarget;
            const d = new FormData(f);
            setError(null);
            try {
              await api.post("/admin/allowlist", { email: String(d.get("email")).trim(), note: String(d.get("note")).trim() || null });
              f.reset();
              mutate();
            } catch (err) {
              setError(err);
            }
          }}
        >
          <Input name="email" type="email" required placeholder="person@company.com" className="max-w-xs" aria-label="Email" />
          <Input name="note" placeholder="Note (optional)" className="max-w-xs" aria-label="Note" />
          <Button type="submit">Add</Button>
        </form>
        <div className="mt-3">
          <ErrorNote error={error} />
        </div>
        {!!allow?.length && (
          <ul className="mt-4 divide-y overflow-hidden rounded-xl border">
            {allow.map((a) => (
              <li key={a.email} className="flex items-center gap-3 bg-card px-4 py-2.5 text-sm">
                <span className="font-medium">{a.email}</span>
                {a.note && <span className="text-muted-foreground">{a.note}</span>}
                <Button
                  size="sm"
                  variant="ghost"
                  className="ml-auto"
                  onClick={async () => {
                    if (!window.confirm(`Remove ${a.email} from the allowlist?`)) return;
                    await api.del(`/admin/allowlist/${encodeURIComponent(a.email)}`);
                    mutate();
                  }}
                >
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </section>
  );
}
