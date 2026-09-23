"use client";

import type { Room } from "livekit-client";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, request } from "@/lib/api";
import type { VoiceAcquire } from "@/lib/types";

export type VoicePhase = "idle" | "requesting" | "queued" | "connecting" | "live" | "ended" | "error";
export type Line = { id: string; who: "you" | "agent"; text: string; final: boolean };

const POLL_MS = 5000;
const HEARTBEAT_MS = 45000; // the server expires a slot after VOICE_SESSION_TTL_SECONDS (360s)

/**
 * A browser voice call through the fair-use access engine: acquire a slot (or wait in the queue),
 * join the LiveKit room, keep the slot alive with heartbeats, and release it on hang-up or unload.
 */
export function useVoiceSession() {
  const [phase, setPhase] = useState<VoicePhase>("idle");
  const [queue, setQueue] = useState<{ position: number; capacity: number } | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const room = useRef<Room | null>(null);
  const beat = useRef<ReturnType<typeof setInterval> | null>(null);
  const audio = useRef<HTMLDivElement | null>(null); // hidden host for the agent's audio elements
  const holding = useRef(false); // true while we hold a slot or a queue position
  const cancelled = useRef(false); // set by stop() to end the queue-polling loop

  const clearTimers = () => {
    if (beat.current) clearInterval(beat.current);
    beat.current = null;
  };

  const dropAudio = () => {
    audio.current?.remove();
    audio.current = null;
  };

  const release = useCallback((keepalive = false) => {
    if (!holding.current) return;
    holding.current = false;
    request("/voice/release", { method: "POST", keepalive }).catch(() => undefined);
  }, []);

  const connect = useCallback(async (grant: VoiceAcquire) => {
    setPhase("connecting");
    const { Room: LkRoom, RoomEvent } = await import("livekit-client");
    const r = new LkRoom({ adaptiveStream: true, dynacast: true });
    room.current = r;

    r.on(RoomEvent.TrackSubscribed, (track) => {
      if (track.kind === "audio") {
        if (!audio.current) {
          audio.current = document.createElement("div");
          audio.current.hidden = true;
          document.body.appendChild(audio.current);
        }
        const el = track.attach();
        el.autoplay = true;
        audio.current.appendChild(el);
      }
    });
    r.on(RoomEvent.TranscriptionReceived, (segments, participant) => {
      // Label by identity: anything from our own participant is the caller, the rest is the agent.
      const who = participant?.identity === r.localParticipant.identity ? "you" : "agent";
      setLines((prev) => {
        const next = [...prev];
        for (const s of segments) {
          const i = next.findIndex((l) => l.id === s.id);
          const line = { id: s.id, who, text: s.text, final: s.final } as Line;
          if (i >= 0) next[i] = line;
          else if (s.text.trim()) next.push(line);
        }
        return next;
      });
    });
    r.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      setAgentSpeaking(speakers.some((p) => p.identity !== r.localParticipant.identity));
    });
    r.on(RoomEvent.Disconnected, () => {
      clearTimers();
      dropAudio();
      release();
      room.current = null;
      setAgentSpeaking(false);
      setPhase((p) => (p === "error" ? p : "ended"));
    });

    await r.connect(grant.url!, grant.token!);
    await r.localParticipant.setMicrophoneEnabled(true);
    beat.current = setInterval(() => {
      api.post("/voice/heartbeat").catch(() => undefined);
    }, HEARTBEAT_MS);
    setPhase("live");
  }, [release]);

  const start = useCallback(async () => {
    clearTimers();
    cancelled.current = false;
    setError(null);
    setLines([]);
    setPhase("requesting");
    try {
      // Acquire is idempotent: while queued, asking again returns the current position or a grant.
      for (;;) {
        const res = await api.post<VoiceAcquire>("/voice/acquire");
        holding.current = true;
        if (cancelled.current) return release();
        if (res.status === "granted") {
          setQueue(null);
          await connect(res);
          return;
        }
        setQueue({ position: res.position ?? 1, capacity: res.capacity ?? 0 });
        setPhase("queued");
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
        if (cancelled.current) return;
      }
    } catch (e) {
      clearTimers();
      release();
      room.current?.disconnect();
      setError((e as Error).message || "Could not start the call");
      setPhase("error");
    }
  }, [connect, release]);

  const stop = useCallback(async () => {
    cancelled.current = true;
    clearTimers();
    const r = room.current;
    room.current = null;
    if (r) await r.disconnect();
    release();
    setQueue(null);
    setAgentSpeaking(false);
    setPhase("ended");
  }, [release]);

  const [muted, setMuted] = useState(false);
  const toggleMute = useCallback(async () => {
    const r = room.current;
    if (!r) return;
    await r.localParticipant.setMicrophoneEnabled(muted);
    setMuted(!muted);
  }, [muted]);

  // Leaving the page (or this screen) must free the slot for the next person.
  useEffect(() => {
    const onUnload = () => release(true);
    window.addEventListener("pagehide", onUnload);
    return () => {
      window.removeEventListener("pagehide", onUnload);
      cancelled.current = true;
      clearTimers();
      room.current?.disconnect();
      dropAudio();
      release(true);
    };
  }, [release]);

  return { phase, queue, lines, agentSpeaking, error, muted, start, stop, toggleMute };
}
