"""
Main entrypoint for Quilchoom's command-line interface.
Orchestrates the CLI for the application using Typer.
"""

import sys
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from quilchoom.application.capture_repository import capture_repository
from quilchoom.application.check_document_staleness import is_document_version_stale
from quilchoom.application.check_knowledge_status import count_pending_evidence
from quilchoom.application.errors import (
    DocumentUnavailableError,
    DocumentVersionUnavailableError,
    HistoryReconstructionError,
    InvalidGeneratedClaimError,
    NoActiveClaimsError,
    ProjectInitializationError,
    ProjectRuntimeError,
)
from quilchoom.application.generate_document import generate_document
from quilchoom.application.get_document_version import get_document_version
from quilchoom.application.get_project_status import DocumentState, get_project_status
from quilchoom.application.initialize_project import initialize_project
from quilchoom.application.interpret_history import interpret_history
from quilchoom.application.reconstruct_history import reconstruct_history
from quilchoom.application.runtime import load_project_runtime
from quilchoom.domain.knowledge_claim import ClaimStatus
from quilchoom.domain.project import Project
from quilchoom.infrastructure.ai.composition import (
    create_document_generator,
    create_knowledge_interpreter,
)
from quilchoom.infrastructure.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIConnectionError,
    AIContextLimitError,
    AIError,
    AIProviderError,
    AIRateLimitError,
    AIResponseError,
)
from quilchoom.infrastructure.config import ConfigurationError, load_config
from quilchoom.infrastructure.database.connection import create_database_engine
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    EventRepository,
    EvidenceRepository,
    InterpretationRunRepository,
    KnowledgeClaimRepository,
)
from quilchoom.infrastructure.filesystem.export import export_document_content
from quilchoom.ui import terminal

app = typer.Typer(
    rich_markup_mode="rich",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)

scribe_app = typer.Typer(
    help="Generate, inspect, and export documentation from project knowledge.",
)
app.add_typer(scribe_app, name="scribe")

_debug = False


class DocumentTarget(str, Enum):
    """Defines document types exposed through Quilchoom's CLI."""

    README = "readme"


def _is_interactive() -> bool:
    """Return whether standard input is attached to an interactive terminal."""
    return sys.stdin.isatty()


def _raise_if_debugging(exc: BaseException) -> None:
    """Re-raise an exception when CLI debug mode is enabled."""

    if _debug:
        raise exc


def _version_callback(value: bool) -> None:
    """Displays Quilchoom's installed version and exits."""

    if value:
        typer.echo(f"Quilchoom {version('quilchoom')}")
        raise typer.Exit()


def _readme_needs_generation(
    project: Project,
    document_repository: DocumentRepository,
    version_repository: DocumentVersionRepository,
    claim_repository: KnowledgeClaimRepository,
) -> bool:
    """Return whether the project's README is missing or stale."""

    document = document_repository.get_by_key(project.id, "readme")

    if document is None:
        return True

    version = version_repository.get_latest(document.id)

    if version is None:
        return True

    return is_document_version_stale(
        version=version,
        claim_repository=claim_repository,
    )


@app.callback()
def main(
    ctx: typer.Context,
    debug: Annotated[
        bool,
        typer.Option(
            "--debug",
            help="Show detailed exception information for debugging.",
        ),
    ] = False,
    version_requested: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the installed Quilchoom version and exit.",
        ),
    ] = False,
) -> None:
    """Turn development activity into traceable project knowledge and documentation."""

    global _debug
    _debug = debug

    if ctx.invoked_subcommand is None:
        terminal.welcome()


@app.command()
def init() -> None:
    """Initialize Quilchoom in the current Git repository."""

    terminal.header("INIT")

    try:
        project = initialize_project()

    except ProjectInitializationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Not inside a Git repository.",
            explanation="Quilchoom must be initialized inside a Git repository.",
            action="Run this command from within the repository you want to track.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except ConfigurationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to load Quilchoom configuration.",
            explanation=str(exc),
            action="Fix .quilchoom/config.toml and run 'quilchoom init' again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    terminal.success("Quilchoom initialized.")
    terminal.field("Project", project.name)
    terminal.field("Workspace", ".quilchoom/")
    terminal.newline()


