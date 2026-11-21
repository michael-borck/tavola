# Tavola — specification

> *tavola* (Italian): a full-page plate or illustration; also a table.
> The unit of output is one page.

A small, privacy-first tool that turns one source into one well-designed
infographic. Bring your own language model; bring your own server. No account,
no telemetry, no CDN.

---

## 1. Vision

Most "AI infographic" tools are a prompt that fills one HTML template. The
result looks like every other AI demo: three stat cards, four bullets, Tailwind
defaults, a number somewhere in a gradient. NotebookLM looks better because it
makes design decisions per source — structure, density, palette, hierarchy,
illustration — not because it has a better template.

Tavola separates those decisions:

1. **Understand the source** into a typed brief.
2. **Choose a design** from a catalog (layout + style pack + density).
3. **Render deterministically** so text is exact and the result is editable.
4. **Check the result** before it is saved.

The promise: *cleaner than template tools, more accurate than NotebookLM.*

## 2. Principles

1. **One page, one idea.** The artefact is a single frame. No decks, no
   scrolling pages, no notebook app.
2. **The model chooses, the code designs.** Free-form HTML from an LLM is how
   you get average output. The model fills a schema and picks from a catalog;
   every visual decision it makes is bounded by a layout you designed.
3. **Text is sacred.** Numbers, units, names, dates, and caveats are rendered
   by code, never painted by an image model.
4. **Local-first.** Ollama is the default. A cloud key is opt-in. No artefact
   references an external URL.
5. **Progressive surfaces.** The same core powers a CLI, a web UI, and later a
   Tauri desktop app. Each surface is optional.
6. **Fail visibly.** A provider error or an invalid design plan is reported,
   not silently replaced by a placeholder.

## 3. Scope of v0.1 (single source)

In scope:

- One source per run: PDF, DOCX, Markdown, HTML, URL, or plain text.
- Four LLM families: Ollama (native), OpenAI-compatible, Gemini, Anthropic.
- Three passes: brief → design plan → render.
- Twenty-five layouts, six style packs, and six illustration presets.
- Orientations: square, portrait, landscape.
- Output: PNG, PDF, HTML; JSON sidecar with brief + plan.
- CLI and local web UI.
- Static quality gate (self-containment, structure, text budgets).
- Browser quality gate (overflow, clipping, type size, contrast, reflow).

Out of scope for v0.1:

- Multiple sources or a persistent notebook.
- Chat with sources, audio overview, slide decks, mind maps.
- Painterly whole-image mode (planned, M4).
- Editing the artefact in the browser beyond regenerating it.
- Accounts, sync, telemetry, hosted multi-tenancy.

## 4. Pipeline

```
                 ┌──────────────┐
source ─────────►│  extract     │  PDF / DOCX / MD / HTML / URL / text
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                        │  condense    │  map-reduce if over ~40k chars
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                        │  BRIEF       │  title, dek, thesis, claims,
                 └──────┬───────┘  relationships, quote, citations
                        ▼
                 ┌──────────────┐
                        │  DESIGN PLAN │  layout, style, orientation,
                 └──────┬───────┘  density, palette, emphasis
                        ▼
                 ┌──────────────┐
                        │  RENDER      │  HTML + CSS tokens (+ SVG)
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                        │ QUALITY GATE │  static + browser checks
                 └──────┬───────┘
                        ▼
                  PNG · PDF · HTML + JSON sidecar
```

### 4.1 Brief

```python
class Claim:
    text: str            # one tight sentence, <= 140 chars
    value: str | None    # the number as printed, e.g. "42%"
    label: str | None    # what the number measures
    numeric: float | None
    unit: str | None
    source: str | None   # short locator, e.g. "p. 12" or "Fig. 3"

class Relationship:
    kind: Literal["sequence", "comparison", "hierarchy", "proportion", "cause"]
    summary: str
    items: list[str]

class Series:
    name: str
    labels: list[str]   # ordered, 3..12
    values: list[float] # same length as labels
    unit: str | None

class Risk:
    risk: str
    mitigation: str | None

class Brief:
    title: str
    dek: str
    thesis: str
    claims: list[Claim]          # 3..6
    relationships: list[Relationship]  # 0..2
    series: list[Series]         # 0..2, for trend charts
    risks: list[Risk]            # 0..3, stated risk/mitigation pairs
    quote: str | None
    bottom_line: str
    citations: list[str]
    suggested_density: Literal["concise", "standard", "detailed"]
```

