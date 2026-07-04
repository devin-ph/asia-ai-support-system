"""API contract and safety tests for the v0.1 vertical slice."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from app.main import create_app
from app.state import DemoState
from app.storage import load_orders, load_tickets


def assert_stable_chat_shape(body: dict[str, object]) -> None:
    assert set(body) == {
        "assistant_message",
        "intent",
        "sentiment",
        "citations",
        "tool_events",
        "pending_action",
    }


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def tickets_path(tmp_path: Path) -> Path:
    path = tmp_path / "demo_tickets.json"
    path.write_text("[]\n", encoding="utf-8")
    return path


@pytest.fixture
def app(tickets_path: Path) -> FastAPI:
    return create_app(DemoState(tickets_path=tickets_path))


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client


@pytest.mark.anyio
async def test_health_and_blank_message_validation(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1",
    }

    blank = await client.post("/api/chat", json={"message": "   "})
    assert blank.status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize(
    "message",
    [
        "Chính sách đổi trả áp dụng trong bao lâu?",
        "Chinh sach doi tra ap dung trong bao lau?",
    ],
)
async def test_policy_answer_is_grounded_for_vietnamese_text(
    client: httpx.AsyncClient,
    message: str,
) -> None:
    response = await client.post(
        "/api/chat",
        json={"message": message},
    )

    assert response.status_code == 200
    body = response.json()
    assert_stable_chat_shape(body)
    assert body["intent"] == "return_refund"
    assert "7 ngày" in body["assistant_message"]
    assert body["citations"] == [
        {
            "title": "Chính sách đổi trả và hoàn tiền",
            "source": "docs/policies/return_policy.md",
            "section": "Điều kiện và thời hạn đổi trả",
        }
    ]
    assert body["tool_events"] == [
        {
            "tool": "policy_search",
            "status": "completed",
            "order": None,
        }
    ]
    assert body["pending_action"] is None


@pytest.mark.anyio
async def test_policy_without_evidence_returns_insufficient_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/chat",
        json={"message": "Có chính sách giao nhanh không?"},
    )

    body = response.json()
    assert body["intent"] == "shipping_policy"
    assert "chưa có đủ thông tin" in body["assistant_message"]
    assert body["citations"] == []
    assert body["tool_events"] == [
        {
            "tool": "policy_search",
            "status": "insufficient_context",
            "order": None,
        }
    ]


@pytest.mark.anyio
async def test_owned_order_returns_only_safe_fields(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/chat",
        json={"message": "Tra cứu đơn hàng ASIA-1001 giúp tôi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert_stable_chat_shape(body)
    assert body["intent"] == "order_lookup"
    assert len(body["tool_events"]) == 1
    event = body["tool_events"][0]
    assert event["tool"] == "order_lookup"
    assert event["status"] == "completed"
    assert set(event["order"]) == {
        "order_id",
        "status",
        "carrier",
        "estimated_delivery",
        "items_count",
        "last_updated",
    }
    assert event["order"]["order_id"] == "ASIA-1001"
    assert body["pending_action"] is None
    assert "owner_customer_id" not in response.text


@pytest.mark.anyio
async def test_non_owned_and_unknown_orders_are_indistinguishable(
    client: httpx.AsyncClient,
) -> None:
    non_owned = await client.post(
        "/api/chat",
        json={"message": "Tra cứu ASIA-9999"},
    )
    unknown = await client.post(
        "/api/chat",
        json={"message": "Tra cứu ASIA-8888"},
    )

    assert non_owned.status_code == 200
    assert unknown.status_code == 200
    assert non_owned.json()["tool_events"] == unknown.json()["tool_events"]
    assert non_owned.json()["tool_events"] == [
        {
            "tool": "order_lookup",
            "status": "not_found",
            "order": None,
        }
    ]
    assert (
        non_owned.json()["assistant_message"]
        == unknown.json()["assistant_message"]
    )
    assert "demo-customer-999" not in non_owned.text


@pytest.mark.anyio
async def test_order_prompt_without_id_does_not_call_lookup_tool(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/chat",
        json={"message": "Tôi muốn tra cứu đơn hàng"},
    )
    overview = await client.get("/api/admin/overview")

    assert response.json()["tool_events"] == []
    assert "cung cấp mã đơn hàng" in response.json()["assistant_message"]
    assert response.json()["pending_action"] is None
    assert overview.json()["tool_counts"]["order_lookup"] == 0


@pytest.mark.anyio
async def test_ticket_requires_confirmation_and_is_idempotent(
    client: httpx.AsyncClient,
    tickets_path: Path,
) -> None:
    draft = await client.post(
        "/api/chat",
        json={"message": "Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi"},
    )
    assert_stable_chat_shape(draft.json())
    assert draft.json()["tool_events"] == []
    action = draft.json()["pending_action"]
    assert action is not None
    before = await client.get("/api/admin/overview")
    assert before.json()["total_tickets"] == 0

    first = await client.post(
        f"/api/actions/{action['action_id']}/confirm",
        json={"confirm": True},
    )
    repeated = await client.post(
        f"/api/actions/{action['action_id']}/confirm",
        json={"confirm": True},
    )

    assert first.json()["status"] == "confirmed"
    assert first.json()["ticket_id"] is not None
    assert repeated.json()["ticket_id"] == first.json()["ticket_id"]

    after = await client.get("/api/admin/overview")
    assert after.json()["total_tickets"] == 1
    assert after.json()["tool_counts"]["ticket_create"] == 1

    persisted = load_tickets(tickets_path)
    assert len(persisted) == 1
    assert persisted[0].ticket_id == first.json()["ticket_id"]
    assert DemoState(tickets_path=tickets_path).overview().total_tickets == 1


@pytest.mark.anyio
async def test_cancelled_ticket_cannot_be_confirmed_later(
    client: httpx.AsyncClient,
) -> None:
    draft = await client.post(
        "/api/chat",
        json={"message": "Mở phiếu khiếu nại giúp tôi"},
    )
    action = draft.json()["pending_action"]
    assert action is not None
    action_id = action["action_id"]

    cancelled = await client.post(
        f"/api/actions/{action_id}/confirm",
        json={"confirm": False},
    )
    confirm_after_cancel = await client.post(
        f"/api/actions/{action_id}/confirm",
        json={"confirm": True},
    )

    assert cancelled.json()["status"] == "cancelled"
    assert confirm_after_cancel.json()["status"] == "cancelled"
    assert confirm_after_cancel.json()["ticket_id"] is None
    overview = await client.get("/api/admin/overview")
    assert overview.json()["total_tickets"] == 0


@pytest.mark.anyio
async def test_admin_counts_intents_sentiment_and_tools(
    client: httpx.AsyncClient,
) -> None:
    await client.post(
        "/api/chat",
        json={"message": "Cảm ơn, chính sách hoàn tiền thế nào?"},
    )
    await client.post(
        "/api/chat",
        json={"message": "Tôi rất bực mình, tra cứu ASIA-1002"},
    )

    response = await client.get("/api/admin/overview")
    body = response.json()
    assert body["total_messages"] == 2
    assert body["intent_counts"]["return_refund"] == 1
    assert body["intent_counts"]["order_lookup"] == 1
    assert set(body["intent_counts"]) == {
        "order_lookup",
        "shipping_policy",
        "return_refund",
        "warranty",
        "ticket_request",
        "other",
    }
    assert body["sentiment_counts"]["positive"] == 1
    assert body["sentiment_counts"]["negative"] == 1
    assert set(body["sentiment_counts"]) == {
        "positive",
        "neutral",
        "negative",
    }
    assert body["tool_calls"] == 2
    assert body["tool_counts"] == {
        "policy_search": 1,
        "order_lookup": 1,
        "ticket_create": 0,
    }
    assert "message" not in body


@pytest.mark.anyio
async def test_unknown_action_returns_404(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/actions/act_missing/confirm",
        json={"confirm": True},
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_cors_allows_only_local_frontend(
    client: httpx.AsyncClient,
) -> None:
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    allowed = await client.options("/api/chat", headers=headers)
    denied = await client.options(
        "/api/chat",
        headers={**headers, "Origin": "https://example.com"},
    )

    assert allowed.status_code == 200
    assert (
        allowed.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )
    assert "access-control-allow-origin" not in denied.headers


def test_synthetic_order_storage_contains_required_demo_ids() -> None:
    orders = load_orders()
    assert {order.order_id for order in orders} >= {
        "ASIA-1001",
        "ASIA-1002",
        "ASIA-9999",
    }
