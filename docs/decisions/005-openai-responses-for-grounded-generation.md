# ADR-005: OpenAI Responses API for grounded generation

## Status

Accepted

## Context

The v0.2 scope allows one optional external generator to turn sufficient local
policy evidence into natural Vietnamese prose. Template generation must remain
the offline default, and the external path must preserve application-owned
citations, bounded failures, synthetic-data rules, and reproducible evaluation.

Adding a generic model gateway or several provider integrations would create
configuration and testing work without improving the v0.2 product contract.
The milestone needs one concrete, well-bounded integration instead.

## Decision

Use the official OpenAI Python SDK and the Responses API for the optional
external generator.

- `template` remains the default generator and requires no network or secret.
- `openai` is the only external generator option in v0.2. It must be selected
  explicitly and its configuration must be validated at startup.
- The reference model is pinned to `gpt-5.4-mini-2026-03-17`. Local experiments
  may override the model, but the runtime must never switch models silently and
  every live evaluation artifact must record the model actually used.
- Network calls use `AsyncOpenAI` and the Responses API with no tools and
  `store=False`. The model returns answer text only; the application attaches
  citation metadata from the retrieved evidence.
- The request contains only generation instructions, a redacted policy query,
  and allowlisted policy evidence. Order, ticket, customer, conversation,
  admin, and raw log data are excluded.
- Calls use a short, explicit timeout, initially 15 seconds. SDK retries are
  disabled so one request cannot turn into an unbounded demo delay.
- Authentication or permission rejection is surfaced as a sanitized service
  error. Connection failure, timeout, rate limiting, server failure, empty
  output, or malformed output falls back to the deterministic evidence
  template. Request cancellation continues to propagate.
- Prompt changes are versioned and evaluated with the frozen v0.2 contract.
  Committed artifacts record provenance, not secrets or raw request content.

The implementation should add only the provider-specific runtime needed for
this decision. It must not introduce a multi-provider registry, model router,
agent framework, tool calling, streaming, external retrieval, or external
embeddings. A second external provider requires a separate decision backed by
a concrete use case.

## Consequences

- Deterministic mode and CI remain fully offline and do not require an API key.
- A pinned model snapshot and recorded prompt, corpus, dataset, and parameter
  provenance make reference evaluations more repeatable.
- Async I/O and a single bounded attempt keep the FastAPI request path from
  blocking indefinitely while preserving simple failure behavior.
- External generation requires network access, an API credential, and paid API
  usage. `store=False` disables response application-state storage, but normal
  API abuse-monitoring retention may still apply; only synthetic, redacted
  policy content may cross this boundary.
- The code is intentionally coupled to one provider at the outer integration
  edge. The internal generator contract remains narrow enough to keep template
  mode and tests independent from the SDK.

## References

- [OpenAI text generation guide](https://developers.openai.com/api/docs/guides/text)
- [GPT-5.4 mini model](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [Official OpenAI Python SDK](https://github.com/openai/openai-python)
- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
- [OpenAI API key safety](https://developers.openai.com/api/docs/guides/production-best-practices)
