"""Draft-and-confirm lifecycle for synthetic support tickets."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from app.schemas import ActionStatus, ActionType, PendingAction
from app.storage import (
    DEMO_TICKETS_PATH,
    DEMO_TICKETS_SEED_PATH,
    TicketRecord,
    load_tickets,
    save_tickets,
)


@dataclass
class _PendingActionRecord:
    action_id: str
    summary: str
    status: ActionStatus = ActionStatus.PENDING
    ticket_id: str | None = None


@dataclass(frozen=True)
class ActionResolution:
    """Result of confirming or declining one pending action."""

    status: ActionStatus
    ticket_id: str | None
    repeated: bool


class TicketService:
    """Keep pending actions in memory and persist confirmed tickets."""

    def __init__(self, tickets_path: Path = DEMO_TICKETS_PATH) -> None:
        self._lock = RLock()
        self._tickets_path = tickets_path
        self._pending_actions: dict[str, _PendingActionRecord] = {}
        initial_store = (
            tickets_path
            if tickets_path.exists()
            else DEMO_TICKETS_SEED_PATH
        )
        self._tickets = {
            ticket.ticket_id: ticket for ticket in load_tickets(initial_store)
        }

    @property
    def ticket_count(self) -> int:
        with self._lock:
            return len(self._tickets)

    def draft_ticket(self, summary: str) -> PendingAction:
        """Create a pending action without creating a ticket."""
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
        """Confirm or decline a pending action idempotently."""
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

            ticket = TicketRecord(
                ticket_id=f"tkt_{uuid.uuid4().hex[:12]}",
                action_id=action_id,
                summary=record.summary,
                created_at=datetime.now(timezone.utc),
            )
            save_tickets(
                (*self._tickets.values(), ticket),
                self._tickets_path,
            )
            self._tickets[ticket.ticket_id] = ticket
            record.status = ActionStatus.CONFIRMED
            record.ticket_id = ticket.ticket_id
            return ActionResolution(
                status=record.status,
                ticket_id=ticket.ticket_id,
                repeated=False,
            )
