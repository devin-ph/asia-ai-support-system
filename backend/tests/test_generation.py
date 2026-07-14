"""Async provider, fallback, cancellation, and telemetry contracts."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx
import pytest
from app.config import load_settings
from app.providers.factory import build_response_runtime
from app.providers.generation import (
    GROUNDING_INSTRUCTIONS,
    GroundedGenerationRequest,
    GroundedResponseRuntime,
    GroundingEvidence,
    OpenAIGroundedResponseGenerator,
    ProviderAuthenticationError,
    ProviderMalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    TemplateResponseGenerator,
)
from openai import APIConnectionError, APITimeoutError, AuthenticationError


@dataclass(frozen=True, slots=True)
class _FakeResponse:
    output_text: str


class _FakeResponsesAPI:
    def __init__(
        self,
        *,
        response: _FakeResponse | None = None,
        error: BaseException | None = None,
    ) -> None:
        self._response = response or _FakeResponse("Câu trả lời có căn cứ.")
        self._error = error
        self.calls: list[dict[str, object]] = []

    async def create(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
        store: bool,
    ) -> _FakeResponse:
        self.calls.append(
            {
                "model": model,
                "instructions": instructions,
                "input": input,
                "store": store,
            }
        )
        if self._error is not None:
            raise self._error
        return self._response


class _FakeOpenAIClient:
    def __init__(self, responses: _FakeResponsesAPI) -> None:
        self.responses = responses


class _FailingGenerator:
    provider_name = "openai"
    model = "test-model"
    prompt_version = "test-prompt-v1"

    def __init__(self, error: BaseException) -> None:
        self._error = error

    async def generate(self, _request: GroundedGenerationRequest) -> str:
        raise self._error


@pytest.fixture
def generation_request() -> GroundedGenerationRequest:
    return GroundedGenerationRequest(
        request_id="req-test-001",
        redacted_query="Đổi trả áp dụng trong bao lâu?",
        evidence=(
            GroundingEvidence(
                chunk_id="return-policy--conditions",
                text="Khách hàng có thể yêu cầu đổi trả trong vòng 7 ngày.",
            ),
        ),
    )


@pytest.mark.anyio
async def test_template_generator_is_offline_and_requires_evidence(
    generation_request: GroundedGenerationRequest,
) -> None:
    answer = await TemplateResponseGenerator().generate(generation_request)

    assert "7 ngày" in answer
    with pytest.raises(ValueError, match="requires evidence"):
        GroundedGenerationRequest(
            request_id="req-empty",
            redacted_query="Câu hỏi",
            evidence=(),
        )


@pytest.mark.anyio
async def test_openai_generator_sends_text_only_request_without_storage(
    generation_request: GroundedGenerationRequest,
) -> None:
    responses = _FakeResponsesAPI()
    generator = OpenAIGroundedResponseGenerator(
        _FakeOpenAIClient(responses),
        model="gpt-5.4-mini-2026-03-17",
    )

    answer = await generator.generate(generation_request)

    assert answer == "Câu trả lời có căn cứ."
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call["model"] == "gpt-5.4-mini-2026-03-17"
    assert call["instructions"] == GROUNDING_INSTRUCTIONS
    assert call["store"] is False
    assert generation_request.redacted_query in str(call["input"])
    assert generation_request.evidence[0].text in str(call["input"])
    assert set(call) == {"model", "instructions", "input", "store"}


@pytest.mark.anyio
async def test_openai_timeout_is_mapped_to_typed_error(
    generation_request: GroundedGenerationRequest,
) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    responses = _FakeResponsesAPI(error=APITimeoutError(request=request))
    generator = OpenAIGroundedResponseGenerator(
        _FakeOpenAIClient(responses),
        model="test-model",
    )

    with pytest.raises(ProviderTimeoutError, match="timed out"):
        await generator.generate(generation_request)


@pytest.mark.anyio
async def test_openai_connection_failure_is_mapped_to_unavailable(
    generation_request: GroundedGenerationRequest,
) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    responses = _FakeResponsesAPI(error=APIConnectionError(request=request))
    generator = OpenAIGroundedResponseGenerator(
        _FakeOpenAIClient(responses),
        model="test-model",
    )

    with pytest.raises(ProviderUnavailableError, match="unavailable"):
        await generator.generate(generation_request)


@pytest.mark.anyio
async def test_openai_authentication_rejection_is_not_disguised_as_success(
    generation_request: GroundedGenerationRequest,
) -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(401, request=request)
    error = AuthenticationError("invalid credential", response=response, body=None)
    responses = _FakeResponsesAPI(error=error)
    runtime = GroundedResponseRuntime(
        OpenAIGroundedResponseGenerator(
            _FakeOpenAIClient(responses),
            model="test-model",
        )
    )

    with pytest.raises(ProviderAuthenticationError, match="rejected authentication"):
        await runtime.generate(generation_request)


@pytest.mark.anyio
async def test_empty_output_is_mapped_to_malformed_response(
    generation_request: GroundedGenerationRequest,
) -> None:
    generator = OpenAIGroundedResponseGenerator(
        _FakeOpenAIClient(_FakeResponsesAPI(response=_FakeResponse("  "))),
        model="test-model",
    )

    with pytest.raises(ProviderMalformedResponseError, match="empty text"):
        await generator.generate(generation_request)


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (ProviderTimeoutError("timeout"), "timeout"),
        (ProviderUnavailableError("unavailable"), "unavailable"),
        (ProviderMalformedResponseError("malformed"), "malformed_response"),
    ],
)
@pytest.mark.anyio
async def test_runtime_uses_template_for_transient_or_malformed_failure(
    error: BaseException,
    reason: str,
    generation_request: GroundedGenerationRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    runtime = GroundedResponseRuntime(_FailingGenerator(error))

    with caplog.at_level(logging.INFO, logger="asia.providers.generation"):
        answer = await runtime.generate(generation_request)

    assert "7 ngày" in answer
    record = caplog.records[-1]
    assert record.fallback_reason == reason
    assert record.error_category == reason


@pytest.mark.anyio
async def test_cancellation_propagates_without_fallback(
    generation_request: GroundedGenerationRequest,
) -> None:
    runtime = GroundedResponseRuntime(_FailingGenerator(asyncio.CancelledError()))

    with pytest.raises(asyncio.CancelledError):
        await runtime.generate(generation_request)


@pytest.mark.anyio
async def test_telemetry_contains_metadata_but_not_secret_or_content(
    generation_request: GroundedGenerationRequest,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "test-placeholder-secret-value"
    settings = load_settings(
        {
            "ASIA_RESPONSE_GENERATOR": "openai",
            "ASIA_LLM_API_KEY": secret,
            "ASIA_LLM_MODEL": "test-model",
            "ASIA_LLM_TIMEOUT_SECONDS": "15",
        }
    )
    runtime = build_response_runtime(
        settings,
        openai_client=_FakeOpenAIClient(_FakeResponsesAPI()),
    )

    with caplog.at_level(logging.INFO, logger="asia.providers.generation"):
        await runtime.generate(generation_request)

    record = caplog.records[-1]
    assert record.request_id == generation_request.request_id
    assert record.provider == "openai"
    assert record.model == "test-model"
    assert record.prompt_version == "grounded-policy-v1"
    assert record.retrieved_chunk_ids == ("return-policy--conditions",)
    assert record.fallback_reason is None
    assert record.error_category is None
    serialized_log = repr(record.__dict__)
    assert secret not in serialized_log
    assert generation_request.redacted_query not in serialized_log
    assert generation_request.evidence[0].text not in serialized_log
