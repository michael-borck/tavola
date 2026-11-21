"""Source extraction, cleaning, and condensing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tavola.content import ContentError, Source, clean_text, condense, read_source


def test_clean_text_keeps_paragraph_breaks() -> None:
    raw = "  Hello   world \t\n\n\n\nSecond   line.  \n"
    assert clean_text(raw) == "Hello world\n\nSecond line."


def test_read_markdown(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("# Title\n\nSome body text.", encoding="utf-8")
    source = read_source(str(target))
    assert source.title == "notes"
    assert source.kind == "text"
    assert "Some body text." in source.text
    assert source.words == 5


def test_read_html_strips_chrome_and_keeps_main(tmp_path: Path) -> None:
    target = tmp_path / "page.html"
    target.write_text(
        "<html><head><title>Doc</title></head><body>"
        "<nav>Skip me</nav><main><p>Hello</p><script>bad()</script></main>"
        "<footer>Skip too</footer></body></html>",
        encoding="utf-8",
    )
    source = read_source(str(target))
    assert source.title == "Doc"
    assert source.kind == "html"
    assert "Hello" in source.text
    assert "Skip me" not in source.text
    assert "bad()" not in source.text


def test_missing_source() -> None:
    with pytest.raises(ContentError):
        read_source("/definitely/not/here.txt")


def test_directory_rejected(tmp_path: Path) -> None:
    with pytest.raises(ContentError):
        read_source(str(tmp_path))


def test_unsupported_suffix(tmp_path: Path) -> None:
    target = tmp_path / "thing.xyz"
    target.write_text("hi", encoding="utf-8")
    with pytest.raises(ContentError):
        read_source(str(target))


class FakeLLM:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, messages, **kwargs: Any):  # type: ignore[no-untyped-def]
        self.calls += 1

        class Result:
            text = "Condensed paragraph."

        return Result()


def test_condense_passthrough_when_short() -> None:
    llm = FakeLLM()
    source = Source(text="short")
    assert condense(source, llm, max_chars=100) is source  # type: ignore[arg-type]
    assert llm.calls == 0


def test_condense_long_source_keeps_title() -> None:
    llm = FakeLLM()
    source = Source(text="A" * 500, title="Report")
    result = condense(source, llm, max_chars=100, chunk_chars=200)  # type: ignore[arg-type]
    assert llm.calls >= 1
    assert result.title == "Report"
    assert len(result.text) <= 100
    assert result.text
