"""Static quality gate.

Measured checks (overflow, minimum type size, contrast) arrive in M1 with
Playwright. These checks run on the HTML string in milliseconds and catch the
mistakes that make an artefact look broken or leak the network: external
references, forbidden constructs, empty fields, and leftover placeholders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from tavola.brief import Brief

Severity = Literal["error", "warning"]

_EXTERNAL_ATTR = re.compile(
    r"""(?:src|href|poster|action)\s*=\s*["']\s*(?:(?:https?:)?//)""",
    re.IGNORECASE,
)
_ANY_URL = re.compile(r"https?://", re.IGNORECASE)
_CSS_URL = re.compile(r"""url\(\s*["']?\s*(?:(?:https?:)?//)""", re.IGNORECASE)
_CSS_IMPORT = re.compile(r"@import\b", re.IGNORECASE)
_SCRIPT_TAG = re.compile(r"<script\b", re.IGNORECASE)
_FRAME_TAG = re.compile(r"<(?:iframe|object|embed)\b", re.IGNORECASE)
_JS_HREF = re.compile(r"(?:href|src)\s*=\s*[\"']\s*javascript:", re.IGNORECASE)
_INLINE_HANDLER = re.compile(r"<[a-z][^>]*?\son[a-z]+\s*=", re.IGNORECASE)
_TITLE = re.compile(r'<h1 class="title">(.*?)</h1>', re.DOTALL)
_DEK = re.compile(r'<p class="dek">(.*?)</p>', re.DOTALL)
_BOTTOM = re.compile(r'<p class="bottom-line">(.*?)</p>', re.DOTALL)
_TEMPLATE_BRACES = re.compile(r"\{\{|\}\}")
_DATA_URI = re.compile(r'''data:[a-zA-Z0-9.+-]+/[a-zA-Z0-9.+-]+;base64,[^\s"')]+''')
_PLACEHOLDERS = re.compile(
    r"lorem ipsum|\bTODO\b|\bTBD\b|\[insert|placeholder text|\bXXX\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    severity: Severity = "error"


@dataclass
class QualityReport:
    issues: list[Issue] = field(default_factory=list)

    def add(self, code: str, message: str, severity: Severity = "error") -> None:
        self.issues.append(Issue(code=code, message=message, severity=severity))

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        if not self.issues:
            return "Static checks passed."
        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        return ", ".join(parts)


class QualityError(Exception):
    """Raised when the static gate finds an error."""


def check_html(html: str, *, brief: Brief | None = None) -> QualityReport:
    report = QualityReport()

    if _EXTERNAL_ATTR.search(html) or _CSS_URL.search(html) or _ANY_URL.search(html):
        report.add(
            "external-reference",
            "The page references an external URL. Tavola output must be self-contained.",
        )
    if _CSS_IMPORT.search(html):
        report.add("external-import", "The page uses @import; bundle styles inline.")
    if _SCRIPT_TAG.search(html):
        report.add("script-tag", "The page contains a <script> tag.")
    if _FRAME_TAG.search(html):
        report.add("embedded-object", "The page embeds an iframe, object, or embed.")
    if _JS_HREF.search(html):
        report.add("javascript-url", "The page contains a javascript: URL.")
    if _INLINE_HANDLER.search(html):
        report.add("inline-handler", "The page contains an inline event handler.")

    if html.lower().count("<h1") != 1:
        report.add("heading-count", "A page needs exactly one <h1>.")
    if '<footer class="colophon">' not in html:
        report.add("missing-footer", "The bottom line footer is missing.")

    title = _TITLE.search(html)
    dek = _DEK.search(html)
    bottom = _BOTTOM.search(html)
    if title is None or not title.group(1).strip():
        report.add("empty-title", "The title is missing or empty.")
    if dek is None or not dek.group(1).strip():
        report.add("empty-dek", "The dek is missing or empty.")
    if bottom is None or not bottom.group(1).strip():
        report.add("empty-bottom-line", "The bottom line is missing or empty.")

    if _TEMPLATE_BRACES.search(html):
        report.add("template-leftover", "Unrendered template braces remain.")
    if _PLACEHOLDERS.search(_DATA_URI.sub("", html)):
        report.add(
            "placeholder-text",
            "The page contains placeholder text.",
            severity="warning",
        )

    if title is not None:
        length = len(re.sub(r"<[^>]+>", "", title.group(1)).strip())
        if length > 120:
            report.add(
                "long-title",
                f"The title is {length} characters; long titles reflow or clip.",
                severity="warning",
            )
    if dek is not None:
        length = len(re.sub(r"<[^>]+>", "", dek.group(1)).strip())
        if length > 260:
            report.add(
                "long-dek",
                f"The dek is {length} characters; consider shortening it.",
                severity="warning",
            )
    if bottom is not None:
        length = len(re.sub(r"<[^>]+>", "", bottom.group(1)).strip())
        if length > 220:
            report.add(
                "long-bottom-line",
                f"The bottom line is {length} characters.",
                severity="warning",
            )

    if brief is not None and len(brief.claims) < 3:
        report.add("too-few-claims", "The brief has fewer than three claims.")

    return report
