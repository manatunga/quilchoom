"""
Unit tests for Quilchoom's project-local configuration models.
"""

import pytest
from pydantic import ValidationError

from quilchoom.infrastructure.config import (
    DEFAULT_OPENAI_MODEL,
    QuilchoomConfig,
    create_default_config,
    load_config,
    write_default_config,
)


def test_quilchoom_config_accepts_valid_configuration():
    config = QuilchoomConfig.model_validate(
        {
            "ai": {
                "provider": "openai",
                "model": "test-model",
            }
        }
    )

    assert config.ai.provider == "openai"
    assert config.ai.model == "test-model"
    assert config.ai.endpoint is None


def test_quilchoom_config_rejects_unknown_top_level_field():
    with pytest.raises(ValidationError):
        QuilchoomConfig.model_validate(
            {
                "ai": {
                    "provider": "openai",
                    "model": "test-model",
                },
                "unknown": "value",
            }
        )


def test_quilchoom_config_rejects_unknown_ai_field():
    with pytest.raises(ValidationError):
        QuilchoomConfig.model_validate(
            {
                "ai": {
                    "provider": "openai",
                    "model": "test-model",
                    "unknown": "value",
                }
            }
        )


def test_load_config_reads_valid_toml(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("""
[ai]
provider = "openai"
model = "test-model"
""")

    config = load_config(config_path)

    assert config.ai.provider == "openai"
    assert config.ai.model == "test-model"
    assert config.ai.endpoint is None


def test_create_default_config():
    config = create_default_config()

    assert config.ai.provider == "openai"
    assert config.ai.model == DEFAULT_OPENAI_MODEL
    assert config.ai.endpoint is None
    assert isinstance(config, QuilchoomConfig)


def test_write_default_config_preserves_existing_config(tmp_path):
    config_path = tmp_path / "config.toml"
    existing_content = '[ai]\nprovider = "openai"\nmodel = "custom-model"\n'
    config_path.write_text(existing_content)

    config = write_default_config(config_path)

    assert config_path.read_text() == existing_content
    assert config.ai.model == "custom-model"


def test_write_default_config_creates_default_config(tmp_path):
    config_path = tmp_path / "config.toml"

    config = write_default_config(config_path)

    assert config_path.is_file()
    assert config_path.read_text() == (
        f'[ai]\nprovider = "openai"\nmodel = "{DEFAULT_OPENAI_MODEL}"\n'
    )
    assert config.ai.provider == "openai"
    assert config.ai.model == DEFAULT_OPENAI_MODEL
