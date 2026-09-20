"""Kokoro TTS (free, self-hosted) via the OpenAI-compatible Kokoro-FastAPI server.

Uses httpx (a core dep) — no extra SDK. Run the server with the `kokoro` container in
docker-compose (see docs/11-deployment.md).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from ofd.core.config import settings
from ofd.core.exceptions import ProviderError


class KokoroTTS:
    name = "kokoro"

    async def synthesize_stream(
        self, text: str, *, voice: str | None = None
    ) -> AsyncIterator[bytes]:
        url = settings.KOKORO_BASE_URL.rstrip("/") + "/v1/audio/speech"
        payload = {
            "model": "kokoro",
            "input": text,
            "voice": voice or settings.KOKORO_VOICE,
            "response_format": "pcm",  # raw PCM for low-latency streaming into the call
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            yield chunk
        except httpx.HTTPError as exc:  # pragma: no cover
            raise ProviderError(f"Kokoro TTS failed: {exc}") from exc
