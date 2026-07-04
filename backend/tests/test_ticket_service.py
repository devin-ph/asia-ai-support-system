"""Tests for ticket drafting and explicit confirmation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.schemas import ActionStatus
from app.storage import load_tickets
from app.ticket_service import TicketService


def _empty_ticket_path(tmp_path: Path) -> Path:
    path = tmp_path / "demo_tickets.json"
    path.write_text("[]\n", encoding="utf-8")
    return path


def test_draft_creates_pending_action_without_ticket(tmp_path: Path) -> None:
    tickets_path = _empty_ticket_path(tmp_path)
    service = TicketService(tickets_path)

    action = service.draft_ticket("Yêu cầu hỗ trợ demo")

    assert action.status == ActionStatus.PENDING
    assert action.action_type.value == "create_ticket"
    assert service.ticket_count == 0
    assert load_tickets(tickets_path) == ()


def test_confirmation_creates_exactly_one_ticket(tmp_path: Path) -> None:
    tickets_path = _empty_ticket_path(tmp_path)
    service = TicketService(tickets_path)
    action = service.draft_ticket("Yêu cầu hỗ trợ demo")

    first = service.resolve_action(action.action_id, confirm=True)
    repeated = service.resolve_action(action.action_id, confirm=True)

    assert first is not None
    assert repeated is not None
    assert first.status == ActionStatus.CONFIRMED
    assert first.ticket_id is not None
    assert repeated.status == ActionStatus.CONFIRMED
    assert repeated.ticket_id == first.ticket_id
    assert repeated.repeated is True

    tickets = load_tickets(tickets_path)
    assert len(tickets) == 1
    assert tickets[0].ticket_id == first.ticket_id
    assert TicketService(tickets_path).ticket_count == 1


def test_decline_never_creates_a_ticket(tmp_path: Path) -> None:
    tickets_path = _empty_ticket_path(tmp_path)
    service = TicketService(tickets_path)
    action = service.draft_ticket("Yêu cầu hỗ trợ demo")

    declined = service.resolve_action(action.action_id, confirm=False)
    confirm_after_decline = service.resolve_action(
        action.action_id,
        confirm=True,
    )

    assert declined is not None
    assert confirm_after_decline is not None
    assert declined.status == ActionStatus.CANCELLED
    assert confirm_after_decline.status == ActionStatus.CANCELLED
    assert confirm_after_decline.ticket_id is None
    assert service.ticket_count == 0
    assert load_tickets(tickets_path) == ()


def test_unknown_action_does_not_create_ticket(tmp_path: Path) -> None:
    tickets_path = _empty_ticket_path(tmp_path)
    service = TicketService(tickets_path)
    assert service.resolve_action("act_missing", confirm=True) is None
    assert load_tickets(tickets_path) == ()


def test_concurrent_confirmations_create_one_ticket(tmp_path: Path) -> None:
    tickets_path = _empty_ticket_path(tmp_path)
    service = TicketService(tickets_path)
    action = service.draft_ticket("Yêu cầu hỗ trợ demo")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(
            executor.map(
                lambda _index: service.resolve_action(
                    action.action_id,
                    confirm=True,
                ),
                range(2),
            )
        )

    ticket_ids = {
        result.ticket_id for result in results if result is not None
    }
    assert len(ticket_ids) == 1
    assert len(load_tickets(tickets_path)) == 1
