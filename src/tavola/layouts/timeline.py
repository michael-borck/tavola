"""Timeline: ordered events or steps with a rail."""

from __future__ import annotations

from tavola.layouts._parts import esc, rail_header
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    relationship = ctx.relationship("sequence")
    summary = relationship.summary if relationship else "How it unfolds"
    if relationship and relationship.items:
        entries = [(item, "") for item in relationship.items[:6]]
    else:
        entries = [
            (
                claim.label or claim.text,
                claim.text if claim.label and claim.text else "",
            )
            for claim in ctx.brief.claims[:6]
        ]

    rows: list[str] = []
    for index, (label, detail) in enumerate(entries):
        detail_html = (
            f'<p class="timeline-detail">{esc(detail)}</p>' if detail else ""
        )
        rows.append(
            '<li class="timeline-item">'
            f'<span class="timeline-marker">{index + 1:02d}</span>'
            '<div class="timeline-body">'
            f'<h3 class="timeline-label">{esc(label)}</h3>'
            f"{detail_html}"
            "</div>"
            "</li>"
        )

    return (
        '<div class="layout-group">'
        + rail_header("Sequence", summary)
        + f'<ol class="timeline">{"".join(rows)}</ol>'
        + "</div>"
    )


register(
    Layout(
        id="timeline",
        name="Timeline",
        description="Ordered events or milestones when the source has a sequence.",
        needs=("sequence",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
