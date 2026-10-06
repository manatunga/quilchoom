"""
Integration tests for knowledge interpretation application workflow.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from quilchoom.application.errors import (
    InterpretationProjectMismatchError,
    InvalidCandidateEvidenceError,
)
from quilchoom.application.interpret_history import interpret_history
from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.history import DevelopmentHistory, HistoryEntry
from quilchoom.domain.interpretation import (
    ClaimCandidate,
    InterpretationContext,
    InterpretationResult,
    InterpretationRun,
)
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.models import Base
from quilchoom.infrastructure.database.repositories import (
    EvidenceRepository,
    InterpretationRunRepository,
    KnowledgeClaimRepository,
    ProjectRepository,
)


class RecordingInterpreter:
    def __init__(self) -> None:
        self.received_context: InterpretationContext | None = None

    def interpret(self, context: InterpretationContext) -> InterpretationResult:
        self.received_context = context
        return InterpretationResult()


class StubInterpreter:
    def __init__(self, result: InterpretationResult) -> None:
        self.result = result
        self.call_count = 0

    def interpret(self, context: InterpretationContext) -> InterpretationResult:
        self.call_count += 1
        return self.result


def test_interpret_history_passes_only_new_entries_and_active_claims(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repo = ProjectRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)
    claim_repo = KnowledgeClaimRepository(db_engine)
    run_repo = InterpretationRunRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence_a = Evidence(
        project_id=project.id,
        type="git_diff",
        content="First change",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_b = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Second change",
        captured_at=datetime.now(UTC),
        source="git",
    )

    evidence_repo.save(evidence_a)
    evidence_repo.save(evidence_b)

    event_a = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="First change",
        source="git",
        source_reference="commit-a",
    )
    event_b = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Second change",
        source="git",
        source_reference="commit-b",
    )

    entry_a = HistoryEntry(
        event=event_a,
        evidence=evidence_a,
    )
    entry_b = HistoryEntry(
        event=event_b,
        evidence=evidence_b,
    )

    history = DevelopmentHistory(
        project_id=project.id,
        entries=[entry_a, entry_b],
    )

    previous_run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence_a.id],
        claim_ids=[],
    )
    run_repo.save_with_claims(previous_run, [])

    active_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Active existing claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_a.id],
    )
    corrected_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Corrected existing claim",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.MEDIUM,
        status=ClaimStatus.CORRECTED,
        evidence_ids=[evidence_a.id],
    )
    invalidated_claim = KnowledgeClaim(
        project_id=project.id,
        statement="Invalidated existing claim",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.LOW,
        status=ClaimStatus.INVALIDATED,
        evidence_ids=[evidence_a.id],
    )

    claim_repo.save(active_claim)
    claim_repo.save(corrected_claim)
    claim_repo.save(invalidated_claim)

    interpreter = RecordingInterpreter()

    run = interpret_history(
        project=project,
        history=history,
        interpreter=interpreter,
        claim_repository=claim_repo,
        run_repository=run_repo,
    )

    received_context = interpreter.received_context

    assert received_context is not None

    assert received_context.project == project

    assert len(received_context.entries) == 1
    assert received_context.entries[0] == entry_b

    assert len(received_context.active_claims) == 1
    assert received_context.active_claims[0].id == active_claim.id

    assert run is not None
    assert run.evidence_ids == [evidence_b.id]
    assert run.claim_ids == []


def test_interpret_history_rejects_history_from_different_project(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    other_project = Project(
        name="Other Project",
        repository_path=tmp_path / "other",
    )

    claim_repo = KnowledgeClaimRepository(db_engine)
    run_repo = InterpretationRunRepository(db_engine)
    interpreter = RecordingInterpreter()

    history = DevelopmentHistory(
        project_id=other_project.id,
        entries=[],
    )

    with pytest.raises(InterpretationProjectMismatchError):
        interpret_history(
            project=project,
            history=history,
            interpreter=interpreter,
            claim_repository=claim_repo,
            run_repository=run_repo,
        )

    assert interpreter.received_context is None


def test_interpret_history_returns_none_when_all_evidence_is_already_interpreted(
    tmp_path,
):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repo = ProjectRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)
    claim_repo = KnowledgeClaimRepository(db_engine)
    run_repo = InterpretationRunRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Already interpreted change",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Already interpreted change",
        source="git",
        source_reference="commit-a",
    )

    history = DevelopmentHistory(
        project_id=project.id,
        entries=[
            HistoryEntry(
                event=event,
                evidence=evidence,
            )
        ],
    )

    previous_run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[evidence.id],
        claim_ids=[],
    )
    run_repo.save_with_claims(previous_run, [])

    interpreter = RecordingInterpreter()

    result = interpret_history(
        project=project,
        history=history,
        interpreter=interpreter,
        claim_repository=claim_repo,
        run_repository=run_repo,
    )

    assert result is None
    assert interpreter.received_context is None


def test_interpret_history_rejects_candidate_with_unavailable_evidence(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repo = ProjectRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)
    claim_repo = KnowledgeClaimRepository(db_engine)
    run_repo = InterpretationRunRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Available change",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Available change",
        source="git",
        source_reference="commit-a",
    )

    history = DevelopmentHistory(
        project_id=project.id,
        entries=[
            HistoryEntry(
                event=event,
                evidence=evidence,
            )
        ],
    )

    unavailable_evidence_id = uuid4()

    interpreter = StubInterpreter(
        InterpretationResult(
            candidates=[
                ClaimCandidate(
                    statement="Unsupported candidate",
                    basis=ClaimBasis.INFERENCE,
                    confidence=ClaimConfidence.MEDIUM,
                    evidence_ids=[unavailable_evidence_id],
                )
            ]
        )
    )

    with pytest.raises(InvalidCandidateEvidenceError):
        interpret_history(
            project=project,
            history=history,
            interpreter=interpreter,
            claim_repository=claim_repo,
            run_repository=run_repo,
        )

    assert run_repo.list_interpreted_evidence_ids(project.id) == set()
    assert claim_repo.list_for_project(project.id) == []


def test_interpret_history_persists_candidates_as_active_claims(tmp_path):
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)

    project_repo = ProjectRepository(db_engine)
    evidence_repo = EvidenceRepository(db_engine)
    claim_repo = KnowledgeClaimRepository(db_engine)
    run_repo = InterpretationRunRepository(db_engine)

    project = Project(
        name="Test Project",
        repository_path=tmp_path,
    )
    project_repo.save(project)

    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="Added authentication",
        captured_at=datetime.now(UTC),
        source="git",
    )
    evidence_repo.save(evidence)

    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Add authentication",
        source="git",
        source_reference="commit-auth",
    )

    history = DevelopmentHistory(
        project_id=project.id,
        entries=[
            HistoryEntry(
                event=event,
                evidence=evidence,
            )
        ],
    )

    interpreter = StubInterpreter(
        InterpretationResult(
            candidates=[
                ClaimCandidate(
                    statement="The project added authentication.",
                    basis=ClaimBasis.OBSERVATION,
                    confidence=ClaimConfidence.HIGH,
                    evidence_ids=[evidence.id],
                )
            ]
        )
    )

    run = interpret_history(
        project=project,
        history=history,
        interpreter=interpreter,
        claim_repository=claim_repo,
        run_repository=run_repo,
    )

    assert run is not None
    assert run.evidence_ids == [evidence.id]
    assert len(run.claim_ids) == 1

    persisted_claims = claim_repo.list_for_project(project.id)

    assert len(persisted_claims) == 1

    persisted_claim = persisted_claims[0]

    assert persisted_claim.id == run.claim_ids[0]
    assert persisted_claim.project_id == project.id
    assert persisted_claim.statement == "The project added authentication."
    assert persisted_claim.basis == ClaimBasis.OBSERVATION
    assert persisted_claim.confidence == ClaimConfidence.HIGH
    assert persisted_claim.status == ClaimStatus.ACTIVE
    assert persisted_claim.evidence_ids == [evidence.id]
