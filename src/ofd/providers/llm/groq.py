"""Groq LLM (free tier: llama-3.1-8b-instant). SDK imported lazily.

Phase 0 scaffold: yields a single consolidated LLMDelta (with any tool calls). Token-level streaming
is added in Phase 1 where it feeds the TTS incrementally.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from ofd.core.config import settings
from ofd.core.exceptions import ProviderError
from ofd.providers.base import LLMDelta, Message, ToolCall, ToolSpec


def _to_message(m: Message) -> dict:
    d: dict = {"role": m.role, "content": m.content}
    if m.name:
        d["name"] = m.name
    if m.tool_call_id:
        d["tool_call_id"] = m.tool_call_id
    return d


def _to_tool(t: ToolSpec) -> dict:
    return {
        "type": "function",
        "function": {"name": t.name, "description": t.description, "parameters": t.parameters},
    }


class GroqLLM:
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

    async def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        stream: bool = True,
    ) -> AsyncIterator[LLMDelta]:
        def _do():
            client = self._client_()
            kwargs: dict = {
                "model": settings.GROQ_LLM_MODEL,
                "messages": [_to_message(m) for m in messages],
                "temperature": temperature,
                "stream": False,
            }
            if tools:
                kwargs["tools"] = [_to_tool(t) for t in tools]
            return client.chat.completions.create(**kwargs)

        try:
            resp = await asyncio.to_thread(_do)
        except Exception as exc:  # pragma: no cover
            raise ProviderError(f"Groq LLM failed: {exc}") from exc

        choice = resp.choices[0]
        msg = choice.message
        tool_calls: list[ToolCall] = []
        for tc in getattr(msg, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))

        yield LLMDelta(
            text=msg.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )
