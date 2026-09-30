"""
Main entrypoint for Quilchoom's command-line interface.
Orchestrates the CLI for the application using Typer.
"""

import typer

from quilchoom.application.errors import ProjectInitializationError
from quilchoom.application.initialize_project import initialize_project
from quilchoom.ui import terminal

app = typer.Typer(rich_markup_mode="rich")


@app.callback()
def main() -> None:
    """Quilchoom development documentation and evidence system."""


@app.command()
def init() -> None:
    """Initialize Quilchoom in the current Git repository."""
    terminal.header("INITIALIZING LOCAL WORKSPACE")

    try:
        project = initialize_project()

    except ProjectInitializationError:
        terminal.error("Current directory is not inside a Git repository.")
        raise typer.Exit(code=1)

    terminal.statement("SCANNING", "Mapping local repository...")
    terminal.success(f"Root repository confirmed at: {project.repository_path}")

    terminal.statement("SCRIBING", "Preparing documentation workspace...")
    terminal.success("Tracking workspace: .quilchoom/")

    terminal.success("Initialization complete. Local workspace is ready", indent=0)
