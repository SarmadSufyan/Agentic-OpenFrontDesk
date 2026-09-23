"use client";

// Small, app-specific primitives shared by the dashboard, onboarding and marketing pages.

import { CheckIcon, CopyIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        {eyebrow && (
          <p className="mb-1.5 text-xs font-semibold tracking-[0.14em] text-primary uppercase">{eyebrow}</p>
        )}
        <h1 className="font-display text-4xl leading-[1.05] sm:text-[2.75rem]">{title}</h1>
        {description && <p className="mt-2.5 text-[0.95rem] text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Panel({
  title,
  description,
  actions,
  children,
  className,
}: {
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-2xl border bg-card p-5 sm:p-6", className)}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-semibold">{title}</h2>}
            {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed px-6 py-12 text-center">
      <div className="mb-4 grid size-11 place-items-center rounded-xl bg-accent text-accent-foreground">
        <Icon className="size-5" />
      </div>
      <p className="font-medium">{title}</p>
      {children && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{children}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

const PILL: Record<string, string> = {
  ready: "bg-accent text-accent-foreground",
  confirmed: "bg-accent text-accent-foreground",
  active: "bg-accent text-accent-foreground",
  won: "bg-accent text-accent-foreground",
  answered: "bg-accent text-accent-foreground",
  booked: "bg-accent text-accent-foreground",
  scheduled: "bg-accent text-accent-foreground",
  completed: "bg-accent text-accent-foreground",
  ok: "bg-accent text-accent-foreground",
  new: "bg-signal/15 text-signal",
  live: "bg-signal/15 text-signal",
  pending: "bg-secondary text-muted-foreground",
  processing: "bg-secondary text-muted-foreground",
  contacted: "bg-secondary text-secondary-foreground",
  failed: "bg-destructive/12 text-destructive",
  disabled: "bg-destructive/12 text-destructive",
  revoked: "bg-destructive/12 text-destructive",
  cancelled: "bg-destructive/12 text-destructive",
  lost: "bg-secondary text-muted-foreground",
  spam: "bg-secondary text-muted-foreground",
};

export function StatusPill({ status, className }: { status: string; className?: string }) {
  const busy = status === "pending" || status === "processing";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        PILL[status] ?? "bg-secondary text-secondary-foreground",
        className,
      )}
    >
      {busy && <span className="size-1.5 animate-pulse rounded-full bg-current" />}
      {status}
    </span>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border bg-card px-5 py-4">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{label}</p>
      <p className="mt-1.5 font-display text-[2.4rem] leading-none tabular-nums">{value}</p>
      {hint && <p className="mt-1.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setDone(true);
          setTimeout(() => setDone(false), 1600);
        } catch {
          toast.error("Could not copy. Select the text and copy it manually.");
        }
      }}
    >
      {done ? <CheckIcon /> : <CopyIcon />}
      {done ? "Copied" : label}
    </Button>
  );
}

export function CodeBlock({ code, className }: { code: string; className?: string }) {
  return (
    <div className={cn("group relative rounded-xl border bg-muted/60", className)}>
      <pre className="overflow-x-auto p-4 pr-24 font-mono text-[0.8rem] leading-relaxed whitespace-pre">
        {code}
      </pre>
      <div className="absolute top-2.5 right-2.5">
        <CopyButton value={code} />
      </div>
    </div>
  );
}

export function Field({
  label,
  htmlFor,
  hint,
  children,
  className,
}: {
  label: string;
  htmlFor?: string;
  hint?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

/** Native select styled like the inputs: accessible, mobile-friendly, no portal. */
export function NativeSelect({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      className={cn(
        "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none transition-colors",
        "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50 dark:bg-input/30",
        className,
      )}
      {...props}
    />
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/8 px-3 py-2 text-sm text-destructive">
      {message}
    </p>
  );
}