@app.command()
def capture() -> None:
    """Capture uncaptured development activity from the Git repository."""

    terminal.header("CAPTURE")

    try:
        runtime = load_project_runtime()

    except ProjectRuntimeError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to capture development activity.",
            explanation=str(exc),
            action="Run 'quilchoom init' if this repository has not been initialized.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    db_engine = create_database_engine(runtime.database_path)

    event_repository = EventRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)

    result = capture_repository(
        project=runtime.project,
        repository_path=runtime.repository_root,
        event_repository=event_repository,
        evidence_repository=evidence_repository,
    )

    if result.captured_commits == 0:
        terminal.info("Development activity is already current.")
        terminal.field("Project", runtime.project.name)

        pending_evidence = count_pending_evidence(
            project=runtime.project,
            evidence_repository=evidence_repository,
            run_repository=run_repository,
        )

        if pending_evidence > 0:
            terminal.newline()
            terminal.next_action("Run 'quilchoom distill' to process pending evidence.")

    else:
        terminal.success(
            f"Captured {result.captured_commits} development "
            f"{'commit' if result.captured_commits == 1 else 'commits'}."
        )
        terminal.field("Project", runtime.project.name)
        terminal.newline()
        terminal.next_action(
            "Run 'quilchoom distill' to turn new evidence into project knowledge."
        )

    terminal.newline()


@app.command()
def log(
    limit: Annotated[
        int,
        typer.Option(
            "-n", "--limit", min=1, help="Maximum number of history entries to show."
        ),
    ] = 20,
) -> None:
    """Show recent reconstructed development activity."""

    terminal.header("LOG")

    try:
        runtime = load_project_runtime()

    except ProjectRuntimeError as exc:
        terminal.error_block(
            title="Unable to show development history.",
            explanation=str(exc),
            action="Run 'quilchoom init' if this repository has not been initialized.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    db_engine = create_database_engine(runtime.database_path)

    event_repository = EventRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)

    try:
        history = reconstruct_history(
            project=runtime.project,
            event_repository=event_repository,
            evidence_repository=evidence_repository,
        )

    except HistoryReconstructionError as exc:
        terminal.error_block(
            title="Unable to reconstruct development history.",
            explanation=str(exc),
        )
        terminal.newline()
        raise typer.Exit(code=1)

    terminal.field("Project", runtime.project.name)

    if not history.entries:
        terminal.info("No development activity has been captured yet.")
        terminal.newline()
        terminal.next_action(
            "Run 'quilchoom capture' to capture Git development activity."
        )
        terminal.newline()
        return

    terminal.newline()
    entries = history.entries[-limit:][::-1]

    for entry in entries:
        reference = entry.event.source_reference[:7]
        date = entry.event.timestamp.strftime("%Y-%m-%d")
        summary = entry.event.summary.splitlines()[0]

        terminal.log_entry(reference, date, summary)

    terminal.newline()
    terminal.next_action(
        "Run 'quilchoom distill' to convert captured evidence into project knowledge."
    )
    terminal.newline()


