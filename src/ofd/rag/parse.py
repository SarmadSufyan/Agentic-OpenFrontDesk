"""Document parsing: PDF / DOCX / TXT / pasted text / website URL -> plain text.

Heavy parsers import lazily (part of the `.[rag]` extra). See docs/05-rag.md.
"""

from __future__ import annotations

import io

from ofd.core.exceptions import ProviderError, ValidationError
from ofd.models.enums import SourceType


def parse_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("pypdf not installed (pip install '.[rag]')") from exc
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages)


def parse_docx(data: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("python-docx not installed (pip install '.[rag]')") from exc
    document = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in document.paragraphs)


async def parse_url(url: str) -> str:
    import httpx

    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover
        raise ProviderError("beautifulsoup4 not installed (pip install '.[rag]')") from exc

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "OpenFrontDesk/0.1"})
        resp.raise_for_status()
        html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n")


async def extract_text(
    source_type: str,
    *,
    data: bytes | None = None,
    text: str | None = None,
    url: str | None = None,
) -> str:
    st = source_type.lower()
    if st == SourceType.TEXT or st == SourceType.TXT:
        if text is None and data is not None:
            text = data.decode("utf-8", errors="replace")
        if not text:
            raise ValidationError("No text provided")
        return text
    if st == SourceType.PDF:
        if data is None:
            raise ValidationError("PDF requires file data")
        return parse_pdf(data)
    if st == SourceType.DOCX:
        if data is None:
            raise ValidationError("DOCX requires file data")
        return parse_docx(data)
    if st == SourceType.URL:
        if not url:
            raise ValidationError("URL required")
        return await parse_url(url)
    raise ValidationError(f"Unsupported source_type: {source_type}")
