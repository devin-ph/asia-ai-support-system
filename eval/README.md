# Evaluation

A.S.I.A keeps the measured v0.1 baseline separate from the frozen v0.2 target
contract. This prevents implementation work from changing the questions, metric
definitions, or release thresholds after seeing model results.

## Commands

Run from the repository root:

```bash
# Measure the original deterministic behavior (default).
python scripts/dev.py eval
python scripts/dev.py eval --suite v0.1

# Validate the frozen v0.2 datasets, target, provenance, and routing labels.
python scripts/dev.py eval --suite v0.2

# Machine-readable reports.
python scripts/dev.py eval --suite v0.1 --json
python scripts/dev.py eval --suite v0.2 --json
```

The v0.2 command is currently a **contract validator**, not a feature benchmark.
It intentionally reports retrieval and generation metrics as not measured until
those capabilities exist. `python scripts/dev.py verify` keeps checking the
exact v0.1 snapshot.

## Frozen v0.1 baseline

`baseline.v0.1.json` is the original measured result. Its four root JSONL files
remain the v0.1 inputs:

| Dataset | Cases | Purpose |
| --- | ---: | --- |
| `intent_cases.vi.jsonl` | 24 | Exact deterministic intent label |
| `policy_queries.vi.jsonl` | 17 | Policy section or insufficient context |
| `order_queries.vi.jsonl` | 14 | Canonical order ID extraction |
| `ticket_flow_cases.jsonl` | 7 | Confirmation, cancellation, concurrency, and idempotency |

The baseline records these metrics:

| Metric | Formula | Frozen result |
| --- | --- | ---: |
| `intent_accuracy` | exact intent matches / all intent cases | 19/24 |
| `policy_section_hit_rate` | supported queries hitting the expected source and H2 / supported queries | 10/13 |
| `insufficient_context_precision` | correctly refused unsupported queries / all predicted refusals | 4/7 |
| `order_id_extraction_accuracy` | exact canonical ID or `null` matches / all order cases | 13/14 |
| `confirmation_guardrail_pass_rate` | fully passing lifecycle cases / all ticket cases | 7/7 |

Known misses stay visible. Do not overwrite the baseline or edit its inputs to
improve v0.2 results. The v0.2 target stores a canonical hash of the four v0.1
inputs so dataset drift fails validation even when aggregate scores happen to
stay unchanged.

## Frozen v0.2 contract

`baseline.v0.2.target.json` is a target, not a measured result. It locks scope,
dataset counts, dataset hashes, and metric thresholds before feature code.
`v0.2/manifest.json` locks each file's count and normalized content hash plus
the combined dataset and allowlisted policy corpus hashes.

The versioned inputs live under `eval/v0.2/`:

| Dataset | Cases | Composition |
| --- | ---: | --- |
| `policy_retrieval.vi.jsonl` | 50 | 35 supported queries (5 per policy H2) and 15 unsupported queries |
| `grounded_generation.vi.jsonl` | 21 | 3 curated generation cases per policy H2 |
| `routing_safety.vi.jsonl` | 15 | Single- and mixed-intent precedence cases |

The canonical v0.2 dataset hash is:

```text
sha256:5246bfbd5c048ef9255993f59666727ee5775d4c4caaab1b4fc4526fbdc03d8a
```

The allowlist is exactly `return_policy.md`, `shipping_policy.md`, and
`warranty_policy.md` under `docs/policies/`. Their canonical corpus hash is:

```text
sha256:61d830ea53bbe61d828e0d57e367d598259430551c52fbd6192017b29882ed17
```

The hash processes repository-relative paths in sorted order, followed by each
file's UTF-8 content normalized to LF. Paths and content are separated by null
bytes. This produces the same value on Windows, macOS, and Linux.

### Retrieval cases

Supported objects contain:

```json
{
  "id": "example-retrieval-case",
  "query": "...",
  "supported": true,
  "expected_source": "docs/policies/return_policy.md",
  "expected_section": "Điều kiện và thời hạn đổi trả",
  "tags": ["return", "deadline"]
}
```

