"""
Provides Quilchoom's terminal output and presentation conventions.
"""

from rich.console import Console

console = Console()


def header(title: str) -> None:
    console.print(f"QUILCHOOM // {title}")
    console.print()


def statement(label: str, message: str) -> None:
    console.print(f"[{label}] {message}")


def success(message: str, indent: int = 4) -> None:
    console.print(f"{' ' * indent}[green][✓][/green] {message}")


def warning(message: str, indent: int = 4) -> None:
    console.print(f"{' ' * indent}[yellow][!][/yellow] {message}")


def error(message: str, indent: int = 0) -> None:
    console.print(f"{' ' * indent}[red][✗][/red] {message}")
