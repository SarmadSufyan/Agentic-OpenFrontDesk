"use client";

import { MenuIcon, WifiOffIcon } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Wordmark } from "@/components/brand";
import { SidebarBody } from "@/components/app/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { status, refreshMe } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (status === "anon") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [status, pathname, router]);

  if (status === "error") {
    return (
      <div className="grid min-h-screen place-items-center p-6">
        <div className="max-w-sm text-center">
          <WifiOffIcon className="mx-auto size-8 text-muted-foreground" />
          <h1 className="mt-4 font-display text-3xl">Can&apos;t reach the API</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            The dashboard could not connect to <span className="font-mono">{API_URL}</span>. Check that the
            backend is running, then try again.
          </p>
          <Button className="mt-6" onClick={() => refreshMe()}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  if (status !== "authed") {
    return (
      <div className="flex min-h-screen">
        <div className="hidden w-64 border-r bg-sidebar p-4 lg:block">
          <Skeleton className="h-8 w-40" />
        </div>
        <div className="flex-1 p-10">
          <Skeleton className="h-10 w-72" />
          <Skeleton className="mt-6 h-40 w-full max-w-4xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r bg-sidebar lg:block">
        <SidebarBody />
      </aside>
      <div className="relative flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b bg-background/85 px-4 backdrop-blur lg:hidden">
          <Sheet open={navOpen} onOpenChange={setNavOpen}>
            <SheetTrigger className="grid size-9 place-items-center rounded-lg hover:bg-muted" aria-label="Open navigation">
              <MenuIcon className="size-5" />
            </SheetTrigger>
            <SheetContent side="left" className="w-72 bg-sidebar p-0">
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <SidebarBody onNavigate={() => setNavOpen(false)} />
            </SheetContent>
          </Sheet>
          <Wordmark href="/dashboard" />
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>
        <div className="absolute top-3 right-4 hidden lg:block">
          <ThemeToggle />
        </div>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-8 lg:py-12">{children}</main>
      </div>
    </div>
  );
}
