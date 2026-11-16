# ADR-008: OpenAI-compatible adapter for local models

## Status

Accepted for the planned v0.3.0 milestone. Extends ADR-005, which required a
separate decision before adding a second model provider.

## Context

The v0.3 benchmark has to score several models within a total API budget of
USD 10. The development machine (8 GB VRAM) runs 4–8B open models locally at
no cost. ADR-005 deliberately limited v0.2 to a single external provider. It
named a concrete multi-provider use case as the condition for adding another,
and the benchmark is that use case.

## Decision

- Serve local models through Ollama's OpenAI-compatible endpoint, and reach
  them with the existing official OpenAI Python SDK pointed at a different
  base URL. The project adds no new SDK, gateway, or model router.
- Pin every model by an exact identifier: an API snapshot name, or a local
  model digest. Every artifact records the identifier actually used, and no
  configuration switches models silently.
- Initial local candidates are `qwen3:8b` and `llama3.1:8b`. They come from two
  model families with tool calling support and noticeably different Vietnamese
  quality. The API model is chosen by a pilot of about 20 cases and pinned
  before the full run. The v0.2.0 reference stays on
  `gpt-5.4-mini-2026-03-17`.
- Cache model results by case hash, model identifier, and prompt hash, so an
  unchanged rerun makes no model call.
- Development iterations use template mode or local models. Paid API calls
  run only at milestone runs.
- The egress rules of ADR-005 apply to every endpoint, including local ones.

## Consequences

- The provider seam must accept more than one OpenAI-compatible endpoint. Its
  configuration validation has to reject ambiguous or partial endpoint
  settings at startup.
- Behavior of the compatibility layer, such as tool calling, structured
  output, and seeds, can differ between Ollama and OpenAI. The harness records
  these differences as results, not as errors to hide.
- Benchmark runs on local models depend on the hardware. The report records
  the quantization and runtime version along with the model digest.
