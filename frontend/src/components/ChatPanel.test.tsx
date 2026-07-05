import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ChatPanel } from "./ChatPanel";
import {
  CHAT_URL,
  chatResponse,
  pendingAction,
} from "../test/fixtures";
import { server } from "../test/server";

async function submitMessage(message: string) {
  const user = userEvent.setup();
  await user.type(screen.getByRole("textbox", { name: "Tin nhắn" }), message);
  await user.click(screen.getByRole("button", { name: "Gửi" }));
}

describe("ChatPanel", () => {
  it("shows the synthetic-only notice as the input description", () => {
    render(<ChatPanel onActivity={vi.fn()} />);

    expect(screen.getByRole("textbox", { name: "Tin nhắn" }))
      .toHaveAccessibleDescription(
        "Demo chỉ sử dụng dữ liệu giả lập. Không nhập thông tin cá nhân hoặc dữ liệu khách hàng thật.",
      );
  });

  it("submits a message and shows the loading state", async () => {
    server.use(
      http.post(CHAT_URL, async () => {
        await delay(100);
        return HttpResponse.json(chatResponse());
      }),
    );
    render(<ChatPanel onActivity={vi.fn()} />);

    await submitMessage("Xin chào A.S.I.A");

    expect(screen.getByText("Xin chào A.S.I.A")).toBeInTheDocument();
    expect(screen.getByText("Đang xử lý…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gửi" })).toBeDisabled();
    expect(
      await screen.findByText("Mình đã tiếp nhận yêu cầu demo."),
    ).toBeInTheDocument();
  });

  it("renders the assistant response and grounded citation", async () => {
    const onActivity = vi.fn();
    server.use(
      http.post(CHAT_URL, () =>
        HttpResponse.json(
          chatResponse({
            assistant_message: "Đổi trả được hỗ trợ trong vòng 7 ngày.",
            intent: "return_refund",
            citations: [
              {
                title: "Chính sách đổi trả và hoàn tiền",
                source: "docs/policies/return_policy.md",
                section: "Điều kiện và thời hạn đổi trả",
              },
            ],
          }),
        ),
      ),
    );
    render(<ChatPanel onActivity={onActivity} />);

    await submitMessage("Chính sách đổi trả trong bao lâu?");

    expect(
      await screen.findByText("Đổi trả được hỗ trợ trong vòng 7 ngày."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Chính sách đổi trả và hoàn tiền"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Điều kiện và thời hạn đổi trả"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("docs/policies/return_policy.md"),
    ).toBeInTheDocument();
    expect(onActivity).toHaveBeenCalledOnce();
  });

  it("renders a safe order summary from a tool event", async () => {
    server.use(
      http.post(CHAT_URL, () =>
        HttpResponse.json(
          chatResponse({
            assistant_message: "Đơn ASIA-1001 đang được giao.",
            intent: "order_lookup",
            tool_events: [
              {
                tool: "order_lookup",
                status: "completed",
                order: {
                  order_id: "ASIA-1001",
                  status: "Đang giao",
                  carrier: "Đơn vị vận chuyển Demo",
                  estimated_delivery: "2026-07-05",
                  items_count: 2,
                  last_updated: "2026-07-03T09:30:00+07:00",
                },
              },
            ],
          }),
        ),
      ),
    );
    render(<ChatPanel onActivity={vi.fn()} />);

    await submitMessage("Tra cứu ASIA-1001");

    const orderId = await screen.findByText("Mã đơn");
    expect(orderId.parentElement).not.toBeNull();
    expect(within(orderId.parentElement!).getByText("ASIA-1001"))
      .toBeInTheDocument();
    expect(screen.getByText("Đang giao")).toBeInTheDocument();
    expect(screen.getByText("Đơn vị vận chuyển Demo")).toBeInTheDocument();
    expect(screen.getByText("2026-07-05")).toBeInTheDocument();
  });

  it("renders ConfirmCard when chat returns a pending action", async () => {
    server.use(
      http.post(CHAT_URL, () =>
        HttpResponse.json(
          chatResponse({
            assistant_message: "Mình đã chuẩn bị phiếu hỗ trợ nháp.",
            intent: "ticket_request",
            pending_action: pendingAction,
          }),
        ),
      ),
    );
    render(<ChatPanel onActivity={vi.fn()} />);

    await submitMessage("Tôi muốn tạo phiếu hỗ trợ");

    expect(
      await screen.findByRole("region", { name: "Xác nhận tạo phiếu" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Xác nhận tạo phiếu" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hủy" })).toBeInTheDocument();
  });

  it("renders the API error detail", async () => {
    server.use(
      http.post(CHAT_URL, () =>
        HttpResponse.json(
          { detail: "Backend demo đang bận." },
          { status: 503 },
        ),
      ),
    );
    render(<ChatPanel onActivity={vi.fn()} />);

    await submitMessage("Xin chào");

    expect(
      await screen.findByText("Backend demo đang bận."),
    ).toBeInTheDocument();
  });
});
