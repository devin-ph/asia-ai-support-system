# A.S.I.A Demo Scope

## Milestone

Current scope: v0.1.1
Base product flows: v0.1

**v0.1: Runnable Vertical Slice**

A.S.I.A is a local demonstration of a Vietnamese e-commerce customer-support
system. The milestone proves the end-to-end product contract with deterministic
logic and synthetic data before introducing an LLM, vector database, external
services, or a production database.

## Demo Identity

The application represents one fixed synthetic customer:

- Customer ID: `demo-customer-001`
- Display name: `Khách hàng Demo`
- All orders, policies, actions, and tickets in this milestone are synthetic.

The API must never return data from an order that is not owned by
`demo-customer-001`.

## Required Flows

### 1. Grounded policy answers

The customer can ask Vietnamese questions about the small policy corpus
included in the repository.

Acceptance criteria:

- Vietnamese text with or without diacritics is understood for supported topics.
- A supported answer is derived from a matching demo policy record.
- Every supported answer includes at least one citation containing the policy
  title, repository-relative source, and exact section heading.
- If no matching evidence exists, the response explicitly says that context is
  insufficient and returns no citations.
- The system must not invent policy details.
- `docs/policies/*.md` is the only trusted policy corpus.

### 2. Synthetic order lookup

The customer can look up an order by a demo order ID.

Acceptance criteria:

- Only safe fields are returned: order ID, status, carrier, estimated delivery,
  item count, and last update time.
- Address, phone, email, payment information, and internal owner identifiers are
  never returned.
- Ownership is checked against `demo-customer-001` before building the
  response.
- Unknown and non-owned order IDs receive the same generic not-found response
  to avoid revealing whether another customer's order exists.
- If no order ID is supplied, the assistant asks for one and performs no lookup.

### 3. Ticket draft and explicit confirmation

The customer can ask for a support ticket.

Acceptance criteria:

- Chat may propose a `create_ticket` action, but it must not create a ticket.
- The proposed action is returned with status `pending` and a summary for review.
- A separate confirmation request is required to create the ticket.
- Cancellation never creates a ticket.
- Repeating a confirmation for the same action is idempotent and returns the
  original ticket ID without creating another ticket.
- Confirming an already cancelled action does not create a ticket.
- Confirmed tickets are stored in the ignored local runtime file
  `var/demo_tickets.json`; pending actions remain process-local and reset on
  restart.
- A fresh runtime store starts from the immutable
  `data/fixtures/demo_tickets.seed.json` fixture.
- `backend/app/ticket_service.py` owns the draft, decline, and idempotent
  confirmation lifecycle.

### 4. Admin overview

The local admin endpoint exposes aggregate, non-PII counters.

Acceptance criteria:

- Total messages and confirmed tickets are reported.
- Intent and sentiment counts are reported.
- Total tool calls and per-tool counts are reported.
- No message content, order ownership data, action payload, or ticket content is
  returned from the admin endpoint.

## API Contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness response and API version |
| `POST` | `/api/chat` | Deterministic Vietnamese support interaction |
| `POST` | `/api/actions/{action_id}/confirm` | Confirm or cancel one pending action |
| `GET` | `/api/admin/overview` | Aggregate demo counters |

`POST /api/chat` keeps one stable envelope containing:

- `assistant_message`
- `intent`
- `sentiment`
- `citations`
- `tool_events`
- `pending_action`

Safe order fields are returned only inside a completed `order_lookup` tool
event. Ticket requests populate `pending_action` but do not create a ticket.

## Demo Tools

The deterministic backend models three local tools:

- `policy_search`
- `order_lookup`
- `ticket_create`

A tool count is incremented only when the corresponding lookup or confirmed
write is actually performed. Merely proposing a ticket does not count as a
write.

## Deterministic Analysis Labels

`backend/app/intent.py` classifies every message without an LLM.

Supported intents:

