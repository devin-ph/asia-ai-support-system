"""Thread-safe in-memory state for the local demo."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from threading import RLock

from app.schemas import (
    ActionStatus,
    ActionType,
    AdminOverview,
    IntentLabel,
    PendingAction,
    SentimentLabel,
)


@dataclass
class _PendingActionRecord:
    action_id: str
    summary: str
    status: ActionStatus = ActionStatus.PENDING
    ticket_id: str | None = None


@dataclass(frozen=True)
class ActionResolution:
    """Result of confirming or cancelling an action."""

    status: ActionStatus
    ticket_id: str | None
    repeated: bool


class DemoState:
    """Own mutable demo state and keep confirmation idempotent."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._pending_actions: dict[str, _PendingActionRecord] = {}
        self._tickets: dict[str, str] = {}
        self._total_messages = 0
        self._intent_counts = {label.value: 0 for label in IntentLabel}
        self._sentiment_counts = {label.value: 0 for label in SentimentLabel}
        self._tool_counts = {
            "policy_search": 0,
            "order_lookup": 0,
            "ticket_create": 0,
        }

    def record_message(
        self,
        intent: IntentLabel,
        sentiment: SentimentLabel,
    ) -> None:
        with self._lock:
            self._total_messages += 1
            self._intent_counts[intent.value] += 1
            self._sentiment_counts[sentiment.value] += 1

    def record_tool(self, name: str) -> None:
        with self._lock:
            self._tool_counts[name] += 1

    def draft_ticket(self, summary: str) -> PendingAction:
        action_id = f"act_{uuid.uuid4().hex[:12]}"
        record = _PendingActionRecord(action_id=action_id, summary=summary)
        with self._lock:
            self._pending_actions[action_id] = record
        return PendingAction(
            action_id=action_id,
            action_type=ActionType.CREATE_TICKET,
            description="Tạo phiếu hỗ trợ cho yêu cầu này",
            payload={"summary": summary},
        )

    def resolve_action(
        self,
        action_id: str,
        *,
        confirm: bool,
    ) -> ActionResolution | None:
        with self._lock:
            record = self._pending_actions.get(action_id)
            if record is None:
                return None
            if record.status != ActionStatus.PENDING:
                return ActionResolution(
                    status=record.status,
                    ticket_id=record.ticket_id,
                    repeated=True,
                )

            if not confirm:
                record.status = ActionStatus.CANCELLED
                return ActionResolution(
                    status=record.status,
                    ticket_id=None,
                    repeated=False,
                )

            ticket_id = f"tkt_{uuid.uuid4().hex[:12]}"
            self._tickets[ticket_id] = record.summary
            record.status = ActionStatus.CONFIRMED
            record.ticket_id = ticket_id
            self._tool_counts["ticket_create"] += 1
            return ActionResolution(
                status=record.status,
                ticket_id=ticket_id,
                repeated=False,
            )

    def overview(self) -> AdminOverview:
        with self._lock:
            tool_counts = self._tool_counts.copy()
            return AdminOverview(
                total_messages=self._total_messages,
                total_tickets=len(self._tickets),
                intent_counts=self._intent_counts.copy(),
                sentiment_counts=self._sentiment_counts.copy(),
                tool_calls=sum(tool_counts.values()),
                tool_counts=tool_counts,
            )

