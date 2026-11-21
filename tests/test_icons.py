"""Bundled icon selection and rendering."""

from __future__ import annotations

from tavola.icons import icon_for, icon_html, icon_svg


def test_icon_keyword_mapping() -> None:
    assert icon_for("street-tree shade") == "leaf"
    assert icon_for("peak temperature") == "thermometer"
    assert icon_for("rainfall intercepted", "one tree") == "droplets"
    assert icon_for("maintenance cost") == "coins"


def test_icon_falls_back_and_has_no_external_urls() -> None:
    assert icon_for("a strange metric") == "chart-no-axes-column"
    svg = icon_svg("leaf")
    assert "<svg" in svg
    assert "http://" not in svg
    assert "http://" not in icon_html("tree")