- `order_lookup`
- `shipping_policy`
- `return_refund`
- `warranty`
- `ticket_request`
- `other`

Supported sentiments:

- `positive`
- `neutral`
- `negative`

Rules normalize Vietnamese diacritics and apply an explicit keyword priority.
These labels are part of the API and admin counter contract.

## Technical Boundaries

Included in v0.1:
- Deterministic intent and sentiment classification
- Keyword search over allowlisted policy sections
- Local JSON fixtures and runtime ticket storage
- Minimal React and TypeScript interface
- Backend/API tests

Added in v0.1.1:
- Provider contracts
- Eval baseline
- Frontend component tests
- GitHub Actions verify

Explicitly excluded:
- OpenAI or any other hosted model
- LangGraph, Qdrant, embeddings, or retrieval infrastructure
- Authentication and production authorization
- Server-side conversation history or session persistence
- PostgreSQL, migrations, a queue, cache, Docker, or cloud deployment
- Real commerce integrations, real customers, or real PII
- Production-grade multilingual NLU

## Safety Invariants

1. Repository fixtures contain synthetic data only.
2. Policy claims require matching repository evidence.
3. Order details require a fixed-customer ownership check.
4. Ticket creation happens only in the confirmation endpoint.
5. Confirmation is idempotent per action ID.
6. API and admin responses do not expose unsafe order fields or stored message
   content.
7. Tests write tickets only to temporary files, never to the repository fixture.
8. Runtime ticket writes never mutate files under `data/fixtures/`.
9. Secrets and credentials are never committed.
10. The chat route has no direct access to a ticket write provider.

## Definition of Done

The milestone is done when:

- All four required flows work through the API.
- `python scripts/dev.py doctor` confirms supported Python and Node versions,
  installed backend/frontend dependencies, importable application code, and
  writable local runtime storage.
- `python scripts/dev.py test` passes.
- `python scripts/dev.py eval` reports the committed deterministic baseline for
  intent, policy retrieval, order extraction, and ticket confirmation.
- `python scripts/dev.py verify` passes before a commit or pull request.
- OpenAPI starts locally with `python scripts/dev.py backend`.
- Tests cover policy grounding, insufficient context, order ownership and safe
  fields, ticket persistence, confirmation idempotency, cancellation, and admin
  counters.
- Shared provider contract tests pass for deterministic and fake
  implementations without changing the route response contract.
- Frontend tests cover chat rendering, citations, safe order summaries,
  confirmation/cancellation, admin refresh, and API error states.
- README instructions and response examples match the implemented API.

## v0.1.1: Reproducibility Hardening

The v0.1.1 maintenance scope does not change the four product flows. It makes
the existing demo reproducible from a clean clone and aligns local and
automated verification:

- Backend direct dependencies live in `backend/requirements.in`; the generated
  `backend/requirements.txt` pins the complete install set.
- `.env.example` is the repository-owned environment contract, even while the
  demo requires no environment variables.
- GitHub Actions installs from the committed Python and npm locks, then runs
  `doctor` and `verify` on representative Node.js 20/Python 3.10 and Node.js
  22/Python 3.12 pairs for every pull request and push to `main`.
- `doctor` validates supported runtimes, exact locked backend dependencies,
  frontend dependencies, application importability, environment configuration,
  and writable local runtime storage.
- `verify` enforces Ruff lint and format checks for Python under `backend/` and
  `scripts/`; Python static typechecking remains deferred.
- Runtime state remains ignored under `var/`; any mutation under the immutable
  `data/fixtures/` directory fails verification.
- A successful verification may report PR/tag readiness only when the working
  tree is clean.

## Status

| Capability | Status |
| --- | --- |
| Local demo | Included |
| Synthetic data | Included |
| Backend/API tests | Included |
| Frontend tests | v0.1.1 |
| Eval baseline | v0.1.1 |
| Real LLM | Excluded |
| Real database | Excluded |
| Production deployment | Excluded |
