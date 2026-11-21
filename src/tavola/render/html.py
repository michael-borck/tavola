"""Deterministic HTML renderer.

One document, exact pixel viewport, no external references. Layouts supply the
body; this module supplies the masthead, footer, CSS, and theme tokens.
"""

from __future__ import annotations

from tavola.brief import Brief
from tavola.config import ORIENTATIONS
from tavola.design import DesignPlan
from tavola.layouts import LayoutContext, get_layout
from tavola.themes import Theme
from tavola.themes.fonts import font_css

BASE_CSS = r"""
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html {
  font-size: calc(min(100vw / 67.5, 100vh / 56.25));
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
body {
  width: 100vw; height: 100vh; overflow: hidden;
  background: var(--bg); color: var(--ink);
  font-family: var(--font-body);
  -webkit-font-smoothing: antialiased;
  text-rendering: geometricPrecision;
}
.poster {
  position: relative; width: 100vw; height: 100vh; overflow: hidden;
  padding: 3.2rem 3.4rem 2.4rem;
  display: flex; flex-direction: column;
}
.poster > * { position: relative; z-index: 1; }
.poster[data-texture="grid"]::before {
  content: ""; position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background-image:
    linear-gradient(to right, var(--border) 1px, transparent 1px),
    linear-gradient(to bottom, var(--border) 1px, transparent 1px);
  background-size: 2.6rem 2.6rem;
  opacity: 0.16;
}
.poster[data-texture="grain"]::before {
  content: ""; position: absolute; inset: 0; pointer-events: none; z-index: 0;
  background-image: repeating-radial-gradient(
    circle at 30% 20%,
    rgba(0, 0, 0, 0.055) 0 1px,
    transparent 1px 3px
  );
  opacity: 0.7;
}

.masthead { display: flex; flex-direction: column; gap: 0.55rem; margin-bottom: 2.1rem; }
.eyebrow {
  font-size: 0.76rem; font-weight: 700; letter-spacing: var(--label-tracking);
  text-transform: uppercase; color: var(--accent);
}
.title {
  font-family: var(--font-display); font-weight: 800;
  font-size: 3.95rem; line-height: 1.02; letter-spacing: -0.022em;
  text-wrap: balance;
}
.dek { font-size: 1.28rem; line-height: 1.42; color: var(--muted); max-width: 58ch; }

.body { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 1.5rem; }
.layout-group {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  justify-content: center; gap: 1.2rem;
}

.thesis {
  font-family: var(--font-display); font-size: 1.62rem; line-height: 1.3;
  font-weight: 600; text-wrap: pretty;
}
.rail-head { display: flex; align-items: baseline; gap: 0.9rem; flex-wrap: wrap; }
.rail-kicker {
  font-size: 0.72rem; font-weight: 700; letter-spacing: var(--label-tracking);
  text-transform: uppercase; color: var(--accent);
}
.rail-title { font-family: var(--font-display); font-size: 1.2rem; font-weight: 600; }

/* Claims */
.claim-list { list-style: none; display: grid; gap: 0.7rem; }
.claim {
  display: grid; grid-template-columns: auto 1fr auto; align-items: start;
  gap: 0.75rem; padding: 0.85rem 1rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); font-size: 1.04rem; line-height: 1.38;
}
.claim-list.compact .claim {
  background: var(--surface-alt); padding: 0.6rem 0.8rem; font-size: 0.96rem;
}
.claim-marker {
  font-family: var(--font-display); font-weight: 800; color: var(--accent);
  font-size: 0.92rem; line-height: 1.5;
}
.claim-text { min-width: 0; }
.claim-source {
  font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase;
  color: var(--muted); border: 1px solid var(--border);
  border-radius: 999px; padding: 0.16rem 0.5rem; white-space: nowrap;
}

/* Stats */
.stat-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 1rem; }
.stat {
  display: flex; flex-direction: column; gap: 0.35rem; padding: 1.15rem 1.2rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow);
}
.stat-value {
  font-family: var(--font-display); font-weight: 800; color: var(--accent);
  font-size: 2.7rem; line-height: 1; letter-spacing: -0.03em;
}
.stat-label { font-size: 0.95rem; line-height: 1.32; color: var(--muted); }
.layout-group .stat { padding: 2rem 1.6rem; justify-content: center; }
.layout-group .stat-value { font-size: 3.2rem; white-space: nowrap; }
.layout-group .stat-label { font-size: 1.05rem; }
.stat-layout { justify-content: space-between; }

/* Bar share */
.bar-share {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  justify-content: flex-start; gap: 1.1rem;
}
.bar-list {
  list-style: none; flex: 1; display: flex; flex-direction: column;
  justify-content: space-evenly; gap: 1.15rem;
}
.bar-row { display: flex; flex-direction: column; gap: 0.4rem; }
.bar-meta { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
.bar-label { font-family: var(--font-display); font-size: 1.35rem; font-weight: 600; }
.bar-value {
  font-family: var(--font-display); font-size: 1.35rem; font-weight: 800;
  color: var(--accent); white-space: nowrap;
}
.bar-track {
  height: 1.15rem; overflow: hidden; border-radius: 999px;
  background: var(--surface-alt); border: 1px solid var(--border);
}
.bar-fill {
  display: block; height: 100%; min-width: 0.4rem;
  background: var(--chart-1, var(--accent)); border-radius: 999px;
}
.bar-fill-2 { background: var(--chart-2, var(--accent)); }
.bar-fill-3 { background: var(--chart-3, var(--accent)); }
.bar-fill-4 { background: var(--chart-4, var(--accent)); }
.bar-note { font-size: 0.78rem; line-height: 1.4; color: var(--muted); }

/* Illustrated brief */
.illustrated {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  gap: 1.25rem;
}
.illus-hero {
  position: relative; flex: 1; min-height: 20rem; overflow: hidden;
  border-radius: var(--radius); background: var(--surface-alt);
  box-shadow: var(--shadow);
}
.illus-art { position: absolute; inset: 0; overflow: hidden; }
.illus-art svg { display: block; width: 100%; height: 100%; overflow: hidden; }
.illus-art img { display: block; width: 100%; height: 100%; object-fit: cover; }
.illus-overlay {
  position: relative; z-index: 1; width: 62%; min-height: 100%;
  display: flex; flex-direction: column; justify-content: center;
  gap: 1rem; padding: 3rem;
  background: linear-gradient(
    90deg,
    var(--bg) 0%,
    color-mix(in srgb, var(--bg) 97%, transparent) 50%,
    color-mix(in srgb, var(--bg) 86%, transparent) 70%,
    transparent 100%
  );
}
.illus-bg { fill: var(--surface-alt); }
.illus-orb-a { fill: var(--chart-1, var(--accent)); opacity: 0.9; }
.illus-orb-b { fill: var(--chart-2, var(--accent)); opacity: 0.75; }
.illus-ribbon {
  fill: none; stroke: var(--chart-3, var(--accent)); stroke-width: 5;
  stroke-linecap: round; opacity: 0.9;
}
.illus-line {
  fill: none; stroke: var(--border); stroke-width: 0.7;
}
.illus-dot-a { fill: var(--accent); }
.illus-dot-b { fill: var(--ink); opacity: 0.65; }
.illus-copy { display: flex; flex-direction: column; gap: 0.9rem; min-width: 0; }
.illus-overlay .rail-kicker { color: var(--ink); }
.illus-lead {
  font-family: var(--font-display); font-size: clamp(2rem, 3.4vw, 3.2rem);
  line-height: 1.12; letter-spacing: -0.02em; text-wrap: balance;
}
.illus-dek { font-size: 1rem; line-height: 1.45; color: var(--muted); max-width: 48ch; }
.illus-lower { display: flex; flex-direction: column; gap: 0.8rem; }
.illus-notes {
  list-style: none; display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: 0.7rem;
}
.illus-note {
  display: flex; flex-direction: column; gap: 0.35rem;
  padding: 0.7rem 0.8rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.illus-note-icon { color: var(--accent); display: inline-flex; }
.illus-note-icon .kpi-svg { width: 1.05rem; height: 1.05rem; }
.evidence-table {
  width: 100%; border-collapse: collapse; font-size: 0.8rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); overflow: hidden;
}
.evidence-table th {
  text-align: left; padding: 0.45rem 0.65rem; color: var(--accent);
  font-family: var(--font-display); font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: var(--label-tracking); border-bottom: 1px solid var(--border);
}
.evidence-table td {
  padding: 0.45rem 0.65rem; color: var(--muted); vertical-align: top;
  border-bottom: 1px solid var(--border);
}
.evidence-table tr:last-child td { border-bottom: 0; }
.evidence-table td:nth-child(2), .evidence-table td:nth-child(3) {
  font-family: var(--font-display); font-weight: 600; color: var(--ink);
  white-space: nowrap;
}
.illus-flow {
  list-style: none; display: grid;
  grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
  gap: 0.65rem;
}
.illus-step {
  display: flex; flex-direction: column; gap: 0.3rem;
  padding: 0.6rem 0.7rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.illus-step .kpi-icon { color: var(--accent); }
.illus-step .kpi-svg { width: 1rem; height: 1rem; }
.illus-step-num {
  font-family: var(--font-display); font-size: 0.7rem; font-weight: 800;
  color: var(--accent); letter-spacing: 0.08em;
}
.illus-step p {
  font-family: var(--font-display); font-size: 0.86rem; line-height: 1.25;
  font-weight: 600;
}
.illus-note p { font-size: 0.88rem; line-height: 1.35; color: var(--muted); }
.orientation-landscape .illus-overlay { width: 56%; }
.orientation-portrait .illus-overlay { width: 68%; padding: 2.4rem; }

/* Illustrated trend */
.illustrated-trend {
  flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 1rem;
}
.illustrated-trend .it-hero { flex: 0 0 clamp(12rem, 26vh, 18rem); min-height: 12rem; }
.illustrated-trend .illus-overlay { padding: 2rem 2.4rem; }
.illustrated-trend .illus-lead { font-size: clamp(1.6rem, 2.5vw, 2.4rem); }
.it-lower { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 0.8rem; }
.it-chart { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 0.5rem; }
.it-chart .trend-figure { flex: 1; min-height: 0; }
.it-chart .trend-plot { flex: 1; height: auto; min-height: 10rem; }

/* Illustrated sequence */
.illustrated-sequence {
  flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 1rem;
}
.illustrated-sequence .it-hero { flex: 0 0 clamp(12rem, 26vh, 18rem); min-height: 12rem; }
.illustrated-sequence .illus-overlay { padding: 2rem 2.4rem; }
.illustrated-sequence .illus-lead { font-size: clamp(1.6rem, 2.5vw, 2.4rem); }
.it-track { position: relative; flex: 1; display: flex; align-items: center; }
.it-guards { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }
.orientation-portrait .it-guards { display: none; }
.it-track-svg {
  position: absolute; left: 0; right: 0; top: 50%; width: 100%; height: 4rem;
  transform: translateY(-50%); z-index: 0; overflow: visible;
}
.it-track-svg path {
  fill: none; stroke: var(--chart-2, var(--accent)); stroke-width: 1.2;
  opacity: 0.38; vector-effect: non-scaling-stroke;
}
.it-flow {
  position: relative; z-index: 1; list-style: none; width: 100%;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 1rem; align-items: stretch;
}
.it-flow .it-step:nth-child(odd) { transform: translateY(-0.25rem); }
.orientation-portrait .it-track { align-items: stretch; }
.orientation-portrait .it-track-svg { display: none; }
.orientation-portrait .it-track::before {
  content: ""; position: absolute; left: 1.1rem; top: 4%; bottom: 4%;
  width: 2px; background: var(--border); z-index: 0;
}
.orientation-portrait .it-flow {
  grid-template-columns: 1fr; grid-auto-rows: 1fr; flex: 1;
  padding-left: 2.6rem;
}
.orientation-portrait .it-flow .it-step {
  position: relative; justify-content: center; transform: none;
  padding: 1.2rem 1.4rem;
}
.orientation-portrait .it-flow .it-step::before {
  content: ""; position: absolute; left: -1.85rem; top: 50%;
  width: 0.55rem; height: 0.55rem; border-radius: 50%;
  background: var(--accent); transform: translateY(-50%); z-index: 2;
}
.orientation-portrait .it-flow .it-step::after { display: none; }
.orientation-portrait .it-flow .it-step p { font-size: 1.15rem; }
.it-step {
  position: relative; display: flex; flex-direction: column; gap: 0.5rem;
  padding: 1rem; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius);
}
.it-step:not(:last-child)::after {
  content: "→"; position: absolute; right: -0.9rem; top: 50%;
  transform: translateY(-50%); color: var(--accent); font-weight: 700;
  z-index: 2;
}
.it-step-head {
  display: flex; justify-content: space-between; align-items: center; gap: 0.5rem;
}
.it-step-num {
  font-family: var(--font-display); font-size: 0.8rem; font-weight: 800;
  color: var(--accent); letter-spacing: 0.08em;
}
.it-step-head .kpi-icon { color: var(--accent); }
.it-step-head .kpi-svg { width: 1.1rem; height: 1.1rem; }
.it-step p {
  font-family: var(--font-display); font-size: 1.02rem; line-height: 1.28;
  font-weight: 600;
}

/* Grouped bars */
.grouped-bars {
  flex: 1; display: flex; flex-direction: column;
  justify-content: center; gap: 1.2rem;
}
.gb-plot {
  flex: 1; min-height: 12rem; display: flex; align-items: stretch;
  gap: 1.1rem; padding: 1rem 1.2rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.gb-group {
  flex: 1; min-width: 0; display: flex; flex-direction: column;
  justify-content: flex-end; gap: 0.4rem;
}
.gb-bars {
  flex: 1; min-height: 8rem; display: flex; align-items: flex-end;
  justify-content: center; gap: 0.3rem;
}
.gb-bar { display: block; width: 34%; min-width: 0.5rem; border-radius: 3px 3px 0 0; }
.gb-bar-1 { background: var(--chart-1, var(--accent)); }
.gb-bar-2 { background: var(--chart-2, var(--accent)); }
.gb-label {
  text-align: center; font-size: 0.72rem; color: var(--muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.gb-legend { display: flex; gap: 1.2rem; font-size: 0.8rem; color: var(--muted); }
.gb-legend span { display: inline-flex; align-items: center; gap: 0.4rem; }
.gb-swatch-1, .gb-swatch-2 { width: 0.7rem; height: 0.7rem; border-radius: 2px; display: inline-block; }
.gb-swatch-1 { background: var(--chart-1, var(--accent)); }
.gb-swatch-2 { background: var(--chart-2, var(--accent)); }

/* Quadrant */
.quadrant {
  flex: 1; display: flex; flex-direction: column;
  justify-content: center; gap: 1.2rem;
}
.q-grid {
  position: relative; flex: 1; min-height: 18rem; display: grid;
  grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr;
  gap: 0.8rem;
}
.q-grid::before, .q-grid::after {
  content: ""; position: absolute; background: var(--border); opacity: 0.6;
}
.q-grid::before { left: 50%; top: 0; bottom: 0; width: 1px; }
.q-grid::after { top: 50%; left: 0; right: 0; height: 1px; }
.q-cell {
  display: flex; flex-direction: column; gap: 0.4rem;
  padding: 1rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.q-cell .kpi-icon { color: var(--accent); }
.q-cell h3 {
  font-family: var(--font-display); font-size: 1rem; line-height: 1.25;
  font-weight: 700;
}
.q-cell p { font-size: 0.84rem; line-height: 1.35; color: var(--muted); }

/* Illustrated comparison */
.illustrated-comparison {
  flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 1rem;
}
.illustrated-comparison .it-hero { flex: 0 0 clamp(11rem, 24vh, 16rem); min-height: 11rem; }
.illustrated-comparison .illus-overlay { padding: 2rem 2.4rem; }
.illustrated-comparison .illus-lead { font-size: clamp(1.55rem, 2.35vw, 2.25rem); }
.illus-compare {
  flex: 1; display: grid; grid-template-columns: 1fr auto 1fr;
  gap: 1rem; align-items: stretch;
}
.ic-side {
  padding: 0.9rem 1rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.ic-side h3 {
  font-family: var(--font-display); font-size: 1.05rem; margin-bottom: 0.55rem;
}
.ic-vs {
  align-self: center; display: grid; place-items: center;
  width: 2.6rem; height: 2.6rem; border-radius: 50%;
  background: var(--accent); color: var(--accent-ink);
  font-family: var(--font-display); font-size: 0.78rem; font-weight: 800;
}

/* Illustrated quote */
.illustrated-quote {
  flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 1rem;
}
.illustrated-quote .it-hero { flex: 1; min-height: 15rem; }
.iq-overlay { width: 70%; padding: 2.4rem 2.8rem; }
.iq-quote {
  font-family: var(--font-display); font-size: clamp(2rem, 3.2vw, 3rem);
  line-height: 1.1; letter-spacing: -0.02em; text-wrap: balance;
  margin: 0;
}
.iq-lower { display: flex; flex-direction: column; gap: 0.6rem; }
.iq-notes {
  list-style: none; display: grid; grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
}
.iq-note {
  padding: 0.8rem 0.9rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.iq-note p { font-size: 0.9rem; line-height: 1.35; color: var(--muted); }

/* AntV diagrams */
.antv-layout {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(15rem, 0.8fr);
  gap: 2.2rem; align-items: stretch;
}
.antv-main {
  min-width: 0; display: flex; flex-direction: column;
  justify-content: center; gap: 1rem;
}
.antv-layout .dash-rail { justify-content: center; }
.antv-figure {
  flex: 0 0 auto; height: clamp(14rem, 30vh, 22rem);
  display: grid; place-items: center;
}
.orientation-portrait .antv-layout {
  grid-template-columns: minmax(0, 1.25fr) minmax(14rem, 0.75fr);
}
.antv-figure svg { width: 100%; height: 100%; max-height: 100%; }
.antv-compare-head {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 1rem; width: 100%; padding: 0 3%;
  font-family: var(--font-display); font-size: 1.2rem; font-weight: 700;
}
.antv-compare-head b {
  color: var(--accent); font-size: 0.82rem; text-transform: uppercase;
  letter-spacing: var(--label-tracking);
}

/* Poster */
.poster-layout {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(16rem, 0.85fr);
  align-items: center; gap: 2.4rem;
}
.poster-copy { display: flex; flex-direction: column; gap: 1.1rem; min-width: 0; }
.poster-quote {
  font-family: var(--font-display); font-size: clamp(2.4rem, 4.4vw, 4.4rem);
  line-height: 1.08; letter-spacing: -0.025em; text-wrap: balance;
}
.poster-sub { font-size: 1.05rem; line-height: 1.45; color: var(--muted); max-width: 46ch; }
.poster-claims {
  list-style: none; display: flex; flex-direction: column; gap: 0.7rem;
  margin-top: 0.6rem; max-width: 52ch;
}
.poster-claim {
  display: grid; grid-template-columns: minmax(4.4rem, auto) 1fr;
  gap: 0.7rem; align-items: baseline; padding-top: 0.6rem;
  border-top: 1px solid var(--border);
}
.poster-claim span {
  font-family: var(--font-display); font-size: 0.9rem; font-weight: 800;
  color: var(--accent); white-space: nowrap;
}
.poster-claim p { font-size: 0.9rem; line-height: 1.35; color: var(--muted); }
.poster-art {
  width: 100%; max-width: min(28rem, 100%); min-width: 0; aspect-ratio: 1;
  justify-self: end; overflow: hidden;
}
.poster-svg { width: 100%; height: 100%; overflow: visible; }
.poster-ring { fill: none; stroke-width: 0.7; }
.poster-ring-1 { stroke: var(--chart-1, var(--accent)); opacity: 0.85; }
.poster-ring-2 { stroke: var(--chart-2, var(--accent)); opacity: 0.55; }
.poster-arc { fill: none; stroke: var(--chart-2, var(--accent)); stroke-width: 5.5; opacity: 0.9; }
.poster-slash { fill: none; stroke: var(--border); stroke-width: 0.5; }
.poster-dot-1 { fill: var(--accent); }
.poster-dot-2 { fill: var(--chart-3, var(--accent)); }
.orientation-portrait .poster-layout {
  grid-template-columns: minmax(0, 1.15fr) minmax(12rem, 0.85fr);
  gap: 1.8rem; align-items: center;
}
.orientation-portrait .poster-art {
  width: min(100%, 22rem); justify-self: end;
}
.orientation-portrait .poster-quote { font-size: clamp(2.1rem, 4.4vw, 3.1rem); }

/* Hierarchy */
.hierarchy {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  justify-content: space-between; gap: 1.3rem;
}
.tree {
  flex: 1; width: 100%; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.tree-root {
  max-width: 70%; padding: 1rem 1.8rem; text-align: center;
  font-family: var(--font-display); font-size: 1.35rem; font-weight: 700;
  color: var(--accent-ink); background: var(--accent);
  border-radius: var(--radius); box-shadow: var(--shadow);
}
.tree-trunk { width: 2px; height: 1.5rem; background: var(--border); }
.tree-children {
  position: relative; width: 100%; padding-top: 1.4rem;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 1rem;
}
.tree-children::before {
  content: ""; position: absolute; top: 0; left: 12%; right: 12%;
  height: 2px; background: var(--border);
}
.tree-child {
  position: relative; display: flex; flex-direction: column; gap: 0.35rem;
  padding: 1.15rem 1rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.tree-child::before {
  content: ""; position: absolute; top: -1.4rem; left: 50%;
  width: 2px; height: 1.4rem; background: var(--border);
}
.tree-child-index {
  font-size: 0.7rem; font-weight: 700; letter-spacing: var(--label-tracking);
  color: var(--accent); text-transform: uppercase;
}
.tree-child h3 {
  font-family: var(--font-display); font-size: 1.05rem; line-height: 1.25;
  font-weight: 600;
}
.tree-notes {
  list-style: none; display: grid; grid-template-columns: 1fr 1fr; gap: 0.7rem;
  width: 100%; margin-top: 0.4rem;
}
.tree-notes li {
  display: grid; grid-template-columns: 1.2rem 1fr; gap: 0.5rem;
  align-items: start; padding: 0.7rem 0.8rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.tree-notes .kpi-svg { width: 1rem; height: 1rem; }
.tree-notes p { font-size: 0.82rem; line-height: 1.35; color: var(--muted); }

/* Trend */
.trend {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  justify-content: center; gap: 1rem;
}
.trend-figure { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 0.4rem; }
.trend-plot {
  flex: 1; min-height: 14rem; display: block;
}
.trend-canvas { position: relative; min-width: 0; min-height: 0; height: 100%; }
.trend-svg {
  display: block; width: 100%; height: 100%; min-height: 0;
  overflow: visible;
}
.trend-grid line { stroke: var(--border); stroke-width: 1; vector-effect: non-scaling-stroke; }
.trend-area { fill: var(--chart-1, var(--accent)); opacity: 0.08; }
.trend-line {
  fill: none; stroke: var(--chart-1, var(--accent)); stroke-width: 2.2;
  stroke-linejoin: round; stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}
.trend-dot {
  position: absolute; width: 0.55rem; height: 0.55rem; border-radius: 50%;
  background: var(--chart-1, var(--accent)); transform: translate(-50%, -50%);
  z-index: 1;
}
.trend-dot-last { width: 0.85rem; height: 0.85rem; }
.trend-line-2 { stroke: var(--chart-2, var(--accent)); }
.trend-dot-series-2 { background: var(--chart-2, var(--accent)); }
.trend-legend {
  display: flex; gap: 1.2rem; flex-wrap: wrap; font-size: 0.78rem;
  color: var(--muted);
}
.trend-legend span { display: inline-flex; align-items: center; gap: 0.4rem; }
.trend-swatch-1, .trend-swatch-2 {
  width: 0.65rem; height: 0.65rem; border-radius: 50%; display: inline-block;
}
.trend-swatch-1 { background: var(--chart-1, var(--accent)); }
.trend-swatch-2 { background: var(--chart-2, var(--accent)); }
.trend-x {
  display: flex; justify-content: space-between;
  font-size: 0.7rem; color: var(--muted);
}
.trend-note { font-size: 0.78rem; color: var(--muted); }

/* Trend dashboard */
.trend-dashboard {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(15rem, 0.8fr);
  gap: 2.2rem; align-items: stretch;
}
.td-main { display: flex; flex-direction: column; gap: 0.9rem; min-width: 0; min-height: 0; }
.td-kpis { display: flex; gap: 0.65rem; }
.td-kpi {
  flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.25rem;
  padding: 0.7rem 0.8rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.td-kpi-head { display: flex; align-items: center; gap: 0.45rem; min-width: 0; }
.kpi-icon { display: inline-flex; color: var(--accent); flex: 0 0 auto; }
.kpi-svg { width: 1.15rem; height: 1.15rem; display: block; }
.td-kpi strong {
  font-family: var(--font-display); font-size: 1.75rem; font-weight: 800;
  line-height: 1; color: var(--accent); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.td-kpi span {
  font-size: 0.7rem; line-height: 1.25; color: var(--muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.td-main .trend-figure { flex: 1; min-height: 0; }
.td-main .trend-plot { flex: 1; height: auto; min-height: 11rem; }
.trend-dashboard .dash-rail { justify-content: center; }

/* Stacked share */
.stacked-share {
  flex: 1; display: flex; flex-direction: column;
  justify-content: space-evenly; gap: 1.8rem;
}
.stacked-figure { display: flex; flex-direction: column; gap: 0.55rem; }
.stacked-bar {
  display: flex; width: 100%; height: 3.4rem; overflow: hidden;
  border: 1px solid var(--border); border-radius: 999px;
  background: var(--surface-alt);
}
.stacked-seg { display: block; height: 100%; min-width: 0.15rem; }
.stacked-seg-1, .stacked-swatch-1 { background: var(--chart-1, var(--accent)); }
.stacked-seg-2, .stacked-swatch-2 { background: var(--chart-2, var(--accent)); }
.stacked-seg-3, .stacked-swatch-3 { background: var(--chart-3, var(--accent)); }
.stacked-seg-4, .stacked-swatch-4 { background: var(--chart-4, var(--accent)); }
.stacked-scale {
  display: flex; justify-content: space-between; font-size: 0.72rem;
  color: var(--muted);
}
.stacked-legend {
  list-style: none; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.05rem 2rem;
}
.stacked-row {
  display: grid; grid-template-columns: 0.8rem minmax(0, 1fr) auto auto;
  gap: 0.7rem; align-items: baseline;
}
.stacked-swatch { width: 0.8rem; height: 0.8rem; border-radius: 2px; }
.stacked-label { font-size: 1.05rem; line-height: 1.3; }
.stacked-value {
  font-family: var(--font-display); font-weight: 800; color: var(--accent);
  white-space: nowrap;
}
.stacked-percent { font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
.orientation-portrait .stacked-legend { grid-template-columns: 1fr; }

/* Dashboard */
.dashboard {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(15rem, 0.8fr);
  gap: 2.2rem; align-items: stretch;
}
.dash-main {
  display: flex; flex-direction: column; justify-content: flex-start;
  gap: 1.1rem; min-width: 0;
}
.dash-bars {
  list-style: none; flex: 1; display: flex; flex-direction: column;
  justify-content: space-evenly; gap: 1.15rem;
}
.dash-donut {
  flex: 1; display: grid; grid-template-columns: minmax(10rem, 15rem) 1fr;
  align-items: center; gap: 1.4rem; min-height: 0;
}
.dash-donut .donut-figure { width: 100%; }
.dash-donut .donut-center strong { font-size: 1.9rem; }
.dash-donut .donut-legend { gap: 0.8rem; }
.dash-donut .donut-legend-label { font-size: 0.92rem; }
.dash-rail {
  border-left: 1px solid var(--border); padding-left: 1.6rem;
  display: flex; flex-direction: column; justify-content: center; gap: 1.05rem;
}
.dash-thesis {
  font-family: var(--font-display); font-size: 1.35rem; line-height: 1.32;
  text-wrap: pretty;
}
.dash-notes { list-style: none; display: flex; flex-direction: column; gap: 0.9rem; }
.dash-note { display: grid; grid-template-columns: 1.8rem 1fr; gap: 0.55rem; }
.dash-note-index {
  font-family: var(--font-display); font-weight: 800; color: var(--accent);
  font-size: 0.82rem; line-height: 1.6;
}
.dash-note p { font-size: 0.92rem; line-height: 1.36; color: var(--muted); }

/* Donut share */
.donut-share {
  flex: 1; min-height: 0; display: flex; flex-direction: column;
  justify-content: flex-start; gap: 1.2rem;
}
.donut-body {
  flex: 1; min-height: 0; display: grid;
  grid-template-columns: minmax(16rem, 22rem) 1fr;
  align-items: center; gap: 2.4rem;
}
.donut-figure { position: relative; width: 100%; aspect-ratio: 1; }
.donut-svg { width: 100%; height: 100%; overflow: visible; }
.donut-track, .donut-seg {
  fill: none; stroke-width: 8.5; stroke-linecap: butt;
}
.donut-track { stroke: var(--surface-alt); }
.donut-seg { stroke: var(--chart-1, var(--accent)); }
.donut-seg-2 { stroke: var(--chart-2, var(--accent)); }
.donut-seg-3 { stroke: var(--chart-3, var(--accent)); }
.donut-seg-4 { stroke: var(--chart-4, var(--accent)); }
.donut-center {
  position: absolute; inset: 0; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 0.1rem; pointer-events: none;
}
.donut-center strong {
  font-family: var(--font-display); font-size: 2.5rem; font-weight: 800;
  line-height: 1; color: var(--ink);
}
.donut-center span {
  font-size: 0.72rem; font-weight: 700; letter-spacing: var(--label-tracking);
  text-transform: uppercase; color: var(--muted);
}
.donut-legend { list-style: none; display: flex; flex-direction: column; gap: 1rem; }
.donut-legend-row {
  display: grid; grid-template-columns: 0.8rem 1fr auto; gap: 0.75rem;
  align-items: baseline;
}
.donut-swatch {
  width: 0.8rem; height: 0.8rem; border-radius: 2px;
  background: var(--chart-1, var(--accent));
}
.donut-swatch-2 { background: var(--chart-2, var(--accent)); }
.donut-swatch-3 { background: var(--chart-3, var(--accent)); }
.donut-swatch-4 { background: var(--chart-4, var(--accent)); }
.donut-legend-label { font-size: 1.08rem; line-height: 1.3; }
.donut-value {
  font-family: var(--font-display); font-weight: 800; color: var(--accent);
  white-space: nowrap;
}
.orientation-portrait .donut-body {
  grid-template-columns: 1fr; justify-items: center; gap: 1.4rem;
}
.orientation-portrait .donut-figure { width: min(18rem, 62vw); }
.orientation-portrait .donut-legend { width: 100%; }
.orientation-landscape .donut-body { grid-template-columns: minmax(14rem, 19rem) 1fr; }
.orientation-landscape .donut-center strong { font-size: 2rem; }

/* Hero */
.hero { flex: 1; min-height: 0; display: grid; grid-template-columns: 1.02fr 1fr; gap: 2.4rem; align-items: center; }
.hero-text { grid-template-columns: 1fr; }
.hero-figure { display: flex; flex-direction: column; gap: 0.7rem; }
.hero-value {
  font-family: var(--font-display); font-weight: 800; color: var(--accent);
  font-size: 9rem; line-height: 0.86; letter-spacing: -0.05em;
}
.hero-label { font-size: 1.22rem; line-height: 1.34; color: var(--muted); max-width: 22ch; }
.hero-copy { display: flex; flex-direction: column; gap: 1.1rem; min-width: 0; }
.orientation-portrait .hero { grid-template-columns: 1fr; align-content: center; gap: 1.6rem; }
.orientation-portrait .hero-value { font-size: 7.6rem; }
.orientation-landscape .title { font-size: 3.35rem; }
.orientation-landscape .hero-value { font-size: 7.4rem; }

/* Timeline */
.timeline { list-style: none; display: grid; gap: 1.05rem; }
.layout-group .timeline { flex: 1; align-content: space-between; position: relative; }
.layout-group .timeline::before {
  content: ""; position: absolute; left: 1.34rem; top: 1.35rem; bottom: 1.35rem;
  width: 2px; background: var(--border);
}
.timeline-item { display: grid; grid-template-columns: 3.1rem 1fr; gap: 1rem; align-items: start; }
.timeline-marker {
  width: 2.7rem; height: 2.7rem; border-radius: 50%;
  display: grid; place-items: center; position: relative; z-index: 1;
  background: var(--accent); color: var(--accent-ink);
  font-family: var(--font-display); font-weight: 800; font-size: 0.95rem;
}
.timeline-body { display: flex; flex-direction: column; gap: 0.2rem; padding-top: 0.35rem; }
.timeline-label { font-family: var(--font-display); font-size: 1.3rem; line-height: 1.2; }
.timeline-detail { color: var(--muted); font-size: 1.02rem; line-height: 1.38; max-width: 46ch; }
.orientation-landscape .layout-group .timeline {
  flex: 1; grid-template-columns: repeat(auto-fit, minmax(0, 1fr));
  grid-auto-rows: 1fr; gap: 2rem; align-content: stretch; padding-top: 0;
}
.orientation-landscape .layout-group .timeline::before {
  left: 0; right: 0; top: 50%; bottom: auto;
  width: auto; height: 2px;
}
.orientation-landscape .timeline-item {
  grid-template-columns: 1fr;
  grid-template-rows: 1fr auto 1fr;
  gap: 0.7rem; justify-items: start; align-items: center;
}
.orientation-landscape .timeline-marker { grid-row: 2; }
.orientation-landscape .timeline-label { font-size: 1.5rem; }
.orientation-landscape .timeline-detail { font-size: 1.08rem; }
.orientation-landscape .timeline-body {
  grid-row: 1; align-self: end; padding: 0 0 0.5rem;
}
.orientation-landscape .timeline-item:nth-child(even) .timeline-body {
  grid-row: 3; align-self: start; padding: 0.5rem 0 0;
}

/* Process */
.steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: 1rem; align-content: start; }
.orientation-portrait .steps { grid-template-columns: 1fr; }
.process-layout { justify-content: space-between; }
.orientation-portrait .process-layout .steps {
  position: relative; padding-left: 2.4rem; gap: 0.65rem;
}
.orientation-portrait .process-layout .steps::before {
  content: ""; position: absolute; left: 0.95rem; top: 1.4rem; bottom: 1.4rem;
  width: 2px; background: var(--border);
}
.orientation-portrait .process-layout .step {
  position: relative; padding: 0.8rem 1rem;
}
.orientation-portrait .process-layout .step::before {
  content: ""; position: absolute; left: -1.72rem; top: 1.6rem;
  width: 0.6rem; height: 0.6rem; border-radius: 50%;
  background: var(--accent); z-index: 2;
}
.orientation-portrait .process-layout .step-number { font-size: 1rem; }
.orientation-portrait .process-layout .step-label { font-size: 1.02rem; }
.process-layout .steps { flex: 0 0 auto; }
.process-thesis {
  font-family: var(--font-display); font-size: 1.15rem; line-height: 1.38;
  color: var(--muted); max-width: 78ch;
}
.process-notes {
  list-style: none; display: grid; grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
}
.process-note {
  display: grid; grid-template-columns: 1.15rem 1fr; gap: 0.55rem;
  align-items: start; padding: 0.7rem 0.8rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.process-note .kpi-svg { width: 1rem; height: 1rem; }
.process-note p { font-size: 0.8rem; line-height: 1.35; color: var(--muted); }
.guard-band {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem;
}
.guard-mitigation { margin-top: 0.25rem; }
.guard-mitigation strong { color: var(--ink); }
.orientation-portrait .illustrated-sequence .guard-band {
  display: none;
}
.guard {
  display: grid; grid-template-columns: 1.3rem 1fr; gap: 0.6rem;
  align-items: start; padding: 0.8rem 0.9rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius);
}
.guard-icon { color: var(--accent); display: inline-flex; margin-top: 0.1rem; }
.guard-icon .kpi-svg { width: 1.1rem; height: 1.1rem; }
.guard h3 {
  font-family: var(--font-display); font-size: 0.78rem; color: var(--accent);
  text-transform: uppercase; letter-spacing: var(--label-tracking);
  margin-bottom: 0.25rem;
}
.guard p { font-size: 0.82rem; line-height: 1.35; color: var(--muted); }
.orientation-portrait .step { justify-content: center; }
.step {
  display: flex; flex-direction: column; gap: 0.55rem; padding: 1.2rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); box-shadow: var(--shadow); min-height: 0;
}
.step-number {
  font-family: var(--font-display); font-weight: 800; color: var(--accent);
  font-size: 2.1rem; line-height: 0.9;
}
.step-label { font-family: var(--font-display); font-size: 1.14rem; line-height: 1.22; }

/* Comparison */
.compare { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr auto 1fr; gap: 1.1rem; align-items: stretch; }
.orientation-portrait .compare { grid-template-columns: 1fr; align-content: center; }
.orientation-portrait .compare-vs { justify-self: center; }
.compare-side {
  display: flex; flex-direction: column; gap: 0.9rem; padding: 1.3rem;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); min-height: 0;
}
.compare-side .claim { background: var(--surface-alt); }
.compare-side-right { border-color: var(--accent); }
.compare-title { font-family: var(--font-display); font-size: 1.5rem; line-height: 1.15; }
.compare-vs {
  align-self: center; font-family: var(--font-display); font-size: 1.1rem;
  font-weight: 800; text-transform: uppercase; letter-spacing: 0.14em;
  color: var(--accent);
}
.compare-verdict {
  font-family: var(--font-display); font-size: 1.18rem; line-height: 1.34;
  border-top: 2px solid var(--accent); padding-top: 0.85rem; margin-top: 0.4rem;
}

/* Statement */
.statement { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 2rem; }
.quote {
  font-family: var(--font-display); font-size: 2.85rem; line-height: 1.16;
  letter-spacing: -0.015em; border-left: 0.42rem solid var(--accent);
  padding-left: 1.5rem; text-wrap: balance;
}
.statement-thesis { font-size: 2.5rem; line-height: 1.2; text-wrap: balance; }
.statement-sub {
  font-family: var(--font-display); font-size: 1.25rem; line-height: 1.35;
  color: var(--muted); max-width: 72ch;
}
.support { width: 100%; max-width: none; }
.statement .claim { grid-template-columns: 2rem minmax(0, 1fr) auto; }
.statement .claim-source {
  max-width: 12rem; overflow: hidden; text-overflow: ellipsis;
}

/* Bento */
.bento { flex: 1; min-height: 0; display: grid; grid-auto-flow: dense; grid-template-columns: repeat(6, 1fr); grid-auto-rows: minmax(0, 1fr); gap: 0.85rem; }
.orientation-portrait .bento { grid-template-columns: repeat(4, 1fr); }
.orientation-landscape .bento { grid-template-columns: repeat(8, 1fr); }
.bento-cell {
  display: flex; flex-direction: column; justify-content: space-between; gap: 0.5rem;
  padding: 1.05rem; overflow: hidden; min-height: 0;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius);
}
.bento-wide { grid-column: span 3; }
.orientation-portrait .bento-wide { grid-column: span 4; }
.orientation-landscape .bento-wide { grid-column: span 4; }
.bento-tall { grid-row: span 2; }
.bento-figure { grid-column: span 2; }
.bento-figure .stat-value { font-size: 4.2rem; }
.bento-stat .stat-value { font-size: 2rem; }
.bento-claim { grid-column: span 2; }
.orientation-portrait .bento-claim { grid-column: span 2; }
.bento-quote { grid-column: span 2; justify-content: center; }
.bento-thesis, .bento-stat, .bento-claim { justify-content: center; }
.bento-quote p { font-family: var(--font-display); font-size: 1.2rem; line-height: 1.3; }
.bento-claim p { font-size: 0.98rem; line-height: 1.36; }
.bento-title { font-family: var(--font-display); font-size: 1.38rem; line-height: 1.24; font-weight: 600; }
.bento-thesis { background: var(--surface-alt); }

/* Footer */
.colophon {
  display: flex; justify-content: space-between; align-items: flex-end; gap: 1.4rem;
  border-top: 1px solid var(--border); padding-top: 0.85rem; margin-top: 1.35rem;
}
.bottom-line { font-size: 1rem; line-height: 1.36; font-weight: 600; max-width: 72ch; }
.bottom-line::before {
  content: "Bottom line"; display: block; font-size: 0.7rem; font-weight: 700;
  letter-spacing: var(--label-tracking); text-transform: uppercase;
  color: var(--accent); margin-bottom: 0.2rem;
}
.citations {
  font-size: 0.7rem; line-height: 1.4; color: var(--muted); text-align: right;
  max-width: 34ch;
}
"""


