"""Safe synthetic order lookup for the fixed demo customer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.schemas import OrderSummary
from app.storage import DEMO_ORDERS_PATH, load_orders

FIXED_DEMO_CUSTOMER_ID = "demo-customer-001"

ORDER_REFERENCE_REQUIRED_MESSAGE = (
    "Bạn vui lòng cung cấp mã đơn hàng theo định dạng ASIA-1001 để mình tra cứu."
)
ORDER_ACCESS_DENIED_MESSAGE = "Không tìm thấy đơn hàng thuộc tài khoản demo với mã đã cung cấp."

_ORDER_REFERENCE_PATTERN = re.compile(
    r"(?<![A-Z0-9])ASIA[-\s]?\d{4}(?![A-Z0-9])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OrderLookupResult:
    """Customer-safe result without ownership metadata."""

    answer: str
    order: OrderSummary | None
    lookup_performed: bool


def extract_order_reference(text: str) -> str | None:
    """Extract and canonicalize the first ASIA order reference."""
    match = _ORDER_REFERENCE_PATTERN.search(text)
    if match is None:
        return None
    compact = re.sub(r"[\s-]", "", match.group(0).upper())
    return f"ASIA-{compact.removeprefix('ASIA')}"


def lookup_order(
    text: str,
    *,
    orders_path: Path = DEMO_ORDERS_PATH,
) -> OrderLookupResult:
    """Look up an order owned by the fixed demo customer.

    Unknown and unauthorized references deliberately produce the same result.
    """
    order_reference = extract_order_reference(text)
    if order_reference is None:
        return OrderLookupResult(
            answer=ORDER_REFERENCE_REQUIRED_MESSAGE,
            order=None,
            lookup_performed=False,
        )

    matched_order = next(
        (
            order
            for order in load_orders(orders_path)
            if order.order_id == order_reference
            and order.owner_customer_id == FIXED_DEMO_CUSTOMER_ID
        ),
        None,
    )
    if matched_order is None:
        return OrderLookupResult(
            answer=ORDER_ACCESS_DENIED_MESSAGE,
            order=None,
            lookup_performed=True,
        )

    safe_order = OrderSummary(
        order_id=matched_order.order_id,
        status=matched_order.status,
        carrier=matched_order.carrier,
        estimated_delivery=matched_order.estimated_delivery,
        items_count=matched_order.items_count,
        last_updated=matched_order.last_updated,
    )
    answer = (
        f"Đơn {safe_order.order_id} hiện ở trạng thái “{safe_order.status}”. "
        f"Dự kiến giao ngày {safe_order.estimated_delivery:%d/%m/%Y} qua "
        f"{safe_order.carrier}."
    )
    return OrderLookupResult(
        answer=answer,
        order=safe_order,
        lookup_performed=True,
    )
