"""Routing, tool events, counters, and drafts through `ReferenceSystem.handle`."""

from __future__ import annotations

import inspect
from datetime import UTC, date, datetime

import pytest
from app.intent import IntentAnalysis, IntentLabel, SentimentLabel
from app.order_service import ORDER_ACCESS_DENIED_MESSAGE, OrderLookupResult
from app.policy_search import INSUFFICIENT_CONTEXT_ANSWER, PolicySearchResult
from app.providers import ChatProviders
from app.reference_system import (
    GENERAL_REPLY,
    TICKET_DRAFT_REPLY,
    ReferenceSystem,
)
from app.schemas import (
    ActionType,
    Citation,
    OrderSummary,
    PendingAction,
    ToolEventStatus,
    ToolName,
)
from app.state import UsageCounters

CITATION = Citation(
    title="Chính sách giả lập",
    source="docs/policies/return_policy.md",
    section="Điều kiện và thời hạn đổi trả",
)
ORDER = OrderSummary(
    order_id="ASIA-1001",
    status="Đang giao",
    carrier="Đơn vị vận chuyển Demo",
    estimated_delivery=date(2026, 7, 10),
    items_count=1,
    last_updated=datetime(2026, 7, 5, 8, tzinfo=UTC),
)


class ScriptedAnalyzer:
    def __init__(self, intent: IntentLabel) -> None:
        self._intent = intent

    def analyze(self, _text: str) -> IntentAnalysis:
        return IntentAnalysis(intent=self._intent, sentiment=SentimentLabel.NEGATIVE)


class ScriptedPolicy:
    def __init__(self, result: PolicySearchResult) -> None:
        self._result = result
        self.request_ids: list[str] = []

    async def answer(self, _query: str, *, request_id: str) -> PolicySearchResult:
        self.request_ids.append(request_id)
        return self._result


class ScriptedOrders:
    def __init__(self, result: OrderLookupResult) -> None:
        self._result = result
        self.calls = 0

    def lookup(self, _text: str) -> OrderLookupResult:
        self.calls += 1
        return self._result


class RecordingDrafter:
    def __init__(self) -> None:
        self.summaries: list[str] = []

    def __call__(self, summary: str) -> PendingAction:
        self.summaries.append(summary)
        return PendingAction(
            action_id=f"act_test_{len(self.summaries)}",
            action_type=ActionType.CREATE_TICKET,
            description="Tạo phiếu hỗ trợ giả lập",
            payload={"summary": summary},
        )


GROUNDED = PolicySearchResult(answer="Có căn cứ.", citations=(CITATION,))
INSUFFICIENT = PolicySearchResult(answer=INSUFFICIENT_CONTEXT_ANSWER, citations=())
NO_POLICY_LOOKUP = PolicySearchResult(
    answer=INSUFFICIENT_CONTEXT_ANSWER,
    citations=(),
    lookup_performed=False,
)
OWNED = OrderLookupResult(answer="Đơn đang giao.", order=ORDER, lookup_performed=True)
NOT_FOUND = OrderLookupResult(
    answer=ORDER_ACCESS_DENIED_MESSAGE,
    order=None,
    lookup_performed=True,
)
NO_ORDER_LOOKUP = OrderLookupResult(answer="Cần mã đơn.", order=None, lookup_performed=False)


def build(
    intent: IntentLabel,
    *,
    policy: PolicySearchResult = GROUNDED,
    orders: OrderLookupResult = OWNED,
) -> tuple[ReferenceSystem, ScriptedPolicy, ScriptedOrders, RecordingDrafter, UsageCounters]:
    policy_provider = ScriptedPolicy(policy)
    orders_provider = ScriptedOrders(orders)
    drafter = RecordingDrafter()
    counters = UsageCounters()
    system = ReferenceSystem(
        ChatProviders(
            analyzer=ScriptedAnalyzer(intent),
            policy=policy_provider,
            orders=orders_provider,
        ),
        draft_ticket=drafter,
        counters=counters,
    )
    return system, policy_provider, orders_provider, drafter, counters


def tool_counts(counters: UsageCounters) -> dict[str, int]:
    return counters.overview(total_tickets=0).tool_counts


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_constructor_takes_no_resolve_or_write_capability() -> None:
    parameters = set(inspect.signature(ReferenceSystem.__init__).parameters)

    assert parameters == {"self", "providers", "draft_ticket", "counters"}


@pytest.mark.parametrize(
    "intent",
    [IntentLabel.SHIPPING_POLICY, IntentLabel.RETURN_REFUND, IntentLabel.WARRANTY],
)
@pytest.mark.anyio
async def test_policy_intents_route_to_grounded_policy(intent: IntentLabel) -> None:
    system, policy, orders, drafter, counters = build(intent)

    response = await system.handle("Câu hỏi chính sách")

    assert response.intent == intent
    assert response.sentiment == SentimentLabel.NEGATIVE
    assert response.assistant_message == "Có căn cứ."
    assert response.citations == [CITATION]
    assert [(e.tool, e.status) for e in response.tool_events] == [
        (ToolName.POLICY_SEARCH, ToolEventStatus.COMPLETED)
    ]
    assert response.pending_action is None
    assert len(policy.request_ids) == 1
    assert orders.calls == 0
    assert drafter.summaries == []
    assert tool_counts(counters)["policy_search"] == 1


@pytest.mark.anyio
async def test_each_policy_turn_gets_a_fresh_request_id() -> None:
    system, policy, *_ = build(IntentLabel.WARRANTY)

    await system.handle("Bảo hành thế nào?")
    await system.handle("Bảo hành thế nào?")

    assert len(set(policy.request_ids)) == 2


@pytest.mark.anyio
async def test_policy_without_evidence_reports_insufficient_context() -> None:
    system, *_, counters = build(IntentLabel.RETURN_REFUND, policy=INSUFFICIENT)

    response = await system.handle("Có giao nhanh không?")

    assert response.citations == []
    assert response.tool_events[0].status == ToolEventStatus.INSUFFICIENT_CONTEXT
    assert tool_counts(counters)["policy_search"] == 1


@pytest.mark.anyio
async def test_policy_without_lookup_emits_no_tool_event() -> None:
    system, *_, counters = build(IntentLabel.SHIPPING_POLICY, policy=NO_POLICY_LOOKUP)

    response = await system.handle("payload nội bộ")

    assert response.tool_events == []
    assert tool_counts(counters)["policy_search"] == 0


@pytest.mark.parametrize(
    ("result", "status", "order"),
    [
        (OWNED, ToolEventStatus.COMPLETED, ORDER),
        (NOT_FOUND, ToolEventStatus.NOT_FOUND, None),
    ],
    ids=["owned", "not-found"],
)
@pytest.mark.anyio
async def test_order_lookup_reports_safe_outcome(
    result: OrderLookupResult,
    status: ToolEventStatus,
    order: OrderSummary | None,
) -> None:
    system, policy, orders, _, counters = build(IntentLabel.ORDER_LOOKUP, orders=result)

    response = await system.handle("Tra cứu ASIA-1001")

    assert response.assistant_message == result.answer
    assert len(response.tool_events) == 1
    event = response.tool_events[0]
    assert (event.tool, event.status, event.order) == (ToolName.ORDER_LOOKUP, status, order)
    assert policy.request_ids == []
    assert orders.calls == 1
    assert tool_counts(counters)["order_lookup"] == 1


@pytest.mark.anyio
async def test_order_prompt_without_lookup_emits_no_tool_event() -> None:
    system, *_, counters = build(IntentLabel.ORDER_LOOKUP, orders=NO_ORDER_LOOKUP)

    response = await system.handle("Kiểm tra đơn giúp tôi")

    assert response.tool_events == []
    assert tool_counts(counters)["order_lookup"] == 0


@pytest.mark.anyio
async def test_ticket_request_only_drafts_a_pending_action() -> None:
    system, policy, orders, drafter, counters = build(IntentLabel.TICKET_REQUEST)

    response = await system.handle("Sản phẩm bị lỗi")

    assert response.assistant_message == TICKET_DRAFT_REPLY
    assert response.pending_action is not None
    assert response.pending_action.action_id == "act_test_1"
    assert response.tool_events == []
    assert drafter.summaries == ["Sản phẩm bị lỗi"]
    assert policy.request_ids == []
    assert orders.calls == 0
    assert tool_counts(counters)["ticket_create"] == 0


@pytest.mark.anyio
async def test_other_intent_returns_general_reply_without_tools() -> None:
    system, policy, orders, drafter, counters = build(IntentLabel.OTHER)

    response = await system.handle("Xin chào")

    assert response.assistant_message == GENERAL_REPLY
    assert response.citations == []
    assert response.tool_events == []
    assert response.pending_action is None
    assert (policy.request_ids, orders.calls, drafter.summaries) == ([], 0, [])
    assert sum(tool_counts(counters).values()) == 0


@pytest.mark.anyio
async def test_every_turn_records_its_labels() -> None:
    system, *_, counters = build(IntentLabel.ORDER_LOOKUP)

    await system.handle("Tra cứu ASIA-1001")
    await system.handle("Tra cứu ASIA-1001")
    overview = counters.overview(total_tickets=0)

    assert overview.total_messages == 2
    assert overview.intent_counts["order_lookup"] == 2
    assert overview.sentiment_counts["negative"] == 2
