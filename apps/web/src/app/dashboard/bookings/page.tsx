"use client";

import { CalendarDaysIcon } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { EmptyState, PageHeader, StatusPill } from "@/components/kit";
import { Skeleton } from "@/components/ui/skeleton";
import { day, time } from "@/lib/format";
import type { Booking } from "@/lib/types";

export default function BookingsPage() {
  const { data: bookings, isLoading } = useSWR<Booking[]>("/bookings");
  // Compare instants, not strings: timestamps may carry different UTC offsets.
  const [now] = useState(() => Date.now());
  const at = (b: Booking) => new Date(b.start_at).getTime();
  const upcoming = (bookings ?? []).filter((b) => at(b) >= now).sort((a, b) => at(a) - at(b));
  const past = (bookings ?? []).filter((b) => at(b) < now);

  return (
    <>
      <PageHeader
        eyebrow="Activity"
        title="Bookings"
        description="Appointments your receptionist booked, always inside your business hours."
      />
      {isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : !bookings?.length ? (
        <EmptyState icon={CalendarDaysIcon} title="No bookings yet">
          Ask for an appointment in the test console to see one appear here.
        </EmptyState>
      ) : (
        <div className="grid gap-10">
          <BookingGroup title="Upcoming" items={upcoming} empty="Nothing booked ahead." />
          <BookingGroup title="Past" items={past} empty="No past bookings." muted />
        </div>
      )}
    </>
  );
}

function BookingGroup({ title, items, empty, muted }: { title: string; items: Booking[]; empty: string; muted?: boolean }) {
  return (
    <section>
      <h2 className="mb-3 text-xs font-semibold tracking-[0.14em] text-muted-foreground uppercase">
        {title} · {items.length}
      </h2>
      {items.length ? (
        <ul className="divide-y overflow-hidden rounded-2xl border bg-card">
          {items.map((b) => (
            <li key={b.id} className={muted ? "flex items-center gap-5 px-5 py-4 opacity-70" : "flex items-center gap-5 px-5 py-4"}>
              <div className="w-28 shrink-0">
                <p className="text-xs text-muted-foreground">{day(b.start_at)}</p>
                <p className="font-display text-2xl leading-tight">{time(b.start_at)}</p>
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{b.customer_name || "Customer"}</p>
                <p className="truncate text-sm text-muted-foreground">
                  {b.service || "Appointment"}
                  {b.customer_phone ? ` · ${b.customer_phone}` : ""}
                </p>
              </div>
              <StatusPill status={b.status} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">{empty}</p>
      )}
    </section>
  );
}
