"""Headless Chromium rendering for PNG and PDF.

Playwright is optional: ``pip install 'tavola[render]'`` and
``playwright install chromium``.
"""

from __future__ import annotations

from pathlib import Path


class RenderError(Exception):
    """Raised when the browser renderer is missing or fails."""


_HINT = (
    "PNG/PDF export needs Playwright: pip install 'tavola[render]' "
    "&& playwright install chromium"
)


def _playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RenderError(_HINT) from e
    return sync_playwright


def html_to_png(
    html: str,
    out: str | Path,
    *,
    width: int,
    height: int,
    scale: int = 2,
) -> Path:
    """Screenshot the exact viewport to a PNG."""
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    sync_playwright = _playwright()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=max(1, scale),
            )
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(120)
            page.screenshot(path=str(target), full_page=False)
            browser.close()
    except RenderError:
        raise
    except Exception as e:
        raise RenderError(
            f"Chromium could not render the page: {e}. If this is a first run, "
            "run 'playwright install chromium'."
        ) from e
    return target


def html_to_pdf(
    html: str,
    out: str | Path,
    *,
    width: int,
    height: int,
) -> Path:
    """Print the exact viewport to a single-page PDF."""
    target = Path(out)
    target.parent.mkdir(parents=True, exist_ok=True)
    sync_playwright = _playwright()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(120)
            page.pdf(
                path=str(target),
                width=f"{width}px",
                height=f"{height}px",
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            browser.close()
    except RenderError:
        raise
    except Exception as e:
        raise RenderError(
            f"Chromium could not print the page: {e}. If this is a first run, "
            "run 'playwright install chromium'."
        ) from e
    return target
