import {
  ArrowRightIcon,
  BookOpenCheckIcon,
  CalendarCheckIcon,
  FlaskConicalIcon,
  MessageSquareTextIcon,
  PhoneCallIcon,
  WorkflowIcon,
} from "lucide-react";
import Link from "next/link";

import { HeroCall } from "@/components/marketing/hero-call";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { buttonVariants } from "@/components/ui/button";
import { GITHUB_URL } from "@/lib/constants";
import { cn } from "@/lib/utils";

const STACK = ["LiveKit", "Groq Whisper", "Kokoro TTS", "pgvector", "FastAPI", "n8n"];

const STEPS = [
  {
    title: "Train it on your business",
    body: "Paste your FAQ, upload price lists and policies, or point it at your website. Everything is indexed in seconds.",
  },
  {
    title: "Test it like a customer",
    body: "Chat with it or talk to it right in your browser. Every answer shows which document it came from.",
  },
  {
    title: "Deploy it everywhere",
    body: "Add a chat widget with one line of code, take calls, and send every lead to the tools you already use.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen">
      <SiteHeader />

      {/* Hero */}
      <section className="grain relative overflow-hidden">
        <div aria-hidden className="dot-grid absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_top_right,black,transparent_65%)]" />
        <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-14 pb-20 sm:px-6 md:pt-20 lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:pb-28">
          <div>
            <p className="rise inline-flex items-center gap-2 rounded-full border bg-card/70 px-3 py-1 text-xs font-medium text-muted-foreground">
              <span className="size-1.5 rounded-full bg-primary" />
              Open source · Apache-2.0 · Free to use
            </p>
            <h1
              className="rise mt-6 font-display text-[3.4rem] leading-[0.98] tracking-tight sm:text-7xl lg:text-[5.4rem]"
              style={{ animationDelay: "80ms" }}
            >
              Your front desk,
              <br />
              <span className="italic text-primary">always</span> on.
            </h1>
            <p
              className="rise mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground"
              style={{ animationDelay: "160ms" }}
            >
              Train an AI receptionist on your own documents. It answers calls and website chats, books
              appointments, and captures every lead, then hands the details to your team and your tools.
            </p>
            <div className="rise mt-8 flex flex-wrap gap-3" style={{ animationDelay: "240ms" }}>
              <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-[0.95rem]")}>
                Create your receptionist
                <ArrowRightIcon />
              </Link>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noreferrer"
                className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-11 px-5 text-[0.95rem]")}
              >
                View the source
              </a>
            </div>
            <p className="rise mt-6 text-sm text-muted-foreground" style={{ animationDelay: "320ms" }}>
              No credit card. Use the hosted version or run it on your own server.
            </p>
          </div>
          <div className="rise" style={{ animationDelay: "200ms" }}>
            <HeroCall />
          </div>
        </div>
      </section>

      {/* Stack strip */}
      <section className="rule-top">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-4 py-6 sm:px-6">
          <span className="text-xs font-semibold tracking-[0.14em] text-muted-foreground uppercase">
            Built on open infrastructure
          </span>
          {STACK.map((s) => (
            <span key={s} className="font-mono text-sm text-foreground/70">
              {s}
            </span>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="rule-top scroll-mt-16">
        <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
          <SectionTitle eyebrow="How it works" title={<>From documents to a working receptionist <span className="italic">in minutes</span>.</>} />
          <ol className="mt-14 grid gap-10 md:grid-cols-3 md:gap-8">
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative border-t pt-6">
                <span className="font-display text-6xl leading-none text-primary/80">{String(i + 1).padStart(2, "0")}</span>
                <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-muted-foreground">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Product */}
      <section id="product" className="rule-top scroll-mt-16 bg-muted/35">
        <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
          <SectionTitle eyebrow="Product" title="Everything a front desk does, and a few things it never could." />
          <div className="mt-14 grid gap-4 md:grid-cols-6">
            <Feature className="md:col-span-4" icon={PhoneCallIcon} title="Answers calls like your best receptionist">
              <p>
                Natural turn-taking, a voice you choose, and the manners of your business. It checks the
                calendar, books the slot, takes messages, and passes the upset caller to a human.
              </p>
              <div className="mt-6 grid gap-2 sm:grid-cols-3">
                {[
                  ["9:30", "New patient booked", "confirmed"],
                  ["11:05", "Price question answered", "answered"],
                  ["12:40", "Callback requested", "lead"],
                ].map(([t, label, tag]) => (
                  <div key={t} className="rounded-xl border bg-background/70 px-3 py-2.5">
                    <p className="font-mono text-xs text-muted-foreground">{t}</p>
                    <p className="mt-0.5 text-sm font-medium text-foreground">{label}</p>
                    <p className="mt-1 text-xs text-primary">{tag}</p>
                  </div>
                ))}
              </div>
            </Feature>
            <Feature className="md:col-span-2" icon={BookOpenCheckIcon} title="Grounded, never guessing">
              <p>
                Answers come only from your documents, with the source attached. If it does not know, it takes
                a message instead of inventing one.
              </p>
              <p className="mt-5 inline-flex items-center gap-2 rounded-lg border bg-background/70 px-2.5 py-1.5 font-mono text-xs">
                <span className="text-primary">source</span> Price list 2026.pdf
              </p>
            </Feature>
            <Feature className="md:col-span-3" icon={MessageSquareTextIcon} title="One line adds chat to your website">
              <p>The same trained assistant, as a chat bubble on any site. No plugin, no build step.</p>
              <pre className="mt-5 overflow-x-auto rounded-xl border bg-background/70 p-3.5 font-mono text-[0.75rem] leading-relaxed text-foreground">
{`<script src="https://your-host/widget.js"
        data-agent="bright-smile"></script>`}
              </pre>
            </Feature>
            <Feature className="md:col-span-3" icon={WorkflowIcon} title="Automations, built in">
              <p>
                Signed webhooks and a REST API connect every lead, booking and call to n8n, Zapier, Make, or
                your own code. Ready-made workflows included.
              </p>
              <div className="mt-5 flex flex-wrap gap-2 font-mono text-xs">
                {["lead.created", "booking.created", "call.completed", "knowledge.ready"].map((e) => (
                  <span key={e} className="rounded-md border bg-background/70 px-2 py-1">
                    {e}
                  </span>
                ))}
              </div>
            </Feature>
            <Feature className="md:col-span-2" icon={CalendarCheckIcon} title="Knows your hours">
              <p>Business hours, time zone and appointment length shape every answer and every booking.</p>
            </Feature>
            <Feature className="md:col-span-4" icon={FlaskConicalIcon} title="Tested like software">
              <p>
                A synthetic caller runs scenario suites against the agent: did it book correctly, stay grounded,
                capture the contact, and answer fast enough? The same checks run in CI on every change.
              </p>
            </Feature>
          </div>
        </div>
      </section>

      {/* Open source & fair use */}
      <section id="open-source" className="rule-top scroll-mt-16">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-24 sm:px-6 lg:grid-cols-2">
          <div>
            <SectionTitle eyebrow="Open source" title={<>Free for everyone. <span className="italic">Yours</span> to run.</>} />
            <p className="mt-6 max-w-lg text-muted-foreground">
              OpenFrontDesk is Apache-2.0 licensed. Use the hosted version at no cost, or run the whole stack on
              your own server with Docker and keep every recording and transcript in your hands.
            </p>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }), "mt-8 h-11 px-5")}
            >
              Read the code on GitHub
            </a>
          </div>
          <dl className="grid gap-px overflow-hidden rounded-2xl border bg-border sm:grid-cols-2">
            {[
              ["Unlimited text", "Knowledge, chat widget and the dashboard are free with no caps on accounts."],
              ["Fair voice", "Live voice lines are shared. When every line is busy you join a short, visible queue."],
              ["Any provider", "Swap Groq, Kokoro and Gemini for Deepgram, Cartesia or Claude with one setting."],
              ["Private by design", "Tenant isolation, redacted logs, hashed API keys, and an audit trail."],
            ].map(([t, d]) => (
              <div key={t} className="bg-card p-6">
                <dt className="font-display text-2xl">{t}</dt>
                <dd className="mt-2 text-sm text-muted-foreground">{d}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* Custom solutions */}
      <section className="px-4 pb-24 sm:px-6">
        <div className="grain mx-auto max-w-6xl overflow-hidden rounded-[2rem] bg-primary px-6 py-14 text-primary-foreground sm:px-12 sm:py-16 dark:border dark:border-primary/20 dark:bg-accent dark:text-foreground">
          <div className="grid items-end gap-10 lg:grid-cols-[1.4fr_1fr]">
            <div>
              <p className="text-xs font-semibold tracking-[0.14em] uppercase opacity-80">Custom solutions</p>
              <h2 className="mt-3 font-display text-4xl leading-[1.05] sm:text-5xl">
                Need something built around <span className="italic">your</span> business?
              </h2>
              <p className="mt-4 max-w-xl opacity-85">
                WhatsApp assistants, HR and internal helpdesks, CRM and calendar integrations, and workflows on
                your own n8n or Zapier accounts. Tell us what you need and we will set up a call.
              </p>
            </div>
            <div className="flex flex-col items-start gap-4 lg:items-end">
              <div className="flex flex-wrap gap-2 lg:justify-end">
                {["WhatsApp", "HR helpdesk", "CRM sync", "Custom workflows"].map((c) => (
                  <span key={c} className="rounded-full border border-primary-foreground/25 px-3 py-1 text-sm dark:border-foreground/20">
                    {c}
                  </span>
                ))}
              </div>
              <Link
                href="/contact"
                className={cn(
                  buttonVariants({ size: "lg" }),
                  "h-11 bg-primary-foreground px-5 text-primary hover:bg-primary-foreground/90 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/90",
                )}
              >
                Tell us what you need
                <ArrowRightIcon />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Final call to action */}
      <section className="rule-top">
        <div className="mx-auto max-w-6xl px-4 py-24 text-center sm:px-6">
          <h2 className="mx-auto max-w-3xl font-display text-5xl leading-[1.02] sm:text-6xl">
            Never miss another call. <span className="italic text-primary">Start tonight.</span>
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-muted-foreground">
            Sign up, add what your business knows, and test your receptionist before your coffee is cold.
          </p>
          <Link href="/signup" className={cn(buttonVariants({ size: "lg" }), "mt-8 h-12 px-6 text-base")}>
            Create your receptionist
            <ArrowRightIcon />
          </Link>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: React.ReactNode }) {
  return (
    <div className="max-w-3xl">
      <p className="text-xs font-semibold tracking-[0.14em] text-primary uppercase">{eyebrow}</p>
      <h2 className="mt-3 font-display text-4xl leading-[1.05] sm:text-5xl">{title}</h2>
    </div>
  );
}

function Feature({
  icon: Icon,
  title,
  children,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("min-w-0 rounded-2xl border bg-card p-6 text-sm text-muted-foreground sm:p-7", className)}>
      <div className="mb-5 grid size-10 place-items-center rounded-xl bg-accent text-accent-foreground">
        <Icon className="size-5" />
      </div>
      <h3 className="mb-2 font-display text-[1.7rem] leading-tight text-foreground">{title}</h3>
      {children}
    </div>
  );
}
