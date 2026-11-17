# Backend Instructions

Applies to `backend/`. The contract lives in `../docs/demo-scope.md`, and this
file only adds backend-specific rules.

## Map

- `app/main.py`: FastAPI app and thin route handlers.
- `app/reference_system.py`: the Reference System. `handle(message)` runs one
  Turn: routing, tool events, counters, and Pending Action drafts.
- `app/config.py`: typed provider settings, validated at startup.
- `app/schemas.py`: public Pydantic request and response models.
- `app/intent.py`: deterministic Vietnamese intent and sentiment analyzer.
- `app/order_service.py`: fixed-customer lookup and safe-field shaping.
- `app/policy_retrieval.py`: allowlisted H2 corpus and local retrieval.
- `app/policy_search.py`: legacy keyword search kept only for the frozen v0.1
  baseline, plus the shared insufficient-context answer.
- `app/providers/`: analyzer, policy, order, ticket, and generation boundaries,
  plus the factory.
- `app/state.py`, `app/ticket_service.py`, `app/storage.py`: `UsageCounters`,
  pending actions, idempotent confirmation, and atomic ticket writes.

## Rules

- Keep handlers thin; business rules belong in `reference_system.py`, services,
  or `state.py`.
- The chat route only calls `ReferenceSystem.handle`. It is built from
  `ChatProviders`, a draft-only callable, and counters, with no ticket write or
  resolve capability. Tickets are written only by the confirmation endpoint.
- Build citations from retrieved evidence. Never trust source, section, or ID
  text returned by a model.
- Pin external endpoints in code. Ambient SDK variables such as
  `OPENAI_BASE_URL` must not redirect egress. Keep secrets out of `repr()`,
  logs, exceptions, and eval artifacts.
- Do not log request bodies, action payloads, or raw prompts and responses.
  Telemetry is limited to provider, model, prompt version, latency, evidence
  IDs, and sanitized error or fallback categories.
- Guard confirmation and ticket writes so that concurrent confirmations create
  one ticket. Write JSON only through `storage.py`, and never under
  `data/fixtures/`.

## Tests and style

- Every behavior change adds or updates tests. Tests use a temporary ticket
  path and must not depend on execution order.
- Python 3.12+, typed functions, and explicit enums. Identifiers in English,
  user-facing text in natural, accented Vietnamese.
- Declare direct dependencies in `requirements.in`. Regenerate
  `requirements.txt` with pip-tools, and never edit the lock by hand.
