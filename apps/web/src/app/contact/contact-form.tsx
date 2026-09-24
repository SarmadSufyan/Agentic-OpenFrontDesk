"use client";

import { ArrowRightIcon, CalendarCheckIcon } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";

import { ErrorNote, Field, NativeSelect } from "@/components/kit";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { BUDGET_LABELS } from "@/lib/constants";
import type { ContactAccepted, ContactOptions } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ContactForm() {
  const { data: options } = useSWR<ContactOptions>("/contact/options");
  const { me, workspace } = useAuth();
  const preselect = useSearchParams().get("need");
  const [needs, setNeeds] = useState<string[]>(preselect ? [preselect] : []);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<ContactAccepted | null>(null);

  if (done) {
    return (
      <div className="rounded-3xl border bg-card p-8">
        <div className="grid size-12 place-items-center rounded-2xl bg-accent text-accent-foreground">
          <CalendarCheckIcon className="size-6" />
        </div>
        <h2 className="mt-6 font-display text-4xl leading-tight">Thank you. We will be in touch shortly.</h2>
        <p className="mt-3 text-muted-foreground">
          A confirmation is on its way to your inbox. Someone from our team reads every request personally and
          will reply within one business day to set up a call.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          {done.scheduling_url && (
            <a href={done.scheduling_url} target="_blank" rel="noopener noreferrer" className={cn(buttonVariants({ size: "lg" }), "h-10 px-5")}>
              Pick a time now <ArrowRightIcon />
            </a>
          )}
          <Link href="/" className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-10 px-5")}>
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form
      key={me?.user.id ?? "anon"}
      className="grid gap-5 rounded-3xl border bg-card p-6 sm:p-8"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const v = (k: string) => String(f.get(k) ?? "").trim();
        if (v("message").length < 10) return setError(new Error("Tell us a little more about your goal (at least 10 characters)."));
        setBusy(true);
        setError(null);
        try {
          setDone(
            await api.post<ContactAccepted>("/contact", {
              name: v("name"),
              email: v("email"),
              company: v("company") || null,
              website: v("website") || null,
              phone: v("phone") || null,
              team_size: v("team_size") || null,
              budget: v("budget") || null,
              needs,
              message: v("message"),
              company_fax: v("company_fax") || null,
              source: me ? "dashboard" : "contact_page",
            }),
          );
          window.scrollTo({ top: 0, behavior: "smooth" });
        } catch (err) {
          setError(err);
        } finally {
          setBusy(false);
        }
      }}
    >
      <div>
        <h2 className="font-display text-3xl">Tell us about your project</h2>
        <p className="mt-1 text-sm text-muted-foreground">Two minutes, no commitment.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Your name" htmlFor="c-name">
          <Input id="c-name" name="name" required maxLength={200} autoComplete="name" defaultValue={me?.user.name ?? ""} />
        </Field>
        <Field label="Work email" htmlFor="c-email">
          <Input id="c-email" name="email" type="email" required autoComplete="email" defaultValue={me?.user.email ?? ""} />
        </Field>
        <Field label="Company" htmlFor="c-company">
          <Input id="c-company" name="company" maxLength={200} autoComplete="organization" defaultValue={workspace?.tenant_name ?? ""} />
        </Field>
        <Field label="Website" htmlFor="c-website">
          <Input id="c-website" name="website" maxLength={300} placeholder="https://" />
        </Field>
        <Field label="Phone or WhatsApp" htmlFor="c-phone">
          <Input id="c-phone" name="phone" maxLength={40} autoComplete="tel" />
        </Field>
        <Field label="Team size" htmlFor="c-team">
          <NativeSelect id="c-team" name="team_size" defaultValue="">
            <option value="">Select</option>
            {options?.team_sizes.map((t) => (
              <option key={t} value={t}>
                {t} people
              </option>
            ))}
          </NativeSelect>
        </Field>
      </div>
      <fieldset>
        <legend className="mb-2 text-sm font-medium">What would you like to build?</legend>
        <div className="flex flex-wrap gap-2">
          {options &&
            Object.entries(options.needs).map(([k, label]) => {
              const on = needs.includes(k);
              return (
                <button
                  key={k}
                  type="button"
                  aria-pressed={on}
                  onClick={() => setNeeds((cur) => (on ? cur.filter((n) => n !== k) : [...cur, k]))}
                  className={cn(
                    "rounded-full border px-3.5 py-1.5 text-sm transition-colors",
                    on ? "border-primary bg-accent font-medium text-accent-foreground" : "hover:border-primary/50",
                  )}
                >
                  {label}
                </button>
              );
            })}
        </div>
      </fieldset>
      <Field label="Budget range" htmlFor="c-budget">
        <NativeSelect id="c-budget" name="budget" defaultValue="">
          <option value="">Select</option>
          {options?.budgets.map((b) => (
            <option key={b} value={b}>
              {BUDGET_LABELS[b] ?? b}
            </option>
          ))}
        </NativeSelect>
      </Field>
      <Field label="Describe your goal" htmlFor="c-message">
        <Textarea
          id="c-message"
          name="message"
          rows={5}
          required
          minLength={10}
          maxLength={5000}
          placeholder="For example: we get about 80 WhatsApp messages a day about prices and availability, and want an assistant that answers and books into Google Calendar."
        />
      </Field>
      {/* Honeypot: hidden from people, tempting to bots. */}
      <div aria-hidden className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label htmlFor="c-fax">Leave this field empty</label>
        <input id="c-fax" name="company_fax" tabIndex={-1} autoComplete="off" />
      </div>
      <ErrorNote error={error} />
      <Button type="submit" size="lg" className="h-11" disabled={busy}>
        {busy ? "Sending..." : "Send request"}
      </Button>
      <p className="text-xs text-muted-foreground">
        We use your details only to reply to this request, and delete them on request.
      </p>
    </form>
  );
}
