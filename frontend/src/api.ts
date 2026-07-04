export type Intent =
  | "order_lookup"
  | "shipping_policy"
  | "return_refund"
  | "warranty"
  | "ticket_request"
  | "other";

export type Sentiment = "positive" | "neutral" | "negative";
export type ActionStatus = "pending" | "confirmed" | "cancelled";

export interface Citation {
  title: string;
  source: string;
  section: string;
}

export interface OrderSummary {
  order_id: string;
  status: string;
  carrier: string;
  estimated_delivery: string;
  items_count: number;
  last_updated: string;
}

export interface ToolEvent {
  tool: "policy_search" | "order_lookup";
  status: "completed" | "insufficient_context" | "not_found";
  order: OrderSummary | null;
}

export interface PendingAction {
  action_id: string;
  action_type: "create_ticket";
  description: string;
  payload: Record<string, string>;
  status: ActionStatus;
}

export interface ChatResponse {
  assistant_message: string;
  intent: Intent;
  sentiment: Sentiment;
  citations: Citation[];
  tool_events: ToolEvent[];
  pending_action: PendingAction | null;
}

export interface ActionConfirmResponse {
  action_id: string;
  status: ActionStatus;
  message: string;
  ticket_id: string | null;
}

export interface AdminOverviewData {
  total_messages: number;
  total_tickets: number;
  intent_counts: Record<string, number>;
  sentiment_counts: Record<string, number>;
  tool_calls: number;
  tool_counts: Record<string, number>;
}

async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let detail = `Yêu cầu thất bại (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the status-based fallback for non-JSON errors.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export function sendMessage(message: string): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
}

export function confirmAction(
  actionId: string,
  confirm: boolean,
): Promise<ActionConfirmResponse> {
  return apiRequest<ActionConfirmResponse>(
    `/api/actions/${encodeURIComponent(actionId)}/confirm`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm }),
    },
  );
}

export function getAdminOverview(): Promise<AdminOverviewData> {
  return apiRequest<AdminOverviewData>("/api/admin/overview");
}
