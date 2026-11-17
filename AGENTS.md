# AGENTS.md

## Project

A.S.I.A is a Vietnamese customer-support demo built to show least-authority AI:
the application owns evidence, citations, and every write, and the model only
proposes. The current milestone is **v0.2.0: Evidence-Grounded Policy
Assistant**. The planned **v0.3.0** turns it into a Vietnamese support-agent
safety benchmark and starts only after the `v0.2.0` tag.

## Read first

1. [`docs/demo-scope.md`](docs/demo-scope.md): the product contract and the
   only source of truth for scope, API, labels, and invariants.
2. [`GLOSSARY.md`](GLOSSARY.md): canonical terms. Use them, and do not
   introduce synonyms.
3. [`eval/README.md`](eval/README.md) when touching evaluation.
4. `backend/AGENTS.md` or `frontend/AGENTS.md` when working in those folders.

Do not build features outside the scope document unless the user asks. When a
change touches the API, labels, tool semantics, storage behavior, invariants,
evaluation datasets, or acceptance criteria, update `docs/demo-scope.md` in the
same change. Record durable technical choices as short ADRs in
`docs/decisions/`. Do not write parallel specs that restate them.

## Commands

```bash
python scripts/dev.py doctor          # check the local environment
python scripts/dev.py backend         # FastAPI on :8000
python scripts/dev.py frontend        # Vite on :5173
python scripts/dev.py test            # fast unit/component loop
python scripts/dev.py eval            # frozen v0.1 baseline
python scripts/dev.py eval --suite v0.2
python scripts/dev.py verify          # gate before committing
python scripts/dev.py verify --security
```

## Non-negotiable invariants

1. Repository fixtures contain synthetic data only.
2. Policy claims require matching repository evidence.
3. Order details require a fixed-customer ownership check.
4. Ticket creation happens only in the confirmation endpoint.
5. Confirmation is idempotent per action ID.
6. API and admin responses do not expose unsafe order fields or stored message content.
7. Tests write tickets only to temporary files, never to the repository fixture.
8. Runtime ticket writes never mutate files under `data/fixtures/`.
9. Secrets and credentials are never committed.
10. The chat route has no direct access to a ticket write provider.

If a change would break one, stop and report the conflict.

Also: treat `data/fixtures/` as immutable, write runtime state only under the
ignored `var/`, and never send order, ticket, pending-action, admin,
conversation, or log data to an external provider.

## Git

The owner runs every Git write command. Agents never stage, commit, amend,
branch, merge, rebase, tag, or push, even when a change is finished. Read-only
commands such as `git status`, `git diff`, and `git log` are fine.

- Everyday work happens directly on `main`. A branch is worth it only for risky
  or multi-day work, such as the v0.3 harness refactor.
- When a task is done, suggest the commands for the owner to run: one
  `git add -- <explicit paths>` and one Conventional Commit message per
  finished task. Split only when it clearly helps.
- Suggested commit messages carry no `Co-Authored-By` or other AI attribution
  trailer.
- Never suggest committing secrets, real PII, `var/`, `node_modules/`, or build
  output.
- CI runs on every push and weekly. If `main` goes red, the next commit fixes it.
- Releases are annotated tags on `main`.

## Done

- `python scripts/dev.py verify` passes for code, test, config, or contract
  changes. For a docs-only edit, a short manual check is enough.
- No invariant is broken, and the scope document matches any contract change.
- Report failures plainly. Suggest commit commands only for work that passes.
