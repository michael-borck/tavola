"""Pass 2: choose a layout, style, orientation, and density.

The model sees the Brief and a catalog of layouts. It returns a DesignPlan.
Invalid ids are rejected, one retry is allowed, then a deterministic heuristic
keeps the CLI usable when a local model returns something unusable.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from tavola.brief import Brief
from tavola.compose import is_chartable, rank_compositions
from tavola.config import DENSITIES, ORIENTATIONS
from tavola.llm import LLMError, LLMProvider

Orientation = Literal["square", "portrait", "landscape"]
Density = Literal["concise", "standard", "detailed"]
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class DesignError(Exception):
    """Raised when a design plan cannot be produced."""


class AssetPrompt(BaseModel):
    """Reserved for M4. Empty in v0.1."""

    purpose: Literal["hero", "texture", "spot"]
    prompt: str
    aspect: str | None = None


class DesignPlan(BaseModel):
    """The bounded design decisions the model is allowed to make."""

    layout: str = Field(description="An id from the layout catalog.")
    style: str = Field(description="An id from the style packs.")
    orientation: Orientation = Field(description="square, portrait, or landscape.")
    density: Density = Field(description="concise, standard, or detailed.")
    palette: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Optional 6-digit hex overrides, most important first.",
    )
    emphasis: list[int] = Field(
        default_factory=list,
        max_length=3,
        description="Claim indices (0-based) to feature.",
    )
    assets: list[AssetPrompt] = Field(default_factory=list)
    rationale: str = Field(default="", description="One line on why this design.")


def _catalog_block(mode: str = "auto") -> str:
    from tavola.layouts import catalog

    lines = []
    for layout in catalog():
        if layout.family == "diagram":
            continue
        if mode == "structured" and layout.family == "illustrated":
            continue
        if mode == "illustrated" and layout.family != "illustrated":
            continue
        needs = ", ".join(layout.needs) or "none"
        orientations = "|".join(layout.orientations)
        lines.append(
            f"- {layout.id} — {layout.description} "
            f"(needs: {needs}; claims {layout.min_claims}-{layout.max_claims}; "
            f"orientations {orientations})"
        )
    return "\n".join(lines)


def _style_block() -> str:
    from tavola.themes import catalog

    return "\n".join(f"- {theme.id} — {theme.description}" for theme in catalog())


def _design_system(brief: Brief) -> str:
    claims = "\n".join(
        f"[{index}] {claim.text}"
        + (f" VALUE={claim.value!r} LABEL={claim.label!r}" if claim.value else "")
        for index, claim in enumerate(brief.claims)
    )
    relationships = (
        "\n".join(
            f"- {rel.kind}: {rel.summary} | items: {', '.join(rel.items)}"
            for rel in brief.relationships
        )
        or "- none"
    )
    return (
        f"TITLE: {brief.title}\n"
        f"DEK: {brief.dek}\n"
        f"THESIS: {brief.thesis}\n"
        f"CLAIMS:\n{claims}\n"
        f"RELATIONSHIPS:\n{relationships}\n"
        f"BOTTOM LINE: {brief.bottom_line}"
    )


_DESIGN_SYSTEM = """\
You are an art director choosing one page design. Return a JSON DesignPlan.

Rules:
- Pick exactly one layout id and one style id from the catalog below. Never
  invent an id.
- Pick the layout whose data needs the Brief actually satisfies. A timeline is
  only right when the relationship is a sequence. A comparison needs two sides.
- Respect the layout's claim range and supported orientations.
- Pick the orientation the content suits: portrait for reading, landscape for
  slides, square for social.
