"""Local FastAPI app: one screen, one Generate.

Keys stay in the process. The browser never receives provider credentials.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from tavola.assets import ILLUSTRATION_STYLES
from tavola.brief import BriefError
from tavola.config import (
    DENSITIES,
    ORIENTATIONS,
    ConfigurationError,
    load_config,
    resolve_design_settings,
    resolve_illustration_settings,
    resolve_llm_settings,
    resolve_serve_settings,
)
from tavola.content import ContentError, Source, clean_text, read_source
from tavola.core import (
    GenerateError,
    GenerateOptions,
    generate,
    save_result,
    slugify,
)
from tavola.design import DesignError
from tavola.layouts import catalog as layout_catalog
from tavola.llm import LLMError
from tavola.render.browser import RenderError
from tavola.themes import catalog as theme_catalog

_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class GenerateRequest(BaseModel):
    text: str = ""
    url: str = ""
    layout: str | None = None
    style: str | None = None
    orientation: str | None = None
    density: str | None = None
    mode: str | None = None
    illustration_enabled: bool | None = None
    illustration_style: str | None = None
    illustration_direction: str | None = None
    language: str | None = None


def create_app(config: dict[str, Any] | None = None):  # type: ignore[no-untyped-def]
    """Build the FastAPI app. Imports FastAPI lazily so the CLI stays light."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as e:  # pragma: no cover - optional extra
        raise ConfigurationError(
            "The web UI needs FastAPI: pip install 'tavola[serve]'."
        ) from e

    settings = config if config is not None else load_config()
    serve_settings = resolve_serve_settings(settings)
    out_dir = Path(str(serve_settings["out_dir"]))
    out_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Tavola", docs_url=None, redoc_url=None)
    app.state.gallery = []
    app.mount("/files", StaticFiles(directory=out_dir), name="files")
    app.mount(
        "/previews",
        StaticFiles(directory=Path(__file__).with_name("previews")),
        name="previews",
    )

    page = Path(__file__).with_name("serve_page.html").read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return page

    @app.get("/api/meta")
    def meta() -> dict[str, Any]:
        design = resolve_design_settings(settings)
        illustration = resolve_illustration_settings(settings)
        provider: dict[str, Any] = {"label": "", "model": None, "ready": False}
        try:
            llm = resolve_llm_settings(settings)
            provider = {
                "label": llm.get("provider"),
                "model": llm.get("model"),
                "ready": True,
            }
        except ConfigurationError as e:
            provider["error"] = str(e)
        return {
            "layouts": [
                {
                    "id": layout.id,
                    "name": layout.name,
                    "description": layout.description,
                    "needs": list(layout.needs),
                    "min_claims": layout.min_claims,
                    "max_claims": layout.max_claims,
                    "orientations": list(layout.orientations),
                }
                for layout in layout_catalog()
            ],
            "styles": [
                {"id": theme.id, "name": theme.name, "description": theme.description}
                for theme in theme_catalog()
            ],
            "orientations": {
                name: {"width": size[0], "height": size[1]}
                for name, size in ORIENTATIONS.items()
            },
            "densities": list(DENSITIES),
            "modes": ["structured", "illustrated", "auto"],
            "illustration_styles": [
                {"id": key, "name": value.name, "description": value.description}
                for key, value in ILLUSTRATION_STYLES.items()
            ],
            "defaults": {**design, "illustration": illustration},
            "provider": provider,
            "out_dir": str(out_dir),
        }

    @app.post("/api/generate")
    def generate_endpoint(payload: GenerateRequest) -> dict[str, Any]:
        try:
            options = GenerateOptions(
                layout=payload.layout or None,
                style=payload.style or None,
                orientation=payload.orientation or None,
                density=payload.density or None,
                mode=payload.mode or None,
                illustration_enabled=payload.illustration_enabled,
                illustration_style=payload.illustration_style or None,
                illustration_direction=payload.illustration_direction,
                language=payload.language or None,
            )
            if payload.url.strip():
                source = read_source(payload.url.strip())
            elif payload.text.strip():
                source = Source(
                    text=clean_text(payload.text),
                    title="Pasted text",
                    kind="text",
                )
            else:
                raise HTTPException(400, "Paste text or give a URL first.")

            result = generate(source, config=settings, options=options)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{stamp}-{slugify(result.brief.title)}.png"
            saved = save_result(result, out_dir / filename, config=settings)
        except HTTPException:
            raise
        except (
            ConfigurationError,
            ContentError,
            LLMError,
            BriefError,
            DesignError,
            GenerateError,
            RenderError,
        ) as e:
            raise HTTPException(400, str(e)) from e

        item = {
            "id": filename,
            "url": f"/files/{filename}",
            "filename": saved.artefact.name,
            "sidecar": saved.sidecar.name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "title": result.brief.title,
            "dek": result.brief.dek,
            "thesis": result.brief.thesis,
            "bottom_line": result.brief.bottom_line,
            "citations": result.brief.citations,
            "claims": [claim.model_dump() for claim in result.brief.claims],
            "layout": result.plan.layout,
            "style": result.plan.style,
            "orientation": result.plan.orientation,
            "density": result.plan.density,
            "width": result.width,
            "height": result.height,
            "warnings": result.warnings,
            "quality": {
                "passed": result.quality.passed,
                "warnings": [issue.message for issue in result.quality.warnings],
            },
        }
        gallery: list[dict[str, Any]] = app.state.gallery
        gallery.insert(0, item)
        del gallery[12:]
        return item

    @app.get("/api/gallery")
    def gallery() -> list[dict[str, Any]]:
        return app.state.gallery

    return app


def _watch_parent(parent_pid: int) -> None:
    """Exit when the desktop shell closes the stdin pipe it handed us.

    Closing stdin is reliable even when the shell is killed, where a PID check
    can keep seeing a zombie parent.
    """
    del parent_pid
    try:
        sys.stdin.buffer.read()
    except OSError:
        pass
    os._exit(0)


def run_server(
    config: dict[str, Any] | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 5827,
    parent_pid: int | None = None,
) -> None:
    """Start uvicorn, refusing to bind beyond localhost in v0.1."""
    if host not in _LOOPBACK:
        raise ConfigurationError(
            "v0.1 serves only on localhost. Pass --host 127.0.0.1, or wait for "
            "the authenticated remote mode."
        )
    try:
        import uvicorn
    except ImportError as e:  # pragma: no cover - optional extra
        raise ConfigurationError(
            "Serving needs uvicorn: pip install 'tavola[serve]'."
        ) from e
    if parent_pid is not None:
        threading.Thread(
            target=_watch_parent, args=(parent_pid,), daemon=True
        ).start()
    uvicorn.run(create_app(config), host=host, port=port, log_level="info")
