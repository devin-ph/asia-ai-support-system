# A.S.I.A Demo Scope

## Current Milestone: v0.2 — RAG and Grounded AI

v0.2 introduces retrieval and grounded AI behind existing provider boundaries.
It preserves all v0.1 product flows, the public API envelope, safety
invariants, synthetic-data boundary, and confirmation guardrail without
broadening the product surface.

### Version history

| Version | Focus | Baseline |
| --- | --- | --- |
| v0.1 | Deterministic vertical slice, 4 product flows | — |
| v0.1.1 | Reproducibility hardening, CI, provider contracts, eval | `eval/baseline.v0.1.json` (frozen) |
| v0.2 | RAG policy retrieval, grounded AI response, optional LLM analyzer | `eval/baseline.v0.2.target.json` |

`eval/baseline.v0.1.json` is frozen. It must not be overwritten to make v0.2
scores look better.

---

## Demo Identity

- Customer ID: `demo-customer-001` (Display: `Khách hàng Demo`)
- All orders, policies, actions, and tickets are synthetic.
- Demo data uses a fixed July 2026 timeline.
- The API must never return data from an order not owned by `demo-customer-001`.

---

## Product Contract (Carried Forward)

The four product flows, API envelope, and tool vocabulary are unchanged.

### API Contract

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness and API version |
| `POST` | `/api/chat` | Vietnamese support interaction |
| `POST` | `/api/actions/{action_id}/confirm` | Confirm or cancel one pending action |
| `GET` | `/api/admin/overview` | Aggregate non-PII counters |

`POST /api/chat` response envelope (stable):

```
assistant_message · intent · sentiment · citations · tool_events · pending_action
```

### Tools

`policy_search` · `order_lookup` · `ticket_create`

A tool count increments only on actual lookup or confirmed write. Proposing a
ticket does not count.

### Analysis labels

Intents: `order_lookup` · `shipping_policy` · `return_refund` · `warranty` ·
`ticket_request` · `other`

Sentiments: `positive` · `neutral` · `negative`

v0.2 may add an LLM analyzer behind the analyzer provider boundary, but it must
emit only these public labels. The deterministic analyzer remains a supported
fallback.

### Acceptance rules (unchanged)

**Policy answers:** Must be derived from `docs/policies/*.md`. Every supported
answer includes exact citation (title, repo-relative source, section heading).
If evidence is missing, return insufficient context and no citations. Do not
invent policy details.

**Order lookup:** Return only safe fields (order ID, status, carrier, estimated
delivery, item count, last update). Never return address, phone, email, payment
data, or internal ownership identifiers. Unknown and non-owned order IDs receive
the same generic not-found response.

**Ticket confirmation:** Chat may propose `create_ticket` but must not create a
ticket. Creation requires a separate confirmation request. Cancellation has no
side effects. Repeated confirmation is idempotent and returns the original
ticket ID.

**Admin overview:** Aggregate counters only. No message content, order ownership
data, action payloads, or ticket content.

---

## v0.2 In Scope

1. **RAG policy retrieval** — retrieve from `docs/policies/*.md` only;
   return exact citations; preserve insufficient-context fallback.
2. **Grounded AI response generation** — generate from cited evidence and safe
   tool results only; fall back to insufficient context when evidence is absent
   or below threshold.
3. **Optional LLM analyzer** — configurable behind the analyzer provider
   boundary; deterministic analyzer remains selectable; all outputs map to
   existing label enums.
4. **Expanded eval** — broader Vietnamese paraphrases, unsupported queries,
   grounded-generation checks, provider-config cases, safety regression; known
   hard cases must not be removed.
5. **Provider config** — select providers via `.env` without committing secrets;
   fail closed when required config is missing; ticket write providers remain
   behind application state and the confirmation endpoint.
6. **Safety regression** — extend test and eval coverage for all 10 invariants.

## v0.2 Out of Scope

Auth · authorization · multi-tenant · cloud/Docker deployment · PostgreSQL ·
queues · caches · production storage · real commerce integrations · real
customers · real PII · server-side conversation history · new product flows ·
model-controlled irreversible writes · changing the public API envelope, labels,
tool vocabulary, or order safe-field allowlist without updating this document.

---

## v0.2 Target Metrics

Locked before implementation in `eval/baseline.v0.2.target.json`.

| Metric | v0.2 minimum |
| --- | --- |
| `policy_section_hit_rate` | ≥ 0.90 (expanded supported cases) |
| `insufficient_context_precision` | ≥ 0.90 (expanded unsupported cases) |
| `grounded_response_pass_rate` | ≥ 0.95 |
| `citation_coverage_rate` | 1.00 for supported generated answers |
| `intent_accuracy` (LLM analyzer) | ≥ 0.90; deterministic fallback ≥ v0.1 frozen score |
| `order_id_extraction_accuracy` | No regression from v0.1 frozen baseline |
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

## Definition of Done

v0.2 is done when:

- All four v0.1 flows work through the API.
- RAG policy retrieval returns exact citations or insufficient context.
- Grounded response generation uses only cited evidence and safe tool outputs.
- The optional LLM analyzer can be enabled or disabled without changing public labels.
- Provider config fails closed when required local settings are missing; no secrets committed.
- Expanded eval reports against v0.2 target metrics; `eval/baseline.v0.1.json` is unchanged.
- Safety regression coverage confirms all 10 invariants hold.
- `python scripts/dev.py doctor` passes.
- `python scripts/dev.py test` passes.
- `python scripts/dev.py verify` passes before a commit or pull request.
- `python scripts/dev.py reset-demo` restores `var/demo_tickets.json` without mutating fixtures or eval snapshots.
- README and response examples match the implemented API.
