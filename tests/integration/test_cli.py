"""
Integration tests for Quilchoom's command-line interface.
"""

import subprocess

from typer.testing import CliRunner

from quilchoom.cli import app

runner = CliRunner()


def test_init_success(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )

    monkeypatch.chdir(repo_root)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert "[Quilchoom] 🚀 Initialized" in result.stdout
    assert (repo_root / ".quilchoom").is_dir()


def test_init_outside_git_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert (
        "[ERROR] ❌ Current directory is not inside a Git repository." in result.stdout
    )
