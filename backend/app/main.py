"""A.S.I.A FastAPI application for the deterministic local demo."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.intent import IntentLabel, analyze_message
from app.order_service import lookup_order
from app.policy_search import search_policy
from app.schemas import (
    ActionConfirmRequest,
    ActionConfirmResponse,
    ActionStatus,
    AdminOverview,
    ChatRequest,
    ChatResponse,
    HealthResponse,
)
from app.state import DemoState

router = APIRouter(prefix="/api")

GENERAL_REPLY = (
    "Xin chào! Mình là A.S.I.A, trợ lý hỗ trợ khách hàng. Bạn có thể hỏi về "
    "chính sách, tra cứu đơn hàng hoặc yêu cầu tạo phiếu hỗ trợ."
)


def _state(request: Request) -> DemoState:
    return request.app.state.demo_state


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return a lightweight liveness response."""
    return HealthResponse()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Handle one deterministic customer-support message."""
    state = _state(request)
    analysis = analyze_message(req.message)
    intent = analysis.intent
    sentiment = analysis.sentiment
    reply = GENERAL_REPLY
    citations = []
    order = None
    actions = []

    if intent in {
        IntentLabel.SHIPPING_POLICY,
        IntentLabel.RETURN_REFUND,
        IntentLabel.WARRANTY,
    }:
        state.record_tool("policy_search")
        policy_result = search_policy(req.message)
        reply = policy_result.answer
        citations = list(policy_result.citations)
    elif intent == IntentLabel.ORDER_LOOKUP:
        order_result = lookup_order(req.message)
        reply = order_result.answer
        order = order_result.order
        if order_result.lookup_performed:
            state.record_tool("order_lookup")
    elif intent == IntentLabel.TICKET_REQUEST:
        reply = (
            "Mình đã chuẩn bị một phiếu hỗ trợ nháp. "
            "Vui lòng kiểm tra và xác nhận trước khi tạo."
        )
        actions.append(state.draft_ticket(req.message))

    state.record_message(intent, sentiment)
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    return ChatResponse(
        reply=reply,
        intent=intent,
        sentiment=sentiment,
        citations=citations,
        order=order,
        actions=actions,
        session_id=session_id,
    )


@router.post(
    "/actions/{action_id}/confirm",
    response_model=ActionConfirmResponse,
)
async def confirm_action(
    action_id: str,
    req: ActionConfirmRequest,
    request: Request,
) -> ActionConfirmResponse:
    """Confirm or cancel a proposed action exactly once."""
    resolution = _state(request).resolve_action(
        action_id,
        confirm=req.confirm,
    )
    if resolution is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy yêu cầu chờ xác nhận.",
        )

    if resolution.status == ActionStatus.CONFIRMED:
        message = (
            "Phiếu hỗ trợ đã được tạo trước đó."
            if resolution.repeated
            else "Phiếu hỗ trợ đã được tạo thành công."
        )
    else:
        message = (
            "Yêu cầu đã bị hủy trước đó."
            if resolution.repeated
            else "Yêu cầu đã được hủy."
        )

    return ActionConfirmResponse(
        action_id=action_id,
        status=resolution.status,
        message=message,
        ticket_id=resolution.ticket_id,
    )


@router.get("/admin/overview", response_model=AdminOverview)
async def admin_overview(request: Request) -> AdminOverview:
    """Return aggregate counters without message or customer data."""
    return _state(request).overview()


def create_app(state: DemoState | None = None) -> FastAPI:
    """Construct an application with fresh injectable in-memory state."""
    application = FastAPI(
        title="A.S.I.A - AI Support for Vietnamese E-Commerce",
        version="0.1",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.state.demo_state = state or DemoState()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(router)
    return application


app = create_app()
