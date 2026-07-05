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
- Node.js `^20.19.0` or `>=22.12.0`
- npm

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
npm ci
cd ..
```

Verify that the machine can run the complete project:

```bash
python scripts/dev.py doctor
```

`doctor` validates the Python and Node versions, npm, backend dependencies and
application import, the frontend lockfile/scripts/installed dependencies,
writable local runtime storage, and the current `.env` contract. If
`frontend/node_modules` is missing or incomplete, run `npm ci` inside
`frontend/`.

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

Run the fast backend and frontend unit/component test loop while developing:

```bash
python scripts/dev.py test
```

For frontend watch mode:

```bash
cd frontend
npm run test:watch
```

Before committing or opening a pull request, run the full-project verification:

```bash
python scripts/dev.py verify
```

To inspect the product-level deterministic baseline separately:

```bash
python scripts/dev.py eval
```

`eval` runs the versioned synthetic cases under [`eval/`](eval/README.md) and
reports intent accuracy, policy-section hit rate, insufficient-context
precision, order-ID extraction accuracy, and confirmation-guardrail pass rate.
Known misses remain visible; this is a benchmark, not a test that is expected
to score 100%.

`verify` runs backend and frontend tests, checks the committed evaluation
snapshot for drift, runs frontend typecheck and production build, validates
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
python scripts/dev.py eval
python scripts/dev.py verify
```

`test` runs the fast backend and frontend unit/component suites. `eval` measures
the deterministic product baseline against versioned JSONL cases. `verify` is
the full-stack “ready to commit / ready for PR” gate and additionally checks the
baseline snapshot, typecheck, production build, and repository hygiene. This
keeps the local test loop useful without making it pay the cost of a frontend
production build.

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

### Evaluation before AI: prove the delta

[`eval/`](eval/README.md) contains versioned Vietnamese intent, policy, order,
and ticket-flow cases. [`scripts/evaluate.py`](scripts/evaluate.py) runs the
current local services against the same ground truth and records the v0.1
scores in `eval/baseline.v0.1.json`.

The baseline deliberately includes natural paraphrases that keyword rules do
not yet handle. A future LLM or retrieval provider should be evaluated on these
same cases and must improve useful metrics without reducing the 100%
confirmation-guardrail result. Dataset changes and implementation changes
should be reviewed separately where practical to avoid moving the goalposts.

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
- The API has no session or conversation persistence. Frontend conversation
  turns are local UI state and reset when the page reloads.
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

1. Formalize provider interfaces and run candidate providers against the
   committed deterministic baseline.
2. Expand policy fixtures and Vietnamese evaluation coverage without replacing
   known hard cases merely to improve scores.
3. Add real authentication and tenant isolation before connecting any commerce
   data.
4. Move durable actions, tickets, idempotency records, and audit events to
   production-grade storage.
5. Evaluate an optional LLM behind grounded retrieval, structured outputs, and
   regression tests—without granting it direct write authority.
6. Add production observability, deployment configuration, accessibility
   review, and operational security controls.

These items are roadmap candidates only and remain outside the v0.1 demo scope.
