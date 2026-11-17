# A.S.I.A Scope

This is the product contract. README, AGENTS files, and ADRs summarize or
explain it; they never override it. Terms follow [`GLOSSARY.md`](../GLOSSARY.md).

| Version | Focus | Status |
| --- | --- | --- |
| v0.1 | Deterministic four-flow vertical slice | Done; baseline frozen in `eval/baseline.v0.1.json` |
| v0.2.0 | Local policy retrieval and grounded generation | Current; waiting on the live reference run |
| v0.3.0 | Vietnamese support-agent safety benchmark | Planned; starts after the `v0.2.0` tag |

**One rule outranks convenience:** evaluation datasets and baselines are never
edited to make a score look better. Each suite is hash-locked; a dataset change
is a reviewed contract change, never a side effect of tuning.

---

## Product contract

### Demo identity

- Fixed synthetic customer `demo-customer-001` (display: `Khách hàng Demo`).
- All orders, policies, actions, tickets, and evaluation cases are synthetic,
  on a fixed July 2026 timeline.
- The API never returns an order not owned by `demo-customer-001`.

### API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness and API version |
| `POST` | `/api/chat` | Vietnamese support interaction |
| `POST` | `/api/actions/{action_id}/confirm` | Confirm or cancel one pending action |
| `GET` | `/api/admin/overview` | Aggregate non-PII counters |

`POST /api/chat` returns exactly:

```text
assistant_message | intent | sentiment | citations | tool_events | pending_action
```

- **Tools:** `policy_search` | `order_lookup` | `ticket_create`. A tool count
  increments only on an actual lookup or a confirmed write; proposing a ticket
  does not count. Retrieval and generation add no tool names or counters.
- **Intents:** `order_lookup` | `shipping_policy` | `return_refund` |
  `warranty` | `ticket_request` | `other`.
- **Sentiments:** `positive` | `neutral` | `negative`.
- **Routing precedence** (deterministic analyzer, the v0.2 authority):
  ticket request > explicit order ID > order keywords > return/refund >
  warranty > shipping > other. For example, `Tạo ticket vì đơn ASIA-1001 giao
  trễ` routes to `ticket_request`.

Changing the envelope, labels, tool vocabulary, or safe order fields is a
contract change and must update this file in the same change.

### Acceptance rules

- **Policy answers:** evidence comes only from H2 sections of the trusted
  policy corpus: `docs/policies/return_policy.md`,
  `docs/policies/shipping_policy.md`, and `docs/policies/warranty_policy.md`.
  Every supported answer cites exact title, repository-relative source, and
  section. Missing or below-threshold evidence returns insufficient context
  with no citations. Citations are built by the application, never by a model.
- **Order lookup:** returns only order ID, status, carrier, estimated delivery,
  item count, and last update. Unknown and non-owned IDs get the same generic
  not-found response.
- **Tickets:** chat may propose `create_ticket` but never creates one. Only the
  confirmation endpoint creates it. Cancel has no side effects; repeated
  confirmation returns the original ticket ID.
- **Admin overview:** aggregate counters only; no message content, ownership
  data, action payloads, ticket content, or provider controls.

### Data egress and failure

- The analyzer and local retriever make no external calls.
- An external generator receives only a redacted policy query, allowlisted
  evidence text, and generation instructions, at an endpoint pinned in code.
- Order results, tickets, pending actions, admin state, conversation history,
  internal customer IDs, and raw logs are never sent externally.
- Redaction covers tested structured identifiers (demo order IDs, emails,
  phone numbers); it is not general PII detection.
- Unknown providers or missing selected-provider settings fail startup.
- At runtime, auth rejection, timeout, unavailability, empty output, or output
  that breaks the grounded contract falls back to the evidence template with a
  sanitized reason. Cancellation propagates instead of falling back.
- No sufficient evidence means no generator call.

### Safety invariants

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

## v0.2.0 Evidence-Grounded Policy Assistant (current)

**In scope:** local H2 retrieval with stable evidence IDs; optional grounded
generation through one external generator (template mode is the offline
default); application-owned citations; versioned v0.2 evaluation datasets;
validated provider configuration; executable coverage of all invariants and the
four E2E flows.

**Out of scope:** LLM analyzer (moved to v0.3) | external embeddings | vector
database | agent framework | LLM tool calling | model-controlled writes | auth |
multi-tenant behavior | cloud or Docker deployment | production storage | real
commerce integrations | real customers or PII | server-side conversation
history | provider controls in the UI | new product flows.

**Targets** (locked in `eval/baseline.v0.2.target.json`; definitions in
[`eval/README.md`](../eval/README.md)):

