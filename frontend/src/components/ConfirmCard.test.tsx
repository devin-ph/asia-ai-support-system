import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ConfirmCard } from "./ConfirmCard";
import { ACTION_URL, pendingAction } from "../test/fixtures";
import { server } from "../test/server";

describe("ConfirmCard", () => {
  it("confirms the issued action and renders its ticket ID", async () => {
    const onResolved = vi.fn();
    const receivedBodies: unknown[] = [];
    server.use(
      http.post(ACTION_URL, async ({ params, request }) => {
        receivedBodies.push(await request.json());
        expect(params.actionId).toBe(pendingAction.action_id);
        return HttpResponse.json({
          action_id: pendingAction.action_id,
          status: "confirmed",
          message: "Phiếu hỗ trợ đã được tạo thành công.",
          ticket_id: "tkt_demo123",
        });
      }),
    );
    render(
      <ConfirmCard action={pendingAction} onResolved={onResolved} />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Xác nhận tạo phiếu" }),
    );

    expect(
      await screen.findByText("Phiếu hỗ trợ đã được tạo thành công."),
    ).toBeInTheDocument();
    expect(screen.getByText("Mã phiếu: tkt_demo123")).toBeInTheDocument();
    expect(receivedBodies).toEqual([{ confirm: true }]);
    expect(onResolved).toHaveBeenCalledOnce();
    expect(
      screen.queryByRole("button", { name: "Xác nhận tạo phiếu" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Hủy" }),
    ).not.toBeInTheDocument();
  });

  it("cancels the issued action without rendering a ticket ID", async () => {
    const onResolved = vi.fn();
    const receivedBodies: unknown[] = [];
    server.use(
      http.post(ACTION_URL, async ({ params, request }) => {
        receivedBodies.push(await request.json());
        expect(params.actionId).toBe(pendingAction.action_id);
        return HttpResponse.json({
          action_id: pendingAction.action_id,
          status: "cancelled",
          message: "Yêu cầu đã được hủy.",
          ticket_id: null,
        });
      }),
    );
    render(
      <ConfirmCard action={pendingAction} onResolved={onResolved} />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Hủy" }));

    expect(
      await screen.findByText("Yêu cầu đã được hủy."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Mã phiếu:/)).not.toBeInTheDocument();
    expect(receivedBodies).toEqual([{ confirm: false }]);
    expect(onResolved).toHaveBeenCalledOnce();
    expect(
      screen.queryByRole("button", { name: "Xác nhận tạo phiếu" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Hủy" }),
    ).not.toBeInTheDocument();
  });
});