def _luminance(colour: str) -> float:
    """Relative luminance for choosing readable text on a hex accent."""
    value = colour.lstrip("#")
    if len(value) != 6:
        return 0.0
    try:
        channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    except ValueError:
        return 0.0
    linear = [
        channel / 12.92
        if channel <= 0.03928
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _theme_css(theme: Theme, plan: DesignPlan) -> str:
    css = theme.css_vars()
    if plan.palette:
        accent = plan.palette[0]
        ink = "#111111" if _luminance(accent) > 0.45 else "#ffffff"
        css += f"\n--accent: {accent};\n--accent-ink: {ink};"
    return css


_FIT_CSS = r"""
.poster { padding: 2.6rem 2.8rem 2rem; }
.masthead { margin-bottom: 1.55rem; }
.body { gap: 1.15rem; }
.layout-group { gap: 0.95rem; }
.claim-list { gap: 0.5rem; }
.claim { padding: 0.72rem 0.85rem; }
.steps { gap: 0.75rem; }
.bento { gap: 0.65rem; }
"""


def render_page(
    brief: Brief,
    plan: DesignPlan,
    theme: Theme,
    *,
    fit: str | None = None,
    assets: dict[str, bytes] | None = None,
) -> str:
    """Render the complete HTML document for an artefact.

    ``fit="tight"`` trims padding and gaps for one reflow attempt. Type does not
    shrink, so a retry cannot make the minimum-font check worse.
    """
    if fit not in {None, "tight"}:
        raise ValueError(f"Unknown fit mode {fit!r}.")
    fit_css = _FIT_CSS if fit == "tight" else ""
    layout = get_layout(plan.layout)
    size = ORIENTATIONS[plan.orientation]
    context = LayoutContext(
        brief=brief,
        plan=plan,
        theme=theme,
        size=size,
        assets=assets or {},
    )
    inner = layout.render(context)

    citations = " · ".join(brief.citations)
    citations_html = (
        f'<p class="citations">{_esc(citations)}</p>' if citations else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={size[0]}, height={size[1]}">
<title>{_esc(brief.title)}</title>
<style>
{font_css(theme)}
:root {{
{_theme_css(theme, plan)}
}}
 {BASE_CSS}
 {fit_css}
 </style>
</head>
<body class="orientation-{plan.orientation} density-{plan.density}">
<div class="poster" data-layout="{_esc(layout.id)}" data-theme="{_esc(theme.id)}" data-texture="{_esc(theme.texture)}">
<header class="masthead">
<p class="eyebrow">{_esc(layout.name)}</p>
<h1 class="title">{_esc(brief.title)}</h1>
<p class="dek">{_esc(brief.dek)}</p>
</header>
<main class="body">
{inner}
</main>
<footer class="colophon">
<p class="bottom-line">{_esc(brief.bottom_line)}</p>
{citations_html}
</footer>
</div>
</body>
</html>
"""


def _esc(value: object) -> str:
    import html

    return html.escape(str(value), quote=True)
