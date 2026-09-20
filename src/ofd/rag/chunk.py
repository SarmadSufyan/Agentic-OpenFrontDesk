"""Token-aware-ish text chunking (word-window with overlap, paragraph-friendly).

Pure functions — unit tested. Real token counting can replace the word heuristic later without
changing the interface. See docs/05-rag.md.
"""

from __future__ import annotations

import re

_WORDS_PER_TOKEN = 0.75  # rough English heuristic


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # collapse runs of spaces/tabs but keep paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    *,
    target_tokens: int = 400,
    overlap_tokens: int = 60,
) -> list[str]:
    """Split text into overlapping chunks of ~target_tokens, respecting word boundaries."""
    text = normalize(text)
    if not text:
        return []

    words = text.split()
    target_words = max(1, int(target_tokens * _WORDS_PER_TOKEN))
    overlap_words = max(0, min(int(overlap_tokens * _WORDS_PER_TOKEN), target_words - 1))
    step = max(1, target_words - overlap_words)

    if len(words) <= target_words:
        return [text]

    chunks: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + target_words]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + target_words >= len(words):
            break
    return chunks
