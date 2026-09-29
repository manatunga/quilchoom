"""
Automated test suite for Quilchoom's CLI.
"""

from typer.testing import CliRunner

from quilchoom.cli import app

runner = CliRunner()

def test_cli():
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert result.output.strip() == "Hello, Developer!"
