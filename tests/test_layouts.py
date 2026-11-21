"""Every layout renders, escapes content, and passes the static gate."""

from __future__ import annotations

import pytest

from tavola.brief import Brief, Series
from tavola.design import DesignError, DesignPlan, validate_plan
from tavola.layouts import catalog, get_layout, layout_ids
from tavola.quality import check_html
from tavola.render import render_page
from tavola.themes import get_theme

EXPECTED = {
    "antv-comparison",
    "antv-hierarchy",
    "antv-sequence",
    "bar-share",
    "bento",
    "donut-share",
    "comparison",
    "dashboard",
    "hero-stat",
    "grouped-bars",
    "hierarchy",
    "illustrated",
    "illustrated-comparison",
    "illustrated-quote",
    "illustrated-sequence",
    "illustrated-trend",
    "poster",
    "process",
    "quadrant",
    "statement",
    "stacked-share",
    "stat-row",
    "timeline",
    "trend",
    "trend-dashboard",
}

MARKERS = {
    "antv-comparison": 'class="antv-layout"',
    "antv-hierarchy": 'class="antv-layout"',
    "antv-sequence": 'class="antv-layout"',
    "bar-share": 'class="bar-share"',
    "bento": 'class="bento"',
    "donut-share": 'class="donut-share"',
    "comparison": 'class="compare"',
    "dashboard": 'class="dashboard"',
    "hero-stat": 'class="hero"',
    "grouped-bars": 'class="grouped-bars"',
    "hierarchy": 'class="hierarchy"',
    "illustrated": 'class="illustrated"',
    "illustrated-comparison": 'class="illustrated-comparison"',
    "illustrated-quote": 'class="illustrated-quote"',
    "illustrated-sequence": 'class="illustrated-sequence"',
    "illustrated-trend": 'class="illustrated-trend"',
    "poster": 'class="poster-layout"',
    "process": 'class="steps"',
    "quadrant": 'class="quadrant"',
    "statement": 'class="statement"',
    "stacked-share": 'class="stacked-share"',
    "stat-row": 'class="stat-row"',
    "timeline": 'class="timeline"',
    "trend": 'class="trend"',
    "trend-dashboard": 'class="trend-dashboard"',
}


def test_catalog_ids() -> None:
    assert set(layout_ids()) == EXPECTED
    assert {layout.id for layout in catalog()} == EXPECTED


def test_every_layout_declares_a_usable_range() -> None:
    for layout in catalog():
        assert layout.min_claims <= layout.max_claims
        assert layout.min_claims >= 3
        assert layout.max_claims <= 6
        assert layout.orientations
        assert layout.description


def test_unknown_layout_raises() -> None:
    with pytest.raises(KeyError):
        get_layout("does-not-exist")


CHART_LAYOUTS = {"bar-share", "donut-share", "dashboard", "stacked-share"}


@pytest.mark.parametrize("layout_id", sorted(EXPECTED))
def test_layout_renders_clean_page(
    layout_id: str,
    brief: Brief,
    chart_brief: Brief,
    series_brief: Brief,
    multi_series_brief: Brief,
    hierarchy_brief: Brief,
) -> None:
    if layout_id == "grouped-bars":
        data = multi_series_brief
    elif layout_id in {"trend", "trend-dashboard", "illustrated-trend"}:
        data = series_brief
    elif layout_id in {"hierarchy", "antv-hierarchy"}:
        data = hierarchy_brief
    else:
        data = chart_brief if layout_id in CHART_LAYOUTS else brief
    theme = get_theme("professional")
    plan = DesignPlan(
        layout=layout_id,
        style=theme.id,
        orientation="portrait",
        density="standard",
    )
    plan = validate_plan(plan, data)
    html = render_page(data, plan, theme)

    assert MARKERS[layout_id] in html
    assert f'data-layout="{layout_id}"' in html
    assert data.title in html
    assert check_html(html, brief=data).passed


@pytest.mark.parametrize("layout_id", sorted(EXPECTED))
def test_layout_supports_every_orientation(layout_id: str, brief: Brief) -> None:
    layout = get_layout(layout_id)
    assert set(layout.orientations) == {"square", "portrait", "landscape"}


