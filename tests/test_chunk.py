"""Unit tests for the RAG chunker (pure functions)."""

from __future__ import annotations

from ofd.rag.chunk import chunk_text, normalize


def test_short_text_is_single_chunk() -> None:
    assert chunk_text("hello world") == ["hello world"]


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_text("   ") == []


def test_normalize_collapses_whitespace() -> None:
    assert normalize("a\r\n\n\n\nb   c") == "a\n\nb c"


def test_long_text_splits_with_overlap() -> None:
    text = " ".join(f"word{i}" for i in range(2000))
    chunks = chunk_text(text, target_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    # consecutive chunks overlap (last word of chunk 0 appears within chunk 1)
    c0 = chunks[0].split()
    c1 = chunks[1].split()
    assert c0[-1] in c1[: len(c0)]
