"""Command line interface: ``tavola SOURCE`` is the default command."""

from __future__ import annotations

import importlib.util
import json
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from typer.core import TyperGroup

from tavola import __version__
from tavola.brief import Brief, BriefError
from tavola.config import (
    DENSITIES,
    ORIENTATIONS,
    ConfigurationError,
    load_config,
    resolve_design_settings,
    resolve_illustration_settings,
    resolve_llm_settings,
    resolve_render_settings,
    resolve_serve_settings,
    save_example_config,
)
from tavola.content import ContentError
from tavola.core import (
    GenerateError,
    GenerateOptions,
    default_filename,
    generate,
    generate_from_brief,
    save_result,
)
from tavola.design import DesignError
from tavola.layouts import catalog as layout_catalog
from tavola.llm import LLMError, get_provider
from tavola.render.browser import RenderError
from tavola.themes import catalog as theme_catalog

console = Console()

_GROUP_OPTIONS = {"--help", "-h", "--version", "-V", "--init-config"}


class DefaultCommandGroup(TyperGroup):
    """Let ``tavola report.pdf`` mean ``tavola generate report.pdf``."""

    default_command = "generate"

    def parse_args(self, ctx, args):  # type: ignore[no-untyped-def]
        if args:
            first = args[0].split("=", 1)[0]
            if first not in self.list_commands(ctx) and first not in _GROUP_OPTIONS:
                args = [self.default_command, *args]
        return super().parse_args(ctx, args)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"tavola {__version__}")
        raise typer.Exit()


app = typer.Typer(
    cls=DefaultCommandGroup,
    add_completion=False,
    help="Turn one source into one well-designed infographic.",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
    init_config: bool = typer.Option(
        False,
        "--init-config",
        help="Write an example tavola.yaml in the current directory and exit.",
    ),
) -> None:
    if init_config:
        try:
            path = save_example_config()
        except ConfigurationError as e:
            _fail(e)
        console.print(f"Wrote [bold]{path}[/bold]. Edit it, then run [bold]tavola SOURCE[/bold].")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command("generate")
def generate_command(
    source: str | None = typer.Argument(
        None, help="A file path or an http(s) URL. Optional with --brief."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Write .png, .pdf, or .html. Default: title.png."
    ),
    brief_file: Path | None = typer.Option(
        None, "--brief", help="Use a JSON Brief and skip extraction."
    ),
    layout: str | None = typer.Option(None, "--layout", help="Force a layout id."),
    style: str | None = typer.Option(None, "--style", help="Force a style id."),
    orientation: str | None = typer.Option(
        None, "--orientation", help="square | portrait | landscape."
    ),
    density: str | None = typer.Option(
        None, "--density", help="concise | standard | detailed."
    ),
    mode: str | None = typer.Option(
        None, "--mode", help="structured | illustrated | auto."
    ),
    illustration_style: str | None = typer.Option(
        None,
        "--illustration-style",
        help="editorial | clay | sketch | minimal",
    ),
    illustration_direction: str | None = typer.Option(
        None,
        "--illustration-direction",
        help="Optional art direction for the generated hero image.",
    ),
    language: str | None = typer.Option(
        None, "--language", help="Write the brief in this language."
    ),
    candidates: int | None = typer.Option(
        None,
        "--candidates",
        min=1,
        max=5,
        help="Render N candidates and keep the best (needs a vision judge).",
    ),
    judge: str | None = typer.Option(
        None,
        "--judge",
        help="Vision judge: auto, none, or a provider label.",
    ),
    router: str | None = typer.Option(
        None,
        "--router",
        help="System One router: off, auto, or tev.",
    ),
    llm: str | None = typer.Option(
        None, "--llm", help="ollama | openai-compatible | gemini | anthropic."
    ),
    model: str | None = typer.Option(None, "--model", help="Override the model."),
    base_url: str | None = typer.Option(
        None, "--base-url", help="Override the provider base URL."
    ),
    api_key: str | None = typer.Option(
        None, "--api-key", help="Override the provider key (prefer ${VAR})."
    ),
    config_path: str | None = typer.Option(
        None, "--config", help="Use this config file instead of ./tavola.yaml."
    ),
) -> None:
    """Generate one infographic from one source or a saved Brief."""
    try:
        config = load_config(config_path)
        if llm:
            config["llm"] = llm
        if model:
            config["model"] = model
        if base_url:
            config["base_url"] = base_url
        if api_key:
            config["api_key"] = api_key

        options = GenerateOptions(
            layout=layout,
            style=style,
            orientation=orientation,
            density=density,
            mode=mode,
            illustration_style=illustration_style,
            illustration_direction=illustration_direction,
            language=language,
            candidates=candidates,
            judge=judge,
            router=router,
        )
        progress = _progress_printer()
        if brief_file is not None:
            result = generate_from_brief(
                _load_brief(brief_file),
                config=config,
                options=options,
                on_progress=progress,
                source_title=brief_file.stem,
                source_origin=str(brief_file),
            )
        elif source:
            result = generate(
                source,
                config=config,
                options=options,
                on_progress=progress,
            )
        else:
            raise GenerateError("Give a source or --brief.")
        target = output or Path(default_filename(result))
        saved = save_result(result, target, config=config)
    except (
        ConfigurationError,
        ContentError,
        LLMError,
        BriefError,
        DesignError,
        GenerateError,
        RenderError,
    ) as e:
        _fail(e)

    for warning in result.warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")
    for issue in result.quality.warnings:
        console.print(f"[yellow]warning:[/yellow] {issue.message}")

    console.print(
        f"[green]✓[/green] [bold]{saved.artefact}[/bold]  "
        f"[dim]{result.width}×{result.height} · {result.plan.layout} · "
        f"{result.plan.style}[/dim]"
    )
    console.print(f"[dim]Sidecar: {saved.sidecar}[/dim]")


