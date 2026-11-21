# Tavola — agent handover / working notes

Read `SPEC.md` before writing code. Read `docs/LAYOUT-CONTRACT.md` before
adding or changing a layout or style pack. This file is the quick orientation.

## What Tavola is

A small, privacy-first tool that turns **one source** into **one well-designed
infographic**. The output is a PNG, a PDF, or editable HTML, plus a JSON
sidecar recording the brief and design plan that produced it.

The product is the artefact, not a notebook app. The model chooses a layout
from a catalog and fills a typed brief; Python does the layout and typography.
That is the whole idea, and it is why the output is not another Tailwind card
grid.

## Current status

**0.1.0 — M1 and M2 complete; M3 in progress.** Package, layered config, four text/vision LLM
providers with structured output, content extraction, brief, design plan,
twenty-five layouts, six style packs, bundled OFL fonts, deterministic HTML
renderer, Playwright PNG/PDF, static quality gate, measured browser gate with
one reflow retry, best-of-3 vision scoring, an optional Tev System One router, Typer CLI,
FastAPI web UI, tests, docs, research notes. `./tavola.yaml` uses
`gemini-2.5-flash` for brief, design, and judge with three candidates and Tev
routing; `GEMINI_API_KEY` is read directly. Ollama remains the package default
and offline fallback.

Verified: 218 tests pass; ruff and basedpyright clean; wheel builds with
`serve_page.html` and the font files included, and passes `twine check`. All 450
style × layout × orientation combinations pass the measured gate (11px type
floor, WCAG AA contrast, no overflow or clipping) with bundled fonts.
Best-of-3 is opt-in: `design.candidates: 3` or `--candidates 3`; without a
vision model it keeps the first passing candidate and records a warning. The
full sweep is one-off, not in CI.

Tauri desktop shell and landing page are built in the working tree; the first
public release, signed/notarized installers, and deployment are not done.

## Run it

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tavola"
uv sync --all-extras
uv run --no-sync ruff check src tests
uv run --no-sync basedpyright
uv run --no-sync pytest

uv run tavola --init-config
uv run tavola layouts
uv run tavola styles
uv run tavola formats
uv run tavola health --connect
uv run tavola report.pdf -o page.png
uv run tavola --brief brief.json -o page.png
uv run tavola serve
```

The repo lives on an exFAT drive. Keep the venv on the internal disk (above);
`uv sync` with a local `.venv` fails on `._*` AppleDouble files in wheels, the
same gotcha as Limn and Canturía.

## Architecture

```
config.py      defaults < ~/.tavola.yaml < ./tavola.yaml < flags, ${VAR}
content.py     PDF/MD/HTML/URL/DOCX extraction, cleaning, map-reduce condense
llm/           base protocol + ollama, openai-compatible, gemini, anthropic
brief.py       Brief schema, prompt, validation, one repair, hard fail
design.py      DesignPlan schema, catalog prompt, candidate variants, heuristic
compose.py     Brief features + deterministic valid-layout ranking
assets.py      cached Gemini text-free hero image generation
icons.py      bundled Lucide icon selection for KPI/stat modules
modules.py     reusable KPI tiles and insight-rail module catalog
router.py      optional Tev/System One layout router
judge.py       vision scoring for best-of-N pages
antv.py        bundled AntV Infographic -> static SVG adapter
vendor/antv/   local UMD bundle + MIT licence
layouts/       Layout registry, _parts/_charts helpers, one module per layout
themes/        Theme token packs, registry, fonts/ + embedded OFL faces
render/html.py page builder, BASE_CSS, theme CSS, orientation classes
render/browser.py Playwright PNG/PDF
quality.py     static checks + browser checks live in measure.py
measure.py     overflow, clipping, type size, contrast, one reflow retry
core.py        pipeline + saving + sidecar
cli.py         Typer, DefaultCommandGroup (`tavola SOURCE` works)
serve.py       FastAPI app factory + in-memory gallery
```

Flow: `read_source → condense → extract_brief → choose_plans → theme →
render → quality/measure → judge → save`. Each stage raises a typed error; the
CLI reports it and exits non-zero. Fallbacks (design heuristic, unavailable
vision judge) are reported as warnings and recorded in the sidecar.

## Decisions already made

- **Single source.** Multi-source notebooks are M5, and only if the artefact
  earns it.
- **The model never writes HTML.** It fills `Brief` and selects from a bounded
  composition catalog; deterministic code builds markup. Free-form markup is
  how the old scripts became average.
- **Graphic decisions are layered.** Rules validate the Brief, a bounded
  catalog defines compositions/modules, and an optional small local router
  (Tev is the first experiment) may choose among valid candidates. Gemini
  remains the content writer and vision judge. See SPEC §4.6.
- **HTML/CSS + SVG is the renderer.** Text must be exact, editable, and crisp.
  Image models are for text-free assets only.
- **No CDN, no external font URLs, no external references in output.** The
  quality gate enforces this.
- **Ollama is the default LLM.** Cloud keys are opt-in and never exposed to the
  browser.
- **Standalone**, not a dependency on Limn, Canturía, or Presenton. Reuse the
  provider pattern, not the package. A shared BYOK library can come later if it
  clearly pays off.
- **AntV Infographic** is a second renderer family for explicit diagram
  layouts; native CSS/SVG remains the default and auto-selection excludes AntV
  until its templates are quality-competitive.
- **One screen, one Generate** in the web UI, like Limn and Canturía.

## Next milestones

1. **M1 — measured quality.** Shipped: browser overflow, min font, contrast,
   orphan checks, one reflow retry, best-of-3 vision scoring, bundled OFL
   fonts.
2. **M2 — diagram engine (started).** Native `bar-share` and `donut-share`;
   next AntV via a bundled local page and Playwright, SVG export, and the
   composition/module catalog. `compose.py` ranks valid layouts and
   `router.py` lets Tev seed a best-of-N candidate (SPEC §4.6).
3. **M3 — desktop (in progress).** Tauri v2 shell, uv-bootstrapped sidecar,
   first-run provider sheet, unsigned CI installers, landing page. Signing,
   notarization, and public release assets remain.
4. **M4 — illustrated mode.** Text-free generated assets via Limn providers,
   composited; optional painterly image-model mode.
5. **M5 — notebooks, only if earned.**

## Adding things

- **A layout:** `docs/LAYOUT-CONTRACT.md` §6. Pure render, classes in
  `BASE_CSS`, contract test.
- **A style pack:** same doc §7. Tokens only, contrast checked, bundled OFL
  pair with system fallbacks.
- **An LLM provider:** implement `LLMProvider.complete` (and `models`), map
  structured output as best the backend allows, register it in
  `tavola/llm/__init__.py`, add it to the config template and README.
- **A source type:** extend `tavola/content.py`; keep optional deps in extras.

## Reference

- Limn: `../limn` — closest sibling. Config layering, provider modules, serve
  page, Tauri sidecar, landing page.
- Canturía: `../song-gen` — closest sibling for BYOK sub-providers
  (`lyricists/` is the pattern for `llms/`).
- Research: `docs/research/2026-11-infographic-landscape.md`.
- NotebookLM/Gemini Notebook benchmark: `benchmarks/gemini-notebook/`.
- Open CoDesign: `../cloned-repos/open-codesign` — reference for token tweaks,
  region comments, and versioned artefacts; not a runtime dependency.
- AntV: <https://github.com/antvis/Infographic>
- Presenton template contract: <https://docs.presenton.ai/creating-custom-presentation-templates>
