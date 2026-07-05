import {
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { AdminOverview } from "./AdminOverview";
import { ADMIN_URL, adminOverview } from "../test/fixtures";
import { server } from "../test/server";

function expectMetric(label: string, value: number) {
  const labelNode = screen.getByText(label);
  const card = labelNode.closest("article");
  expect(card).not.toBeNull();
  expect(within(card!).getByText(String(value))).toBeInTheDocument();
}

describe("AdminOverview", () => {
  it("fetches and renders the aggregate overview", async () => {
    server.use(
      http.get(ADMIN_URL, () =>
        HttpResponse.json(
          adminOverview({
            total_messages: 4,
            total_tickets: 1,
            intent_counts: { order_lookup: 2, ticket_request: 1 },
            sentiment_counts: { neutral: 3, negative: 1 },
            tool_calls: 3,
            tool_counts: { order_lookup: 2, ticket_create: 1 },
          }),
        ),
      ),
    );
    render(<AdminOverview refreshToken={0} />);

    await waitFor(() => expectMetric("Tin nhắn", 4));
    expectMetric("Phiếu hỗ trợ", 1);
    expectMetric("Tool calls", 3);
    expect(screen.getAllByText("order lookup")).toHaveLength(2);
    expect(screen.getByText("ticket create")).toBeInTheDocument();
  });

  it("renders empty metrics without an error", async () => {
    server.use(
      http.get(ADMIN_URL, () =>
        HttpResponse.json(adminOverview()),
      ),
    );
    render(<AdminOverview refreshToken={0} />);

    await waitFor(() => expectMetric("Tin nhắn", 0));
    expectMetric("Phiếu hỗ trợ", 0);
    expectMetric("Tool calls", 0);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("refreshes when the parent activity token changes", async () => {
    let requestCount = 0;
    server.use(
      http.get(ADMIN_URL, () => {
        requestCount += 1;
        return HttpResponse.json(
          adminOverview({
            total_messages: requestCount,
          }),
        );
      }),
    );
    const { rerender } = render(<AdminOverview refreshToken={0} />);

    await waitFor(() => expectMetric("Tin nhắn", 1));
    rerender(<AdminOverview refreshToken={1} />);

    await waitFor(() => expectMetric("Tin nhắn", 2));
    expect(requestCount).toBe(2);
  });
});
