"""A.S.I.A FastAPI application with deterministic product behavior."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, load_settings
from app.providers import (
    ChatProviders,
    GroundedResponseRuntime,
    default_chat_providers,
)
from app.providers.factory import build_response_runtime
from app.reference_system import ReferenceSystem
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


def _state(request: Request) -> DemoState:
    return request.app.state.demo_state


def _reference_system(request: Request) -> ReferenceSystem:
    return request.app.state.reference_system


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return a lightweight liveness response."""
    return HealthResponse()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Handle one customer Turn through the Reference System."""
    return await _reference_system(request).handle(req.message)


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
        message = "Yêu cầu đã bị hủy trước đó." if resolution.repeated else "Yêu cầu đã được hủy."

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


def create_app(
    state: DemoState | None = None,
    *,
    chat_providers: ChatProviders | None = None,
    settings: Settings | None = None,
    response_runtime: GroundedResponseRuntime | None = None,
) -> FastAPI:
    """Construct an application with fresh injectable in-memory state."""
    validated_settings = settings or load_settings()
    application = FastAPI(
        title="A.S.I.A - AI Support for Vietnamese E-Commerce",
        version="0.1",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    runtime = response_runtime or build_response_runtime(validated_settings)
    demo_state = state or DemoState()
    application.state.demo_state = demo_state
    application.state.reference_system = ReferenceSystem(
        chat_providers or default_chat_providers(runtime),
        draft_ticket=demo_state.draft_ticket,
        counters=demo_state.counters,
    )
    application.state.settings = validated_settings
    application.state.response_runtime = runtime
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
