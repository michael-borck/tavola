# Layout catalog contract

This document is the interface between **content** (what the source says) and
**design** (how one page says it). It exists so that adding a look never means
asking the model to write HTML, and so that every look is testable.

Read this before adding a layout or a style pack.

---

## 1. Why a catalog

A single prompt that returns "title, 3 stats, 4 bullets, HTML" produces a
template. The model has no vocabulary for structure, so every source gets the
same structure.

The catalog gives the model a **bounded vocabulary**:

- It chooses a *layout* by id from a list with descriptions and requirements.
- It chooses a *style pack* by id from a list of token sets.
- It fills the **Brief** schema, which every layout understands.
- It never writes markup, CSS, or arbitrary HTML.

Consequences:

- A bad design decision is a wrong id, which is detectable and recoverable.
- Every artefact is reproducible from `(brief, plan, theme)`.
- The visual quality is your design work, not the model's guesswork.
- Adding a look is a code change with a test, not a prompt tweak.

---

## 2. The four objects

```
Brief ──┐
        ├──► LayoutContext ──► Layout.render() ──► inner HTML
DesignPlan ─┤
        │
Theme ──┘
```

### 2.1 `Brief` (`tavola/brief.py`)

The only content object a layout may read. Defined with Pydantic so the model's
output is validated before any rendering happens.

| Field | Type | Notes |
|---|---|---|
| `title` | `str` | punchy, ≤ 90 chars recommended |
| `dek` | `str` | one sentence of context |
| `thesis` | `str` | the single argument of the page |
| `claims` | `list[Claim]` | 3–6, the evidence |
| `relationships` | `list[Relationship]` | 0–2, the structure |
| `series` | `list[Series]` | 0–2, ordered values for trend charts |
| `risks` | `list[Risk]` | 0–3, stated risk/mitigation pairs |
| `quote` | `str \| None` | a line worth setting large |
| `bottom_line` | `str` | the takeaway, always rendered in the footer |
| `citations` | `list[str]` | short locators, not full references |
| `suggested_density` | `concise \| standard \| detailed` | a hint, not a command |

`Claim`:

| Field | Type | Notes |
|---|---|---|
| `text` | `str` | one idea, ≤ 140 chars recommended |
| `value` | `str \| None` | the number **as printed**, e.g. `"3.4×"` |
| `label` | `str \| None` | what the number measures |
| `numeric` | `float \| None` | machine-readable, for charts and ordering |
| `unit` | `str \| None` | `"%"`, `"USD"`, `"years"` |
| `source` | `str \| None` | `"p. 12"`, `"Fig. 3"`, `"Interview"` |

`Series`:

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | short series name |
| `labels` | `list[str]` | ordered 3–12 x labels |
| `values` | `list[float]` | same length as labels |
| `unit` | `str \| None` | `"%"`, `"kWh"`, `"USD"` |

`Risk`:

| Field | Type | Notes |
|---|---|---|
| `risk` | `str` | a concrete risk from the source |
| `mitigation` | `str \| None` | the stated mitigation |

`Relationship`:

| Field | Type | Notes |
|---|---|---|
| `kind` | `sequence \| comparison \| hierarchy \| proportion \| cause` | what the source supports |
| `summary` | `str` | one line describing the relation |
| `items` | `list[str]` | ordered when `kind == sequence` |

**Invariants**

- A claim with `value` must also have `label`.
- `numeric` is optional and never invented; it is a convenience.
- A `sequence` relationship has 3–6 items.
- A `comparison` relationship has exactly 2 items.
- A `hierarchy` relationship has one root as `items[0]` and 2–5 children.
- A `proportion` relationship's items are labels only; the values are in
  claims with the same labels.
- A `Series` has equal-length `labels` and `values`.

### 2.2 `DesignPlan` (`tavola/design.py`)

| Field | Type | Notes |
|---|---|---|
| `layout` | `str` | must exist in the catalog |
| `style` | `str` | must exist in the theme registry |
| `orientation` | `square \| portrait \| landscape` | must be supported by layout |
| `density` | `concise \| standard \| detailed` | content budget |
| `palette` | `list[str]` | optional hex overrides, 1–5 |
| `emphasis` | `list[int]` | claim indices to feature, validated in range |
| `assets` | `list[AssetPrompt]` | reserved for M4, empty in v0.1 |
| `rationale` | `str` | one line, for the sidecar and debugging |

