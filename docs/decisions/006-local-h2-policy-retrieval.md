# ADR-006: Local H2 Policy Retrieval

## Status

Accepted.

## Context

v0.2 must improve Vietnamese policy retrieval over the frozen keyword baseline
without adding external embeddings, a vector database, or an ingestion system.
The trusted corpus is three small Markdown files whose H2 sections already form
the citation units exposed by the product contract.

## Decision

- Load only the three policy files allowlisted in `docs/demo-scope.md`.
- Treat each H2 section as one evidence unit with a deterministic
  `<source>#<normalized-heading>` identifier.
- Rank sections in memory using accent-normalized lexical overlap, heading
  overlap, word n-grams, and a fixed global sufficiency threshold.
- Refuse below-threshold queries instead of returning a best-effort section.
- Keep retrieval local and deterministic. The optional external generator may
  receive evidence text only after retrieval succeeds.
- Calibrate weights and the threshold against the frozen v0.2 dataset, while
  reporting that result only as evidence for that dataset.

## Consequences

- CI and template mode need no network, model download, or API key.
- Evidence IDs and citation metadata remain reproducible across processes and
  source load order.
- The implementation stays proportional to the seven-section corpus.
- Lexical aliases and thresholds are intentionally limited. A materially larger
  corpus or sustained frozen-set misses would justify a new ADR for embeddings
  or another retrieval strategy.