- Pick the density the source can carry. Do not pick detailed for four claims.
- Emphasis indices must exist in the Brief.
- Do not return HTML, CSS, or commentary outside the JSON.
"""


def choose_plan(
    brief: Brief,
    llm: LLMProvider,
    *,
    settings: dict[str, Any],
    layout: str | None = None,
    style: str | None = None,
    orientation: str | None = None,
    density: str | None = None,
    on_progress: Callable[[str], None] | None = None,
    variation: tuple[int, int] | None = None,
    avoid: list[str] | None = None,
    temperature: float = 0.2,
) -> tuple[DesignPlan, list[str]]:
    """Return a validated plan plus any warnings (for the CLI and sidecar)."""
    warnings: list[str] = []
    default_orientation = str(settings.get("orientation") or "portrait")
    default_style = str(settings.get("style") or "professional")
    default_density = str(settings.get("density") or "standard")
    mode = str(settings.get("mode") or "auto")
    ranked = rank_compositions(
        brief,
        orientation=orientation or default_orientation,
        mode=mode,
    )
    shortlist = "; ".join(
        f"{item.layout} ({item.reason})" for item in ranked[:4]
    ) or "none"
    shortlist_line = (
        f"COMPOSITION SHORTLIST: {shortlist}\n"
        "Prefer this shortlist. Use another valid layout only when the Brief "
        "clearly needs it.\n"
    )

    variant_lines = ""
    if variation:
        index, total = variation
        variant_lines = f"VARIANT: {index} of {total}\n"
        if avoid:
            variant_lines += (
                "ALREADY CONSIDERED: " + ", ".join(sorted(set(avoid))) + "\n"
                "Prefer a different valid layout and style when the Brief allows.\n"
            )

    messages = [
        {"role": "system", "content": _DESIGN_SYSTEM},
        {
            "role": "user",
            "content": (
                "BRIEF\n-----\n"
                f"{_design_system(brief)}\n"
                "-----\n"
                f"{variant_lines}"
                f"LAYOUTS\n{_catalog_block(mode)}\n\n"
                f"STYLES\n{_style_block()}\n\n"
                f"{shortlist_line}"
                f"DEFAULT ORIENTATION: {default_orientation}\n"
                f"DEFAULT STYLE: {default_style}\n"
                f"DEFAULT DENSITY: {default_density}\n\n"
                "Return JSON for the DesignPlan schema."
            ),
        },
    ]

    if on_progress:
        if variation:
            on_progress(
                f"choosing a layout ({variation[0]} of {variation[1]})…"
            )
        else:
            on_progress("choosing a layout…")

    plan: DesignPlan | None = None
    try:
        raw = llm.json(
            messages,
            schema=DesignPlan,
            temperature=temperature,
            max_tokens=1500,
        )
        plan = DesignPlan.model_validate(raw)
    except (ValidationError, LLMError) as first_error:
        # One repair, then the heuristic. Keep the first error for the message.
        repair = [
            {"role": "system", "content": _DESIGN_SYSTEM},
            {
                "role": "user",
                "content": (
                    messages[1]["content"]
                    + "\n\nYour previous JSON failed validation with:\n"
                    + f"{first_error}\n\nReturn a corrected DesignPlan. JSON only."
                ),
            },
        ]
        try:
            raw = llm.json(
                repair,
                schema=DesignPlan,
                temperature=max(0.1, temperature - 0.1),
                max_tokens=1500,
            )
            plan = DesignPlan.model_validate(raw)
        except (ValidationError, LLMError):
            plan = heuristic_plan(brief, settings=settings)
            warnings.append(
                "The model did not return a usable design plan; "
                f"fell back to the '{plan.layout}' layout."
            )

    assert plan is not None
    plan, plan_warnings = _apply_overrides(
        plan,
        brief,
        layout=layout,
        style=style,
        orientation=orientation,
        density=density,
    )
    warnings.extend(plan_warnings)
    return plan, warnings


def _apply_overrides(
    plan: DesignPlan,
    brief: Brief,
    *,
    layout: str | None,
    style: str | None,
    orientation: str | None,
    density: str | None,
) -> tuple[DesignPlan, list[str]]:
    warnings: list[str] = []
    if layout:
        plan.layout = layout
    if style:
        plan.style = style
    if orientation:
        plan.orientation = orientation  # type: ignore[assignment]
    if density:
        plan.density = density  # type: ignore[assignment]

    try:
        plan = validate_plan(plan, brief)
    except DesignError as e:
        warnings.append(f"{e} Using the heuristic layout instead.")
        fallback = heuristic_plan(brief, settings={})
        plan.layout = fallback.layout
        plan, _ = _apply_overrides(
            plan,
            brief,
            layout=None,
            style=None,
            orientation=None,
            density=None,
        )
        plan = validate_plan(plan, brief)
    return plan, warnings


def validate_plan(plan: DesignPlan, brief: Brief) -> DesignPlan:
    """Check ids, orientation, palette, and emphasis against the registries."""
    from tavola.layouts import get_layout
    from tavola.themes import get_theme

    try:
        layout = get_layout(plan.layout)
    except KeyError:
        raise DesignError(f"Unknown layout {plan.layout!r}.") from None
    try:
        get_theme(plan.style)
    except KeyError:
        raise DesignError(f"Unknown style {plan.style!r}.") from None

    if plan.orientation not in ORIENTATIONS:
        raise DesignError(f"Unknown orientation {plan.orientation!r}.")
    if plan.orientation not in layout.orientations:
        raise DesignError(
            f"Layout {layout.id!r} does not support {plan.orientation!r}; "
            f"use one of {', '.join(layout.orientations)}."
        )
    if plan.density not in DENSITIES:
        raise DesignError(f"Unknown density {plan.density!r}.")
    if not (layout.min_claims <= len(brief.claims) <= layout.max_claims):
        raise DesignError(
            f"Layout {layout.id!r} needs {layout.min_claims}-"
            f"{layout.max_claims} claims, but the brief has {len(brief.claims)}."
        )
    numeric = brief.numeric_claims()
    if "numeric" in layout.needs and not numeric:
        raise DesignError(
            f"Layout {layout.id!r} needs at least one claim with a printed value."
        )
    if "multi_numeric" in layout.needs and len(numeric) < 3:
        raise DesignError(
            f"Layout {layout.id!r} needs at least three claims with printed "
            f"values, but the brief has {len(numeric)}."
        )
    if "chartable" in layout.needs and not is_chartable(brief):
        raise DesignError(
            f"Layout {layout.id!r} needs comparable numeric claims that can "
            "share one chart scale."
        )
    if "series" in layout.needs and not brief.series:
        raise DesignError(
            f"Layout {layout.id!r} needs an ordered series with labels and values."
        )
    if "multi_series" in layout.needs and len(brief.series) < 2:
        raise DesignError(
            f"Layout {layout.id!r} needs at least two ordered series."
        )
    if "comparison" in layout.needs:
        relationship = brief.relationship("comparison")
        if relationship is None or len(relationship.items) != 2:
            raise DesignError(
                f"Layout {layout.id!r} needs a comparison relationship with "
                "exactly two sides."
            )
    if "hierarchy" in layout.needs:
        relationship = brief.relationship("hierarchy")
        if relationship is None or len(relationship.items) < 3:
            raise DesignError(
                f"Layout {layout.id!r} needs a hierarchy with a root and at "
                "least two children."
            )
    for colour in plan.palette:
        if not _HEX_RE.match(colour):
            raise DesignError(f"Palette entry {colour!r} is not a #rrggbb colour.")
    valid_indices = [i for i in plan.emphasis if 0 <= i < len(brief.claims)]
    plan.emphasis = list(dict.fromkeys(valid_indices))
    return plan


def heuristic_plan(brief: Brief, *, settings: dict[str, Any]) -> DesignPlan:
    """A boring, deterministic choice when the model cannot produce one."""
    relationship_kinds = {rel.kind for rel in brief.relationships}
    numeric = brief.numeric_claims()
    claim_count = len(brief.claims)

    layout_id = "bento"
    if "comparison" in relationship_kinds:
        comparison = brief.relationship("comparison")
        layout_id = (
            "comparison"
            if comparison is not None and len(comparison.items) == 2
            else "illustrated"
        )
    elif "hierarchy" in relationship_kinds:
        hierarchy = brief.relationship("hierarchy")
        if hierarchy is not None and len(hierarchy.items) >= 3:
            layout_id = "hierarchy"
        else:
            layout_id = "bento"
    elif "sequence" in relationship_kinds:
        sequence = brief.relationship("sequence")
        items = sequence.items if sequence else []
        layout_id = "timeline" if _looks_temporal(items) else "process"
    elif "proportion" in relationship_kinds and len(numeric) >= 3:
        layout_id = "donut-share"
    elif len(numeric) >= 3 and claim_count >= 5:
        layout_id = "bento"
    elif len(numeric) >= 3:
        layout_id = "stat-row"
    elif numeric and claim_count >= 4:
        layout_id = "hero-stat"
    elif brief.quote:
        layout_id = "statement"

    from tavola.layouts import get_layout

    mode = str(settings.get("mode") or "auto")
    if mode == "illustrated":
        layout_id = "illustrated"
    layout = get_layout(layout_id)
    if not (layout.min_claims <= claim_count <= layout.max_claims):
        layout_id = "bento"
    if layout_id == "bento" and claim_count < 4:
        layout_id = "statement"

    orientation = str(settings.get("orientation") or "portrait")
    if orientation not in ORIENTATIONS:
        orientation = "portrait"
    density = str(settings.get("density") or "standard")
    if density not in DENSITIES:
        density = "standard"

    return DesignPlan(
        layout=layout_id,
        style=str(settings.get("style") or "professional"),
        orientation=orientation,  # type: ignore[arg-type]
        density=density,  # type: ignore[arg-type]
        emphasis=[0] if brief.claims else [],
        rationale="Deterministic fallback based on the brief's relationships.",
    )


def _looks_temporal(items: list[str]) -> bool:
    """True if labels look like dates, times, or ordinal steps."""
    if not items:
        return False
    pattern = re.compile(
        r"\b(1[89]\d{2}|20\d{2}|Q[1-4]|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|"
        r"Nov|Dec|\d{1,2}:\d{2}|day|week|month|year|first|then|finally)\b",
        re.IGNORECASE,
    )
    return sum(1 for item in items if pattern.search(item)) >= max(1, len(items) // 2)


def choose_plans(
    brief: Brief,
    llm: LLMProvider,
    *,
    settings: dict[str, Any],
    count: int = 3,
    layout: str | None = None,
    style: str | None = None,
    orientation: str | None = None,
    density: str | None = None,
    on_progress: Callable[[str], None] | None = None,
    seed: DesignPlan | None = None,
) -> tuple[list[DesignPlan], list[str]]:
    """Ask for up to ``count`` distinct plans, keeping the first of any tie."""
    total = max(1, min(5, count))
    plans: list[DesignPlan] = []
    warnings: list[str] = []
    seen: set[tuple[str, str, str, str, tuple[int, ...]]] = set()
    avoid: list[str] = []
    if seed is not None:
        plans.append(seed)
        seen.add(
            (
                seed.layout,
                seed.style,
                seed.orientation,
                seed.density,
                tuple(seed.emphasis),
            )
        )
        avoid.extend([seed.layout, seed.style])

    for index in range(1, total + 1):
        if seed is not None and index == 1:
            continue
        plan, plan_warnings = choose_plan(
            brief,
            llm,
            settings=settings,
            layout=layout,
            style=style,
            orientation=orientation,
            density=density,
            on_progress=on_progress,
            variation=(index, total) if total > 1 else None,
            avoid=avoid,
            temperature=min(0.85, 0.2 + 0.22 * (index - 1)),
        )
        warnings.extend(plan_warnings)
        key = (
            plan.layout,
            plan.style,
            plan.orientation,
            plan.density,
            tuple(plan.emphasis),
        )
        if key in seen:
            continue
        seen.add(key)
        plans.append(plan)
        avoid.extend([plan.layout, plan.style])

    if not plans:  # pragma: no cover - choose_plan always returns one
        plans.append(heuristic_plan(brief, settings=settings))
    if len(plans) < total:
        plans = _fill_variants(
            plans,
            brief,
            settings=settings,
            total=total,
            layout=layout,
            style=style,
            orientation=orientation,
            density=density,
        )
    return plans, _unique(warnings)


def _fill_variants(
    plans: list[DesignPlan],
    brief: Brief,
    *,
    settings: dict[str, Any],
    total: int,
    layout: str | None,
    style: str | None,
    orientation: str | None,
    density: str | None,
) -> list[DesignPlan]:
    """Add deterministic valid plans when the model repeats a design."""
    from tavola.themes import theme_ids

    result = list(plans)
    used = {
        (
            item.layout,
            item.style,
            item.orientation,
            item.density,
            tuple(item.emphasis),
        )
        for item in result
    }
    used_layouts = {item.layout for item in result}
    used_styles = {item.style for item in result}
    default_orientation = str(
        settings.get("orientation") or result[0].orientation
    )
    default_density = str(settings.get("density") or result[0].density)
    desired_orientation = orientation or default_orientation
    desired_density = density or default_density
    styles = [style] if style else [str(settings.get("style") or "professional")]
    if not style:
        styles.extend(item for item in theme_ids() if item not in styles)

    def add(candidate: DesignPlan) -> bool:
        try:
            candidate = validate_plan(candidate, brief)
        except DesignError:
            return False
        key = (
            candidate.layout,
            candidate.style,
            candidate.orientation,
            candidate.density,
            tuple(candidate.emphasis),
        )
        if key in used:
            return False
        candidate.rationale = (
            "Deterministic variant added to keep the candidate set diverse."
        )
        result.append(candidate)
        used.add(key)
        used_layouts.add(candidate.layout)
        used_styles.add(candidate.style)
        return True

    if not layout:
        mode = str(settings.get("mode") or "auto")
        for item in rank_compositions(
            brief, orientation=desired_orientation, mode=mode
        ):
            if len(result) >= total:
                break
            if item.layout in used_layouts:
                continue
            for candidate_style in styles:
                if add(
                    DesignPlan(
                        layout=item.layout,
                        style=candidate_style,
                        orientation=desired_orientation,  # type: ignore[arg-type]
                        density=desired_density,  # type: ignore[arg-type]
                    )
                ):
                    break

    if not style:
        for base in list(result):
            if len(result) >= total:
                break
            for candidate_style in styles:
                if candidate_style in used_styles:
                    continue
                if add(
                    base.model_copy(
                        update={
                            "style": candidate_style,
                            "rationale": (
                                "Deterministic style variant for best-of-N "
                                "diversity."
                            ),
                        }
                    )
                ):
                    break

    return result


def _unique(messages: list[str]) -> list[str]:
    return list(dict.fromkeys(messages))
