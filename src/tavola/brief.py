"""Pass 1: turn a source into a typed Brief.

The Brief is the only content object a layout reads. Relationship detection
lives here because it is what lets the design pass choose a timeline instead of
another card grid.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from tavola.llm import LLMProvider


class BriefError(Exception):
    """Raised when a brief cannot be produced or validated."""


Density = Literal["concise", "standard", "detailed"]
RelationKind = Literal["sequence", "comparison", "hierarchy", "proportion", "cause"]


class Claim(BaseModel):
    """One piece of evidence. A claim may carry a printed number."""

    text: str = Field(description="One tight sentence, ideally under 140 characters.")
    value: str | None = Field(
        default=None,
        description="The number or figure as printed, e.g. '42%', '3.4x', '$2.1bn'.",
    )
    label: str | None = Field(
        default=None,
        description="What the value measures, e.g. 'of adults under 30'.",
    )
    numeric: float | None = Field(
        default=None,
        description="Machine-readable value only when the source states it plainly.",
    )
    unit: str | None = Field(default=None, description="%, USD, years, people, ...")
    source: str | None = Field(
        default=None,
        description="Short locator such as 'p. 12', 'Fig. 3', or 'Interview'.",
    )


class Relationship(BaseModel):
    """How the source's ideas relate. Drives layout selection."""

    kind: RelationKind = Field(
        description=(
            "sequence = ordered steps or events; comparison = two sides; "
            "hierarchy = one root with branches; proportion = parts of a whole; "
            "cause = one thing leading to another."
        )
    )
    summary: str = Field(description="One line describing the relationship.")
    items: list[str] = Field(
        default_factory=list,
        description=(
            "Ordered labels. sequence: 3-6. comparison: exactly 2. "
            "hierarchy: root first, then 2-5 children."
        ),
    )


class Series(BaseModel):
    """A small ordered series for a line or trend chart."""

    name: str = Field(description="Short series name, e.g. 'Retail price'.")
    labels: list[str] = Field(
        min_length=3,
        max_length=12,
        description="Ordered x labels, e.g. years or months.",
    )
    values: list[float] = Field(
        min_length=3,
        max_length=12,
        description="Values aligned one-to-one with the labels.",
    )
    unit: str | None = Field(default=None, description="%, USD, kWh, ...")

    @model_validator(mode="after")
    def _same_length(self) -> Series:
        if len(self.labels) != len(self.values):
            raise ValueError("Series labels and values must have equal length.")
        return self


class Risk(BaseModel):
    """One risk and the mitigation the source pairs with it."""

    risk: str = Field(description="A concrete risk stated by the source.")
    mitigation: str | None = Field(
        default=None,
        description="The mitigation the source pairs with this risk.",
    )


class Brief(BaseModel):
    """The content contract between extraction and design."""

    title: str = Field(description="Punchy title, ideally under 90 characters.")
    dek: str = Field(description="One sentence of context under the title.")
    thesis: str = Field(description="The single argument of the page, one sentence.")
    claims: list[Claim] = Field(
        min_length=3,
        max_length=6,
        description="Three to six pieces of evidence, strongest first.",
    )
    relationships: list[Relationship] = Field(
        default_factory=list,
        max_length=2,
        description="Zero to two relationships actually supported by the source.",
    )
    series: list[Series] = Field(
        default_factory=list,
        max_length=2,
        description="Zero to two small ordered series for trend charts.",
    )
    risks: list[Risk] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three risks paired with stated mitigations.",
    )
    quote: str | None = Field(
        default=None, description="A verbatim line worth setting large, if any."
    )
    bottom_line: str = Field(description="The takeaway, one sentence.")
    citations: list[str] = Field(
        default_factory=list,
        description="Short locators only, e.g. 'IPCC 2023, p. 14'.",
    )
    suggested_density: Density = Field(
        default="standard", description="How much content the source can carry."
    )

    def numeric_claims(self) -> list[Claim]:
        return [claim for claim in self.claims if claim.value]

    def relationship(self, kind: str) -> Relationship | None:
        for relationship in self.relationships:
            if relationship.kind == kind:
                return relationship
        return None


