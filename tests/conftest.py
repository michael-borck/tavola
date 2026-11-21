"""Shared fixtures: a realistic brief, plan, and theme."""

from __future__ import annotations

import pytest

from tavola.brief import Brief, Claim, Relationship, Series
from tavola.design import DesignPlan
from tavola.themes import get_theme


@pytest.fixture
def brief() -> Brief:
    return Brief(
        title="Cities cool down when trees return",
        dek="A decade of street-tree planting shows measurable relief from heat.",
        thesis="Shade is infrastructure, and it pays for itself.",
        claims=[
            Claim(
                text="Urban trees cut peak street temperature by 4.2°C.",
                value="4.2°C",
                label="peak street cooling",
                numeric=4.2,
                unit="°C",
                source="p. 12",
            ),
            Claim(
                text="One mature tree intercepts 1,400 litres of rainfall a year.",
                value="1,400 L",
                label="rainfall intercepted per tree",
                numeric=1400,
                unit="L",
                source="p. 18",
            ),
            Claim(
                text="Tree cover fell from 29% to 21% in a decade.",
                value="8 points",
                label="tree cover lost",
                numeric=8,
                unit="points",
            ),
            Claim(
                text="Residents report fewer heat-illness days after planting.",
            ),
            Claim(
                text="Maintenance costs less than new air conditioning.",
            ),
        ],
        relationships=[
            Relationship(
                kind="sequence",
                summary="How a planting programme works",
                items=["Survey the street", "Plant in winter", "Water for two years", "Evaluate shade"],
            ),
            Relationship(
                kind="comparison",
                summary="Street trees against air conditioning",
                items=["Street trees", "Air conditioning"],
            ),
        ],
        quote="The cheapest cooling is a tree that was planted ten years ago.",
        bottom_line="Fund shade like infrastructure, not decoration.",
        citations=["IPCC 2023, p. 14", "City survey 2024"],
        suggested_density="standard",
    )


@pytest.fixture
def plan() -> DesignPlan:
    return DesignPlan(
        layout="hero-stat",
        style="professional",
        orientation="portrait",
        density="standard",
        emphasis=[0],
        rationale="The brief is anchored by one strong figure.",
    )


@pytest.fixture
def theme():
    return get_theme("professional")


@pytest.fixture
def chart_brief() -> Brief:
    return Brief(
        title="Where the grid gets its power",
        dek="Solar and wind now supply most regional electricity.",
        thesis="Renewables carry the majority of the grid.",
        claims=[
            Claim(text="Solar supplied 50%.", value="50%", label="Solar", numeric=50, unit="%"),
            Claim(text="Wind supplied 30%.", value="30%", label="Wind", numeric=30, unit="%"),
            Claim(text="Hydro supplied 20%.", value="20%", label="Hydro", numeric=20, unit="%"),
            Claim(text="Residents report cleaner air."),
            Claim(text="Costs fell over the decade."),
        ],
        relationships=[
            Relationship(kind="proportion", summary="Share of the grid", items=["Solar", "Wind", "Hydro"]),
        ],
        bottom_line="The grid is mostly renewable.",
    )


@pytest.fixture
def series_brief() -> Brief:
    return Brief(
        title="Electricity prices are falling",
        dek="Retail prices fell after the 2022 peak.",
        thesis="The trend is down, but still above pre-crisis levels.",
        claims=[
            Claim(text="Prices peaked in 2022.", value="2022"),
            Claim(text="The latest price is 21 c/kWh.", value="21"),
            Claim(text="The five-year average is 24 c/kWh.", value="24"),
        ],
        series=[
            Series(
                name="Retail electricity price",
                labels=["2021", "2022", "2023", "2024", "2025"],
                values=[19, 32, 27, 23, 21],
                unit="c/kWh",
            )
        ],
        bottom_line="The direction is finally down.",
    )


@pytest.fixture
def hierarchy_brief() -> Brief:
    return Brief(
        title="What makes a street hot",
        dek="Three forces combine to raise street temperature.",
        thesis="Heat is a system problem, not a single cause.",
        claims=[
            Claim(text="Dark surfaces absorb sunlight."),
            Claim(text="Low tree cover removes shade."),
            Claim(text="Heat illness rises in exposed neighbourhoods."),
        ],
        relationships=[
            Relationship(
                kind="hierarchy",
                summary="Drivers of street heat",
                items=["Street heat", "Dark surfaces", "Low tree cover", "Heat illness"],
            )
        ],
        bottom_line="Cool the surfaces and plant the shade.",
    )


@pytest.fixture
def multi_series_brief(series_brief: Brief) -> Brief:
    data = series_brief.model_copy(deep=True)
    data.series.append(
        Series(
            name="Wholesale price",
            labels=["2021", "2022", "2023", "2024", "2025"],
            values=[12, 24, 19, 16, 14],
            unit="c/kWh",
        )
    )
    return data
