"""
Integration tests for Quilchoom's knowledge interpretation pipeline.
"""

import subprocess

from sqlalchemy import create_engine

from quilchoom.application.capture_commit import capture_commit
from quilchoom.application.interpret_history import interpret_history
from quilchoom.application.reconstruct_history import reconstruct_history
from quilchoom.domain.interpretation import (
    ClaimCandidate,
    InterpretationContext,
    InterpretationResult,
)
from quilchoom.domain.knowledge_claim import ClaimBasis, ClaimConfidence, ClaimStatus
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    EventRepository,
    EvidenceRepository,
    InterpretationRunRepository,
    KnowledgeClaimRepository,
    ProjectRepository,
)


class DeterministicInterpreter:
    def interpret(self, context: InterpretationContext) -> InterpretationResult:
        entry = context.entries[0]

        candidate = ClaimCandidate(
            statement="The project contains a captured Git change.",
            basis=ClaimBasis.OBSERVATION,
            confidence=ClaimConfidence.HIGH,
            evidence_ids=[entry.evidence.id],
        )

        return InterpretationResult(candidates=[candidate])


def test_interpret_captured_git_history_end_to_end(tmp_path):
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    (tmp_path / "README.md").write_text("# My project\n")

    subprocess.run(
        ["git", "add", "."],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    sha = result.stdout.strip()

    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(
        name="my_project",
        repository_path=tmp_path,
    )

    project_repo = ProjectRepository(db_engine)
    event_repo = EventRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)
    claim_repo = KnowledgeClaimRepository(db_engine)
    run_repo = InterpretationRunRepository(db_engine)

    project_repo.save(project)

    captured_event, captured_evidence = capture_commit(
        project=project,
        repository_path=tmp_path,
        commit_sha=sha,
        event_repository=event_repo,
        evidence_repository=evidence_repo,
    )

    history = reconstruct_history(
        project=project,
        event_repository=event_repo,
        evidence_repository=evidence_repo,
    )

    assert len(history.entries) == 1
    assert history.entries[0].event.id == captured_event.id
    assert history.entries[0].evidence.id == captured_evidence.id

    interpreter = DeterministicInterpreter()

    interpretation_run = interpret_history(
        project=project,
        history=history,
        interpreter=interpreter,
        claim_repository=claim_repo,
        run_repository=run_repo,
    )

    assert interpretation_run is not None
    assert interpretation_run.evidence_ids == [captured_evidence.id]
    assert len(interpretation_run.claim_ids) == 1

    claims = claim_repo.list_for_project(project.id)

    assert len(claims) == 1

    claim = claims[0]

    assert claim.id == interpretation_run.claim_ids[0]
    assert claim.project_id == project.id
    assert claim.statement == "The project contains a captured Git change."
    assert claim.basis == ClaimBasis.OBSERVATION
    assert claim.confidence == ClaimConfidence.HIGH
    assert claim.status == ClaimStatus.ACTIVE
    assert claim.evidence_ids == [captured_evidence.id]

    second_run = interpret_history(
        project=project,
        history=history,
        interpreter=interpreter,
        claim_repository=claim_repo,
        run_repository=run_repo,
    )

    assert second_run is None
    assert len(claim_repo.list_for_project(project.id)) == 1
