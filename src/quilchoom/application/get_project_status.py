"""
Determines the current local workflow status of a Quilchoom project.
"""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from quilchoom.application.check_document_staleness import (
    is_document_version_stale,
)
from quilchoom.application.check_knowledge_status import count_pending_evidence
from quilchoom.domain.knowledge_claim import ClaimStatus
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    EvidenceRepository,
    InterpretationRunRepository,
    KnowledgeClaimRepository,
)
from quilchoom.infrastructure.git.repository import list_commit_shas


class DocumentState(str, Enum):
    """Defines the freshness state of a generated project document."""

    CURRENT = "current"
    STALE = "stale"


class DocumentStatus(BaseModel):
    """Represents the current status of a generated project document."""

    key: str
    kind: str
    version_number: int
    state: DocumentState


class ProjectStatus(BaseModel):
    """Represents the current local workflow status of a Quilchoom project."""

    total_commits: int
    pending_commits: int
    pending_evidence: int
    active_claims: int
    documents: list[DocumentStatus]


def get_project_status(
    project: Project,
    repository_root: Path,
    evidence_repository: EvidenceRepository,
    run_repository: InterpretationRunRepository,
    claim_repository: KnowledgeClaimRepository,
    document_repository: DocumentRepository,
    version_repository: DocumentVersionRepository,
) -> ProjectStatus:
    """Determines the current local workflow status of a project."""

    commit_shas = list_commit_shas(repository_root)

    evidence = evidence_repository.list_for_project(project.id)

    captured_commit_shas = {item.reference for item in evidence if item.source == "git"}

    total_commits = len(commit_shas)
    pending_commits = sum(1 for sha in commit_shas if sha not in captured_commit_shas)

    pending_evidence = count_pending_evidence(
        project=project,
        evidence_repository=evidence_repository,
        run_repository=run_repository,
    )

    claims = claim_repository.list_for_project(project.id)
    active_claims = sum(1 for claim in claims if claim.status == ClaimStatus.ACTIVE)

    documents = document_repository.list_for_project(project.id)

    document_statuses: list[DocumentStatus] = []

    for document in documents:
        latest_version = version_repository.get_latest(document.id)

        if latest_version is None:
            continue

        stale = is_document_version_stale(
            version=latest_version,
            claim_repository=claim_repository,
        )

        document_status = DocumentStatus(
            key=document.key,
            kind=document.kind,
            version_number=latest_version.version_number,
            state=(DocumentState.STALE if stale else DocumentState.CURRENT),
        )
        document_statuses.append(document_status)

    return ProjectStatus(
        total_commits=total_commits,
        pending_commits=pending_commits,
        pending_evidence=pending_evidence,
        active_claims=active_claims,
        documents=document_statuses,
    )
