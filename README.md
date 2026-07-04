# A.S.I.A

**AI Support & Insight Analytics System**

A.S.I.A is a local Vietnamese e-commerce support demo. The current milestone,
**v0.1: Runnable Vertical Slice**, proves the product contract end to end with a
FastAPI backend, a minimal React interface, deterministic rules, and synthetic
data.

The demo deliberately uses no hosted model, vector database, production
database, or real customer data. Its purpose is to validate safe behavior and
clear integration boundaries before introducing external infrastructure.

The complete behavioral contract and safety invariants live in
[`docs/demo-scope.md`](docs/demo-scope.md).

## What the vertical slice demonstrates

The v0.1 slice connects four customer-support flows through one runnable UI and
API:

1. **Grounded policy answers**
   Vietnamese shipping, return, refund, and warranty questions are answered
   from trusted Markdown policy sections. Matching answers include citations;
   unsupported questions return an insufficient-context response.

2. **Safe synthetic order lookup**
   Demo order references such as `ASIA-1001` are checked against the fixed
   customer `demo-customer-001`. Only allowlisted order fields are returned.
   Unknown and non-owned orders receive the same safe denial.

3. **Ticket drafting with explicit confirmation**
   A chat request may draft a pending action, but it cannot create a ticket.
   Ticket creation happens only after a separate confirmation request.
   Confirmation is idempotent, so repeating it does not create duplicates.

4. **Basic admin overview**
   The frontend displays aggregate message, ticket, intent, sentiment, and tool
   counts without exposing message content or customer data.

`POST /api/chat` keeps a stable response envelope:

- `assistant_message`
- `intent`
- `sentiment`
- `citations`
- `tool_events`
- `pending_action`

## Technology

- Python 3.10+
- FastAPI and Pydantic
- Pytest, HTTPX, and AnyIO
- React, TypeScript, and Vite
- Local Markdown policies and validated synthetic JSON storage
- Process-local actions and aggregate counters

## Run locally

### Prerequisites

- Python 3.10 or newer
- Node.js and npm

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
source .venv/bin/activate
```

Install dependencies from the repository root:

```bash
python -m pip install -r backend/requirements.txt
cd frontend
npm install
cd ..
```

Verify the local environment:

```bash
python scripts/dev.py doctor
```

### Start the backend

In the first terminal:

```bash
python scripts/dev.py backend
```

The backend is available at:

- API: `http://127.0.0.1:8000/api`
- OpenAPI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### Start the frontend

In a second terminal:

```bash
python scripts/dev.py frontend
```

Open `http://127.0.0.1:5173`.

### Run tests

Use the fast backend test loop while developing:

```bash
python scripts/dev.py test
```

Before committing or opening a pull request, run the full-project verification:

```bash
python scripts/dev.py verify
```

`verify` runs backend tests, frontend typecheck and production build, validates
runtime/fixture Git hygiene, scans candidate files for obvious credential
assignments without printing values, and checks staged and unstaged diffs for
whitespace errors. Lint and format checks are not included until the project
adopts those tools explicitly.

## Demo script

Start both servers, open the frontend, and follow this sequence.

### 1. Ask a grounded policy question

Send:

```text
Chính sách đổi trả áp dụng trong bao lâu?
```

Expected result:

- The answer is derived from the return policy.
- A citation shows the policy title, source file, and matching section.
- The intent and sentiment labels appear with the response.

You can also try:

```text
Phí vận chuyển được tính như thế nào?
Sản phẩm này được bảo hành trong bao lâu?
```

For the safe fallback path, ask about a topic that is not present in the policy
documents. The assistant should say that it lacks sufficient context and return
no citations.

### 2. Look up a synthetic order

Send:

```text
Tra cứu đơn hàng ASIA-1001 giúp tôi
```

Expected result:

- The order lookup tool completes.
- The API returns only allowlisted safe fields; the UI presents a compact order
  summary without ownership, contact, address, or payment data.

`ASIA-1001` and `ASIA-1002` belong to the fixed demo customer. `ASIA-9999` is a
non-owned safety fixture and must return the same generic denial as an unknown
order.

### 3. Draft and confirm a support ticket

Send:

```text
Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi
```

Expected result:

- Chat returns a pending action instead of creating a ticket.
- The UI displays a confirmation card.
- Choosing **Xác nhận tạo phiếu** calls
  `POST /api/actions/{action_id}/confirm` and creates exactly one ticket.
- Choosing **Hủy** creates no ticket.

### 4. Review the admin overview

The admin panel refreshes after chat activity and action confirmation. Verify
that message, ticket, intent, sentiment, and tool counters reflect the demo
steps without displaying message bodies or customer details.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness and API version |
| `POST` | `/api/chat` | Deterministic support interaction |
| `POST` | `/api/actions/{action_id}/confirm` | Confirm or cancel a pending action |
| `GET` | `/api/admin/overview` | Aggregate, non-PII demo counters |

