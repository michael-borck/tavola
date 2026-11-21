"""Bundled OFL fonts, embedded as data URIs.

Fonts are latin-subset WOFF2 files so an artefact stays self-contained without
shipping hundreds of kilobytes of unused glyphs. Themes keep a system fallback
for languages outside the latin subset.
"""

from __future__ import annotations

import base64
from functools import cache
from pathlib import Path

from tavola.themes.base import Theme

_FONT_DIR = Path(__file__).with_name("fonts")

FONT_FACES: dict[str, tuple[str, str]] = {
    "Inter": ("inter-latin.woff2", "100 900"),
    "Source Serif 4": ("source-serif-4-latin.woff2", "200 900"),
    "Caveat": ("caveat-latin.woff2", "400 700"),
}


@cache
def _font_uri(filename: str) -> str | None:
    path = _FONT_DIR / filename
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    return "data:font/woff2;base64," + base64.b64encode(payload).decode("ascii")


def font_css(theme: Theme) -> str:
    """Return @font-face rules for the bundled families this theme names."""
    families = f"{theme.font_display} {theme.font_body}"
    blocks: list[str] = []
    for family, (filename, weight) in FONT_FACES.items():
        if family not in families:
            continue
        uri = _font_uri(filename)
        if uri is None:
            continue
        blocks.append(
            "@font-face {\n"
            f'  font-family: "{family}";\n'
            "  font-style: normal;\n"
            f"  font-weight: {weight};\n"
            "  font-display: block;\n"
            f'  src: url("{uri}") format("woff2");\n'
            "}"
        )
    return "\n".join(blocks)


def bundled_families() -> list[str]:
    return sorted(FONT_FACES)
