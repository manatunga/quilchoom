"""
Orchestrates knowledge interpretation from reconstructed development history.
"""

from quilchoom.application.errors import (
    InterpretationProjectMismatchError,
    InvalidCandidateEvidenceError,
)
from quilchoom.domain.history import DevelopmentHistory
from quilchoom.domain.interpretation import InterpretationContext, InterpretationRun
from quilchoom.domain.knowledge_claim import ClaimStatus, KnowledgeClaim
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    InterpretationRunRepository,
    KnowledgeClaimRepository,
)
from quilchoom.interfaces.knowledge_interpreter import KnowledgeInterpreter


def interpret_history(
    project: Project,
    history: DevelopmentHistory,
    interpreter: KnowledgeInterpreter,
    claim_repository: KnowledgeClaimRepository,
    run_repository: InterpretationRunRepository,
) -> InterpretationRun | None:
    if project.id != history.project_id:
        raise InterpretationProjectMismatchError(
            f"Development history belongs to a different project: {history.project_id}"
        )

    interpreted_evidence_ids = run_repository.list_interpreted_evidence_ids(project.id)
    new_entries = [
        entry
        for entry in history.entries
        if entry.evidence.id not in interpreted_evidence_ids
    ]

    if not new_entries:
        return None

    existing_claims = claim_repository.list_for_project(project.id)
    active_claims = [
        claim for claim in existing_claims if claim.status == ClaimStatus.ACTIVE
    ]

    context = InterpretationContext(
        project=project,
        entries=new_entries,
        active_claims=active_claims,
    )

    result = interpreter.interpret(context)

    allowed_evidence_ids = {entry.evidence.id for entry in new_entries}

    for candidate in result.candidates:
        invalid_evidence_ids = set(candidate.evidence_ids) - allowed_evidence_ids

        if invalid_evidence_ids:
            raise InvalidCandidateEvidenceError(
                "Candidate references unavailable evidence: "
                + ", ".join(str(evidence_id) for evidence_id in invalid_evidence_ids)
            )

    claims: list[KnowledgeClaim] = []

    for candidate in result.candidates:
        claim = KnowledgeClaim(
            project_id=project.id,
            statement=candidate.statement,
            basis=candidate.basis,
            confidence=candidate.confidence,
            status=ClaimStatus.ACTIVE,
            evidence_ids=candidate.evidence_ids,
        )
        claims.append(claim)

    run = InterpretationRun(
        project_id=project.id,
        evidence_ids=[entry.evidence.id for entry in new_entries],
        claim_ids=[claim.id for claim in claims],
    )

    run_repository.save_with_claims(run, claims)

    return run
