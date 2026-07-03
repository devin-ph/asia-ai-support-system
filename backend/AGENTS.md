# Backend Instructions

These instructions apply to all files under `backend/`.

## Purpose

The backend implements the deterministic API contract for the
`v0.1: Runnable Vertical Slice` milestone. Read
`../docs/demo-scope.md` before changing behavior.

## Architecture

- `app/main.py`: FastAPI construction, middleware, and HTTP route orchestration.
- `app/schemas.py`: public request and response models.
- `app/support.py`: deterministic text normalization, intent, sentiment, policy,
  and order logic.
- `app/state.py`: in-memory actions, tickets, and aggregate counters.
- `app/demo_data.py`: validated loader for repository-owned synthetic fixtures.
- `tests/`: API contract and safety tests.
- `../data/`: synthetic policy and order fixtures.

Keep route handlers thin. Business rules belong in `support.py` or `state.py`,
not directly in HTTP handlers.

## API Invariants

- Preserve the response envelope documented in `docs/demo-scope.md`.
- Use Pydantic models for public request and response data.
- Validate and trim user input at the API boundary.
- Return the same response for unknown and non-owned order IDs.
- Never add owner IDs, addresses, contact details, payment data, or internal
  notes to `OrderSummary`.
- Policy responses without evidence must contain no citations.
- Chat may draft an action but must never execute a write.
- Ticket creation is allowed only through the confirmation endpoint.
- Repeated confirmation of one action must return the original result.
- Admin responses contain aggregate counters only.

## State and Concurrency

State is intentionally process-local and resets on restart. Mutations that
implement confirmation idempotency must be guarded so two concurrent
confirmations cannot create two tickets in one process.

Do not add persistence, background workers, or external services in this
milestone.

## Synthetic Data

- Use only fixtures committed under `data/`.
- The fixed customer is `CUS-DEMO-001`.
- Include at least one non-owned order only for ownership-denial tests.
- Never expose the non-owned record through an API response.
- Do not add realistic names, addresses, phone numbers, emails, or payment
  details.

## Tests

Every behavior change must include or update tests. At minimum, preserve tests
for:

- health and request validation;
- Vietnamese intent detection with diacritics;
- grounded policy citations and insufficient context;
- owned, unknown, and non-owned order lookup;
- ticket draft, confirmation, cancellation, and repeated confirmation;
- admin message, intent, sentiment, ticket, and tool counters.

Run:

```bash
python scripts/dev.py test
```

Tests must construct fresh in-memory state and must not depend on execution
order.

## Style

- Target Python 3.10 or newer.
- Prefer small typed functions and explicit enums over unstructured strings.
- Keep user-facing Vietnamese natural and correctly accented.
- Keep code and identifiers in English.
- Avoid broad `Any` types in domain state.
- Do not log request bodies or action payloads.
- Add dependencies only when the standard library and current stack are
  insufficient.

