# Deterministic evaluation baseline

This directory measures the current v0.1 behavior before A.S.I.A introduces an
LLM, retrieval provider, or other probabilistic component. The expected values
describe the desired product behavior; they are not rewritten to make the
current rules score 100%.

Run the evaluation from the repository root:

```bash
python scripts/dev.py eval
```

The committed `baseline.v0.1.json` records the reproducible deterministic
scores. `python scripts/dev.py verify` checks that this snapshot has not drifted
silently. When an intentional implementation or dataset change affects a
metric, review the case-level differences and update the snapshot in the same
change.

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
