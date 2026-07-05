# ADR-004: Synthetic data only in v0.1

## Status

Accepted

## Context

The demo needs realistic-looking data to exercise the four flows (policy,
orders, tickets, admin). Using real or semi-real data introduces PII risk,
legal exposure, and makes fixtures unsuitable for public repositories.

## Decision

All data in v0.1 is **synthetic by construction**:

- `data/fixtures/demo_orders.json` — fabricated order records with no real
  names, addresses, phone numbers, emails, or payment details.
- `data/fixtures/demo_tickets.seed.json` — empty seed for runtime tickets.
- `docs/policies/*.md` — simplified Vietnamese policy documents written for
  the demo, not copied from any real store.
- `demo-customer-001` — a fixed synthetic identity, not a real person.
- `var/demo_tickets.json` — locally generated runtime state, Git-ignored.

## Consequences

- No fixture should ever contain realistic PII, even as placeholder text.
- Tests write tickets only to temporary files, never to repository fixtures.
- The `verify` command scans for obvious credential assignments.
- This is a **non-negotiable invariant**: demo data must remain synthetic.
