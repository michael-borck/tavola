"""Text-free illustration assets for the illustrated compositions."""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from tavola.brief import Brief

if TYPE_CHECKING:
    from tavola.themes import Theme


@dataclass(frozen=True)
class IllustrationStyle:
    id: str
    name: str
    description: str
    prompt: str


ILLUSTRATION_STYLES: dict[str, IllustrationStyle] = {
    "editorial": IllustrationStyle(
        "editorial",
        "Editorial",
        "Flat editorial illustration, warm muted palette, simple shapes.",
        "flat editorial illustration, screen-print texture, warm muted palette, "
        "simple confident shapes, generous negative space",
    ),
    "clay": IllustrationStyle(
        "clay",
        "Clay",
        "Soft 3D clay render with tactile matte materials.",
        "soft 3D clay render, rounded tactile shapes, matte materials, "
        "warm studio lighting, shallow depth of field",
    ),
    "sketch": IllustrationStyle(
        "sketch",
        "Sketch",
        "Loose ink and watercolour with paper grain.",
        "loose hand-drawn ink and watercolour editorial illustration, paper "
        "grain, imperfect lines, restrained accent colour",
    ),
    "minimal": IllustrationStyle(
        "minimal",
        "Minimal",
        "Geometric vector shapes with a two-colour palette.",
        "minimal geometric vector illustration, two-colour palette, clean "
        "silhouettes, lots of negative space",
    ),
    "papercut": IllustrationStyle(
        "papercut",
        "Papercut",
        "Layered paper shapes with tactile edges and shadows.",
        "layered paper-cut editorial illustration, torn paper edges, soft "
        "shadows, tactile paper texture, limited colour palette",
    ),
    "cinematic": IllustrationStyle(
        "cinematic",
        "Cinematic",
        "Dramatic light, atmosphere, and depth.",
        "cinematic editorial illustration, dramatic directional light, "
        "atmospheric depth, rich shadows, restrained colour",
    ),
}


class AssetError(Exception):
    """Raised when a text-free asset cannot be produced."""


_ASPECT = {"square": "1:1", "portrait": "4:5", "landscape": "16:9"}
_ORIENTATION = {
    "square": "square",
    "portrait": "portrait",
    "landscape": "landscape",
}


def build_hero_prompt(
    brief: Brief,
    style: str,
    direction: str = "",
    *,
    orientation: str = "portrait",
    theme: Theme | None = None,
) -> str:
    extra = f" Art direction: {direction.strip()}." if direction.strip() else ""
    palette = ""
    if theme is not None:
        palette = (
            f" Palette: anchor the image with {theme.accent} as the accent, "
            f"keep neutrals compatible with {theme.bg} and {theme.ink}. "
        )
    return (
        "Create a text-free editorial illustration for a one-page infographic. "
        f"Subject: {brief.title}. Idea: {brief.thesis}. "
        f"Style: {style}.{extra}{palette}"
        f"Format: {_ORIENTATION.get(orientation, 'portrait')} composition. "
        "The layout will overlay type on the left side. Keep the left 55% calm, "
        "low-contrast, and free of important detail; place the subject toward "
        "the right. "
        "Do not include any words, letters, numbers, labels, logos, signage, "
        "watermarks, UI, or charts. No text in the image. "
        "Use a restrained editorial palette and simple, confident shapes."
    )


def generate_hero(
    brief: Brief,
    *,
    illustration: dict[str, Any],
    llm: dict[str, Any],
    orientation: str = "portrait",
    theme: Theme | None = None,
) -> bytes:
    """Generate (or reuse) one text-free hero image."""
    provider = str(illustration.get("provider") or "off")
    if provider in {"off", "none", ""}:
        raise AssetError("Illustration provider is disabled.")
    if provider != "gemini":
        raise AssetError(f"Unsupported illustration provider {provider!r}.")

    model = str(illustration.get("model") or "gemini-2.5-flash-image")
    style = str(
        illustration.get("style")
        or "flat editorial illustration, warm muted palette, simple shapes"
    )
    prompt = build_hero_prompt(
        brief,
        style,
        str(illustration.get("direction") or ""),
        orientation=orientation,
        theme=theme,
    )
    cache_root = Path(
        os.path.expanduser(
            str(illustration.get("cache_dir") or "~/.cache/tavola/assets")
        )
    )
    key = hashlib.sha256(
        f"{provider}|{model}|{orientation}|{prompt}".encode()
    ).hexdigest()
    cache_path = cache_root / f"{key}.png"
    if cache_path.exists():
        return cache_path.read_bytes()

    if not llm.get("api_key"):
        raise AssetError("No Gemini API key for the illustration provider.")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": _ASPECT.get(orientation, "4:5")},
        },
    }
    try:
        response = requests.post(
            f"{str(llm['base_url']).rstrip('/')}/v1beta/models/{model}:generateContent",
            params={"key": str(llm["api_key"])},
            json=body,
            timeout=float(illustration.get("timeout") or 180),
        )
    except requests.RequestException as e:
        raise AssetError(f"Could not reach the image model: {e}") from e
    if response.status_code >= 400:
        raise AssetError(
            f"Image model returned {response.status_code}: "
            f"{response.text.strip() or response.reason}"
        )
    data = response.json()
    candidates = data.get("candidates") if isinstance(data, dict) else None
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        for part in parts or []:
            if not isinstance(part, dict):
                continue
            inline = part.get("inlineData")
            if isinstance(inline, dict) and inline.get("data"):
                image = base64.b64decode(inline["data"])
                cache_root.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(image)
                return image
    raise AssetError("The image model returned no image.")
