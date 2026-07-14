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
| v0.2.1 | Candidate milestone for an optional LLM analyzer | Deferred |

`eval/baseline.v0.1.json` and its four root JSONL inputs are frozen. They must
not be overwritten or expanded to make v0.2 scores look better.

The v0.2 target contract was amended before feature implementation on
2026-07-14 to add refusal recall and citation validity, separate v0.2 datasets,
and defer the LLM analyzer to v0.2.1. The amendment does not change the v0.1
baseline.

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

An LLM analyzer is not part of v0.2.0. If introduced in v0.2.1, it must emit
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

LLM analyzer (deferred to v0.2.1) | external embeddings | vector database |
agent framework | LLM tool calling | model-controlled writes | auth |
authorization | multi-tenant behavior | cloud or Docker deployment |
PostgreSQL | queues | caches | production storage | real commerce integrations |
real customers or PII | server-side conversation history | public AI counters |
provider controls or badges | UI redesign | new product flows.

Changing the public API envelope, labels, tool vocabulary, or order safe-field
allowlist requires a separately reviewed scope amendment.

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
- Provider authentication rejection is surfaced as a service error rather than
  disguised as successful AI mode.
- Timeout, temporary unavailability, empty output, or malformed output falls
  back to a deterministic template derived from retrieved evidence.
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
- Template mode and CI run without secrets or network access.
- External provider configuration, egress, timeout, auth, malformed-output, and
  fallback behavior have executable tests.
- All 10 invariants and the original E2E flows pass.
- `eval/baseline.v0.1.json` and its datasets are unchanged.
- A reference live result records provider, model, prompt, corpus, dataset, and
  parameter provenance without secrets or raw prompts.
- The v0.2 manifest, dataset hash, policy corpus hash, and frozen v0.1 input hash
  match their committed contract.
- `python scripts/dev.py doctor`, `python scripts/dev.py verify`, release
  security checks, and Playwright pass at their documented gates.
- README, evaluation docs, ADRs, and examples match implemented behavior.
