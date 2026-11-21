"""Heuristic and validated design plans."""

from __future__ import annotations

from typing import Any

import pytest

from tavola.brief import Brief, Claim, Relationship
from tavola.design import (
    DesignError,
    DesignPlan,
    choose_plan,
    choose_plans,
    heuristic_plan,
    validate_plan,
)
from tavola.llm import LLMError


def _plan(**overrides: Any) -> DesignPlan:
    values: dict[str, Any] = {
        "layout": "hero-stat",
        "style": "professional",
        "orientation": "portrait",
        "density": "standard",
    }
    values.update(overrides)
    return DesignPlan(**values)


def test_heuristic_plan_is_valid(brief: Brief) -> None:
    plan = heuristic_plan(brief, settings={})
    assert plan.layout == "comparison"
    validate_plan(plan, brief)


def test_heuristic_prefers_timeline_for_dates() -> None:
    brief = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[Claim(text=f"Claim {i}") for i in range(4)],
        relationships=[
            Relationship(
                kind="sequence",
                summary="A history",
                items=["2019 pilot", "2021 rollout", "2024 review"],
            )
        ],
        bottom_line="B",
    )
    plan = heuristic_plan(brief, settings={"orientation": "landscape"})
    assert plan.layout == "timeline"
    assert plan.orientation == "landscape"
    validate_plan(plan, brief)


def test_heuristic_prefers_process_for_steps() -> None:
    brief = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[Claim(text=f"Claim {i}") for i in range(4)],
        relationships=[
            Relationship(
                kind="sequence",
                summary="How it works",
                items=["Collect", "Sort", "Ship"],
            )
        ],
        bottom_line="B",
    )
    plan = heuristic_plan(brief, settings={})
    assert plan.layout == "process"


def test_validate_rejects_unknown_layout(brief: Brief) -> None:
    with pytest.raises(DesignError):
        validate_plan(_plan(layout="magazine-spread"), brief)


def test_validate_rejects_unknown_style(brief: Brief) -> None:
    with pytest.raises(DesignError):
        validate_plan(_plan(style="brutalist"), brief)


def test_validate_rejects_claim_count() -> None:
    brief = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[Claim(text=f"Claim {i}") for i in range(3)],
        bottom_line="B",
    )
    with pytest.raises(DesignError):
        validate_plan(_plan(layout="bento"), brief)


def test_validate_rejects_bad_palette(brief: Brief) -> None:
    with pytest.raises(DesignError):
        validate_plan(_plan(palette=["red"]), brief)


def test_validate_filters_and_dedupes_emphasis(brief: Brief) -> None:
    plan = validate_plan(_plan(emphasis=[0, 0, 2]), brief)
    assert plan.emphasis == [0, 2]
    plan = validate_plan(_plan(emphasis=[99, 1]), brief)
    assert plan.emphasis == [1]


class FakeLLM:
    name = "fake"
    model = "fake-model"

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def json(self, messages, *, schema, **kwargs):  # type: ignore[no-untyped-def]
        return self.payload


def test_choose_plan_uses_model_and_applies_overrides(brief: Brief) -> None:
    payload = {
        "layout": "hero-stat",
        "style": "editorial",
        "orientation": "landscape",
        "density": "standard",
        "emphasis": [0, 1],
        "rationale": "One strong figure.",
    }
    plan, warnings = choose_plan(
        brief,
        FakeLLM(payload),  # type: ignore[arg-type]
        settings={"orientation": "portrait", "style": "professional"},
        layout="comparison",
        style=None,
        orientation=None,
        density=None,
    )
    assert warnings == []
    assert plan.layout == "comparison"
    assert plan.style == "editorial"
    assert plan.orientation == "landscape"
    validate_plan(plan, brief)


def test_choose_plan_falls_back_when_model_and_repair_fail(brief: Brief) -> None:
    class BrokenLLM:
        name = "broken"
        model = None

        def json(self, messages, *, schema, **kwargs):  # type: ignore[no-untyped-def]
            raise LLMError("not json")

    plan, warnings = choose_plan(
        brief,
        BrokenLLM(),  # type: ignore[arg-type]
        settings={},
    )
    assert warnings
    validate_plan(plan, brief)


