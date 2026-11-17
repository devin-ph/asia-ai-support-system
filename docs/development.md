# Development

Setup, daily commands, and release steps. The product contract lives in
[`demo-scope.md`](demo-scope.md); metric definitions live in
[`../eval/README.md`](../eval/README.md).

## Setup

Prerequisites: Python 3.12+ and Node.js 26 LTS (selected by `.nvmrc`;
`^22.22.2` and `^24.15.0` also work). CI covers Python 3.12 and 3.14 with Node
22 and 26.

```bash
python -m venv .venv
```

Activate it with `.\.venv\Scripts\Activate.ps1` on Windows PowerShell or
`source .venv/bin/activate` on macOS and Linux. Then install the locked
dependencies and check the environment:

```bash
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
python scripts/dev.py doctor
```

Run the backend and frontend in two terminals, then open
`http://127.0.0.1:5173` (API docs at `http://127.0.0.1:8000/docs`):

```bash
python scripts/dev.py backend
python scripts/dev.py frontend
```

### Optional OpenAI generator

Template mode is the default and needs no `.env`, key, or network. To try the
OpenAI generator, copy `.env.example` to the ignored `.env` and set:

```dotenv
ASIA_RESPONSE_GENERATOR=openai
ASIA_LLM_API_KEY=<local-secret>
ASIA_LLM_MODEL=gpt-5.4-mini-2026-03-17
ASIA_LLM_TIMEOUT_SECONDS=15
```

Process environment values override `.env`. The generator is called only after
local retrieval finds sufficient evidence, at an endpoint pinned in code.

## Commands

| Command | Purpose |
| --- | --- |
| `python scripts/dev.py doctor` | Validate runtimes, locks, imports, frontend setup, and provider settings |
| `python scripts/dev.py test` | Backend and frontend unit/component tests |
| `python scripts/dev.py eval` | Frozen v0.1 deterministic baseline |
| `python scripts/dev.py eval --suite v0.2` | Offline v0.2 retrieval, groundedness, citation, and routing gates |
| `python scripts/dev.py verify` | Pre-commit gate: lint, format, tests, both eval suites, typecheck, build, hygiene, secret scan |
| `python scripts/dev.py verify --security` | Also audit the locked Python and npm dependency graphs |
| `python scripts/dev.py reset-demo` | Restore ignored ticket state from the synthetic seed |
| `npm run e2e --prefix frontend` | Playwright browser flows (run `npx playwright install chromium` once) |

CI runs `doctor`, `verify --security`, and E2E on every push and once a week,
in template mode with no provider credential. Dependabot opens grouped weekly
update PRs.

## Releasing v0.2.0

1. Configure the OpenAI generator above with the pinned model, and set a hard
   budget limit on the OpenAI project first. One run is 21 short calls.
2. Run `python scripts/dev.py eval --suite v0.2 --live`. It reads `.env`,
   makes one attempt per case with no retries, and writes an ignored
   `var/eval/live-result-*.json`. A run with any provider fallback cannot be
   used; rerun it.
3. Give every case a `human_score` of 0, 1, or 2 using the rubric in
   `eval/README.md`. Each case holds the generated `answer_text`; match it by
   `id` to the question and required claims in
   `eval/v0.2/grounded_generation.vi.jsonl`. Score what the answer says, not
   the automated flags.
4. Run `python scripts/dev.py eval --suite v0.2 --curate-reference <file>`. It
   validates the run and writes `eval/results/v0.2-reference.json`.
5. Commit the reference on `main`, run
   `python scripts/dev.py verify --release` and the E2E suite, then tag
   `v0.2.0`.

## Demo walkthrough

| Proof | Try | Expected |
| --- | --- | --- |
| Retrieval beyond keywords | `Chính sách giao hàng cho biết dữ liệu hành trình được tổng hợp từ đâu?` | Finds `Theo dõi hành trình`; the frozen keyword search does not |
| Refusal | `Có chính sách giao nhanh không?` | Insufficient context, no citation, no generator call |
| Order privacy | `Tra cứu đơn hàng ASIA-1001 giúp tôi` | Safe fields only; `ASIA-9999` (not owned) looks identical to an unknown ID |
| Confirmation guardrail | `Tôi muốn tạo phiếu hỗ trợ vì sản phẩm bị lỗi` | Cancel creates nothing; confirm creates exactly one ticket, even if repeated |
| Fallback | `python -m pytest backend/tests/test_grounded_policy.py -k "safe_fallback and timeout"` | A forced timeout returns the evidence template with a trusted citation |

## Updating dependencies

Dependabot handles routine updates. For a manual Python change, edit
`backend/requirements.in`, then:

```bash
python -m pip install pip-tools
python -m piptools compile --upgrade --allow-unsafe --strip-extras backend/requirements.in -o backend/requirements.txt
python -m piptools sync backend/requirements.txt
```

Frontend dependencies are locked by `frontend/package-lock.json`. When a Node
major changes, update `frontend/package.json`, `scripts/dev.py`, `.nvmrc`, and
CI together.

## Repository map

| Path | Contents |
| --- | --- |
| `backend/` | FastAPI app, provider boundaries, services, tests |
| `frontend/` | React UI, component tests, Playwright flows |
| `docs/demo-scope.md` | Product contract and invariants |
| `docs/decisions/` | Architecture Decision Records |
| `docs/releases/` | Release evidence and invariant-to-test map |
| `docs/policies/` | Trusted synthetic policy corpus |
| `eval/` | Versioned Vietnamese cases, frozen baselines, targets |
| `data/fixtures/` | Immutable synthetic fixtures |
| `var/` | Ignored runtime state |
| `scripts/` | `dev.py` workflow entry point and `evaluate.py` harness |

## Known limitations

- Intent and sentiment are keyword-based until the v0.3 LLM analyzer.
  Generation is single-turn and uses only the top evidence section.
- One fixed synthetic customer; no authentication or tenant isolation.
- Pending actions and counters are process-local; tickets go to an ignored
  local JSON file.
- The health endpoint and frontend package report contract version `0.1`,
  because v0.2 keeps the public API unchanged.
