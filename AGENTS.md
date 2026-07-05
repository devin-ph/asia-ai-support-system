# AGENTS.md

## Project

A.S.I.A is a demo AI customer support system for Vietnamese e-commerce support.

The current milestone is **v0.1: Runnable Vertical Slice**.

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

Use `doctor` to determine whether a newly cloned environment can run the full
project. It must validate supported runtime versions, installed dependencies,
backend importability, frontend scripts, and writable local state rather than
only checking whether executables exist.

Use `test` for the fast backend and frontend unit/component test loop. Use
`eval` to measure the versioned deterministic baseline. Use `verify` before
commit or pull request to add the baseline drift check, frontend
typecheck/build, and repository hygiene checks.

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

## Git Behavior

Use a branch-first, human-commit workflow that keeps `main` runnable and
demo-ready. Follow `docs/dev-workflow.md` for branch prefixes, detailed Git
commands, commit guidance, and merge and cleanup procedures.

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

After completing work, report exactly in this format:

```text
Branch        : <current-branch>
Verify        : PASSED | FAILED | SKIPPED (<reason>)
Scope check   : all changes within scope | <out-of-scope notes>

Changed files:
  Commit 1 – "<type>(<scope>): <message>"
    - <file>
    - <file>

Suggested merge commit:
  "merge: <summary>"

Review commands:
  git status --short
  git diff main
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
* API response shapes remain stable or docs are updated.
* New behavior stays inside the v0.1 scope.
* No secrets, real PII, generated build artifacts, or dependency folders are committed.
