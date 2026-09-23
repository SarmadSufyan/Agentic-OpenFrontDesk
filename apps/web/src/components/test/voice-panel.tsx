"use client";

import { MicIcon, MicOffIcon, PhoneIcon, PhoneOffIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { useVoiceSession } from "./use-voice-session";

const BARS = Array.from({ length: 22 }, (_, i) => ({ delay: ((i * 37) % 100) / 100, height: 35 + ((i * 29) % 65) }));

const LABEL: Record<string, string> = {
  idle: "Ready when you are",
  requesting: "Finding a free line...",
  queued: "All lines are busy",
  connecting: "Connecting...",
  live: "Live",
  ended: "Call ended",
  error: "Could not connect",
};

export function VoicePanel({ className }: { className?: string }) {
  const v = useVoiceSession();
  const endRef = useRef<HTMLDivElement>(null);
  const active = v.phase === "live" || v.phase === "connecting";
  const waiting = v.phase === "requesting" || v.phase === "queued";

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [v.lines]);

  return (
    <div className={cn("flex h-[560px] flex-col overflow-hidden rounded-2xl border bg-card", className)}>
      <div className="flex items-center gap-2.5 border-b px-4 py-3">
        <span
          className={cn(
            "size-2.5 rounded-full",
            v.phase === "live" ? "live-dot bg-signal" : waiting || v.phase === "connecting" ? "animate-pulse bg-signal/60" : "bg-muted-foreground/30",
          )}
        />
        <div>
          <p className="text-sm font-semibold">Voice test</p>
          <p className="text-xs text-muted-foreground">{LABEL[v.phase]}</p>
        </div>
      </div>

      <div className="flex h-24 items-center justify-center gap-[4px] border-b bg-muted/40" aria-hidden>
        {BARS.map((b, i) => (
          <span
            key={i}
            className={cn("wave-bar w-1 rounded-full", v.agentSpeaking ? "bg-primary" : "bg-foreground/20")}
            style={{
              height: `${b.height}%`,
              animationDelay: `${b.delay}s`,
              animationPlayState: v.phase === "live" ? "running" : "paused",
              transform: v.phase === "live" ? undefined : "scaleY(0.2)",
            }}
          />
        ))}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {v.phase === "queued" && v.queue && (
          <div className="rounded-xl border border-signal/30 bg-signal/8 p-4 text-sm">
            <p className="font-medium">
              You are number <span className="font-display text-2xl text-signal">{v.queue.position}</span> in line.
            </p>
            <p className="mt-1 text-muted-foreground">
              Live voice is shared fairly between everyone on the free plan ({v.queue.capacity} lines). Keep this
              page open; the call starts automatically when a line frees up. Text chat works right away.
            </p>
          </div>
        )}
        {v.phase === "error" && v.error && (
          <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/8 p-4 text-sm text-destructive">
            {v.error}
          </p>
        )}
        {!v.lines.length && (v.phase === "idle" || v.phase === "ended") && (
          <div className="px-2 pt-6 text-center text-sm text-muted-foreground">
            <p>Talk to your receptionist exactly as a caller would.</p>
            <p className="mt-1">Allow microphone access when your browser asks. Headphones avoid echo.</p>
          </div>
        )}
        {v.lines.map((l) => (
          <div key={l.id} className={cn("flex flex-col gap-1", l.who === "agent" ? "items-start" : "items-end")}>
            <span className="text-[0.66rem] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
              {l.who === "agent" ? "Receptionist" : "You"}
            </span>
            <p
              className={cn(
                "max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed",
                l.who === "agent" ? "rounded-tl-sm bg-secondary" : "rounded-tr-sm bg-primary text-primary-foreground",
                !l.final && "opacity-70",
              )}
            >
              {l.text}
            </p>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="flex items-center justify-center gap-2 border-t p-3">
        {active ? (
          <>
            <Button variant="outline" size="lg" onClick={v.toggleMute} disabled={v.phase !== "live"}>
              {v.muted ? <MicOffIcon /> : <MicIcon />}
              {v.muted ? "Unmute" : "Mute"}
            </Button>
            <Button size="lg" onClick={v.stop} className="bg-signal text-signal-foreground hover:bg-signal/85">
              <PhoneOffIcon /> Hang up
            </Button>
          </>
        ) : waiting ? (
          <Button variant="outline" size="lg" onClick={v.stop}>
            Leave the queue
          </Button>
        ) : (
          <Button size="lg" onClick={v.start}>
            <PhoneIcon /> {v.phase === "ended" ? "Call again" : "Start a test call"}
          </Button>
        )}
      </div>
    </div>
  );
}
