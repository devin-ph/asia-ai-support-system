import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

interface AdminOverview {
  total_messages: number;
  total_tickets: number;
  intent_counts: Record<string, number>;
  sentiment_counts: Record<string, number>;
  tool_calls: number;
  tool_counts: Record<string, number>;
}

interface ChatResponse {
  tool_events: Array<{
    tool: string;
    status: string;
    order: Record<string, unknown> | null;
  }>;
}

async function getAdminOverview(
  request: APIRequestContext,
): Promise<AdminOverview> {
  const response = await request.get("http://127.0.0.1:8000/api/admin/overview");
  expect(response.ok()).toBe(true);
  return (await response.json()) as AdminOverview;
}

async function sendChatMessage(page: Page, message: string) {
  await page.getByRole("textbox", { name: "Tin nhắn" }).fill(message);
  await page.getByRole("button", { name: "Gửi" }).click();
}

function metricValue(page: Page, label: string) {
  return page
    .locator("article")
    .filter({ has: page.getByText(label, { exact: true }) })
    .locator("strong");
}

test.describe.serial("A.S.I.A demo browser flows", () => {
  let initialOverview: AdminOverview;

  test.beforeAll(async ({ request }) => {
    initialOverview = await getAdminOverview(request);
  });

  test("answers a policy question with a visible citation", async ({ page }) => {
    await page.goto("/");

    await sendChatMessage(page, "Chính sách đổi trả áp dụng trong bao lâu?");

    await expect(page.getByText(/vòng 7 ngày/)).toBeVisible();
    const citations = page.getByRole("region", { name: "Nguồn chính sách" });
    await expect(citations).toBeVisible();
    await expect(
      citations.getByText("Chính sách đổi trả và hoàn tiền"),
    ).toBeVisible();
    await expect(
      citations.getByText("Điều kiện và thời hạn đổi trả"),
    ).toBeVisible();
    await expect(
      citations.getByText("docs/policies/return_policy.md"),
    ).toBeVisible();
  });

  test("renders a safe order lookup summary without extra fields", async ({ page }) => {
    await page.goto("/");

    const chatResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith("/api/chat") &&
        response.request().method() === "POST",
    );
    await sendChatMessage(page, "Tra cứu đơn hàng ASIA-1001 giúp tôi");
    const payload = (await (await chatResponse).json()) as ChatResponse;
    const orderEvent = payload.tool_events.find(
      (event) => event.tool === "order_lookup" && event.status === "completed",
    );

    expect(orderEvent?.order).toBeTruthy();
    expect(Object.keys(orderEvent?.order ?? {}).sort()).toEqual([
      "carrier",
      "estimated_delivery",
      "items_count",
      "last_updated",
      "order_id",
      "status",
    ]);

    const orderSummary = page.locator(".order-summary");
    await expect(orderSummary.getByText("Mã đơn")).toBeVisible();
    await expect(
      orderSummary.getByText("ASIA-1001", { exact: true }),
    ).toBeVisible();
    await expect(orderSummary.getByText("Đang giao")).toBeVisible();
    await expect(orderSummary.getByText("Đơn vị vận chuyển Demo")).toBeVisible();
    await expect(orderSummary.getByText("2026-07-05")).toBeVisible();

    await expect(page.getByText("owner_customer_id")).toHaveCount(0);
    await expect(page.getByText("demo-customer-001")).toHaveCount(0);
    await expect(page.getByText(/địa chỉ|address|phone|email|payment/i))
      .toHaveCount(0);
  });

  test(
    "requires explicit ticket cancellation or confirmation",
    async ({ page, request }) => {
      await page.goto("/");
      const beforeCancel = await getAdminOverview(request);

      await sendChatMessage(page, "Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi");

      const cancelCard = page.getByRole("region", {
        name: "Xác nhận tạo phiếu",
      });
      await expect(cancelCard).toBeVisible();
      await expect(
        cancelCard.getByText("Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi"),
      ).toBeVisible();
      await cancelCard.getByRole("button", { name: "Hủy" }).click();
      await expect(cancelCard.getByText("Yêu cầu đã được hủy.")).toBeVisible();

      const afterCancel = await getAdminOverview(request);
      expect(afterCancel.total_tickets).toBe(beforeCancel.total_tickets);
      expect(afterCancel.tool_counts.ticket_create).toBe(
        beforeCancel.tool_counts.ticket_create,
      );

      await sendChatMessage(page, "Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi");

      const confirmCards = page.getByRole("region", {
        name: "Xác nhận tạo phiếu",
      });
      const confirmCard = confirmCards.last();
      await expect(confirmCard).toBeVisible();
      await confirmCard
        .getByRole("button", { name: "Xác nhận tạo phiếu" })
        .click();
      await expect(
        confirmCard.getByText("Phiếu hỗ trợ đã được tạo thành công."),
      ).toBeVisible();
      await expect(confirmCard.getByText(/Mã phiếu: tkt_/)).toBeVisible();

      const afterConfirm = await getAdminOverview(request);
      expect(afterConfirm.total_tickets).toBe(beforeCancel.total_tickets + 1);
      expect(afterConfirm.tool_counts.ticket_create).toBe(
        beforeCancel.tool_counts.ticket_create + 1,
      );
    },
  );

  test("refreshes admin metrics after the demo flow", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("button", { name: "Làm mới" }).click();

    await expect(metricValue(page, "Tin nhắn")).toHaveText(
      String(initialOverview.total_messages + 4),
    );
    await expect(metricValue(page, "Phiếu hỗ trợ")).toHaveText(
      String(initialOverview.total_tickets + 1),
    );
    await expect(metricValue(page, "Tool calls")).toHaveText(
      String(initialOverview.tool_calls + 3),
    );
    const toolsList = page
      .locator(".metric-list")
      .filter({ has: page.getByRole("heading", { name: "Tools" }) });
    await expect(toolsList.getByText("policy search")).toBeVisible();
    await expect(toolsList.getByText("order lookup")).toBeVisible();
    await expect(toolsList.getByText("ticket create")).toBeVisible();
  });
});