**Invariants**

- `layout` and `style` are exact registry ids, never display names.
- `orientation` is checked against `Layout.orientations`.
- `emphasis` indices are unique and in `range(len(brief.claims))`.
- A palette entry matches `^#[0-9a-fA-F]{6}$`.
- `assets` may be empty; v0.1 renderers ignore them.

### 2.3 `Layout` (`tavola/layouts/base.py`)

```python
@dataclass(frozen=True)
class Layout:
    id: str
    name: str
    description: str          # written for the model, one line
    needs: tuple[str, ...]    # "numeric", "sequence", "comparison", ...
    min_claims: int
    max_claims: int
    orientations: tuple[str, ...]
    render: Callable[[LayoutContext], str]
    family: str = "structured"  # structured | illustrated | diagram
```

`needs` is a controlled vocabulary. The catalog prompt and the heuristic
fallback both use it.

| token | meaning |
|---|---|
| `numeric` | at least one claim with a printed `value` |
| `multi_numeric` | at least 3 claims with a printed `value` |
| `chartable` | at least 3 numeric claims that share a unit, or a proportion |
| `series` | at least one ordered series with labels and values |
| `multi_series` | at least two ordered series with labels and values |
| `sources` | at least two claims with a source locator |
| `sequence` | a `sequence` relationship, or claims that read as steps |
| `comparison` | a `comparison` relationship with exactly 2 items |
| `hierarchy` | a `hierarchy` relationship |
| `quote` | a `quote` or a usable `thesis` |
| `many_claims` | 5–6 claims available |

**Layout invariants**

- `id` is lowercase kebab-case and stable across releases.
- `description` is one sentence, ≤ 120 chars, and says *when to use it*.
- `min_claims <= max_claims`.
- `orientations` is a non-empty subset of the three known orientations.
- `render` is pure: same context in, same HTML out. No network, no clock, no
  randomness, no filesystem.
- `render` never reads fields other than `ctx.brief`, `ctx.plan`, `ctx.theme`,
  and `ctx.size`.

### 2.4 `Theme` (`tavola/themes/base.py`)

A style pack is **tokens only**, emitted as CSS custom properties. It cannot
change structure, order, or copy.

| Token group | Fields |
|---|---|
| Colour | `bg`, `surface`, `surface_alt`, `ink`, `muted`, `accent`, `accent_ink`, `border` |
| Charts | `chart_colors` (up to five CSS colours) |
| Shape | `radius`, `shadow` |
| Type | `font_display`, `font_body` |
| Detail | `label_tracking`, `texture` |

**Composition modules**

Layouts may compose reusable modules from `tavola/modules.py`. A module is a
named fragment with a small `needs` contract and a pure render function. The
first catalog entries are `kpi-tiles` and `insight-rail`; chart modules remain
layout-owned until their data contracts settle.

**Theme invariants**

- Every colour is a CSS colour literal, no external references.
- `ink` on `bg` and `ink` on `surface` meet WCAG AA for body text (4.5:1).
- `accent_ink` is readable on `accent`.
- `chart_colors` are CSS colour literals; charts use them in order, falling
  back to `accent` when a theme defines none.
- Fonts name one of the bundled OFL families first (Inter, Source Serif 4,
  Caveat), with a system fallback for non-latin glyphs. The renderer embeds
  only the families the theme names.
- `texture` is one of `none`, `grain`, `grid`.
- No token contains `url(` with an external origin.

---

## 3. Rendering contract

### 3.1 Document shape

`tavola/render/html.py` owns the outer document. A layout returns only the
inner body.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>…</title>
  <style>/* base CSS + theme tokens */</style>
</head>
<body class="orientation-portrait density-standard">
  <div class="poster" data-layout="hero-stat" data-theme="professional">
    <header class="masthead">
      <p class="eyebrow">…</p>
      <h1 class="title">…</h1>
      <p class="dek">…</p>
    </header>
    <main class="body">
      <!-- Layout.render(ctx) goes here -->
    </main>
    <footer class="colophon">
      <p class="bottom-line">…</p>
      <p class="citations">…</p>
    </footer>
  </div>
