"""Map our config (STT/LLM/TTS provider selection) to LiveKit plugin instances.

This keeps the "swap free <-> premium by env" story consistent for the live pipeline. The realtime
plugins are LiveKit's (they handle streaming); our `ofd.providers.*` ABCs are for non-realtime work
(RAG embeddings, batch STT, eval text-mode). Plugin SDKs are imported lazily so this module is safe to
import without the full agent extra installed.
"""

from __future__ import annotations

import re
from typing import Any

from ofd.core.config import settings
from ofd.core.exceptions import ConfigError


def build_stt() -> Any:
    p = settings.STT_PROVIDER.lower()
    if p == "groq":
        from livekit.plugins import groq

        return groq.STT(model=settings.GROQ_STT_MODEL)
    if p == "deepgram":
        from livekit.plugins import deepgram

        return deepgram.STT(model="nova-3")
    raise ConfigError(f"No LiveKit STT plugin wired for STT_PROVIDER={p!r}")


def build_llm() -> Any:
    p = settings.LLM_PROVIDER.lower()
    if p == "groq":
        from livekit.plugins import groq

        return groq.LLM(model=settings.GROQ_LLM_MODEL)
    if p == "gemini":
        from livekit.plugins import google  # livekit-plugins-google

        return google.LLM(model=settings.GEMINI_LLM_MODEL)
    if p == "openai":
        from livekit.plugins import openai

        return openai.LLM(model="gpt-4o-mini")
    raise ConfigError(f"No LiveKit LLM plugin wired for LLM_PROVIDER={p!r}")


_KOKORO_VOICE = re.compile(r"^[a-z]{2}_[a-z]+$")  # e.g. af_heart, bm_george


def build_tts(voice: str | None = None) -> Any:
    """Build the TTS plugin. `voice` is the agent's configured voice; for Kokoro it overrides
    KOKORO_VOICE when it is a valid Kokoro voice id."""
    p = settings.TTS_PROVIDER.lower()
    if p == "kokoro":
        # Kokoro-FastAPI is OpenAI-compatible, so we drive it through the OpenAI TTS plugin.
        from livekit.plugins import openai

        chosen = voice if voice and _KOKORO_VOICE.match(voice) else settings.KOKORO_VOICE
        return openai.TTS(
            base_url=settings.KOKORO_BASE_URL.rstrip("/") + "/v1",
            model="kokoro",
            voice=chosen,
            api_key="not-needed",
        )
    if p == "cartesia":
        from livekit.plugins import cartesia

        return cartesia.TTS(voice=settings.CARTESIA_VOICE or None)
    if p == "deepgram":
        from livekit.plugins import deepgram

        return deepgram.TTS()
    raise ConfigError(f"No LiveKit TTS plugin wired for TTS_PROVIDER={p!r}")


def build_turn_detection() -> Any:
    """Semantic turn detection if the plugin is installed; otherwise fall back to VAD endpointing."""
    try:
        from livekit.plugins.turn_detector.multilingual import MultilingualModel

        return MultilingualModel()
    except Exception:
        return "vad"
