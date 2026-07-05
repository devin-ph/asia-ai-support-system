# Git Workflow Rules

This project uses a lightweight branch-based workflow to keep `main` stable and demo-ready.

## Branch roles

* `main` must stay stable, runnable, and demo-ready.
* Do not commit experimental or half-broken work directly to `main`.
* Use a short-lived branch for every agent-authored change.

Use branch prefixes consistently:

* `feat/...` for real product features.
* `fix/...` for bug fixes.
* `docs/...` for documentation-only changes.
* `test/...` for adding or updating tests.
* `chore/...` for tooling, harnessing, setup, verification scripts, dependency/config cleanup.
* `refactor/...` for code structure changes that should not alter behavior.
* `ci/...` for CI/CD workflow changes.

Examples:

* `chore/v0.1.1-alignment`
* `fix/runtime-ticket-storage`
* `docs/frontend-agents`
* `test/frontend-confirmation-flow`
* `ci/github-actions-verify`
* `refactor/provider-boundaries`
* `feat/rag-provider`

## Branch workflow

Inspect the repository before switching branches or editing files:

```bash
git status
git branch --show-current
git branch --list
git branch -r
```

Continue on the current branch only when it clearly matches the task. Otherwise,
start from an up-to-date `main` and create a focused branch:

```bash
git checkout main
git pull --ff-only origin main
git checkout -b chore/v0.1.1-alignment
```

Do not switch branches or pull while unrelated local changes are present.

Every agent-authored change uses a short-lived branch. In this workflow,
“trivial” means a wording, formatting, or link correction that does not change
runnable code, configuration, dependencies, agent instructions, the product or
API contract, or a safety rule. Trivial changes may use manual verification,
but they do not bypass branch protection or human review.

## Commit message rules (Conventional Commits)

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

## Commit planning

When the agent finishes a task, it should propose commit groups instead of
committing automatically.

Use one commit when the changes are part of one logical unit. Split commits when
there are clearly separate purposes, such as implementation, tests, docs, or
workflow/tooling. Use the exact handoff format defined in the root `AGENTS.md`
so the plan stays consistent across tasks.

## Agent-assisted work

For agent-assisted work, keep the workflow simple: make changes on a short-lived
branch, run relevant checks, then stop before committing. The agent should
suggest commit grouping and messages, but the human decides when to commit,
push, and merge.

Recommended work sequence:

```bash
git status
git branch --show-current
python scripts/dev.py verify
git diff --name-only
git diff --stat
```

Use `python scripts/dev.py test` for the fast development loop. Use `verify` for
the final readiness check; it includes tests, deterministic baseline drift,
frontend typecheck and build, repository hygiene, credential-pattern scanning,
and diff checks.

Rules:

* Work on a short-lived branch, not directly on `main`.
* Keep changes inside the requested scope.
* Do not commit, push, or merge unless the user explicitly asks.
* Do not use `git add .` unless the diff has been reviewed and every changed
  file is intentional.
* Do not include secrets, real PII, generated build artifacts, dependency
  folders, runtime state, or unrelated local changes.
* If verification fails, report the failure and leave the change uncommitted.
* A trivial documentation change, as defined above, may use a short manual
  verification note instead of the full verification command.

After finishing, use the handoff format in the root `AGENTS.md`. The review
commands must include working-tree changes because agent work is intentionally
left uncommitted.

## Manual review commands

Use these commands to review a branch before merging it into `main`:

```bash
git status
git branch --show-current
git log main..HEAD --oneline
git diff main...HEAD --name-only
git diff main...HEAD --stat
git diff main...HEAD
```

For reviewing staged changes before committing:

```bash
git diff --staged
```

For reviewing all committed and uncommitted changes against `main`:

```bash
git status --short
git diff main
```

## Before merging to main

Run the project verification commands documented in this repo.

Use:

```bash
python scripts/dev.py verify
```

Only merge when:

* intentional changes have been reviewed and committed by the human;
* the working tree is clean after committing intentional changes;
* backend tests pass;
* frontend component tests and typecheck/build pass;
* demo-critical flows are not broken;
* tracked fixtures are not dirtied by runtime/demo data;
* the change matches the current milestone scope.

## Merge workflow and merge commits

When integrating a branch into `main`, prefer merge commits for non-trivial branches to preserve branch context.

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

## Milestones and tags

Use Git tags to mark stable demo milestones.

Examples:

```bash
git tag -a v0.1.0 -m "A.S.I.A v0.1 runnable vertical slice"
git push origin v0.1.0
```

Use tags for stable snapshots. Do not keep many long-lived demo branches unless there is a specific reason.

## Branch cleanup

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
