"use client";

import Link from "next/link";

import { Wordmark } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/#how", label: "How it works" },
  { href: "/#product", label: "Product" },
  { href: "/#open-source", label: "Open source" },
  { href: "/contact", label: "Custom solutions" },
];

export function SiteHeader() {
  const { status } = useAuth();
  return (
    <header className="sticky top-0 z-40 border-b border-transparent bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/65">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <Wordmark />
        <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="transition-colors hover:text-foreground">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-1.5">
          <ThemeToggle />
          {status === "authed" ? (
            <Link href="/dashboard" className={cn(buttonVariants({ size: "lg" }), "px-4")}>
              Open dashboard
            </Link>
          ) : (
            <>
              <Link href="/login" className={cn(buttonVariants({ variant: "ghost", size: "lg" }), "hidden sm:inline-flex")}>
                Sign in
              </Link>
              <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "px-4")}>
                Start free
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
