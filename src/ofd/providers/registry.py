"""Provider registry — picks implementations from settings, lazily.

    from ofd.providers.registry import get_llm, get_stt, get_tts, get_embeddings

Implementation modules import their vendor SDK lazily, so importing this module (and starting the
API) never requires the provider SDKs to be installed.
"""

from __future__ import annotations

from functools import lru_cache

from ofd.core.config import settings
from ofd.core.exceptions import ConfigError
from ofd.providers.base import EmbeddingsProvider, LLMProvider, STTProvider, TTSProvider


@lru_cache
def get_stt() -> STTProvider:
    p = settings.STT_PROVIDER.lower()
    if p == "groq":
        from ofd.providers.stt.groq import GroqSTT

        return GroqSTT()
    raise ConfigError(f"STT provider not implemented yet: {p!r}", details={"provider": p})


@lru_cache
def get_llm() -> LLMProvider:
    p = settings.LLM_PROVIDER.lower()
    if p == "groq":
        from ofd.providers.llm.groq import GroqLLM

        return GroqLLM()
    if p == "gemini":
        from ofd.providers.llm.gemini import GeminiLLM

        return GeminiLLM()
    raise ConfigError(f"LLM provider not implemented yet: {p!r}", details={"provider": p})


@lru_cache
def get_tts() -> TTSProvider:
    p = settings.TTS_PROVIDER.lower()
    if p == "kokoro":
        from ofd.providers.tts.kokoro import KokoroTTS

        return KokoroTTS()
    raise ConfigError(f"TTS provider not implemented yet: {p!r}", details={"provider": p})


@lru_cache
def get_embeddings() -> EmbeddingsProvider:
    p = settings.EMBEDDINGS_PROVIDER.lower()
    if p == "fastembed":
        from ofd.providers.embeddings import FastEmbedEmbeddings

        return FastEmbedEmbeddings()
    if p == "gemini":
        from ofd.providers.embeddings import GeminiEmbeddings

        return GeminiEmbeddings()
    raise ConfigError(f"Embeddings provider not implemented yet: {p!r}", details={"provider": p})
