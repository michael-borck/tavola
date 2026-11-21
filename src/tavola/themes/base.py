"""Theme tokens: a style pack is colour, type, shape, and texture only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """One style pack. Emitted as CSS custom properties, never as layout code."""

    id: str
    name: str
    description: str
    bg: str
    surface: str
    surface_alt: str
    ink: str
    muted: str
    accent: str
    accent_ink: str
    border: str
    radius: str
    shadow: str
    font_display: str
    font_body: str
    label_tracking: str
    texture: str = "none"
    chart_colors: tuple[str, ...] = ()

    def css_vars(self) -> str:
        values = [
            f"--bg: {self.bg};",
            f"--surface: {self.surface};",
            f"--surface-alt: {self.surface_alt};",
            f"--ink: {self.ink};",
            f"--muted: {self.muted};",
            f"--accent: {self.accent};",
            f"--accent-ink: {self.accent_ink};",
            f"--border: {self.border};",
            f"--radius: {self.radius};",
            f"--shadow: {self.shadow};",
            f"--font-display: {self.font_display};",
            f"--font-body: {self.font_body};",
            f"--label-tracking: {self.label_tracking};",
        ]
        values.extend(
            f"--chart-{index}: {colour};"
            for index, colour in enumerate(self.chart_colors[:5], start=1)
        )
        return "\n".join(values)


_THEMES: dict[str, Theme] = {}


def register(theme: Theme) -> Theme:
    if theme.id in _THEMES:
        raise ValueError(f"Theme id {theme.id!r} is already registered.")
    if theme.texture not in {"none", "grain", "grid"}:
        raise ValueError(f"Unknown texture {theme.texture!r} for {theme.id!r}.")
    _THEMES[theme.id] = theme
    return theme


def get_theme(theme_id: str) -> Theme:
    try:
        return _THEMES[theme_id]
    except KeyError:
        known = ", ".join(sorted(_THEMES)) or "none"
        raise KeyError(f"Unknown style {theme_id!r}; known: {known}.") from None


def catalog() -> list[Theme]:
    return [_THEMES[key] for key in sorted(_THEMES)]


def theme_ids() -> list[str]:
    return sorted(_THEMES)