def test_model_text_is_escaped(brief: Brief) -> None:
    dangerous = brief.model_copy(deep=True)
    dangerous.claims[3].text = '<script>alert("x")</script> & more'
    dangerous.claims[0].label = '<img src=x onerror="alert(1)">'
    plan = validate_plan(
        DesignPlan(
            layout="hero-stat",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        dangerous,
    )
    html = render_page(dangerous, plan, get_theme("professional"))
    assert "<script>alert" not in html
    assert "<img src=x" not in html
    assert "&lt;img" in html
    assert "&lt;script&gt;" in html
    assert "&amp; more" in html
    assert check_html(html, brief=dangerous).passed


def test_timeline_shows_claim_detail(brief: Brief) -> None:
    unlinked = brief.model_copy(deep=True)
    unlinked.relationships = []
    plan = validate_plan(
        DesignPlan(
            layout="timeline",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        unlinked,
    )
    html = render_page(unlinked, plan, get_theme("professional"))
    assert "timeline-detail" in html
    assert unlinked.claims[0].text in html


def test_citation_rendered(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="statement",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(brief, plan, get_theme("professional"))
    assert "IPCC 2023, p. 14" in html


def test_bar_share_renders_proportional_bars(chart_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="bar-share",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        chart_brief,
    )
    html = render_page(chart_brief, plan, get_theme("professional"))
    assert html.count('class="bar-fill bar-fill-') == 3
    assert "each value’s share" in html
    assert 'class="bar-fill bar-fill-2"' in html


def test_bar_share_uses_share_mode_for_percentage_parts() -> None:
    from tavola.brief import Claim

    parts = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[
            Claim(text="Solar: 50%.", value="50%", numeric=50, unit="%"),
            Claim(text="Wind: 30%.", value="30%", numeric=30, unit="%"),
            Claim(text="Hydro: 20%.", value="20%", numeric=20, unit="%"),
        ],
        bottom_line="B",
    )
    plan = validate_plan(
        DesignPlan(
            layout="bar-share",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        parts,
    )
    html = render_page(parts, plan, get_theme("professional"))
    assert "each value’s share of the total" in html
    assert "width: 50.0%" in html
    assert "width: 30.0%" in html
    assert "width: 20.0%" in html


def test_donut_share_renders_ring_and_legend() -> None:
    from tavola.brief import Claim

    parts = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[
            Claim(text="Solar: 50%.", value="50%", label="Solar", numeric=50, unit="%"),
            Claim(text="Wind: 30%.", value="30%", label="Wind", numeric=30, unit="%"),
            Claim(text="Hydro: 20%.", value="20%", label="Hydro", numeric=20, unit="%"),
        ],
        bottom_line="B",
    )
    plan = validate_plan(
        DesignPlan(
            layout="donut-share",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        parts,
    )
    html = render_page(parts, plan, get_theme("professional"))
    assert html.count('class="donut-seg') == 3
    assert 'stroke-dasharray="50.00 50.00"' in html
    assert ">100%<" in html


def test_donut_prefers_the_proportion_relationship() -> None:
    from tavola.brief import Claim, Relationship

    parts = Brief(
        title="T",
        dek="D",
        thesis="H",
        claims=[
            Claim(text="Solar supplied 42%.", value="42%", label="solar", numeric=42, unit="%"),
            Claim(text="Wind supplied 27%.", value="27%", label="wind", numeric=27, unit="%"),
            Claim(text="Solar and wind supplied 69%.", value="69%", label="solar and wind", numeric=69, unit="%"),
            Claim(text="Hydro supplied 18%.", value="18%", label="hydro", numeric=18, unit="%"),
            Claim(text="Other supplied 13%.", value="13%", label="other sources", numeric=13, unit="%"),
        ],
        relationships=[
            Relationship(
                kind="proportion",
                summary="Share of the whole",
                items=["solar", "wind", "hydro", "other sources"],
            )
        ],
        bottom_line="B",
    )
    plan = validate_plan(
        DesignPlan(
            layout="donut-share",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        parts,
    )
    html = render_page(parts, plan, get_theme("professional"))
    assert html.count('class="donut-seg') == 4
    assert ">69%<" not in html
    assert ">13%<" in html


def test_dashboard_combines_bars_and_insights(chart_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="dashboard",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        chart_brief,
    )
    html = render_page(chart_brief, plan, get_theme("professional"))
    assert html.count('class="donut-seg') == 3
    assert 'class="dash-rail"' in html
    assert 'class="dash-note"' in html


def test_chart_rejects_mixed_units(brief: Brief) -> None:
    with pytest.raises(DesignError, match="comparable numeric"):
        validate_plan(
            DesignPlan(
                layout="bar-share",
                style="professional",
                orientation="portrait",
                density="standard",
            ),
            brief,
        )


def test_stacked_share_renders_segmented_bar(chart_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="stacked-share",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        chart_brief,
    )
    html = render_page(chart_brief, plan, get_theme("professional"))
    assert html.count('class="stacked-seg stacked-seg-') == 3
    assert "width: 50.00%" in html
    assert html.count('class="stacked-row"') == 3


def test_trend_renders_line_and_labels(series_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="trend",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        series_brief,
    )
    html = render_page(series_brief, plan, get_theme("professional"))
    assert 'class="trend-line"' in html
    assert html.count('class="trend-dot') == 5
    assert "2021" in html and "2025" in html


def test_trend_dashboard_adds_kpis(series_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="trend-dashboard",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        series_brief,
    )
    html = render_page(series_brief, plan, get_theme("professional"))
    assert 'class="trend-line"' in html
    assert html.count('class="td-kpi"') == 3
    assert 'class="dash-rail"' in html


def test_trend_supports_two_series(series_brief: Brief) -> None:
    data = series_brief.model_copy(deep=True)
    data.series.append(
        Series(
            name="Wholesale price",
            labels=["2021", "2022", "2023", "2024", "2025"],
            values=[12, 24, 19, 16, 14],
            unit="c/kWh",
        )
    )
    plan = validate_plan(
        DesignPlan(
            layout="trend",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        data,
    )
    html = render_page(data, plan, get_theme("professional"))
    assert html.count('class="trend-line') == 2
    assert "trend-line-2" in html
    assert "trend-legend" in html
    assert "trend-dot-series-2" in html


def test_hierarchy_renders_root_and_children(hierarchy_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="hierarchy",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        hierarchy_brief,
    )
    html = render_page(hierarchy_brief, plan, get_theme("professional"))
    assert 'class="tree-root"' in html
    assert html.count('class="tree-child"') == 3
    assert "Street heat" in html


def test_poster_renders_quote_and_art(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="poster",
            style="editorial",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(brief, plan, get_theme("editorial"))
    assert 'class="poster-quote"' in html
    assert 'class="poster-art"' in html
    assert 'class="poster-svg"' in html


def test_antv_sequence_renders_svg(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="antv-sequence",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(brief, plan, get_theme("professional"))
    assert '<svg' in html
    assert "AntV" not in html or "antv-layout" in html
    assert "http://" not in html


def test_antv_hierarchy_renders_svg(hierarchy_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="antv-hierarchy",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        hierarchy_brief,
    )
    html = render_page(hierarchy_brief, plan, get_theme("professional"))
    assert '<svg' in html
    assert "antv-layout" in html


def test_antv_comparison_renders_svg(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="antv-comparison",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(brief, plan, get_theme("professional"))
    assert "antv-compare-head" in html
    assert '<svg' in html


def test_illustrated_uses_a_generated_hero(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="illustrated",
            style="editorial",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(
        brief,
        plan,
        get_theme("editorial"),
        assets={"hero": b"png"},
    )
    assert "data:image/png;base64," in html


def test_illustrated_brief_renders_hero_and_stats(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="illustrated",
            style="editorial",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(brief, plan, get_theme("editorial"))
    assert 'class="illus-hero"' in html
    assert 'class="illus-art"' in html
    assert html.count('class="td-kpi"') == 3


def test_illustrated_trend_adds_chart(series_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="illustrated-trend",
            style="editorial",
            orientation="portrait",
            density="standard",
        ),
        series_brief,
    )
    html = render_page(
        series_brief,
        plan,
        get_theme("editorial"),
        assets={"hero": b"png"},
    )
    assert "data:image/png;base64," in html
    assert 'class="trend-line"' in html
    assert html.count('class="td-kpi"') == 3


def test_grouped_bars_renders_two_series(multi_series_brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="grouped-bars",
            style="scientific",
            orientation="portrait",
            density="standard",
        ),
        multi_series_brief,
    )
    html = render_page(multi_series_brief, plan, get_theme("scientific"))
    assert html.count('class="gb-bar gb-bar-1"') == 5
    assert html.count('class="gb-bar gb-bar-2"') == 5
    assert "Wholesale price" in html


def test_quadrant_renders_four_cells(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="quadrant",
            style="professional",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(brief, plan, get_theme("professional"))
    assert html.count('class="q-cell"') == 4


def test_illustrated_comparison_uses_art(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="illustrated-comparison",
            style="editorial",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(
        brief, plan, get_theme("editorial"), assets={"hero": b"png"}
    )
    assert "data:image/png;base64," in html
    assert 'class="illus-compare"' in html
    assert html.count('class="ic-side"') == 2


def test_illustrated_quote_renders_quote(brief: Brief) -> None:
    plan = validate_plan(
        DesignPlan(
            layout="illustrated-quote",
            style="editorial",
            orientation="portrait",
            density="standard",
        ),
        brief,
    )
    html = render_page(
        brief, plan, get_theme("editorial"), assets={"hero": b"png"}
    )
    assert 'class="iq-quote"' in html
    assert "cheapest cooling" in html
