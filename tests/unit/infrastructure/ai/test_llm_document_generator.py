"""
Unit tests on LLM-backed document generation behavior.
"""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from quilchoom.domain.document import Document
from quilchoom.domain.knowledge_claim import (
    ClaimBasis,
    ClaimConfidence,
    ClaimStatus,
    KnowledgeClaim,
)
from quilchoom.domain.project import Project
from quilchoom.infrastructure.ai.errors import AIResponseError
from quilchoom.infrastructure.ai.llm_document_generator import LLMDocumentGenerator
from quilchoom.infrastructure.ai.models import AIDocumentGenerationOutput
from quilchoom.interfaces.document_generator import DocumentGenerationContext
from quilchoom.interfaces.llm_provider import (
    JSONSchema,
    LLMRequest,
    LLMResponse,
)


class RecordingLLMProvider:
    """Records structured generation calls for document generator tests."""

    def generate_structured(
        self,
        request: LLMRequest,
        schema: JSONSchema,
    ) -> LLMResponse:
        self.request = request
        self.schema = schema

        input_data = json.loads(request.input)
        claim_id = input_data["claims"][0]["id"]

        return LLMResponse(
            output={
                "content": "# Quilchoom",
                "claim_ids": [claim_id],
            }
        )


def test_document_generator_sends_only_deliberately_projected_context(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)
    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Quilchoom records development activity.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    context = DocumentGenerationContext(
        project=project,
        document=document,
        claims=[claim],
    )

    provider = RecordingLLMProvider()
    generator = LLMDocumentGenerator(provider)

    generator.generate(context)

    input_data = json.loads(provider.request.input)

    assert input_data["project"]["name"] == "Quilchoom"
    assert set(input_data["project"]) == {"name"}

    assert input_data["document"]["key"] == "readme"
    assert input_data["document"]["kind"] == "readme"
    assert set(input_data["document"]) == {"key", "kind"}

    claim_data = input_data["claims"][0]

    assert set(claim_data) == {
        "id",
        "statement",
        "basis",
        "confidence",
    }
    assert claim_data["id"] == str(claim.id)
    assert claim_data["statement"] == claim.statement
    assert claim_data["basis"] == ClaimBasis.OBSERVATION.value
    assert claim_data["confidence"] == ClaimConfidence.HIGH.value

    assert "repository_path" not in input_data["project"]
    assert "project_id" not in claim_data
    assert "status" not in claim_data
    assert "evidence_ids" not in claim_data


def test_document_generator_passes_output_schema_to_provider(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)
    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Quilchoom records development activity.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    context = DocumentGenerationContext(
        project=project,
        document=document,
        claims=[claim],
    )

    provider = RecordingLLMProvider()
    generator = LLMDocumentGenerator(provider)

    generator.generate(context)

    assert provider.schema == AIDocumentGenerationOutput.model_json_schema()


def test_document_generator_maps_valid_ai_output_to_domain_result(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)
    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Quilchoom records development activity.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    context = DocumentGenerationContext(
        project=project,
        document=document,
        claims=[claim],
    )

    class DocumentProvider:
        def generate_structured(
            self,
            request: LLMRequest,
            schema: JSONSchema,
        ) -> LLMResponse:
            return LLMResponse(
                output={
                    "content": "# Quilchoom\n\nQuilchoom records development activity.",
                    "claim_ids": [str(claim.id)],
                }
            )

    generator = LLMDocumentGenerator(DocumentProvider())

    result = generator.generate(context)

    assert result.content == ("# Quilchoom\n\nQuilchoom records development activity.")
    assert result.claim_ids == [claim.id]


def test_document_generator_translates_invalid_ai_output_to_response_error(tmp_path):
    project = Project(name="Quilchoom", repository_path=tmp_path)
    document = Document(
        project_id=project.id,
        key="readme",
        kind="readme",
    )
    claim = KnowledgeClaim(
        project_id=project.id,
        statement="Quilchoom records development activity.",
        basis=ClaimBasis.OBSERVATION,
        confidence=ClaimConfidence.HIGH,
        status=ClaimStatus.ACTIVE,
        evidence_ids=[uuid4()],
    )

    context = DocumentGenerationContext(
        project=project,
        document=document,
        claims=[claim],
    )

    class InvalidOutputProvider:
        def generate_structured(
            self,
            request: LLMRequest,
            schema: JSONSchema,
        ) -> LLMResponse:
            return LLMResponse(
                output={
                    "content": "",
                    "claim_ids": [],
                }
            )

    generator = LLMDocumentGenerator(InvalidOutputProvider())

    with pytest.raises(AIResponseError) as exc_info:
        generator.generate(context)

    assert isinstance(exc_info.value.__cause__, ValidationError)
