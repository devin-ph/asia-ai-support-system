# A.S.I.A v0.1 Demo Scope

## Milestone

**v0.1: Runnable Vertical Slice**

A.S.I.A is a local demonstration of a Vietnamese e-commerce customer-support
system. The milestone proves the end-to-end product contract with deterministic
logic and synthetic data before introducing an LLM, vector database, external
services, or persistent storage.

## Demo Identity

The application represents one fixed synthetic customer:

- Customer ID: `CUS-DEMO-001`
- Display name: `Khách hàng Demo`
- All orders, policies, actions, and tickets in this milestone are synthetic.

The API must never return data from an order that is not owned by
`CUS-DEMO-001`.

## Required Flows

### 1. Grounded policy answers

The customer can ask Vietnamese questions about the small policy corpus
included in the repository.

Acceptance criteria:

- Vietnamese text with or without diacritics is understood for supported topics.
- A supported answer is derived from a matching demo policy record.
- Every supported answer includes at least one citation containing a source and
  an evidence snippet.
- If no matching evidence exists, the response explicitly says that context is
  insufficient and returns no citations.
- The system must not invent policy details.

### 2. Synthetic order lookup

The customer can look up an order by a demo order ID.

Acceptance criteria:

- Only safe fields are returned: order ID, status, carrier, estimated delivery,
  item count, and last update time.
- Address, phone, email, payment information, and internal owner identifiers are
  never returned.
- Ownership is checked against `CUS-DEMO-001` before building the response.
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

- `reply`
- `intent`
- `sentiment`
- `citations`
- `order` when a safe owned-order lookup succeeds
- `actions`
- `session_id`

## Demo Tools

The deterministic backend models three local tools:

- `policy_search`
- `order_lookup`
- `ticket_create`

A tool count is incremented only when the corresponding lookup or confirmed
write is actually performed. Merely proposing a ticket does not count as a
write.

## Technical Boundaries

Included:

- FastAPI and Pydantic
- In-memory state that resets on restart
- Deterministic intent and sentiment classification
- Repository-owned synthetic policy and order fixtures
- Automated API tests
- Local CORS configuration for the development frontend

Explicitly excluded:

- OpenAI or any other hosted model
- LangGraph, Qdrant, embeddings, or retrieval infrastructure
- Authentication and production authorization
- A database, queue, cache, Docker, or cloud deployment
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
7. Secrets and credentials are never committed.

## Definition of Done

The milestone is done when:

- All four required flows work through the API.
- `python scripts/dev.py doctor` passes once backend and frontend prerequisites
  are installed and present.
- `python scripts/dev.py test` passes.
- OpenAPI starts locally with `python scripts/dev.py backend`.
- Tests cover policy grounding, insufficient context, order ownership and safe
  fields, ticket confirmation idempotency, cancellation, and admin counters.
- README instructions and response examples match the implemented API.

