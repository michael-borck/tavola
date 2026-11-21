"""The pipeline: read, condense, brief, plan, render, check, save."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tavola import __version__
from tavola.assets import AssetError, generate_hero
from tavola.brief import Brief, extract_brief
from tavola.compose import rank_compositions
from tavola.config import (
    ORIENTATIONS,
    ConfigurationError,
    load_config,
    resolve_design_settings,
    resolve_illustration_settings,
    resolve_llm_settings,
    resolve_render_settings,
)
from tavola.content import Source, clean_text, condense, read_source
from tavola.design import DesignError, DesignPlan, choose_plans, validate_plan
from tavola.judge import VisualScore, score_page
from tavola.llm import LLMError, LLMProvider, get_provider
from tavola.measure import MeasureError, MeasureResult, measure_html
from tavola.quality import QualityReport, check_html
from tavola.render import render_page
from tavola.router import RouterError, route_layout
from tavola.themes import Theme, get_theme


class GenerateError(Exception):
    """Raised when a pipeline stage cannot produce an artefact."""


@dataclass
class GenerateOptions:
    """One-off overrides that beat config for this run."""

    layout: str | None = None
    style: str | None = None
    orientation: str | None = None
    density: str | None = None
    mode: str | None = None
    language: str | None = None
    candidates: int | None = None
    judge: str | None = None
    router: str | None = None
    illustration_enabled: bool | None = None
    illustration_style: str | None = None
    illustration_direction: str | None = None


@dataclass
class GenerateResult:
    """Everything the CLI, web UI, and sidecar need after a run."""

    brief: Brief
    plan: DesignPlan
    theme: Theme
    html: str
    quality: QualityReport
    warnings: list[str] = field(default_factory=list)
    source_title: str = ""
    source_origin: str | None = None
    provider: str = ""
    model: str | None = None
    measurements: dict[str, Any] | None = None
    candidates: list[CandidateResult] = field(default_factory=list)
    routing: dict[str, Any] | None = None

    @property
    def width(self) -> int:
        return ORIENTATIONS[self.plan.orientation][0]

    @property
    def height(self) -> int:
        return ORIENTATIONS[self.plan.orientation][1]


@dataclass
class SaveResult:
    artefact: Path
    sidecar: Path
    html: Path | None = None


@dataclass
class CandidateResult:
    """One rendered plan in a best-of-N run."""

    plan: DesignPlan
    theme: Theme
    html: str
    quality: QualityReport
    measurements: dict[str, Any] | None = None
    screenshot: bytes | None = None
    visual: VisualScore | None = None
    score: float | None = None
    score_source: str = ""
    reason: str = ""

    def sidecar(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "plan": self.plan.model_dump(),
            "score": self.score,
            "score_source": self.score_source,
            "reason": self.reason,
            "measurements": self.measurements,
        }
        return payload


def generate(
    source: str | Path | Source,
    *,
    config: dict[str, Any] | None = None,
    options: GenerateOptions | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> GenerateResult:
    """Run the full pipeline and return the rendered, checked artefact."""
    settings = config if config is not None else load_config()
    options = options or GenerateOptions()
    progress = on_progress or (lambda _message: None)

    llm_settings = resolve_llm_settings(settings)
    provider = get_provider(llm_settings)

    if isinstance(source, Source):
        document = source
    else:
        target = str(source)
        progress("reading the source…")
        document = read_source(target)
    if not document.text.strip():
        raise GenerateError("The source has no readable text.")

    document = condense(document, provider, on_progress=on_progress)

    brief = extract_brief(
        document.text,
        provider,
        language=options.language,
        on_progress=on_progress,
    )
    return _finish(
        brief,
        provider=provider,
        settings=settings,
        options=options,
        on_progress=on_progress,
        source_title=document.title,
        source_origin=document.origin,
    )


def generate_from_brief(
    brief: Brief,
    *,
    config: dict[str, Any] | None = None,
    options: GenerateOptions | None = None,
    on_progress: Callable[[str], None] | None = None,
    source_title: str = "",
    source_origin: str | None = None,
) -> GenerateResult:
    """Skip extraction and brief passes when the caller supplies a Brief."""
    settings = config if config is not None else load_config()
    provider = get_provider(resolve_llm_settings(settings))
    return _finish(
        brief,
        provider=provider,
        settings=settings,
        options=options or GenerateOptions(),
        on_progress=on_progress,
        source_title=source_title,
        source_origin=source_origin,
    )


def _finish(
    brief: Brief,
    *,
    provider: LLMProvider,
    settings: dict[str, Any],
    options: GenerateOptions,
    on_progress: Callable[[str], None] | None,
    source_title: str,
    source_origin: str | None,
) -> GenerateResult:
    progress = on_progress or (lambda _message: None)
    design_defaults = resolve_design_settings(settings)
    if options.mode:
        design_defaults["mode"] = options.mode
    render_settings = resolve_render_settings(settings)
    requested = (
        options.candidates
        if options.candidates is not None
        else int(design_defaults.get("candidates") or 1)
    )
    requested = max(1, min(5, requested))
    judge = (
        options.judge
        if options.judge is not None
        else str(design_defaults.get("judge") or "auto")
    ).strip() or "auto"
    measure_enabled = bool(render_settings.get("measure", True))

    warnings: list[str] = []
    router = (
        options.router
        if options.router is not None
        else str(design_defaults.get("router") or "off")
    )
    seed, routing = _seed_from_router(
        brief,
        settings=settings,
        design=design_defaults,
        router=router,
        layout_override=options.layout,
        orientation=options.orientation,
        progress=progress,
        warnings=warnings,
    )
    count = requested
    if count > 1 and not measure_enabled:
        count = 1
        warnings.append(
            "Best-of-N needs render.measure; using one candidate."
        )
    if count > 1 and judge.lower() == "none":
        count = 1
        warnings.append(
            "Best-of-N needs a vision judge; set design.judge to auto or a "
            "provider label, or use one candidate."
        )

    if seed is None and count > 1 and not options.layout:
        seed = _rule_seed(
            brief,
            design=design_defaults,
            orientation=options.orientation,
            density=options.density,
        )

    plans, design_warnings = choose_plans(
        brief,
        provider,
        settings=design_defaults,
        count=count,
        layout=options.layout,
        style=options.style,
        orientation=options.orientation,
        density=options.density,
        on_progress=on_progress,
        seed=seed,
    )
    warnings.extend(design_warnings)

    assets: dict[str, bytes] = {}
    illustration = resolve_illustration_settings(settings)
    if options.illustration_enabled is False:
        illustration["provider"] = "off"
    elif options.illustration_enabled is True:
        illustration["provider"] = "gemini"
    if options.illustration_style:
        from tavola.assets import ILLUSTRATION_STYLES

        chosen = ILLUSTRATION_STYLES.get(options.illustration_style)
        if chosen is None:
            warnings.append(
                f"Unknown illustration style {options.illustration_style!r}; "
                "using the configured style."
            )
        else:
            illustration["preset"] = chosen.id
            illustration["style"] = chosen.prompt
    if options.illustration_direction is not None:
        illustration["direction"] = options.illustration_direction.strip()
    if (
        illustration["provider"] != "off"
        and any(
            plan.layout in {
                "illustrated",
                "illustrated-comparison",
                "illustrated-quote",
                "illustrated-sequence",
                "illustrated-trend",
            }
            for plan in plans
        )
    ):
        progress("creating the hero visual…")
        try:
            image_llm = resolve_llm_settings(
                settings,
                provider_label="gemini",
                global_overrides=False,
            )
            illustrated = next(
                plan
                for plan in plans
                if plan.layout
                in {
                    "illustrated",
                    "illustrated-comparison",
                    "illustrated-quote",
                    "illustrated-sequence",
                    "illustrated-trend",
                }
            )
            assets["hero"] = generate_hero(
                brief,
                illustration=illustration,
                llm=image_llm,
                orientation=illustrated.orientation,
                theme=get_theme(illustrated.style),
            )
        except (ConfigurationError, AssetError) as e:
            warnings.append(f"Illustration skipped: {e}")

    candidates: list[CandidateResult] = []
    failures: list[str] = []
    for index, plan in enumerate(plans, start=1):
        if len(plans) > 1:
            progress(f"rendering candidate {index} of {len(plans)}…")
        else:
            progress("rendering the page…")
        try:
            candidate = _prepare_candidate(
                brief,
                plan,
                settings=render_settings,
                warnings=warnings,
                capture=count > 1,
                assets=assets,
            )
        except GenerateError as e:
            failures.append(f"candidate {index}: {e}")
            warnings.append(f"Candidate {index} was skipped: {e}")
            continue
        candidates.append(candidate)

    if not candidates:
        detail = "; ".join(failures) or "no candidate was produced"
        raise GenerateError(f"No candidate passed the quality gates: {detail}")

    chosen = candidates[0]
    if len(candidates) > 1:
        chosen = _choose_candidate(
            candidates,
            brief,
            provider,
            settings,
            judge,
            progress,
            warnings,
        )

    model = provider.model if provider.model else None
    return GenerateResult(
        brief=brief,
        plan=chosen.plan,
        theme=chosen.theme,
        html=chosen.html,
        quality=chosen.quality,
        warnings=list(dict.fromkeys(warnings)),
        source_title=source_title,
        source_origin=source_origin,
        provider=provider.name,
        model=str(model) if model else None,
        measurements=chosen.measurements,
        candidates=candidates,
        routing=routing,
    )


def _rule_seed(
    brief: Brief,
    *,
    design: dict[str, Any],
    orientation: str | None,
    density: str | None,
) -> DesignPlan | None:
    target_orientation = str(
        orientation or design.get("orientation") or "portrait"
    )
    mode = str(design.get("mode") or "auto")
    ranked = rank_compositions(
        brief, orientation=target_orientation, mode=mode
    )
    if not ranked:
        return None
    plan = DesignPlan(
        layout=ranked[0].layout,
        style=str(design.get("style") or "professional"),
        orientation=target_orientation,  # type: ignore[arg-type]
        density=str(density or design.get("density") or "standard"),  # type: ignore[arg-type]
        rationale="Seeded by the deterministic composition ranking.",
    )
    try:
        return validate_plan(plan, brief)
    except DesignError:
        return None


def _seed_from_router(
    brief: Brief,
    *,
    settings: dict[str, Any],
    design: dict[str, Any],
    router: str,
    layout_override: str | None,
    orientation: str | None,
    progress: Callable[[str], None],
    warnings: list[str],
) -> tuple[DesignPlan | None, dict[str, Any] | None]:
    label = router.strip() or "off"
    if label.lower() in {"off", "none", ""} or layout_override:
        return None, None
    if label.lower() == "auto":
        label = "tev"
    target_orientation = str(orientation or design.get("orientation") or "portrait")
    mode = str(design.get("mode") or "auto")
    candidates = rank_compositions(
        brief, orientation=target_orientation, mode=mode
    )[:4]
    if len(candidates) < 2:
        return None, None

    progress(f"routing with {label}…")
    try:
        router_settings = resolve_llm_settings(
            settings,
            provider_label=label,
            global_overrides=False,
        )
        decision = route_layout(
            brief,
            base_url=str(router_settings["base_url"]),
            model=str(router_settings["model"]),
            candidates=candidates,
            timeout=float(router_settings.get("timeout") or 60),
        )
    except (ConfigurationError, RouterError) as e:
        warnings.append(f"Router {label!r} skipped: {e}")
        return None, {"router": label, "error": str(e)}

    routing = {
        "router": label,
        "model": str(router_settings["model"]),
        "layout": decision.layout,
        "confidence": round(decision.confidence, 3),
        "probability": round(decision.probability, 3),
        "probabilities": decision.probabilities,
        "usage": decision.usage,
        "accepted": decision.probability >= 0.65,
    }
    if decision.probability < 0.65:
        warnings.append(
            f"Router {label!r} was not decisive enough "
            f"({decision.probability:.0%}); used the design model."
        )
        return None, routing

    plan = DesignPlan(
        layout=decision.layout,
        style=str(design.get("style") or "professional"),
        orientation=target_orientation,  # type: ignore[arg-type]
        density=str(design.get("density") or "standard"),  # type: ignore[arg-type]
        rationale=f"Seeded by the {label} router.",
    )
    try:
        validate_plan(plan, brief)
    except DesignError as e:
        warnings.append(f"Router choice was invalid: {e}")
        routing["error"] = str(e)
        routing["accepted"] = False
        return None, routing
    return plan, routing


def _prepare_candidate(
    brief: Brief,
    plan: DesignPlan,
    *,
    settings: dict[str, Any],
    warnings: list[str],
    capture: bool,
    assets: dict[str, bytes] | None = None,
) -> CandidateResult:
    theme = get_theme(plan.style)
    html = render_page(brief, plan, theme, assets=assets)
    quality = check_html(html, brief=brief)
    if not quality.passed:
        detail = "; ".join(issue.message for issue in quality.errors)
        raise GenerateError(f"the static quality gate failed: {detail}")

    measurements: dict[str, Any] | None = None
    screenshot: bytes | None = None
    if settings.get("measure", True):
        measured = _measure(html, plan, warnings, capture=capture)
        if measured is not None:
            quality.issues.extend(measured.issues)
            measurements = measured.metrics
            screenshot = getattr(measured, "screenshot", None)

            if _needs_reflow(measured):
                tight_html = render_page(
                    brief, plan, theme, fit="tight", assets=assets
                )
                tight_quality = check_html(tight_html, brief=brief)
                if tight_quality.passed:
                    tight_measured = _measure(
                        tight_html, plan, warnings, capture=capture
                    )
                    if tight_measured is not None:
                        tight_quality.issues.extend(tight_measured.issues)
                        if tight_quality.passed:
                            html = tight_html
                            quality = tight_quality
                            measurements = tight_measured.metrics
                            screenshot = getattr(tight_measured, "screenshot", None)
                            _add_warning(
                                warnings, "The page was reflowed to fit the viewport."
                            )

        if not quality.passed:
            detail = "; ".join(issue.message for issue in quality.errors)
            raise GenerateError(f"the measured quality gate failed: {detail}")

    return CandidateResult(
        plan=plan,
        theme=theme,
        html=html,
        quality=quality,
        measurements=measurements,
        screenshot=screenshot,
    )


def _choose_candidate(
    candidates: list[CandidateResult],
    brief: Brief,
    provider: LLMProvider,
    settings: dict[str, Any],
    judge: str,
    progress: Callable[[str], None],
    warnings: list[str],
) -> CandidateResult:
    if judge.lower() != "none":
        judge_provider = _judge_provider(settings, judge, provider, warnings)
        if judge_provider is not None:
            missing = any(candidate.screenshot is None for candidate in candidates)
            if missing:
                warnings.append(
                    "Vision scoring skipped: candidate screenshots unavailable."
                )
            else:
                for index, candidate in enumerate(candidates, start=1):
                    progress(f"scoring candidate {index} of {len(candidates)}…")
                    assert candidate.screenshot is not None
                    try:
                        visual = score_page(
                            brief,
                            candidate.plan,
                            candidate.screenshot,
                            judge_provider,
                        )
                    except (LLMError, ValueError) as e:
                        warnings.append(
                            f"Vision scoring failed ({e}); "
                            "kept the first candidate that passed."
                        )
                        return candidates[0]
                    candidate.visual = visual
                    candidate.score = visual.total
                    candidate.score_source = "vision"
                    candidate.reason = visual.reason
                best = max(
                    enumerate(candidates),
                    key=lambda item: (item[1].score or 0.0, -item[0]),
                )
                return best[1]

    warnings.append(
        "Best-of-N ran without vision scoring; kept the first candidate "
        "that passed."
    )
    return candidates[0]


def _judge_provider(
    settings: dict[str, Any],
    judge: str,
    fallback: LLMProvider,
    warnings: list[str],
) -> LLMProvider | None:
    if judge.lower() in {"", "auto"}:
        return fallback
    try:
        judge_settings = resolve_llm_settings(
            settings,
            provider_label=judge,
            global_overrides=False,
        )
        return get_provider(judge_settings)
    except (ConfigurationError, LLMError) as e:
        warnings.append(f"Could not start judge {judge!r}: {e}")
        return None


def _add_warning(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def generate_from_text(
    text: str,
    *,
    title: str = "Pasted text",
    config: dict[str, Any] | None = None,
    options: GenerateOptions | None = None,
) -> GenerateResult:
    """Convenience for the web UI: a pasted block instead of a file or URL."""
    return generate(
        Source(text=clean_text(text), title=title, kind="text"),
        config=config,
        options=options,
    )


def _measure(
    html: str,
    plan: DesignPlan,
    warnings: list[str],
    *,
    capture: bool = False,
) -> MeasureResult | None:
    size = ORIENTATIONS[plan.orientation]
    try:
        return measure_html(
            html,
            width=size[0],
            height=size[1],
            screenshot=capture,
        )
    except MeasureError as e:
        _add_warning(warnings, f"Measured checks skipped: {e}")
        return None


def _needs_reflow(measured: MeasureResult) -> bool:
    codes = {
        issue.code for issue in measured.issues if issue.severity == "error"
    }
    return bool(codes) and codes <= {"overflow", "clipping"}


def slugify(value: str, *, fallback: str = "tavola", limit: int = 60) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return (slug or fallback)[:limit].strip("-") or fallback


def default_filename(result: GenerateResult, suffix: str = ".png") -> str:
    return f"{slugify(result.brief.title)}{suffix}"


def save_result(
    result: GenerateResult,
    output: str | Path | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> SaveResult:
    """Write the artefact and its JSON sidecar. Format comes from the suffix."""
    settings = config if config is not None else load_config()
    suffix = Path(output).suffix.lower() if output else ".png"
    if not suffix:
        output = f"{output}.png"
        suffix = ".png"
    if suffix not in {".png", ".pdf", ".html", ".htm"}:
        raise GenerateError(
            f"Unsupported output format {suffix!r}; use .png, .pdf, or .html."
        )

    target = Path(output) if output else Path(default_filename(result))
    target = target.expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    html_path: Path | None = None
    if suffix in {".html", ".htm"}:
        target.write_text(result.html, encoding="utf-8")
        html_path = target
    elif suffix == ".png":
        from tavola.render.browser import html_to_png

        render_settings = resolve_render_settings(settings)
        html_to_png(
            result.html,
            target,
            width=result.width,
            height=result.height,
            scale=int(render_settings.get("scale") or 2),
        )
    else:
        from tavola.render.browser import html_to_pdf

        html_to_pdf(
            result.html,
            target,
            width=result.width,
            height=result.height,
        )

    sidecar = target.with_suffix(".json")
    sidecar.write_text(_sidecar_json(result, suffix), encoding="utf-8")
    return SaveResult(artefact=target, sidecar=sidecar, html=html_path)


def _sidecar_json(result: GenerateResult, suffix: str) -> str:
    import json

    payload = {
        "schemaVersion": 2,
        "app": "tavola",
        "version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "title": result.source_title,
            "origin": result.source_origin,
        },
        "provider": {"name": result.provider, "model": result.model},
        "brief": result.brief.model_dump(),
        "plan": result.plan.model_dump(),
        "design": {
            "routing": result.routing,
            "candidates": [candidate.sidecar() for candidate in result.candidates],
        },
        "render": {
            "format": suffix.lstrip("."),
            "width": result.width,
            "height": result.height,
        },
        "warnings": result.warnings,
        "quality": {
            "passed": result.quality.passed,
            "issues": [
                {
                    "code": issue.code,
                    "severity": issue.severity,
                    "message": issue.message,
                }
                for issue in result.quality.issues
            ],
            "measurements": result.measurements,
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
