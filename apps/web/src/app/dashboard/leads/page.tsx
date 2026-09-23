"use client";

import { InboxIcon, SearchIcon } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { EmptyState, PageHeader } from "@/components/kit";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ago } from "@/lib/format";
import type { Lead } from "@/lib/types";

export default function LeadsPage() {
  const { data: leads, isLoading } = useSWR<Lead[]>("/leads");
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const rows = (leads ?? []).filter(
    (l) => !needle || [l.name, l.phone, l.email, l.intent, l.message].some((v) => v?.toLowerCase().includes(needle)),
  );

  return (
    <>
      <PageHeader
        eyebrow="Activity"
        title="Leads"
        description="Messages, callback requests and contact details captured by phone, chat and the API."
        actions={
          <div className="relative w-64">
            <SearchIcon className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search leads" className="pl-8" aria-label="Search leads" />
          </div>
        }
      />
      {isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : !leads?.length ? (
        <EmptyState icon={InboxIcon} title="No leads yet">
          When someone asks for a callback or leaves a message, it lands here and in any connected tools.
        </EmptyState>
      ) : (
        <div className="grid gap-3">
          {rows.map((l) => (
            <article key={l.id} className="rounded-2xl border bg-card p-5">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h2 className="font-semibold">{l.name || "Unknown caller"}</h2>
                {l.intent && <span className="rounded-full bg-accent px-2.5 py-0.5 text-xs text-accent-foreground">{l.intent}</span>}
                <span className="ml-auto text-xs text-muted-foreground">{ago(l.created_at)}</span>
              </div>
              {l.message && <p className="mt-2 text-sm text-muted-foreground">{l.message}</p>}
              <div className="mt-3 flex flex-wrap gap-4 text-sm">
                {l.phone && (
                  <a href={`tel:${l.phone}`} className="font-mono text-primary hover:underline">
                    {l.phone}
                  </a>
                )}
                {l.email && (
                  <a href={`mailto:${l.email}`} className="text-primary hover:underline">
                    {l.email}
                  </a>
                )}
              </div>
            </article>
          ))}
          {!rows.length && <p className="text-sm text-muted-foreground">No leads match &ldquo;{q}&rdquo;.</p>}
        </div>
      )}
    </>
  );
}
