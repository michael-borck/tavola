"""AntV hierarchy: a tree rendered by AntV Infographic."""

from __future__ import annotations

from tavola.antv import render_antv, theme_block
from tavola.layouts._parts import rail_header
from tavola.layouts.base import Layout, LayoutContext, register
from tavola.modules import get_module


def render(ctx: LayoutContext) -> str:
    relationship = ctx.relationship("hierarchy")
    if relationship is None or len(relationship.items) < 3:
        return '<div class="layout-group"><p class="thesis">Hierarchy</p></div>'
    root, *children = relationship.items[:6]
    child_data = "\n".join(f"        - label {child}" for child in children)
    syntax = (
        "infographic hierarchy-tree\n"
        f"{theme_block(ctx.theme)}\n"
        "data\n  items\n"
        f"    - label {root}\n"
        "      children\n"
        f"{child_data}"
    )
    svg = render_antv(syntax, width=ctx.width, height=ctx.height, theme=ctx.theme)
    return (
        '<section class="antv-layout">'
        '<div class="antv-main">'
        + rail_header("Diagram", relationship.summary)
        + f'<div class="antv-figure">{svg}</div>'
        + "</div>"
        + get_module("insight-rail").render(ctx)
        + "</section>"
    )


register(
    Layout(
        id="antv-hierarchy",
        name="AntV hierarchy",
        description=(
            "An automatic tree diagram rendered by AntV Infographic. Use for "
            "a root with several branches."
        ),
        needs=("hierarchy",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
        family="diagram",
    )
)
