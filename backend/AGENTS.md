# Backend Instructions

These instructions apply to all files under `backend/`.

## Purpose

The backend preserves the deterministic API contract while implementing the
`v0.2.0: Evidence-Grounded Policy Assistant` milestone. Read
`../docs/demo-scope.md` and `../eval/README.md` before changing behavior.

## Architecture

- `app/main.py`: FastAPI construction, middleware, and HTTP route orchestration.
- `app/config.py`: typed provider settings and conditional startup validation.
- `app/schemas.py`: public request and response models.
- `app/intent.py`: deterministic Vietnamese intent and sentiment analysis.
- `app/order_service.py`: fixed-customer lookup and safe order response shaping.
- `app/policy_search.py`: keyword search over allowlisted Markdown sections.
- `app/providers/`: narrow analyzer, policy, order, ticket, and async response
  generation contracts plus their reviewed adapters and factory.
- `app/state.py`: in-memory actions and counters plus ticket orchestration.
- `app/storage.py`: validated JSON loading and atomic ticket writes.
- `app/ticket_service.py`: pending actions and idempotent ticket confirmation.
- `tests/`: API contract and safety tests.
- `../eval/`: versioned JSONL behavior cases and deterministic baseline.
- `../data/fixtures/`: immutable synthetic JSON fixtures.
- `../var/`: ignored local runtime state.

Keep route handlers thin. Business rules belong in dedicated services or
`state.py`, not directly in HTTP handlers.

## API Invariants

- Preserve the response envelope documented in `docs/demo-scope.md`.
- The chat response has exactly `assistant_message`, `intent`, `sentiment`,
  `citations`, `tool_events`, and `pending_action`.
- `ChatRequest` accepts only `message`; do not expose reserved or ignored
  session fields before server-side conversation persistence exists.
- Use Pydantic models for public request and response data.
- Validate and trim user input at the API boundary.
- Return the same response for unknown and non-owned order IDs.
- Never add owner IDs, addresses, contact details, payment data, or internal
  notes to `OrderSummary`.
- Policy responses without evidence must contain no citations.
- Policy citations contain the Markdown title, repository-relative source, and
  exact H2 section.
- Local retrieval is the only supported policy evidence source. External
  embeddings and network retrieval are out of scope.
- The application builds citations from retrieved evidence. Never trust source,
  title, section, or evidence IDs emitted by a model.
- An external generator may return policy answer text only and may run only
  after sufficient allowlisted evidence exists.
- External provider input is limited to a redacted policy query, allowlisted
  evidence text, and generation instructions.
- Never send order results, ownership data, ticket payloads, pending actions,
  admin state, conversation history, or raw logs to an external provider.
- Chat may call `draft_ticket` but must never execute or persist a ticket.
- The chat route may access only `ChatProviders`; that bundle contains no
  ticket write capability.
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
Do not add PostgreSQL, migrations, background workers, external embeddings,
vector databases, or services beyond the one reviewed policy generator in this
milestone.

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
- deterministic and fake implementations passing the same provider contracts;
- provider replacement preserving the public chat response envelope.
- v0.2 dataset schemas, hashes, metric contracts, and v0.1 baseline immutability;
- local retrieval provenance, sufficiency, and refusal behavior;
- no-evidence no-call, external-data egress, redaction, timeout, malformed
  output, authentication, cancellation, and grounded fallback behavior;
- application-owned citation coverage and validity.

Run:

```bash
python scripts/dev.py test
python scripts/dev.py eval
python scripts/dev.py eval --suite v0.2
```

For a backend-only iteration, run `python -m pytest backend/tests` from the
repository root. See [`eval/README.md`](../eval/README.md) for metric
definitions. Run `python scripts/dev.py verify` before committing.

Tests must construct fresh state with a temporary ticket file and must not
depend on execution order.

## Style

- Target Python 3.10 or newer.
- Prefer small typed functions and explicit enums over unstructured strings.
- Keep user-facing Vietnamese natural and correctly accented.
- Keep code and identifiers in English.
- Avoid broad `Any` types in domain state.
- Do not log request bodies or action payloads.
- Do not log raw provider prompts or responses by default. Internal telemetry is
  limited to provider/model identifiers, prompt version, latency, evidence IDs,
  fallback reason, and sanitized error category.
- Add dependencies only when the standard library and current stack are
  insufficient.
- Declare direct dependencies in `requirements.in`. Regenerate the fully pinned
  `requirements.txt` with the documented pip-tools command; do not edit the
  lock by hand.
- Install backend dependencies only from `requirements.txt`, then run
  `python -m pip check`.
