"""The Brief schema, cleaning, and one-repair extraction."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from tavola.brief import (
    Brief,
    BriefError,
    Claim,
    Relationship,
    Risk,
    clean_brief,
    extract_brief,
)


def _brief_payload() -> dict[str, Any]:
    return {
        "title": "  A title  ",
        "dek": "  A dek.  ",
        "thesis": "  A thesis.  ",
        "claims": [
            {"text": " One. ", "value": " 4% ", "label": " of users "},
            {"text": " Two. "},
            {"text": " Three. "},
        ],
        "relationships": [
            {"kind": "sequence", "summary": " Steps. ", "items": [" A ", "", " B "]}
        ],
        "quote": "   ",
        "bottom_line": "  The point.  ",
        "citations": [" p. 1 ", ""],
    }


def test_brief_requires_three_claims() -> None:
    with pytest.raises(ValidationError):
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[Claim(text="one")],
            bottom_line="B",
        )


def test_clean_brief_trims_and_drops_empty_values() -> None:
    brief = clean_brief(Brief.model_validate(_brief_payload()))
    assert brief.title == "A title"
    assert brief.quote is None
    assert brief.citations == ["p. 1"]
    assert brief.claims[0].value == "4%"
    assert brief.claims[0].label == "of users"
    assert brief.relationships[0].summary == "Steps."
    assert brief.relationships[0].items == ["A", "B"]


def test_claim_without_value_drops_numeric_fields() -> None:
    claim = Claim(text="No number", value=None, numeric=3.0, unit="kg")
    brief = clean_brief(
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[claim, Claim(text="b"), Claim(text="c")],
            bottom_line="B",
        )
    )
    assert brief.claims[0].numeric is None
    assert brief.claims[0].unit is None


class FakeLLM:
    name = "fake"
    model = "fake-model"

    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.replies = replies
        self.calls = 0

    def json(self, messages, *, schema, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        return self.replies[min(self.calls - 1, len(self.replies) - 1)]


def test_extract_brief_returns_clean_model() -> None:
    llm = FakeLLM([_brief_payload()])
    brief = extract_brief("Some source text.", llm)  # type: ignore[arg-type]
    assert brief.title == "A title"
    assert llm.calls == 1


def test_extract_brief_repairs_once() -> None:
    invalid = {"title": "T", "dek": "D", "thesis": "H", "claims": [], "bottom_line": "B"}
    llm = FakeLLM([invalid, _brief_payload()])
    brief = extract_brief("Some source text.", llm)  # type: ignore[arg-type]
    assert len(brief.claims) == 3
    assert llm.calls == 2


def test_extract_brief_rejects_empty_source() -> None:
    llm = FakeLLM([_brief_payload()])
    with pytest.raises(BriefError):
        extract_brief("   ", llm)  # type: ignore[arg-type]


def test_relationship_lookup(brief: Brief) -> None:
    assert brief.relationship("sequence") is not None
    assert brief.relationship("hierarchy") is None
    assert len(brief.numeric_claims()) == 3
    assert isinstance(brief.relationships[0], Relationship)


def test_clean_brief_recovers_printed_values() -> None:
    brief = clean_brief(
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[
                Claim(text="Trees cut peak heat by 4.2°C."),
                Claim(text="One tree catches 1,400 litres of rain."),
                Claim(text="Cover fell from 29% to 21%."),
            ],
            bottom_line="B",
        )
    )
    assert brief.claims[0].value == "4.2°C"
    assert brief.claims[0].numeric == 4.2
    assert brief.claims[0].unit == "°C"
    assert brief.claims[1].value == "1,400 litres"
    assert brief.claims[1].numeric == 1400
    assert brief.claims[1].unit == "litres"
    assert brief.claims[2].value == "29% → 21%"
    assert brief.claims[2].unit == "%"


def test_clean_brief_does_not_overwrite_explicit_values() -> None:
    brief = clean_brief(
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[
                Claim(text="This says 10 but the model says 12.", value="12"),
                Claim(text="No figure here."),
                Claim(text="Another line."),
            ],
            bottom_line="B",
        )
    )
    assert brief.claims[0].value == "12"
    assert brief.claims[1].value is None


def test_clean_brief_strips_braces_and_attaches_units() -> None:
    brief = clean_brief(
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[
                Claim(text="Solar supplied 42% of power.", value="{42}", numeric=42, unit="%"),
                Claim(text="Wind supplied 27% of power.", value="{27}", numeric=27, unit="%"),
                Claim(text="Hydro supplied 18% of power.", value="18", numeric=18, unit="%"),
            ],
            bottom_line="B",
        )
    )
    assert [claim.value for claim in brief.claims] == ["42%", "27%", "18%"]


def test_clean_brief_infers_a_proportion_relationship() -> None:
    brief = clean_brief(
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[
                Claim(text="Solar", value="50%", label="Solar", numeric=50, unit="%"),
                Claim(text="Wind", value="30%", label="Wind", numeric=30, unit="%"),
                Claim(text="Hydro", value="20%", label="Hydro", numeric=20, unit="%"),
            ],
            bottom_line="B",
        )
    )
    relationship = brief.relationship("proportion")
    assert relationship is not None
    assert relationship.items == ["Solar", "Wind", "Hydro"]


def test_clean_brief_fills_unit_from_value() -> None:
    brief = clean_brief(
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[
                Claim(text="A", value="42%", numeric=42, unit="percent"),
                Claim(text="B", value="27%", numeric=27),
                Claim(text="C", value="31%", numeric=31),
            ],
            bottom_line="B",
        )
    )
    assert [claim.unit for claim in brief.claims] == ["%", "%", "%"]

def test_clean_brief_trims_risks_and_mitigations() -> None:
    brief = clean_brief(
        Brief(
            title="T",
            dek="D",
            thesis="H",
            claims=[Claim(text="A"), Claim(text="B"), Claim(text="C")],
            risks=[Risk(risk="  dry spring  ", mitigation="  backup crew  ")],
            bottom_line="B",
        )
    )
    assert brief.risks[0].risk == "dry spring"
    assert brief.risks[0].mitigation == "backup crew"
