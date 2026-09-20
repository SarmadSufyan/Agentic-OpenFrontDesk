"""Provider interfaces and normalized result types.

Every external AI capability implements one of these Protocols. Callers (services, agent, RAG)
depend only on these interfaces — never on a vendor SDK. See docs/07-providers.md and ADR-0002.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

# --- Normalized message / tool shapes -----------------------------------------

Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str
    name: str | None = None
    tool_call_id: str | None = None


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema


# --- Normalized results -------------------------------------------------------


@dataclass
class STTResult:
    text: str
    is_final: bool = True
    confidence: float | None = None
    language: str | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMDelta:
    """A streamed chunk of an LLM response."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None


# --- Interfaces ---------------------------------------------------------------


@runtime_checkable
class STTProvider(Protocol):
    name: str

    async def transcribe(self, audio: bytes, *, language: str | None = None) -> STTResult: ...

    def transcribe_stream(
        self, audio: AsyncIterator[bytes], *, language: str | None = None
    ) -> AsyncIterator[STTResult]: ...


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(
        self,
        messages: list[Message],
        *,
        tools: list[ToolSpec] | None = None,
        temperature: float = 0.3,
        stream: bool = True,
    ) -> AsyncIterator[LLMDelta]: ...


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    def synthesize_stream(
        self, text: str, *, voice: str | None = None
    ) -> AsyncIterator[bytes]: ...


@runtime_checkable
class EmbeddingsProvider(Protocol):
    name: str

    @property
    def dim(self) -> int: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
