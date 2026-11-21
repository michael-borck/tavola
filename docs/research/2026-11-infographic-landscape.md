# Research: the AI infographic landscape (Nov 2026)

Method: read the existing `infographic-gen` scripts, the Limn and Canturía
codebases, the public READMEs of GroqCasters and Open Notebook, and the
project pages / docs of the tools below. No benchmarks were run; star counts
and licences are as published.

The question was narrow: **what already exists that would let Tavola produce
genuinely good infographics, rather than another prompt-filled template?**

## 1. What the existing scripts do

`generate_infographic.py` and `generate_notebook.py`:

- extract a title, subtitle, 3 stats, 4 bullets, and a bottom line with Gemini;
- interpolate them into one Tailwind CDN template;
- screenshot it with Playwright at 900px.

The limitation is not the model. It is that there is one structural decision
(three cards above a list) and no design system. Tailwind's CDN defaults,
system font stack, and a single accent colour produce the recognisable
"AI demo" look. There is no layout choice, no density control, no typography
scale, no imagery, and no check that anything fits.

**Conclusion:** the pipeline needs a design pass and a catalog, not a longer
prompt.

## 2. NotebookLM / Gemini Notebook infographics

Google's feature (Studio → Infographic) generates a single PNG. Documented
controls: output language, detail (Concise / Standard / Detailed beta),
orientation (Square / Portrait / Landscape), a visual style, and a custom
prompt. The ten styles announced in March 2026 are Sketch Note, Kawaii,
Professional, Scientific, Anime, Clay, Editorial, Instructional, Bento Grid,
and Bricks. Output is raster; there is no editing after generation other than
regenerating; Google warns about factual and visual inaccuracies.

The important detail: NotebookLM's infographics are produced by an image model
(Nano Banana Pro / Gemini image), not an HTML renderer. That explains both the
strengths (organic composition, bespoke illustration) and the weaknesses
(baked-in text errors, no editability, no brand tokens).

**Conclusion:** do not try to match the illustration style with a template.
Match the *design decision quality*, and beat it on text accuracy and
editability. A generated-illustration mode is a later, optional layer.

## 3. Tools reviewed

### AntV Infographic — the most useful find

<https://github.com/antvis/Infographic> · MIT · ~200 templates

A declarative infographic engine from Ant Group. A YAML-like DSL selects a
template and supplies data; output is SVG. It has a theme system (hand-drawn,
gradients, patterns), a built-in editor, streaming rendering, and an SSR
`renderToString` entry point. It ships agent skills for generating syntax.

Why it matters: the templates cover the diagram-shaped layouts that are
expensive to build well — timelines, sequences, hierarchies, comparisons,
relations, word clouds. That is exactly where a hand-written CSS layout is
weakest. It is AI-friendly by design: the syntax is tolerant and streamable.

Trade-offs: it is a JS package, so the Python side needs a browser (Playwright
or the Tauri webview) to render it; its visual language is distinct and may
fight an editorial theme unless the theme is customised.

**Decision:** adopt for M2 diagram layouts. Keep editorial layouts in Tavola's
own CSS.

### Presenton

<https://github.com/presenton/presenton> · Apache-2.0

An open-source AI presentation generator: self-hosted Docker app, desktop
builds, BYOK for OpenAI/Gemini/Anthropic/Ollama/OpenRouter, editable PPTX/PDF
export, MCP server, and a template system.

The architecture is the valuable part, not the code:

- A template is a **layout component plus a schema** describing what content it
  expects. The AI fills the schema; it does not write the layout.
- A separate **outline** step is approved before design, so story and layout
  are distinct.
- A template gallery with previews, and template creation from an existing
  PPTX/PDF.

**Decision:** copy the contract (schema-per-layout, separate outline/design
step, catalog with descriptions). Do not copy the stack.

### LIDA (Microsoft)

<https://github.com/microsoft/lida> · MIT

"Automatic Generation of Visualizations and Infographics using LLMs." Strong
on data-faithful charts: summarise a dataframe, propose goals, generate chart
code, execute, repair. The infographic part is explicitly beta and uses Stable
Diffusion via `peacasso`; it is dated and not design-led.

**Decision:** borrow the idea of goals/relationships before charts and the
repair loop. Do not depend on it.

### infogroove

<https://pypi.org/project/infogroove> · MIT · 0.5.2, Jan 2026

Declarative JSON templates → SVG using `svg.py` and `sympy`, with a safe
expression subset. Nice small engine, alpha, no design library.

**Decision:** watch it as a possible pure-Python SVG backend; not the product.

### infographics-builder

<https://pypi.org/project/infographics-builder> · MIT · 2.2.0

CLI for poster generation: `rembg` background removal, parallel headless
Chrome rendering, colour auto-patching, asset validation. A utility, not a
designer.

**Decision:** borrow the rendering/validation ideas; the Playwright path in
Tavola is simpler.