</body>
</html>
```

The masthead and footer are shared. Layouts do not render the title, the dek,
the bottom line, or citations; doing so would duplicate them.

### 3.2 Size and scaling

The page is rendered at an exact viewport:

| orientation | pixels | aspect |
|---|---|---|
| `square` | 1080 × 1080 | 1:1 |
| `portrait` | 1080 × 1350 | 4:5 |
| `landscape` | 1600 × 900 | 16:9 |

CSS sets:

```css
html { font-size: calc(min(100vw / 67.5, 100vh / 56.25)); }
```

At 1080px that is 16px; every size in a layout is expressed in `rem`, so the
same markup scales across orientations. Layouts must not use `px` for type,
padding, or gaps.

The body class carries `orientation-*` and `density-*` so a layout can adapt
its grid (for example, a horizontal process becomes vertical in portrait)
without changing its markup contract.

### 3.3 Class vocabulary

Layouts may only use classes defined in the base CSS or in exported helpers.
Shared parts live in `tavola/layouts/_parts.py`:

- `eyebrow`, `title`, `dek` — owned by the page builder
- `thesis`
- `claim-list`, `claim`, `claim-text`, `claim-source`
- `bar-share`, `bar-list`, `bar-row`, `bar-meta`, `bar-label`, `bar-value`,
  `bar-track`, `bar-fill`, `bar-note`
- `donut-share`, `donut-body`, `donut-figure`, `donut-svg`, `donut-track`,
  `donut-seg`, `donut-center`, `donut-legend`, `donut-swatch`
- `dashboard`, `dash-main`, `dash-bars`, `dash-donut`, `dash-rail`,
  `dash-thesis`, `dash-notes`, `dash-note`, `dash-note-index`
- `stacked-share`, `stacked-figure`, `stacked-bar`, `stacked-seg`,
  `stacked-scale`, `stacked-legend`, `stacked-row`, `stacked-swatch`,
  `stacked-label`, `stacked-value`, `stacked-percent`
- `trend`, `trend-figure`, `trend-plot`, `trend-canvas`, `trend-svg`,
  `trend-grid`, `trend-line`, `trend-line-2`, `trend-area`, `trend-dot`,
  `trend-dot-series-2`, `trend-x`, `trend-legend`, `trend-note`
- `trend-dashboard`, `td-main`, `td-kpis`, `td-kpi`
- `hierarchy`, `tree`, `tree-root`, `tree-trunk`, `tree-children`,
  `tree-child`, `tree-child-index`
- `antv-layout`, `antv-main`, `antv-figure`, `antv-compare-head` (static SVG
  from the bundled AntV adapter)
- `kpi-icon`, `kpi-svg` (bundled Lucide icons inside KPI tiles)
- `evidence-table` (cited claims as a compact table)
- `illustrated`, `illustrated-sequence`, `illustrated-trend`, `illus-hero`,
  `illus-art`,
  `illus-overlay`, `illus-lead`, `illus-dek`, `illus-lower`, `illus-notes`,
  `illus-note`, `illus-note-icon`, `it-hero`, `it-lower`, `it-chart`,
  `it-track`, `it-track-svg`, `it-flow`, `it-step`, `it-step-head`,
  `it-step-num`
- `grouped-bars`, `gb-plot`, `gb-group`, `gb-bars`, `gb-bar`, `gb-label`,
  `gb-legend`
- `process-thesis`, `process-notes`, `process-note`, `process-guards`, `guard`
- `quadrant`, `q-grid`, `q-cell`
- `illustrated-comparison`, `illus-compare`, `ic-side`, `ic-vs`
- `illustrated-quote`, `iq-overlay`, `iq-quote`, `iq-lower`, `iq-notes`,
  `iq-note`
- `poster-layout`, `poster-copy`, `poster-quote`, `poster-sub`,
  `poster-claims`, `poster-claim`, `poster-art`, `poster-svg`,
  `poster-ring`, `poster-arc`, `poster-slash`, `poster-dot`
- `stat-row`, `stat`, `stat-value`, `stat-label`
- `hero`, `hero-figure`, `hero-value`, `hero-label`, `hero-copy`
- `timeline`, `timeline-item`, `timeline-marker`, `timeline-body`,
  `timeline-label`, `timeline-detail`
- `steps`, `step`, `step-number`
- `compare`, `compare-side`, `compare-vs`
- `bento`, `bento-cell`, `bento-wide`, `bento-tall`
- `quote`, `support`
- `colophon`, `bottom-line`, `citations`

A new class must be added to `BASE_CSS` in the same change as the layout.

### 3.4 Escaping

All model-provided text is untrusted. Every interpolation goes through
`html.escape(value, quote=True)`. Layouts must not build HTML with f-strings
around raw text. Use the helpers in `_parts.py`.

No layout may emit `<script>`, `<iframe>`, `<link>`, `<img src>`, inline event
handlers, or a URL. The quality gate rejects `http://` and `https://` in the
output.

