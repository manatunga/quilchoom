"""
Defines Quilchoom's project-local configuration.
"""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from quilchoom.infrastructure.ai.config import AIConfig

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


class ConfigurationError(Exception):
    """Raised when Quilchoom's project-local configuration cannot be loaded."""


class QuilchoomConfig(BaseModel):
    """Represents validated project-local Quilchoom configuration."""

    model_config = ConfigDict(extra="forbid")

    ai: AIConfig


def load_config(config_path: Path) -> QuilchoomConfig:
    """Loads and validates Quilchoom's project-local configuration."""

    try:
        with config_path.open("rb") as file:
            config = tomllib.load(file)
    except FileNotFoundError as exc:
        raise ConfigurationError(
            f"Configuration file not found: {config_path}"
        ) from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(
            f"Configuration file contains invalid TOML: {config_path}"
        ) from exc

    try:
        return QuilchoomConfig.model_validate(config)
    except ValidationError as exc:
        raise ConfigurationError(
            f"Configuration file contains invalid settings: {config_path}"
        ) from exc


def create_default_config() -> QuilchoomConfig:
    """Creates Quilchoom's default project-local configuration."""

    ai_config = AIConfig(
        provider="openai",
        model=DEFAULT_OPENAI_MODEL,
    )

    return QuilchoomConfig(ai=ai_config)


def write_default_config(config_path: Path) -> QuilchoomConfig:
    """Writes Quilchoom's default project-local configuration."""

    if config_path.is_file():
        return load_config(config_path)

    config = create_default_config()

    content = f'[ai]\nprovider = "{config.ai.provider}"\nmodel = "{config.ai.model}"\n'

    config_path.write_text(content)

    return config
