"""Gloom CLI - Google Cloud Context & ADC Switching.

A high-performance CLI for managing gcloud configurations and
Application Default Credentials via symlink manipulation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table

from gloom import __version__
from gloom.core.adc import ADCError, ADCManager, ADCNotFoundError
from gloom.core.config import GloomConfig
from gloom.core.gcloud import GcloudConfig
from gloom.utils.logger import console, print_error, print_info, print_success, print_warning

# Main app
app = typer.Typer(
    name="gloom",
    help="🌙 High-performance Google Cloud context & ADC switching",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Cache subcommand group
cache_app = typer.Typer(
    name="cache",
    help="Manage cached ADC contexts",
    no_args_is_help=True,
)
app.add_typer(cache_app, name="cache")

# Config subcommand group
config_app = typer.Typer(
    name="config",
    help="Manage gcloud configurations",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold]gloom[/bold] version [cyan]{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """🌙 Gloom - High-performance Google Cloud context & ADC switching."""
    pass


# =============================================================================
# Core Commands
# =============================================================================


@app.command("list", help="List all cached ADC contexts")
def list_contexts(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed information"),
    ] = False,
) -> None:
    """List all cached ADC contexts."""
    config = GloomConfig()
    adc_mgr = ADCManager(config)

    projects = adc_mgr.list_cached_projects()
    current_name, _ = adc_mgr.get_current_context()

    if not projects:
        print_warning("No cached contexts found. Use 'gloom cache add <name>' to add one.")
        raise typer.Exit(0)

    table = Table(title="Cached ADC Contexts", show_header=True, header_style="bold")
    table.add_column("", width=2)  # Active indicator
    table.add_column("Name", style="project")
    table.add_column("Project ID")
    table.add_column("Account", style="account")

    if verbose:
        table.add_column("Path", style="path")

    for project in projects:
        is_active = project.name == current_name
        indicator = "[active]●[/active]" if is_active else " "

        row = [
            indicator,
            project.name,
            project.project_id or "-",
            project.account or "-",
        ]

        if verbose:
            row.append(str(project.adc_path) if project.adc_path else "-")

        table.add_row(*row)

    console.print(table)


@app.command("switch", help="Switch to a cached ADC context")
def switch_context(
    name: Annotated[str, typer.Argument(help="Name of the cached context to switch to")],
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
) -> None:
    """Switch to a cached ADC context."""
    config = GloomConfig()
    adc_mgr = ADCManager(config)

    try:
        project = adc_mgr.switch_context(name)

        if not quiet:
            print_success(f"Switched to context: [project]{project.name}[/project]")
            if project.project_id:
                print_info(f"Project: {project.project_id}")
            if project.account:
                print_info(f"Account: {project.account}")

    except ADCNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1) from e
    except ADCError as e:
        print_error(f"Failed to switch context: {e}")
        raise typer.Exit(1) from e


@app.command("current", help="Show the current ADC context")
def show_current(
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Only print context name")] = False,
) -> None:
    """Show the current ADC context."""
    config = GloomConfig()
    adc_mgr = ADCManager(config)

    current_name, adc_info = adc_mgr.get_current_context()

    if quiet:
        if current_name:
            console.print(current_name)
        raise typer.Exit(0 if current_name else 1)

    if current_name is None and adc_info is None:
        print_warning("No ADC configured. Run 'gcloud auth application-default login' first.")
        raise typer.Exit(1)

    if current_name is None:
        print_warning("ADC exists but is not managed by Gloom.")
        if adc_info:
            print_info(f"Type: {adc_info.credential_type}")
            if adc_info.account:
                print_info(f"Account: {adc_info.account}")
        raise typer.Exit(0)

    console.print(f"[active]●[/active] Current context: [project]{current_name}[/project]")
    if adc_info:
        if adc_info.project_id:
            print_info(f"Project: {adc_info.project_id}")
        if adc_info.account:
            print_info(f"Account: {adc_info.account}")


# =============================================================================
# Cache Commands
# =============================================================================


@cache_app.command("add", help="Cache the current ADC as a named context")
def cache_add(
    name: Annotated[str, typer.Argument(help="Name for this cached context")],
    source: Annotated[
        Optional[Path],
        typer.Option("--source", "-s", help="Path to ADC file (default: current ADC)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing cached context"),
    ] = False,
) -> None:
    """Cache an ADC file as a named context."""
    config = GloomConfig()
    adc_mgr = ADCManager(config)

    try:
        project = adc_mgr.cache_adc(name, source_path=source, force=force)
        print_success(f"Cached context: [project]{project.name}[/project]")

        if project.project_id:
            print_info(f"Project: {project.project_id}")
        if project.account:
            print_info(f"Account: {project.account}")

    except FileExistsError:
        print_error(f"Context '{name}' already exists. Use --force to overwrite.")
        raise typer.Exit(1)
    except ADCError as e:
        print_error(f"Failed to cache ADC: {e}")
        raise typer.Exit(1) from e


@cache_app.command("remove", help="Remove a cached context")
def cache_remove(
    name: Annotated[str, typer.Argument(help="Name of the cached context to remove")],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation"),
    ] = False,
) -> None:
    """Remove a cached ADC context."""
    config = GloomConfig()
    adc_mgr = ADCManager(config)

    # Check if exists
    projects = adc_mgr.list_cached_projects()
    if not any(p.name == name for p in projects):
        print_error(f"Context '{name}' not found.")
        raise typer.Exit(1)

    # Confirm
    if not force:
        confirm = typer.confirm(f"Remove cached context '{name}'?")
        if not confirm:
            print_info("Cancelled.")
            raise typer.Exit(0)

    if adc_mgr.remove_cached_project(name):
        print_success(f"Removed context: [project]{name}[/project]")
    else:
        print_error(f"Failed to remove context '{name}'")
        raise typer.Exit(1)


@cache_app.command("list", help="List cached contexts (alias for 'gloom list')")
def cache_list(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed information"),
    ] = False,
) -> None:
    """List cached contexts."""
    list_contexts(verbose=verbose)


# =============================================================================
# Config Commands (gcloud configurations)
# =============================================================================


@config_app.command("list", help="List gcloud configurations")
def config_list() -> None:
    """List gcloud named configurations."""
    config = GloomConfig()
    gcloud = GcloudConfig(config)

    configurations = gcloud.list_configurations()

    if not configurations:
        print_warning("No gcloud configurations found.")
        raise typer.Exit(0)

    table = Table(title="gcloud Configurations", show_header=True, header_style="bold")
    table.add_column("", width=2)
    table.add_column("Name", style="project")
    table.add_column("Project")
    table.add_column("Account", style="account")
    table.add_column("Region")

    for cfg in configurations:
        indicator = "[active]●[/active]" if cfg.is_active else " "
        table.add_row(
            indicator,
            cfg.name,
            cfg.project or "-",
            cfg.account or "-",
            cfg.region or "-",
        )

    console.print(table)


@config_app.command("activate", help="Activate a gcloud configuration")
def config_activate(
    name: Annotated[str, typer.Argument(help="Configuration name to activate")],
) -> None:
    """Activate a gcloud configuration."""
    config = GloomConfig()
    gcloud = GcloudConfig(config)

    try:
        cfg = gcloud.activate_configuration(name)
        print_success(f"Activated configuration: [project]{cfg.name}[/project]")

        if cfg.project:
            print_info(f"Project: {cfg.project}")
        if cfg.account:
            print_info(f"Account: {cfg.account}")

    except Exception as e:
        print_error(f"Failed to activate configuration: {e}")
        raise typer.Exit(1) from e


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    app()
