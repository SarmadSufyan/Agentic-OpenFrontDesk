"use client";

import { PhoneCallIcon } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";

import { EmptyState, PageHeader, StatusPill } from "@/components/kit";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { duration, when } from "@/lib/format";
import type { Call, CallDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function CallsPage() {
  const { data: calls, isLoading } = useSWR<Call[]>("/calls");
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        eyebrow="Activity"
        title="Calls"
        description="Every call your receptionist handled, with the full transcript."
      />
      {isLoading ? (
        <Skeleton className="h-64 rounded-2xl" />
      ) : !calls?.length ? (
        <EmptyState icon={PhoneCallIcon} title="No calls yet">
          Calls appear here after they end. Try one from the test console to see the full flow.
        </EmptyState>
      ) : (
        <div className="overflow-hidden rounded-2xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-5">When</TableHead>
                <TableHead>Caller</TableHead>
                <TableHead>Outcome</TableHead>
                <TableHead className="pr-5 text-right">Length</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {calls.map((c) => (
                <TableRow key={c.id} className="cursor-pointer" onClick={() => setOpenId(c.id)}>
                  <TableCell className="pl-5">{when(c.started_at ?? c.created_at)}</TableCell>
                  <TableCell>{c.caller_number || <span className="text-muted-foreground">Web caller</span>}</TableCell>
                  <TableCell>
                    <StatusPill status={c.status === "active" ? "live" : c.outcome || c.status} />
                  </TableCell>
                  <TableCell className="pr-5 text-right font-mono tabular-nums">{duration(c.duration_seconds)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      <Sheet open={!!openId} onOpenChange={(o) => !o && setOpenId(null)}>
        <SheetContent className="w-full sm:max-w-lg">{openId && <CallTranscript id={openId} />}</SheetContent>
      </Sheet>
    </>
  );
}

function CallTranscript({ id }: { id: string }) {
  const { data: call } = useSWR<CallDetail>(`/calls/${id}`);
  const ttft = (call?.latency_ms?.llm_ttft as { p50_ms?: number } | undefined)?.p50_ms;
  return (
    <>
      <SheetHeader className="border-b">
        <SheetTitle className="font-display text-2xl font-normal">Call transcript</SheetTitle>
        <SheetDescription>
          {call ? (
            <>
              {when(call.started_at)} · {duration(call.duration_seconds)}
              {call.outcome ? ` · ${call.outcome.replace("_", " ")}` : ""}
              {ttft ? ` · replies in ~${ttft} ms` : ""}
            </>
          ) : (
            "Loading..."
          )}
        </SheetDescription>
      </SheetHeader>
      <div className="flex-1 space-y-3 overflow-y-auto px-4 pb-6">
        {call?.summary && <p className="rounded-xl bg-accent/60 p-3 text-sm">{call.summary}</p>}
        {!call ? (
          <Skeleton className="h-60 rounded-xl" />
        ) : call.transcript.length ? (
          call.transcript.map((t, i) => {
            const agent = t.role === "assistant" || t.role === "agent";
            return (
              <div key={i} className={cn("flex flex-col gap-1", agent ? "items-start" : "items-end")}>
                <span className="text-[0.66rem] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
                  {agent ? "Receptionist" : "Caller"}
                </span>
                <p
                  className={cn(
                    "max-w-[88%] rounded-2xl px-3.5 py-2 text-sm",
                    agent ? "rounded-tl-sm bg-secondary" : "rounded-tr-sm bg-primary text-primary-foreground",
                  )}
                >
                  {t.text}
                </p>
              </div>
            );
          })
        ) : (
          <p className="text-sm text-muted-foreground">No transcript was recorded for this call.</p>
        )}
      </div>
    </>
  );
}
