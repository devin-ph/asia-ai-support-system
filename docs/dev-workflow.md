# Git Workflow Rules

This project uses a lightweight branch-based workflow to keep `main` stable and demo-ready.

## Branch roles

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
* `ci/...` for CI/CD workflow changes.

Examples:

* `chore/v0.1.1-alignment`
* `fix/runtime-ticket-storage`
* `docs/frontend-agents`
* `test/frontend-confirmation-flow`
* `ci/github-actions-verify`
* `refactor/provider-boundaries`
* `feat/rag-provider`

## Before starting work

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

## Completion flow

For normal implementation tasks, must finish by committing the intentional changes and pushing the current working branch.

Before committing, confirm that the current branch is not `main`:

```bash
git branch --show-current
```

If the output is main, create an appropriate short-lived branch first:
```bash
git checkout -b <prefix>/<short-slug>
```

Recommended command sequence:

```bash
git status
git branch --show-current
python scripts/dev.py verify
git add <intentional-files-only>
git commit -m "<type>(<scope>): <short description>"
git push -u origin <current-branch>
```

Rules:

* Commit only intentional tracked changes.
* Use a Conventional Commits message.
* Push the current branch to `origin` when authentication is available.
* Do not push directly to `main`.
* Do not merge into `main` unless the user explicitly asks.
* Do not commit secrets, real PII, generated build artifacts, dependency folders, runtime state, or unrelated local changes.
* If verification fails, stop and report the failure. Do not commit unless the user explicitly asks for a work-in-progress commit.
* For docs-only changes, full verification may be replaced with a short manual verification note.

After finishing, report:

* changed files;
* verification result;
* commit hash;
* pushed branch;
* any remaining manual follow-up.

## Before merging to main

Run the project verification commands documented in this repo.

Use:

```bash
python scripts/dev.py verify
```

Only merge when:

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
