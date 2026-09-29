"""
Main entrypoint for Quilchoom's command-line interface.
Orchestrates the CLI for the application using Typer.
"""

import typer

app = typer.Typer(rich_markup_mode="rich")


@app.callback(invoke_without_command=True)
def greet(name: str = "Developer"):
    typer.echo(f"Hello, {name}!")
