"""
Provides persistence operations for Quilchoom's domain objects.
"""

from datetime import UTC
from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from quilchoom.domain.correction import Correction
from quilchoom.domain.document import Document, DocumentVersion
from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.knowledge_claim import ClaimStatus, KnowledgeClaim
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.errors import (
    DocumentNotFoundError,
    EvidenceNotFoundError,
    EvidenceProjectMismatchError,
    KnowledgeClaimNotFoundError,
    KnowledgeClaimProjectMismatchError,
)
from quilchoom.infrastructure.database.models import (
    CorrectionModel,
    DocumentModel,
    DocumentVersionModel,
    EventModel,
    EvidenceModel,
    KnowledgeClaimModel,
    ProjectModel,
)


class ProjectRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: ProjectModel) -> Project:
        return Project(
            id=UUID(model.id),
            name=model.name,
            repository_path=Path(model.repository_path),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def save(self, project: Project) -> None:
        with Session(self.engine) as session:
            project_model = ProjectModel(
                id=str(project.id),
                name=project.name,
                repository_path=str(project.repository_path),
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
            session.add(project_model)
            session.commit()

    def get_by_id(self, project_id: UUID) -> Project | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(ProjectModel).where(ProjectModel.id == str(project_id))
            ).first()

            if model is None:
                return None

            project = self._to_domain(model)

            return project

    def get_by_repository_path(self, repository_path: Path) -> Project | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(ProjectModel).where(
                    ProjectModel.repository_path == str(repository_path)
                )
            ).first()

            if model is None:
                return None

            project = self._to_domain(model)

            return project


class EventRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: EventModel) -> Event:
        return Event(
            id=UUID(model.id),
            project_id=UUID(model.project_id),
            type=model.type,
            timestamp=model.timestamp.replace(tzinfo=UTC),
            summary=model.summary,
            source=model.source,
            source_reference=model.source_reference,
            metadata=model.event_metadata,
        )

    def save(self, event: Event) -> None:
        with Session(self.engine) as session:
            event_model = EventModel(
                id=str(event.id),
                project_id=str(event.project_id),
                type=event.type,
                timestamp=event.timestamp.replace(tzinfo=None),
                summary=event.summary,
                source=event.source,
                source_reference=event.source_reference,
                event_metadata=event.metadata,
            )
            session.add(event_model)
            session.commit()

    def get_by_id(self, event_id: UUID) -> Event | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(EventModel).where(EventModel.id == str(event_id))
            ).first()

            if model is None:
                return None

            event = self._to_domain(model)

            return event

    def get_by_source_reference(
        self,
        project_id: UUID,
        source: str,
        source_reference: str,
    ) -> Event | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(EventModel).where(
                    EventModel.project_id == str(project_id),
                    EventModel.source == source,
                    EventModel.source_reference == source_reference,
                )
            ).first()

            if model is None:
                return None

            return self._to_domain(model)

    def list_for_project(self, project_id: UUID) -> list[Event]:
        with Session(self.engine) as session:
            models = session.scalars(
                select(EventModel)
                .where(EventModel.project_id == str(project_id))
                .order_by(EventModel.timestamp.asc())
            ).all()

            events = [self._to_domain(model) for model in models]

            return events


class EvidenceRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: EvidenceModel) -> Evidence:
        return Evidence(
            id=UUID(model.id),
            project_id=UUID(model.project_id),
            type=model.type,
            content=model.content,
            reference=model.reference,
            captured_at=model.captured_at.replace(tzinfo=UTC),
            source=model.source,
            metadata=model.evidence_metadata,
        )

    def save(self, evidence: Evidence) -> None:
        with Session(self.engine) as session:
            evidence_model = EvidenceModel(
                id=str(evidence.id),
                project_id=str(evidence.project_id),
                type=evidence.type,
                content=evidence.content,
                reference=evidence.reference,
                captured_at=evidence.captured_at.replace(tzinfo=None),
                source=evidence.source,
                evidence_metadata=evidence.metadata,
            )
            session.add(evidence_model)
            session.commit()

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(EvidenceModel).where(EvidenceModel.id == str(evidence_id))
            ).first()

            if model is None:
                return None

            evidence = self._to_domain(model)

            return evidence

    def get_by_reference(
        self,
        project_id: UUID,
        source: str,
        reference: str,
    ) -> Evidence | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(EvidenceModel).where(
                    EvidenceModel.project_id == str(project_id),
                    EvidenceModel.source == source,
                    EvidenceModel.reference == reference,
                )
            ).first()

            if model is None:
                return None

            return self._to_domain(model)

    def list_for_project(self, project_id: UUID) -> list[Evidence]:
        with Session(self.engine) as session:
            models = session.scalars(
                select(EvidenceModel)
                .where(EvidenceModel.project_id == str(project_id))
                .order_by(EvidenceModel.captured_at.asc())
            ).all()

            evidence = [self._to_domain(model) for model in models]

            return evidence


class KnowledgeClaimRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: KnowledgeClaimModel) -> KnowledgeClaim:
        return KnowledgeClaim(
            id=UUID(model.id),
            project_id=UUID(model.project_id),
            statement=model.statement,
            basis=model.basis,
            confidence=model.confidence,
            status=model.status,
            evidence_ids=[UUID(evidence.id) for evidence in model.evidence],
        )

    def save(self, claim: KnowledgeClaim) -> None:
        with Session(self.engine) as session:
            evidence_models = session.scalars(
                select(EvidenceModel).where(
                    EvidenceModel.id.in_(
                        [str(evidence_id) for evidence_id in claim.evidence_ids]
                    )
                )
            ).all()

            found_evidence_ids = {UUID(model.id) for model in evidence_models}
            missing_evidence_ids = set(claim.evidence_ids) - found_evidence_ids

            if missing_evidence_ids:
                raise EvidenceNotFoundError(
                    "Evidence not found: "
                    + ", ".join(
                        str(evidence_id) for evidence_id in missing_evidence_ids
                    )
                )

            mismatched_evidence_ids = [
                UUID(model.id)
                for model in evidence_models
                if model.project_id != str(claim.project_id)
            ]

            if mismatched_evidence_ids:
                raise EvidenceProjectMismatchError(
                    "Evidence belongs to a different project: "
                    + ", ".join(
                        str(evidence_id) for evidence_id in mismatched_evidence_ids
                    )
                )

            claim_model = KnowledgeClaimModel(
                id=str(claim.id),
                project_id=str(claim.project_id),
                statement=claim.statement,
                basis=claim.basis,
                confidence=claim.confidence,
                status=claim.status,
                evidence=evidence_models,
            )
            session.add(claim_model)
            session.commit()

    def get_by_id(self, claim_id: UUID) -> KnowledgeClaim | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(KnowledgeClaimModel).where(
                    KnowledgeClaimModel.id == str(claim_id)
                )
            ).first()

            if model is None:
                return None

            claim = self._to_domain(model)

            return claim

    def list_for_project(self, project_id: UUID) -> list[KnowledgeClaim]:
        with Session(self.engine) as session:
            models = session.scalars(
                select(KnowledgeClaimModel).where(
                    KnowledgeClaimModel.project_id == str(project_id)
                )
            ).all()

            claims = [self._to_domain(model) for model in models]

            return claims


class CorrectionRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: CorrectionModel) -> Correction:
        return Correction(
            id=UUID(model.id),
            project_id=UUID(model.project_id),
            target_claim_id=UUID(model.target_claim_id),
            reason=model.reason,
            replacement_claim_id=(
                UUID(model.replacement_claim_id)
                if model.replacement_claim_id is not None
                else None
            ),
            created_at=model.created_at.replace(tzinfo=UTC),
        )

    def _to_model(self, correction: Correction) -> CorrectionModel:
        return CorrectionModel(
            id=str(correction.id),
            project_id=str(correction.project_id),
            target_claim_id=str(correction.target_claim_id),
            reason=correction.reason,
            replacement_claim_id=(
                str(correction.replacement_claim_id)
                if correction.replacement_claim_id is not None
                else None
            ),
            created_at=correction.created_at,
        )

    def save(self, correction: Correction) -> None:
        with Session(self.engine) as session:
            correction_model = self._to_model(correction)
            session.add(correction_model)
            session.commit()

    def save_with_claim_status_update(
        self,
        correction: Correction,
        status: ClaimStatus,
    ) -> None:
        with Session(self.engine) as session:
            target_model = session.scalars(
                select(KnowledgeClaimModel).where(
                    KnowledgeClaimModel.id == str(correction.target_claim_id)
                )
            ).first()

            if target_model is None:
                raise KnowledgeClaimNotFoundError(
                    f"Knowledge claim not found: {correction.target_claim_id}"
                )

            target_model.status = status

            correction_model = self._to_model(correction)
            session.add(correction_model)
            session.commit()

    def get_by_id(self, correction_id: UUID) -> Correction | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(CorrectionModel).where(CorrectionModel.id == str(correction_id))
            ).first()

            if model is None:
                return None

            correction = self._to_domain(model)

            return correction

    def list_for_project(self, project_id: UUID) -> list[Correction]:
        with Session(self.engine) as session:
            models = session.scalars(
                select(CorrectionModel).where(
                    CorrectionModel.project_id == str(project_id)
                )
            ).all()

            corrections = [self._to_domain(model) for model in models]

            return corrections


class DocumentRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: DocumentModel) -> Document:
        return Document(
            id=UUID(model.id),
            project_id=UUID(model.project_id),
            key=model.key,
            kind=model.kind,
            created_at=model.created_at.replace(tzinfo=UTC),
        )

    def save(self, document: Document) -> None:
        with Session(self.engine) as session:
            document_model = DocumentModel(
                id=str(document.id),
                project_id=str(document.project_id),
                key=document.key,
                kind=document.kind,
                created_at=document.created_at.replace(tzinfo=None),
            )
            session.add(document_model)
            session.commit()

    def get_by_id(self, document_id: UUID) -> Document | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(DocumentModel).where(DocumentModel.id == str(document_id))
            ).first()

            if model is None:
                return None

            document = self._to_domain(model)

            return document

    def get_by_key(self, project_id: UUID, key: str) -> Document | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(DocumentModel).where(
                    DocumentModel.project_id == str(project_id),
                    DocumentModel.key == key,
                )
            ).first()

            if model is None:
                return None

            document = self._to_domain(model)

            return document

    def list_for_project(self, project_id: UUID) -> list[Document]:
        with Session(self.engine) as session:
            models = session.scalars(
                select(DocumentModel)
                .where(DocumentModel.project_id == str(project_id))
                .order_by(
                    DocumentModel.created_at.asc(),
                    DocumentModel.id.asc(),
                )
            ).all()

            documents = [self._to_domain(model) for model in models]

            return documents


class DocumentVersionRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def _to_domain(self, model: DocumentVersionModel) -> DocumentVersion:
        return DocumentVersion(
            id=UUID(model.id),
            document_id=UUID(model.document_id),
            version_number=model.version_number,
            content=model.content,
            origin=model.origin,
            claim_ids=[UUID(claim.id) for claim in model.claims],
            created_at=model.created_at.replace(tzinfo=UTC),
        )

    def save(self, version: DocumentVersion) -> None:
        with Session(self.engine) as session:
            document_model = session.scalars(
                select(DocumentModel).where(
                    DocumentModel.id == str(version.document_id)
                )
            ).first()

            if document_model is None:
                raise DocumentNotFoundError(
                    f"Document not found: {version.document_id}"
                )

            claim_models = session.scalars(
                select(KnowledgeClaimModel).where(
                    KnowledgeClaimModel.id.in_(
                        [str(claim_id) for claim_id in version.claim_ids]
                    )
                )
            ).all()

            found_claim_ids = {UUID(model.id) for model in claim_models}
            missing_claim_ids = set(version.claim_ids) - found_claim_ids

            if missing_claim_ids:
                raise KnowledgeClaimNotFoundError(
                    "Knowledge claim not found: "
                    + ", ".join(str(claim_id) for claim_id in missing_claim_ids)
                )

            mismatched_claim_ids = [
                UUID(claim_model.id)
                for claim_model in claim_models
                if claim_model.project_id != document_model.project_id
            ]

            if mismatched_claim_ids:
                raise KnowledgeClaimProjectMismatchError(
                    "Knowledge claim belongs to a different project: "
                    + ", ".join(str(claim_id) for claim_id in mismatched_claim_ids)
                )

            version_model = DocumentVersionModel(
                id=str(version.id),
                document_id=str(version.document_id),
                version_number=version.version_number,
                content=version.content,
                origin=version.origin,
                claims=claim_models,
                created_at=version.created_at.replace(tzinfo=None),
            )
            session.add(version_model)
            session.commit()

    def get_by_id(self, version_id: UUID) -> DocumentVersion | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(DocumentVersionModel).where(
                    DocumentVersionModel.id == str(version_id)
                )
            ).first()

            if model is None:
                return None

            version = self._to_domain(model)

            return version

    def list_for_document(self, document_id: UUID) -> list[DocumentVersion]:
        with Session(self.engine) as session:
            models = session.scalars(
                select(DocumentVersionModel)
                .where(DocumentVersionModel.document_id == str(document_id))
                .order_by(DocumentVersionModel.version_number.asc())
            ).all()

            versions = [self._to_domain(model) for model in models]

            return versions

    def get_latest(self, document_id: UUID) -> DocumentVersion | None:
        with Session(self.engine) as session:
            model = session.scalars(
                select(DocumentVersionModel)
                .where(DocumentVersionModel.document_id == str(document_id))
                .order_by(DocumentVersionModel.version_number.desc())
            ).first()

            if model is None:
                return None

            version = self._to_domain(model)

            return version
