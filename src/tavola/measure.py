"""Measured layout checks in a real browser.

The static gate in :mod:`tavola.quality` catches structure and self-containment
mistakes. This module checks the rendered page for the things only a browser
knows: overflow, clipping, tiny type, and low contrast.
"""

from __future__ import annotations

from typing import Any

from tavola.quality import Issue

_HINT = (
    "Measured checks need Playwright: pip install 'tavola[render]' "
    "&& playwright install chromium"
)


class MeasureError(Exception):
    """Raised when the measured gate cannot run."""


_CHECK_JS = r"""
(options) => {
  const vw = innerWidth;
  const vh = innerHeight;
  const label = (el) => {
    const cls = typeof el.className === "string"
      ? el.className.trim().split(/\s+/).filter(Boolean).slice(0, 2)
          .map((name) => "." + name).join("")
      : "";
    return el.tagName.toLowerCase() + cls;
  };
  const visible = (el) => {
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    if (Number(style.opacity) === 0) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };
  const r2 = (value) => Math.round(value * 10) / 10;

  const all = [...document.querySelectorAll(".poster *")];
  const outside = [];
  for (const el of all) {
    if (!visible(el)) continue;
    if (el.closest('[aria-hidden="true"]')) continue;
    const rect = el.getBoundingClientRect();
    if (
      rect.bottom > vh + 1 || rect.right > vw + 1 ||
      rect.top < -1 || rect.left < -1
    ) {
      outside.push({
        el: label(el),
        top: Math.round(rect.top),
        bottom: Math.round(rect.bottom),
        left: Math.round(rect.left),
        right: Math.round(rect.right),
      });
    }
  }

  const candidates = [
    ".poster", ".masthead", ".body", ".layout-group", ".bento",
    ".bento-cell", ".compare", ".compare-side", ".steps", ".step",
    ".claim-list", ".claim", ".stat-row", ".stat", ".timeline",
    ".timeline-item", ".timeline-body", ".hero", ".statement", ".colophon",
  ];
  const clipped = [];
  for (const el of document.querySelectorAll(candidates.join(","))) {
    if (!visible(el)) continue;
    const style = getComputedStyle(el);
    const clipsX = style.overflowX !== "visible";
    const clipsY = style.overflowY !== "visible";
    if (!clipsX && !clipsY) continue;
    const badX = clipsX && el.scrollWidth > el.clientWidth + 1;
    const badY = clipsY && el.scrollHeight > el.clientHeight + 1;
    if (badX || badY) {
      clipped.push({
        el: label(el),
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
        scrollHeight: el.scrollHeight,
        clientHeight: el.clientHeight,
      });
    }
  }

  const parseColor = (value) => {
    const match = String(value).match(/^rgba?\(([^)]+)\)$/);
    if (!match) return null;
    const parts = match[1].split(/[,/\s]+/).filter(Boolean).map(Number);
    if (parts.length < 3 || parts.some(Number.isNaN)) return null;
    return { r: parts[0], g: parts[1], b: parts[2], a: parts[3] ?? 1 };
  };
  const composite = (fg, bg) => {
    const a = fg.a + bg.a * (1 - fg.a);
    if (a <= 0) return { r: 0, g: 0, b: 0, a: 0 };
    return {
      r: (fg.r * fg.a + bg.r * bg.a * (1 - fg.a)) / a,
      g: (fg.g * fg.a + bg.g * bg.a * (1 - fg.a)) / a,
      b: (fg.b * fg.a + bg.b * bg.a * (1 - fg.a)) / a,
      a,
    };
  };
  const channel = (value) => {
    const v = value / 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  const luminance = (color) =>
    0.2126 * channel(color.r) + 0.7152 * channel(color.g) +
    0.0722 * channel(color.b);
  const contrast = (fg, bg) => {
    const a = luminance(fg);
    const b = luminance(bg);
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  };
  const effectiveBackground = (el) => {
    const chain = [];
    for (let node = el; node; node = node.parentElement) chain.push(node);
    let bg = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = chain.length - 1; i >= 0; i -= 1) {
      const color = parseColor(getComputedStyle(chain[i]).backgroundColor);
      if (color && color.a > 0) bg = composite(color, bg);
    }
    return bg;
  };

  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const failures = [];
  let minFont = null;
  let minFontLabel = "";
  let minFontText = "";
  let contrastChecks = 0;
  let contrastMin = null;
  let contrastMinLabel = "";
  let node = walker.nextNode();
  while (node) {
    const text = (node.textContent || "").trim();
    const el = node.parentElement;
    if (text && el && !seen.has(el) && visible(el)) {
      seen.add(el);
      const style = getComputedStyle(el);
      const size = parseFloat(style.fontSize);
      const color = parseColor(style.color);
      if (size > 0 && color) {
        if (minFont === null || size < minFont) {
          minFont = size;
          minFontLabel = label(el);
          minFontText = text.slice(0, 50);
        }
        const bg = effectiveBackground(el);
        const fg = color.a < 1 ? composite(color, bg) : color;
        const ratio = contrast(fg, bg);
        const weight = parseInt(style.fontWeight, 10) || 400;
        const large = size >= 24 || (size >= 18.66 && weight >= 700);
        const required = large ? options.contrastLarge : options.contrastNormal;
        contrastChecks += 1;
        if (contrastMin === null || ratio < contrastMin) {
          contrastMin = ratio;
          contrastMinLabel = label(el);
        }
        if (ratio + 0.01 < required) {
          failures.push({
            el: label(el),
            text: text.slice(0, 50),
            ratio: r2(ratio),
            required,
            fontPx: r2(size),
          });
        }
      }
    }
    node = walker.nextNode();
  }

  const orphaned = [];
  for (const heading of document.querySelectorAll("h1, h2, h3")) {
    if (!visible(heading)) continue;
    const text = (heading.textContent || "").trim();
    const rect = heading.getBoundingClientRect();
    const size = parseFloat(getComputedStyle(heading).fontSize);
    if (!text) {
      orphaned.push({ el: label(heading), reason: "empty heading" });
      continue;
    }
    const next = heading.nextElementSibling;
    if (next && visible(next)) {
      const gap = next.getBoundingClientRect().top - rect.bottom;
      if (gap > Math.max(48, size * 3)) {
        orphaned.push({
          el: label(heading), reason: "detached from following content",
          gap: Math.round(gap),
        });
      }
    } else if (rect.bottom > vh - 48) {
      orphaned.push({ el: label(heading), reason: "stranded at page bottom" });
    }
  }

  return {
    elements: all.length,
    outside: outside.slice(0, 12),
    clipped: clipped.slice(0, 12),
    smallType: minFont !== null && minFont < options.minFont
      ? { px: r2(minFont), el: minFontLabel, text: minFontText } : null,
    minFont: minFont === null ? null : r2(minFont),
    minFontLabel,
    contrastChecks,
    contrastMin: contrastMin === null ? null : r2(contrastMin),
    contrastMinLabel,
    contrastFailures: failures.slice(0, 12),
    orphaned: orphaned.slice(0, 12),
  };
}
"""


