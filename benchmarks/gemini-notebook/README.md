# Gemini Notebook / NotebookLM design benchmark

Three synthetic sources cover different infographic shapes:

| Source | Tests |
|---|---|
| `sources/01-urban-heat-data.pdf` | data-heavy: stat strip, chart, comparison table, sequence |
| `sources/02-launch-timeline.pdf` | phased programme: timeline, dependencies, risk cards |
| `sources/03-library-argument.pdf` | qualitative argument: pillars, hierarchy, quote, comparison |

The Markdown equivalents and `generate_sources.py` make the PDFs reproducible.

## What to capture from a reference run

- Orientation and level of detail.
- Visual style selected by Auto-select.
- The finished infographic.
- Whether it uses a chart, table, timeline, hierarchy, or illustration.
- Any visible labels, numbers, or claims that are wrong.
- Where the page feels designed rather than simply structured.

## What to compare

1. Composition: one dominant idea, or a grid of equal cards?
2. Data treatment: chart selection, table use, annotation quality.
3. Text density: claims kept, wording compression, duplicated numbers.
4. Hierarchy: title, subhead, evidence, detail, footnote.
5. Visual language: illustrations, icons, colour bands, connectors, paper or clay texture.
6. Editability: can text be corrected without redrawing the page?
7. Accuracy: are labels, units, and relationships preserved?

## Product split

Native layouts stay deterministic and editable. The illustrated direction needs a
second layer: text-free assets (hero illustration, icon badges, textures)
composed behind native text and charts. Do not ask an image model to draw the
whole infographic, and do not flatten layers until the final PNG/PDF export.

Reference outputs belong in `references/` only. They are design evidence, not
product assets.