Rules given to the model: never invent a number; keep the printed unit; one
claim per idea; cite where possible; choose the relationship that the source
actually supports; only record a series when the source has ordered values.

Validation: Pydantic, then one repair call containing the validation error,
then a hard failure. `--brief file.json` bypasses extraction entirely.

### 4.2 Design plan

```python
class DesignPlan:
    layout: str            # id from the catalog
    style: str             # id from the style packs
    orientation: Literal["square", "portrait", "landscape"]
    density: Literal["concise", "standard", "detailed"]
    palette: list[str]     # optional override, validated as hex
    emphasis: list[int]    # claim indices to feature
    assets: list[AssetPrompt]
    rationale: str
```

The prompt contains the catalog with each layout's id, name, description, data
requirements, claim range, and supported orientations. The model returns JSON
only. Invalid ids are rejected; one retry; then a deterministic heuristic
selects a layout and the CLI reports the fallback.

Overrides: `--layout`, `--style`, `--orientation`, `--density` always win over
the model.

### 4.3 Render

- HTML/CSS is the primary renderer. One page, exact pixel size, no external
  references, no JavaScript.
- Typography scales with the viewport against a fixed baseline, so the same
  layout works in all three orientations.
- Themes are token sets (CSS custom properties), never layout code.
- PNG and PDF use headless Chromium via Playwright at 2× scale by default.
- HTML is always available and is the editable artefact.
- SVG output for diagram-shaped layouts (M2, AntV Infographic).

### 4.4 Quality gate

Static checks:

- exactly one `h1`; non-empty title, dek, and bottom line
- no external references, `@import`, `<script>`, iframes, inline handlers,
  `javascript:` URLs, or unrendered template braces
- no placeholder text (warning)
- title, dek, and bottom-line length budgets (warning)
- claim count and orientation checked by design-plan validation before render
- artefact contains no `http://` or `https://` reference

Measured (browser, `render.measure: true`):

- overflow and clipping per element
- minimum rendered font size (11px)
- contrast ratio (WCAG AA: 4.5:1 normal, 3:1 large)
- orphaned headings (warning)
- one automatic reflow retry when overflow or clipping is the only failure;
  type does not shrink, so the retry cannot create a tiny-type failure

### 4.5 Best-of-N

`design.mode` (`structured`, `illustrated`, or `auto`) chooses the layout
family; `illustration.provider` (`off` or `gemini`) enables a cached, text-free
hero image for illustrated compositions. `design.candidates` (1–5; default 1)
asks for distinct design plans from the
same Brief, renders each, and runs the static and measured gates. When
`design.judge` is `auto` or a provider label, each screenshot is scored by a
vision model on legibility, composition, and hierarchy; the highest weighted
score wins. Candidates that fail a gate are skipped. If the judge or browser is
unavailable, Tavola keeps the first passing candidate and records the reason in
the warnings and sidecar. A judge can be another provider, so a local text
model can write and a cloud vision model can rank.

### 4.6 Decision layers and the composition catalog (planned)

Tavola separates content decisions from visual construction. The model never
places arbitrary boxes or writes HTML; it selects from a bounded catalog, and
deterministic code builds the page.

Planned decision layers:

1. **Content.** A capable model fills the typed `Brief`. Numbers, units, and
   relationships are preserved exactly; this is the fidelity layer.
2. **Validity.** Deterministic rules inspect the Brief: numeric count, units,
   percentage totals, relationships, claim range, and orientation. Invalid
   chart or layout choices are vetoed before rendering.
3. **Routing.** Rules first rank the valid compositions. An optional small
   local classifier (e.g. Tev through Ollama) may choose among the surviving
   compositions or chart types, with a confidence score. Low confidence, an
   unavailable router, or a failing router falls back to the design LLM or the
   heuristic. The router never invents numbers or copy.
4. **Composition.** The selected composition maps to fixed layout modules and
   an ordered slot list: masthead, primary visual, evidence, secondary visual,
   footer. Modules are things such as `kpi-row`, `bar`, `donut`,
   `stacked-bar`, `quote`, `timeline`, and `illustration`. Module
   compatibility is validated. The renderer owns markup and typography.
5. **Ranking.** Best-of-N renders the surviving compositions and a vision model
   ranks legibility, composition, and hierarchy.