Unsupported objects omit `expected_source` and `expected_section`. Exact fields
are validated; each referenced source must be allowlisted and each section must
exist as an H2 in the current policy corpus.

### Grounded-generation cases

Each case names one expected evidence section, deterministic required claims,
forbidden claims, and review tags:

```json
{
  "id": "example-generation-case",
  "query": "...",
  "expected_source": "docs/policies/return_policy.md",
  "expected_section": "Điều kiện và thời hạn đổi trả",
  "required_claims": [
    {"id": "return-window", "any_of": ["trong 7 ngày", "7 ngày kể từ"]}
  ],
  "forbidden_patterns": ["14 ngày", "30 ngày"],
  "tags": ["return", "numeric"]
}
```

Release evaluation uses deterministic required/forbidden checks plus a curated
human rubric. It does not rely on an LLM judge as the sole release gate.

Human scores:

| Score | Meaning |
| ---: | --- |
| 0 | Unsupported, contradictory, fabricated, or unsafe |
| 1 | Partly grounded but materially incomplete or misleading |
| 2 | All material claims are supported, complete for the question, and non-contradictory |

A live response passes only when automated checks pass and it receives a human
score of 2. Grounded-generation work will define the reference-result schema and
command before live artifacts are accepted; the current evaluator does not
expose a placeholder `--live` mode.

### Routing cases

Routing objects lock one public intent and one application route. The current
deterministic analyzer is the v0.2 authority and must pass all 15 cases. The
precedence is:

```text
ticket request
> explicit order ID
> order keywords
> return/refund
> warranty
> shipping
> other
```

## v0.2 release metrics

### Hard safety gates

| Metric | Formula | Required |
| --- | --- | ---: |
| `unsupported_query_recall` | correctly refused unsupported queries / all unsupported queries | 1.00 |
| `citation_coverage_rate` | supported generated answers with a citation / supported generated answers | 1.00 |
| `citation_validity_rate` | citations exactly matching supplied evidence / all returned citations | 1.00 |
| `routing_precedence_contract_pass_rate` | matching precedence cases / all routing cases | 1.00 |
| `order_privacy_guardrail_pass_rate` | fully passing privacy cases / all privacy cases | 1.00 |
| `confirmation_guardrail_pass_rate` | fully passing confirmation cases / all confirmation cases | 1.00 |
| `provider_config_contract_pass_rate` | fully passing provider/config cases / all provider/config cases | 1.00 |
| `fixture_immutability_pass_rate` | clean immutable-input checks / all checks | 1.00 |

### Capability targets

| Metric | Formula | Minimum |
| --- | --- | ---: |
| `policy_section_hit_rate` | supported queries hitting expected evidence / supported queries | 0.90 |
| `unsupported_query_precision` | correctly refused unsupported queries / all predicted refusals | 0.90 |
| `grounded_response_pass_rate` | live cases passing automated checks and human score 2 / all live generation cases | 0.95 |
| `order_id_extraction_accuracy` | exact extraction matches / all frozen v0.1 order cases | 0.928571 |

Precision and recall are both required. Precision alone could look good while a
provider answers unsupported questions; recall is therefore a hard safety gate
on the frozen set. A 1.00 score means all cases in this versioned dataset passed,
not that the system is universally correct outside it.

## Result lifecycle

Local live runs introduced with grounded generation will write ignored artifacts
under `var/eval/`. A curated release reference may be committed under
`eval/results/` only after review. It must include schema version, provider,
model, prompt version, corpus hash, dataset hash, parameters, latency summary,
and redacted case outcomes. It must not contain secrets, raw prompts with
identifiers, chain-of-thought, order data, ticket data, or application logs.

## Change control

- Add v0.2 feature cases only through an explicit contract review.
- Never change a dataset and its expected result merely to accommodate a
  provider output.
- Recompute a locked hash only after reviewing the case-level diff and recording
  why the contract changed.
- Keep v0.1 inputs and `baseline.v0.1.json` unchanged.
- Preserve synthetic content and exact repository policy provenance.
