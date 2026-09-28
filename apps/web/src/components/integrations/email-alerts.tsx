"use client";

import { MailIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import useSWR from "swr";

import { ErrorNote, Field, Panel } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AlertSettings } from "@/lib/types";

/** "Email me every new lead / booking / call summary", with no automation tool needed. */
export function EmailAlerts() {
  const { data, mutate } = useSWR<AlertSettings>("/integrations/alerts");
  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <MailIcon className="size-4 text-primary" /> Email alerts
        </span>
      }
      description="Get an email the moment something happens. No other tools needed."
    >
      {data ? <AlertsForm key={JSON.stringify([data.emails, data.events])} data={data} onSaved={mutate} /> : <Skeleton className="h-40 rounded-xl" />}
    </Panel>
  );
}

function AlertsForm({ data, onSaved }: { data: AlertSettings; onSaved: (d: AlertSettings) => void }) {
  const { me } = useAuth();
  const [emails, setEmails] = useState(data.emails.length ? data.emails.join(", ") : me?.user.email ?? "");
  const [events, setEvents] = useState<string[]>(data.events);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<"save" | "test" | null>(null);
  const saved = data.emails.length > 0 && data.events.length > 0;

  const recipients = () =>
    emails
      .split(/[,;\s]+/)
      .map((e) => e.trim())
      .filter(Boolean);

  async function save() {
    setBusy("save");
    setError(null);
    try {
      const out = await api.put<AlertSettings>("/integrations/alerts", { emails: recipients(), events });
      onSaved(out);
      toast.success(out.events.length ? "Email alerts saved" : "Email alerts turned off");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  async function test() {
    setBusy("test");
    setError(null);
    try {
      const r = await api.post<{ sent: boolean; recipients: string[] }>("/integrations/alerts/test");
      if (r.sent) toast.success(`Test email sent to ${r.recipients.join(", ")}`);
      else toast.error("The test email could not be sent. Check the server's email settings.");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="grid gap-4">
      {!data.email_available && (
        <p className="rounded-lg border border-signal/30 bg-signal/8 px-3 py-2 text-sm">
          Email sending is not set up on this server yet, so alerts cannot go out. Your choices are saved and
          start working as soon as the operator configures email (SMTP).
        </p>
      )}
      <Field label="Send alerts to" htmlFor="alert-emails" hint="Up to 5 addresses, separated by commas.">
        <Input id="alert-emails" value={emails} onChange={(e) => setEmails(e.target.value)} placeholder="you@business.com" />
      </Field>
      <fieldset className="grid gap-2.5">
        <legend className="mb-1 text-sm font-medium">Email me about</legend>
        {data.catalog.map((c) => (
          <label key={c.type} className="flex items-center gap-2.5 text-sm">
            <Checkbox
              checked={events.includes(c.type)}
              onCheckedChange={(on) => setEvents((cur) => (on ? [...cur, c.type] : cur.filter((x) => x !== c.type)))}
            />
            {c.label}
          </label>
        ))}
      </fieldset>
      <ErrorNote error={error} />
      <div className="flex flex-wrap gap-2">
        <Button onClick={save} disabled={busy !== null}>
          {busy === "save" ? "Saving..." : "Save alerts"}
        </Button>
        <Button variant="outline" onClick={test} disabled={busy !== null || !saved || !data.email_available}>
          {busy === "test" ? "Sending..." : "Send a test email"}
        </Button>
      </div>
    </div>
  );
}
