"""
Generates documentation artifacts from active project knowledge.
"""

from quilchoom.application.create_document_version import create_document_version
from quilchoom.application.errors import InvalidGeneratedClaimError, NoActiveClaimsError
from quilchoom.domain.document import Document, DocumentVersion, DocumentVersionOrigin
from quilchoom.domain.knowledge_claim import ClaimStatus
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    KnowledgeClaimRepository,
)
from quilchoom.interfaces.document_generator import (
    DocumentGenerationContext,
    DocumentGenerator,
)


def generate_document(
    project: Project,
    key: str,
    kind: str,
    generator: DocumentGenerator,
    document_repository: DocumentRepository,
    version_repository: DocumentVersionRepository,
    claim_repository: KnowledgeClaimRepository,
) -> DocumentVersion:
    existing_document = document_repository.get_by_key(project.id, key)

    if existing_document is None:
        document = Document(
            project_id=project.id,
            key=key,
            kind=kind,
        )

    else:
        document = existing_document

    claims = claim_repository.list_for_project(project.id)
    active_claims = [claim for claim in claims if claim.status == ClaimStatus.ACTIVE]

    if not active_claims:
        raise NoActiveClaimsError(
            f"No active knowledge claims available for project: {project.id}"
        )

    context = DocumentGenerationContext(
        project=project,
        document=document,
        claims=active_claims,
    )
    result = generator.generate(context)

    allowed_claim_ids = {claim.id for claim in active_claims}

    for claim_id in result.claim_ids:
        if claim_id not in allowed_claim_ids:
            raise InvalidGeneratedClaimError(
                f"Generated document references unavailable claim: {claim_id}"
            )

    if existing_document is None:
        version = DocumentVersion(
            document_id=document.id,
            version_number=1,
            content=result.content,
            origin=DocumentVersionOrigin.GENERATED,
            claim_ids=result.claim_ids,
        )
        document_repository.save_with_initial_version(document, version)

        return version

    return create_document_version(
        document_id=document.id,
        content=result.content,
        origin=DocumentVersionOrigin.GENERATED,
        claim_ids=result.claim_ids,
        document_repository=document_repository,
        version_repository=version_repository,
    )
