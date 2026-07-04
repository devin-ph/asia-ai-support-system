import { useState } from "react";

import {
  confirmAction,
  type ActionConfirmResponse,
  type PendingAction,
} from "../api";

interface ConfirmCardProps {
  action: PendingAction;
  onResolved: () => void;
}

export function ConfirmCard({
  action,
  onResolved,
}: ConfirmCardProps) {
  const [result, setResult] = useState<ActionConfirmResponse | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function resolve(confirm: boolean) {
    setIsSubmitting(true);
    setError("");
    try {
      const response = await confirmAction(action.action_id, confirm);
      setResult(response);
      onResolved();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Không thể xử lý yêu cầu.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="confirm-card" aria-label="Xác nhận tạo phiếu">
      <div>
        <p className="eyebrow">Cần xác nhận</p>
        <h4>{action.description}</h4>
        <p className="confirm-summary">{action.payload.summary}</p>
      </div>

      {result ? (
        <div className={`action-result action-result--${result.status}`}>
          <strong>{result.message}</strong>
          {result.ticket_id && <span>Mã phiếu: {result.ticket_id}</span>}
        </div>
      ) : (
        <div className="button-row">
          <button
            className="button button--primary"
            disabled={isSubmitting}
            onClick={() => void resolve(true)}
            type="button"
          >
            Xác nhận tạo phiếu
          </button>
          <button
            className="button button--secondary"
            disabled={isSubmitting}
            onClick={() => void resolve(false)}
            type="button"
          >
            Hủy
          </button>
        </div>
      )}

      {error && <p className="error-message">{error}</p>}
    </section>
  );
}
