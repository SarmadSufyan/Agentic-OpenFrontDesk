"use client";

import { ArrowUpIcon, RotateCcwIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { ChatReply } from "@/lib/types";
import { cn } from "@/lib/utils";

type Turn = { role: "user" | "assistant"; content: string; sources?: string[]; error?: boolean };

const SUGGESTIONS = [
  "What are your opening hours?",
  "How much does it cost?",
  "Can I book something for tomorrow?",
  "Do you offer anything for kids?",
];

/** Text test console. Uses the same grounded brain and tools as the public chat widget. */
export function ChatPanel({ slug, greeting, className }: { slug: string; greeting?: string; className?: string }) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [turns, busy]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    const history = turns.filter((t) => !t.error).slice(-10).map(({ role, content }) => ({ role, content }));
    setTurns((t) => [...t, { role: "user", content: message }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.post<ChatReply>(`/widget/${slug}/chat`, { message, history }, false);
      setTurns((t) => [...t, { role: "assistant", content: res.reply, sources: res.sources }]);
    } catch (e) {
      setTurns((t) => [...t, { role: "assistant", content: (e as Error).message, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={cn("flex h-[560px] flex-col overflow-hidden rounded-2xl border bg-card", className)}>
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div>
          <p className="text-sm font-semibold">Chat test</p>
          <p className="text-xs text-muted-foreground">Same answers your website visitors get.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setTurns([])} disabled={!turns.length || busy}>
          <RotateCcwIcon /> Reset
        </Button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5" aria-live="polite">
        <Bubble role="assistant" content={greeting || "Hi! How can I help you today?"} />
        {turns.map((t, i) => (
          <Bubble key={i} {...t} />
        ))}
        {busy && (
          <div className="flex gap-1 px-1" aria-label="Receptionist is typing">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60"
                style={{ animationDelay: `${i * 120}ms` }}
              />
            ))}
          </div>
        )}
        {!turns.length && (
          <div className="flex flex-wrap gap-2 pt-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                className="rounded-full border bg-background px-3 py-1.5 text-xs transition-colors hover:border-primary hover:text-primary"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="flex items-end gap-2 border-t p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          rows={1}
          placeholder="Ask anything a customer would..."
          className="max-h-32 min-h-10 resize-none"
          aria-label="Message"
        />
        <Button type="submit" size="icon-lg" disabled={!input.trim() || busy} aria-label="Send">
          <ArrowUpIcon />
        </Button>
      </form>
    </div>
  );
}

function Bubble({ role, content, sources, error }: Turn) {
  const agent = role === "assistant";
  return (
    <div className={cn("flex flex-col gap-1.5", agent ? "items-start" : "items-end")}>
      <p
        className={cn(
          "max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed whitespace-pre-wrap",
          agent ? "rounded-tl-sm bg-secondary" : "rounded-tr-sm bg-primary text-primary-foreground",
          error && "border border-destructive/30 bg-destructive/8 text-destructive",
        )}
      >
        {content}
      </p>
      {agent && !!sources?.length && (
        <div className="flex max-w-[85%] flex-wrap gap-1.5">
          {sources.map((s) => (
            <span key={s} className="rounded-md border bg-background px-1.5 py-0.5 font-mono text-[0.68rem] text-muted-foreground">
              <span className="text-primary">source</span> {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