@app.command("layouts")
def list_layouts() -> None:
    """List the layout catalog."""
    table = Table(title="Layouts", show_lines=False)
    table.add_column("id", style="bold cyan", no_wrap=True)
    table.add_column("name")
    table.add_column("claims", justify="center")
    table.add_column("orientations")
    table.add_column("description", overflow="fold")
    for layout in layout_catalog():
        table.add_row(
            layout.id,
            layout.name,
            f"{layout.min_claims}-{layout.max_claims}",
            ", ".join(layout.orientations),
            layout.description,
        )
    console.print(table)


@app.command("styles")
def list_styles() -> None:
    """List the style packs."""
    table = Table(title="Styles")
    table.add_column("id", style="bold cyan", no_wrap=True)
    table.add_column("name")
    table.add_column("description", overflow="fold")
    for theme in theme_catalog():
        table.add_row(theme.id, theme.name, theme.description)
    console.print(table)


@app.command("models")
def list_models(
    config_path: str | None = typer.Option(
        None, "--config", help="Use this config file instead of ./tavola.yaml."
    ),
) -> None:
    """List the models the configured provider reports."""
    try:
        config = load_config(config_path)
        settings = resolve_llm_settings(config)
        provider = get_provider(settings)
        names = provider.models()
    except (ConfigurationError, LLMError) as e:
        _fail(e)

    if not names:
        console.print("The provider did not report any models.")
        return
    console.print(
        f"[dim]{settings['provider']} @ {settings['base_url']}[/dim]"
    )
    for name in names:
        console.print(f"  [bold]{name}[/bold]" if name == settings["model"] else f"  {name}")


