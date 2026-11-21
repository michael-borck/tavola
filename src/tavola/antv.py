"""AntV Infographic adapter: render syntax to a static SVG."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from tavola.themes import Theme

_HINT = "AntV rendering needs Playwright: pip install 'tavola[render]'"
_VENDOR = Path(__file__).resolve().parent / "vendor" / "antv"
_BUNDLE = _VENDOR / "infographic.min.js"


class AntVError(Exception):
    """Raised when AntV cannot produce an SVG."""


@cache
def _bundle() -> str:
    try:
        return _BUNDLE.read_text(encoding="utf-8")
    except OSError as e:
        raise AntVError(f"Bundled AntV bundle is missing: {e}") from e


def _font_name(css: str) -> str:
    return css.split(",", 1)[0].strip().strip('"').strip("'") or "Inter"


def theme_block(theme: Theme) -> str:
    palette = "\n".join(f"    - {colour}" for colour in theme.chart_colors[:5])
    return (
        "theme\n"
        f"  colorPrimary {theme.accent}\n"
        f"  colorBg {theme.bg}\n"
        "  palette\n"
        f"{palette}\n"
        "  base\n"
        "    text\n"
        f"      fill {theme.ink}\n"
        f"      font-family {_font_name(theme.font_body)}\n"
        "  item\n"
        "    label\n"
        f"      fill {theme.ink}\n"
        "    desc\n"
        f"      fill {theme.muted}"
    )


def render_antv(syntax: str, *, width: int, height: int, theme: Theme) -> str:
    """Render AntV syntax to an SVG string, without shipping the JS."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - optional extra
        raise AntVError(_HINT) from e

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_content(
                '<!doctype html><html><body><div id="antv" '
                f'style="width:{width}px;height:{height}px"></div>'
                "</body></html>"
            )
            page.add_script_tag(content=_bundle())
            page.evaluate(
                """(args) => {
                  const container = document.querySelector("#antv");
                  container.innerHTML = "";
                  const graphic = new AntVInfographic.Infographic({
                    container: "#antv",
                    width: args.width,
                    height: args.height,
                    editable: false,
                  });
                  graphic.render(args.syntax);
                }""",
                {"syntax": syntax, "width": width, "height": height},
            )
            page.wait_for_function(
                """() => {
                  const svg = document.querySelector("#antv svg");
                  return !!svg && svg.style.visibility !== "hidden";
                }""",
                timeout=3000,
            )
            svg = page.evaluate(
                '() => document.querySelector("#antv svg")?.outerHTML || ""'
            )
            browser.close()
    except AntVError:
        raise
    except Exception as e:
        raise AntVError(
            f"AntV could not render the diagram: {e}. If this is a first run, "
            "run 'playwright install chromium'."
        ) from e

    if not svg:
        raise AntVError("AntV returned no SVG.")
    return _clean_svg(svg)


def _clean_svg(svg: str) -> str:
    cleaned = re.sub(r'\s+xmlns(:\w+)?="http://www\.w3\.org/[^"]+"', "", svg)
    cleaned = re.sub(r'width="\d+px"', 'width="100%"', cleaned, count=1)
    cleaned = re.sub(r'height="\d+px"', 'height="100%"', cleaned, count=1)
    if "http://" in cleaned or "https://" in cleaned:
        raise AntVError("AntV emitted an external URL; refusing to embed it.")
    return cleaned
