"""
Unit tests on environment-based AI credential resolution.
"""

import pytest

from quilchoom.infrastructure.ai.credentials import resolve_environment_credential
from quilchoom.infrastructure.ai.errors import AIConfigurationError


def test_resolves_environment_credential(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TEST_AI_API_KEY", "secret-value")

    credential = resolve_environment_credential("TEST_AI_API_KEY")

    assert credential == "secret-value"


def test_strips_environment_credential_whitespace(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TEST_AI_API_KEY", "  secret-value  ")

    credential = resolve_environment_credential("TEST_AI_API_KEY")

    assert credential == "secret-value"


def test_rejects_missing_environment_credential(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("TEST_AI_API_KEY", raising=False)

    with pytest.raises(
        AIConfigurationError,
        match="TEST_AI_API_KEY",
    ):
        resolve_environment_credential("TEST_AI_API_KEY")


def test_rejects_empty_environment_credential(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TEST_AI_API_KEY", "")

    with pytest.raises(
        AIConfigurationError,
        match="TEST_AI_API_KEY",
    ):
        resolve_environment_credential("TEST_AI_API_KEY")


def test_rejects_whitespace_only_environment_credential(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("TEST_AI_API_KEY", "   ")

    with pytest.raises(
        AIConfigurationError,
        match="TEST_AI_API_KEY",
    ):
        resolve_environment_credential("TEST_AI_API_KEY")
