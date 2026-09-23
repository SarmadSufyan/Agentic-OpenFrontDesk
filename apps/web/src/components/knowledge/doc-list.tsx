"use client";

import { FileTextIcon, GlobeIcon, RefreshCwIcon, Trash2Icon, TypeIcon } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, StatusPill } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { ago, compact } from "@/lib/format";
import { useDocs } from "@/lib/hooks";
import type { KnowledgeDoc } from "@/lib/types";

const ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  text: TypeIcon,
  url: GlobeIcon,
};

export function DocList({ manage = true }: { manage?: boolean }) {
  const { data: docs, isLoading, mutate } = useDocs();

  if (isLoading) {
    return (
      <div className="grid gap-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-14 rounded-xl" />
        ))}
      </div>
    );
  }
  if (!docs?.length) {
    return (
      <EmptyState icon={FileTextIcon} title="No knowledge yet">
        Add your prices, services, hours and FAQs. The receptionist only answers from what you add here.
      </EmptyState>
    );
  }

  async function remove(doc: KnowledgeDoc) {
    if (!window.confirm(`Remove "${doc.title}"? The receptionist will stop using it immediately.`)) return;
    try {
      await api.del(`/knowledge/${doc.id}`);
      toast.success("Removed");
      mutate();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function reindex(doc: KnowledgeDoc) {
    try {
      await api.post(`/knowledge/${doc.id}/reindex`);
      toast.success("Re-indexed");
      mutate();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <ul className="divide-y overflow-hidden rounded-xl border">
      {docs.map((d) => {
        const Icon = ICON[d.source_type] ?? FileTextIcon;
        return (
          <li key={d.id} className="flex items-center gap-3 bg-card px-4 py-3">
            <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-muted text-muted-foreground">
              <Icon className="size-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{d.title}</p>
              <p className="truncate text-xs text-muted-foreground">
                {d.status === "failed" && d.error
                  ? d.error
                  : `${d.source_type.toUpperCase()} · ${compact(d.char_count)} characters · ${d.chunk_count} ${d.chunk_count === 1 ? "passage" : "passages"} · ${ago(d.created_at)}`}
              </p>
            </div>
            <StatusPill status={d.status} />
            {manage && (
              <div className="flex shrink-0">
                {d.status === "ready" && (
                  <Button variant="ghost" size="icon-sm" aria-label={`Re-index ${d.title}`} onClick={() => reindex(d)}>
                    <RefreshCwIcon />
                  </Button>
                )}
                <Button variant="ghost" size="icon-sm" aria-label={`Remove ${d.title}`} onClick={() => remove(d)}>
                  <Trash2Icon />
                </Button>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