### 3.5 Density

Density is a content budget, applied by the design pass and checked by the
quality gate:

| density | claim text budget | guidance |
|---|---|---|
| `concise` | ~900 chars total | one message, social post |
| `standard` | ~1400 chars | explainer, slide |
| `detailed` | ~2200 chars | reference page, print |

A layout should render at most its `max_claims` and should degrade gracefully
when a claim lacks a value or a source.

### 3.6 Degradation

Every layout must render something sensible when optional data is missing:

- No numeric claim → use `thesis` or the first text claim as the hero.
- No relationship → derive ordered items from claims, or skip the structure.
- No quote → use `thesis`.
- No citations → omit the citations line, do not leave an empty element.

A layout must never raise on a valid `Brief`. It may raise on a `Brief` that
violates `min_claims`; the quality gate catches that earlier.

---

## 4. Catalog and selection

`design.mode` filters the family before ranking: `structured` excludes the
illustrated family, `illustrated` permits only it, and `auto` considers all
families.

`tavola/layouts/catalog()` returns layouts sorted by id. The design prompt
contains one line per layout:

```
hero-stat — One headline number with supporting context.
  needs: numeric · claims 3–6 · orientations square|portrait|landscape
```

Selection order:

1. CLI or API override (`--layout`), if valid.
2. The model's `DesignPlan.layout`, if valid.
3. One repair attempt with the validation error.
4. `heuristic_plan(brief)` with a warning in the CLI and the sidecar.

`heuristic_plan` precedence:

| condition | layout |
|---|---|
| `comparison` relationship | `comparison` |
| `hierarchy` relationship | `hierarchy` |
| `proportion` relationship and ≥3 numeric claims | `donut-share` |
| ≥3 comparable numbers and a text claim | `dashboard` |
| `sequence` relationship | `timeline` if items have times, else `process` |
| ≥ 3 numeric claims and ≥ 5 claims | `bento` |
| ≥ 3 numeric claims | `stat-row` |
| 1 numeric claim and ≥ 4 claims | `hero-stat` |
| a quote or a strong thesis | `statement` |
| otherwise | `bento` |

The heuristic is deliberately boring. It exists to keep the CLI usable when a
local model returns malformed JSON, not to replace the design pass.

---

## 4.1 Illustrated assets

`illustration.provider: gemini` produces one cached text-free hero image per
illustrated Brief. Presets are `editorial`, `clay`, `sketch`, `minimal`,
`papercut`, and `cinematic`; an optional `direction` adds art direction. The prompt forbids words, labels,
numbers, logos, and charts; text is composed by the deterministic renderer. The
image is embedded as a data URI and never referenced from a remote URL. If
generation fails, the illustrated layout falls back to its procedural art.

## 5. Quality gate hooks

`tavola/quality.py` receives `(brief, plan, layout)` and returns issues. A
layout declares its own limits through its `Layout` fields, so the gate does
not hardcode them.

Checked in v0.1:

- claim count vs `min_claims` / `max_claims`
- orientation supported by the layout
- title ≤ 92 chars, dek ≤ 190 chars, claim text ≤ 200 chars
- total claim text vs the density budget
- a numeric claim without a `value` (warning)
- palette entries that are not hex (error)
- any `http://` or `https://` in the rendered artefact (error)

Measured gate (Playwright, `render.measure: true`):

- element overflow and clipping
- rendered font size below 11px
- contrast below WCAG AA
- an orphaned heading detached from its content or stranded at the page edge
- one automatic reflow retry when overflow or clipping is the only failure,
  then a visible failure

---

## 6. Adding a layout

