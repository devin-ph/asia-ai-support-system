# ADR-009: Agent authorization gateway as future work

## Status

Proposed. Not part of v0.3.0.

## Context

The Reference System's guardrails could be generalized beyond this demo:
propose-then-confirm writes, idempotency per action, and narrow capability
bundles. One natural form is an MCP-style gateway that sits between any agent
and its tools. Several open-source and commercial gateways with human approval
and policy layers already exist. A new one adds value only if it can show
measured protection rather than assert it.

## Decision

Do not build a gateway in v0.3.0. Record it as the planned follow-up. If the
project pursues it, the gateway will:

- extract only the existing propose, confirm, and idempotency layer, and the
  capability scoping, as a small proxy for the Reference System's tools;
- be validated with the v0.3 attack cases, so the benchmark proves what the
  gateway blocks;
- stay out of enterprise gateway territory: no identity provider integration,
  no multi-tenant policy management, and no general agent framework.

## Consequences

- v0.3 keeps a bounded scope and a short timeline.
- Because the benchmark comes first, any future gateway already has its own
  test suite.
- Accepting this ADR later requires a scope amendment in
  `docs/demo-scope.md`.
