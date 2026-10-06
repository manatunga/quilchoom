"""
Integration tests for Quilchoom's command-line interface.
"""

import subprocess
from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from quilchoom import cli as cli_module
from quilchoom.application.errors import ProjectRuntimeError
from quilchoom.application.get_project_status import (
    DocumentState,
    DocumentStatus,
    ProjectStatus,
)
from quilchoom.cli import app
from quilchoom.domain.interpretation import ClaimCandidate, InterpretationResult
from quilchoom.domain.knowledge_claim import ClaimBasis, ClaimConfidence
from quilchoom.infrastructure.ai.errors import AIConnectionError
from quilchoom.interfaces.document_generator import DocumentGenerationResult

runner = CliRunner()


class FakeKnowledgeInterpreter:
    """Returns deterministic knowledge claims for CLI distillation tests."""

    def interpret(self, context):
        return InterpretationResult(
            candidates=[
                ClaimCandidate(
                    statement="The project contains captured development activity.",
                    basis=ClaimBasis.OBSERVATION,
                    confidence=ClaimConfidence.HIGH,
                    evidence_ids=[entry.evidence.id for entry in context.entries],
                )
            ]
        )


class EmptyKnowledgeInterpreter:
    """Returns no knowledge claims for CLI distillation tests."""

    def interpret(self, context):
        return InterpretationResult()


class FailingKnowledgeInterpreter:
    """Raises an AI failure for CLI distillation tests."""

    def interpret(self, context):
        raise AIConnectionError("Unable to reach the AI provider.")


class FakeDocumentGenerator:
    """Returns deterministic generated documentation for CLI tests."""

    def generate(self, context):
        return DocumentGenerationResult(
            content="# Test Project\n\nGenerated documentation.",
            claim_ids=[claim.id for claim in context.claims],
        )


class SecondDocumentGenerator:
    """Returns deterministic second-version documentation for CLI tests."""

    def generate(self, context):
        return DocumentGenerationResult(
            content="# Version 2\n",
            claim_ids=[claim.id for claim in context.claims],
        )


