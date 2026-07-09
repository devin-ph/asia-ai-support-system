# Git Workflow Rules

This project uses a lightweight Git workflow to keep `main` stable and demo-ready
without turning every change into ceremony.

## Main rules

* `main` must stay stable, runnable, and demo-ready.
* Do not commit experimental or half-broken work directly to `main`.
* Keep changes inside the requested scope.
* Do not commit secrets, real PII, generated build artifacts, dependency
  folders, runtime state, or unrelated local changes.

## Branching

Use a short-lived branch for non-trivial work: code, tests, configuration,
dependencies, CI, product contract, safety rules, agent instructions, or changes
that may need review before reaching `main`.

Small wording, formatting, or link-only documentation edits may stay on the
current branch when the working tree is clean. A documentation-only edit is
trivial only if it does not change agent instructions, the product contract,
safety rules, runnable code, configuration, or dependencies.

Prefer these branch prefixes:

* `feat/...` for product features.
* `fix/...` for bug fixes.
* `test/...` for tests.
* `chore/...` for tooling, scripts, config, maintenance, or dependencies.
* `refactor/...` for structure changes without intended behavior changes.
* `ci/...` for CI/CD changes.
* `docs/...` for documentation-only work that changes guidance, scope, ADRs,
  README, or architecture notes.

Before editing, check the repository state:

```bash
git status
git branch --show-current
```

Reuse the current branch when it clearly matches the task. Otherwise, start from
an up-to-date `main` and create a focused branch:

```bash
git checkout main
git pull --ff-only origin main
git checkout -b <type>/<short-slug>
```

Do not switch branches or pull while unrelated local changes are present.

If a tool creates a vendor-prefixed branch such as `codex/...`, it is not fatal.
Rename it before merge when a clean project branch name is useful.

## Commits

Use Conventional Commits:

```text
<type>(optional-scope): <short description>
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `ci`, `style`.

Optimize commits for review, but do not over-split:

* Use one commit for a cohesive change.
* Split commits only when it meaningfully improves review, such as separating
  code behavior, tests, docs, CI/tooling, dependencies, or mechanical formatting.
* Most small tasks need one commit. Most medium tasks need one to three commits.

Use explicit paths in commit proposals:

```bash
git add -- <file> <file>
git commit -m "<type>(optional-scope): <short description>"
```

Avoid `git add .` unless the full diff has been reviewed. Use `git add -p` when
one file contains unrelated logical changes.

## Checks

Use the smallest useful check while developing:

```bash
python scripts/dev.py test
```

Use the full gate before merging non-trivial changes to `main`:

```bash
python scripts/dev.py verify
```

Trivial documentation-only edits may use a short manual verification note.
If verification fails, report the failure and leave the change uncommitted.

## Integration

Use the simplest integration strategy that fits the change:

* Fast-forward or squash small/simple branches when a compact history is better.
* Use squash when the branch has noisy WIP commits that do not add review value.
* Use a normal merge commit only when preserving branch context is useful.
* When using a merge commit, prefer `merge: <short summary>`.
* Do not merge into `main` until the change has been reviewed and relevant checks
  have passed.

## Assisted workflows

By default, assisted work should inspect the repo, make the requested change, run
relevant checks, then stop before committing, pushing, or merging unless
explicitly asked.

Final responses should be helpful first and structured second: provide a natural
review summary and, when useful, copyable commit commands. Do not force a large
template when a concise note is enough.