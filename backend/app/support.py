"""Deterministic support logic for the local vertical slice."""

from __future__ import annotations

import re
import unicodedata

from app.demo_data import DEMO_CUSTOMER_ID, ORDERS, POLICIES, OrderRecord
from app.schemas import Citation, IntentLabel, OrderSummary, SentimentLabel

_ORDER_ID_PATTERN = re.compile(r"\bASIA[-\s]?\d{4}\b", re.IGNORECASE)

_TICKET_KEYWORDS = (
    "tao phieu",
    "mo phieu",
    "lap phieu",
    "khieu nai",
    "ticket",
    "complaint",
)
_POLICY_KEYWORDS = (
    "chinh sach",
    "doi tra",
    "tra hang",
    "hoan tien",
    "bao hanh",
    "phi giao hang",
    "phi van chuyen",
    "thoi gian giao hang",
    "policy",
    "return",
    "refund",
    "warranty",
)
_ORDER_KEYWORDS = (
    "don hang",
    "ma don",
    "tra cuu",
    "tracking",
    "order",
)
_NEGATIVE_KEYWORDS = (
    "buc minh",
    "that vong",
    "khieu nai",
    "qua cham",
    "te",
    "hong",
    "loi",
)
_POSITIVE_KEYWORDS = (
    "cam on",
    "hai long",
    "rat tot",
    "tuyet voi",
)

INSUFFICIENT_POLICY_REPLY = (
    "Mình chưa có đủ thông tin chính sách trong dữ liệu demo để trả lời chính "
    "xác câu hỏi này. Bạn có thể hỏi về đổi trả, hoàn tiền, bảo hành hoặc phí "
    "giao hàng."
)
ORDER_ID_REQUIRED_REPLY = (
    "Bạn vui lòng cung cấp mã đơn hàng theo định dạng ASIA-1001 để mình tra cứu."
)
ORDER_NOT_FOUND_REPLY = (
    "Không tìm thấy đơn hàng thuộc tài khoản demo với mã đã cung cấp."
)
GENERAL_REPLY = (
    "Xin chào! Mình là A.S.I.A, trợ lý hỗ trợ khách hàng. Bạn có thể hỏi về "
    "chính sách, tra cứu đơn hàng hoặc yêu cầu tạo phiếu hỗ trợ."
)


def _contains_keyword(text: str, keyword: str) -> bool:
    pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
    return re.search(pattern, text) is not None


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def normalize_vietnamese(text: str) -> str:
    """Normalize Vietnamese text for deterministic keyword matching."""
    lowered = text.casefold().replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )


def detect_intent(text: str) -> IntentLabel:
    """Classify one of the supported demo intents."""
    normalized = normalize_vietnamese(text)
    if _contains_any(normalized, _TICKET_KEYWORDS):
        return IntentLabel.TICKET_CREATE
    if _ORDER_ID_PATTERN.search(text):
        return IntentLabel.ORDER_LOOKUP
    if _contains_any(normalized, _POLICY_KEYWORDS):
        return IntentLabel.POLICY_QUESTION
    if _contains_any(normalized, _ORDER_KEYWORDS):
        return IntentLabel.ORDER_LOOKUP
    return IntentLabel.GENERAL


def detect_sentiment(text: str) -> SentimentLabel:
    """Return a coarse deterministic sentiment label."""
    normalized = normalize_vietnamese(text)
    if _contains_any(normalized, _NEGATIVE_KEYWORDS):
        return SentimentLabel.NEGATIVE
    if _contains_any(normalized, _POSITIVE_KEYWORDS):
        return SentimentLabel.POSITIVE
    return SentimentLabel.NEUTRAL


def answer_policy(text: str) -> tuple[str, list[Citation]]:
    """Return the best supported policy answer or insufficient context."""
    normalized = normalize_vietnamese(text)
    best_policy = None
    best_score = 0

    for policy in POLICIES:
        score = sum(
            _contains_keyword(normalized, normalize_vietnamese(keyword))
            for keyword in policy.keywords
        )
        if score > best_score:
            best_policy = policy
            best_score = score

    if best_policy is None:
        return INSUFFICIENT_POLICY_REPLY, []

    citation = Citation(
        source=best_policy.source,
        snippet=best_policy.snippet,
    )
    return best_policy.answer, [citation]


def extract_order_id(text: str) -> str | None:
    """Extract and canonicalize a supported demo order ID."""
    match = _ORDER_ID_PATTERN.search(text)
    if match is None:
        return None
    compact = re.sub(r"[\s-]", "", match.group(0).upper())
    return f"ASIA-{compact.removeprefix('ASIA')}"


def _owned_order(order_id: str) -> OrderRecord | None:
    for order in ORDERS:
        if (
            order.order_id == order_id
            and order.owner_customer_id == DEMO_CUSTOMER_ID
        ):
            return order
    return None


def answer_order(text: str) -> tuple[str, OrderSummary | None, bool]:
    """Safely answer an order lookup.

    The boolean indicates whether an actual lookup was performed.
    """
    order_id = extract_order_id(text)
    if order_id is None:
        return ORDER_ID_REQUIRED_REPLY, None, False

    order = _owned_order(order_id)
    if order is None:
        return ORDER_NOT_FOUND_REPLY, None, True

    summary = OrderSummary(
        order_id=order.order_id,
        status=order.status,
        carrier=order.carrier,
        estimated_delivery=order.estimated_delivery,
        items_count=order.items_count,
        last_updated=order.last_updated,
    )
    reply = (
        f"Đơn {summary.order_id} hiện ở trạng thái “{summary.status}”. "
        f"Dự kiến giao ngày {summary.estimated_delivery:%d/%m/%Y} qua "
        f"{summary.carrier}."
    )
    return reply, summary, True
