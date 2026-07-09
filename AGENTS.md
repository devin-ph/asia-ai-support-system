# AGENTS.md

## Project

A.S.I.A is a demo AI customer support system for Vietnamese e-commerce support.

The current milestone is **v0.1.1: Reproducibility Hardening**.

## Current Goal

Build a local demo that supports four flows:

1. Vietnamese policy questions with grounded answers and citations.
2. Synthetic order lookup for a fixed demo customer.
3. Support ticket drafting with explicit user confirmation.
4. Basic admin overview showing message, ticket, intent, sentiment, and tool counts.

## Source of Truth

Read documents in this order:

1. `docs/demo-scope.md`
2. `README.md`
3. `backend/AGENTS.md` when working inside `backend/`
4. `frontend/AGENTS.md` when working inside `frontend/`

Do not implement features outside `docs/demo-scope.md` unless the user explicitly requests them.

Any change to required flows, API shapes, intent or sentiment labels, tool
semantics, storage behavior, safety invariants, or milestone acceptance
criteria must update `docs/demo-scope.md` in the same change. If the product
contract is unaffected, do not edit the scope document merely for churn.

## Commands

Use these commands when possible:

```bash
python scripts/dev.py doctor
python scripts/dev.py backend
python scripts/dev.py frontend
python scripts/dev.py test
python scripts/dev.py eval
python scripts/dev.py verify
```

`doctor` validates runtime prerequisites. `test` runs the fast unit/component
loop. `eval` measures the deterministic baseline. `verify` is the pre-commit
gate. See [`README.md`](README.md) for detailed descriptions and
[`eval/README.md`](eval/README.md) for metric definitions.

## Safety Rules

* Use synthetic data only.
* Treat files under `data/fixtures/` as immutable repository fixtures.
* Write local runtime state only under the ignored `var/` directory.
* Never add real customer data, real PII, secrets, or API keys.
* Do not expose write actions directly to a model or chat handler.
* Keep ticket write providers behind application state and the confirmation
  endpoint.
* Ticket creation must require explicit user confirmation and repeated
  confirmation must not create duplicate tickets.
* If policy evidence is missing, return an insufficient-context response instead
  of inventing an answer.
* Order lookup must only return safe fields and must enforce the fixed demo
  customer ownership check.

## Non-Negotiable Invariants

These constraints must hold after every change. No exception, no workaround.

1. Chat route must not directly execute irreversible write actions.
2. Ticket creation must require explicit user confirmation.
3. Policy answers must cite evidence or return insufficient context.
4. Demo data must remain synthetic.
5. Running the demo must not dirty tracked fixtures.
6. Unauthorized and unknown orders must not leak distinguishable details.

If a proposed change would violate any invariant, stop and report the conflict
instead of proceeding.

## Git Behavior

Use a review-first workflow that keeps `main` runnable and demo-ready. Follow
`docs/dev-workflow.md` for the detailed Git workflow.

The agent may inspect the repository, create or reuse a suitable branch, make
changes, and run checks. By default, the agent must not commit, push, or merge.
Leave the working tree ready for review unless the user explicitly asks for Git
write actions.

Use a short-lived branch for non-trivial changes, especially code, tests,
configuration, dependencies, CI, safety rules, product contract, or agent
instruction changes. Small wording, formatting, or link-only documentation edits
may stay on the current branch when the working tree is clean.

Before editing:

* Check the current branch and working tree.
* Reuse the current branch when it clearly matches the task.
* Create a focused branch when working from `main`, when the task is non-trivial,
  or when the current branch is unrelated.
* Preserve unrelated local changes.

Before returning work:

* Run the relevant check for the size of the change. Use
  `python scripts/dev.py verify` for non-trivial code, test, tooling,
  configuration, contract, or behavior changes.
* For trivial documentation-only edits, a short manual verification note is
  enough.
* Report verification failures clearly and leave the change uncommitted.
* Provide a natural review summary and, when useful, copyable commit commands.

Commit proposals should favor clarity without over-splitting. One commit is fine
for a cohesive change. Suggest multiple commits only when that would make review
meaningfully easier, such as separating code behavior, tests, docs, CI/tooling,
dependencies, or mechanical formatting.

Use explicit paths in commit commands and avoid `git add .` unless the full diff
has been reviewed:

```bash
git add -- <file> <file>
git commit -m "<type>(optional-scope): <short description>"
```

Must not:

* Commit unless the user explicitly asks.
* Push unless the user explicitly asks.
* Merge into `main` unless the user explicitly asks.
* Commit or push directly to `main`.
* Commit secrets, real PII, generated build artifacts, dependency folders,
  runtime state, or unrelated local changes.

## Definition of Done

A change is ready for review when:

* Relevant tests pass or a manual verification note is provided.
* `python scripts/dev.py verify` passes before merging non-trivial changes to
  `main`.
* No non-negotiable invariant is violated.
* Product-contract or API shape changes update `docs/demo-scope.md` in the same
  change.
* New behavior stays inside the v0.1 scope unless explicitly requested.
* No secrets, real PII, generated build artifacts, dependency folders, or
  runtime state are committed.

See [`docs/demo-scope.md`](docs/demo-scope.md) for the full milestone
acceptance criteria and product-level definition of done.
