"""Typed runtime configuration for the v0.2 response generator."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

RESPONSE_GENERATOR_ENV = "ASIA_RESPONSE_GENERATOR"
LLM_API_KEY_ENV = "ASIA_LLM_API_KEY"
LLM_MODEL_ENV = "ASIA_LLM_MODEL"
LLM_TIMEOUT_ENV = "ASIA_LLM_TIMEOUT_SECONDS"
DEFAULT_LLM_TIMEOUT_SECONDS = 15.0
MAX_LLM_TIMEOUT_SECONDS = 120.0


class ProviderConfigurationError(ValueError):
    """Raised when the selected provider cannot be configured safely."""


class ResponseGeneratorName(str, Enum):
    """Supported response generator implementations."""

    TEMPLATE = "template"
    OPENAI = "openai"


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated application settings with conditional provider requirements."""

    response_generator: ResponseGeneratorName
    llm_api_key: str | None
    llm_model: str | None
    llm_timeout_seconds: float


def _optional_value(environment: Mapping[str, str], name: str) -> str | None:
    value = environment.get(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def load_settings(environment: Mapping[str, str] | None = None) -> Settings:
    """Load and validate settings without reading or printing secret values."""
    values = os.environ if environment is None else environment

    raw_generator = values.get(RESPONSE_GENERATOR_ENV, ResponseGeneratorName.TEMPLATE.value)
    try:
        response_generator = ResponseGeneratorName(raw_generator.strip().casefold())
    except ValueError as exc:
        allowed = ", ".join(generator.value for generator in ResponseGeneratorName)
        raise ProviderConfigurationError(
            f"{RESPONSE_GENERATOR_ENV} must be one of: {allowed}"
        ) from exc

    raw_timeout = values.get(LLM_TIMEOUT_ENV, str(DEFAULT_LLM_TIMEOUT_SECONDS)).strip()
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise ProviderConfigurationError(f"{LLM_TIMEOUT_ENV} must be a positive number") from exc
    if not math.isfinite(timeout) or timeout <= 0 or timeout > MAX_LLM_TIMEOUT_SECONDS:
        raise ProviderConfigurationError(
            f"{LLM_TIMEOUT_ENV} must be greater than 0 and at most {MAX_LLM_TIMEOUT_SECONDS:g}"
        )

    api_key = _optional_value(values, LLM_API_KEY_ENV)
    model = _optional_value(values, LLM_MODEL_ENV)
    if response_generator is ResponseGeneratorName.OPENAI:
        missing = [
            name
            for name, value in (
                (LLM_API_KEY_ENV, api_key),
                (LLM_MODEL_ENV, model),
            )
            if value is None
        ]
        if missing:
            raise ProviderConfigurationError(
                "openai response generation requires: " + ", ".join(missing)
            )

    return Settings(
        response_generator=response_generator,
        llm_api_key=api_key,
        llm_model=model,
        llm_timeout_seconds=timeout,
    )


__all__ = [
    "DEFAULT_LLM_TIMEOUT_SECONDS",
    "LLM_API_KEY_ENV",
    "LLM_MODEL_ENV",
    "LLM_TIMEOUT_ENV",
    "MAX_LLM_TIMEOUT_SECONDS",
    "ProviderConfigurationError",
    "RESPONSE_GENERATOR_ENV",
    "ResponseGeneratorName",
    "Settings",
    "load_settings",
]
