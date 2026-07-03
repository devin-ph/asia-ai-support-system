# A.S.I.A

**AI Support & Insight Analytics System**

A.S.I.A is a local Vietnamese e-commerce support demo. The current milestone,
`v0.1`, uses deterministic logic and synthetic data to prove a safe,
runnable API contract before adding an LLM or external infrastructure.

## What the demo supports

- Grounded Vietnamese policy answers with evidence citations.
- Safe lookup of synthetic orders owned by one fixed demo customer.
- Support-ticket drafting followed by explicit, idempotent confirmation.
- Aggregate admin counters for messages, tickets, intents, sentiment, and tools.

See [docs/demo-scope.md](docs/demo-scope.md) for the complete scope and safety
invariants.

## Stack

- Python 3.10+
- FastAPI and Pydantic
- Pytest, HTTPX, and AnyIO
- In-memory state and repository-owned synthetic fixtures

No database, hosted model, vector store, Docker, or real customer data is used
in this milestone.

## Local setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Then install the backend dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

Check the repository prerequisites:

```bash
python scripts/dev.py doctor
```

Start the API:

```bash
python scripts/dev.py backend
```

The API is then available at:

- API base: `http://127.0.0.1:8000/api`
- OpenAPI UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Run the test suite:

```bash
python scripts/dev.py test
```

## Demo inputs

Useful prompts for `POST /api/chat`:

- `Chính sách đổi trả áp dụng trong bao lâu?`
- `Tra cứu đơn hàng ASIA-1001 giúp tôi`
- `Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi`

Synthetic order behavior:

- `ASIA-1001` and `ASIA-1002` belong to the fixed demo customer.
- `ASIA-9001` is a non-owned safety fixture and must never return order details.
- Unknown and non-owned IDs intentionally receive the same response.

## API endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | API liveness and version |
| `POST` | `/api/chat` | Policy, order, ticket-draft, and general chat flows |
| `POST` | `/api/actions/{action_id}/confirm` | Confirm or cancel a pending action |
| `GET` | `/api/admin/overview` | Aggregate, non-PII demo counters |

## Current limitations

- State resets whenever the backend restarts.
- Intent and sentiment detection are deterministic keyword rules.
- Policies and orders are deliberately small synthetic fixtures.
- The frontend has not yet been scaffolded; `doctor` reports it as missing until
  `frontend/package.json` is added.
