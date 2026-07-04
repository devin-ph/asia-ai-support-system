import { useState, type FormEvent } from "react";

import { sendMessage, type ChatResponse, type ToolEvent } from "../api";
import { CitationPanel } from "./CitationPanel";
import { ConfirmCard } from "./ConfirmCard";

interface ChatPanelProps {
  onActivity: () => void;
}

interface ChatTurn {
  id: string;
  userMessage: string;
  response?: ChatResponse;
  error?: string;
}

export function ChatPanel({ onActivity }: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [isSending, setIsSending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isSending) {
      return;
    }

    const id = crypto.randomUUID();
    setTurns((current) => [
      ...current,
      { id, userMessage: trimmedMessage },
    ]);
    setMessage("");
    setIsSending(true);

    try {
      const response = await sendMessage(trimmedMessage);
      setTurns((current) =>
        current.map((turn) => (turn.id === id ? { ...turn, response } : turn)),
      );
      onActivity();
    } catch (requestError) {
      const error =
        requestError instanceof Error
          ? requestError.message
          : "Không thể gửi tin nhắn.";
      setTurns((current) =>
        current.map((turn) => (turn.id === id ? { ...turn, error } : turn)),
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <section className="chat-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Customer support</p>
          <h2>Trò chuyện với A.S.I.A</h2>
        </div>
      </div>

      <div className="conversation" aria-live="polite">
        {turns.length === 0 && (
          <div className="empty-state">
            <p>Thử một trong các câu hỏi:</p>
            <span>“Chính sách đổi trả trong bao lâu?”</span>
            <span>“Tra cứu đơn hàng ASIA-1001”</span>
            <span>“Tôi muốn tạo phiếu hỗ trợ”</span>
          </div>
        )}

        {turns.map((turn) => (
          <article className="chat-turn" key={turn.id}>
            <div className="message message--user">{turn.userMessage}</div>
            {!turn.response && !turn.error && (
              <div className="message message--assistant">Đang xử lý…</div>
            )}
            {turn.error && (
              <div className="message message--error">{turn.error}</div>
            )}
            {turn.response && (
              <div className="assistant-block">
                <div className="message message--assistant">
                  {turn.response.assistant_message}
                </div>
                <div className="tag-row">
                  <span>{turn.response.intent}</span>
                  <span>{turn.response.sentiment}</span>
                </div>
                <ToolEvents events={turn.response.tool_events} />
                <CitationPanel citations={turn.response.citations} />
                {turn.response.pending_action && (
                  <ConfirmCard
                    action={turn.response.pending_action}
                    onResolved={onActivity}
                  />
                )}
              </div>
            )}
          </article>
        ))}
      </div>

      <form className="chat-form" onSubmit={(event) => void submit(event)}>
        <label htmlFor="chat-message">Tin nhắn</label>
        <div>
          <textarea
            id="chat-message"
            maxLength={2000}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Nhập câu hỏi bằng tiếng Việt…"
            rows={3}
            value={message}
          />
          <button
            className="button button--primary"
            disabled={isSending || message.trim().length === 0}
            type="submit"
          >
            Gửi
          </button>
        </div>
      </form>
    </section>
  );
}

function ToolEvents({ events }: { events: ToolEvent[] }) {
  if (events.length === 0) {
    return null;
  }

  return (
    <div className="tool-events">
      {events.map((event, index) => (
        <section key={`${event.tool}-${index}`}>
          <div className="tool-event-heading">
            <span>{event.tool}</span>
            <strong>{event.status}</strong>
          </div>
          {event.order && (
            <dl className="order-summary">
              <div>
                <dt>Mã đơn</dt>
                <dd>{event.order.order_id}</dd>
              </div>
              <div>
                <dt>Trạng thái</dt>
                <dd>{event.order.status}</dd>
              </div>
              <div>
                <dt>Vận chuyển</dt>
                <dd>{event.order.carrier}</dd>
              </div>
              <div>
                <dt>Dự kiến giao</dt>
                <dd>{event.order.estimated_delivery}</dd>
              </div>
            </dl>
          )}
        </section>
      ))}
    </div>
  );
}
