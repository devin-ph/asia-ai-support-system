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

## Standard Commands

Use these commands when possible:

```bash
python scripts/dev.py doctor
python scripts/dev.py backend
python scripts/dev.py frontend
python scripts/dev.py test
python scripts/dev.py verify
```

Use `doctor` to determine whether a newly cloned environment can run the full
project. It must validate supported runtime versions, installed dependencies,
backend importability, frontend scripts, and writable local state rather than
only checking whether executables exist.

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

This project uses a simple personal-project branching workflow.

### Branch roles

* `main` must stay stable, runnable, and demo-ready.
* Do not commit experimental or half-broken work directly to `main`.
* Create a short-lived branch before making non-trivial changes.

Use branch prefixes consistently:

* `feat/...` for real product features.
* `fix/...` for bug fixes.
* `docs/...` for README, AGENTS.md, walkthroughs, architecture notes, and other documentation.
* `test/...` for adding or updating tests.
* `chore/...` for tooling, harnessing, setup, verification scripts, dependency/config cleanup.
* `refactor/...` for code structure changes that should not alter behavior.

Examples:

* `chore/v0.1.1-alignment`
* `fix/runtime-ticket-storage`
* `docs/frontend-agents`
* `test/frontend-confirmation-flow`
* `ci/github-actions-verify`
* `refactor/provider-boundaries`
* `feat/rag-provider`

### Commit message rules (Conventional Commits)

All commits should follow the Conventional Commits format:

<type>(optional-scope): <short description>

Common types:

* `feat`: new feature
* `fix`: bug fix
* `docs`: documentation changes
* `test`: adding or updating tests
* `chore`: tooling, scripts, config, maintenance
* `refactor`: code changes without behavior change
* `ci`: CI/CD related changes

Examples:

```bash
git commit -m "feat(rag): add provider abstraction"
git commit -m "fix(runtime): persist ticket storage correctly"
git commit -m "docs(frontend): add AGENTS.md for UI rules"
git commit -m "test(frontend): cover confirmation flow"
git commit -m "chore(verify): add unified verification command"
```

### Before starting work

Start from an up-to-date `main`:

```bash
git checkout main
git pull --ff-only origin main
git status
```

Then create a focused branch:

```bash
git checkout -b chore/v0.1.1-alignment
```

### Before merging to main

Run the project verification commands documented in this repo.

Use:

```bash
python scripts/dev.py verify
```

Only merge when:

* the working tree is clean except for intentional changes;
* backend tests pass;
* frontend typecheck/build pass;
* demo-critical flows are not broken;
* tracked fixtures are not dirtied by runtime/demo data;
* the change matches the current milestone scope.

### Merge workflow and merge commits

When integrating a branch into `main`, use a merge commit (do not squash) so that the branch context is preserved.

Example:

```bash
git checkout main
git pull --ff-only origin main
git merge --no-ff chore/verification-harness -m "merge: integrate verification harness and workflow guidelines"
git push origin main
```

Guidelines:

* Always ensure the branch has passed verification before merging.
* Use a clear merge commit message describing what is being integrated.
* Prefer `--no-ff` to keep a visible history of feature/chore branches.
* After merging, verify again on `main` if needed.

### Milestones and tags

Use Git tags to mark stable demo milestones.

Examples:

```bash
git tag -a v0.1.0 -m "A.S.I.A v0.1 runnable vertical slice"
git push origin v0.1.0
```

Use tags for stable snapshots. Do not keep many long-lived demo branches unless there is a specific reason.

### Branch cleanup

After a branch has been merged into `main` and `main` is stable, delete the branch locally and remotely if it is no longer needed.

Check merged local branches:

```bash
git branch --merged main
```

Delete a merged local branch:

```bash
git branch -d branch-name
```

Delete the remote branch:

```bash
git push origin --delete branch-name
```

Sync/prune stale remote references:

```bash
git fetch --prune origin
```

Do not delete:

* `main`;
* the current branch;
* unmerged branches;
* milestone tags;
* branches that intentionally preserve a long-running experiment.

## Definition of Done

A change is done only when:

* The vertical slice still runs locally.
* Relevant tests pass or a manual verification note is added.
* `python scripts/dev.py verify` passes before commit or pull request.
* API response shapes remain stable or docs are updated.
* New behavior stays inside the v0.1 scope.
* No secrets, real PII, generated build artifacts, or dependency folders are committed.
