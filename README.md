# A.S.I.A

**AI Support & Insight Analytics System**

A.S.I.A is a local Vietnamese e-commerce support demo. The current milestone,
**v0.1: Runnable Vertical Slice**, proves the product contract end to end with a
FastAPI backend, a minimal React interface, deterministic rules, and synthetic
data.

The demo deliberately uses no hosted model, vector database, production
database, or real customer data. Its purpose is to validate safe behavior and
clear integration boundaries before introducing external infrastructure.

> **Demo-ready ≠ Production-ready.**
> This repository is a local development demonstration. It has no
> authentication, no durable storage, no cloud deployment, and no real customer
> data. The code proves that the product contract, safety invariants, and
> integration seams work correctly before any of those concerns are added.
> See [Current limitations](#current-limitations) for the full list.

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
- Playwright browser E2E for the four demo flows
- Local Markdown policies and validated synthetic JSON storage
- Process-local actions and aggregate counters

## Run locally

### Prerequisites

- Python 3.10 or newer
- Node.js 22 LTS (recommended; selected by `.nvmrc`)
- Node.js `^20.19.0` remains supported for compatibility
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

If your Node version manager supports `.nvmrc`, select the repository default:

```bash
nvm use
```

The frontend enables npm's strict engine check, so unsupported Node majors fail
during installation instead of continuing with a warning.

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
their exact locked versions, application import, the frontend
lockfile/scripts/installed dependencies, writable local runtime storage, and
the current `.env` contract. If backend dependencies do not match the lock,
rerun `python -m pip install -r backend/requirements.txt`. If
`frontend/node_modules` is missing or incomplete, run `npm ci` inside
`frontend/`.

### Update backend dependencies

[`backend/requirements.in`](backend/requirements.in) contains the direct
backend and test dependencies. [`backend/requirements.txt`](backend/requirements.txt)
is the generated, fully pinned install lock; do not edit it by hand.

To intentionally update the lock:

```bash
python -m pip install pip-tools
python -m piptools compile --allow-unsafe --strip-extras backend/requirements.in -o backend/requirements.txt
python -m piptools sync backend/requirements.txt
python -m pip check
```

Review dependency updates together with the full verification result before
committing the regenerated lock.

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

Run the minimal browser E2E flow against real local backend and frontend
servers:

```bash
cd frontend
npx playwright install chromium
npm run e2e
```

Before committing or opening a pull request, run the full-project verification:

```bash
python scripts/dev.py verify
```

Run the dependency-security variant before release:

```bash
python scripts/dev.py verify --security
```

GitHub Actions repeats `doctor` and `verify` from a clean checkout using two
representative supported pairs: Python 3.10 with Node.js 20, and Python 3.12
with the default Node.js 22 LTS. CI invokes `verify --security`, which includes
`python -m pip_audit -r backend/requirements.txt` against the complete locked
Python dependency set. Local verification remains the fastest feedback loop;
CI is the independent reproducibility and vulnerability check for pull requests
and `main`.

To inspect the product-level deterministic baseline separately:

```bash
python scripts/dev.py eval
```

`eval` runs the versioned synthetic cases under [`eval/`](eval/README.md) and
reports intent accuracy, policy-section hit rate, insufficient-context
precision, order-ID extraction accuracy, and confirmation-guardrail pass rate.
Known misses remain visible; this is a benchmark, not a test that is expected
to score 100%.

`verify` runs Ruff lint and format checks for `backend/` and `scripts/`, backend
and frontend unit/component tests, checks the committed evaluation snapshot for drift, runs
frontend typecheck and production build, validates runtime/fixture Git hygiene,
scans candidate files for obvious credential assignments without printing
values, and checks staged and unstaged diffs for whitespace errors.
`verify --security` additionally audits the locked Python dependencies for known
vulnerabilities. Python static typechecking remains deferred to a later
milestone.

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
the full-stack “ready to commit / ready for PR” gate and additionally checks
Python lint and formatting, the baseline snapshot, frontend typecheck,
production build, and repository hygiene. This keeps the local test loop useful
without making it pay the cost of a frontend production build.

### Provider boundaries: narrow, replaceable seams

`backend/app/providers/` defines four capability-specific boundaries instead of
a generic agent framework:

| Boundary | Default implementation | Preserved behavior |
| --- | --- | --- |
| Analyzer | deterministic intent and sentiment rules | Public intent and sentiment enums |
| Policy | allowlisted keyword search | Grounded answer, exact citations, and safe fallback |
| Orders | synthetic fixture lookup | Ownership denial and safe-field allowlist |
| Tickets | guarded local ticket service | Draft, explicit confirmation, cancellation, and idempotency |

The chat route receives a `ChatProviders` bundle containing only analyzer,
policy, and order reads. Ticket providers remain behind `DemoState`: chat can
request a draft, but only the confirmation endpoint can reach
`resolve_action`. Replacing a read provider therefore does not alter the HTTP
request or response models and does not grant a model write authority.

`backend/tests/test_providers.py` runs the same contracts against deterministic
and fake implementations and verifies that swapping `ChatProviders` preserves
the stable response envelope. A future provider should be added to these
parameterized contracts before it is selected at runtime.

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

### Decision log

[`docs/decisions/`](docs/decisions/) contains lightweight Architecture Decision
Records (ADRs) that capture key technical choices and their rationale:

| ADR | Decision |
|-----|----------|
| [001](docs/decisions/001-deterministic-baseline-before-llm.md) | Prove safety with deterministic rules before adding any LLM |
| [002](docs/decisions/002-provider-boundaries-over-agent-framework.md) | Use narrow provider boundaries, not a generic agent framework |
| [003](docs/decisions/003-confirmation-guardrail-separation.md) | Separate action proposal from execution |
| [004](docs/decisions/004-synthetic-data-only-in-v01.md) | All v0.1 data must be synthetic by construction |

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

1. Implement an optional candidate provider behind the existing boundaries and
   run it against the committed deterministic baseline and shared contracts.
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
