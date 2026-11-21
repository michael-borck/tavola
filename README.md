# Tavola

**Sources into a single, well-designed page.**

Tavola turns one document into one infographic: a PNG, a PDF, or editable
HTML. It runs on your machine, uses the language model you point it at
(Ollama by default, or any OpenAI-compatible endpoint), and never sends your
source anywhere else.

No account, no telemetry, no CDN, no hosted service.

```
source.pdf ──► brief ──► design plan ──► HTML/CSS ──► PNG · PDF · HTML
```

Tavola is the artefact half of a "NotebookLM for one page": it cares about
the visual result, not about being a notebook app.

## Why it looks better than a prompt-and-fill script

One prompt that returns a title, three stats and four bullets produces a
template, not a design. Tavola separates four decisions:

1. **Brief** — typed facts, claims, numbers, citations, and the *relationship*
   between them (sequence, comparison, hierarchy, proportion).
2. **Design plan** — the model chooses a layout from a catalog and a style pack;
   it does not write HTML.
3. **Render** — deterministic, local HTML/CSS. Text is always exact; SVG
   export is M2.
4. **Quality gate** — static checks for self-contained output and text budgets,
   then browser checks for overflow, clipping, tiny type, and contrast, plus
   optional best-of-3 vision scoring.

25 layouts × 6 style packs is 150 looks that share one renderer. See
[docs/LAYOUT-CONTRACT.md](docs/LAYOUT-CONTRACT.md).

## Install

The desktop builds are attached to GitHub Releases; macOS and Windows builds
are unsigned for now. There is no PyPI release yet, so the wheel is also on the
release page.

From a checkout:

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tavola"
uv sync --all-extras
uv run tavola --init-config
```

For PNG and PDF export, install Playwright's Chromium:
`uv run playwright install chromium`.

For development on this machine (the repo lives on exFAT, so keep the venv on
the internal disk):

```bash
export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tavola"
uv sync --all-extras
uv run --no-sync ruff check src tests
uv run --no-sync basedpyright
uv run --no-sync pytest
```

## Configure

Layered, later wins: defaults → `~/.tavola.yaml` → `./tavola.yaml` → flags.
Secrets are `${VAR}` references, so no plaintext keys live in the file.

```bash
tavola --init-config
```

```yaml
llm: ollama

# For the quality baseline used in this checkout:
#   llm: gemini
#   model: gemini-2.5-flash
#   export GEMINI_API_KEY=...
#   design.candidates: 3
#   design.judge: gemini
#   design.router: tev

llms:
  ollama:                       # local, no key, the default
    base_url: http://127.0.0.1:11434
    model: qwen3.5:4b
    think: false                # reasoning models otherwise spend the budget thinking

  openai-compatible:            # OpenAI, LM Studio, llama.cpp, OpenRouter
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
    api_key: "${OPENAI_API_KEY}"

  gemini:
    model: gemini-2.5-flash
    # api_key: "${GEMINI_API_KEY}"  # or set GEMINI_API_KEY

  anthropic:
    model: claude-sonnet-4-5
    api_key: "${ANTHROPIC_API_KEY}"

design:
  mode: structured              # structured | illustrated | auto
  layout: auto                  # or a layout id from `tavola layouts`
  style: professional           # professional | scientific | editorial | sketch
  orientation: portrait         # square | portrait | landscape
  density: standard             # concise | standard | detailed
  candidates: 1                 # 3 = best-of-3 with a vision judge
  judge: auto                   # auto | none | a provider label
  router: off                   # off | auto | tev (local System One router)

illustration:
  provider: off                 # off | gemini text-free hero art
  model: gemini-2.5-flash-image
  preset: editorial             # editorial | clay | sketch | minimal | papercut | cinematic
  direction: ""                 # optional; text inside images stays forbidden

render:
  measure: true                 # browser checks before saving
```

## CLI

```bash
# The default command: one source in, one infographic out
tavola report.pdf
tavola notes.md -o page.png --style editorial --orientation square

# Diagram-shaped sources pick their own layout
tavola roadmap.txt --layout timeline --density concise

# Best-of-3 with a vision judge
tavola report.pdf --candidates 3 --judge gemini

# Write the editable artefact instead of a PNG
tavola paper.pdf -o paper.html

# Skip extraction and design from a saved Brief
tavola --brief brief.json -o page.png

# Inspect the catalog and the environment
tavola layouts
tavola styles
tavola formats
tavola models
tavola health --connect

