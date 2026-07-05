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
* Never add real customer data or real PII.
* Never commit secrets or API keys.
* Do not expose write actions directly to a model or chat handler.
* Keep ticket write providers behind application state and the confirmation
  endpoint.
* Ticket creation must require explicit user confirmation.
* Repeated confirmation must not create duplicate tickets.
* If policy evidence is missing, return an insufficient-context response instead of inventing an answer.
* Order lookup must only return safe fields and must enforce the fixed demo customer ownership check.

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

Use a branch-first, review-first workflow that keeps `main` runnable and
demo-ready. Follow `docs/dev-workflow.md` for branch prefixes, detailed Git
commands, commit guidance, and merge procedures.

The agent may create or switch to an appropriate short-lived branch, make the
requested changes, and run relevant checks. By default, the agent must not
commit, push, or merge. Instead, it should leave the working tree ready for
human review and suggest how the changes should be committed.

Every agent-authored change belongs on a short-lived branch. A trivial
documentation edit may need only manual verification, but it is not an
exception to branch protection or human review.

Before making changes, the agent must:

* Inspect the current branch, local and remote branches, and working tree.
* Reuse the current branch only when it clearly matches the task.
* Create an appropriately prefixed short-lived branch before editing if the
  current branch is `main` or unrelated to the task.
* Preserve unrelated local changes.

Before handing work back, the agent must:

* Run `python scripts/dev.py verify` for code, test, tooling, configuration,
  contract, or behavior changes.
* For a wording-, formatting-, or link-only documentation change, record a
  short manual verification note instead.
* Report verification failures clearly and leave the change uncommitted.
* Group changed files into logical commits and suggest Conventional Commit
  messages.

After completing work, the agent must provide a review summary followed by a commit proposal.

The review summary should be natural language. Briefly explain what changed,
why it changed, what to pay attention to, verification results, and any follow-up
if relevant.

**Commit proposal** should provide copyable shell commands for each suggested
commit. Use explicit file paths instead of `git add .`.

```bash
git add -- <file> <file>
git commit -m "<type>(optional-scope): <short description>"
```

For multiple commits, provide one command block per commit:

```bash
git add -- <file> <file>
git commit -m "<type>(optional-scope): <short description>"
git add -- <file> <file>
git commit -m "<type>(optional-scope): <short description>"
```

Then suggest the merge commit message:

```bash
git merge --no-ff <branch-name> -m "merge: <short summary>"
```

Must not:

* Commit unless the user explicitly asks.
* Push unless the user explicitly asks.
* Merge into `main` unless the user explicitly asks.
* Commit or push directly to `main`.
* Commit secrets, real PII, generated build artifacts, dependency folders,
  runtime state, or unrelated local changes.

## Definition of Done

A change is ready for review only when:

* The vertical slice still runs locally.
* Relevant tests pass or a manual verification note is added.
* `python scripts/dev.py verify` passes before merging to `main`; for trivial
  documentation changes, a short manual verification note is acceptable.
* No non-negotiable invariant is violated.
* API response shapes remain stable or docs are updated.
* Product-contract changes update `docs/demo-scope.md` in the same change.
* New behavior stays inside the v0.1 scope.
* No secrets, real PII, generated build artifacts, or dependency folders are committed.

See [`docs/demo-scope.md`](docs/demo-scope.md) for the full milestone
acceptance criteria and product-level definition of done.
