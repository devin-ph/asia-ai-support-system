"""Thread-safe in-memory state for the local demo."""

from pathlib import Path
from threading import RLock

from app.intent import IntentLabel, SentimentLabel
from app.schemas import (
    ActionStatus,
    AdminOverview,
    PendingAction,
)
from app.storage import DEMO_TICKETS_PATH
from app.ticket_service import ActionResolution, TicketService


class DemoState:
    """Own mutable demo state and keep confirmation idempotent."""

    def __init__(self, tickets_path: Path = DEMO_TICKETS_PATH) -> None:
        self._lock = RLock()
        self._ticket_service = TicketService(tickets_path)
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
        return self._ticket_service.draft_ticket(summary)

    def resolve_action(
        self,
        action_id: str,
        *,
        confirm: bool,
    ) -> ActionResolution | None:
        resolution = self._ticket_service.resolve_action(
            action_id,
            confirm=confirm,
        )
        if (
            resolution is not None
            and resolution.status == ActionStatus.CONFIRMED
            and not resolution.repeated
        ):
            self.record_tool("ticket_create")
        return resolution

    def overview(self) -> AdminOverview:
        with self._lock:
            tool_counts = self._tool_counts.copy()
            return AdminOverview(
                total_messages=self._total_messages,
                total_tickets=self._ticket_service.ticket_count,
                intent_counts=self._intent_counts.copy(),
                sentiment_counts=self._sentiment_counts.copy(),
                tool_calls=sum(tool_counts.values()),
                tool_counts=tool_counts,
            )