class SequenceLLM:
    name = "fake"
    model = "fake-model"

    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = payloads
        self.calls = 0
        self.messages: list[list[dict[str, Any]]] = []

    def json(self, messages, *, schema, **kwargs):  # type: ignore[no-untyped-def]
        self.messages.append(messages)
        payload = self.payloads[min(self.calls, len(self.payloads) - 1)]
        self.calls += 1
        return payload


def test_choose_plans_asks_for_variants_and_dedupes(brief: Brief) -> None:
    payloads = [
        {
            "layout": "hero-stat",
            "style": "professional",
            "orientation": "portrait",
            "density": "standard",
            "emphasis": [0],
        },
        {
            "layout": "stat-row",
            "style": "scientific",
            "orientation": "portrait",
            "density": "concise",
            "emphasis": [1],
        },
        {
            "layout": "bento",
            "style": "editorial",
            "orientation": "portrait",
            "density": "detailed",
            "emphasis": [2],
        },
    ]
    llm = SequenceLLM(payloads)
    plans, warnings = choose_plans(
        brief,
        llm,  # type: ignore[arg-type]
        settings={"orientation": "portrait"},
        count=3,
    )
    assert warnings == []
    assert [plan.layout for plan in plans] == ["hero-stat", "stat-row", "bento"]
    assert "VARIANT: 2 of 3" in llm.messages[1][1]["content"]
    assert "ALREADY CONSIDERED" in llm.messages[1][1]["content"]


def test_choose_plans_fills_distinct_variants(brief: Brief) -> None:
    payload = {
        "layout": "hero-stat",
        "style": "professional",
        "orientation": "portrait",
        "density": "standard",
    }
    plans, warnings = choose_plans(
        brief,
        SequenceLLM([payload]),  # type: ignore[arg-type]
        settings={},
        count=3,
    )
    assert len(plans) == 3
    assert len({(plan.layout, plan.style) for plan in plans}) == 3
    assert warnings == []


def test_validate_rejects_stat_row_without_values() -> None:
    brief = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[Claim(text=f"Claim {i}") for i in range(3)],
        bottom_line="B",
    )
    with pytest.raises(DesignError, match="printed value"):
        validate_plan(_plan(layout="stat-row"), brief)


def test_validate_rejects_multiway_comparison(brief: Brief) -> None:
    multi = brief.model_copy(deep=True)
    multi.relationships = [
        Relationship(kind="comparison", summary="Four options", items=["A", "B", "C", "D"])
    ]
    with pytest.raises(DesignError, match="exactly two"):
        validate_plan(_plan(layout="comparison"), multi)


def test_validate_rejects_comparison_without_relationship(brief: Brief) -> None:
    no_comparison = brief.model_copy(deep=True)
    no_comparison.relationships = []
    with pytest.raises(DesignError, match="comparison relationship"):
        validate_plan(_plan(layout="comparison"), no_comparison)


def test_choose_plans_can_start_from_a_router_seed(brief: Brief) -> None:
    payload = {
        "layout": "stat-row",
        "style": "scientific",
        "orientation": "portrait",
        "density": "standard",
    }
    seed = _plan(layout="bento", style="editorial")
    llm = SequenceLLM([payload])
    plans, warnings = choose_plans(
        brief,
        llm,  # type: ignore[arg-type]
        settings={},
        count=2,
        seed=seed,
    )
    assert plans[0] is seed
    assert plans[1].layout == "stat-row"
    assert llm.calls == 1
    assert warnings == []


def test_validate_rejects_trend_without_series(brief: Brief) -> None:
    with pytest.raises(DesignError, match="ordered series"):
        validate_plan(_plan(layout="trend"), brief)


def test_validate_rejects_hierarchy_without_relationship(brief: Brief) -> None:
    with pytest.raises(DesignError, match="hierarchy"):
        validate_plan(_plan(layout="hierarchy"), brief)
