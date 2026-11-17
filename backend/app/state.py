"""Thread-safe in-memory state for the local demo."""

from pathlib import Path
from threading import RLock

from app.intent import IntentLabel, SentimentLabel
from app.providers.tickets import (
    ActionResolution,
    LocalTicketProvider,
    TicketProvider,
)
from app.schemas import (
    ActionStatus,
    AdminOverview,
    PendingAction,
)
from app.storage import DEMO_TICKETS_PATH

TICKET_CREATE_TOOL = "ticket_create"


class UsageCounters:
    """Aggregate message, label, and tool counts without storing content."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._total_messages = 0
        self._intent_counts = {label.value: 0 for label in IntentLabel}
        self._sentiment_counts = {label.value: 0 for label in SentimentLabel}
        self._tool_counts = {
            "policy_search": 0,
            "order_lookup": 0,
            TICKET_CREATE_TOOL: 0,
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

    def overview(self, *, total_tickets: int) -> AdminOverview:
        with self._lock:
            tool_counts = self._tool_counts.copy()
            return AdminOverview(
                total_messages=self._total_messages,
                total_tickets=total_tickets,
                intent_counts=self._intent_counts.copy(),
                sentiment_counts=self._sentiment_counts.copy(),
                tool_calls=sum(tool_counts.values()),
                tool_counts=tool_counts,
            )


class DemoState:
    """Own usage counters and the ticket lifecycle; keep confirmation idempotent."""

    def __init__(
        self,
        tickets_path: Path = DEMO_TICKETS_PATH,
        *,
        ticket_provider: TicketProvider | None = None,
    ) -> None:
        self.counters = UsageCounters()
        self._ticket_provider = ticket_provider or LocalTicketProvider(tickets_path)

    def draft_ticket(self, summary: str) -> PendingAction:
        return self._ticket_provider.draft_ticket(summary)

    def resolve_action(
        self,
        action_id: str,
        *,
        confirm: bool,
    ) -> ActionResolution | None:
        resolution = self._ticket_provider.resolve_action(
            action_id,
            confirm=confirm,
        )
        if (
            resolution is not None
            and resolution.status == ActionStatus.CONFIRMED
            and not resolution.repeated
        ):
            self.counters.record_tool(TICKET_CREATE_TOOL)
        return resolution

    def overview(self) -> AdminOverview:
        return self.counters.overview(
            total_tickets=self._ticket_provider.ticket_count,
        )
