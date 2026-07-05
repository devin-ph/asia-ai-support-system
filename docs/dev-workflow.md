# Git Workflow Rules

This project uses a lightweight branch-based workflow to keep `main` stable and demo-ready.

## Branch roles

* `main` must stay stable, runnable, and demo-ready.
* Do not commit experimental or half-broken work directly to `main`.
* Use a short-lived branch for every proposed change.

Use branch prefixes consistently:

* `feat/...` for real product features.
* `fix/...` for bug fixes.
* `docs/...` for README, AGENTS.md, walkthroughs, architecture notes, and other documentation.
* `test/...` for adding or updating tests.
* `chore/...` for tooling, scripts, config, maintenance, dependency/config cleanup.
* `refactor/...` for code structure changes that should not alter behavior.
* `ci/...` for CI/CD workflow changes.

Examples:

* `chore/v0.1.1-alignment`
* `fix/runtime-ticket-storage`
* `docs/clarify-demo-scope`
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
workflow/tooling.

See the root `AGENTS.md` for review summary and commit proposal guidance.

## Assisted workflows

For assisted workflows, keep the workflow simple: make changes on a short-lived
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

Final response should include a natural review summary followed by a lightweight
commit proposal as described in the root `AGENTS.md`.

## Branch cleanup

After a branch has been merged into `main` and `main` is stable, delete the
branch locally and remotely if it is no longer needed.

Always switch away from the branch before deleting it:

```bash
git checkout main
git pull --ff-only origin main
```

Check merged local branches:

```bash
git branch --merged main
```

Delete a merged local branch:

```bash
git branch -d branch-name
```

If a branch was integrated through squash merge or rebase, it may not appear in
git branch --merged main because the original branch commits are not directly
reachable from main.

Before force-deleting such a branch, inspect what remains different:

```bash
git log main..branch-name --oneline
git diff main...branch-name --stat
```

Only force-delete when the branch's work is already integrated, intentionally
superseded, or no longer needed:

```bash
git branch -D branch-name
```

Delete the remote branch when it still exists:

```bash
git push origin --delete branch-name
```

Some hosting platforms can automatically delete remote branches after merge.
After remote cleanup, sync/prune stale remote-tracking references:

```bash
git fetch --prune origin
```

Use `git branch -D` only when intentionally discarding or cleaning up work that
has already been accounted for.

Do not delete:

* `main`;
* the current branch;
* unmerged branches;
* milestone tags;
* branches that intentionally preserve a long-running experiment.
