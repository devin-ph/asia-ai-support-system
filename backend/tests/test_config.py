"""Configuration and factory contracts for the v0.2 generator runtime."""

from __future__ import annotations

import pytest
from app.config import (
    LLM_API_KEY_ENV,
    LLM_MODEL_ENV,
    LLM_TIMEOUT_ENV,
    RESPONSE_GENERATOR_ENV,
    ProviderConfigurationError,
    ResponseGeneratorName,
    Settings,
    load_settings,
)
from app.main import create_app
from app.providers.factory import build_response_generator
from app.providers.generation import (
    OpenAIGroundedResponseGenerator,
    TemplateResponseGenerator,
)


class _UnusedResponsesAPI:
    async def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
        store: bool,
    ) -> object:
        raise AssertionError("factory construction must not call the external provider")


class _UnusedOpenAIClient:
    responses = _UnusedResponsesAPI()


def test_template_settings_are_offline_by_default() -> None:
    settings = load_settings({})

    assert settings == Settings(
        response_generator=ResponseGeneratorName.TEMPLATE,
        llm_api_key=None,
        llm_model=None,
        llm_timeout_seconds=15.0,
    )
    assert isinstance(build_response_generator(settings), TemplateResponseGenerator)


@pytest.mark.parametrize(
    ("environment", "missing_name"),
    [
        (
            {
                RESPONSE_GENERATOR_ENV: "openai",
                LLM_MODEL_ENV: "gpt-5.4-mini-2026-03-17",
            },
            LLM_API_KEY_ENV,
        ),
        (
            {
                RESPONSE_GENERATOR_ENV: "openai",
                LLM_API_KEY_ENV: "test-placeholder-not-a-real-key",
            },
            LLM_MODEL_ENV,
        ),
    ],
)
def test_openai_settings_require_key_and_model(
    environment: dict[str, str],
    missing_name: str,
) -> None:
    with pytest.raises(ProviderConfigurationError, match=missing_name):
        load_settings(environment)


def test_unknown_generator_fails_instead_of_substituting_template() -> None:
    with pytest.raises(ProviderConfigurationError, match="template, openai"):
        load_settings({RESPONSE_GENERATOR_ENV: "external"})


@pytest.mark.parametrize("value", ["", "0", "-1", "121", "nan", "inf", "not-a-number"])
def test_timeout_must_be_a_finite_positive_number(value: str) -> None:
    with pytest.raises(ProviderConfigurationError, match=LLM_TIMEOUT_ENV):
        load_settings({LLM_TIMEOUT_ENV: value})


def test_factory_builds_openai_without_making_a_request() -> None:
    settings = load_settings(
        {
            RESPONSE_GENERATOR_ENV: "openai",
            LLM_API_KEY_ENV: "test-placeholder-not-a-real-key",
            LLM_MODEL_ENV: "gpt-5.4-mini-2026-03-17",
            LLM_TIMEOUT_ENV: "9.5",
        }
    )

    generator = build_response_generator(
        settings,
        openai_client=_UnusedOpenAIClient(),
    )

    assert isinstance(generator, OpenAIGroundedResponseGenerator)
    assert generator.provider_name == "openai"
    assert generator.model == "gpt-5.4-mini-2026-03-17"


def test_factory_configures_one_bounded_sdk_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    client = _UnusedOpenAIClient()

    def fake_async_openai(**kwargs: object) -> _UnusedOpenAIClient:
        captured.update(kwargs)
        return client

    monkeypatch.setattr("app.providers.factory.AsyncOpenAI", fake_async_openai)
    settings = load_settings(
        {
            RESPONSE_GENERATOR_ENV: "openai",
            LLM_API_KEY_ENV: "test-placeholder-not-a-real-key",
            LLM_MODEL_ENV: "gpt-5.4-mini-2026-03-17",
            LLM_TIMEOUT_ENV: "9.5",
        }
    )

    generator = build_response_generator(settings)

    assert isinstance(generator, OpenAIGroundedResponseGenerator)
    assert captured == {
        "api_key": "test-placeholder-not-a-real-key",
        "timeout": 9.5,
        "max_retries": 0,
    }


def test_factory_defensively_rejects_incomplete_openai_settings() -> None:
    settings = Settings(
        response_generator=ResponseGeneratorName.OPENAI,
        llm_api_key=None,
        llm_model=None,
        llm_timeout_seconds=15.0,
    )

    with pytest.raises(ProviderConfigurationError, match="incomplete"):
        build_response_generator(settings, openai_client=_UnusedOpenAIClient())


def test_application_startup_validates_selected_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RESPONSE_GENERATOR_ENV, "openai")
    monkeypatch.delenv(LLM_API_KEY_ENV, raising=False)
    monkeypatch.delenv(LLM_MODEL_ENV, raising=False)

    with pytest.raises(ProviderConfigurationError, match=LLM_API_KEY_ENV):
        create_app()
