import type {
  AdminOverviewData,
  ChatResponse,
  PendingAction,
} from "../api";

export const CHAT_URL = "http://localhost:5173/api/chat";
export const ACTION_URL =
  "http://localhost:5173/api/actions/:actionId/confirm";
export const ADMIN_URL = "http://localhost:5173/api/admin/overview";

export const pendingAction: PendingAction = {
  action_id: "act_demo123",
  action_type: "create_ticket",
  description: "Tạo phiếu hỗ trợ cho yêu cầu này",
  payload: {
    summary: "Sản phẩm demo bị lỗi",
  },
  status: "pending",
};

export function chatResponse(
  overrides: Partial<ChatResponse> = {},
): ChatResponse {
  return {
    assistant_message: "Mình đã tiếp nhận yêu cầu demo.",
    intent: "other",
    sentiment: "neutral",
    citations: [],
    tool_events: [],
    pending_action: null,
    ...overrides,
  };
}

export function adminOverview(
  overrides: Partial<AdminOverviewData> = {},
): AdminOverviewData {
  return {
    total_messages: 0,
    total_tickets: 0,
    intent_counts: {},
    sentiment_counts: {},
    tool_calls: 0,
    tool_counts: {},
    ...overrides,
  };
}
