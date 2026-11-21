"""Source extraction and condensing.

One source in v0.1: a file path or an http(s) URL. Extraction keeps paragraph
structure so the brief pass can see headings, lists, and numbers rather than a
wall of text.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from tavola.llm import LLMProvider

MAX_SOURCE_CHARS = 40_000
CHUNK_CHARS = 12_000

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".text", ".log", ".csv"}
_HTML_SUFFIXES = {".html", ".htm"}


class ContentError(Exception):
    """Raised when a source cannot be read or extracted."""


@dataclass
class Source:
    """One source document, cleaned and ready for the brief pass."""

    text: str
    title: str = ""
    origin: str | None = None
    kind: str = "text"

    @property
    def words(self) -> int:
        return len(self.text.split())


def clean_text(text: str) -> str:
    """Normalise whitespace while keeping paragraph breaks."""
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.splitlines()]
    cleaned: list[str] = []
    blank = 0
    for line in lines:
        if not line:
            blank += 1
            if blank <= 1:
                cleaned.append("")
            continue
        blank = 0
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup(
        ["script", "style", "nav", "footer", "header", "aside", "noscript", "svg"]
    ):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True)
    return clean_text(text), title


def _from_url(url: str, timeout: float = 30) -> Source:
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "tavola/0.1 (+https://github.com/michael-borck/tavola)"},
        )
    except requests.RequestException as e:
        raise ContentError(f"Could not fetch {url}: {e}") from e
    if response.status_code >= 400:
        raise ContentError(f"Fetching {url} returned {response.status_code}.")
    content_type = response.headers.get("content-type", "")
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as e:  # pragma: no cover - dependency is core
            raise ContentError("PDF support needs pypdf.") from e
        import io

        reader = PdfReader(io.BytesIO(response.content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        return Source(
            text=clean_text(text), title=Path(url).stem, origin=url, kind="pdf"
        )
    if "html" in content_type or not content_type:
        text, title = _html_to_text(response.text)
        return Source(text=text, title=title or url, origin=url, kind="html")
    return Source(
        text=clean_text(response.text), title=Path(url).stem, origin=url, kind="text"
    )


def _from_pdf(path: Path) -> Source:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover - dependency is core
        raise ContentError("PDF support needs pypdf.") from e
    try:
        reader = PdfReader(str(path))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:  # pypdf raises a variety of errors
        raise ContentError(f"Could not read PDF {path}: {e}") from e
    return Source(text=clean_text(text), title=path.stem, origin=str(path), kind="pdf")


def _from_docx(path: Path) -> Source:
    try:
        import docx  # type: ignore[import-not-found]
    except ImportError as e:
        raise ContentError(
            "DOCX support is optional: pip install 'tavola[docx]'."
        ) from e
    document = docx.Document(str(path))
    text = "\n\n".join(paragraph.text for paragraph in document.paragraphs)
    return Source(text=clean_text(text), title=path.stem, origin=str(path), kind="docx")


def read_source(target: str) -> Source:
    """Read a URL or a file and return cleaned text plus a title."""
    if target.startswith(("http://", "https://")):
        return _from_url(target)

    path = Path(target).expanduser()
    if not path.exists():
        raise ContentError(f"Source not found: {target}")
    if path.is_dir():
        raise ContentError(
            f"{target} is a directory. Tavola reads one file in v0.1."
        )

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _from_pdf(path)
    if suffix == ".docx":
        return _from_docx(path)
    if suffix in _HTML_SUFFIXES:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ContentError(f"Could not read {target}: {e}") from e
        text, title = _html_to_text(raw)
        return Source(text=text, title=title or path.stem, origin=str(path), kind="html")
    if suffix in _TEXT_SUFFIXES or suffix == "":
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ContentError(f"Could not read {target}: {e}") from e
        return Source(
            text=clean_text(raw), title=path.stem, origin=str(path), kind="text"
        )
    raise ContentError(
        f"Unsupported source type {suffix!r}. Use PDF, DOCX, HTML, Markdown, or text."
    )


def _chunks(text: str, size: int) -> list[str]:
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for paragraph in paragraphs:
        if length + len(paragraph) > size and current:
            chunks.append("\n\n".join(current))
            current = []
            length = 0
        current.append(paragraph)
        length += len(paragraph) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks or [text]


_CONDENSE_SYSTEM = """\
You compress source material for a designer. Keep every number, unit, name,
date, and caveat exactly as written. Drop repetition, navigation, and filler.
Keep the order of ideas. Return plain prose in short paragraphs, no headings,
no commentary, no markdown fences."""


def condense(
    source: Source,
    llm: LLMProvider,
    *,
    max_chars: int = MAX_SOURCE_CHARS,
    chunk_chars: int = CHUNK_CHARS,
    on_progress: Callable[[str], None] | None = None,
) -> Source:
    """Shorten very long sources with map-reduce, preserving facts."""
    if len(source.text) <= max_chars:
        return source

    chunks = _chunks(source.text, chunk_chars)
    summaries: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        if on_progress:
            on_progress(f"condensing source {index}/{len(chunks)}…")
        result = llm.complete(
            [
                {"role": "system", "content": _CONDENSE_SYSTEM},
                {"role": "user", "content": chunk},
            ],
            temperature=0.1,
            max_tokens=900,
        )
        summaries.append(result.text.strip())

    joined = "\n\n".join(summaries)
    if len(joined) > max_chars:
        joined = joined[:max_chars].rsplit("\n\n", 1)[0]
    return Source(
        text=joined,
        title=source.title,
        origin=source.origin,
        kind=source.kind,
    )