_BRIEF_SYSTEM = """\
You are an editor preparing one page. Read the source and return a JSON Brief.

Rules:
- Never invent a number, name, date, or unit. If the source does not state it,
  omit it.
- A claim is one idea in one sentence. When the sentence contains a printed
  number, set `value` to that figure, set `numeric` to its machine-readable
  value, and say what it measures in `label`. Do not leave `value` null when
  the claim visibly contains a figure.
- Use 3 to 6 claims. Put the strongest first.
- Record only relationships the source actually supports. A list of steps is a
  `sequence`; two sides are a `comparison`; a root and branches are a
  `hierarchy`; parts of a whole are a `proportion`; one thing causing another
  is `cause`. Do not invent a relationship to fill the field.
- For a `proportion`, each claim is one part; do not add a combined total as
  another claim.
- If the source states risks and mitigations, put each pair in `risks` as
  `{risk, mitigation}`. Use only mitigations the source actually states.
- For `cause`, use the order risk first, mitigation second.
- If the source contains a small table or ordered series, put it in `series`
  with labels and values in the same order. Do not infer a series from vague
  prose or invent points.
- `title` is a headline, not a summary. `dek` adds context. `thesis` is the one
  argument a reader should remember.
- `bottom_line` is the takeaway, not a repeat of the title.
- Citations are short locators (page, figure, section), never URLs.
- Keep the source's language. Do not translate.
- `suggested_density`: concise for one message, standard for an explainer,
  detailed only when the source carries several distinct findings.
"""


def _user_prompt(source_text: str, language: str | None) -> str:
    language_line = (
        f"\nWrite the brief in {language}, keeping proper nouns as they appear.\n"
        if language
        else ""
    )
    return (
        "SOURCE\n"
        "------\n"
        f"{source_text}\n"
        "------\n"
        f"{language_line}"
        "Return JSON for the Brief schema."
    )


def clean_brief(brief: Brief) -> Brief:
    """Trim whitespace and drop empty list entries without changing meaning."""
    brief.title = brief.title.strip()
    brief.dek = brief.dek.strip()
    brief.thesis = brief.thesis.strip()
    brief.bottom_line = brief.bottom_line.strip()
    if brief.quote is not None:
        quote = brief.quote.strip()
        brief.quote = quote or None
    brief.citations = [
        citation.strip() for citation in brief.citations if citation.strip()
    ]
    for claim in brief.claims:
        claim.text = claim.text.strip()
        if claim.value is not None:
            claim.value = _clean_value(claim.value)
        if claim.label is not None:
            claim.label = claim.label.strip() or None
        if claim.source is not None:
            claim.source = claim.source.strip() or None
        _enrich_claim(claim)
        if claim.unit:
            claim.unit = _normalise_unit(claim.unit)
        if claim.value:
            _attach_unit(claim)
        if not claim.value:
            claim.numeric = None
            claim.unit = None
    for relationship in brief.relationships:
        relationship.summary = relationship.summary.strip()
        relationship.items = [item.strip() for item in relationship.items if item.strip()]
    for series in brief.series:
        series.name = series.name.strip()
        series.unit = (series.unit or "").strip() or None
        series.labels = [label.strip() for label in series.labels]
    for risk in brief.risks:
        risk.risk = risk.risk.strip()
        risk.mitigation = (risk.mitigation or "").strip() or None
    _infer_proportion(brief)
    return brief


def _infer_proportion(brief: Brief) -> None:
    """Add a proportion relationship when percentages already form a whole."""
    if len(brief.relationships) >= 2:
        return
    if any(rel.kind == "proportion" for rel in brief.relationships):
        return
    parts = [
        claim
        for claim in brief.claims
        if claim.unit == "%" and claim.numeric is not None
    ]
    if len(parts) < 3:
        return
    total = sum(abs(claim.numeric or 0.0) for claim in parts)
    if not (90 <= total <= 110):
        return
    brief.relationships.append(
        Relationship(
            kind="proportion",
            summary="Share of the whole",
            items=[claim.label or claim.text for claim in parts],
        )
    )


