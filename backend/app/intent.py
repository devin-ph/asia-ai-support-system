"""Deterministic Vietnamese intent and sentiment analysis."""

from __future__ import annotations

import enum
import re
import unicodedata
from dataclasses import dataclass


class IntentLabel(str, enum.Enum):
    """Supported customer-support intents."""

    ORDER_LOOKUP = "order_lookup"
    SHIPPING_POLICY = "shipping_policy"
    RETURN_REFUND = "return_refund"
    WARRANTY = "warranty"
    TICKET_REQUEST = "ticket_request"
    OTHER = "other"


class SentimentLabel(str, enum.Enum):
    """Supported coarse sentiment labels."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


@dataclass(frozen=True)
class IntentAnalysis:
    """Combined deterministic analysis result."""

    intent: IntentLabel
    sentiment: SentimentLabel


_ORDER_ID_PATTERN = re.compile(r"\bASIA[-\s]?\d{4}\b", re.IGNORECASE)

_INTENT_KEYWORDS: tuple[tuple[IntentLabel, tuple[str, ...]], ...] = (
    (
        IntentLabel.TICKET_REQUEST,
        (
            "tao phieu",
            "mo phieu",
            "lap phieu",
            "phieu ho tro",
            "khieu nai",
            "ticket",
            "complaint",
        ),
    ),
    (
        IntentLabel.ORDER_LOOKUP,
        (
            "don hang",
            "ma don",
            "tra cuu",
            "tracking",
            "order",
        ),
    ),
    (
        IntentLabel.RETURN_REFUND,
        (
            "doi tra",
            "doi hang",
            "tra hang",
            "hoan tien",
            "hoan lai",
            "return",
            "refund",
        ),
    ),
    (
        IntentLabel.WARRANTY,
        (
            "bao hanh",
            "warranty",
        ),
    ),
    (
        IntentLabel.SHIPPING_POLICY,
        (
            "phi giao hang",
            "phi van chuyen",
            "thoi gian giao hang",
            "chinh sach giao hang",
            "giao nhanh",
            "shipping fee",
            "shipping policy",
        ),
    ),
)

_NEGATIVE_KEYWORDS = (
    "buc minh",
    "that vong",
    "khong hai long",
    "khieu nai",
    "qua cham",
    "chua nhan",
    "te",
    "hong",
    "loi",
)
_POSITIVE_KEYWORDS = (
    "cam on",
    "hai long",
    "rat tot",
    "tuyet voi",
    "ho tro tot",
)


def normalize_vietnamese(text: str) -> str:
    """Normalize Vietnamese text for accent-insensitive matching."""
    lowered = text.casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(character for character in decomposed if unicodedata.category(character) != "Mn")


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, text) is not None


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def detect_intent(text: str) -> IntentLabel:
    """Classify text into one supported intent using ordered rules."""
    normalized = normalize_vietnamese(text)

    ticket_keywords = _INTENT_KEYWORDS[0][1]
    if _contains_any(normalized, ticket_keywords):
        return IntentLabel.TICKET_REQUEST
    if _ORDER_ID_PATTERN.search(text):
        return IntentLabel.ORDER_LOOKUP

    for intent, keywords in _INTENT_KEYWORDS[1:]:
        if _contains_any(normalized, keywords):
            return intent
    return IntentLabel.OTHER


def detect_sentiment(text: str) -> SentimentLabel:
    """Classify text into positive, neutral, or negative sentiment."""
    normalized = normalize_vietnamese(text)
    if _contains_any(normalized, _NEGATIVE_KEYWORDS):
        return SentimentLabel.NEGATIVE
    if _contains_any(normalized, _POSITIVE_KEYWORDS):
        return SentimentLabel.POSITIVE
    return SentimentLabel.NEUTRAL


def analyze_message(text: str) -> IntentAnalysis:
    """Analyze intent and sentiment without external services."""
    return IntentAnalysis(
        intent=detect_intent(text),
        sentiment=detect_sentiment(text),
    )
