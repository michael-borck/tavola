"""Deterministic composition ranking."""

from __future__ import annotations

from tavola.brief import Brief, Claim, Relationship
from tavola.compose import rank_compositions


def _brief(**overrides) -> Brief:  # type: ignore[no-untyped-def]
    values = {
        "title": "T",
        "dek": "D",
        "thesis": "H",
        "claims": [
            Claim(text="One", value="1"),
            Claim(text="Two", value="2"),
            Claim(text="Three", value="3"),
        ],
        "bottom_line": "B",
    }
    values.update(overrides)
    return Brief(**values)


def test_comparison_tops_the_ranking() -> None:
    brief = _brief(
        relationships=[
            Relationship(kind="comparison", summary="A vs B", items=["A", "B"])
        ]
    )
    assert rank_compositions(brief)[0].layout == "comparison"


def test_proportion_prefers_donut() -> None:
    brief = _brief(
        claims=[
            Claim(text="A", value="50%", numeric=50, unit="%"),
            Claim(text="B", value="30%", numeric=30, unit="%"),
            Claim(text="C", value="20%", numeric=20, unit="%"),
        ],
        relationships=[
            Relationship(kind="proportion", summary="Share", items=["A", "B", "C"])
        ],
    )
    ranked = rank_compositions(brief)
    assert ranked[0].layout == "donut-share"
    assert "bar-share" in [item.layout for item in ranked]
    assert "stacked-share" in [item.layout for item in ranked]


def test_no_numeric_does_not_offer_charts() -> None:
    ranked = rank_compositions(
        _brief(claims=[Claim(text="A"), Claim(text="B"), Claim(text="C")])
    )
    assert ranked[0].layout == "statement"
    assert "bar-share" not in [item.layout for item in ranked]
    assert "donut-share" not in [item.layout for item in ranked]


def test_invalid_orientation_is_excluded() -> None:
    brief = _brief()
    layout = "stat-row"
    ranked = rank_compositions(brief, orientation="landscape")
    assert layout in [item.layout for item in ranked]


def test_no_numeric_claims_only_returns_statement() -> None:
    brief = _brief(
        claims=[Claim(text="A"), Claim(text="B"), Claim(text="C")],
    )
    assert [item.layout for item in rank_compositions(brief)] == ["statement"]


def test_dashboard_enters_for_numbers_plus_qualitative_claims() -> None:
    brief = _brief(
        claims=[
            Claim(text="A", value="1", numeric=1),
            Claim(text="B", value="2", numeric=2),
            Claim(text="C", value="3", numeric=3),
            Claim(text="A qualitative note."),
        ]
    )
    ranked = [item.layout for item in rank_compositions(brief)]
    assert "dashboard" in ranked
    assert ranked.index("dashboard") < ranked.index("hero-stat")


def test_series_tops_the_ranking(series_brief) -> None:  # type: ignore[no-untyped-def]
    ranked = rank_compositions(series_brief)
    assert ranked[0].layout == "trend"
    assert "trend-dashboard" in [item.layout for item in ranked]


def test_hierarchy_tops_the_ranking(hierarchy_brief) -> None:  # type: ignore[no-untyped-def]
    assert rank_compositions(hierarchy_brief)[0].layout == "hierarchy"


def test_illustrated_report_outranks_sequence_with_sources(brief) -> None:  # type: ignore[no-untyped-def]
    ranked = [item.layout for item in rank_compositions(brief, mode="illustrated")]
    assert ranked[0] == "illustrated"


def test_mode_filters_layout_families(brief) -> None:  # type: ignore[no-untyped-def]
    structured = rank_compositions(brief, mode="structured")
    illustrated = rank_compositions(brief, mode="illustrated")
    auto = rank_compositions(brief, mode="auto")
    assert "illustrated" not in [item.layout for item in structured]
    assert "illustrated-sequence" in [item.layout for item in illustrated]
    assert "illustrated" in [item.layout for item in auto]


def test_illustrated_report_outranks_process_without_sources(brief) -> None:  # type: ignore[no-untyped-def]
    data = brief.model_copy(deep=True)
    data.quote = None
    for claim in data.claims:
        claim.source = None
    ranked = [item.layout for item in rank_compositions(data, mode="auto")]
    assert ranked[0] == "illustrated"


def test_quote_prefers_illustrated_quote() -> None:
    from tavola.brief import Claim

    brief = Brief(
        title="The library is the last free room",
        dek="Civic space matters.",
        thesis="Fund the room, not just the shelves.",
        claims=[Claim(text="Access"), Claim(text="Attention"), Claim(text="Company")],
        quote="A library card is the cheapest membership in civic life.",
        bottom_line="Fund the room.",
    )
    ranked = [item.layout for item in rank_compositions(brief, mode="auto")]
    assert ranked[0] == "illustrated-quote"
