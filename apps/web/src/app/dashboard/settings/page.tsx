"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useSWRConfig } from "swr";

import { ErrorNote, Field, NativeSelect, PageHeader, Panel } from "@/components/kit";
import { HoursEditor, timezones } from "@/components/settings/hours-editor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TONES, VERTICALS, VOICES } from "@/lib/constants";
import { useAgent, useTenant } from "@/lib/hooks";
import type { Agent, BusinessHours, Tenant } from "@/lib/types";

export default function SettingsPage() {
  const { data: tenant } = useTenant();
  const { data: agent } = useAgent();
  const { workspace } = useAuth();
  const canEdit = workspace?.role === "owner" || workspace?.role === "admin";

  return (
    <>
      <PageHeader eyebrow="Workspace" title="Settings" description="How your business works and how your receptionist sounds." />
      {!canEdit && <p className="mb-6 text-sm text-muted-foreground">Only owners and admins can change settings.</p>}
      <div className="grid gap-6 lg:grid-cols-2">
        {tenant ? <BusinessForm key={tenant.id} tenant={tenant} disabled={!canEdit} /> : <Skeleton className="h-[520px] rounded-2xl" />}
        {agent ? <AgentForm key={agent.id} agent={agent} disabled={!canEdit} /> : <Skeleton className="h-[520px] rounded-2xl" />}
      </div>
    </>
  );
}

function BusinessForm({ tenant, disabled }: { tenant: Tenant; disabled: boolean }) {
  const { mutate } = useSWRConfig();
  const { refreshMe } = useAuth();
  const [hours, setHours] = useState<BusinessHours>(tenant.business_hours ?? {});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <Panel title="Business" description="Your receptionist uses these to answer questions and to offer valid appointment times.">
      <form
        className="grid gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setBusy(true);
          setError(null);
          try {
            const updated = await api.patch<Tenant>("/tenants/current", {
              name: String(f.get("name")).trim(),
              vertical: String(f.get("vertical")) || null,
              timezone: String(f.get("timezone")),
              business_hours: hours,
            });
            await mutate("/tenants/current", updated, { revalidate: false });
            refreshMe();
            toast.success("Business settings saved");
          } catch (err) {
            setError(err);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Field label="Business name" htmlFor="b-name">
          <Input id="b-name" name="name" defaultValue={tenant.name} required disabled={disabled} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Type of business" htmlFor="b-vertical">
            <NativeSelect id="b-vertical" name="vertical" defaultValue={tenant.vertical ?? ""} disabled={disabled}>
              <option value="">Choose one</option>
              {VERTICALS.map((v) => (
                <option key={v.value} value={v.value}>
                  {v.label}
                </option>
              ))}
            </NativeSelect>
          </Field>
          <Field label="Time zone" htmlFor="b-tz">
            <NativeSelect id="b-tz" name="timezone" defaultValue={tenant.timezone} disabled={disabled}>
              {timezones().map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </NativeSelect>
          </Field>
        </div>
        <Field label="Opening hours">
          <HoursEditor value={hours} onChange={setHours} />
        </Field>
        <ErrorNote error={error} />
        <div>
          <Button type="submit" disabled={busy || disabled}>
            {busy ? "Saving..." : "Save business settings"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function AgentForm({ agent, disabled }: { agent: Agent; disabled: boolean }) {
  const { mutate } = useSWRConfig();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const services = agent.booking_rules?.services ?? [];

  return (
    <Panel title="Receptionist" description="Voice, tone and greeting apply to phone and chat.">
      <form
        className="grid gap-4"
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          setBusy(true);
          setError(null);
          try {
            const updated = await api.put<Agent>("/agents/current", {
              name: String(f.get("name")).trim(),
              voice: String(f.get("voice")),
              tone: String(f.get("tone")),
              greeting: String(f.get("greeting")).trim(),
              booking_rules: {
                ...agent.booking_rules,
                slot_minutes: Number(f.get("slot")),
                services: String(f.get("services"))
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              },
            });
            await mutate("/agents/current", updated, { revalidate: false });
            toast.success("Receptionist saved");
          } catch (err) {
            setError(err);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" htmlFor="a-name">
            <Input id="a-name" name="name" defaultValue={agent.name} required disabled={disabled} />
          </Field>
          <Field label="Voice" htmlFor="a-voice">
            <NativeSelect id="a-voice" name="voice" defaultValue={agent.voice} disabled={disabled}>
              {!VOICES.some((v) => v.value === agent.voice) && <option value={agent.voice}>{agent.voice}</option>}
              {VOICES.map((v) => (
                <option key={v.value} value={v.value}>
                  {v.label}
                </option>
              ))}
            </NativeSelect>
          </Field>
        </div>
        <Field label="Tone" htmlFor="a-tone">
          <NativeSelect id="a-tone" name="tone" defaultValue={agent.tone} disabled={disabled}>
            {!TONES.some((t) => t.value === agent.tone) && <option value={agent.tone}>{agent.tone}</option>}
            {TONES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}: {t.hint}
              </option>
            ))}
          </NativeSelect>
        </Field>
        <Field label="Greeting" htmlFor="a-greeting" hint="The first thing callers and visitors hear.">
          <Textarea id="a-greeting" name="greeting" rows={3} defaultValue={agent.greeting} required disabled={disabled} />
        </Field>
        <Field label="Services it can book" htmlFor="a-services" hint="Comma separated, e.g. Cleaning, Whitening, Check-up.">
          <Input id="a-services" name="services" defaultValue={services.join(", ")} disabled={disabled} />
        </Field>
        <Field label="Appointment length" htmlFor="a-slot">
          <NativeSelect id="a-slot" name="slot" defaultValue={String(agent.booking_rules?.slot_minutes ?? 30)} disabled={disabled}>
            {[15, 20, 30, 45, 60, 90].map((m) => (
              <option key={m} value={m}>
                {m} minutes
              </option>
            ))}
          </NativeSelect>
        </Field>
        <ErrorNote error={error} />
        <div>
          <Button type="submit" disabled={busy || disabled}>
            {busy ? "Saving..." : "Save receptionist"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
