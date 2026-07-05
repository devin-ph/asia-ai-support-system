"""Provider boundary for intent and sentiment analysis."""

from __future__ import annotations

from typing import Protocol

from app.intent import IntentAnalysis, analyze_message


class AnalyzerProvider(Protocol):
    """Analyze one customer message into the public deterministic labels."""

    def analyze(self, text: str) -> IntentAnalysis:
        """Return intent and sentiment for one message."""
        ...


class DeterministicAnalyzerProvider:
    """Adapt the current rule-based analyzer to the provider contract."""

    def analyze(self, text: str) -> IntentAnalysis:
        return analyze_message(text)
