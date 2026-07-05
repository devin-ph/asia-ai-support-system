"""Tests for fixed-customer synthetic order lookup."""

from __future__ import annotations

import pytest
from app.order_service import (
    ORDER_ACCESS_DENIED_MESSAGE,
    ORDER_REFERENCE_REQUIRED_MESSAGE,
    extract_order_reference,
    lookup_order,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Kiểm tra ASIA-1001 giúp tôi", "ASIA-1001"),
        ("Đơn asia 1002 đang ở đâu?", "ASIA-1002"),
        ("ASIA-10010 không đúng định dạng", None),
        ("Tôi chưa có mã đơn", None),
    ],
)
def test_extract_order_reference(text: str, expected: str | None) -> None:
    assert extract_order_reference(text) == expected


def test_lookup_owned_order_returns_only_safe_fields() -> None:
    result = lookup_order("Tra cứu ASIA-1001")
    assert result.lookup_performed is True
    assert result.order is not None
    assert set(result.order.model_dump()) == {
        "order_id",
        "status",
        "carrier",
        "estimated_delivery",
        "items_count",
        "last_updated",
    }
    assert result.order.order_id == "ASIA-1001"
    assert "owner" not in result.answer.casefold()


def test_unauthorized_and_unknown_orders_have_same_safe_denial() -> None:
    unauthorized = lookup_order("Tra cứu ASIA-9999")
    unknown = lookup_order("Tra cứu ASIA-8888")

    assert unauthorized == unknown
    assert unauthorized.answer == ORDER_ACCESS_DENIED_MESSAGE
    assert unauthorized.order is None
    assert "demo-customer-999" not in unauthorized.answer


def test_lookup_without_reference_does_not_access_an_order() -> None:
    result = lookup_order("Tôi muốn tra cứu đơn hàng")
    assert result.answer == ORDER_REFERENCE_REQUIRED_MESSAGE
    assert result.order is None
    assert result.lookup_performed is False
