"""The layout catalog contract.

A layout is a pure function from ``LayoutContext`` to inner HTML. It never
writes the outer document, never touches the network, and never renders the
title, dek, bottom line, or citations (the page builder owns those).

See ``docs/LAYOUT-CONTRACT.md`` before adding one.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tavola.brief import Claim, Relationship
from tavola.themes import Theme

if TYPE_CHECKING:
    from tavola.brief import Brief
    from tavola.design import DesignPlan

_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_KNOWN_ORIENTATIONS = {"square", "portrait", "landscape"}


@dataclass(frozen=True)
class LayoutContext:
    """Everything a layout may read, and nothing else."""

    brief: Brief
    plan: DesignPlan
    theme: Theme
    size: tuple[int, int]
    assets: dict[str, bytes] = field(default_factory=dict)

    @property
    def width(self) -> int:
        return self.size[0]

    @property
    def height(self) -> int:
        return self.size[1]

    @property
    def density(self) -> str:
        return self.plan.density

    def numeric_claims(self) -> list[Claim]:
        return [claim for claim in self.brief.claims if claim.value]

    def text_claims(self) -> list[Claim]:
        return [claim for claim in self.brief.claims if not claim.value]

    def hero_claim(self) -> Claim | None:
        return next(iter(self.numeric_claims()), None)

    def relationship(self, kind: str) -> Relationship | None:
        return self.brief.relationship(kind)

    def sequence_items(self) -> list[str]:
        relationship = self.relationship("sequence")
        if relationship and relationship.items:
            return relationship.items
        return [claim.label or claim.text for claim in self.brief.claims]

    def comparison_items(self) -> tuple[str, str]:
        relationship = self.relationship("comparison")
        if relationship and len(relationship.items) >= 2:
            return relationship.items[0], relationship.items[1]
        labels = [claim.label or claim.text for claim in self.brief.claims]
        if len(labels) >= 2:
            return labels[0], labels[1]
        return "Option A", "Option B"


RenderFn = Callable[[LayoutContext], str]


@dataclass(frozen=True)
class Layout:
    """One page structure. Invariants are enforced by ``register``."""

    id: str
    name: str
    description: str
    needs: tuple[str, ...]
    min_claims: int
    max_claims: int
    orientations: tuple[str, ...]
    render: RenderFn
    family: str = "structured"


_LAYOUTS: dict[str, Layout] = {}


def register(layout: Layout) -> Layout:
    if not _ID_RE.match(layout.id):
        raise ValueError(f"Layout id {layout.id!r} must be lowercase kebab-case.")
    if layout.id in _LAYOUTS:
        raise ValueError(f"Layout id {layout.id!r} is already registered.")
    if not layout.description.strip():
        raise ValueError(f"Layout {layout.id!r} needs a description.")
    if layout.min_claims > layout.max_claims:
        raise ValueError(f"Layout {layout.id!r} has min_claims > max_claims.")
    if not layout.orientations:
        raise ValueError(f"Layout {layout.id!r} needs at least one orientation.")
    unknown = set(layout.orientations) - _KNOWN_ORIENTATIONS
    if unknown:
        raise ValueError(f"Layout {layout.id!r} has unknown orientations {unknown}.")
    _LAYOUTS[layout.id] = layout
    return layout


def get_layout(layout_id: str) -> Layout:
    try:
        return _LAYOUTS[layout_id]
    except KeyError:
        known = ", ".join(sorted(_LAYOUTS)) or "none"
        raise KeyError(f"Unknown layout {layout_id!r}; known: {known}.") from None


def catalog() -> list[Layout]:
    return [_LAYOUTS[key] for key in sorted(_LAYOUTS)]


def layout_ids() -> list[str]:
    return sorted(_LAYOUTS)
