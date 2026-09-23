"use client";

import { useEffect, useReducer, useSyncExternalStore } from "react";

import { cn } from "@/lib/utils";

type Step =
  | { kind: "caller" | "agent"; text: string }
  | { kind: "tool"; name: string; detail: string }
  | { kind: "event"; text: string };

const SCRIPT: Step[] = [
  { kind: "caller", text: "Hi, do you have anything open Tuesday morning for a cleaning?" },
  { kind: "tool", name: "check_availability", detail: "Tue 10:30 · 11:00" },
  {
    kind: "agent",
    text: "We do. Tuesday at 10:30 or 11:00, and a routine cleaning is $90. Which suits you?",
  },
  { kind: "caller", text: "10:30 please. It's Maya Chen." },
  { kind: "tool", name: "book_appointment", detail: "Tue 10:30 · Maya Chen" },
  { kind: "agent", text: "You're booked for Tuesday at 10:30, Maya. See you then!" },
  { kind: "event", text: "booking.created → Google Sheets, Slack" },
];

type State = { step: number; chars: number; seconds: number };
type Action = { type: "type" } | { type: "next" } | { type: "reset" } | { type: "tick" };

function reducer(s: State, a: Action): State {
  switch (a.type) {
    case "type":
      return { ...s, chars: s.chars + 2 };
    case "next":
      return { ...s, step: s.step + 1, chars: 0 };
    case "reset":
      return { step: 0, chars: 0, seconds: 0 };
    case "tick":
      return { ...s, seconds: s.seconds + 1 };
  }
}

function subscribeMotion(cb: () => void) {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

const BARS = Array.from({ length: 34 }, (_, i) => ({
  delay: ((i * 137) % 100) / 100,
  height: 30 + ((i * 53) % 70),
}));

export function HeroCall() {
  const reduced = useSyncExternalStore(
    subscribeMotion,
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => false,
  );
  const [state, dispatch] = useReducer(reducer, { step: 0, chars: 0, seconds: 14 });

  // One timer drives the whole script: type the current line, pause, advance, loop.
  useEffect(() => {
    if (reduced) return;
    const cur = SCRIPT[state.step];
    let delay: number;
    let action: Action;
    if (!cur) {
      delay = 3800;
      action = { type: "reset" };
    } else if ((cur.kind === "caller" || cur.kind === "agent") && state.chars < cur.text.length) {
      delay = cur.kind === "agent" ? 26 : 34;
      action = { type: "type" };
    } else {
      delay = cur.kind === "tool" ? 900 : cur.kind === "event" ? 1400 : 700;
      action = { type: "next" };
    }
    const t = setTimeout(() => dispatch(action), delay);
    return () => clearTimeout(t);
  }, [state.step, state.chars, reduced]);

  useEffect(() => {
    if (reduced) return;
    const t = setInterval(() => dispatch({ type: "tick" }), 1000);
    return () => clearInterval(t);
  }, [reduced]);

  const visible = reduced ? SCRIPT : SCRIPT.slice(0, state.step + 1);
  const current = SCRIPT[state.step];
  const speaking = !reduced && current && (current.kind === "caller" || current.kind === "agent") ? current.kind : null;
  const mm = String(Math.floor(state.seconds / 60)).padStart(2, "0");
  const ss = String(state.seconds % 60).padStart(2, "0");

  return (
    <div className="relative">
      <div aria-hidden className="absolute -inset-6 -z-10 rounded-[2.5rem] bg-primary/10 blur-2xl" />
      <div
        className="overflow-hidden rounded-[1.6rem] border bg-card shadow-[0_30px_80px_-30px_color-mix(in_oklch,var(--foreground)_35%,transparent)]"
        role="img"
        aria-label="Example of the AI receptionist answering a call, checking availability and booking an appointment"
      >
        <div className="flex items-center gap-3 border-b px-5 py-3.5">
          <span className="live-dot size-2.5 rounded-full bg-signal" />
          <span className="text-sm font-semibold">Live call</span>
          <span className="truncate text-sm text-muted-foreground">Bright Smile Dental</span>
          <span className="ml-auto font-mono text-xs text-muted-foreground tabular-nums">
            {mm}:{ss}
          </span>
        </div>

        <div className="flex h-14 items-center justify-center gap-[3px] border-b bg-muted/40 px-5" aria-hidden>
          {BARS.map((b, i) => (
            <span
              key={i}
              className={cn(
                "wave-bar w-[3px] rounded-full transition-colors duration-500",
                speaking === "agent" ? "bg-primary" : speaking === "caller" ? "bg-foreground/45" : "bg-foreground/15",
              )}
              style={{
                height: `${b.height}%`,
                animationDelay: `${b.delay}s`,
                animationPlayState: speaking ? "running" : "paused",
              }}
            />
          ))}
        </div>

        <div className="relative h-[340px] overflow-hidden px-5">
          <div className="pointer-events-none absolute inset-x-0 top-0 z-10 h-12 bg-gradient-to-b from-card to-transparent" />
          <div className="flex h-full flex-col justify-end gap-3 pb-5">
            {visible.map((s, i) => {
              const isCurrent = !reduced && i === state.step;
              if (s.kind === "tool" || s.kind === "event") {
                return (
                  <div key={i} className="rise flex" style={{ animationDuration: "0.45s" }}>
                    <span
                      className={cn(
                        "inline-flex max-w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 font-mono text-[0.72rem]",
                        s.kind === "event" ? "border-signal/30 bg-signal/10 text-signal" : "bg-muted/70 text-muted-foreground",
                      )}
                    >
                      {s.kind === "tool" ? (
                        <>
                          <span className="text-primary">{s.name}</span>
                          <span className="truncate">→ {s.detail}</span>
                        </>
                      ) : (
                        <span className="truncate">webhook · {s.text}</span>
                      )}
                    </span>
                  </div>
                );
              }
              const text = isCurrent ? s.text.slice(0, state.chars) : s.text;
              const agent = s.kind === "agent";
              return (
                <div key={i} className={cn("flex flex-col gap-1", agent ? "items-start" : "items-end")}>
                  <span className="text-[0.68rem] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
                    {agent ? "Receptionist" : "Caller"}
                  </span>
                  <p
                    className={cn(
                      "max-w-[88%] rounded-2xl px-3.5 py-2 text-[0.92rem] leading-snug",
                      agent ? "rounded-tl-sm bg-primary text-primary-foreground" : "rounded-tr-sm bg-secondary",
                      isCurrent && text.length < s.text.length && "caret",
                    )}
                  >
                    {text}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
