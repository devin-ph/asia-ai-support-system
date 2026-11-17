"""The Reference System: least-authority handling of one customer Turn."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from app.intent import IntentLabel
from app.providers import ChatProviders
from app.schemas import (
    ChatResponse,
    Citation,
    OrderSummary,
    PendingAction,
    ToolEvent,
    ToolEventStatus,
    ToolName,
)
from app.state import UsageCounters

GENERAL_REPLY = (
    "Xin chào! Mình là A.S.I.A, trợ lý hỗ trợ khách hàng. Bạn có thể hỏi về "
    "chính sách, tra cứu đơn hàng hoặc yêu cầu tạo phiếu hỗ trợ."
)
TICKET_DRAFT_REPLY = (
    "Mình đã chuẩn bị một phiếu hỗ trợ nháp. Vui lòng kiểm tra và xác nhận trước khi tạo."
)

POLICY_INTENTS = frozenset(
    {
        IntentLabel.SHIPPING_POLICY,
        IntentLabel.RETURN_REFUND,
        IntentLabel.WARRANTY,
    }
)

TicketDrafter = Callable[[str], PendingAction]
"""Propose a ticket as a Pending Action. It must never create or resolve one."""


class ReferenceSystem:
    """Handle one Turn: the application routes, the model may only propose.

    The constructor receives read-only providers, a draft-only callable for
    Pending Actions, and usage counters. It never receives a capability that
    resolves an action or writes a ticket; that belongs to the confirmation
    endpoint alone.
    """

    def __init__(
        self,
        providers: ChatProviders,
        *,
        draft_ticket: TicketDrafter,
        counters: UsageCounters,
    ) -> None:
        self._providers = providers
        self._draft_ticket = draft_ticket
        self._counters = counters

    async def handle(self, message: str) -> ChatResponse:
        """Return the reply, labels, citations, tool events, and any draft."""
        analysis = self._providers.analyzer.analyze(message)
        intent = analysis.intent
        assistant_message = GENERAL_REPLY
        citations: list[Citation] = []
        tool_events: list[ToolEvent] = []
        pending_action: PendingAction | None = None

        if intent in POLICY_INTENTS:
            policy_result = await self._providers.policy.answer(
                message,
                request_id=uuid.uuid4().hex,
            )
            assistant_message = policy_result.answer
            citations = list(policy_result.citations)
            if policy_result.lookup_performed:
                tool_events.append(
                    self._tool_event(
                        ToolName.POLICY_SEARCH,
                        ToolEventStatus.COMPLETED
                        if citations
                        else ToolEventStatus.INSUFFICIENT_CONTEXT,
                    )
                )
        elif intent == IntentLabel.ORDER_LOOKUP:
            order_result = self._providers.orders.lookup(message)
            assistant_message = order_result.answer
            if order_result.lookup_performed:
                tool_events.append(
                    self._tool_event(
                        ToolName.ORDER_LOOKUP,
                        ToolEventStatus.COMPLETED
                        if order_result.order is not None
                        else ToolEventStatus.NOT_FOUND,
                        order=order_result.order,
                    )
                )
        elif intent == IntentLabel.TICKET_REQUEST:
            assistant_message = TICKET_DRAFT_REPLY
            pending_action = self._draft_ticket(message)

        self._counters.record_message(intent, analysis.sentiment)
        return ChatResponse(
            assistant_message=assistant_message,
            intent=intent,
            sentiment=analysis.sentiment,
            citations=citations,
            tool_events=tool_events,
            pending_action=pending_action,
        )

    def _tool_event(
        self,
        tool: ToolName,
        status: ToolEventStatus,
        *,
        order: OrderSummary | None = None,
    ) -> ToolEvent:
        self._counters.record_tool(tool)
        return ToolEvent(tool=tool, status=status, order=order)
