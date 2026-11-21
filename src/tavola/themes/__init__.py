"""Theme registry."""

# pyright: reportUnusedImport=false

from tavola.themes import builtin  # noqa: E402,F401  (registers built-ins)
from tavola.themes.base import Theme, catalog, get_theme, register, theme_ids

__all__ = ["Theme", "catalog", "get_theme", "register", "theme_ids"]
