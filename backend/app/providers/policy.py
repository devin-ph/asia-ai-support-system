"""Application-owned policy retrieval, generation, and citation assembly."""

from __future__ import annotations

import re
from typing import Protocol

from app.policy_retrieval import LocalPolicyRetriever, PolicyEvidence
from app.policy_search import (
    INSUFFICIENT_CONTEXT_ANSWER,
    PolicySearchResult,
)
from app.providers.generation import (
    GroundedGenerationRequest,
    GroundedResponseRuntime,
    GroundingEvidence,
)
from app.schemas import Citation

_ORDER_ID_PATTERN = re.compile(r"ASIA(?:[-\s]?\d{4,})", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\w)")
_INTERNAL_CUSTOMER_ID_PATTERN = re.compile(
    r"demo[-_\s]+customer[-_\s]+\d+",
    re.IGNORECASE,
)
_ACTION_ID_PATTERN = re.compile(r"act_[a-z0-9_-]+", re.IGNORECASE)
_TICKET_ID_PATTERN = re.compile(r"tkt_[a-z0-9_-]+", re.IGNORECASE)
_STRUCTURED_DELIMITER_PATTERN = re.compile(r"[\[{]")
_SENSITIVE_PAYLOAD_PATTERN = re.compile(
    r"(?<!\w)[\"']?(?:ticket_payload|pending_action|admin_state|order_response|"
    r"internal_customer_id|customer_id|conversation_history|raw_logs?|action_id|"
    r"action_type|ticket_id|payload)[\"']?\s*[:=]",
    re.IGNORECASE,
)


class PolicyProvider(Protocol):
    """Answer one policy query without delegating citation ownership."""

    async def answer(
        self,
        query: str,
        *,
        request_id: str,
    ) -> PolicySearchResult:
        """Return a grounded answer or the insufficient-context result."""
        ...


class GroundedPolicyProvider:
    """Retrieve local evidence, generate text, and attach trusted citations."""

    def __init__(
        self,
        response_runtime: GroundedResponseRuntime,
        *,
        retriever: LocalPolicyRetriever | None = None,
    ) -> None:
        self._retriever = retriever or LocalPolicyRetriever()
        self._response_runtime = response_runtime

    async def answer(
        self,
        query: str,
        *,
        request_id: str,
    ) -> PolicySearchResult:
        policy_query = _extract_policy_portion(query)
        if policy_query is None:
            return _insufficient_context_result(lookup_performed=False)

        retrieval = self._retriever.retrieve(policy_query)
        if not retrieval.sufficient:
            return _insufficient_context_result()

        evidence = retrieval.evidence[:1]
        request = GroundedGenerationRequest(
            request_id=request_id,
            redacted_query=_redact_identifiers(policy_query),
            evidence=tuple(
                GroundingEvidence(
                    chunk_id=item.evidence_id,
                    text=item.text,
                )
                for item in evidence
            ),
        )
        generation = await self._response_runtime.generate_result(request)
        return PolicySearchResult(
            answer=generation.text,
            citations=build_citations_from(evidence),
            generation_fallback_reason=generation.fallback_reason,
        )


def redact_policy_query(query: str) -> str | None:
    """Remove tested identifiers and exclude structured application payloads."""
    policy_portion = _extract_policy_portion(query)
    return _redact_identifiers(policy_portion) if policy_portion is not None else None


def _extract_policy_portion(query: str) -> str | None:
    boundaries = tuple(
        match.start()
        for match in (
            _SENSITIVE_PAYLOAD_PATTERN.search(query),
            _STRUCTURED_DELIMITER_PATTERN.search(query),
        )
        if match is not None
    )
    boundary = min(boundaries) if boundaries else None
    policy_portion = query[:boundary] if boundary is not None else query
    policy_portion = " ".join(policy_portion.split())
    if boundary is not None:
        policy_portion = policy_portion.rstrip("{[(:,;\"' ")
    return policy_portion if re.search(r"\w", policy_portion) else None


def _redact_identifiers(policy_portion: str) -> str:
    redacted = _INTERNAL_CUSTOMER_ID_PATTERN.sub(
        "[CUSTOMER_ID]",
        policy_portion,
    )
    redacted = _ORDER_ID_PATTERN.sub("[ORDER_ID]", redacted)
    redacted = _ACTION_ID_PATTERN.sub("[ACTION_ID]", redacted)
    redacted = _TICKET_ID_PATTERN.sub("[TICKET_ID]", redacted)
    redacted = _EMAIL_PATTERN.sub("[EMAIL]", redacted)
    redacted = _PHONE_PATTERN.sub("[PHONE]", redacted)
    return redacted


def build_citations_from(
    evidence: tuple[PolicyEvidence, ...],
) -> tuple[Citation, ...]:
    """Build citation metadata exclusively from allowlisted local evidence."""
    return tuple(
        Citation(
            title=item.title,
            source=item.source,
            section=item.section,
        )
        for item in evidence
    )


def _insufficient_context_result(
    *,
    lookup_performed: bool = True,
) -> PolicySearchResult:
    return PolicySearchResult(
        answer=INSUFFICIENT_CONTEXT_ANSWER,
        citations=(),
        lookup_performed=lookup_performed,
    )


__all__ = [
    "GroundedPolicyProvider",
    "PolicyProvider",
    "build_citations_from",
    "redact_policy_query",
]
