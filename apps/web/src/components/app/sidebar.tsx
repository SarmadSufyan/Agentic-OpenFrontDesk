"use client";

import {
  BookOpenIcon,
  CalendarDaysIcon,
  ChevronsUpDownIcon,
  FlaskConicalIcon,
  InboxIcon,
  LayoutGridIcon,
  LogOutIcon,
  MessageCircleQuestionIcon,
  PhoneCallIcon,
  RocketIcon,
  SettingsIcon,
  ShieldCheckIcon,
  WorkflowIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Wordmark } from "@/components/brand";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

type Item = { href: string; label: string; icon: React.ComponentType<{ className?: string }> };

const GROUPS: { label?: string; items: Item[]; admin?: boolean }[] = [
  { items: [{ href: "/dashboard", label: "Overview", icon: LayoutGridIcon }] },
  {
    label: "Build",
    items: [
      { href: "/dashboard/knowledge", label: "Knowledge", icon: BookOpenIcon },
      { href: "/dashboard/test", label: "Test", icon: FlaskConicalIcon },
      { href: "/dashboard/deploy", label: "Deploy", icon: RocketIcon },
    ],
  },
  {
    label: "Activity",
    items: [
      { href: "/dashboard/conversations", label: "Calls", icon: PhoneCallIcon },
      { href: "/dashboard/leads", label: "Leads", icon: InboxIcon },
      { href: "/dashboard/bookings", label: "Bookings", icon: CalendarDaysIcon },
    ],
  },
  {
    label: "Workspace",
    items: [
      { href: "/dashboard/integrations", label: "Integrations", icon: WorkflowIcon },
      { href: "/dashboard/settings", label: "Settings", icon: SettingsIcon },
    ],
  },
  { label: "Platform", admin: true, items: [{ href: "/dashboard/admin", label: "Admin", icon: ShieldCheckIcon }] },
];

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { me } = useAuth();
  return (
    <nav className="grid gap-6">
      {GROUPS.filter((g) => !g.admin || me?.is_admin).map((g, gi) => (
        <div key={gi} className="grid gap-0.5">
          {g.label && (
            <p className="mb-1 px-3 text-[0.68rem] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
              {g.label}
            </p>
          )}
          {g.items.map((item) => {
            const active = item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                )}
              >
                <item.icon className={cn("size-4", active && "text-primary")} />
                {item.label}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
}

export function AccountMenu() {
  const { me, workspace, logout } = useAuth();
  const router = useRouter();
  const initials = (me?.user.name || me?.user.email || "?")
    .split(/[\s@]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex w-full items-center gap-2.5 rounded-xl border bg-card px-2.5 py-2 text-left outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary text-xs font-semibold text-primary-foreground">
          {initials}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{workspace?.tenant_name}</span>
          <span className="block truncate text-xs text-muted-foreground">{me?.user.email}</span>
        </span>
        <ChevronsUpDownIcon className="size-4 text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent side="top" className="w-56">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Signed in as {workspace?.role}
        </DropdownMenuLabel>
        <DropdownMenuItem onClick={() => router.push("/dashboard/settings")}>
          <SettingsIcon /> Workspace settings
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push("/contact")}>
          <MessageCircleQuestionIcon /> Custom solutions
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          onClick={() => {
            logout();
            router.replace("/login");
          }}
        >
          <LogOutIcon /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-8 p-4">
      <div className="px-1 pt-1">
        <Wordmark href="/dashboard" />
      </div>
      <div className="flex-1 overflow-y-auto">
        <SidebarNav onNavigate={onNavigate} />
      </div>
      <AccountMenu />
    </div>
  );
}
