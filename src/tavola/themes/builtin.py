"""Built-in style packs.

Each style names its bundled OFL families first, with system fallbacks for
glyphs outside the latin subset. The renderer embeds only the families a theme
uses, so there is no network request at render time.
"""

from __future__ import annotations

from tavola.themes.base import Theme, register

register(
    Theme(
        id="professional",
        name="Professional",
        description="Deep navy, one amber accent, a clean sans for reports and briefings.",
        bg="#0b1220",
        surface="#121c2f",
        surface_alt="#18243a",
        ink="#f4f7fb",
        muted="#a7b4c9",
        accent="#f4b942",
        accent_ink="#1a1206",
        border="#26344d",
        radius="18px",
        shadow="0 24px 60px rgba(0, 0, 0, 0.45)",
        font_display=(
            '"Inter", "SF Pro Display", "Helvetica Neue", "Segoe UI", '
            "Arial, sans-serif"
        ),
        font_body=(
            '"Inter", "SF Pro Text", "Helvetica Neue", "Segoe UI", Arial, sans-serif'
        ),
        label_tracking="0.16em",
        texture="grid",
        chart_colors=(
            "#f4b942",
            "#6ec6e6",
            "#f08a75",
            "#8fd6b0",
            "#b7a6e6",
        ),
    )
)

register(
    Theme(
        id="scientific",
        name="Scientific",
        description="Paper white, ink black, teal accent, serif type for research.",
        bg="#f7f5ef",
        surface="#ffffff",
        surface_alt="#efece3",
        ink="#1c2422",
        muted="#5b6660",
        accent="#0f766e",
        accent_ink="#ffffff",
        border="#d9d5ca",
        radius="10px",
        shadow="0 10px 28px rgba(28, 36, 34, 0.10)",
        font_display=(
            '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", '
            "Palatino, Georgia, serif"
        ),
        font_body=(
            '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", '
            "Palatino, Georgia, serif"
        ),
        label_tracking="0.12em",
        texture="none",
        chart_colors=(
            "#0f766e",
            "#356a9a",
            "#b07a28",
            "#a54b3c",
            "#6d7f44",
        ),
    )
)

register(
    Theme(
        id="editorial",
        name="Editorial",
        description="Cream paper, oxblood accent, high-contrast serif for essays.",
        bg="#f3ece1",
        surface="#fbf7f0",
        surface_alt="#e8ddcd",
        ink="#221a17",
        muted="#6b5a51",
        accent="#8f2d2d",
        accent_ink="#fff7ee",
        border="#d8c8b4",
        radius="4px",
        shadow="0 14px 34px rgba(34, 26, 23, 0.12)",
        font_display=(
            '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", '
            "Palatino, Georgia, serif"
        ),
        font_body=(
            '"Source Serif 4", "Charter", "Iowan Old Style", '
            '"Palatino Linotype", Georgia, serif'
        ),
        label_tracking="0.18em",
        texture="grain",
        chart_colors=(
            "#8f2d2d",
            "#34516f",
            "#b2852f",
            "#6f7a4a",
            "#a35a63",
        ),
    )
)

register(
    Theme(
        id="sketch",
        name="Sketch",
        description="Warm paper, ink blue, hand-drawn borders for workshops and notes.",
        bg="#fbf8ef",
        surface="#ffffff",
        surface_alt="#f0ecdf",
        ink="#1e2a38",
        muted="#566478",
        accent="#2563eb",
        accent_ink="#ffffff",
        border="#9fb0c7",
        radius="14px",
        shadow="4px 4px 0 rgba(30, 42, 56, 0.85)",
        font_display=(
            '"Caveat", "Bradley Hand", "Chalkboard SE", "Segoe Print", '
            '"Comic Sans MS", cursive'
        ),
        font_body=(
            '"Inter", "Avenir Next", "Segoe UI", "Helvetica Neue", Arial, '
            "sans-serif"
        ),
        label_tracking="0.10em",
        texture="grid",
        chart_colors=(
            "#2563eb",
            "#e07a2f",
            "#3a8b5c",
            "#7c5cbf",
            "#d64545",
        ),
    )
)

register(
    Theme(
        id="noir",
        name="Noir",
        description="Near-black paper, bone white type, one red accent for hard-edged briefings.",
        bg="#08090b",
        surface="#121318",
        surface_alt="#1b1d24",
        ink="#f4f1ea",
        muted="#a6a39c",
        accent="#e5484d",
        accent_ink="#0b0b0d",
        border="#2b2e38",
        radius="6px",
        shadow="0 20px 50px rgba(0, 0, 0, 0.55)",
        font_display=(
            '"Inter", "SF Pro Display", "Helvetica Neue", "Segoe UI", '
            "Arial, sans-serif"
        ),
        font_body=(
            '"Inter", "SF Pro Text", "Helvetica Neue", "Segoe UI", Arial, sans-serif'
        ),
        label_tracking="0.18em",
        texture="none",
        chart_colors=("#e5484d", "#f4b942", "#6ec6e6", "#a78bfa", "#8fd6b0"),
    )
)

register(
    Theme(
        id="warm",
        name="Warm",
        description="Soft paper, rust accent, serif headlines for human, magazine-like pages.",
        bg="#fbf4e8",
        surface="#fffaf2",
        surface_alt="#f2e4d1",
        ink="#2a1d16",
        muted="#6f5b4c",
        accent="#b54f1d",
        accent_ink="#fffaf2",
        border="#e5d1ba",
        radius="14px",
        shadow="0 16px 36px rgba(42, 29, 22, 0.12)",
        font_display=(
            '"Source Serif 4", "Iowan Old Style", "Palatino Linotype", '
            "Palatino, Georgia, serif"
        ),
        font_body=(
            '"Inter", "SF Pro Text", "Helvetica Neue", "Segoe UI", Arial, sans-serif'
        ),
        label_tracking="0.12em",
        texture="grain",
        chart_colors=("#b54f1d", "#0f766e", "#b08d57", "#6b7f3f", "#8f2d2d"),
    )
)
