"""AntV sequence: a horizontal arrow list rendered by AntV Infographic."""

from __future__ import annotations

from tavola.antv import render_antv, theme_block
from tavola.layouts._parts import rail_header
from tavola.layouts.base import Layout, LayoutContext, register
from tavola.modules import get_module


def render(ctx: LayoutContext) -> str:
    relationship = ctx.relationship("sequence")
    labels = ctx.sequence_items()[:6]
    claims = ctx.brief.claims[: len(labels)]
    data = "\n".join(
        f"    - label {label}"
        + (
            f"\n      desc {claim.text}"
            if claim.text.rstrip(".") != label.rstrip(".")
            else ""
        )
        for label, claim in zip(labels, claims, strict=False)
    )
    syntax = (
        "infographic list-row-simple-horizontal-arrow\n"
        f"{theme_block(ctx.theme)}\n"
        "data\n  lists\n"
        f"{data}"
    )
    svg = render_antv(syntax, width=ctx.width, height=ctx.height, theme=ctx.theme)
    return (
        '<section class="antv-layout">'
        '<div class="antv-main">'
        + rail_header("Diagram", relationship.summary if relationship else "Sequence")
        + f'<div class="antv-figure">{svg}</div>'
        + "</div>"
        + get_module("insight-rail").render(ctx)
        + "</section>"
    )


register(
    Layout(
        id="antv-sequence",
        name="AntV sequence",
        description=(
            "An automatic horizontal sequence diagram rendered by AntV "
            "Infographic. Use for ordered steps or milestones."
        ),
        needs=("sequence",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="diagram",
    )
)
