import type { Metadata } from "next";
import { Suspense } from "react";

import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";

import { ContactForm } from "./contact-form";

export const metadata: Metadata = {
  title: "Custom solutions",
  description:
    "WhatsApp assistants, HR helpdesk bots, CRM integrations and workflow automations built around your business.",
};

const OFFERS = [
  ["WhatsApp assistant", "Answers customers on WhatsApp from your knowledge base, books appointments, and hands off to your team."],
  ["HR and internal helpdesk", "Answers staff questions from your policies, handbooks and onboarding documents."],
  ["Chatbot and voice receptionist", "Trained on your services and prices, capturing leads around the clock."],
  ["Workflow automation", "Leads, calls and bookings flowing into your CRM, sheets, email and chat, on your own accounts."],
];

export default function ContactPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <section className="grain relative">
        <div className="mx-auto grid max-w-6xl gap-14 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:py-24">
          <div>
            <p className="text-xs font-semibold tracking-[0.14em] text-primary uppercase">Custom solutions</p>
            <h1 className="mt-3 font-display text-5xl leading-[1.02] sm:text-6xl">
              Built around how your business <span className="italic">actually</span> works.
            </h1>
            <p className="mt-5 max-w-lg text-lg text-muted-foreground">
              OpenFrontDesk is free and self-serve. When you need more, tell us what you have in mind and we will
              personally set up a call to plan it with you.
            </p>
            <dl className="mt-10 grid gap-6">
              {OFFERS.map(([t, d]) => (
                <div key={t} className="border-l-2 border-primary/40 pl-4">
                  <dt className="font-semibold">{t}</dt>
                  <dd className="mt-1 text-sm text-muted-foreground">{d}</dd>
                </div>
              ))}
            </dl>
            <ol className="mt-10 grid gap-3 text-sm text-muted-foreground">
              <li>
                <span className="font-display text-xl text-foreground">1.</span> Tell us what you need.
              </li>
              <li>
                <span className="font-display text-xl text-foreground">2.</span> We reply within one business day to schedule a call.
              </li>
              <li>
                <span className="font-display text-xl text-foreground">3.</span> We build it on your accounts, so you stay in control.
              </li>
            </ol>
          </div>
          <div className="relative">
            <Suspense>
              <ContactForm />
            </Suspense>
          </div>
        </div>
      </section>
      <SiteFooter />
    </div>
  );
}