## AI harnessing

The repository is structured so a human or coding agent can make changes
without treating the current chat system as an unconstrained AI application.
The harness establishes scope, repeatable commands, deterministic substitutes,
and safety checks around every change.

### `AGENTS.md`: operating instructions

[`AGENTS.md`](AGENTS.md) defines the project goal, source-of-truth order,
standard commands, safety rules, and definition of done for coding agents.
[`backend/AGENTS.md`](backend/AGENTS.md) adds backend-specific architecture and
API invariants. These files keep implementation work aligned with the current
milestone and discourage accidental scope expansion.

### `docs/demo-scope.md`: executable product contract

[`docs/demo-scope.md`](docs/demo-scope.md) describes the four required flows,
acceptance criteria, stable response shape, technical boundaries, and safety
invariants. It is read before implementation and reviewed alongside tests, so
the demo scope acts as the product-level contract rather than an informal
wish list.

### `scripts/dev.py`: repeatable development loop

[`scripts/dev.py`](scripts/dev.py) gives humans and agents one consistent entry
point:

```bash
python scripts/dev.py doctor
python scripts/dev.py backend
python scripts/dev.py frontend
python scripts/dev.py test
python scripts/dev.py verify
```

`test` is intentionally backend-only and optimized for the fast development
loop. `verify` is the full-stack “ready to commit / ready for PR” gate. This
separation reduces environment guesswork without making every local test run
pay the cost of a frontend production build.

### Fake providers: deterministic local stand-ins

v0.1 does not yet define a formal `FakeProvider` interface. Instead, small local
services act as deterministic stand-ins for dependencies that may exist in a
later milestone:

| Local stand-in | Replaces for v0.1 |
| --- | --- |
| `backend/app/intent.py` | Hosted intent and sentiment model |
| `backend/app/policy_search.py` | Embedding search, vector database, or hosted retrieval |
| `backend/app/order_service.py` | Commerce or order-management integration |
| `backend/app/ticket_service.py` | External helpdesk write API |

These stand-ins are fast, inspectable, testable, and offline. Future providers
should preserve the same public contracts and safety behavior so they can be
evaluated against the deterministic baseline.

### Synthetic data: safe fixtures by construction

- `data/fixtures/demo_orders.json` contains immutable synthetic order fixtures.
- `data/fixtures/demo_tickets.seed.json` is the immutable empty ticket seed.
- `var/demo_tickets.json` stores locally confirmed demo tickets and is ignored
  by Git. It is created on the first confirmed ticket.
- `docs/policies/*.md` is the only trusted policy corpus.
- The fixed identity is `demo-customer-001`.

No fixture should contain real names, addresses, phone numbers, email
addresses, payment information, secrets, or production identifiers.

### Confirmation guardrail: separate proposal from execution

The chat handler may only propose a `create_ticket` action. It returns that
proposal as `pending_action`; it does not perform the write. A separate
confirmation endpoint owns execution.

The guardrail also enforces:

- explicit user confirmation before ticket creation;
- cancellation without side effects;
- one ticket per action ID;
- the same result for repeated confirmation;
- no later confirmation of an already cancelled action.

This separation must remain in place if an LLM or external helpdesk provider is
introduced later. A model may help draft an action, but it must not receive
direct authority to execute it.

## Current limitations

- Intent and sentiment analysis use deterministic keyword rules.
- Policy retrieval is keyword-based and limited to the small repository corpus.
- The demo represents one fixed synthetic customer and has no authentication.
- Pending actions, messages, and aggregate counters are process-local and reset
  when the backend restarts.
- Confirmed tickets persist to the ignored `var/demo_tickets.json` runtime
  file, which is not suitable for multiple processes or production
  concurrency.
- There is no LLM, embedding model, vector database, PostgreSQL, queue, cache,
  Docker setup, or cloud deployment.
- The frontend is intentionally minimal and targets the local API.
- The application is a development demo, not a production support system.

## Next roadmap

The next milestone should preserve the v0.1 contracts and guardrails while
replacing local stand-ins incrementally:

1. Formalize provider interfaces and contract tests around the deterministic
   baseline.
2. Expand policy fixtures, Vietnamese evaluation cases, and frontend test
   coverage.
3. Add real authentication and tenant isolation before connecting any commerce
   data.
4. Move durable actions, tickets, idempotency records, and audit events to
   production-grade storage.
5. Evaluate an optional LLM behind grounded retrieval, structured outputs, and
   regression tests—without granting it direct write authority.
6. Add production observability, deployment configuration, accessibility
   review, and operational security controls.

These items are roadmap candidates only and remain outside the v0.1 demo scope.
