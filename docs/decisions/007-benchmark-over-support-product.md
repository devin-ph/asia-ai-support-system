# ADR-007: Benchmark over support product

## Status

Accepted for the planned v0.3.0 milestone.

## Context

Up to v0.2.0, A.S.I.A has been a Vietnamese e-commerce support demo. Support
chatbots are a crowded category, and growing this one into a real product would
mean authentication, tenancy, and production storage. That work weakens the
synthetic-data invariant and adds nothing to the project's actual thesis.

The project's distinctive work sits elsewhere: least-authority boundaries
between model and application, evaluation baselines that cannot be moved after
the fact, and measured Vietnamese behavior. Public agent-safety benchmarks
exist, but the ones reviewed are English-first and general-domain. None
combined Vietnamese, customer support, and unauthorized-action safety.

## Decision

- From v0.3.0, the primary deliverable is a Vietnamese support-agent safety
  benchmark. The existing support demo becomes its **Reference System**.
- The benchmark scores **configurations under test**, each an architecture
  paired with a pinned model. Comparing architectures with the model held
  fixed is what tests the least-authority thesis. Comparing models alone would
  yield only another model leaderboard.
- The comparison architecture is a **Baseline Agent** that calls tools
  directly and carries the strongest defensive instructions available. A weak
  baseline would make the result meaningless, so its prompt is versioned and
  must be a genuine best effort.
- The Baseline Agent exists only inside the evaluation harness, with temporary
  stores. ADR-002 and ADR-003 still govern the product runtime without
  exception.
- Safety is scored by deterministic oracles over observed effects, never by a
  model acting as judge. Every configuration also reports task success and
  over-refusal, so refusing everything cannot pass as safety.

## Considered options

- **Keep growing the support product** toward a usable multi-store system.
  Rejected: it turns the project into authentication and CRUD work and
  conflicts with the synthetic-data invariant.
- **Extract an agent authorization gateway now.** Deferred to future work in
  ADR-009. Several open-source gateways already exist. A new one is only
  credible once a benchmark can show what it blocks.
- **Change domain** (university rules, public procedures) and keep the chatbot
  shape. Rejected: it is the same RAG chatbot with a different corpus.

## Consequences

- v0.3 needs a Baseline Agent with tool calling. That is a scoped exception to
  the v0.2 rule against LLM tool calling, limited to the evaluation harness.
- Results become claims about architectures. The benchmark therefore has to
  publish its prompts, its datasets, and its oracle definitions alongside the
  numbers.
- The project name keeps the acronym but changes its expansion to *Agent
  Safety & Integrity Assessment*.
