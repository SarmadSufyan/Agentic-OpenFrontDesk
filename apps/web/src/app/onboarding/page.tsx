"use client";

import { ArrowLeftIcon, ArrowRightIcon, CheckIcon } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useSWRConfig } from "swr";

import { Wordmark } from "@/components/brand";
import { CodeBlock, ErrorNote, Field, NativeSelect } from "@/components/kit";
import { AddKnowledge } from "@/components/knowledge/add-knowledge";
import { DocList } from "@/components/knowledge/doc-list";
import { HoursEditor, timezones } from "@/components/settings/hours-editor";
import { ChatPanel } from "@/components/test/chat-panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { API_URL, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TONES, VERTICALS, VOICES } from "@/lib/constants";
import { useAgent, useDocs, useSaveSettings, useTenant } from "@/lib/hooks";
import type { Agent, BusinessHours, Tenant } from "@/lib/types";
import { cn } from "@/lib/utils";

const STEPS = ["Your business", "Your receptionist", "What it knows", "Try it", "Go live"];

export default function OnboardingPage() {
  return (
    <Suspense>
      <Onboarding />
    </Suspense>
  );
}

function Onboarding() {
  const { status } = useAuth();
  const router = useRouter();
  const { data: tenant } = useTenant();
  const { data: agent } = useAgent();
  // The step lives in the URL, so a refresh (or the browser back button) keeps your place.
  const raw = Number(useSearchParams().get("step"));
  const step = Number.isInteger(raw) && raw >= 0 && raw < STEPS.length ? raw : 0;
  const setStep = (n: number) => router.push(`/onboarding?step=${n}`, { scroll: true });

  useEffect(() => {
    if (status === "anon") router.replace("/login?next=/onboarding");
  }, [status, router]);

  const ready = status === "authed" && tenant && agent;

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[320px_1fr]">
      <aside className="grain relative border-b bg-sidebar px-6 py-6 lg:min-h-screen lg:border-r lg:border-b-0 lg:px-8 lg:py-8">
        <Wordmark href="/dashboard" />
        <ol className="mt-8 flex gap-2 overflow-x-auto lg:mt-14 lg:grid lg:gap-1">
          {STEPS.map((s, i) => (
            <li key={s} className="shrink-0">
              <div
                className={cn(
                  "flex items-center gap-3 rounded-lg px-2 py-2 text-sm",
                  i === step ? "font-medium text-foreground" : "text-muted-foreground",
                )}
              >
                <span
                  className={cn(
                    "grid size-7 shrink-0 place-items-center rounded-full border text-xs font-semibold",
                    i < step && "border-primary bg-primary text-primary-foreground",
                    i === step && "border-primary text-primary",
                  )}
                >
                  {i < step ? <CheckIcon className="size-3.5" /> : i + 1}
                </span>
                <span className="hidden sm:inline">{s}</span>
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-10 hidden text-sm text-muted-foreground lg:block">
          Takes about five minutes. You can change everything later in Settings.
        </p>
      </aside>

      <main className="px-5 py-10 sm:px-10 lg:px-16 lg:py-16">
        <div className="mx-auto max-w-2xl">
          {!ready ? (
            <Skeleton className="h-[480px] rounded-2xl" />
          ) : step === 0 ? (
            <BusinessStep tenant={tenant} onNext={() => setStep(1)} />
          ) : step === 1 ? (
            <AgentStep agent={agent} onBack={() => setStep(0)} onNext={() => setStep(2)} />
          ) : step === 2 ? (
            <KnowledgeStep onBack={() => setStep(1)} onNext={() => setStep(3)} />
          ) : step === 3 ? (
            <TestStep slug={tenant.slug} greeting={agent.greeting} onBack={() => setStep(2)} onNext={() => setStep(4)} />
          ) : (
            <LiveStep slug={tenant.slug} />
          )}
        </div>
      </main>
    </div>
  );
}

function StepTitle({ n, title, children }: { n: number; title: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <p className="text-xs font-semibold tracking-[0.14em] text-primary uppercase">
        Step {n} of {STEPS.length}
      </p>
      <h1 className="mt-2 font-display text-[2.6rem] leading-[1.04]">{title}</h1>
      <p className="mt-2 text-muted-foreground">{children}</p>
    </div>
  );
}

/** Step footer. With `onNext` the button is a plain button (for steps that contain their own forms,
 * since forms cannot be nested); without it, it submits the step's form. */
function Nav({
  onBack,
  onNext,
  next,
  busy,
}: {
  onBack?: () => void;
  onNext?: () => void;
  next: React.ReactNode;
  busy?: boolean;
}) {
  return (
    <div className="mt-8 flex items-center justify-between gap-3 border-t pt-6">
      {onBack ? (
        <Button type="button" variant="ghost" onClick={onBack}>
          <ArrowLeftIcon /> Back
        </Button>
      ) : (
        <span />
      )}
      <Button type={onNext ? "button" : "submit"} onClick={onNext} size="lg" className="h-10 px-5" disabled={busy}>
        {next} <ArrowRightIcon />
      </Button>
    </div>
  );
}

function BusinessStep({ tenant, onNext }: { tenant: Tenant; onNext: () => void }) {
  const { mutate } = useSWRConfig();
  const { refreshMe } = useAuth();
  const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  const [hours, setHours] = useState<BusinessHours>(tenant.business_hours ?? {});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <form
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
          onNext();
        } catch (err) {
          setError(err);
        } finally {
          setBusy(false);
        }
      }}
    >
      <StepTitle n={1} title={<>Tell us about <span className="italic">your business</span></>}>
        Your receptionist uses this to greet people and to only offer appointments when you are open.
      </StepTitle>
      <div className="grid gap-5">
        <Field label="Business name" htmlFor="o-name">
          <Input id="o-name" name="name" defaultValue={tenant.name} required className="h-10" />
        </Field>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Type of business" htmlFor="o-vertical">
            <NativeSelect id="o-vertical" name="vertical" defaultValue={tenant.vertical ?? ""} className="h-10">
              <option value="">Choose one</option>
              {VERTICALS.map((v) => (
                <option key={v.value} value={v.value}>
                  {v.label}
                </option>
              ))}
            </NativeSelect>
          </Field>
          <Field label="Time zone" htmlFor="o-tz">
            <NativeSelect
              id="o-tz"
              name="timezone"
              defaultValue={tenant.timezone === "UTC" && browserTz ? browserTz : tenant.timezone}
              className="h-10"
            >
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
      </div>
      <Nav next="Continue" busy={busy} />
    </form>
  );
}

