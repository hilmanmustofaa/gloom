"""Rich console logging utilities for Gloom CLI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

if TYPE_CHECKING:
    pass

# Custom theme for Gloom
GLOOM_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "project": "bold magenta",
        "account": "dim cyan",
        "path": "dim blue",
        "active": "bold green",
        "inactive": "dim",
    }
)

# Global console instance - use stdout for CLI testing compatibility
console = Console(theme=GLOOM_THEME)


def get_logger(name: str = "gloom", *, verbose: bool = False) -> logging.Logger:
    """Get a configured logger with Rich formatting.

    Args:
        name: Logger name.
        verbose: If True, set DEBUG level. Otherwise INFO.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = RichHandler(
            console=console,
            show_time=verbose,
            show_path=verbose,
            rich_tracebacks=True,
            tracebacks_show_locals=verbose,
        )

        level = logging.DEBUG if verbose else logging.INFO
        logger.setLevel(level)
        handler.setLevel(level)

        logger.addHandler(handler)

    return logger


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]✓[/success] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[error]✗[/error] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]⚠[/warning] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[info]ℹ[/info] {message}")