The rules layer is implemented in `compose.py`: it checks the Brief's numbers,
units, relationships, claim range, and orientation, then ranks only valid
layouts. The design prompt receives that shortlist. The Tev router is now
implemented through Ollama's `/v1/systemone` decision API; it seeds one
candidate, and the design model supplies the rest. `modules.py` now catalogs
the first reusable fragments (`kpi-tiles`, `insight-rail`). The AntV renderer
family is also live for sequence, hierarchy, and comparison diagrams. The broader module
catalog remains planned. The router's input is still a narrow classifier over
the Brief:

```json
{
  "archetype": "dashboard | editorial | timeline | comparison | narrative",
  "chart": "none | bar | donut | stacked-bar | line",
  "density": "concise | standard | detailed",
  "confidence": 0.0
}
```

It is enabled per directory with `design.router: tev` (or `--router tev`).
A choice is accepted only when its top probability is at least 0.65; otherwise
Tavola keeps the design model. Config also accepts `off`, `auto`, or another
provider label. The router is a convenience, not a source of truth: hard data
constraints always win.

The component catalog is the larger visual unlock. A dashboard composition can
combine a KPI row, one dominant chart, and one insight column; an editorial
composition can combine a quote, a diagram, and supporting claims. Illustration
generation is implemented as a text-free hero layer for the illustrated
compositions; more illustration styles and richer asset modules remain future
work.

## 5. BYOK and LLM providers

| id | Transport | Structured output | Notes |
|---|---|---|---|
| `ollama` | `POST /api/chat` | `format` = JSON Schema | default; local |
| `openai-compatible` | `POST /v1/chat/completions` | `response_format` json_schema → json_object → plain | OpenAI, LM Studio, llama.cpp, OpenRouter |
| `gemini` | `POST /v1beta/models/{model}:generateContent` | `responseMimeType` + `responseSchema` | schema refs resolved to a Gemini subset |
| `anthropic` | `POST /v1/messages` | forced tool use | one tool named `emit_result` |

All four transports can attach PNG screenshots for best-of-N when the selected
model supports vision. Every provider raises `LLMError` with a readable message. Models can be listed
with `tavola models`. Keys live in `~/.tavola.yaml` or the environment, are
never exposed to the browser by the web UI, and are sent only to the endpoint
the user configured.

## 6. Surfaces

### CLI

`tavola SOURCE` is the default command. Subcommands: `layouts`, `styles`,
`formats`, `models`, `health`, `serve`. `--init-config` writes a template and
`--brief FILE` skips extraction.

### Web UI (`tavola serve`)

One page: paste text or give a URL, choose a style, orientation, density, and
optionally a layout, then Generate. Preview, download the PNG, and download the
brief-and-plan JSON. The gallery is in memory; each run also writes its PNG and
sidecar to `serve.out_dir`. FastAPI plus a self-contained HTML page with no
CDN. Binds `127.0.0.1` and refuses non-loopback hosts in v0.1; authenticated
remote mode comes later.

### Desktop (M3)

Tauri v2, OS webview, `uv`-bootstrapped private runtime, sidecar on a random
localhost port, first-run Settings sheet that writes `~/.tavola.yaml`. Same
pattern as Limn and Canturía. `v0.1.1` ships signed/notarized macOS and unsigned
Windows/Linux installers from GitHub Releases, and the wheel is on PyPI.

## 7. Config

Layers, later wins:

1. built-in defaults
2. `~/.tavola.yaml`
3. `./tavola.yaml` or `--config FILE`
4. CLI flags / environment

```yaml
llm: ollama
llms:
  ollama: { base_url: http://127.0.0.1:11434, model: qwen3.5:4b, think: false, timeout: 300 }
  openai-compatible:
    base_url: https://api.openai.com/v1
    model: gpt-4o-mini
    api_key: "${OPENAI_API_KEY}"
    timeout: 180
  gemini: { model: gemini-2.5-flash, api_key: "${GEMINI_API_KEY}" }
  anthropic: { model: claude-sonnet-4-5, api_key: "${ANTHROPIC_API_KEY}" }
design:
  mode: structured
  layout: auto
  style: professional
  orientation: portrait
  density: standard
  candidates: 1
  judge: auto
  router: off
illustration:
  provider: off
  model: gemini-2.5-flash-image
  preset: editorial
  direction: ""
render:
  scale: 2
serve:
  host: 127.0.0.1
  port: 5827
  out_dir: ~/Pictures/Tavola
```

