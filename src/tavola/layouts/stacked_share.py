"""Stacked share: one horizontal bar divided into parts of a whole."""

from __future__ import annotations

from tavola.layouts._charts import build_chart
from tavola.layouts._parts import claim_list, esc, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    model = build_chart(ctx)
    if len(model.claims) < 2 or model.total <= 0:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )

    relationship = ctx.relationship("proportion")
    title = relationship.summary if relationship else "Share of total"
    segments = []
    rows = []
    for index, (claim, value) in enumerate(
        zip(model.claims, model.values, strict=True), start=1
    ):
        share = max(0.0, min(100.0, value / model.total * 100))
        segments.append(
            f'<span class="stacked-seg stacked-seg-{index}" '
            f'style="width: {share:.2f}%"></span>'
        )
        percent = f'<span class="stacked-percent">{share:.1f}%</span>'
        if claim.unit == "%":
            percent = ""
        rows.append(
            '<li class="stacked-row">'
            f'<span class="stacked-swatch stacked-swatch-{index}"></span>'
            f'<span class="stacked-label">{esc(claim.label or claim.text)}</span>'
            f'<span class="stacked-value">{esc(claim.value)}</span>'
            f"{percent}"
            "</li>"
        )

    return (
        '<section class="stacked-share">'
        + rail_header("Share", title)
        + '<div class="stacked-figure">'
        + '<div class="stacked-bar" role="img" '
        + f'aria-label="{esc(title)}">'
        + "".join(segments)
        + "</div>"
        + '<div class="stacked-scale"><span>0</span><span>100%</span></div>'
        + "</div>"
        + f'<ul class="stacked-legend">{"".join(rows)}</ul>'
        + '<p class="bar-note">Segments show each value’s share of the total.</p>'
        + "</section>"
    )


register(
    Layout(
        id="stacked-share",
        name="Stacked share",
        description=(
            "One horizontal 100% bar divided into parts of a whole, with a "
            "legend. Use when the numbers share a unit and represent a total."
        ),
        needs=("multi_numeric", "chartable"),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
