# A.S.I.A

**AI Support & Insight Analytics System**

A.S.I.A is a local Vietnamese e-commerce support demo built with FastAPI and
React. v0.1.1 proves four customer-support flows with deterministic behavior
and synthetic data. The current development milestone is **v0.2.0:
Evidence-Grounded Policy Assistant**; its scope, evaluation contract, and target
metrics are frozen before feature implementation.

> **Demo-ready is not production-ready.** The repository has no authentication,
> tenant isolation, production database, cloud deployment, or real customer
> data. The complete product contract and v0.2 boundaries live in
> [`docs/demo-scope.md`](docs/demo-scope.md).

## What the demo proves

| Flow | Behavior | Safety boundary |
| --- | --- | --- |
| Policy support | Answers Vietnamese shipping, return, refund, and warranty questions with citations from trusted Markdown | Missing evidence returns insufficient context, not an invented answer |
| Order lookup | Looks up synthetic orders for the fixed demo customer | Returns allowlisted fields only; unknown and non-owned orders are indistinguishable |
| Ticket support | Drafts a pending support action in chat | A separate explicit confirmation creates exactly one ticket per action |
| Admin overview | Shows message, ticket, intent, sentiment, and tool counts | Exposes aggregate counters only, without message or customer content |

The current implementation uses deterministic providers so behavior is
repeatable. v0.2 adds local policy retrieval and optional grounded generation
behind the same contracts and guardrails. The optional LLM analyzer is deferred
to v0.2.1.

## Technology

- Python 3.10+, FastAPI, Pydantic, Pytest, HTTPX, and Ruff
- React 19, TypeScript, Vite, Vitest, and Playwright
- Trusted Markdown policy documents and validated synthetic JSON fixtures
- Process-local pending actions and counters; ignored local ticket storage

## Quick start

### Prerequisites

- Python 3.10 or newer
- Node.js `^22.12.0` LTS, selected by `.nvmrc`
- Node.js `^20.19.0` is also supported for compatibility
- npm

Create a Python virtual environment and activate it.

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

Then install the locked backend and frontend dependencies from the repository
root.

```bash
python -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
```

Check that the local environment satisfies the repository contract.

```bash
python scripts/dev.py doctor
```

Start the backend in one terminal:

```bash
python scripts/dev.py backend
```

Start the frontend in another terminal:

```bash
python scripts/dev.py frontend
```

Open `http://127.0.0.1:5173`. API documentation is available at
`http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/redoc`.

## Development loop

Run project commands from the repository root.

| Command | Purpose |
| --- | --- |
| `python scripts/dev.py doctor` | Validate runtimes, locked dependencies, imports, frontend setup, local storage, and environment configuration |
| `python scripts/dev.py backend` | Start the FastAPI development server on port 8000 |
| `python scripts/dev.py frontend` | Start the Vite development server on port 5173 |
| `python scripts/dev.py reset-demo` | Restore ignored ticket state from the immutable synthetic seed |
| `python scripts/dev.py test` | Run backend and frontend unit/component tests |
| `python scripts/dev.py eval` | Measure the frozen deterministic v0.1 baseline |
| `python scripts/dev.py eval --suite v0.2` | Validate the frozen v0.2 datasets and contract; feature metrics activate in their implementation phases |
| `python scripts/dev.py verify` | Run the full pre-commit verification gate |
| `python scripts/dev.py verify --security` | Add a vulnerability audit of locked Python dependencies |

`verify` covers Python lint and formatting, backend and frontend tests, baseline
drift, TypeScript checks, the production frontend build, fixture/runtime
hygiene, obvious secret assignments, and Git whitespace errors. CI runs the
security variant from clean checkouts; local `verify` is the fastest complete
feedback loop.

Run browser E2E coverage for the four demo flows with:

```bash
cd frontend
npx playwright install chromium
npm run e2e
```

Playwright starts or reuses the local backend and frontend servers configured
in `frontend/playwright.config.ts`.

### Evaluation baselines

`eval/baseline.v0.1.json` is the frozen deterministic reference. Known misses
remain visible so future providers must demonstrate a real improvement instead
of moving the goalposts. `eval/baseline.v0.2.target.json` records the v0.2
targets before implementation. The v0.2 suite currently validates 86 versioned
cases, exact policy provenance, routing precedence, and cross-platform dataset
hashes without pretending unimplemented feature metrics exist.

Metric definitions, datasets, and baseline rules are documented in
[`eval/README.md`](eval/README.md).

### Updating dependencies

Direct Python dependencies belong in `backend/requirements.in`; the generated
`backend/requirements.txt` is the fully pinned install lock. Regenerate it only
for an intentional dependency change:

```bash
python -m pip install pip-tools
python -m piptools compile --allow-unsafe --strip-extras backend/requirements.in -o backend/requirements.txt
python -m piptools sync backend/requirements.txt
python -m pip check
```

Frontend dependencies are locked by `frontend/package-lock.json`; use `npm ci`
for reproducible installation. Review lockfile changes together with a complete
verification result.

## Demo walkthrough

Start both servers, open the frontend, and use these scenarios.

