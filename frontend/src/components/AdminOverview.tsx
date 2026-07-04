import { useCallback, useEffect, useState } from "react";

import { getAdminOverview, type AdminOverviewData } from "../api";

interface AdminOverviewProps {
  refreshToken: number;
}

const EMPTY_OVERVIEW: AdminOverviewData = {
  total_messages: 0,
  total_tickets: 0,
  intent_counts: {},
  sentiment_counts: {},
  tool_calls: 0,
  tool_counts: {},
};

function label(value: string) {
  return value.replaceAll("_", " ");
}

export function AdminOverview({ refreshToken }: AdminOverviewProps) {
  const [overview, setOverview] =
    useState<AdminOverviewData>(EMPTY_OVERVIEW);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError("");
    try {
      setOverview(await getAdminOverview());
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Không thể tải thống kê.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, refreshToken]);

  return (
    <aside className="admin-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Admin</p>
          <h2>Tổng quan demo</h2>
        </div>
        <button
          className="button button--ghost"
          disabled={isLoading}
          onClick={() => void refresh()}
          type="button"
        >
          Làm mới
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      <div className="metric-grid">
        <article>
          <span>Tin nhắn</span>
          <strong>{overview.total_messages}</strong>
        </article>
        <article>
          <span>Phiếu hỗ trợ</span>
          <strong>{overview.total_tickets}</strong>
        </article>
        <article>
          <span>Tool calls</span>
          <strong>{overview.tool_calls}</strong>
        </article>
      </div>

      <MetricList title="Intent" values={overview.intent_counts} />
      <MetricList title="Sentiment" values={overview.sentiment_counts} />
      <MetricList title="Tools" values={overview.tool_counts} />
    </aside>
  );
}

function MetricList({
  title,
  values,
}: {
  title: string;
  values: Record<string, number>;
}) {
  return (
    <section className="metric-list">
      <h3>{title}</h3>
      {Object.entries(values).map(([name, count]) => (
        <div key={name}>
          <span>{label(name)}</span>
          <strong>{count}</strong>
        </div>
      ))}
    </section>
  );
}