Environment: `TAVOLA_LLM`, `TAVOLA_MODEL`, `TAVOLA_BASE_URL`,
`TAVOLA_API_KEY`, `TAVOLA_STYLE`, `TAVOLA_LAYOUT`, `TAVOLA_ORIENTATION`,
`TAVOLA_DENSITY`, `TAVOLA_MODE`, `TAVOLA_CANDIDATES`, `TAVOLA_JUDGE`,
`TAVOLA_ROUTER`, `TAVOLA_HOST`,
`TAVOLA_PORT`, `TAVOLA_OUT_DIR`,
`TAVOLA_OLLAMA_URL`, `TAVOLA_OLLAMA_MODEL`, `TAVOLA_OPENAI_URL`,
`TAVOLA_OPENAI_MODEL`, `TAVOLA_OPENAI_API_KEY`, `TAVOLA_GEMINI_MODEL`,
`TAVOLA_GEMINI_API_KEY`, `TAVOLA_ANTHROPIC_MODEL`,
`TAVOLA_ANTHROPIC_API_KEY`.

## 8. Storage and privacy

- The source is read locally. Condensed text and the brief go to the configured
  LLM. With `design.candidates` above 1, rendered candidate PNGs also go to the
  judge provider; `design.judge` can name a different provider.
- The web gallery is in memory and dies with the process.
- Generate writes the image plus `<name>.json` into `serve.out_dir`; the
  gallery listing lives in memory.
- No artefact references an external host. Bundled Inter, Source Serif 4, and
  Caveat subsets are embedded as data URIs, with system font fallbacks.
- No accounts, no telemetry, no analytics.

## 9. Architecture

```
tavola/
  config.py            layered config + env expansion
  content.py           source extraction, cleaning, condensing
  brief.py             Brief schema, prompt, validation, repair
  design.py            DesignPlan schema, catalog prompt, heuristic fallback
  compose.py           deterministic composition features and candidate ranking
  assets.py            cached text-free hero asset generation
  modules.py           reusable module catalog (KPI tiles, insight rail)
  icons.py             bundled Lucide icon selection
  router.py            optional Tev/System One layout router
  judge.py             vision scoring for best-of-N candidates
  antv.py              bundled AntV Infographic -> static SVG adapter
  vendor/antv/         local UMD bundle + MIT licence
  layouts/             one module per layout + registry + shared parts
  themes/              token packs + registry + bundled OFL fonts
  render/html.py       page builder, base CSS, theme tokens
  render/browser.py    Playwright PNG/PDF
  quality.py           static quality gate
  measure.py           browser quality gate (overflow, type, contrast)
  core.py              pipeline orchestration and file output
  cli.py               Typer CLI
  serve.py             FastAPI app factory
  serve_page.html      self-contained web UI
desktop/               Tauri v2 shell (M3)
tests/
docs/
```

Dependencies: Typer, Rich, PyYAML, Pydantic, Requests, pypdf, BeautifulSoup.
Playwright behind `[render]`, FastAPI/uvicorn behind `[serve]`, python-docx
behind `[docx]`.

## 10. Milestones

1. **M0 — Scaffold (this commit).** Package, config, providers, content
   extraction, brief, design plan, 25 layouts, 6 themes, renderer, quality gate,
   CLI, web UI, tests, docs.
2. **M1 — Measured quality (shipped).** Browser overflow/contrast/type-size
   checks, one reflow retry, best-of-3 vision scoring, and bundled OFL fonts.
3. **M2 — Diagram engine (started).** Native `bar-share`, `donut-share`,
   `dashboard`, `stacked-share`, `trend`, `trend-dashboard`, `hierarchy`, and
   `poster`; next AntV Infographic for
   timeline/process/hierarchy/comparison, SVG export, a composition/module
   catalog, and an optional small router (SPEC §4.6).
4. **M3 — Desktop.** Tauri shell, uv runtime, Settings sheet, CI installers,
   landing page.
5. **M4 — Illustrated assets.** More visual styles, spot-icon modules, and
   optional painterly mode; text always stays deterministic.
6. **M5 — Notebooks (only if earned).** Multiple sources, saved projects,
   citation pane. Not before the artefact is good.

## 11. Non-goals

- A general notebook or research assistant.
- A Canva competitor or a freeform editor.
- A model host. Tavola calls the model you point it at.
- Hosted multi-tenant SaaS.
- Pixel-for-pixel imitation of NotebookLM. The target is a better *artefact*,
  not a copy of its idiosyncratic illustration style.
