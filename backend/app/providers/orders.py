"""Provider boundary for safe order lookup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.order_service import OrderLookupResult, lookup_order
from app.storage import DEMO_ORDERS_PATH


class OrdersProvider(Protocol):
    """Look up an order while preserving ownership and field allowlists."""

    def lookup(self, text: str) -> OrderLookupResult:
        """Return only the customer-safe lookup result."""
        ...


@dataclass(frozen=True, slots=True)
class FixtureOrdersProvider:
    """Read orders from the immutable synthetic v0.1 fixture."""

    orders_path: Path = DEMO_ORDERS_PATH

    def lookup(self, text: str) -> OrderLookupResult:
        return lookup_order(text, orders_path=self.orders_path)
