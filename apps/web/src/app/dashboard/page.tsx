"use client";

import { ArrowRightIcon, CalendarDaysIcon, CheckIcon, InboxIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";

import { EmptyState, PageHeader, Panel, Stat, StatusPill } from "@/components/kit";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { ago, day, time } from "@/lib/format";
import { useAnalytics, useDocs, useTenant } from "@/lib/hooks";
import type { Booking, Lead } from "@/lib/types";
import { cn } from "@/lib/utils";

function greeting(now: number) {
  const h = new Date(now).getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function OverviewPage() {
  const { me } = useAuth();
  const [now] = useState(() => Date.now()); // fixed per visit; render stays pure
  const { data: stats } = useAnalytics();
  const { data: tenant } = useTenant();
  const { data: docs } = useDocs();
  const { data: leads } = useSWR<Lead[]>("/leads");
  const { data: bookings } = useSWR<Booking[]>("/bookings");

  const first = me?.user.name?.split(" ")[0];
  const settings = tenant?.settings ?? {};
  const steps = [
    { done: Boolean(settings.onboarded), label: "Set up your business profile", href: "/onboarding" },
    { done: Boolean(docs?.some((d) => d.status === "ready")), label: "Teach it about your business", href: "/dashboard/knowledge" },
    { done: Boolean(settings.tested_at), label: "Test it like a customer", href: "/dashboard/test" },
    { done: Boolean(settings.widget_copied_at), label: "Add it to your website", href: "/dashboard/deploy" },
  ];
  const remaining = steps.filter((s) => !s.done).length;
  const upcoming = (bookings ?? [])
    .filter((b) => b.status === "confirmed" && new Date(b.start_at).getTime() >= now)
    .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime())
    .slice(0, 5);

  return (
    <>
      <PageHeader
        eyebrow={tenant?.name ?? "Overview"}
        title={
          <>
            {greeting(now)}
            {first ? `, ${first}` : ""}.
          </>
        }
        description="Here is what your front desk has been up to."
      />

      {tenant && docs && remaining > 0 && (
        <Panel
          className="mb-6 border-primary/25 bg-accent/40"
          title="Finish setting up"
          description={`${4 - remaining} of 4 done. Each step takes a minute or two.`}
        >
          <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((s, i) => (
              <li key={s.label}>
                <Link
                  href={s.href}
                  className={cn(
                    "flex h-full items-start gap-3 rounded-xl border bg-card p-3.5 text-sm transition-colors hover:border-primary/50",
                    s.done && "opacity-60",
                  )}
                >
                  <span
                    className={cn(
                      "grid size-6 shrink-0 place-items-center rounded-full border text-xs font-semibold",
                      s.done ? "border-primary bg-primary text-primary-foreground" : "text-muted-foreground",
                    )}
                  >
                    {s.done ? <CheckIcon className="size-3.5" /> : i + 1}
                  </span>
                  <span className={cn(s.done && "line-through")}>{s.label}</span>
                </Link>
              </li>
            ))}
          </ol>
        </Panel>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {stats ? (
          <>
            <Stat label="Calls" value={stats.calls_total} hint={stats.avg_latency_ms ? `~${Math.round(stats.avg_latency_ms)} ms to first word` : "Answered by the receptionist"} />
            <Stat label="Bookings" value={stats.bookings_total} hint="Across voice and chat" />
            <Stat label="Leads" value={stats.leads_total} hint="Messages and callbacks" />
            <Stat label="Minutes" value={stats.minutes_total} hint="Talk time handled" />
          </>
        ) : (
          [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[118px] rounded-2xl" />)
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel
          title="Latest leads"
          actions={
            <Link href="/dashboard/leads" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
              View all <ArrowRightIcon />
            </Link>
          }
        >
          {!leads ? (
            <Skeleton className="h-40 rounded-xl" />
          ) : leads.length ? (
            <ul className="divide-y">
              {leads.slice(0, 5).map((l) => (
                <li key={l.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{l.name || l.phone || l.email || "Unknown caller"}</p>
                    <p className="truncate text-sm text-muted-foreground">{l.message || l.intent || "No message"}</p>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">{ago(l.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState icon={InboxIcon} title="No leads yet">
              When a caller or visitor leaves their details, they show up here and in your integrations.
            </EmptyState>
          )}
        </Panel>

        <Panel
          title="Upcoming bookings"
          actions={
            <Link href="/dashboard/bookings" className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}>
              View all <ArrowRightIcon />
            </Link>
          }
        >
          {!bookings ? (
            <Skeleton className="h-40 rounded-xl" />
          ) : upcoming.length ? (
            <ul className="divide-y">
              {upcoming.map((b) => (
                <li key={b.id} className="flex items-center gap-4 py-3 first:pt-0 last:pb-0">
                  <div className="w-20 shrink-0">
                    <p className="text-xs text-muted-foreground">{day(b.start_at)}</p>
                    <p className="font-display text-xl leading-tight">{time(b.start_at)}</p>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{b.customer_name || "Customer"}</p>
                    <p className="truncate text-sm text-muted-foreground">{b.service || "Appointment"}</p>
                  </div>
                  <StatusPill status={b.status} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState icon={CalendarDaysIcon} title="Nothing booked ahead">
              Bookings made by phone or chat appear here, inside your business hours.
            </EmptyState>
          )}
        </Panel>
      </div>
    </>
  );
}
