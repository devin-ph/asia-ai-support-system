"""Shared contracts for deterministic and replaceable demo providers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest

from app.intent import (
    IntentAnalysis,
    IntentLabel,
    SentimentLabel,
)
from app.order_service import (
    ORDER_ACCESS_DENIED_MESSAGE,
    OrderLookupResult,
)
from app.policy_search import (
    INSUFFICIENT_CONTEXT_ANSWER,
    PolicySearchResult,
)
from app.providers import (
    ChatProviders,
    DeterministicAnalyzerProvider,
    FixtureOrdersProvider,
    KeywordPolicyProvider,
    default_chat_providers,
)
from app.providers.analyzer import AnalyzerProvider
from app.providers.orders import OrdersProvider
from app.providers.policy import PolicyProvider
from app.providers.tickets import (
    LocalTicketProvider,
    TicketProvider,
)
from app.schemas import (
    ActionStatus,
    ActionType,
    Citation,
    OrderSummary,
    PendingAction,
)
from app.state import DemoState
from app.storage import load_tickets
from app.ticket_service import ActionResolution
from app.main import create_app


class FakeAnalyzerProvider:
    """Small test double with the same typed analyzer result."""

    def __init__(self, intent: IntentLabel = IntentLabel.RETURN_REFUND) -> None:
        self._intent = intent

    def analyze(self, _text: str) -> IntentAnalysis:
        return IntentAnalysis(
            intent=self._intent,
            sentiment=SentimentLabel.NEUTRAL,
        )


class FakePolicyProvider:
    """Return one synthetic grounded policy result."""

    def search(self, query: str) -> PolicySearchResult:
        if "nấu ăn" in query:
            return PolicySearchResult(
                answer=INSUFFICIENT_CONTEXT_ANSWER,
                citations=(),
            )
        return PolicySearchResult(
            answer="Nội dung chính sách giả lập có căn cứ.",
            citations=(
                Citation(
                    title="Chính sách giả lập",
                    source="docs/policies/return_policy.md",
                    section="Điều kiện và thời hạn đổi trả",
                ),
            ),
        )


class FakeOrdersProvider:
    """Return safe fields only, like a future commerce adapter must."""

    def lookup(self, text: str) -> OrderLookupResult:
        if "ASIA-1001" not in text:
            return OrderLookupResult(
                answer=ORDER_ACCESS_DENIED_MESSAGE,
                order=None,
                lookup_performed=True,
            )
        return OrderLookupResult(
            answer="Đơn ASIA-1001 đang được giao.",
            order=OrderSummary(
                order_id="ASIA-1001",
                status="Đang giao",
                carrier="Đơn vị vận chuyển Demo",
                estimated_delivery=date(2026, 7, 10),
                items_count=1,
                last_updated=datetime(
                    2026,
                    7,
                    5,
                    8,
                    tzinfo=timezone.utc,
                ),
            ),
            lookup_performed=True,
        )


class FakeTicketProvider:
    """In-memory test double preserving the confirmation guardrail."""

    def __init__(self) -> None:
        self._next_action = 1
        self._actions: dict[str, ActionResolution] = {}
        self._ticket_count = 0
        self.draft_calls = 0
        self.resolve_calls = 0

    @property
    def ticket_count(self) -> int:
        return self._ticket_count

    def draft_ticket(self, summary: str) -> PendingAction:
        self.draft_calls += 1
        action_id = f"act_fake_{self._next_action}"
        self._next_action += 1
        self._actions[action_id] = ActionResolution(
            status=ActionStatus.PENDING,
            ticket_id=None,
            repeated=False,
        )
        return PendingAction(
            action_id=action_id,
            action_type=ActionType.CREATE_TICKET,
            description="Tạo phiếu hỗ trợ giả lập",
            payload={"summary": summary},
        )

    def resolve_action(
        self,
        action_id: str,
        *,
        confirm: bool,
    ) -> ActionResolution | None:
        self.resolve_calls += 1
        current = self._actions.get(action_id)
        if current is None:
            return None
        if current.status != ActionStatus.PENDING:
            return ActionResolution(
                status=current.status,
                ticket_id=current.ticket_id,
                repeated=True,
            )
        if not confirm:
            resolved = ActionResolution(
                status=ActionStatus.CANCELLED,
                ticket_id=None,
                repeated=False,
            )
        else:
            self._ticket_count += 1
            resolved = ActionResolution(
                status=ActionStatus.CONFIRMED,
                ticket_id=f"tkt_fake_{self._ticket_count}",
                repeated=False,
            )
        self._actions[action_id] = resolved
        return resolved


def fake_chat_providers() -> ChatProviders:
    return ChatProviders(
        analyzer=FakeAnalyzerProvider(),
        policy=FakePolicyProvider(),
        orders=FakeOrdersProvider(),
    )


def test_chat_provider_bundle_excludes_ticket_capabilities() -> None:
    assert {field.name for field in fields(ChatProviders)} == {
        "analyzer",
        "policy",
        "orders",
    }


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def tickets_path(tmp_path: Path) -> Path:
    path = tmp_path / "demo_tickets.json"
    path.write_text("[]\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "provider",
    [DeterministicAnalyzerProvider(), FakeAnalyzerProvider()],
    ids=["deterministic", "fake"],
)
def test_analyzer_provider_contract(provider: AnalyzerProvider) -> None:
    result = provider.analyze("Tôi muốn đổi trả sản phẩm")

    assert isinstance(result, IntentAnalysis)
    assert isinstance(result.intent, IntentLabel)
    assert isinstance(result.sentiment, SentimentLabel)


@pytest.mark.parametrize(
    "provider",
    [KeywordPolicyProvider(), FakePolicyProvider()],
    ids=["deterministic", "fake"],
)
def test_policy_provider_contract(provider: PolicyProvider) -> None:
    grounded = provider.search("Tôi muốn đổi trả sản phẩm")
    insufficient = provider.search("Shop có hướng dẫn nấu ăn không?")

    assert isinstance(grounded, PolicySearchResult)
    assert grounded.answer
    assert grounded.citations
    assert all(
        citation.source.startswith("docs/policies/")
        for citation in grounded.citations
    )
    assert all(citation.section for citation in grounded.citations)
    assert insufficient.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert insufficient.citations == ()


@pytest.mark.parametrize(
    "provider",
    [FixtureOrdersProvider(), FakeOrdersProvider()],
    ids=["deterministic", "fake"],
)
def test_orders_provider_contract(provider: OrdersProvider) -> None:
    owned = provider.lookup("Tra cứu ASIA-1001")
    denied = provider.lookup("Tra cứu ASIA-8888")
    non_owned = provider.lookup("Tra cứu ASIA-9999")

    assert owned.lookup_performed is True
    assert owned.order is not None
    assert set(owned.order.model_dump()) == {
        "order_id",
        "status",
        "carrier",
        "estimated_delivery",
        "items_count",
        "last_updated",
    }
    assert denied.lookup_performed is True
    assert denied.order is None
    assert denied.answer == ORDER_ACCESS_DENIED_MESSAGE
    assert non_owned.order is None
    assert non_owned.answer == denied.answer


def _local_ticket_provider(path: Path) -> TicketProvider:
    return LocalTicketProvider(path)


def _fake_ticket_provider(_path: Path) -> TicketProvider:
    return FakeTicketProvider()


@pytest.mark.parametrize(
    "provider_factory",
    [_local_ticket_provider, _fake_ticket_provider],
    ids=["local", "fake"],
)
def test_ticket_provider_confirmation_contract(
    provider_factory: Callable[[Path], TicketProvider],
    tickets_path: Path,
) -> None:
    provider = provider_factory(tickets_path)
    action = provider.draft_ticket("Yêu cầu hỗ trợ tổng hợp")

    assert action.status == ActionStatus.PENDING
    assert provider.ticket_count == 0

    first = provider.resolve_action(action.action_id, confirm=True)
    repeated = provider.resolve_action(action.action_id, confirm=True)

    assert first is not None
    assert repeated is not None
    assert first.status == ActionStatus.CONFIRMED
    assert first.ticket_id is not None
    assert repeated.status == ActionStatus.CONFIRMED
    assert repeated.ticket_id == first.ticket_id
    assert repeated.repeated is True
    assert provider.ticket_count == 1

    cancelled_action = provider.draft_ticket("Yêu cầu sẽ hủy")
    cancelled = provider.resolve_action(
        cancelled_action.action_id,
        confirm=False,
    )
    confirm_after_cancel = provider.resolve_action(
        cancelled_action.action_id,
        confirm=True,
    )

    assert cancelled is not None
    assert confirm_after_cancel is not None
    assert cancelled.status == ActionStatus.CANCELLED
    assert confirm_after_cancel.status == ActionStatus.CANCELLED
    assert confirm_after_cancel.ticket_id is None
    assert provider.ticket_count == 1


@pytest.mark.parametrize(
    "providers_factory",
    [default_chat_providers, fake_chat_providers],
    ids=["deterministic", "fake"],
)
@pytest.mark.anyio
async def test_provider_swap_preserves_chat_route_contract(
    providers_factory: Callable[[], ChatProviders],
    tickets_path: Path,
) -> None:
    application = create_app(
        DemoState(tickets_path=tickets_path),
        chat_providers=providers_factory(),
    )
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/chat",
            json={"message": "Tôi muốn đổi trả sản phẩm"},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "assistant_message",
        "intent",
        "sentiment",
        "citations",
        "tool_events",
        "pending_action",
    }
    assert body["intent"] == "return_refund"
    assert body["citations"]
    assert body["tool_events"][0]["tool"] == "policy_search"


@pytest.mark.anyio
async def test_chat_route_cannot_execute_ticket_write(
    tickets_path: Path,
) -> None:
    tickets = FakeTicketProvider()
    application = create_app(
        DemoState(ticket_provider=tickets),
        chat_providers=ChatProviders(
            analyzer=FakeAnalyzerProvider(IntentLabel.TICKET_REQUEST),
            policy=FakePolicyProvider(),
            orders=FakeOrdersProvider(),
        ),
    )
    transport = httpx.ASGITransport(app=application)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        draft = await client.post(
            "/api/chat",
            json={"message": "Tạo phiếu hỗ trợ"},
        )

        action = draft.json()["pending_action"]
        assert action is not None
        assert tickets.draft_calls == 1
        assert tickets.resolve_calls == 0
        assert tickets.ticket_count == 0

        confirmed = await client.post(
            f"/api/actions/{action['action_id']}/confirm",
            json={"confirm": True},
        )

    assert confirmed.status_code == 200
    assert tickets.resolve_calls == 1
    assert tickets.ticket_count == 1
    assert load_tickets(tickets_path) == ()
