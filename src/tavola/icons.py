"""Small bundled icon set for KPI and stat modules."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

_DIR = Path(__file__).with_name("icons")
_FALLBACK = "chart-no-axes-column"

_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("leaf", ("tree", "shade", "canopy", "green", "forest", "vegetation", "plant")),
    ("heart-pulse", ("health", "illness", "resident", "wellbeing")),
    ("thermometer", ("peak", "degree", "temperature", "heat", "hot")),
    ("sun", ("solar", "sunlight", "cooling")),
    ("droplets", ("rain", "rainfall", "water", "drain", "litre", "liter")),
    ("wind", ("wind", "renewable", "power", "energy", "electricity")),
    ("building", ("city", "urban", "street", "building", "district")),
    ("coins", ("cost", "price", "budget", "money", "cheap", "fund", "maintenance")),
    ("clock", ("year", "month", "day", "time", "decade", "hour")),
    ("chart-no-axes-column", ("percent", "share", "cover", "growth", "rate")),
)


def icon_for(label: str | None, text: str | None = None) -> str:
    for value in (label, text):
        haystack = (value or "").casefold()
        if not haystack:
            continue
        for icon, words in _KEYWORDS:
            if any(word in haystack for word in words):
                return icon
    return _FALLBACK


@cache
def icon_svg(name: str) -> str:
    path = _DIR / f"{name}.svg"
    try:
        svg = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)
    svg = re.sub(r'\s+xmlns="[^"]+"', "", svg)
    return svg.replace("<svg ", '<svg class="kpi-svg" aria-hidden="true" ', 1)


def icon_html(label: str | None, text: str | None = None) -> str:
    svg = icon_svg(icon_for(label, text))
    return f'<span class="kpi-icon">{svg}</span>' if svg else ""
