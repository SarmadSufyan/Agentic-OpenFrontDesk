import Link from "next/link";

import { cn } from "@/lib/utils";

/** The mark: a reception desk bell on an evergreen tile. */
export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden className={cn("size-7 shrink-0", className)}>
      <rect width="32" height="32" rx="9" className="fill-primary" />
      <path
        d="M9.5 21.5h13M11 20a5 5 0 0 1 10 0"
        className="stroke-primary-foreground"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="16" cy="12.4" r="1.5" className="fill-primary-foreground" />
    </svg>
  );
}

export function Wordmark({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={cn("flex items-center gap-2.5 outline-none", className)}>
      <Mark />
      <span className="font-display text-[1.45rem] leading-none tracking-tight">
        Open<span className="italic">Front</span>Desk
      </span>
    </Link>
  );
}
