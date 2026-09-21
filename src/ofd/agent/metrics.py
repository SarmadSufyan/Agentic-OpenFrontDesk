"""Per-call latency tracking for the voice pipeline.

Consumes LiveKit metrics events and accumulates the key conversational-latency components:
end-of-utterance delay, LLM time-to-first-token, and TTS time-to-first-byte. Reports p50/p95 at
call end. Attribute access is defensive so it survives minor LiveKit version changes.
See docs/04-voice-pipeline.md and docs/14-observability.md.
"""

from __future__ import annotations

from ofd.core.logging import get_logger

logger = get_logger("ofd.agent.metrics")


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1))))
    return round(ordered[k] * 1000, 1)  # seconds -> ms


class LatencyTracker:
    def __init__(self) -> None:
        self.eou: list[float] = []  # end-of-utterance delay (s)
        self.llm_ttft: list[float] = []  # LLM time to first token (s)
        self.tts_ttfb: list[float] = []  # TTS time to first byte (s)

    def handle(self, m: object) -> None:
        for attr, bucket in (
            ("end_of_utterance_delay", self.eou),
            ("ttft", self.llm_ttft),
            ("ttfb", self.tts_ttfb),
        ):
            val = getattr(m, attr, None)
            if isinstance(val, (int, float)) and val >= 0:
                bucket.append(float(val))

    def summary(self) -> None:
        def stats(name: str, vals: list[float]) -> dict:
            return {
                "n": len(vals),
                "p50_ms": _percentile(vals, 50),
                "p95_ms": _percentile(vals, 95),
            }

        eou = stats("eou", self.eou)
        llm = stats("llm_ttft", self.llm_ttft)
        tts = stats("tts_ttfb", self.tts_ttfb)

        # Approx spoken-response latency = eou + llm_ttft + tts_ttfb (p50 components).
        parts = [x for x in (eou["p50_ms"], llm["p50_ms"], tts["p50_ms"]) if x is not None]
        approx_p50 = round(sum(parts), 1) if parts else None

        logger.info(
            "call_latency_summary",
            eou=eou,
            llm_ttft=llm,
            tts_ttfb=tts,
            approx_response_p50_ms=approx_p50,
            budget_note="free-stack target p50<700ms, p95<1100ms",
        )

    def snapshot(self) -> dict:
        def stats(vals: list[float]) -> dict:
            return {
                "n": len(vals),
                "p50_ms": _percentile(vals, 50),
                "p95_ms": _percentile(vals, 95),
            }

        return {
            "eou": stats(self.eou),
            "llm_ttft": stats(self.llm_ttft),
            "tts_ttfb": stats(self.tts_ttfb),
        }

    async def summary_async(self) -> None:
        """Async wrapper for use as a LiveKit shutdown callback."""
        self.summary()
