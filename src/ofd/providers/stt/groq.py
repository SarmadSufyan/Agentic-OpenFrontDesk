"""Groq Whisper STT (free tier). SDK imported lazily.

Batch transcription is implemented here; true low-latency streaming is wired through the LiveKit
plugin in the agent (Phase 1). This adapter is used for RAG/eval/batch and as a fallback.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from ofd.core.config import settings
from ofd.core.exceptions import ProviderError
from ofd.providers.base import STTResult


class GroqSTT:
    name = "groq"

    def __init__(self) -> None:
        self._client = None

    def _client_(self):
        if self._client is None:
            try:
                from groq import Groq
            except ImportError as exc:  # pragma: no cover
                raise ProviderError("groq SDK not installed (pip install '.[providers]')") from exc
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    async def transcribe(self, audio: bytes, *, language: str | None = None) -> STTResult:
        def _do() -> str:
            client = self._client_()
            resp = client.audio.transcriptions.create(
                file=("audio.wav", audio),
                model=settings.GROQ_STT_MODEL,
                language=language,
            )
            return resp.text

        try:
            text = await asyncio.to_thread(_do)
        except Exception as exc:  # pragma: no cover
            raise ProviderError(f"Groq STT failed: {exc}") from exc
        return STTResult(text=text, is_final=True, language=language)

    async def transcribe_stream(
        self, audio: AsyncIterator[bytes], *, language: str | None = None
    ) -> AsyncIterator[STTResult]:
        # Placeholder: buffer then transcribe. Real streaming = LiveKit plugin in Phase 1.
        chunks = [c async for c in audio]
        yield await self.transcribe(b"".join(chunks), language=language)
