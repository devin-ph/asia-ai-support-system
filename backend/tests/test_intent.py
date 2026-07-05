"""Tests for the deterministic Vietnamese analyzer."""

from __future__ import annotations

import pytest
from app.intent import (
    IntentLabel,
    SentimentLabel,
    analyze_message,
    detect_intent,
    detect_sentiment,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Tra cứu đơn hàng ASIA-1001", IntentLabel.ORDER_LOOKUP),
        ("Phi giao hang la bao nhieu?", IntentLabel.SHIPPING_POLICY),
        ("Tôi muốn đổi trả và hoàn tiền", IntentLabel.RETURN_REFUND),
        ("Sản phẩm này được bảo hành không?", IntentLabel.WARRANTY),
        ("Mở phiếu hỗ trợ giúp tôi", IntentLabel.TICKET_REQUEST),
        ("Xin chào, hôm nay bạn thế nào?", IntentLabel.OTHER),
    ],
)
def test_detect_intent(
    message: str,
    expected: IntentLabel,
) -> None:
    assert detect_intent(message) == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Cảm ơn, hỗ trợ rất tốt", SentimentLabel.POSITIVE),
        ("Tôi rất bực mình vì giao quá chậm", SentimentLabel.NEGATIVE),
        ("Tôi muốn hỏi thông tin đơn hàng", SentimentLabel.NEUTRAL),
    ],
)
def test_detect_sentiment(
    message: str,
    expected: SentimentLabel,
) -> None:
    assert detect_sentiment(message) == expected


def test_analyze_message_combines_both_results() -> None:
    result = analyze_message("Tôi thất vọng và muốn tạo phiếu hỗ trợ")
    assert result.intent == IntentLabel.TICKET_REQUEST
    assert result.sentiment == SentimentLabel.NEGATIVE