| Scenario | Vietnamese message or action | Expected result |
| --- | --- | --- |
| Grounded policy | `Chính sách đổi trả áp dụng trong bao lâu?` | Answer from the return policy with title, source, and section citation |
| Unsupported policy | `Cửa hàng có chương trình tích điểm không?` | Insufficient-context response with no citations |
| Owned order | `Tra cứu đơn hàng ASIA-1001 giúp tôi` | Compact order summary containing safe fields only |
| Protected order | Look up `ASIA-9999` or an unknown ID | The same generic not-found response in both cases |
| Ticket confirmation | `Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi` | Pending action first; confirm creates one ticket, cancel creates none |
| Admin overview | Open the admin panel after the previous steps | Aggregate intent, sentiment, message, ticket, and tool counts update without exposing content |

`ASIA-1001` and `ASIA-1002` belong to the fixed synthetic customer
`demo-customer-001`. `ASIA-9999` is a non-owned safety fixture. Repeating a
successful ticket confirmation returns the original ticket instead of creating
a duplicate.

To start the walkthrough again with clean local ticket state, run:

```bash
python scripts/dev.py reset-demo
```

This command writes only to the ignored `var/` directory. It does not modify
repository fixtures or evaluation baselines.

## API quick reference

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness and API version |
| `POST` | `/api/chat` | Vietnamese support interaction |
| `POST` | `/api/actions/{action_id}/confirm` | Confirm or cancel one pending action |
| `GET` | `/api/admin/overview` | Aggregate non-PII counters |

`POST /api/chat` keeps this stable response envelope:

```text
assistant_message | intent | sentiment | citations | tool_events | pending_action
```

The public intent and sentiment labels, tool semantics, safe order fields, and
acceptance rules are defined in [`docs/demo-scope.md`](docs/demo-scope.md).

## Design boundaries

- Repository data is synthetic. Files under `data/fixtures/` are immutable;
  local runtime writes belong under the ignored `var/` directory.
- `docs/policies/*.md` is the only trusted policy corpus. Supported claims need
  exact evidence; missing evidence produces an insufficient-context response.
- Order access is restricted to `demo-customer-001`, and responses expose only
  the safe-field allowlist.
- Chat may propose a ticket but cannot create one. Ticket writes remain behind
  the confirmation endpoint and are idempotent per action ID.
- Analyzer, policy, order, and ticket capabilities use narrow provider
  boundaries so implementations can change without widening API authority.

These are summaries, not parallel specifications. The scope document owns the
behavioral contract, while accepted technical decisions and their rationale
live under [`docs/decisions/`](docs/decisions/README.md).

## Repository map

| Path | Responsibility |
| --- | --- |
| [`backend/`](backend/) | FastAPI application, provider boundaries, services, and backend tests |
| [`frontend/`](frontend/) | React demo UI, component tests, and Playwright flows |
| [`docs/demo-scope.md`](docs/demo-scope.md) | Current milestone, product contract, scope boundaries, and safety invariants |
| [`docs/decisions/`](docs/decisions/README.md) | Architecture Decision Records |
| [`docs/dev-workflow.md`](docs/dev-workflow.md) | Branching, commit, verification, and integration workflow |
| [`docs/policies/`](docs/policies/) | Trusted synthetic policy corpus |
| [`eval/`](eval/README.md) | Versioned Vietnamese cases, frozen baseline, and target metrics |
| [`data/fixtures/`](data/fixtures/) | Immutable synthetic repository fixtures |
| `var/` | Ignored local runtime state |
| [`scripts/dev.py`](scripts/dev.py) | Common development and verification entry point |
| [`AGENTS.md`](AGENTS.md) | Operating instructions for coding agents |

## Current limitations

- Intent, sentiment, and policy retrieval are deterministic and keyword-based.
- The demo represents one fixed synthetic customer with no authentication or
  tenant isolation.
- Conversations, pending actions, and aggregate counters are process-local.
- Confirmed tickets use an ignored local JSON file, not production storage.
- There is no hosted LLM, vector database, PostgreSQL, queue, cache, Docker
  setup, cloud deployment, or real commerce integration.
- The frontend targets a local demo API and is not a production support client.

## v0.2 direction

The v0.2 scope, metric definitions, policy corpus, and 86 evaluation cases are
now frozen. The next engineering decision is to select one concrete grounded
generation provider through an ADR, then add its validated offline-first
runtime boundary.

Implementation can then move into local H2 evidence retrieval, followed by
policy-only grounded generation and application-owned citations. Release work
will finish by exercising the existing safety invariants, deterministic mode,
security checks, and four original E2E flows. These steps do not introduce new
product flows or broaden model authority.

Authentication, deployment, multi-tenant behavior, production storage, vector
infrastructure, external embeddings, real commerce data, model-controlled write
actions, and UI expansion remain out of scope. The LLM analyzer is a possible
v0.2.1 milestone, not a v0.2.0 release dependency. Exact product boundaries
live in [`docs/demo-scope.md`](docs/demo-scope.md); evaluation gates live in
[`eval/baseline.v0.2.target.json`](eval/baseline.v0.2.target.json) and
[`eval/README.md`](eval/README.md).
