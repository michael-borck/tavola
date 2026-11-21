"""Layout registry. Importing this package registers the built-in catalog."""

# pyright: reportUnusedImport=false

from tavola.layouts import (  # noqa: E402,F401  (registration side effects)
    antv_comparison,
    antv_hierarchy,
    antv_sequence,
    bar_share,
    bento,
    comparison,
    dashboard,
    donut_share,
    grouped_bars,
    hero_stat,
    hierarchy,
    illustrated,
    illustrated_comparison,
    illustrated_quote,
    illustrated_sequence,
    illustrated_trend,
    poster,
    process,
    quadrant,
    stacked_share,
    stat_row,
    statement,
    timeline,
    trend,
    trend_dashboard,
)
from tavola.layouts.base import (
    Layout,
    LayoutContext,
    catalog,
    get_layout,
    layout_ids,
    register,
)

__all__ = [
    "Layout",
    "LayoutContext",
    "catalog",
    "get_layout",
    "layout_ids",
    "register",
]
