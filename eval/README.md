# Evaluation baselines and targets

This directory measures the current v0.1 behavior and records the locked v0.2
target metrics before A.S.I.A introduces RAG retrieval, grounded AI response
generation, or an optional LLM analyzer. The expected values describe desired
product behavior; they are not rewritten to make the current rules score 100%.

Run the evaluation from the repository root:

```bash
python scripts/dev.py eval
```

The committed `baseline.v0.1.json` records the original reproducible
deterministic scores. Keep it as the frozen v0.1 reference baseline.
`python scripts/dev.py verify` checks that this snapshot has not drifted
silently. When an intentional deterministic implementation or dataset change
affects a v0.1 metric, review the case-level differences before updating the
snapshot in the same change.

`baseline.v0.2.target.json` is not a measured result. It is the locked target
contract for the v0.2 RAG and grounded-AI milestone. v0.2 implementation work
should compare candidate providers against that target without overwriting the
v0.1 baseline to move the goalposts.

## Datasets

- `intent_cases.vi.jsonl`: Vietnamese messages with an `expected_intent`.
- `policy_queries.vi.jsonl`: policy queries with an expected trusted source and
  exact section, or `expected: "insufficient_context"`.
- `order_queries.vi.jsonl`: messages with an expected canonical order ID or
  `null` when no valid ID should be extracted.
- `ticket_flow_cases.jsonl`: sequential, concurrent, cancelled, repeated, and
  unknown-action confirmation flows with expected statuses and ticket counts.

Every JSONL object has a stable, unique `id`. Cases use synthetic content only.
Evaluation ticket writes go to a temporary directory and never touch
`data/fixtures/` or `var/`.

## Metrics

- `intent_accuracy`: exact intent matches divided by all intent cases.
- `policy_section_hit_rate`: supported policy queries returning the expected
  source file and exact section divided by all supported policy queries.
- `insufficient_context_precision`: correctly rejected unsupported queries
  divided by all queries the search predicted as insufficient. This highlights
  over-conservative rejection of questions that do have trusted evidence.
- `order_id_extraction_accuracy`: exact canonical ID or `null` matches divided
  by all extraction cases.
- `confirmation_guardrail_pass_rate`: complete ticket-flow cases satisfying all
  expected lifecycle, persistence, cancellation, concurrency, and idempotency
  assertions divided by all ticket-flow cases.

These are evaluation metrics, not release thresholds. In particular, known
misses remain visible in the dataset so a future provider must demonstrate a
real improvement without weakening the confirmation guardrail.

## v0.2 target metrics

The v0.2 target file locks the metric expectations before implementation:

- RAG policy retrieval improves supported policy hit rate and unsupported
  insufficient-context precision to at least 0.90 on expanded cases.
- Grounded response generation adds generated-answer checks, with at least 0.95
  grounded-response pass rate and 1.00 citation coverage for supported policy
  answers.
- The optional LLM analyzer must reach at least 0.90 intent accuracy when
  enabled, while the deterministic fallback must not regress from the frozen
  v0.1 baseline.
- Order privacy, ticket confirmation, provider configuration, and fixture
  immutability guardrails remain 1.00 targets.
