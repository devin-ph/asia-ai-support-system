# ADR-001: Deterministic baseline before LLM

## Status

Accepted

## Context

A.S.I.A will eventually integrate an LLM for intent classification, policy
retrieval, and response generation. However, introducing a probabilistic
component before the product contract is stable creates two problems:

1. It is impossible to tell whether a regression is caused by a code change, a
   prompt change, or model drift.
2. Safety invariants (confirmation guardrail, ownership checks, citation
   grounding) cannot be verified against a non-deterministic system without
   expensive statistical testing.

## Decision

Build the v0.1 vertical slice with **deterministic keyword rules only**. Record
a versioned evaluation baseline (`eval/baseline.v0.1.json`) against synthetic
Vietnamese test cases. Any future provider — LLM, RAG, embedding — must be
evaluated on the same cases and must improve useful metrics without weakening
the 100% confirmation-guardrail pass rate.

## Consequences

- The v0.1 baseline deliberately includes known misses (Vietnamese paraphrases
  that keyword rules cannot handle). These are features of the benchmark, not
  bugs to hide.
- Dataset changes and implementation changes should be reviewed in separate
  commits where practical to avoid moving the goalposts.
- A future LLM provider can be tested incrementally by running the shared
  provider contracts in `backend/tests/test_providers.py`.