# Web UI
tavola serve
```

Every artefact gets a versioned JSON sidecar next to it with the brief, the design
plan, candidate scores, the provider, the warnings, and the render size — enough to
reproduce or edit the page.

## How the three passes work

**1. Brief.** The source is extracted (PDF, DOCX, Markdown, HTML, URL, text),
condensed with map-reduce when it is long, then converted into a `Brief`:
title, dek, one-sentence thesis, 3–6 claims (value, unit, source), 0–2
relationships, optional ordered series, a quote, citations. The relationship is
what lets a timeline be a timeline instead of a pile of cards.

**2. Design plan.** The model sees the brief and a catalog of layouts and style
packs. It returns a `DesignPlan`: layout id, style id, orientation, density,
optional palette, emphasis, and asset prompts. Invalid ids are rejected and the
model is asked once more; after that a deterministic heuristic picks a sensible
layout with a warning. Set `design.candidates: 3` or pass `--candidates 3` to
render three different plans, measure each, and let a vision model score
legibility, composition, and hierarchy. Without vision support, Tavola keeps
the first candidate that passed and reports why.

**3. Render.** Python builds the HTML from the chosen layout and theme tokens.
No external CSS, no JavaScript, no network requests: Inter, Source Serif 4, and
Caveat are embedded as latin-subset WOFF2 data URIs with system fallbacks. PNG
and PDF go through headless Chromium; the HTML stays editable. SVG export is M2.

## Layouts

| id | Best for | Needs |
|---|---|---|
| `hero-stat` | one headline number with context | a numeric claim |
| `bar-share` | parts of a whole or comparable figures | 3+ numeric claims |
| `donut-share` | parts of one whole with a legend | 3+ numeric claims |
| `dashboard` | a chart with a short insight rail | 3+ comparable numbers + a text claim |
| `stacked-share` | parts of a whole as one stacked bar | 3+ comparable numbers |
| `trend` | change over time as a line chart | an ordered series |
| `trend-dashboard` | KPI tiles plus a line chart and insight rail | an ordered series |
| `hierarchy` | a root with child nodes | a hierarchy relationship |
| `grouped-bars` | two aligned series as bars | two series with shared labels |
| `quadrant` | four competing priorities | four claims |
| `illustrated-comparison` | illustrated hero with two sides | a comparison relationship |
| `illustrated-quote` | illustrated hero with a quote | a quote or strong thesis |
| `illustrated` | an illustrated hero, thesis, and stat strip | mixed numbers and narrative |
| `illustrated-sequence` | hero art, KPI tiles, and a step flow | a sequence relationship |
| `illustrated-trend` | hero art, KPI tiles, and a line chart | an ordered series |
| `poster` | a large quote or thesis with abstract geometry | a strong quote or argument |
| `antv-comparison` | an automatic two-sided diagram | a comparison relationship |
| `antv-sequence` | an automatic horizontal sequence diagram | a sequence relationship |
| `antv-hierarchy` | an automatic tree diagram | a hierarchy relationship |
| `stat-row` | 3–4 comparable figures | 3+ numeric claims |
| `timeline` | things that happened in order | a sequence or ordered claims |
| `process` | how something works | a sequence or ordered claims |
| `comparison` | A vs B, before/after | a `comparison` relationship |
| `statement` | a strong quote or argument | a quote or thesis |
| `bento` | mixed evidence, 4–6 claims | 4+ claims |

Style packs: `professional`, `scientific`, `editorial`, `sketch`, `noir`,
`warm`. They change
tokens (colour, type, radius, texture), never structure. Bundled fonts:
Inter, Source Serif 4, and Caveat (SIL OFL).

Orientations: `square` 1080×1080, `portrait` 1080×1350, `landscape` 1600×900.

## Render modes

- **Structured** *(v0.1)* — local HTML/CSS, exact text, editable in a browser.
- **Illustrated** *(shipped, opt-in)* — a text-free generated hero image with
  exact native text, KPI tiles, and charts composed on top.
- **Painterly** *(planned, opt-in)* — a whole poster from an image model, with
  the deterministic renderer available for text correction.

## Privacy

- Ollama runs locally. A cloud provider is used only if you configure one, with
  your key, and only the source text and brief are sent. Best-of-N is opt-in;
  it also sends the rendered candidate images to the judge provider, which can
  be the same local model or a different, explicitly configured one.
- The web UI offers mode, theme, visual style, illustration on/off, art direction, format, and density. It keeps its gallery in memory. Generate writes the PNG and sidecar
  into `serve.out_dir` (`~/Pictures/Tavola` by default).
- Nothing is logged, telegraphed, or phoned home. The artefact has no external
  references.

## Desktop

A Tauri v2 shell wraps a `uv`-bootstrapped private runtime and the local
`tavola serve` process, using the same pattern as
[Limn](https://github.com/michael-borck/limn) and
[Canturía](https://github.com/michael-borck/canturia). Unsigned installers
come from GitHub Releases; see `desktop/README.md`.

## License

MIT.