def extract_brief(
    source_text: str,
    llm: LLMProvider,
    *,
    language: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> Brief:
    """Run the brief pass, with one repair attempt on invalid output."""
    if not source_text.strip():
        raise BriefError("The source is empty after extraction.")

    messages = [
        {"role": "system", "content": _BRIEF_SYSTEM},
        {"role": "user", "content": _user_prompt(source_text, language)},
    ]
    if on_progress:
        on_progress("reading the source into a brief…")

    raw = llm.json(messages, schema=Brief, temperature=0.2, max_tokens=3000)
    try:
        return clean_brief(Brief.model_validate(raw))
    except ValidationError as first_error:
        if on_progress:
            on_progress("brief did not validate; asking for one repair…")
        repair = [
            {"role": "system", "content": _BRIEF_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"{_user_prompt(source_text, language)}\n\n"
                    "Your previous JSON failed validation with:\n"
                    f"{first_error}\n\n"
                    "Return a corrected JSON object. Do not add commentary."
                ),
            },
        ]
        raw = llm.json(repair, schema=Brief, temperature=0.1, max_tokens=3000)
        try:
            return clean_brief(Brief.model_validate(raw))
        except ValidationError as second_error:
            raise BriefError(
                f"The model could not produce a valid brief: {second_error}"
            ) from second_error


_NUMBER = r"\d[\d,]*(?:\.\d+)?"
_UNIT_WORDS = (
    "million|billion|thousand|litres?|liters?|people|persons?|years?|days?|"
    "hours?|minutes?|hectares?|tonnes?|tons?|kg|km|cm|mm|ha|bn|USD|EUR|GBP"
)
_VALUE_RE = re.compile(
    rf"(?<![\w.])((?:[$€£]\s?)?{_NUMBER}(?:\s?(?:%|°[CF]|{_UNIT_WORDS}))?)"
    rf"(?=$|[\s.,;:)])",
    re.IGNORECASE,
)
_RANGE_RE = re.compile(
    r"(?<!\w)(\d+(?:\.\d+)?)\s*%\s*(?:to|→|–|—|-)\s*(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


def _printed_value(text: str) -> tuple[str, float | None, str | None] | None:
    """Pull a printed figure out of a claim when the model omitted it."""
    range_match = _RANGE_RE.search(text)
    if range_match:
        left, right = range_match.groups()
        return f"{left}% → {right}%", None, "%"

    matches = [match.group(1).strip() for match in _VALUE_RE.finditer(text)]
    if len(matches) != 1:
        return None
    value = re.sub(r"\s+", " ", matches[0]).strip()
    number = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", value)
    numeric = float(number.group(0).replace(",", "")) if number else None
    if not value:
        return None
    return value, numeric, _unit_of(value)


def _unit_of(value: str) -> str | None:
    if "%" in value:
        return "%"
    match = re.search(r"°[CF]", value)
    if match:
        return match.group(0)
    match = re.search(r"[$€£]", value)
    if match:
        return match.group(0)
    match = re.search(
        rf"\b({_UNIT_WORDS})\b",
        value,
        re.IGNORECASE,
    )
    return match.group(1).lower() if match else None


def _normalise_unit(value: str) -> str | None:
    unit = value.strip()
    if not unit:
        return None
    aliases = {
        "percent": "%",
        "percentage": "%",
        "pct": "%",
        "degrees celsius": "°C",
        "celsius": "°C",
        "degrees fahrenheit": "°F",
        "fahrenheit": "°F",
    }
    return aliases.get(unit.casefold(), unit)


def _clean_value(value: str) -> str | None:
    cleaned = value.strip()
    cleaned = re.sub(r"^[{\[]\s*(.*?)\s*[}\]]$", r"\1", cleaned)
    return cleaned.strip() or None


def _attach_unit(claim: Claim) -> None:
    if not claim.value or not claim.unit:
        return
    if claim.unit in {"%", "°C", "°F"} and claim.unit not in claim.value:
        claim.value = f"{claim.value}{claim.unit}"
    elif claim.unit in {"$", "€", "£"} and not claim.value.startswith(claim.unit):
        claim.value = f"{claim.unit}{claim.value}"


def _enrich_claim(claim: Claim) -> None:
    if not claim.value:
        found = _printed_value(claim.text)
        if found:
            claim.value, numeric, unit = found
            claim.numeric = numeric
            claim.unit = unit
    elif claim.numeric is None or claim.unit is None:
        if claim.numeric is None:
            number = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", claim.value)
            if number:
                claim.numeric = float(number.group(0).replace(",", ""))
        if claim.unit is None:
            claim.unit = _unit_of(claim.value)
