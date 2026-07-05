"""Narrow provider boundaries for the current customer-support flows."""

from __future__ import annotations

from dataclasses import dataclass

from app.providers.analyzer import (
    AnalyzerProvider,
    DeterministicAnalyzerProvider,
)
from app.providers.orders import FixtureOrdersProvider, OrdersProvider
from app.providers.policy import KeywordPolicyProvider, PolicyProvider


@dataclass(frozen=True, slots=True)
class ChatProviders:
    """Read-only capabilities that the chat route may invoke."""

    analyzer: AnalyzerProvider
    policy: PolicyProvider
    orders: OrdersProvider


def default_chat_providers() -> ChatProviders:
    """Build the deterministic provider set used by the v0.1 demo."""
    return ChatProviders(
        analyzer=DeterministicAnalyzerProvider(),
        policy=KeywordPolicyProvider(),
        orders=FixtureOrdersProvider(),
    )


__all__ = [
    "AnalyzerProvider",
    "ChatProviders",
    "DeterministicAnalyzerProvider",
    "FixtureOrdersProvider",
    "KeywordPolicyProvider",
    "OrdersProvider",
    "PolicyProvider",
    "default_chat_providers",
]
