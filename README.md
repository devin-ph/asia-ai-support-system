# A.S.I.A

**Agent Safety & Integrity Assessment**

> A Vietnamese benchmark and reference design for customer-support agents that
> must cite, refuse, and never act without confirmation.

A.S.I.A is moving from a support demo to a safety benchmark. The current
release candidate, **v0.2.0: Evidence-Grounded Policy Assistant**, ships the
**Reference System**: a local Vietnamese e-commerce support demo built with
FastAPI and React, with four flows, deterministic guardrails, and synthetic
data. The planned **v0.3.0** milestone measures that least-authority design
against a tool-calling Baseline Agent across several pinned models. See
[v0.3 direction](#v03-direction). Scope, evaluation contracts, and target
metrics are frozen before each milestone's implementation.

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

The public policy flow now uses measured local H2 retrieval, grounded template
generation by default, and application-owned citations. The optional OpenAI
generator may select complete lines or paragraphs from retrieved evidence; the
application accepts only full verbatim evidence units, renders the fixed answer
wrapper, and falls back to the deterministic template for any invalid output.
Retrieval, citations, routing, and all write guardrails remain
application-controlled.
This safety boundary does not change the public API. The optional LLM analyzer
is deferred to v0.3.0.

## Technology

- Python 3.12+, FastAPI, Pydantic, Pytest, HTTPX, and Ruff
- OpenAI Python SDK 3 for the optional Responses API adapter
- React 19, TypeScript 7, Vite 8, Vitest 5, MSW 3, and Playwright
- Trusted Markdown policy documents and validated synthetic JSON fixtures
- Process-local pending actions and counters; ignored local ticket storage

## Quick start

### Prerequisites

- Python 3.12 or newer (CI covers 3.12 and 3.14)
- Node.js 26 LTS, selected by `.nvmrc`
- Node.js `^22.22.2` and `^24.15.0` LTS are also supported (CI covers 22 and 26)
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

### Response generator configuration

Template generation is the default and needs neither `.env`, an API key, nor
network access. To validate the optional OpenAI runtime locally, copy
`.env.example` to the ignored `.env` file and set:

```dotenv
ASIA_RESPONSE_GENERATOR=openai
ASIA_LLM_API_KEY=<local-secret>
ASIA_LLM_MODEL=gpt-5.4-mini-2026-03-17
ASIA_LLM_TIMEOUT_SECONDS=15
```

`doctor` validates only the settings required by the selected generator,
enforces a timeout greater than 0 and at most 120 seconds, and never prints the
key. Process environment values take precedence over `.env`. The policy route
calls the selected generator only after sufficient local evidence exists;
template mode remains fully deterministic and offline. Local experiments may
override `ASIA_LLM_MODEL`, but only the pinned
`gpt-5.4-mini-2026-03-17` snapshot is eligible for the curated v0.2 reference.

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
| `python scripts/dev.py eval --suite v0.2` | Run frozen v0.2 retrieval, groundedness, citation, and routing gates offline |
| `python scripts/dev.py eval --suite v0.2 --live` | Explicitly run the configured external generator and write an ignored review artifact |
| `python scripts/dev.py eval --suite v0.2 --curate-reference <live-result>` | Validate a human-scored live run and write the fixed release reference |
| `python scripts/dev.py eval --suite v0.2 --require-reference` | Fail unless the Git-tracked reference is current and its human review is complete |
| `python scripts/dev.py verify` | Run the full pre-commit verification gate |
| `python scripts/dev.py verify --security` | Add vulnerability audits of the locked Python and npm dependency graphs |
| `python scripts/dev.py verify --release` | Run the release-evidence sub-gate: security audit, tracked reference, `main`, and clean tree |

`verify` covers Python lint and formatting, backend and frontend tests, the
frozen v0.1 regression, v0.2 offline gates, TypeScript checks, the production
frontend build, fixture/runtime hygiene, obvious secret assignments, and Git
whitespace errors. It is a pre-commit/PR gate and deliberately does not claim
tag readiness. `verify --release` is the release-evidence sub-gate: it also runs
the Python and npm dependency audits and fails until the pinned-model reference is
human-reviewed, tracked by Git, current on `main`, and the tree is clean. It
does not run `doctor` or browser E2E; those remain separate final-sequence
commands.

CI uses template mode, makes no external-generator API call, and needs no
provider credential. CI setup still uses ordinary network access to download
locked Python/npm packages and Playwright Chromium; the dependency audit may
also access package/advisory metadata.

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
targets before implementation. The v0.2 suite validates 86 versioned cases,
exact policy provenance, routing precedence, cross-platform dataset hashes,
retrieval, automated groundedness, and application-owned citations. The final
grounded-response metric remains pending until an external reference run is
scored with the documented human rubric.

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

Start both servers, open the frontend, and use this short release walkthrough.

| Proof | Message, action, or command | Expected result |
| --- | --- | --- |
| Retrieval beyond v0.1 keywords | `Chính sách giao hàng cho biết dữ liệu hành trình được tổng hợp từ đâu?` | Local retrieval finds `Theo dõi hành trình`; the frozen keyword search does not |
| Unsupported policy | `Có chính sách giao nhanh không?` | Insufficient context, no citation, and no generator call |
| Grounded failure fallback | `python -m pytest backend/tests/test_grounded_policy.py -k "safe_fallback and timeout"` | Forced timeout returns the evidence template and trusted citation |
| LLM-isolated order lookup | `Tra cứu đơn hàng ASIA-1001 giúp tôi` | Safe order summary; the generator is not called; admin counts update |
| Confirmation guardrail | `Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi` | Cancel creates none; explicit confirmation creates exactly one ticket |

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

The product milestone/release is `v0.2.0`. The health response, FastAPI
metadata, and frontend package retain API/package version `0.1`/`0.1.0`
because v0.2 preserves the existing public routes, envelope, and labels; those
values are contract versions, not the milestone status.

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
| [`docs/releases/`](docs/releases/v0.2.0.md) | Release evidence, invariant mapping, gates, and known limitations |
| [`docs/dev-workflow.md`](docs/dev-workflow.md) | Branching, commit, verification, and integration workflow |
| [`docs/policies/`](docs/policies/) | Trusted synthetic policy corpus |
| [`eval/`](eval/README.md) | Versioned Vietnamese cases, frozen baseline, and target metrics |
| [`data/fixtures/`](data/fixtures/) | Immutable synthetic repository fixtures |
| `var/` | Ignored local runtime state |
| [`scripts/dev.py`](scripts/dev.py) | Common development and verification entry point |
| [`AGENTS.md`](AGENTS.md) | Operating instructions for coding agents |

## Current limitations

- Intent and sentiment remain deterministic and keyword-based. Grounded policy
  generation is single-turn and uses only the top local evidence section.
- The demo represents one fixed synthetic customer with no authentication or
  tenant isolation.
- Conversations, pending actions, and aggregate counters are process-local.
- Confirmed tickets use an ignored local JSON file, not production storage.
- External generation requires an explicitly configured API key and network;
  no curated external-model reference is committed until the live human review
  is complete. There is no vector database, PostgreSQL, queue, cache, Docker
  setup, cloud deployment, or real commerce integration.
- The frontend targets a local demo API and is not a production support client.

## v0.2 direction

The v0.2 scope, metric definitions, policy corpus, and 86 evaluation cases are
now frozen. [ADR-006](docs/decisions/006-local-h2-policy-retrieval.md) records
the local retrieval decision, while
[ADR-005](docs/decisions/005-openai-responses-for-grounded-generation.md)
selects the OpenAI Responses API as the single optional external generator.
Its async runtime is integrated while template generation remains the offline
default.

Local H2 retrieval, grounded template generation, redaction, no-evidence
no-call behavior, safe provider fallback, and application-owned citations now
pass their offline gates. A November 2026 maintenance pass refreshed the
toolchain and dependencies (Python 3.12+, Node 22/24/26 LTS, OpenAI SDK 3,
Vite 8, TypeScript 7) and cleared both dependency audits, so every final gate
must be rerun on the release SHA. The remaining v0.2 gate is a genuine
external reference run with complete human review, followed by review and a
clean release tree. These steps do not introduce new product flows or broaden
model authority.

Candidate gate status and the executable invariant map live in
[`docs/releases/v0.2.0.md`](docs/releases/v0.2.0.md); that record must show no
pending required gate before tagging.

Authentication, deployment, multi-tenant behavior, production storage, vector
infrastructure, external embeddings, real commerce data, model-controlled write
actions, and UI expansion remain out of scope. The LLM analyzer is part of the
planned v0.3.0 milestone, not a v0.2.0 release dependency. Exact product
boundaries live in [`docs/demo-scope.md`](docs/demo-scope.md); evaluation gates
live in [`eval/baseline.v0.2.target.json`](eval/baseline.v0.2.target.json) and
[`eval/README.md`](eval/README.md).

## v0.3 direction

v0.3.0 starts after the `v0.2.0` tag. It turns the project into a Vietnamese
support-agent safety benchmark.
[ADR-007](docs/decisions/007-benchmark-over-support-product.md) records why the
benchmark replaced further support-product growth.

- **What is scored:** configurations under test, each one architecture paired
  with one pinned model. The Reference System, where the model only proposes,
  is compared with a Baseline Agent that calls tools directly under the
  strongest defensive prompt available.
- **Models:** two local open models through an OpenAI-compatible endpoint, and
  one pinned API model chosen by a small pilot
  ([ADR-008](docs/decisions/008-openai-compatible-adapter-for-local-models.md)).
- **Cases:** about 300 synthetic Vietnamese cases covering grounded answers,
  refusals, direct and indirect injection, cross-customer probing, and
  unauthorized actions. About 30% are written without diacritics, in teencode,
  or in Vietnamese-English code-switching.
- **Scoring:** violation rate per invariant, measured by deterministic oracles
  with no model as judge, reported next to task success and over-refusal.
- **Gate:** zero Reference System violations across every attack case and
  every model.
- **Publication:** a static benchmark report, plus a template-mode playground.

An agent authorization gateway is recorded as proposed future work in
[ADR-009](docs/decisions/009-agent-authorization-gateway-future-work.md).
The full v0.3.0 contract lives in
[`docs/demo-scope.md`](docs/demo-scope.md#planned-milestone-v030-vietnamese-support-agent-safety-benchmark),
and terminology lives in [`GLOSSARY.md`](GLOSSARY.md).