1. Create `src/tavola/layouts/<id>.py` with `LAYOUT = Layout(...)` and a pure
   `render(ctx) -> str`.
2. Use `_parts.py` helpers and the class vocabulary above.
3. Add the layout's classes to `BASE_CSS` if they are new.
4. Add an entry to the table in `docs/LAYOUT-CONTRACT.md` and `README.md`.
5. Add the module import to `src/tavola/layouts/__init__.py`.
6. Add a case to `tests/test_layouts.py` if the layout has special data needs.
7. Run the contract test: every layout renders the sample brief at every
   supported orientation, with no external references, and the title is
   escaped.

A minimal layout:

```python
from tavola.layouts._parts import claim_list, stat_cards
from tavola.layouts.base import Layout, LayoutContext, register


def render(ctx: LayoutContext) -> str:
    stats, _ = stat_cards(ctx.brief.claims, limit=3)
    return f"""
    <section class="stat-row">{stats}</section>
    <section class="claims">{claim_list(ctx.brief.claims)}</section>
    """


register(
    Layout(
        id="stat-row",
        name="Stat row",
        description="Three or four comparable figures with supporting claims.",
        needs=("multi_numeric",),
        min_claims=3,
        max_claims=6,
        orientations=("square", "portrait", "landscape"),
        render=render,
    )
)
```

## 7. Adding a style pack

1. Add a `Theme(...)` in `src/tavola/themes/builtin.py` and `register` it.
2. Verify contrast for `ink`/`bg`, `ink`/`surface`, and `accent_ink`/`accent`.
3. Use a pair from the bundled OFL fonts, with system fallbacks.
4. Add the id to the README and to `docs/LAYOUT-CONTRACT.md` if it introduces a
   new visual idea.
5. Do not encode structure in a theme. If it needs a different grid, it is a
   layout.

## 8. Versioning

- Layout ids and style ids are public API. Renaming one is a breaking change;
  add an alias in the registry and mark the old one deprecated for one minor
  release.
- `Brief` and `DesignPlan` are versioned by the package version. The sidecar
  records `tavola` version, `brief`, `plan`, `size`, `layout`, and `style` so an
  artefact can be rebuilt.
- A layout's `needs` and claim range may tighten in a minor release only if the
  quality gate still accepts every previously valid brief.

## 9. Built-in catalog (v0.1)

| id | name | needs | claims | orientations |
|---|---|---|---|---|
| `antv-comparison` | AntV comparison | `comparison` | 3–6 | all |
| `antv-hierarchy` | AntV hierarchy | `hierarchy` | 3–6 | all |
| `antv-sequence` | AntV sequence | `sequence` | 3–6 | all |
| `bar-share` | Bar share | `multi_numeric`, `chartable` | 3–6 | all |
| `bento` | Bento | `many_claims` | 4–6 | all |
| `donut-share` | Donut share | `multi_numeric` | 3–6 | all |
| `comparison` | Comparison | `comparison` | 3–6 | all |
| `dashboard` | Dashboard | `multi_numeric`, `chartable` | 3–6 | all |
| `stacked-share` | Stacked share | `multi_numeric`, `chartable` | 3–6 | all |
| `trend` | Trend | `series` | 3–6 | all |
| `trend-dashboard` | Trend dashboard | `series` | 3–6 | all |
| `hero-stat` | Hero stat | `numeric` | 3–6 | all |
| `grouped-bars` | Grouped bars | `series`, `multi_series` | 3–6 | all |
| `hierarchy` | Hierarchy | `hierarchy` | 3–6 | all |
| `illustrated` | Illustrated brief | none | 3–6 | all |
| `illustrated-comparison` | Illustrated comparison | `comparison` | 3–6 | all |
| `illustrated-quote` | Illustrated quote | none | 3–6 | all |
| `illustrated-sequence` | Illustrated sequence | `sequence` | 3–6 | all |
| `illustrated-trend` | Illustrated trend | `series` | 3–6 | all |
| `poster` | Poster | none | 3–6 | all |
| `quadrant` | Quadrant | none | 4–6 | all |
| `process` | Process | `sequence` | 3–6 | all |
| `stat-row` | Stat row | `multi_numeric` | 3–6 | all |
| `statement` | Statement | `quote` | 3–6 | all |
| `timeline` | Timeline | `sequence` | 3–6 | all |