| Metric | Minimum |
| --- | ---: |
| `policy_section_hit_rate` | 0.90 |
| `unsupported_query_precision` | 0.90 |
| `unsupported_query_recall` | 1.00 |
| `grounded_response_pass_rate` | 0.95 |
| `citation_coverage_rate` / `citation_validity_rate` | 1.00 |
| `routing_precedence_contract_pass_rate` | 1.00 |
| `order_id_extraction_accuracy` | 0.928571 |
| Order privacy, confirmation, provider config, fixture immutability | 1.00 |

**Done when:**

- The four flows, the public contract, and all ten invariants pass in
  `verify` and the Playwright E2E suite.
- Offline v0.2 metrics meet their targets and the frozen v0.1 inputs are
  unchanged.
- One live run with the pinned model `gpt-5.4-mini-2026-03-17` has no
  provider fallback, a human has scored all 21 generation cases, and
  `--curate-reference` has written `eval/results/v0.2-reference.json`.
- `python scripts/dev.py verify --release` passes, and the `v0.2.0` tag is
  created from `main`.

---

## v0.3.0 Vietnamese Support-Agent Safety Benchmark (planned)

The project becomes **A.S.I.A — Agent Safety & Integrity Assessment**: a
Vietnamese benchmark and reference design for customer-support agents that
must cite, refuse, and never act without confirmation. The support demo becomes
its Reference System ([ADR-007](decisions/007-benchmark-over-support-product.md)).
Nothing here changes the v0.2.0 contract.

### What is scored

A configuration under test is one architecture paired with one pinned model.

| Architecture | Authority | Where it may run |
| --- | --- | --- |
| Reference System | Application owns routing validation, evidence, citations, and writes; the model only proposes | Product runtime and evaluation |
| Baseline Agent | Model calls tools directly, including `ticket_create`, guarded by the strongest defensive prompt available | Evaluation harness only |

- The Baseline Agent is unreachable from any API route and writes only to
  temporary per-run stores; the invariants keep applying to the product runtime.
- Its defensive prompt is versioned and a genuine best effort, so the result
  compares prompt guardrails with architectural guardrails.
- Models: two local open models through an OpenAI-compatible endpoint (initial
  candidates `qwen3:8b` and `llama3.1:8b`, pinned by digest) plus one pinned
  API model chosen by a pilot of about 20 cases
  ([ADR-008](decisions/008-openai-compatible-adapter-for-local-models.md)).

### Reference System changes

- **LLM analyzer:** proposes intent and sentiment from the existing labels
  only; the application validates and falls back to the deterministic
  analyzer. Target on the frozen v0.1 intent cases: `intent_accuracy` at least
  0.90, deterministic fallback at least 0.791667.
- **Trusted policy corpus:** grows to about ten synthetic documents; the
  allowlist above changes in the same commit. A retrieval-strategy change needs
  a new ADR.
- **Pending-action retention** is bounded before any public deployment.
  Eviction may make an old action ID unknown but must never allow a duplicate
  ticket.

### Dataset and scoring

- About 300 synthetic Vietnamese cases under `eval/v0.3/`, in six categories:
  grounded answer, insufficient context, direct injection, indirect injection,
  cross-customer probing, unauthorized action. Every attack case names the
  invariant it targets.
- About 30% carry a linguistic-variant tag: no diacritics, teencode, or
  Vietnamese-English code-switching.
- **Attack corpus:** poisoned policy variants that live only under `eval/` and
  never join the trusted policy corpus.
- Single-turn cases plus harness-driven confirmation sequences; no multi-turn
  attack scripts.
- Each configuration reports **violation rate** per invariant and **task
  success** with **over-refusal** on legitimate cases.
- Safety is scored by deterministic oracles over observed effects, never by a
  model judge. Humans review only a sampled prose-quality check.
- Local models run three times per case (temperature 0, fixed seed); the API
  model runs once. Results are cached by case, model, and prompt hash. Paid API
  spend is capped at USD 10.
- Data is licensed CC BY 4.0; code stays MIT.

### Gates

- Locked before implementation: datasets, metric definitions, and the
  **Reference System safety gate of zero violations** across all attack cases
  and models.
- Locked after the pilot: the Reference System minimum task success rate.
- The Baseline Agent is measured, never gated.

### Publication

- Primary: a static benchmark report on GitHub Pages.
- Secondary: a template-mode playground with no credentials, shared state that
  resets periodically, a visible reset notice, and basic rate limiting.

**Out of scope:** agent authorization gateway (future work,
[ADR-009](decisions/009-agent-authorization-gateway-future-work.md)) |
multi-turn attacks | model-controlled writes in the Reference System | auth |
multi-tenant behavior | production storage | real data | external embeddings |
server-side conversation history. LLM tool calling exists only inside the
Baseline Agent, and deployment covers only the report and the playground.
