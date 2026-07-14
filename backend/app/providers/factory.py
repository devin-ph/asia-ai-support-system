"""Construct the configured response generator without silent substitution."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.config import ProviderConfigurationError, ResponseGeneratorName, Settings
from app.providers.generation import (
    GroundedResponseGenerator,
    GroundedResponseRuntime,
    OpenAIClient,
    OpenAIGroundedResponseGenerator,
    TemplateResponseGenerator,
)


def build_response_generator(
    settings: Settings,
    *,
    openai_client: OpenAIClient | None = None,
) -> GroundedResponseGenerator:
    """Build exactly the selected implementation or fail configuration."""
    if settings.response_generator is ResponseGeneratorName.TEMPLATE:
        return TemplateResponseGenerator()

    if settings.response_generator is ResponseGeneratorName.OPENAI:
        if settings.llm_api_key is None or settings.llm_model is None:
            raise ProviderConfigurationError("openai response generator settings are incomplete")
        client = openai_client
        if client is None:
            client = AsyncOpenAI(
                api_key=settings.llm_api_key,
                timeout=settings.llm_timeout_seconds,
                max_retries=0,
            )
        return OpenAIGroundedResponseGenerator(client, model=settings.llm_model)

    raise ProviderConfigurationError(
        f"unsupported response generator: {settings.response_generator!s}"
    )


def build_response_runtime(
    settings: Settings,
    *,
    openai_client: OpenAIClient | None = None,
    logger: logging.Logger | None = None,
) -> GroundedResponseRuntime:
    """Build the selected generator with deterministic transient fallback."""
    return GroundedResponseRuntime(
        build_response_generator(settings, openai_client=openai_client),
        logger=logger,
    )


__all__ = ["build_response_generator", "build_response_runtime"]
