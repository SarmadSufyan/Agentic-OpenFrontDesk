"""Google Gemini LLM (free tier via AI Studio). SDK imported lazily.

Phase 0 scaffold: text completion only (function-calling mapping added in Phase 2). Note: use an
AI Studio API key (GEMINI_API_KEY) — a Google One subscription does not grant API access.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from ofd.core.config import settings
from ofd.core.exceptions import ProviderError
from ofd.providers.base import LLMDelta, Message, ToolSpec


def _to_contents(messages: list[Message]) -> tuple[str | None, list[dict]]:
    """Return (system_instruction, contents) in Gemini's format."""
    system = None
    contents: list[dict] = []
    for m in messages:
        if m.role == "system":
            system = (system + "\n" + m.content) if system else m.content
            continue
        role = "model" if m.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m.content}]})
    return system, contents


class GeminiLLM:
    name = "gemini"

    async def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        stream: bool = True,
    ) -> AsyncIterator[LLMDelta]:
        def _do() -> str:
            try:
                import google.generativeai as genai
            except ImportError as exc:  # pragma: no cover
                raise ProviderError(
                    "google-generativeai not installed (pip install '.[providers]')"
                ) from exc
            genai.configure(api_key=settings.GEMINI_API_KEY)
            system, contents = _to_contents(messages)
            model = genai.GenerativeModel(settings.GEMINI_LLM_MODEL, system_instruction=system)
            resp = model.generate_content(contents, generation_config={"temperature": temperature})
            return resp.text or ""

        try:
            text = await asyncio.to_thread(_do)
        except ProviderError:
            raise
        except Exception as exc:  # pragma: no cover
            raise ProviderError(f"Gemini LLM failed: {exc}") from exc

        yield LLMDelta(text=text, finish_reason="stop")
