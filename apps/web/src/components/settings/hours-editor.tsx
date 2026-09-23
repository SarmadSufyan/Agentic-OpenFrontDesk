"use client";

import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { DAYS, HOURS_PRESETS } from "@/lib/constants";
import type { BusinessHours } from "@/lib/types";

export function HoursEditor({ value, onChange }: { value: BusinessHours; onChange: (v: BusinessHours) => void }) {
  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap gap-2">
        {HOURS_PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() =>
              onChange(Object.fromEntries(DAYS.map((d) => [d.key, p.days.includes(d.key) ? [p.open, p.close] : null])))
            }
            className="rounded-full border px-3 py-1 text-xs transition-colors hover:border-primary hover:text-primary"
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="divide-y overflow-hidden rounded-xl border">
        {DAYS.map((d) => {
          const span = value[d.key];
          const open = Boolean(span);
          return (
            <div key={d.key} className="flex flex-wrap items-center gap-3 bg-card px-3.5 py-2.5">
              <Switch
                checked={open}
                onCheckedChange={(on) => onChange({ ...value, [d.key]: on ? span ?? ["09:00", "17:00"] : null })}
                aria-label={`Open on ${d.label}`}
              />
              <span className="w-24 text-sm">{d.label}</span>
              {open && span ? (
                <div className="flex w-full items-center gap-2 text-sm sm:w-auto">
                  <Input
                    type="time"
                    value={span[0]}
                    onChange={(e) => onChange({ ...value, [d.key]: [e.target.value, span[1]] })}
                    className="h-8 min-w-0 flex-1 sm:w-[8.5rem] sm:flex-none"
                    aria-label={`${d.label} opening time`}
                  />
                  <span className="text-muted-foreground">to</span>
                  <Input
                    type="time"
                    value={span[1]}
                    onChange={(e) => onChange({ ...value, [d.key]: [span[0], e.target.value] })}
                    className="h-8 min-w-0 flex-1 sm:w-[8.5rem] sm:flex-none"
                    aria-label={`${d.label} closing time`}
                  />
                </div>
              ) : (
                <span className="text-sm text-muted-foreground">Closed</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function timezones(): string[] {
  try {
    const zones = Intl.supportedValuesOf("timeZone");
    return zones.includes("UTC") ? zones : ["UTC", ...zones]; // new workspaces default to UTC
  } catch {
    return ["UTC"];
  }
}