### aiz-infographic

<https://github.com/aizzaku/aiz-infographic>

An agent skill that produces self-contained HTML infographics with PNG export.
Its inventory is the useful part: four canvases, 27 snippets, 24 styles, 15
elements, 11 templates, and a quality gate before export. This is close to the
"style pack + layout catalog" idea, expressed as prompts and snippets.

**Decision:** use it as a checklist for what a style pack should include.

### SenseNova-Skills `sn-infographic`

<https://github.com/OpenSenseNova/SenseNova-Skills>

An image-model infographic pipeline: 87 layouts, 66 styles, prompt-quality
scoring, multi-round generation with VLM review, and quality ranking. Its
output is raster and depends on a specific model family, but the **review
loop** is the idea worth stealing: generate several candidates, have a vision
model score legibility and composition, keep the best.

**Decision:** best-of-3 plus VLM scoring is an M1 feature.

### GroqCasters

<https://github.com/jgravelle/GroqCasters> · MIT

A 2024 podcast generator: outline → expand → dialogue, host profiles as data,
optional pre-written script, Bark TTS with custom voice samples.

Relevant ideas: the staged pipeline, personas/style profiles as configuration,
and a "use an existing script" path (which maps to Tavola's `--brief`). The
rest of the stack is dated.

### Open Notebook

<https://github.com/lfnovo/open-notebook> · MIT

A self-hosted NotebookLM alternative: sources (PDF, video, audio, web),
multi-provider models via Esperanto, vector/full-text search, chat with
citations, podcast generation with speaker profiles, REST API, MCP, optional
password, Docker.

Useful concepts for Tavola:

- a provider registry with "test connection" and keys encrypted at rest;
- sources → transformations → artefact (their episode profiles map directly to
  design profiles);
- background jobs with progress;
- citations on every claim;
- one-command self-hosting.

Not useful: the stack (Next.js + SurrealDB + LangChain) and the notebook
surface area. Tavola should not become a research app before its artefact is
good.

## 4. Renderer comparison

| Approach | Text accuracy | Editability | Design ceiling | Offline |
|---|---|---|---|---|
| HTML/CSS + SVG | perfect | HTML/SVG | high, with a real design system | yes |
| Canvas | good | none | high, but manual layout | yes |
| SVG library (svg.py) | perfect | SVG | medium; text metrics are hard | yes |
| Image model (Nano Banana, SDXL) | poor | none | highest, one-off | no |
| AntV Infographic | perfect | SVG/DSL | high for diagrams | yes (bundled) |

**Decision:** HTML/CSS is the primary renderer. SVG is used for charts and
diagram layouts. Image generation is reserved for text-free assets.

## 5. What "good" requires

Across every tool above, the same four things separate a designed page from a
filled template:

1. **Structure chosen for the content.** A timeline only when the source has a
   sequence; a comparison only when it has two sides. This is why `Brief`
   carries a relationship.
2. **A real type scale.** Display size, dek, body, label, caption — with
   tracking and line-height decisions, not browser defaults.
3. **A restrained palette and one accent.** Two neutrals, one accent, one
   surface. Contrast checked.
4. **One visual idea.** A hero number, a rail, a bento, a quote. Not three
   cards and four bullets because that is what the prompt said.

The quality gate exists because all four fail silently when text overflows.

## 6. Decisions recorded

- Name: **Tavola** (Italian: a full-page plate/illustration). PyPI and npm were
  free on 2026-11-19.
- v0.1 is single-source.
- The model selects from a catalog; it does not write HTML.
- HTML/CSS + tokens is the renderer; Playwright for PNG/PDF.
- Ollama is the default provider; OpenAI-compatible, Gemini, and Anthropic are
  supported with structured output.
- AntV is planned for diagram layouts, not adopted as the core.
- Generated assets and painterly mode are later, opt-in layers.
- No CDN, no external fonts, no external references in the artefact.
- Do not build a notebook app until the artefact is good.

## 7. References

- AntV Infographic: <https://github.com/antvis/Infographic>
- Presenton: <https://github.com/presenton/presenton>
- LIDA: <https://github.com/microsoft/lida>
- infogroove: <https://pypi.org/project/infogroove>
- infographics-builder: <https://pypi.org/project/infographics-builder>
- aiz-infographic: <https://github.com/aizzaku/aiz-infographic>
- SenseNova-Skills: <https://github.com/OpenSenseNova/SenseNova-Skills>
- GroqCasters: <https://github.com/jgravelle/GroqCasters>
- Open Notebook: <https://github.com/lfnovo/open-notebook>
- NotebookLM infographic help:
  <https://support.google.com/notebooklm/answer/16758265>
- NotebookLM styles announcement:
  <https://workspaceupdates.googleblog.com/2026/03/new-ways-to-customize-and-interact-with-your-content-in-NotebookLM.html>
