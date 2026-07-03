"""Load and validate repository-owned synthetic demo fixtures."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEMO_CUSTOMER_ID = "CUS-DEMO-001"
RecordT = TypeVar("RecordT", bound=BaseModel)


class PolicyRecord(BaseModel):
    """One grounded policy answer and its supporting evidence."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    keywords: tuple[str, ...] = Field(min_length=1)
    answer: str
    snippet: str
    source: str


class OrderRecord(BaseModel):
    """Internal synthetic order record, including the ownership field."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    owner_customer_id: str
    status: str
    carrier: str
    estimated_delivery: date
    items_count: int = Field(ge=1)
    last_updated: datetime


def _load_records(
    filename: str,
    model: type[RecordT],
) -> tuple[RecordT, ...]:
    path = DATA_DIR / filename
    adapter = TypeAdapter(list[model])  # type: ignore[valid-type]
    records = adapter.validate_json(path.read_text(encoding="utf-8"))
    return tuple(records)


POLICIES = _load_records("policies.json", PolicyRecord)
ORDERS = _load_records("orders.json", OrderRecord)