def _create_git_repository(repo_root) -> None:
    repo_root.mkdir()

    subprocess.run(
        ["git", "init"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )


def _commit_file(repo_root, content: str, message: str) -> None:
    tracked_file = repo_root / "example.txt"
    tracked_file.write_text(content)

    subprocess.run(
        ["git", "add", "example.txt"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )


def test_init_success(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    result = runner.invoke(app, ["init"])

    assert "QUILCHOOM / INIT" in result.stdout
    assert "✓ Quilchoom initialized." in result.stdout
    assert "• Project: test-project" in result.stdout
    assert "• Workspace: .quilchoom/" in result.stdout
    assert result.exit_code == 0

    assert (repo_root / ".quilchoom").is_dir()


def test_init_outside_git_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init"])

    assert "QUILCHOOM / INIT" in result.stdout
    assert "× Not inside a Git repository." in result.stdout
    assert "Quilchoom must be initialized inside a Git repository." in result.stdout
    assert (
        "→ Run this command from within the repository you want to track."
        in result.stdout
    )
    assert result.exit_code == 1


def test_capture_captures_repository_commits(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _commit_file(repo_root, "first\n", "First commit")
    _commit_file(repo_root, "second\n", "Second commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["capture"])

    assert "QUILCHOOM / CAPTURE" in result.stdout
    assert "✓ Captured 2 development commits." in result.stdout
    assert "• Project: test-project" in result.stdout
    assert (
        "→ Run 'quilchoom distill' to turn new evidence into project knowledge."
        in result.stdout
    )
    assert result.exit_code == 0


def test_capture_is_current_after_commits_are_captured(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _commit_file(repo_root, "content\n", "Initial commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    result = runner.invoke(app, ["capture"])

    assert "QUILCHOOM / CAPTURE" in result.stdout
    assert "• Development activity is already current." in result.stdout
    assert "• Project: test-project" in result.stdout
    assert "→ Run 'quilchoom distill' to process pending evidence." in result.stdout
    assert result.exit_code == 0


def test_capture_empty_repository_has_no_next_action(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["capture"])

    assert result.exit_code == 0
    assert "QUILCHOOM / CAPTURE" in result.stdout
    assert "• Development activity is already current." in result.stdout
    assert "• Project: test-project" in result.stdout
    assert "quilchoom distill" not in result.stdout


def test_capture_uninitialized_repository(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    result = runner.invoke(app, ["capture"])

    assert "QUILCHOOM / CAPTURE" in result.stdout
    assert "× Unable to capture development activity." in result.stdout
    assert "Quilchoom is not initialized in this repository." in result.stdout
    assert (
        "→ Run 'quilchoom init' if this repository has not been initialized."
        in result.stdout
    )
    assert result.exit_code == 1

    assert not (repo_root / ".quilchoom").exists()


def test_log_shows_recent_activity_newest_first(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _commit_file(repo_root, "first\n", "First commit")
    _commit_file(repo_root, "second\n", "Second commit")
    _commit_file(repo_root, "third\n", "Third commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    result = runner.invoke(app, ["log"])

    assert "QUILCHOOM / LOG" in result.stdout
    assert "• Project: test-project" in result.stdout
    assert "First commit" in result.stdout
    assert "Second commit" in result.stdout
    assert "Third commit" in result.stdout

    assert result.stdout.index("Third commit") < result.stdout.index("Second commit")
    assert result.stdout.index("Second commit") < result.stdout.index("First commit")

    assert (
        "→ Run 'quilchoom distill' to convert captured evidence into project knowledge."
        in result.stdout
    )
    assert result.exit_code == 0


def test_log_respects_limit(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _commit_file(repo_root, "first\n", "First commit")
    _commit_file(repo_root, "second\n", "Second commit")
    _commit_file(repo_root, "third\n", "Third commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    result = runner.invoke(app, ["log", "-n", "2"])

    assert "Third commit" in result.stdout
    assert "Second commit" in result.stdout
    assert "First commit" not in result.stdout
    assert result.exit_code == 0


def test_log_empty_history(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["log"])

    assert "QUILCHOOM / LOG" in result.stdout
    assert "• Project: test-project" in result.stdout
    assert "• No development activity has been captured yet." in result.stdout
    assert (
        "→ Run 'quilchoom capture' to capture Git development activity."
        in result.stdout
    )
    assert result.exit_code == 0


def test_log_rejects_non_positive_limit(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["log", "-n", "0"])

    assert result.exit_code != 0


def test_init_rejects_invalid_existing_configuration(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    _create_git_repository(repo_root)

    workspace = repo_root / ".quilchoom"
    workspace.mkdir()
    (workspace / "config.toml").write_text("[ai\ninvalid")

    monkeypatch.chdir(repo_root)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1
    assert "Unable to load Quilchoom configuration." in result.output
    assert "invalid TOML" in result.output
    assert "Quilchoom initialized." not in result.output


def test_distill_uninitialized_repository(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    result = runner.invoke(app, ["distill"])

    assert "QUILCHOOM / DISTILL" in result.stdout
    assert "× Unable to distill project knowledge." in result.stdout
    assert "Quilchoom is not initialized in this repository." in result.stdout
    assert result.exit_code == 1


def test_distill_is_current_without_pending_evidence(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["distill"])

    assert "QUILCHOOM / DISTILL" in result.stdout
    assert "• Project knowledge is already current." in result.stdout
    assert "• Project: test-project" in result.stdout
    assert (
        "→ Run 'quilchoom capture' after making development changes." in result.stdout
    )
    assert result.exit_code == 0


def test_distill_requires_ai_credential_for_pending_evidence(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _commit_file(repo_root, "content\n", "Initial commit")

    monkeypatch.chdir(repo_root)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    result = runner.invoke(app, ["distill"])

    assert "QUILCHOOM / DISTILL" in result.stdout
    assert "× Unable to configure AI." in result.stdout
    assert "OPENAI_API_KEY" in result.stdout
    assert result.exit_code == 1


def test_distill_creates_project_knowledge(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _commit_file(repo_root, "first\n", "First commit")
    _commit_file(repo_root, "second\n", "Second commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "create_knowledge_interpreter",
        lambda config: FakeKnowledgeInterpreter(),
    )

    result = runner.invoke(app, ["distill"])

    assert "QUILCHOOM / DISTILL" in result.stdout
    assert "✓ Distilled 2 evidence items into 1 knowledge claim." in result.stdout
    assert "• Project: test-project" in result.stdout
    assert (
        "→ Run 'quilchoom scribe generate readme' to generate documentation."
        in result.stdout
    )
    assert result.exit_code == 0

    second_result = runner.invoke(app, ["distill"])

    assert "• Project knowledge is already current." in second_result.stdout
    assert (
        "→ Run 'quilchoom scribe generate readme' to generate documentation."
        in second_result.stdout
    )
    assert second_result.exit_code == 0


def test_distill_marks_evidence_interpreted_when_no_claims_are_produced(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _commit_file(repo_root, "content\n", "Initial commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "create_knowledge_interpreter",
        lambda config: EmptyKnowledgeInterpreter(),
    )

    result = runner.invoke(app, ["distill"])

    assert "✓ Distilled 1 evidence item into 0 knowledge claims." in result.stdout
    assert (
        "→ Run 'quilchoom capture' after making development changes." in result.stdout
    )
    assert result.exit_code == 0

    second_result = runner.invoke(app, ["distill"])

    assert "• Project knowledge is already current." in second_result.stdout
    assert second_result.exit_code == 0


def test_distill_ai_failure_leaves_evidence_pending(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _commit_file(repo_root, "content\n", "Initial commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "create_knowledge_interpreter",
        lambda config: FailingKnowledgeInterpreter(),
    )

    failed_result = runner.invoke(app, ["distill"])

    assert failed_result.exit_code == 1
    assert "× AI provider is temporarily unavailable." in failed_result.stdout
    assert "Unable to reach the AI provider." in failed_result.stdout
    assert "→ Try again later." in failed_result.stdout

    monkeypatch.setattr(
        cli_module,
        "create_knowledge_interpreter",
        lambda config: FakeKnowledgeInterpreter(),
    )

    retry_result = runner.invoke(app, ["distill"])

    assert retry_result.exit_code == 0
    assert "✓ Distilled 1 evidence item into 1 knowledge claim." in retry_result.stdout


def test_distill_does_not_recommend_generation_when_readme_is_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Current knowledge and a current README require no further action."""

    repo_root = tmp_path / "repo"
    _create_git_repository(repo_root)
    monkeypatch.chdir(repo_root)

    init_result = runner.invoke(app, ["init"])
    assert init_result.exit_code == 0

    _prepare_generated_readme(repo_root, monkeypatch)

    result = runner.invoke(app, ["distill"])

    assert result.exit_code == 0
    assert "Project knowledge is already current." in result.stdout
    assert "scribe generate readme" not in result.stdout


def test_scribe_generate_uninitialized_repository(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    result = runner.invoke(app, ["scribe", "generate", "readme"])

    assert "QUILCHOOM / SCRIBE GENERATE" in result.stdout
    assert "× Unable to generate documentation." in result.stdout
    assert "Quilchoom is not initialized in this repository." in result.stdout
    assert result.exit_code == 1


def test_scribe_generate_requires_project_knowledge_before_ai(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["scribe", "generate", "readme"])

    assert result.exit_code == 1
    assert "No project knowledge is available for documentation." in result.stdout
    assert (
        "Quilchoom needs active knowledge claims before it can generate a README."
        in result.stdout
    )
    assert "→ Run 'quilchoom distill' first." in result.stdout
    assert "Unable to configure AI." not in result.stdout


def test_scribe_generate_creates_readme(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _commit_file(repo_root, "content\n", "Initial commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "create_knowledge_interpreter",
        lambda config: FakeKnowledgeInterpreter(),
    )

    assert runner.invoke(app, ["distill"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "create_document_generator",
        lambda config: FakeDocumentGenerator(),
    )

    result = runner.invoke(app, ["scribe", "generate", "readme"])

    assert result.exit_code == 0
    assert "QUILCHOOM / SCRIBE GENERATE" in result.stdout
    assert "✓ Generated README version 1." in result.stdout
    assert "• Project: test-project" in result.stdout
    assert "• Claims used: 1" in result.stdout
    assert "→ Run 'quilchoom scribe show readme' to view it." in result.stdout

    second_result = runner.invoke(
        app,
        ["scribe", "generate", "readme"],
    )

    assert second_result.exit_code == 0
    assert "✓ Generated README version 2." in second_result.stdout


def test_scribe_generate_rejects_unsupported_document_target(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        app,
        ["scribe", "generate", "architecture"],
    )

    assert result.exit_code != 0


def _prepare_generated_readme(repo_root, monkeypatch) -> None:
    _commit_file(repo_root, "content\n", "Initial commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "create_knowledge_interpreter",
        lambda config: FakeKnowledgeInterpreter(),
    )
    assert runner.invoke(app, ["distill"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "create_document_generator",
        lambda config: FakeDocumentGenerator(),
    )
    assert (
        runner.invoke(
            app,
            ["scribe", "generate", "readme"],
        ).exit_code
        == 0
    )


def test_scribe_show_outputs_latest_readme_as_raw_markdown(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    result = runner.invoke(app, ["scribe", "show", "readme"])

    assert result.exit_code == 0
    assert result.stdout == "# Test Project\n\nGenerated documentation.\n"


def test_scribe_show_outputs_requested_historical_version(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    monkeypatch.setattr(
        cli_module,
        "create_document_generator",
        lambda config: SecondDocumentGenerator(),
    )

    assert (
        runner.invoke(
            app,
            ["scribe", "generate", "readme"],
        ).exit_code
        == 0
    )

    latest_result = runner.invoke(
        app,
        ["scribe", "show", "readme"],
    )
    historical_result = runner.invoke(
        app,
        ["scribe", "show", "readme", "-V", "1"],
    )

    assert latest_result.exit_code == 0
    assert latest_result.stdout == "# Version 2\n"

    assert historical_result.exit_code == 0
    assert historical_result.stdout == ("# Test Project\n\nGenerated documentation.\n")


def test_scribe_show_rejects_missing_document(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["scribe", "show", "readme"])

    assert result.exit_code == 1
    assert "README has not been generated." in result.stdout
    assert "No generated README is available for this project." in result.stdout
    assert "→ Run 'quilchoom scribe generate readme' first." in result.stdout


def test_scribe_show_rejects_missing_version(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    result = runner.invoke(
        app,
        ["scribe", "show", "readme", "--version", "99"],
    )

    assert result.exit_code == 1
    assert "README version 99 does not exist." in result.stdout
    assert "The requested document version is not available." in result.stdout


def test_scribe_show_rejects_non_positive_version(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    result = runner.invoke(
        app,
        ["scribe", "show", "readme", "--version", "0"],
    )

    assert result.exit_code != 0


def test_scribe_export_writes_readme(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    destination = repo_root / "README.md"

    result = runner.invoke(
        app,
        ["scribe", "export", "readme", str(destination)],
    )

    assert result.exit_code == 0
    assert destination.read_text() == ("# Test Project\n\nGenerated documentation.")
    assert "✓ Exported README version 1." in result.stdout
    assert "• Destination:" in result.stdout


def test_scribe_export_writes_requested_historical_version(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    monkeypatch.setattr(
        cli_module,
        "create_document_generator",
        lambda config: SecondDocumentGenerator(),
    )

    assert (
        runner.invoke(
            app,
            ["scribe", "generate", "readme"],
        ).exit_code
        == 0
    )

    destination = repo_root / "README.md"

    result = runner.invoke(
        app,
        [
            "scribe",
            "export",
            "readme",
            str(destination),
            "-V",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert destination.read_text() == ("# Test Project\n\nGenerated documentation.")
    assert "✓ Exported README version 1." in result.stdout


def test_scribe_export_force_overwrites_existing_file(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    destination = repo_root / "README.md"
    destination.write_text("Existing README")

    result = runner.invoke(
        app,
        [
            "scribe",
            "export",
            "readme",
            str(destination),
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert destination.read_text() == ("# Test Project\n\nGenerated documentation.")
    assert "✓ Exported README version 1." in result.stdout


def test_scribe_export_rejects_existing_file_non_interactively(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    destination = repo_root / "README.md"
    destination.write_text("Existing README")

    monkeypatch.setattr(
        cli_module,
        "_is_interactive",
        lambda: False,
    )

    result = runner.invoke(
        app,
        ["scribe", "export", "readme", str(destination)],
    )

    assert result.exit_code == 1
    assert "Destination already exists." in result.stdout
    assert "Re-run with '--force' to overwrite it." in result.stdout
    assert destination.read_text() == "Existing README"


def test_scribe_export_confirms_interactive_overwrite(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    destination = repo_root / "README.md"
    destination.write_text("Existing README")

    monkeypatch.setattr(
        cli_module,
        "_is_interactive",
        lambda: True,
    )

    result = runner.invoke(
        app,
        ["scribe", "export", "readme", str(destination)],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Overwrite it?" in result.stdout
    assert destination.read_text() == ("# Test Project\n\nGenerated documentation.")
    assert "✓ Exported README version 1." in result.stdout


def test_scribe_export_cancels_interactive_overwrite(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    destination = repo_root / "README.md"
    destination.write_text("Existing README")

    monkeypatch.setattr(
        cli_module,
        "_is_interactive",
        lambda: True,
    )

    result = runner.invoke(
        app,
        ["scribe", "export", "readme", str(destination)],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Export cancelled." in result.stdout
    assert destination.read_text() == "Existing README"


def test_scribe_export_handles_filesystem_failure(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)
    _prepare_generated_readme(repo_root, monkeypatch)

    destination = repo_root / "missing" / "README.md"

    result = runner.invoke(
        app,
        ["scribe", "export", "readme", str(destination)],
    )

    assert result.exit_code == 1
    assert "Unable to export README." in result.stdout
    assert (
        "Check the destination path and permissions, then try again." in result.stdout
    )
    assert not destination.exists()


def test_status_uninitialized_repository(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "QUILCHOOM / STATUS" in result.stdout
    assert "× Unable to determine project status." in result.stdout
    assert "Quilchoom is not initialized in this repository." in result.stdout
    assert (
        "→ Run 'quilchoom init' if this repository has not been initialized."
        in result.stdout
    )


def test_status_reports_current_empty_project(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "QUILCHOOM / STATUS" in result.stdout
    assert "• Project: test-project" in result.stdout

    assert "Activity" in result.stdout
    assert "Knowledge" in result.stdout
    assert "Documents" in result.stdout

    assert result.stdout.count("• Up to date.") == 2
    assert "• README: not generated" in result.stdout

    assert "quilchoom capture" not in result.stdout
    assert "quilchoom distill" not in result.stdout
    assert "quilchoom scribe generate readme" not in result.stdout


def test_status_reports_pending_commits_and_prioritizes_capture(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _commit_file(repo_root, "first\n", "First commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    _commit_file(repo_root, "second\n", "Second commit")

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "! 1 commit pending capture." in result.stdout
    assert "! 1 evidence item pending distillation." in result.stdout
    assert (
        "→ Run 'quilchoom capture' to capture pending Git development activity."
        in result.stdout
    )
    assert (
        "Run 'quilchoom distill' to convert pending evidence to project knowledge."
        not in result.stdout
    )


def test_status_reports_pending_evidence_and_recommends_distill(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _commit_file(repo_root, "content\n", "Initial commit")

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["capture"]).exit_code == 0

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Activity" in result.stdout
    assert "! 1 evidence item pending distillation." in result.stdout
    assert (
        "→ Run 'quilchoom distill' to convert pending evidence to project knowledge."
        in result.stdout
    )
    assert "pending capture" not in result.stdout


def test_status_reports_current_readme(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    _prepare_generated_readme(repo_root, monkeypatch)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "• Project: test-project" in result.stdout
    assert result.stdout.count("• Up to date.") == 2
    assert "• README: version 1 · current" in result.stdout
    assert "quilchoom capture" not in result.stdout
    assert "quilchoom distill" not in result.stdout
    assert "quilchoom scribe generate readme" not in result.stdout


def test_status_reports_stale_readme_and_recommends_generation(
    tmp_path,
    monkeypatch,
):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    monkeypatch.setattr(
        cli_module,
        "get_project_status",
        lambda **kwargs: ProjectStatus(
            total_commits=0,
            pending_commits=0,
            pending_evidence=0,
            active_claims=1,
            documents=[
                DocumentStatus(
                    key="readme",
                    kind="readme",
                    version_number=2,
                    state=DocumentState.STALE,
                )
            ],
        ),
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "! README: version 2 · stale" in result.stdout
    assert "→ Run 'quilchoom scribe generate readme'." in result.stdout


def test_complete_core_workflow(tmp_path, monkeypatch):
    repo_root = tmp_path / "test-project"
    _create_git_repository(repo_root)

    monkeypatch.chdir(repo_root)

    assert runner.invoke(app, ["init"]).exit_code == 0

    _commit_file(
        repo_root,
        "initial content\n",
        "Initial implementation",
    )

    status_after_commit = runner.invoke(app, ["status"])

    assert status_after_commit.exit_code == 0
    assert "! 1 commit pending capture." in status_after_commit.stdout
    assert (
        "→ Run 'quilchoom capture' to capture pending Git development activity."
        in status_after_commit.stdout
    )

    capture_result = runner.invoke(app, ["capture"])

    assert capture_result.exit_code == 0

    status_after_capture = runner.invoke(app, ["status"])

    assert status_after_capture.exit_code == 0
    assert "Up to date." in status_after_capture.stdout
    assert "pending capture" not in status_after_capture.stdout
    assert "! 1 evidence item pending distillation." in status_after_capture.stdout
    assert "README: not generated" in status_after_capture.stdout
    assert (
        "Run 'quilchoom distill' to convert pending evidence to project knowledge."
        in status_after_capture.stdout
    )

    monkeypatch.setattr(
        cli_module,
        "create_knowledge_interpreter",
        lambda config: FakeKnowledgeInterpreter(),
    )

    distill_result = runner.invoke(app, ["distill"])

    assert distill_result.exit_code == 0

    status_after_distill = runner.invoke(app, ["status"])

    assert status_after_distill.exit_code == 0
    assert status_after_distill.stdout.count("• Up to date.") == 2
    assert "pending distillation" not in status_after_distill.stdout
    assert "README: not generated" in status_after_distill.stdout
    assert "Run 'quilchoom scribe generate readme'." in status_after_distill.stdout

    monkeypatch.setattr(
        cli_module,
        "create_document_generator",
        lambda config: FakeDocumentGenerator(),
    )

    generate_result = runner.invoke(
        app,
        ["scribe", "generate", "readme"],
    )

    assert generate_result.exit_code == 0

    status_after_scribe_generate = runner.invoke(app, ["status"])

    assert status_after_scribe_generate.exit_code == 0
    assert status_after_scribe_generate.stdout.count("• Up to date.") == 2
    assert "• README: version 1 · current" in status_after_scribe_generate.stdout
    assert "→ Run '" not in status_after_scribe_generate.stdout

    show_result = runner.invoke(
        app,
        ["scribe", "show", "readme"],
    )

    assert show_result.exit_code == 0
    assert show_result.stdout == "# Test Project\n\nGenerated documentation.\n"

    destination = repo_root / "README.md"

    export_result = runner.invoke(
        app,
        ["scribe", "export", "readme", str(destination)],
    )

    assert export_result.exit_code == 0
    assert destination.read_text() == "# Test Project\n\nGenerated documentation."


def test_debug_reraises_handled_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Debug mode exposes handled exceptions instead of rendering friendly errors."""

    repo_root = tmp_path / "repo"
    _create_git_repository(repo_root)
    monkeypatch.chdir(repo_root)

    init_result = runner.invoke(app, ["init"])
    assert init_result.exit_code == 0

    def fail_runtime(_repository_path: Path | None = None) -> None:
        raise ProjectRuntimeError("debug failure")

    monkeypatch.setattr(cli_module, "load_project_runtime", fail_runtime)

    result = runner.invoke(app, ["--debug", "status"])

    assert result.exit_code != 0
    assert isinstance(result.exception, ProjectRuntimeError)
    assert str(result.exception) == "debug failure"


def test_root_command_shows_welcome_screen() -> None:
    """Bare invocation displays Quilchoom's welcome screen."""

    result = runner.invoke(app)

    assert result.exit_code == 0
    assert "QUILCHOOM" in result.stdout
    assert "DEVELOPMENT MEMORY" in result.stdout
    assert "CAPTURE" in result.stdout
    assert "DISTILL" in result.stdout
    assert "SCRIBE" in result.stdout
    assert "THE STORY BEHIND YOUR CODE" in result.stdout


def test_root_help_does_not_show_welcome_screen() -> None:
    """Root help remains a command reference rather than the welcome screen."""

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Turn development activity into traceable project knowledge" in result.stdout
    assert "DEVELOPMENT MEMORY" not in result.stdout
    assert "Commands" in result.stdout


def test_version_option_shows_installed_version() -> None:
    """Version option displays Quilchoom's installed package version."""

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == f"Quilchoom {version('quilchoom')}"
