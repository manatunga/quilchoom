"""
Provides persistence operations for Quilchoom's domain objects.
"""

from datetime import UTC
from pathlib import Path
from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from quilchoom.domain.event import Event
from quilchoom.domain.evidence import Evidence
from quilchoom.domain.knowledge_claim import KnowledgeClaim
from quilchoom.domain.project import Project
from quilchoom.infrastructure.database.errors import (
    EvidenceNotFoundError,
    EvidenceProjectMismatchError,
)
from quilchoom.infrastructure.database.models import (
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
