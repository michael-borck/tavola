"""Measured browser checks: overflow, clipping, type size, contrast."""

from __future__ import annotations

import pytest

from tavola.measure import MeasureError, measure_html

_BASE = """<!doctype html>
<html><head><style>
* { box-sizing: border-box; margin: 0; }
body { font-family: sans-serif; background: #ffffff; color: #111111; }
.poster { width: 100vw; height: 100vh; padding: 10px; }
</style></head><body><div class="poster">__BODY__</div></body></html>"""


def _measure(body: str):  # type: ignore[no-untyped-def]
    try:
        return measure_html(_BASE.replace("__BODY__", body), width=400, height=300)
    except MeasureError as e:
        pytest.skip(str(e))


def test_clean_page_passes() -> None:
    result = _measure(
        '<h1 style="font-size: 24px">Title</h1>'
        '<p style="font-size: 16px">A readable sentence.</p>'
    )
    assert result.passed
    assert result.issues == []
    assert result.metrics["min_font_px"] == 16


def test_overflow_is_reported() -> None:
    result = _measure('<div style="width: 500px; height: 10px">Wide</div>')
    assert any(issue.code == "overflow" for issue in result.issues)


def test_clipping_is_reported() -> None:
    result = _measure(
        '<div class="claim" style="height: 10px; overflow: hidden">'
        '<span style="font-size: 16px">A line that does not fit</span></div>'
    )
    assert any(issue.code == "clipping" for issue in result.issues)


def test_small_type_is_reported() -> None:
    result = _measure('<span style="font-size: 8px">Tiny</span>')
    assert any(issue.code == "small-type" for issue in result.issues)


def test_low_contrast_is_reported() -> None:
    result = _measure('<p style="font-size: 16px; color: #eeeeee">Faint</p>')
    assert any(issue.code == "low-contrast" for issue in result.issues)


def test_measure_can_capture_a_png() -> None:
    try:
        result = measure_html(
            _BASE.replace("__BODY__", '<p style="font-size: 16px">Readable.</p>'),
            width=400,
            height=300,
            screenshot=True,
        )
    except MeasureError as e:
        pytest.skip(str(e))
    assert result.screenshot is not None
    assert result.screenshot.startswith(b"\x89PNG")


def test_aria_hidden_decorative_overflow_is_ignored() -> None:
    result = _measure(
        '<div aria-hidden="true" style="width: 900px; height: 900px">Art</div>'
    )
    assert not any(issue.code == "overflow" for issue in result.issues)
