"""
Main entrypoint for Quilchoom's command-line interface.
Orchestrates the CLI for the application using Typer.
"""

import typer

from quilchoom.application.errors import ProjectInitializationError
from quilchoom.application.initialize_project import initialize_project

app = typer.Typer(rich_markup_mode="rich")


@app.callback()
def main() -> None:
    """Quilchoom development documentation and evidence system."""


@app.command()
def init() -> None:
    """Initialize Quilchoom in the current Git repository."""
    try:
        project = initialize_project()

    except ProjectInitializationError:
        typer.echo("[ERROR] ❌ Current directory is not inside a Git repository.")
        raise typer.Exit(code=1)

    typer.echo(f"[Quilchoom] 🚀 Initialized '{project.name}'")
    typer.echo(f"[Quilchoom] 📁 Repository: {project.repository_path}")
