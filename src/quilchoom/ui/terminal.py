"""
Provides Quilchoom's terminal output and presentation conventions.
"""

import time
from typing import Self

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()


def header(title: str) -> None:
    """Displays Quilchoom's header."""
    console.print()
    console.print(f"[yellow]QUILCHOOM[/yellow] / {title}")
    console.print()


def info(message: str) -> None:
    """Displays neutral informational output."""
    console.print(f"[dim]•[/dim] {message}")


def success(message: str) -> None:
    """Displays a successful result."""
    console.print(f"[green]✓[/green] {message}")


def warning(message: str) -> None:
    """Displays an attention or pending-state message."""
    console.print(f"[yellow]![/yellow] {message}")


def error(message: str) -> None:
    """Displays an error message."""
    console.print(f"[red]×[/red] {message}")


def next_action(message: str) -> None:
    """Displays a suggested next action."""
    console.print(f"[cyan]→[/cyan] {message}")


class Progress:
    """Displays indeterminate terminal progress for a long-running operation."""

    frames = ("◇", "◈", "◆", "◈")
    interval = 0.18

    def __init__(self, message: str) -> None:
        self.message = message
        self.started_at = 0.0
        self.live: Live | None = None

    def __enter__(self) -> Self:
        """Starts indeterminate terminal progress."""
        self.started_at = time.monotonic()

        if console.is_terminal:
            self.live = Live(
                self,
                console=console,
                refresh_per_second=12,
                transient=True,
            )
            self.live.start()

        return self

    def __rich__(self) -> Text:
        """Renders the current progress animation frame."""

        elapsed = time.monotonic() - self.started_at
        frame_index = int(elapsed / self.interval) % len(self.frames)
        frame = self.frames[frame_index]

        text = Text()
        text.append(frame, style="cyan")
        text.append(f" {self.message}")

        return text

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Stops indeterminate terminal progress."""

        if self.live is not None:
            self.live.stop()


def error_block(
    title: str,
    explanation: str,
    action: str | None = None,
) -> None:
    """Displays a structured error with explanation and recovery guidance."""

    error(title)
    console.print()
    console.print(f"  {explanation}")

    if action is not None:
        console.print()
        console.print(f"  [cyan]→[/cyan] {action}")


def newline() -> None:
    """Displays a blank terminal line."""
    console.print()


def field(label: str, value: str) -> None:
    """Displays a labeled command result field."""

    text = Text()
    text.append(f"• {label}: ", style="dim")
    text.append(value, style="cyan")

    console.print(text)


def log_entry(reference: str, date: str, summary: str) -> None:
    """Displays a compact development history entry."""

    text = Text()
    text.append(f"{reference}  ", style="cyan")
    text.append(f"{date}  ", style="dim")
    text.append(summary)

    console.print(text)


def section(title: str) -> None:
    """Displays a terminal output section heading."""

    console.print(title)


def welcome() -> None:
    """Displays Quilchoom's command-line welcome screen."""

    welcome_width = 55
    cell_width = 18

    identity = Text()
    identity.append("// ", style="dim")
    identity.append("DEVELOPMENT MEMORY")

    banner = Panel(
        identity,
        title="QUILCHOOM",
        title_align="left",
        border_style="yellow",
        width=welcome_width,
        padding=(0, 2),
    )

    pipeline = Text()
    pipeline.append("        ")
    pipeline.append("◇", style="cyan")
    pipeline.append("─────────────────", style="dim cyan")
    pipeline.append("◈", style="bold cyan")
    pipeline.append("─────────────────", style="dim cyan")
    pipeline.append("◆", style="cyan")

    labels = "".join(
        label.center(cell_width) for label in ("CAPTURE", "DISTILL", "SCRIBE")
    )

    tagline = Text(
        "THE STORY BEHIND YOUR CODE".center(welcome_width),
        style="bold",
    )

    console.print()
    console.print(banner)
    console.print()

    console.print(pipeline)
    console.print(Text(labels, style="dim"))
    console.print()
    console.print(tagline)
    console.print()

    console.print("Development leaves evidence.")
    console.print("Quilchoom turns it into traceable project knowledge")
    console.print("and useful documentation.")
    console.print()

    next_action("Run 'quilchoom init' to begin.")
    next_action("Run 'quilchoom --help' for all commands.")
    console.print()
