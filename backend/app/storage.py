"""Validated JSON storage for synthetic demo orders and tickets."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "data" / "fixtures"
RUNTIME_DIR = PROJECT_ROOT / "var"
DEMO_ORDERS_PATH = FIXTURES_DIR / "demo_orders.json"
DEMO_TICKETS_SEED_PATH = FIXTURES_DIR / "demo_tickets.seed.json"
DEMO_TICKETS_PATH = RUNTIME_DIR / "demo_tickets.json"


class OrderRecord(BaseModel):
    """Internal synthetic order record, including ownership."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    owner_customer_id: str
    status: str
    carrier: str
    estimated_delivery: date
    items_count: int = Field(ge=1)
    last_updated: datetime


class TicketRecord(BaseModel):
    """One confirmed synthetic support ticket."""

    model_config = ConfigDict(frozen=True)

    ticket_id: str
    action_id: str
    summary: str
    created_at: datetime


_ORDER_ADAPTER = TypeAdapter(list[OrderRecord])
_TICKET_ADAPTER = TypeAdapter(list[TicketRecord])


def load_orders(path: Path = DEMO_ORDERS_PATH) -> tuple[OrderRecord, ...]:
    """Load and validate the synthetic order fixture."""
    records = _ORDER_ADAPTER.validate_json(path.read_text(encoding="utf-8"))
    return tuple(records)


def load_tickets(path: Path = DEMO_TICKETS_PATH) -> tuple[TicketRecord, ...]:
    """Load confirmed synthetic tickets, returning empty for a new store."""
    if not path.exists():
        return ()
    records = _TICKET_ADAPTER.validate_json(path.read_text(encoding="utf-8"))
    return tuple(records)


def save_tickets(
    tickets: Iterable[TicketRecord],
    path: Path = DEMO_TICKETS_PATH,
) -> None:
    """Validate and atomically save confirmed synthetic tickets."""
    records = tuple(tickets)
    _TICKET_ADAPTER.validate_python(records)
    payload = [ticket.model_dump(mode="json") for ticket in records]

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        temporary_path.write_text(
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

