# Backend Instructions

These instructions apply to all files under `backend/`.

## Purpose

The backend implements the deterministic API contract for the
`v0.1: Runnable Vertical Slice` milestone. Read
`../docs/demo-scope.md` before changing behavior.

## Architecture

- `app/main.py`: FastAPI construction, middleware, and HTTP route orchestration.
- `app/schemas.py`: public request and response models.
- `app/intent.py`: deterministic Vietnamese intent and sentiment analysis.
- `app/order_service.py`: fixed-customer lookup and safe order response shaping.
- `app/policy_search.py`: keyword search over allowlisted Markdown sections.
- `app/state.py`: in-memory actions and counters plus ticket orchestration.
- `app/storage.py`: validated JSON loading and atomic ticket writes.
- `app/ticket_service.py`: pending actions and idempotent ticket confirmation.
- `tests/`: API contract and safety tests.
- `../data/fixtures/`: immutable synthetic JSON fixtures.
- `../var/`: ignored local runtime state.

Keep route handlers thin. Business rules belong in dedicated services or
`state.py`, not directly in HTTP handlers.

## API Invariants

- Preserve the response envelope documented in `docs/demo-scope.md`.
- The chat response has exactly `assistant_message`, `intent`, `sentiment`,
  `citations`, `tool_events`, and `pending_action`.
- Use Pydantic models for public request and response data.
- Validate and trim user input at the API boundary.
- Return the same response for unknown and non-owned order IDs.
- Never add owner IDs, addresses, contact details, payment data, or internal
  notes to `OrderSummary`.
- Policy responses without evidence must contain no citations.
- Policy citations contain the Markdown title, repository-relative source, and
  exact H2 section.
- Chat may call `draft_ticket` but must never execute or persist a ticket.
- Ticket creation is allowed only through the confirmation endpoint.
- Repeated confirmation of one action must return the original result.
- Admin responses contain aggregate counters only.

## State and Concurrency

Pending actions, message counters, and tool counters are process-local and reset
on restart. Confirmed tickets persist in the ignored
`var/demo_tickets.json` runtime store. Mutations
that implement confirmation idempotency and ticket writes must be guarded so
two concurrent confirmations cannot create two tickets in one process.

Write JSON through `storage.py`; tests must inject a temporary ticket path.
Never write runtime state back into `data/fixtures/`.
Do not add PostgreSQL, migrations, background workers, or external services in
this milestone.

## Synthetic Data

- Use only fixtures committed under `data/fixtures/`.
- Treat `docs/policies/*.md` as the only trusted policy corpus.
- The fixed customer is `demo-customer-001`.
- Include at least one non-owned order only for ownership-denial tests.
- Never expose the non-owned record through an API response.
- Keep `data/fixtures/demo_tickets.seed.json` initialized as an empty JSON list
  in Git.
- Keep `var/` ignored; `var/demo_tickets.json` is generated locally on the
  first confirmed ticket.
- Do not add realistic names, addresses, phone numbers, emails, or payment
  details.

## Tests

Every behavior change must include or update tests. At minimum, preserve tests
for:

- health and request validation;
- all supported Vietnamese intent and sentiment labels, including text with
  diacritics;
- grounded policy citations and insufficient context;
- all allowlisted policy topics and exact citation metadata;
- owned, unknown, and non-owned order lookup;
- ticket draft, persistence, confirmation, cancellation, and repeated
  confirmation;
- admin message, intent, sentiment, ticket, and tool counters.

Run:

```bash
python scripts/dev.py test
```

Tests must construct fresh state with a temporary ticket file and must not
depend on execution order.

## Style

- Target Python 3.10 or newer.
- Prefer small typed functions and explicit enums over unstructured strings.
- Keep user-facing Vietnamese natural and correctly accented.
- Keep code and identifiers in English.
- Avoid broad `Any` types in domain state.
- Do not log request bodies or action payloads.
- Add dependencies only when the standard library and current stack are
  insufficient.
