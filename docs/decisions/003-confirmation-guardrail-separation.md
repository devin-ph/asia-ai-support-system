# ADR-003: Confirmation guardrail separation

## Status

Accepted

## Context

In many chatbot systems, the model can directly create tickets, send emails,
or trigger other irreversible actions within the same request that drafted
them. This means a single prompt injection or model hallucination can cause
real-world side effects.

## Decision

**Separate proposal from execution.** The chat handler may only propose a
`create_ticket` action and return it as `pending_action` with status `pending`.
A separate confirmation endpoint (`POST /api/actions/{action_id}/confirm`)
owns execution.

The guardrail also enforces:

- Explicit user confirmation before ticket creation.
- Cancellation without side effects.
- One ticket per action ID (idempotent confirmation).
- The same result for repeated confirmation.
- No confirmation of an already cancelled action.

## Consequences

- The chat route has no access to the ticket write provider.
- A future LLM may help draft an action, but it must not receive direct
  authority to execute it.
- Frontend must show both confirm and cancel options and disable buttons while
  a request is in-flight.
- This separation is a **non-negotiable invariant** that must survive across
  milestones.
