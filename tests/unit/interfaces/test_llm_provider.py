"""
Tests the provider-neutral LLM interface models.
"""

import pytest
from pydantic import ValidationError

from quilchoom.interfaces.llm_provider import LLMUsage


def test_llm_usage_accepts_zero_for_both_token_counts():
    usage = LLMUsage(input_tokens=0, output_tokens=0)

    assert usage.input_tokens == 0
    assert usage.output_tokens == 0


def test_llm_usage_rejects_negative_token_counts():
    with pytest.raises(ValidationError):
        LLMUsage(input_tokens=-1)

    with pytest.raises(ValidationError):
        LLMUsage(output_tokens=-1)
