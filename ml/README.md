# ML

Reserved. This directory is intentionally empty.

Model adapters do not live here. The v0.2 OpenAI adapter and the planned v0.3
OpenAI-compatible adapter for local models sit behind the narrow provider seam
in `backend/app/providers/`
([ADR-005](../docs/decisions/005-openai-responses-for-grounded-generation.md),
[ADR-008](../docs/decisions/008-openai-compatible-adapter-for-local-models.md)).
Benchmark datasets, the attack corpus, and Baseline Agent prompts belong under
`eval/`, which is versioned and hash-locked.

Use this directory only if a later milestone needs model artifacts that fit
neither place, and record that decision in an ADR first. See
[`docs/demo-scope.md`](../docs/demo-scope.md) for current scope.
