"""Public Pydantic schemas for the A.S.I.A API."""

from __future__ import annotations

import enum
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.intent import IntentLabel, SentimentLabel


class ActionStatus(str, enum.Enum):
    """Lifecycle states for a proposed action."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class ActionType(str, enum.Enum):
    """Write actions supported by this milestone."""

    CREATE_TICKET = "create_ticket"


class HealthResponse(BaseModel):
    """Response for `GET /api/health`."""

    status: str = Field(default="ok", examples=["ok"])
    version: str = Field(default="0.1", examples=["0.1"])


class Citation(BaseModel):
    """Reference to one trusted Markdown policy section."""

    title: str = Field(..., examples=["Chính sách đổi trả và hoàn tiền"])
    source: str = Field(..., examples=["docs/policies/return_policy.md"])
    section: str = Field(..., examples=["Điều kiện và thời hạn đổi trả"])


class OrderSummary(BaseModel):
    """Safe, customer-facing order fields."""

    order_id: str = Field(..., examples=["ASIA-1001"])
    status: str = Field(..., examples=["Đang giao"])
    carrier: str = Field(..., examples=["Đơn vị vận chuyển Demo"])
    estimated_delivery: date
    items_count: int = Field(ge=1)
    last_updated: datetime


class PendingAction(BaseModel):
    """An action proposal that requires explicit confirmation."""

    action_id: str = Field(..., examples=["act_abc123"])
    action_type: ActionType
    description: str
    payload: dict[str, str] = Field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING


class ChatRequest(BaseModel):
    """Request body for `POST /api/chat`."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        examples=["Chính sách đổi trả áp dụng trong bao lâu?"],
    )
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        examples=["sess_xyz789"],
    )


class ChatResponse(BaseModel):
    """Stable response envelope for `POST /api/chat`."""

    reply: str
    intent: IntentLabel
    sentiment: SentimentLabel
    citations: list[Citation] = Field(default_factory=list)
    order: OrderSummary | None = None
    actions: list[PendingAction] = Field(default_factory=list)
    session_id: str


class ActionConfirmRequest(BaseModel):
    """Request body for the action confirmation endpoint."""

    confirm: bool = Field(
        ...,
        description="True to execute the action; False to cancel it.",
    )


class ActionConfirmResponse(BaseModel):
    """Result of confirming or cancelling one action."""

    action_id: str
    status: ActionStatus
    message: str
    ticket_id: str | None = None


class AdminOverview(BaseModel):
    """Aggregate, non-PII counters for the admin dashboard."""

    total_messages: int = Field(default=0, ge=0)
    total_tickets: int = Field(default=0, ge=0)
    intent_counts: dict[str, int] = Field(default_factory=dict)
    sentiment_counts: dict[str, int] = Field(default_factory=dict)
    tool_calls: int = Field(default=0, ge=0)
    tool_counts: dict[str, int] = Field(default_factory=dict)