@app.command()
def distill() -> None:
    """Distill captured development evidence into project knowledge."""

    terminal.header("DISTILL")

    try:
        runtime = load_project_runtime()

    except ProjectRuntimeError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to distill project knowledge.",
            explanation=str(exc),
            action="Run 'quilchoom init' if this repository has not been initialized.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    db_engine = create_database_engine(runtime.database_path)

    event_repository = EventRepository(db_engine)
    evidence_repository = EvidenceRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)
    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    pending_evidence = count_pending_evidence(
        project=runtime.project,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
    )

    if pending_evidence == 0:
        active_claims = [
            claim
            for claim in claim_repository.list_for_project(runtime.project.id)
            if claim.status == ClaimStatus.ACTIVE
        ]

        terminal.info("Project knowledge is already current.")
        terminal.field("Project", runtime.project.name)

        if active_claims and _readme_needs_generation(
            project=runtime.project,
            document_repository=document_repository,
            version_repository=version_repository,
            claim_repository=claim_repository,
        ):
            terminal.next_action(
                "Run 'quilchoom scribe generate readme' to generate documentation."
            )

        elif not active_claims:
            terminal.next_action(
                "Run 'quilchoom capture' after making development changes."
            )

        terminal.newline()
        return

    try:
        history = reconstruct_history(
            project=runtime.project,
            event_repository=event_repository,
            evidence_repository=evidence_repository,
        )

    except HistoryReconstructionError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to reconstruct development history.",
            explanation=str(exc),
        )
        terminal.newline()
        raise typer.Exit(code=1)

    try:
        config_path = runtime.workspace / "config.toml"
        config = load_config(config_path)

    except ConfigurationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to load Quilchoom configuration.",
            explanation=str(exc),
            action="Check .quilchoom/config.toml and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    try:
        interpreter = create_knowledge_interpreter(config.ai)

    except AIConfigurationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to configure AI.",
            explanation=str(exc),
            action="Check your AI configuration and credentials, then try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    try:
        with terminal.Progress("Distilling project knowledge..."):
            run = interpret_history(
                project=runtime.project,
                history=history,
                interpreter=interpreter,
                claim_repository=claim_repository,
                run_repository=run_repository,
            )

    except AIAuthenticationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI authentication failed.",
            explanation=str(exc),
            action="Check your AI provider credentials and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except (AIConnectionError, AIRateLimitError) as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI provider is temporarily unavailable.",
            explanation=str(exc),
            action="Try again later.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIContextLimitError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Development history is too large to process.",
            explanation=str(exc),
            action="Use a model with a larger context window and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIResponseError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI provider returned an unusable response.",
            explanation=str(exc),
            action="Try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIProviderError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI provider failed.",
            explanation=str(exc),
            action="Check your AI provider and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to distill project knowledge.",
            explanation=str(exc),
            action="Check your AI provider and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    if run is None:
        active_claims = [
            claim
            for claim in claim_repository.list_for_project(runtime.project.id)
            if claim.status == ClaimStatus.ACTIVE
        ]

        terminal.info("Project knowledge is already current.")
        terminal.field("Project", runtime.project.name)

        if active_claims and _readme_needs_generation(
            project=runtime.project,
            document_repository=document_repository,
            version_repository=version_repository,
            claim_repository=claim_repository,
        ):
            terminal.next_action(
                "Run 'quilchoom scribe generate readme' to generate documentation."
            )

        elif not active_claims:
            terminal.next_action(
                "Run 'quilchoom capture' after making development changes."
            )

        terminal.newline()
        return

    evidence_count = len(run.evidence_ids)
    claim_count = len(run.claim_ids)

    evidence_label = "item" if evidence_count == 1 else "items"
    claim_label = "claim" if claim_count == 1 else "claims"

    terminal.success(
        f"Distilled {evidence_count} evidence {evidence_label} "
        f"into {claim_count} knowledge {claim_label}."
    )
    terminal.field("Project", runtime.project.name)
    terminal.newline()

    active_claims = [
        claim
        for claim in claim_repository.list_for_project(runtime.project.id)
        if claim.status == ClaimStatus.ACTIVE
    ]

    if active_claims:
        terminal.next_action(
            "Run 'quilchoom scribe generate readme' to generate documentation."
        )
    else:
        terminal.next_action(
            "Run 'quilchoom capture' after making development changes."
        )

    terminal.newline()


