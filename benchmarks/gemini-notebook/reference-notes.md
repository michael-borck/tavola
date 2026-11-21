# Reference notes

Observed from the three supplied Gemini Notebook outputs and the customise panel.

## 01 — Urban heat data

- Landscape composition with a strong illustrated hero band: hot city on the
  left, shaded street on the right.
- Problem and solution are placed over the hero, not in separate cards.
- Three-column stat strip with custom icons, larger numbers, and short labels.
- Comparison table and four-stage implementation sequence share the lower half.
- Colour is semantic: warm orange for heat, green for trees, red/amber/green for
  cost.
- The page is dense but the eye still follows hero → numbers → comparison →
  sequence.

**Lesson:** the illustration establishes the argument; the numbers and table
carry the evidence. It is not a chart-only page.

## 02 — Library argument

- Three illustrated pillars across the top: access, non-commercial space,
  social connection.
- A central white band interrupts the grid with the main thesis.
- A second row turns the argument into consequences and recommendations.
- The legacy-metrics versus civic-value comparison uses a bridge metaphor.
- Icons and spot illustrations carry most of the emotional weight.

**Lesson:** qualitative content can still be a structured infographic if the
composition has a visual metaphor. A poster-plus-columns layout is not enough.

## 03 — Launch timeline

- Curved path connecting five illustrated milestones.
- Dates sit in badges; clock/medal motifs mark milestones and evaluation.
- Each stop has an icon, a phase title, and a short description.
- A bottom row of three safeguards extends the page beyond the timeline.

**Lesson:** the “flow feel” is a path plus illustrated nodes plus a secondary
band of risks. AntV can supply the path/nodes; the illustration system supplies
the character.

## Customise panel

Controls include:

- Language.
- Orientation: landscape, portrait, square.
- Visual style: Auto-select, Kawaii, Clay, Sketch note, Anime, and scrolling
  variants.
- Detail level: Concise, Standard, Detailed (beta).
- Source count.
- Free-text direction, e.g. “Use a blue colour theme and highlight the 3 key
  stats.”
- AI-usage meter and Generate later/now actions.

**Lesson:** “style” is not a colour palette. It changes the illustration
language, shape treatment, texture, and density. Auto-select is a router.

## What this means for Tavola

1. Keep the deterministic renderer and exact text overlay.
2. Add a hybrid illustrated composition with a hero asset, stat strip, and one
   supporting diagram/table.
3. Use an open vector icon set for repeated icons; generate only the hero or
   concept illustration, not every icon.
4. Treat visual styles as prompt + token + shape + texture packs, not just
   colour themes.
5. Export flat PNG only at the end; keep HTML/PDF and the layer structure for
   editing and quality checks.
