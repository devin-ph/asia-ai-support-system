# ADR-002: Provider boundaries over agent framework

## Status

Accepted

## Context

Many AI support systems use a generic agent framework (LangChain, LangGraph,
AutoGen) that gives a model broad tool access and lets it decide what to call.
This makes safety invariants hard to enforce because the model can reach any
tool at any time.

## Decision

Use **four narrow provider boundaries** instead of a generic agent:

| Boundary | Capability | Default |
|----------|-----------|---------|
| Analyzer | Intent + sentiment classification | Deterministic keyword rules |
| Policy | Grounded policy retrieval | Allowlisted keyword search |
| Orders | Safe order lookup | Synthetic fixture lookup |
| Tickets | Guarded ticket lifecycle | Local ticket service |

The chat route receives a `ChatProviders` bundle containing only analyzer,
policy, and order reads. Ticket write access is kept behind `DemoState` and
reachable only through the confirmation endpoint.

## Consequences

- Replacing a read provider (e.g., swapping keyword search for RAG) does not
  alter the HTTP response contract or grant write authority.
- Shared contract tests in `test_providers.py` run against deterministic and
  fake implementations and verify that swapping providers preserves the stable
  response envelope.
- A new provider type requires updating the provider contracts, not just
  plugging in a function.
