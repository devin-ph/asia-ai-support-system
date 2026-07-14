"""Narrow provider boundaries for the current customer-support flows."""

from __future__ import annotations

from dataclasses import dataclass

from app.providers.analyzer import (
    AnalyzerProvider,
    DeterministicAnalyzerProvider,
)
from app.providers.generation import (
    GroundedGenerationRequest,
    GroundedGenerationResult,
    GroundedResponseGenerator,
    GroundedResponseRuntime,
    GroundingEvidence,
    OpenAIGroundedResponseGenerator,
    ProviderAuthenticationError,
    ProviderMalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    TemplateResponseGenerator,
)
from app.providers.orders import FixtureOrdersProvider, OrdersProvider
from app.providers.policy import (
    GroundedPolicyProvider,
    PolicyProvider,
)


@dataclass(frozen=True, slots=True)
class ChatProviders:
    """Read-only capabilities that the chat route may invoke."""

    analyzer: AnalyzerProvider
    policy: PolicyProvider
    orders: OrdersProvider


def default_chat_providers(
    response_runtime: GroundedResponseRuntime | None = None,
) -> ChatProviders:
    """Build the deterministic read providers used by the local demo."""
    runtime = response_runtime or GroundedResponseRuntime(TemplateResponseGenerator())
    return ChatProviders(
        analyzer=DeterministicAnalyzerProvider(),
        policy=GroundedPolicyProvider(runtime),
        orders=FixtureOrdersProvider(),
    )


__all__ = [
    "AnalyzerProvider",
    "ChatProviders",
    "DeterministicAnalyzerProvider",
    "FixtureOrdersProvider",
    "GroundedGenerationRequest",
    "GroundedGenerationResult",
    "GroundedPolicyProvider",
    "GroundedResponseGenerator",
    "GroundedResponseRuntime",
    "GroundingEvidence",
    "OpenAIGroundedResponseGenerator",
    "OrdersProvider",
    "PolicyProvider",
    "ProviderAuthenticationError",
    "ProviderMalformedResponseError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    "TemplateResponseGenerator",
    "default_chat_providers",
]
