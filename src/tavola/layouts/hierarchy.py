"""Hierarchy: one root with a row of child nodes."""

from __future__ import annotations

from tavola.icons import icon_html
from tavola.layouts._parts import claim_list, esc, rail_header, thesis
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    relationship = ctx.relationship("hierarchy")
    if relationship is None or len(relationship.items) < 3:
        return (
            '<div class="layout-group">'
            f"{thesis(ctx.brief.thesis)}"
            f"{claim_list(ctx.brief.claims, limit=4)}"
            "</div>"
        )
    root, *children = relationship.items[:6]
    child_html = "".join(
        '<div class="tree-child">'
        f'<span class="tree-child-index">{index:02d}</span>'
        f"<h3>{esc(child)}</h3>"
        "</div>"
        for index, child in enumerate(children, start=1)
    )
    notes = [claim for claim in ctx.brief.claims if not claim.value][:2]
    notes_html = "".join(
        '<li><span class="kpi-icon">'
        f"{icon_html(claim.label, claim.text)}</span>"
        f"<p>{esc(claim.text)}</p></li>"
        for claim in notes
    )
    notes_block = (
        f'<ul class="tree-notes">{notes_html}</ul>' if notes_html else ""
    )
    return (
        '<section class="hierarchy">'
        + rail_header("Hierarchy", relationship.summary)
        + '<div class="tree">'
        + f'<div class="tree-root">{esc(root)}</div>'
        + '<div class="tree-trunk"></div>'
        + f'<div class="tree-children">{child_html}</div>'
        + "</div>"
        + notes_block
        + "</section>"
    )


register(
    Layout(
        id="hierarchy",
        name="Hierarchy",
        description=(
            "One root with two to five child nodes. Use when the source "
            "contains a clear parent-and-branches relationship."
        ),
        needs=("hierarchy",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
