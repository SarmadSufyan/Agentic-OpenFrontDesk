"""Embeddings providers: fastembed (free, local, CPU) and Gemini (free tier).

NOTE: the vector column dimension (`EMBEDDINGS_DIM`) must match the chosen model. bge-small = 384,
Gemini text-embedding-004 = 768. Changing models requires updating EMBEDDINGS_DIM and reindexing.
"""

from __future__ import annotations

import asyncio

from ofd.core.config import settings
from ofd.core.exceptions import ProviderError


class FastEmbedEmbeddings:
    name = "fastembed"

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model_name = model_name
        self._model = None

    def _get(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:  # pragma: no cover
                raise ProviderError("fastembed not installed (pip install '.[rag]')") from exc
            self._model = TextEmbedding(model_name=self._model_name)
        return self._model

    @property
    def dim(self) -> int:
        return settings.EMBEDDINGS_DIM  # 384 for bge-small

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def _do() -> list[list[float]]:
            model = self._get()
            return [list(map(float, v)) for v in model.embed(texts)]

        return await asyncio.to_thread(_do)


class GeminiEmbeddings:
    name = "gemini"

    @property
    def dim(self) -> int:
        return 768  # text-embedding-004; set EMBEDDINGS_DIM=768 to use this

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def _do() -> list[list[float]]:
            try:
                import google.generativeai as genai
            except ImportError as exc:  # pragma: no cover
                raise ProviderError(
                    "google-generativeai not installed (pip install '.[providers]')"
                ) from exc
            genai.configure(api_key=settings.GEMINI_API_KEY)
            out: list[list[float]] = []
            for t in texts:
                r = genai.embed_content(model=settings.GEMINI_EMBEDDINGS_MODEL, content=t)
                out.append(list(r["embedding"]))
            return out

        return await asyncio.to_thread(_do)