def measure_html(
    html: str,
    *,
    width: int,
    height: int,
    min_font_px: float = 11.0,
    contrast_normal: float = 4.5,
    contrast_large: float = 3.0,
    screenshot: bool = False,
) -> MeasureResult:
    """Open the page at the exact viewport and return issues plus metrics."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - optional extra
        raise MeasureError(_HINT) from e

    options = {
        "minFont": min_font_px,
        "contrastNormal": contrast_normal,
        "contrastLarge": contrast_large,
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(120)
            data = page.evaluate(_CHECK_JS, options)
            png = page.screenshot(type="png") if screenshot else None
            browser.close()
    except MeasureError:
        raise
    except Exception as e:
        raise MeasureError(
            f"Chromium could not measure the page: {e}. If this is a first run, "
            "run 'playwright install chromium'."
        ) from e

    issues: list[Issue] = []
    outside = data.get("outside") or []
    if outside:
        names = ", ".join(item["el"] for item in outside[:4])
        issues.append(
            Issue(
                code="overflow",
                message=(
                    f"{len(outside)} element(s) extend beyond the "
                    f"{width}×{height} viewport: {names}."
                ),
            )
        )

    clipped = data.get("clipped") or []
    if clipped:
        names = ", ".join(item["el"] for item in clipped[:4])
        issues.append(
            Issue(
                code="clipping",
                message=f"{len(clipped)} element(s) clip their content: {names}.",
            )
        )

    small = data.get("smallType")
    if small:
        issues.append(
            Issue(
                code="small-type",
                message=(
                    f"Text renders at {small['px']}px, below the "
                    f"{min_font_px}px minimum: {small['el']}."
                ),
            )
        )

    contrast_failures = data.get("contrastFailures") or []
    if contrast_failures:
        worst = min(contrast_failures, key=lambda item: item["ratio"])
        issues.append(
            Issue(
                code="low-contrast",
                message=(
                    f"{len(contrast_failures)} text style(s) fall below the "
                    f"contrast target; lowest {worst['ratio']}:1 in "
                    f"{worst['el']}."
                ),
            )
        )

    orphaned = data.get("orphaned") or []
    if orphaned:
        names = ", ".join(item["el"] for item in orphaned[:4])
        issues.append(
            Issue(
                code="orphan-heading",
                message=f"Orphaned heading(s): {names}.",
                severity="warning",
            )
        )

    metrics: dict[str, Any] = {
        "elements": data.get("elements"),
        "min_font_px": data.get("minFont"),
        "min_font_element": data.get("minFontLabel"),
        "contrast_checks": data.get("contrastChecks"),
        "contrast_min": data.get("contrastMin"),
        "contrast_min_element": data.get("contrastMinLabel"),
        "overflow": outside,
        "clipped": clipped,
        "contrast_failures": contrast_failures,
        "orphaned": orphaned,
    }
    return MeasureResult(issues=issues, metrics=metrics, screenshot=png)


class MeasureResult:
    """Issues and raw measurements from one rendered page."""

    def __init__(
        self,
        *,
        issues: list[Issue],
        metrics: dict[str, Any],
        screenshot: bytes | None = None,
    ) -> None:
        self.issues = issues
        self.metrics = metrics
        self.screenshot = screenshot

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)
