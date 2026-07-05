"""Provider boundaries for ticket drafting and confirmed writes."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.schemas import PendingAction
from app.storage import DEMO_TICKETS_PATH
from app.ticket_service import ActionResolution, TicketService


class TicketDraftProvider(Protocol):
    """Create a reviewable proposal without executing a write."""

    def draft_ticket(self, summary: str) -> PendingAction:
        """Return a pending action and create no ticket."""
        ...


class TicketWriteProvider(Protocol):
    """Execute or cancel a previously drafted action."""

    @property
    def ticket_count(self) -> int:
        """Return the number of confirmed tickets."""
        ...

    def resolve_action(
        self,
        action_id: str,
        *,
        confirm: bool,
    ) -> ActionResolution | None:
        """Resolve one action idempotently after explicit confirmation."""
        ...


class TicketProvider(TicketDraftProvider, TicketWriteProvider, Protocol):
    """Complete ticket lifecycle required by application state."""


class LocalTicketProvider:
    """Adapt the guarded local ticket service to the provider contracts."""

    def __init__(self, tickets_path: Path = DEMO_TICKETS_PATH) -> None:
        self._service = TicketService(tickets_path)

    @property
    def ticket_count(self) -> int:
        return self._service.ticket_count

    def draft_ticket(self, summary: str) -> PendingAction:
        return self._service.draft_ticket(summary)

    def resolve_action(
        self,
        action_id: str,
        *,
        confirm: bool,
    ) -> ActionResolution | None:
        return self._service.resolve_action(action_id, confirm=confirm)
