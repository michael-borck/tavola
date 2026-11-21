"""Page builder: exact size, escaping, theme and palette application."""

from __future__ import annotations

from typing import Any

from tavola.brief import Brief
from tavola.design import DesignPlan
from tavola.render import render_page


def _plan(**overrides: Any) -> DesignPlan:
    values: dict[str, Any] = {
        "layout": "hero-stat",
        "style": "professional",
        "orientation": "portrait",
        "density": "standard",
    }
    values.update(overrides)
    return DesignPlan(**values)


def test_page_has_exact_viewport(brief: Brief, plan: DesignPlan, theme) -> None:
    html = render_page(brief, plan, theme)
    assert 'content="width=1080, height=1350"' in html
    assert 'class="orientation-portrait' in html
    assert "width: 1080" not in html


def test_tight_fit_reflows_without_shrinking_type(
    brief: Brief, plan: DesignPlan, theme
) -> None:
    html = render_page(brief, plan, theme, fit="tight")
    assert "padding: 2.6rem 2.8rem 2rem" in html
    assert "calc(min(100vw / 67.5, 100vh / 56.25))" in html


def test_square_dimensions(brief: Brief, theme) -> None:
    html = render_page(brief, _plan(orientation="square"), theme)
    assert 'content="width=1080, height=1080"' in html


def test_html_is_escaped(brief: Brief, theme) -> None:
    dangerous = brief.model_copy(deep=True)
    dangerous.title = "A & B <C>"
    dangerous.dek = 'He said "no" & left'
    html = render_page(dangerous, _plan(), theme)
    assert "A &amp; B &lt;C&gt;" in html
    assert "He said &quot;no&quot; &amp; left" in html
    assert "<title>A &amp; B &lt;C&gt;</title>" in html


def test_theme_texture_and_layout_attributes(brief: Brief, plan: DesignPlan, theme) -> None:
    html = render_page(brief, plan, theme)
    assert 'data-theme="professional"' in html
    assert 'data-texture="grid"' in html
    assert 'data-layout="hero-stat"' in html
    assert "--accent: #f4b942;" in html


def test_palette_override_sets_contrasting_accent_ink(brief: Brief, theme) -> None:
    html = render_page(brief, _plan(palette=["#00ff00"]), theme)
    assert "--accent: #00ff00;" in html
    assert "--accent-ink: #111111;" in html


def test_no_external_references(brief: Brief, plan: DesignPlan, theme) -> None:
    html = render_page(brief, plan, theme)
    assert "https://" not in html
    assert "http://" not in html
    assert "@import" not in html


def test_bundled_font_is_embedded(brief: Brief, plan: DesignPlan, theme) -> None:
    html = render_page(brief, plan, theme)
    assert "@font-face" in html
    assert 'font-family: "Inter"' in html
    assert "data:font/woff2;base64," in html


def test_every_theme_embeds_a_bundled_font(brief: Brief) -> None:
    from tavola.themes import catalog

    for style in catalog():
        html = render_page(
            brief, _plan(style=style.id), style
        )
        assert "data:font/woff2;base64," in html, style.id


def test_chart_palette_is_emitted(brief: Brief) -> None:
    from tavola.themes import catalog

    for theme in catalog():
        html = render_page(brief, _plan(style=theme.id), theme)
        assert "--chart-1:" in html
        assert len(theme.chart_colors) == 5
