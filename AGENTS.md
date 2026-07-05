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
* Ticket creation must require explicit user confirmation.
* Repeated confirmation must not create duplicate tickets.
* If policy evidence is missing, return an insufficient-context response instead of inventing an answer.
* Order lookup must only return safe fields and must enforce the fixed demo customer ownership check.

## Git Workflow Rules

This project uses a lightweight branch-based workflow to keep `main` stable and demo-ready.

* `main` must always be runnable and suitable for demo.
* Do not commit experimental or half-broken work directly to `main`.
* Create a short-lived branch before non-trivial changes.
* Follow Conventional Commits for commit messages.
* Run `python scripts/dev.py verify` before merging back to `main`.
* Prefer merge commits for non-trivial branches to preserve branch context.
* Delete merged short-lived branches after `main` is stable.

Use branch prefixes:

* `feat/...`
* `fix/...`
* `docs/...`
* `test/...`
* `chore/...`
* `refactor/...`
* `ci/...`

For detailed Git commands, see `docs/dev-workflow.md`.

## Git Behavior

For non-trivial implementation, test, refactor, documentation, or tooling tasks, always complete the Git workflow instead of only suggesting Git commands.

Must:

* Check the current branch. If on `main`, create an appropriate short-lived branch first. Never commit directly to `main`.
* Inspect the working tree with `git status`.
* Run `python scripts/dev.py verify` before committing code, test, tooling, or behavior changes.
* For docs-only changes, full verification may be replaced with a short manual verification note.
* If verification fails, stop and report the failure immediately. Do not commit unless the user explicitly asks for a work-in-progress commit.
* Stage only intentional files.
* Create a Conventional Commit.
* Push the current working branch to `origin` if authentication and remote access are available.
* Report results in this format:

  Branch   : <name>
  Commit   : <hash> – "<message>"
  Verify   : PASSED | FAILED
  Push     : SUCCESS | FAILED
  Follow-up: <manual steps or blockers if any>

Must not:

* Commit directly to `main`.
* Push directly to `main`.
* Merge into `main` unless the user explicitly asks.
* Commit secrets, real PII, generated build artifacts, dependency folders, runtime state, or unrelated local changes.

For the detailed command sequence, see `docs/dev-workflow.md`.

## Definition of Done

A change is done only when:

* The vertical slice still runs locally.
* Relevant tests pass or a manual verification note is added.
* `python scripts/dev.py verify` passes before merging to `main`; for docs-only changes, add a short manual verification note if full verification is unnecessary.
* API response shapes remain stable or docs are updated.
* New behavior stays inside the v0.1 scope.
* No secrets, real PII, generated build artifacts, or dependency folders are committed.