@app.command()
def health(
    config_path: str | None = typer.Option(
        None, "--config", help="Use this config file instead of ./tavola.yaml."
    ),
    connect: bool = typer.Option(
        False, "--connect", help="Also ask the provider for its model list."
    ),
) -> None:
    """Check configuration, paths, and optional provider reachability."""
    try:
        config = load_config(config_path)
        llm = resolve_llm_settings(config)
        design = resolve_design_settings(config)
        render = resolve_render_settings(config)
        illustration = resolve_illustration_settings(config)
        serve = resolve_serve_settings(config)
    except ConfigurationError as e:
        _fail(e)

    playwright = importlib.util.find_spec("playwright") is not None
    table = Table(title="Tavola health", show_header=False)
    table.add_column("check", style="bold")
    table.add_column("value")
    table.add_row("provider", str(llm["provider"]))
    table.add_row("endpoint", str(llm["base_url"]))
    table.add_row("model", str(llm["model"] or "(unset)"))
    table.add_row("api key", "set" if llm["api_key"] else "not set")
    table.add_row("layouts", str(len(layout_catalog())))
    table.add_row("styles", str(len(theme_catalog())))
    table.add_row(
        "default",
        f"{design['mode']} · {design['layout']} · {design['style']} · "
        f"{design['orientation']} · {design['density']}",
    )
    table.add_row(
        "variants",
        f"{design['candidates']} candidate(s) · judge {design['judge']} · "
        f"router {design['router']}",
    )
    table.add_row(
        "illustration",
        f"{illustration['provider']} · {illustration['preset']} · "
        f"{illustration['model']}",
    )
    table.add_row("fonts", "Inter, Source Serif 4, Caveat (bundled OFL)")
    table.add_row(
        "png/pdf",
        f"playwright {'installed' if playwright else 'missing'} · "
        f"{render['scale']}x · measure {'on' if render.get('measure') else 'off'}",
    )
    table.add_row("serve", f"{serve['host']}:{serve['port']} → {serve['out_dir']}")
    console.print(table)

    if connect:
        try:
            names = get_provider(llm).models()
        except LLMError as e:
            _fail(f"Connection check failed: {e}")
        console.print(f"[green]Connected.[/green] {len(names)} model(s) reported.")


@app.command()
def formats() -> None:
    """List the exact output sizes."""
    table = Table(title="Formats")
    table.add_column("orientation", style="bold cyan")
    table.add_column("pixels")
    table.add_column("use")
    uses = {
        "square": "social posts",
        "portrait": "reading and phone summaries",
        "landscape": "slides and documents",
    }
    for name, (width, height) in ORIENTATIONS.items():
        table.add_row(name, f"{width} × {height}", uses.get(name, ""))
    console.print(table)
    console.print(f"[dim]Densities: {', '.join(DENSITIES)}[/dim]")


@app.command()
def serve(
    host: str | None = typer.Option(None, "--host", help="Bind address (localhost only)."),
    port: int | None = typer.Option(None, "--port", help="Port."),
    out_dir: Path | None = typer.Option(
        None, "--out-dir", help="Where generated images are saved."
    ),
    parent_pid: int | None = typer.Option(
        None, "--parent-pid", hidden=True, help="Exit when this process goes away."
    ),
    open_browser: bool = typer.Option(
        False, "--open", help="Open the browser after the server starts."
    ),
) -> None:
    """Run the local web UI."""
    from tavola.serve import run_server

    try:
        config = load_config()
        settings = resolve_serve_settings(config)
        resolved_host = host or str(settings["host"])
        resolved_port = int(port or settings["port"])
        if out_dir:
            config.setdefault("serve", {})["out_dir"] = str(out_dir)
        if open_browser:
            webbrowser.open(f"http://{resolved_host}:{resolved_port}/")
        run_server(
            config,
            host=resolved_host,
            port=resolved_port,
            parent_pid=parent_pid,
        )
    except (ConfigurationError, OSError) as e:
        _fail(e)


def _progress_printer() -> Callable[[str], None]:
    def report(message: str) -> None:
        console.print(f"[dim]{message}[/dim]")

    return report


def _load_brief(path: Path) -> Brief:
    target = path.expanduser()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except OSError as e:
        raise BriefError(f"Could not read {target}: {e}") from e
    except json.JSONDecodeError as e:
        raise BriefError(f"{target} is not valid JSON: {e}") from e
    try:
        return Brief.model_validate(payload)
    except ValidationError as e:
        raise BriefError(f"{target} is not a valid Brief: {e}") from e


def _fail(error: object) -> NoReturn:
    console.print(f"[red]error:[/red] {error}")
    raise typer.Exit(code=1)
