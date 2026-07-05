"""Provider boundary for grounded policy retrieval."""

from __future__ import annotations

from typing import Protocol

from app.policy_search import PolicySearchResult, search_policy


class PolicyProvider(Protocol):
    """Answer one query from trusted policy evidence."""

    def search(self, query: str) -> PolicySearchResult:
        """Return a grounded answer or the insufficient-context result."""
        ...


class KeywordPolicyProvider:
    """Adapt the current allowlisted keyword search to the contract."""

    def search(self, query: str) -> PolicySearchResult:
        return search_policy(query)
