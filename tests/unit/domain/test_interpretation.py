"""
Unit tests for Quilchoom's knowledge interpretation domain objects.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.history import HistoryEntry
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


def test_interpretation_context_accepts_history_without_active_claims():
    project = Project(
        name="Quilchoom",
        repository_path=Path("/tmp/quilchoom"),
    )
    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Add interpretation support",
        source="git",
        source_reference="abc123",
    )
    evidence = Evidence(
        project_id=project.id,
        type="git_diff",
        content="diff content",
        captured_at=datetime.now(UTC),
        source="git",
        reference="abc123",
    )
    entry = HistoryEntry(event=event, evidence=evidence)

    context = InterpretationContext(
        project=project,
        entries=[entry],
    )

    assert context.project == project
    assert context.entries == [entry]
    assert context.active_claims == []


def test_interpretation_context_accepts_active_claims():
    project = Project(
        name="Quilchoom",
        repository_path=Path("/tmp/quilchoom"),
    )
    evidence_id = uuid4()
    event = Event(
        project_id=project.id,
        type="git_commit",
        timestamp=datetime.now(UTC),
        summary="Add interpretation support",
        source="git",
        source_reference="abc123",
    )
    evidence = Evidence(
        id=evidence_id,
        project_id=project.id,
        type="git_diff",
        content="diff content",
        captured_at=datetime.now(UTC),
        source="git",
        reference="abc123",
    )
    entry = HistoryEntry(event=event, evidence=evidence)
    claim = KnowledgeClaim(
        project_id=project.id,
        statement="The project uses knowledge interpretation.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[evidence_id],
    )

    context = InterpretationContext(
        project=project,
        entries=[entry],
        active_claims=[claim],
    )

    assert context.active_claims == [claim]


def test_interpretation_context_rejects_empty_entries():
    project = Project(
        name="Quilchoom",
        repository_path=Path("/tmp/quilchoom"),
    )

    with pytest.raises(ValidationError):
        InterpretationContext(
            project=project,
            entries=[],
        )


def test_claim_candidate_accepts_valid_candidate():
    evidence_id = uuid4()

    candidate = ClaimCandidate(
        statement="The project added knowledge interpretation.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        evidence_ids=[evidence_id],
    )

    assert candidate.statement == "The project added knowledge interpretation."
    assert candidate.basis == ClaimBasis.OBSERVATION
    assert candidate.confidence == ClaimConfidence.HIGH
    assert candidate.evidence_ids == [evidence_id]


def test_claim_candidate_accepts_inference_basis():
    candidate = ClaimCandidate(
        statement="The change may support future interpretation workflows.",
        basis=ClaimBasis.INFERENCE,
        confidence=ClaimConfidence.MEDIUM,
        evidence_ids=[uuid4()],
    )

    assert candidate.basis == ClaimBasis.INFERENCE


def test_claim_candidate_rejects_empty_statement():
    with pytest.raises(ValidationError):
        ClaimCandidate(
            statement="",
            basis=ClaimBasis.OBSERVATION,
            confidence=ClaimConfidence.HIGH,
            evidence_ids=[uuid4()],
        )


def test_claim_candidate_rejects_empty_evidence_ids():
    with pytest.raises(ValidationError):
        ClaimCandidate(
            statement="The project added knowledge interpretation.",
            basis=ClaimBasis.OBSERVATION,
            confidence=ClaimConfidence.HIGH,
            evidence_ids=[],
        )


def test_interpretation_result_defaults_to_no_candidates():
    result = InterpretationResult()

    assert result.candidates == []


def test_interpretation_result_accepts_candidates():
    candidate = ClaimCandidate(
        statement="The project added knowledge interpretation.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        evidence_ids=[uuid4()],
    )

    result = InterpretationResult(candidates=[candidate])

    assert result.candidates == [candidate]


def test_interpretation_run_accepts_valid_run():
    project_id = uuid4()
    evidence_id = uuid4()
    claim_id = uuid4()

    run = InterpretationRun(
        project_id=project_id,
        evidence_ids=[evidence_id],
        claim_ids=[claim_id],
    )

    assert run.project_id == project_id
    assert run.evidence_ids == [evidence_id]
    assert run.claim_ids == [claim_id]
    assert run.id is not None
    assert run.created_at.tzinfo == UTC


def test_interpretation_run_accepts_no_claims():
    run = InterpretationRun(
        project_id=uuid4(),
        evidence_ids=[uuid4()],
    )

    assert run.claim_ids == []


def test_interpretation_run_rejects_empty_evidence_ids():
    with pytest.raises(ValidationError):
        InterpretationRun(
            project_id=uuid4(),
            evidence_ids=[],
        )