function AgentStep({ agent, onBack, onNext }: { agent: Agent; onBack: () => void; onNext: () => void }) {
  const { mutate } = useSWRConfig();
  const [tone, setTone] = useState(TONES.some((t) => t.value === agent.tone) ? agent.tone : TONES[0].value);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        setBusy(true);
        setError(null);
        try {
          const updated = await api.put<Agent>("/agents/current", {
            name: String(f.get("name")).trim(),
            voice: String(f.get("voice")),
            greeting: String(f.get("greeting")).trim(),
            tone,
          });
          await mutate("/agents/current", updated, { revalidate: false });
          onNext();
        } catch (err) {
          setError(err);
        } finally {
          setBusy(false);
        }
      }}
    >
      <StepTitle n={2} title={<>Shape <span className="italic">your receptionist</span></>}>
        Pick how it sounds. The same personality answers the phone and the website chat.
      </StepTitle>
      <div className="grid gap-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Name" htmlFor="o-aname">
            <Input id="o-aname" name="name" defaultValue={agent.name} required className="h-10" />
          </Field>
          <Field label="Voice" htmlFor="o-voice">
            <NativeSelect id="o-voice" name="voice" defaultValue={agent.voice} className="h-10">
              {VOICES.map((v) => (
                <option key={v.value} value={v.value}>
                  {v.label}
                </option>
              ))}
            </NativeSelect>
          </Field>
        </div>
        <fieldset>
          <legend className="mb-2 text-sm font-medium">Tone</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {TONES.map((t) => (
              <label
                key={t.value}
                className={cn(
                  "cursor-pointer rounded-xl border p-3.5 transition-colors",
                  tone === t.value ? "border-primary bg-accent/60" : "hover:border-primary/40",
                )}
              >
                <input
                  type="radio"
                  name="tone"
                  value={t.value}
                  checked={tone === t.value}
                  onChange={() => setTone(t.value)}
                  className="sr-only"
                />
                <span className="block text-sm font-medium">{t.label}</span>
                <span className="block text-xs text-muted-foreground">{t.hint}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <Field label="Greeting" htmlFor="o-greeting" hint="The first sentence callers and visitors hear.">
          <Textarea id="o-greeting" name="greeting" rows={3} defaultValue={agent.greeting} required />
        </Field>
        <ErrorNote error={error} />
      </div>
      <Nav onBack={onBack} next="Continue" busy={busy} />
    </form>
  );
}

function KnowledgeStep({ onBack, onNext }: { onBack: () => void; onNext: () => void }) {
  const { data: docs } = useDocs();
  return (
    <div>
      <StepTitle n={3} title={<>Teach it <span className="italic">what you know</span></>}>
        Add your prices, services, policies and FAQs. It answers only from these, so the more you add, the better it
        gets.
      </StepTitle>
      <div className="rounded-2xl border bg-card p-5">
        <AddKnowledge compact />
      </div>
      <div className="mt-5">
        <DocList manage={false} />
      </div>
      <Nav onBack={onBack} onNext={onNext} next={docs?.length ? "Continue" : "Skip for now"} />
    </div>
  );
}

function TestStep({ slug, greeting, onBack, onNext }: { slug: string; greeting: string; onBack: () => void; onNext: () => void }) {
  const save = useSaveSettings();
  return (
    <div>
      <StepTitle n={4} title={<>Ask it <span className="italic">anything</span></>}>
        Chat as if you were a customer. Voice testing is in the dashboard once you finish.
      </StepTitle>
      <ChatPanel slug={slug} greeting={greeting} className="h-[460px]" />
      <Nav
        onBack={onBack}
        onNext={() => {
          save({ tested_at: new Date().toISOString() }).catch(() => undefined);
          onNext();
        }}
        next="Looks good"
      />
    </div>
  );
}

function LiveStep({ slug }: { slug: string }) {
  const router = useRouter();
  const save = useSaveSettings();
  const [busy, setBusy] = useState(false);
  const snippet = `<script src="${API_URL}/widget.js"\n        data-agent="${slug}"></script>`;
  return (
    <div>
      <StepTitle n={5} title={<>You are <span className="italic">live</span></>}>
        Add this line to your website to put the receptionist in a chat bubble. You can change its color on the Deploy
        page.
      </StepTitle>
      <CodeBlock code={snippet} />
      <ul className="mt-6 grid gap-2 text-sm text-muted-foreground">
        <li>Leads and bookings appear in your dashboard as they happen.</li>
        <li>Connect Sheets, Slack, a CRM or WhatsApp from Integrations.</li>
        <li>Test the voice receptionist from the Test page.</li>
      </ul>
      <div className="mt-8 border-t pt-6">
        <Button
          size="lg"
          className="h-10 px-5"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            await save({ onboarded: true }).catch(() => undefined);
            router.push("/dashboard");
          }}
        >
          Go to my dashboard <ArrowRightIcon />
        </Button>
      </div>
    </div>
  );
}
