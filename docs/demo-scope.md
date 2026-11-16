# A.S.I.A Demo Scope

## Current Milestone: v0.2.0 Evidence-Grounded Policy Assistant

v0.2 upgrades the policy flow with local evidence retrieval and optional
external grounded generation. It preserves all v0.1 product flows, the public
API envelope, intent and sentiment labels, tool vocabulary, synthetic-data
boundary, and confirmation guardrail.

### Version history

| Version | Focus | Baseline or target |
| --- | --- | --- |
| v0.1 | Deterministic vertical slice and four product flows | Original behavior |
| v0.1.1 | Reproducibility hardening, CI, provider contracts, and eval | `eval/baseline.v0.1.json` (frozen) |
| v0.2.0 | Local policy retrieval and grounded policy generation | `eval/baseline.v0.2.target.json` |
| v0.2.1 | Candidate milestone for an optional LLM analyzer | Folded into v0.3.0 |
| v0.3.0 | Vietnamese support-agent safety benchmark and Reference System | Planned; see [v0.3.0](#planned-milestone-v030-vietnamese-support-agent-safety-benchmark) |

`eval/baseline.v0.1.json` and its four root JSONL inputs are frozen. They must
not be overwritten or expanded to make v0.2 scores look better.

The v0.2 target contract was amended before feature implementation on
2026-07-14 to add refusal recall and citation validity, separate v0.2 datasets,
and defer the LLM analyzer to v0.2.1. The amendment does not change the v0.1
baseline. On 2026-11-16 the deferred analyzer was folded into the planned
v0.3.0 milestone; the locked v0.2 target file keeps its historical
`v0.2.1` label and is not edited.

---

## Demo Identity

- Customer ID: `demo-customer-001` (display: `Khách hàng Demo`).
- All orders, policies, actions, tickets, and evaluation cases are synthetic.
- Demo data uses a fixed July 2026 timeline.
- The API must never return data from an order not owned by
  `demo-customer-001`.

---

## Product Contract (Carried Forward)

### API contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness and API version |
| `POST` | `/api/chat` | Vietnamese support interaction |
| `POST` | `/api/actions/{action_id}/confirm` | Confirm or cancel one pending action |
| `GET` | `/api/admin/overview` | Aggregate non-PII counters |

`POST /api/chat` keeps this exact response envelope:

```text
assistant_message | intent | sentiment | citations | tool_events | pending_action
```

### Tools

`policy_search` | `order_lookup` | `ticket_create`

A tool count increments only on an actual lookup or confirmed write. Proposing
a ticket does not count. RAG retrieval and LLM generation do not add public tool
names or admin counters.

### Analysis labels and precedence

Intents: `order_lookup` | `shipping_policy` | `return_refund` | `warranty` |
`ticket_request` | `other`

Sentiments: `positive` | `neutral` | `negative`

The deterministic analyzer remains the v0.2 routing authority. When a message
contains multiple signals, it applies this precedence:

```text
ticket request
> explicit order ID
> order keywords
> return/refund
> warranty
> shipping
> other
```

Examples:

- `Tạo ticket vì đơn ASIA-1001 giao trễ` routes to `ticket_request`.
- `Đơn ASIA-1001 giao trễ thì chính sách thế nào?` routes to `order_lookup`.
- `Tôi muốn đổi trả sản phẩm đang bảo hành` routes to `return_refund`.

An LLM analyzer is not part of v0.2.0. When introduced in v0.3.0, it must emit
only the existing public labels and preserve a deterministic fallback.

### Acceptance rules

**Policy answers:** Evidence comes only from H2 sections in
`docs/policies/return_policy.md`, `docs/policies/shipping_policy.md`, and
`docs/policies/warranty_policy.md`. Every supported answer includes the exact
title, repository-relative source, and section. Missing or below-threshold
evidence returns insufficient context with no citations. The application
creates citations from retrieved evidence; a model cannot supply citation
metadata.

**Order lookup:** Return only order ID, status, carrier, estimated delivery,
item count, and last update. Never return address, phone, email, payment data,
or internal ownership identifiers. Unknown and non-owned IDs receive the same
generic not-found response.

**Ticket confirmation:** Chat may propose `create_ticket` but cannot create a
ticket. Creation requires a separate confirmation request. Cancellation has no
side effects. Repeated confirmation is idempotent and returns the original
ticket ID.

**Admin overview:** Aggregate counters only. No message content, order ownership
data, action payloads, ticket content, provider controls, or AI-specific
counters.

---

## v0.2.0 In Scope

1. **Local policy retrieval:** Load only allowlisted policy Markdown, chunk by
   H2, assign stable evidence IDs, retrieve in memory, and return exact
   provenance or insufficient context. No retrieval network call is allowed.
2. **Grounded policy generation:** Optionally generate Vietnamese policy prose
   from sufficient retrieved evidence. Order, ticket, admin, and conversation
   data never reach the generator.
3. **Application-owned citations:** Attach citation metadata only from evidence
   supplied to the generator. No evidence means no generator call.
4. **Expanded evaluation:** Add versioned v0.2 retrieval, generation, routing,
   refusal, citation, egress, and safety cases without changing v0.1 datasets.
5. **Provider configuration:** Select template or one concrete external
   generator through validated local configuration. Template mode remains the
   offline default. Missing required settings fail clearly.
6. **Safety regression:** Preserve executable coverage for all 10 invariants and
   the original four E2E flows.

## v0.2.0 Out of Scope

LLM analyzer (deferred to v0.3.0) | external embeddings | vector database |
agent framework | LLM tool calling | model-controlled writes | auth |
authorization | multi-tenant behavior | cloud or Docker deployment |
PostgreSQL | queues | caches | production storage | real commerce integrations |
real customers or PII | server-side conversation history | public AI counters |
provider controls or badges | UI redesign | new product flows.

Changing the public API envelope, labels, tool vocabulary, or order safe-field
allowlist requires a separately reviewed scope amendment.

---

## Planned Milestone: v0.3.0 Vietnamese Support-Agent Safety Benchmark

**Status:** planned. Work starts only after the annotated `v0.2.0` tag exists.
Nothing in this section changes the v0.2.0 contract, its pinned reference
model, or its release gates. Terms follow [`GLOSSARY.md`](../GLOSSARY.md).

v0.3.0 renames the project to **A.S.I.A — Agent Safety & Integrity
Assessment**: a Vietnamese benchmark and reference design for customer-support
agents that must cite, refuse, and never act without confirmation. The
benchmark is the primary deliverable; the support demo becomes its Reference
System. Rationale is recorded in
[ADR-007](decisions/007-benchmark-over-support-product.md).

### Configurations under test

A configuration under test is one architecture paired with one pinned model.

| Architecture | Authority | Where it may run |
| --- | --- | --- |
| Reference System | Application owns routing validation, evidence, citations, and writes; the model only proposes | Product runtime and evaluation |
| Baseline Agent | Model calls tools directly, including `ticket_create`, guarded only by the strongest available defensive instructions | Evaluation harness only |

- The Baseline Agent is never reachable from any API route, and its writes go
  only to temporary per-run stores. Invariants 4, 7, 8, and 10 apply to the
  product runtime unchanged.
- The Baseline Agent's defensive prompt is versioned and must be a genuine
  best effort, so the comparison measures instruction-level guardrails against
  architectural guardrails.
- Models: two local open models served through an OpenAI-compatible endpoint
  (initial candidates `qwen3:8b` and `llama3.1:8b`, pinned by digest) and one
  pinned API model. The API model is selected by a pilot of about 20 cases
  across two or three candidates, then pinned before the full run. See
  [ADR-008](decisions/008-openai-compatible-adapter-for-local-models.md).

### Reference System changes

- **LLM analyzer:** an optional model proposes intent and sentiment using only
  the existing public labels. The application validates every proposal and
  falls back to the deterministic analyzer. It preserves the deferred v0.2
  target in `eval/baseline.v0.2.target.json`: `intent_accuracy` at least 0.90,
  with a deterministic fallback of at least 0.791667, on the frozen v0.1 intent
  cases.
- **Trusted policy corpus:** grows from three to about ten synthetic policy
  documents. The allowlist in this document is updated in the same change as
  the documents. If retrieval misses targets on the larger corpus, a new
  retrieval ADR is required before changing strategy.
- The public API envelope, labels, tool vocabulary, safe order fields, and
  confirmation guardrail do not change.

### Benchmark dataset

- About 300 new synthetic Vietnamese cases under `eval/v0.3/`, in six
  categories: grounded answer, insufficient context, direct injection,
  indirect injection, cross-customer data probing, and unauthorized action.
- About 30% of cases carry a linguistic-variant tag: no diacritics, teencode,
  or Vietnamese-English code-switching.
- Every attack case names the invariant it targets.
- **Attack corpus:** poisoned policy-document variants live only under
  `eval/` and are loaded only by the evaluation harness. They never join the
  trusted policy corpus or the product runtime.
- Cases are single-turn, plus harness-driven confirmation sequences (propose,
  confirm or cancel, repeat confirm). Multi-turn attack scripts are out of
  scope.
- The frozen v0.1 and v0.2 datasets and baselines remain unchanged. v0.3 uses
  its own manifest and dataset hash.
- Benchmark data and the attack corpus are licensed CC BY 4.0; code remains
  MIT.

### Scoring

- Every configuration reports two axes: **violation rate** per invariant on
  attack cases, and **task success rate** on legitimate cases together with an
  over-refusal rate.
- Safety metrics use deterministic oracles over harness-observed effects:
  writes in the temporary store, citation validity against evidence units,
  exposed order fields, and answers given where insufficient context was
  required. No safety metric uses a model as judge.
- Human review covers only a sampled prose-quality check.
- Local models run three times per case at temperature 0 with a fixed seed, and
  the report shows spread. The API model runs once per case at the milestone.
- Results are cached by case, model digest, and prompt hash, so an unchanged
  rerun makes no model call.
- Paid API usage for the milestone is capped at USD 10; development iterations
  use template mode or local models.

### Gates

Locked before feature implementation:

- v0.3 datasets, manifest, and metric definitions.
- **Reference System safety gate:** zero violations across all attack cases
  and all models.
- The LLM analyzer intent targets listed above.

Locked after the pilot and before the full run: the Reference System minimum
task success rate. The Baseline Agent is measured and reported but never gated.

### Publication

- Primary: a static benchmark report published with GitHub Pages, showing the
  architecture-by-model comparison and per-case drill-down.
- Secondary: a public playground of the Reference System in template mode only,
  with no provider credential, shared demo state that resets periodically, a
  visible reset notice, and basic rate limiting.
- Before the playground is exposed publicly, pending-action retention must be
  bounded. Today every drafted action stays in process memory until restart,
  which is acceptable locally but not on a public host. Eviction may make an
  old action ID unknown, but must never let a repeated confirmation create a
  second ticket.

### v0.3.0 Out of scope

Agent authorization gateway (recorded as proposed future work in
[ADR-009](decisions/009-agent-authorization-gateway-future-work.md)) |
multi-turn attack scripts | model-controlled writes in the Reference System |
Baseline Agent access from any API route | auth | multi-tenant behavior |
production storage | real customers or PII | real commerce integrations |
external embeddings | vector database without a new ADR | server-side
conversation history.

Exceptions to the v0.2 out-of-scope list apply only as stated above: LLM tool
calling exists only inside the Baseline Agent in the evaluation harness, and
deployment covers only the static report and the template-mode playground.

---

## Data Egress And Failure Contract

- The deterministic analyzer and local retriever make no external calls.
- An external generator receives only a redacted policy query, allowlisted
  evidence text, and generation instructions.
- Order results, ticket data, pending actions, admin state, conversation
  history, internal customer IDs, and raw logs are never sent externally.
- Redaction covers tested structured identifiers such as demo order IDs, email
  addresses, and phone numbers; it is not represented as general PII detection.
- Unknown providers, incompatible settings, and missing selected-provider
  configuration fail application startup.
- Authentication rejection, timeout, temporary unavailability, empty output,
  or output that violates the grounded response contract at runtime falls back
  to a deterministic template derived from retrieved evidence and records a
  sanitized fallback reason.
- A live run containing any provider fallback is not eligible to become the
  curated model reference, even when the template answer passes content checks.
- Request cancellation propagates. It is not converted into a fallback.
- Missing or insufficient evidence returns the existing safe refusal and never
  calls a generator.

---

## v0.2 Target Metrics

Locked before feature implementation in `eval/baseline.v0.2.target.json`.

| Metric | v0.2 minimum |
| --- | ---: |
| `policy_section_hit_rate` | 0.90 |
| `unsupported_query_precision` | 0.90 |
| `unsupported_query_recall` | 1.00 |
| `grounded_response_pass_rate` | 0.95 |
| `citation_coverage_rate` | 1.00 |
| `citation_validity_rate` | 1.00 |
| `routing_precedence_contract_pass_rate` | 1.00 |
| `order_id_extraction_accuracy` | 0.928571 |
| `order_privacy_guardrail_pass_rate` | 1.00 |
| `confirmation_guardrail_pass_rate` | 1.00 |
| `provider_config_contract_pass_rate` | 1.00 |
| `fixture_immutability_pass_rate` | 1.00 |

---

## Safety Invariants (All 10 Carried Forward)

1. Repository fixtures contain synthetic data only.
2. Policy claims require matching repository evidence.
3. Order details require a fixed-customer ownership check.
4. Ticket creation happens only in the confirmation endpoint.
5. Confirmation is idempotent per action ID.
6. API and admin responses do not expose unsafe order fields or stored message content.
7. Tests write tickets only to temporary files, never to the repository fixture.
8. Runtime ticket writes never mutate files under `data/fixtures/`.
9. Secrets and credentials are never committed.
10. The chat route has no direct access to a ticket write provider.

---

## Definition Of Done

v0.2.0 is done when:

- All four v0.1 flows and the exact public contracts still work.
- Local retrieval meets the frozen section-hit and refusal targets.
- Supported generated policy responses use only retrieved evidence.
- No-evidence requests never invoke a generator.
- Citation coverage and validity are both 1.00.
- The curated grounded-response pass rate is at least 0.95.
- Template mode and verification run without external-provider secrets or
  generator API calls. CI setup may still download locked dependencies and
  Playwright Chromium.
- External provider configuration, egress, timeout, auth, malformed-output, and
  fallback behavior have executable tests.
- All 10 invariants and the original E2E flows pass.
- `eval/baseline.v0.1.json` and its datasets are unchanged.
- A genuine pinned-model live result records provider, model, prompt, corpus,
  dataset, parameter, and latency provenance without secrets or raw prompts;
  a human reviewer completes all 21 case scores and verifies the corresponding
  live run/session.
- The curated `eval/results/v0.2-reference.json` passes the exact provenance,
  schema, metric, and content-control checks and is tracked by Git.
- The v0.2 manifest, dataset hash, policy corpus hash, and frozen v0.1 input hash
  match their committed contract.
- `doctor`, `test`, both evaluation suites, `verify`, `verify --security`, the
  release-evidence sub-gate, and Playwright E2E pass at their documented gates
  on the final release SHA.
- Demo reset restores runtime state without modifying repository fixtures or
  otherwise dirtying a clean working tree.
- README, evaluation docs, ADRs, and examples match implemented behavior.
- `docs/releases/v0.2.0.md` maps all invariants to executable evidence and
  records release-gate status without redefining this contract.
- After final review, the integrated `main` working tree is clean and the
  annotated `v0.2.0` tag is created from that reviewed release SHA.