@scribe_app.command("generate")
def scribe_generate(document: DocumentTarget) -> None:
    """Generate a documentation artifact from project knowledge."""

    key = document.value
    kind = document.value

    terminal.header("SCRIBE GENERATE")

    try:
        runtime = load_project_runtime()

    except ProjectRuntimeError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to generate documentation.",
            explanation=str(exc),
            action="Run 'quilchoom init' if this repository has not been initialized.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    db_engine = create_database_engine(runtime.database_path)

    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)

    active_claims = [
        claim
        for claim in claim_repository.list_for_project(runtime.project.id)
        if claim.status == ClaimStatus.ACTIVE
    ]

    if not active_claims:
        terminal.error_block(
            title="No project knowledge is available for documentation.",
            explanation=f"Quilchoom needs active knowledge claims before it can generate a {document.name}.",
            action="Run 'quilchoom distill' first.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    try:
        config_path = runtime.workspace / "config.toml"
        config = load_config(config_path)

    except ConfigurationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to load Quilchoom configuration.",
            explanation=str(exc),
            action="Check .quilchoom/config.toml and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    try:
        generator = create_document_generator(config.ai)

    except AIConfigurationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to configure AI.",
            explanation=str(exc),
            action="Check your AI configuration and credentials, then try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    try:
        with terminal.Progress(f"Generating {document.name}..."):
            version = generate_document(
                project=runtime.project,
                key=key,
                kind=kind,
                generator=generator,
                document_repository=document_repository,
                version_repository=version_repository,
                claim_repository=claim_repository,
            )

    except NoActiveClaimsError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="No project knowledge is available for documentation.",
            explanation=f"Quilchoom needs active knowledge claims before it can generate a {document.name}.",
            action="Run 'quilchoom distill' first.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIAuthenticationError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI authentication failed.",
            explanation=str(exc),
            action="Check your AI provider credentials and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except (AIConnectionError, AIRateLimitError) as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI provider is temporarily unavailable.",
            explanation=str(exc),
            action="Try again later.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIContextLimitError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Project knowledge is too large to process.",
            explanation=str(exc),
            action="Use a model with a larger context window and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except (AIResponseError, InvalidGeneratedClaimError) as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI provider returned an unusable response.",
            explanation=str(exc),
            action="Try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIProviderError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="AI provider failed.",
            explanation=str(exc),
            action="Check your AI provider and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except AIError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title=f"Unable to generate {document.name}.",
            explanation=str(exc),
            action="Check your AI provider and try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    claim_count = len(version.claim_ids)

    terminal.success(f"Generated {document.name} version {version.version_number}.")
    terminal.field("Project", runtime.project.name)
    terminal.field("Claims used", str(claim_count))
    terminal.newline()
    terminal.next_action("Run 'quilchoom scribe show readme' to view it.")
    terminal.newline()


@scribe_app.command("show")
def scribe_show(
    document: DocumentTarget,
    version: Annotated[
        int | None,
        typer.Option(
            "-V", "--version", min=1, help="Show a specific document version."
        ),
    ] = None,
) -> None:
    """Show a stored documentation artifact."""

    try:
        runtime = load_project_runtime()

    except ProjectRuntimeError as exc:
        _raise_if_debugging(exc)

        terminal.newline()
        terminal.error_block(
            title="Unable to retrieve documentation.",
            explanation=str(exc),
            action="Run 'quilchoom init' if this repository has not been initialized.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    db_engine = create_database_engine(runtime.database_path)

    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    try:
        stored_version = get_document_version(
            project=runtime.project,
            key=document.value,
            version_number=version,
            document_repository=document_repository,
            version_repository=version_repository,
        )

    except DocumentUnavailableError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title=f"{document.name} has not been generated.",
            explanation=f"No generated {document.name} is available for this project.",
            action=f"Run 'quilchoom scribe generate {document.value}' first.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except DocumentVersionUnavailableError as exc:
        _raise_if_debugging(exc)

        if version is not None:
            title = f"{document.name} version {version} does not exist."
        else:
            title = f"No {document.name} version is available."

        terminal.error_block(
            title=title,
            explanation="The requested document version is not available.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    typer.echo(stored_version.content, nl=False)

    if not stored_version.content.endswith("\n"):
        typer.echo()


@scribe_app.command("export")
def scribe_export(
    document: DocumentTarget,
    destination: Annotated[
        Path,
        typer.Argument(
            help="Path to write the exported document.",
        ),
    ],
    version: Annotated[
        int | None,
        typer.Option(
            "-V", "--version", min=1, help="Show a specific document version."
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "-f", "--force", help="Overwrite the destination without prompting."
        ),
    ] = False,
) -> None:
    """Export a stored documentation artifact to the filesystem."""

    terminal.header("SCRIBE EXPORT")

    try:
        runtime = load_project_runtime()

    except ProjectRuntimeError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to export documentation.",
            explanation=str(exc),
            action="Run 'quilchoom init' if this repository has not been initialized.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    db_engine = create_database_engine(runtime.database_path)

    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    try:
        stored_version = get_document_version(
            project=runtime.project,
            key=document.value,
            version_number=version,
            document_repository=document_repository,
            version_repository=version_repository,
        )

    except DocumentUnavailableError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title=f"{document.name} has not been generated.",
            explanation=f"No generated {document.name} is available for this project.",
            action=f"Run 'quilchoom scribe generate {document.value}' first.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    except DocumentVersionUnavailableError as exc:
        _raise_if_debugging(exc)

        if version is not None:
            title = f"{document.name} version {version} does not exist."
        else:
            title = f"No {document.name} version is available."

        terminal.error_block(
            title=title,
            explanation="The requested document version is not available.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    if destination.exists() and not force:
        if not _is_interactive():
            terminal.error_block(
                title="Destination already exists.",
                explanation=f"{destination} already exists and cannot be overwritten non-interactively.",
                action="Re-run with '--force' to overwrite it.",
            )
            terminal.newline()
            raise typer.Exit(code=1)

        confirmed = typer.confirm(
            f"{destination} already exists. Overwrite it?",
            default=False,
        )

        if not confirmed:
            terminal.info("Export cancelled.")
            terminal.newline()
            raise typer.Exit(code=0)

    try:
        export_document_content(
            destination=destination,
            content=stored_version.content,
        )

    except OSError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title=f"Unable to export {document.name}.",
            explanation=str(exc),
            action="Check the destination path and permissions, then try again.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    terminal.success(
        f"Exported {document.name} version {stored_version.version_number}."
    )
    terminal.field("Destination", str(destination))
    terminal.newline()


@app.command()
def status() -> None:
    """Show the current local workflow status."""

    terminal.header("STATUS")

    try:
        runtime = load_project_runtime()

    except ProjectRuntimeError as exc:
        _raise_if_debugging(exc)

        terminal.error_block(
            title="Unable to determine project status.",
            explanation=str(exc),
            action="Run 'quilchoom init' if this repository has not been initialized.",
        )
        terminal.newline()
        raise typer.Exit(code=1)

    db_engine = create_database_engine(runtime.database_path)

    evidence_repository = EvidenceRepository(db_engine)
    run_repository = InterpretationRunRepository(db_engine)
    claim_repository = KnowledgeClaimRepository(db_engine)
    document_repository = DocumentRepository(db_engine)
    version_repository = DocumentVersionRepository(db_engine)

    project_status = get_project_status(
        project=runtime.project,
        repository_root=runtime.repository_root,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
        claim_repository=claim_repository,
        document_repository=document_repository,
        version_repository=version_repository,
    )

    terminal.field("Project", runtime.project.name)
    terminal.newline()

    terminal.section("Activity")

    if project_status.pending_commits > 0:
        count = project_status.pending_commits
        noun = "commit" if count == 1 else "commits"
        terminal.warning(f"{count} {noun} pending capture.")

    else:
        terminal.info("Up to date.")

    terminal.newline()

    terminal.section("Knowledge")

    if project_status.pending_evidence > 0:
        count = project_status.pending_evidence
        noun = "evidence item" if count == 1 else "evidence items"
        terminal.warning(f"{count} {noun} pending distillation.")

    else:
        terminal.info("Up to date.")

    terminal.newline()

    readme_status = next(
        (document for document in project_status.documents if document.key == "readme"),
        None,
    )

    terminal.section("Documents")

    if readme_status is None:
        terminal.info("README: not generated")

    elif readme_status.state == DocumentState.STALE:
        terminal.warning(f"README: version {readme_status.version_number} · stale")

    else:
        terminal.info(f"README: version {readme_status.version_number} · current")

    terminal.newline()

    next_step: str | None = None

    if project_status.pending_commits > 0:
        next_step = (
            "Run 'quilchoom capture' to capture pending Git development activity."
        )

    elif project_status.pending_evidence > 0:
        next_step = (
            "Run 'quilchoom distill' to convert pending evidence to project knowledge."
        )

    elif project_status.active_claims > 0 and (
        readme_status is None or readme_status.state == DocumentState.STALE
    ):
        next_step = "Run 'quilchoom scribe generate readme'."

    if next_step is not None:
        terminal.next_action(next_step)
        terminal.newline()
