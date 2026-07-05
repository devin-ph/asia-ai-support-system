"""Evaluate the deterministic v0.1 support baseline against JSONL cases."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
EVAL_DIR = ROOT / "eval"
DEFAULT_BASELINE = EVAL_DIR / "baseline.v0.1.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.order_service import extract_order_reference  # noqa: E402
from app.policy_search import search_policy  # noqa: E402
from app.storage import load_tickets  # noqa: E402
from app.ticket_service import TicketService  # noqa: E402
from app.intent import detect_intent  # noqa: E402

DATASET_PATHS = {
    "intent": EVAL_DIR / "intent_cases.vi.jsonl",
    "policy": EVAL_DIR / "policy_queries.vi.jsonl",
    "order": EVAL_DIR / "order_queries.vi.jsonl",
    "ticket": EVAL_DIR / "ticket_flow_cases.jsonl",
}


class EvaluationDataError(ValueError):
    """Raised when an evaluation dataset violates its contract."""


@dataclass(frozen=True)
class MetricResult:
    """One exact-match metric and its actionable failure list."""

    passed: int
    total: int
    failures: tuple[str, ...] = ()

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def snapshot(self) -> dict[str, int | float]:
        return {
            "score": round(self.score, 6),
            "passed": self.passed,
            "total": self.total,
        }


def load_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    """Load UTF-8 JSONL and enforce non-empty, unique case identifiers."""
    if not path.is_file():
        raise EvaluationDataError(f"Dataset not found: {path}")

    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw_line.strip():
            continue
        try:
            case = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise EvaluationDataError(
                f"{path.name}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(case, dict):
            raise EvaluationDataError(
                f"{path.name}:{line_number}: each case must be an object"
            )
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise EvaluationDataError(
                f"{path.name}:{line_number}: id must be a non-empty string"
            )
        if case_id in seen_ids:
            raise EvaluationDataError(
                f"{path.name}:{line_number}: duplicate id {case_id!r}"
            )
        seen_ids.add(case_id)
        cases.append(case)

    if not cases:
        raise EvaluationDataError(f"Dataset is empty: {path}")
    return tuple(cases)


def evaluate_intents(cases: tuple[dict[str, Any], ...]) -> MetricResult:
    failures: list[str] = []
    for case in cases:
        predicted = detect_intent(_required_string(case, "text")).value
        expected = _required_string(case, "expected_intent")
        if predicted != expected:
            failures.append(f"{case['id']}: expected={expected}, got={predicted}")
    return MetricResult(len(cases) - len(failures), len(cases), tuple(failures))


def evaluate_policies(
    cases: tuple[dict[str, Any], ...],
) -> tuple[MetricResult, MetricResult]:
    section_total = 0
    section_hits = 0
    section_failures: list[str] = []
    predicted_insufficient = 0
    correct_insufficient = 0
    insufficient_failures: list[str] = []

    for case in cases:
        result = search_policy(_required_string(case, "query"))
        is_insufficient = not result.citations
        expects_insufficient = case.get("expected") == "insufficient_context"

        if is_insufficient:
            predicted_insufficient += 1
            if expects_insufficient:
                correct_insufficient += 1
            else:
                insufficient_failures.append(
                    f"{case['id']}: predicted insufficient for a trusted section"
                )

        if expects_insufficient:
            continue

        expected_policy = _required_string(case, "expected_policy")
        expected_section = _required_string(case, "expected_section")
        section_total += 1
        hit = any(
            Path(citation.source).name == expected_policy
            and citation.section == expected_section
            for citation in result.citations
        )
        if hit:
            section_hits += 1
        else:
            returned = [
                f"{Path(citation.source).name}#{citation.section}"
                for citation in result.citations
            ]
            section_failures.append(
                f"{case['id']}: expected={expected_policy}#{expected_section}, "
                f"got={returned or ['insufficient_context']}"
            )

    return (
        MetricResult(section_hits, section_total, tuple(section_failures)),
        MetricResult(
            correct_insufficient,
            predicted_insufficient,
            tuple(insufficient_failures),
        ),
    )


def evaluate_order_extraction(
    cases: tuple[dict[str, Any], ...],
) -> MetricResult:
    failures: list[str] = []
    for case in cases:
        expected = case.get("expected_order_id")
        if expected is not None and not isinstance(expected, str):
            raise EvaluationDataError(
                f"{case['id']}: expected_order_id must be a string or null"
            )
        predicted = extract_order_reference(_required_string(case, "text"))
        if predicted != expected:
            failures.append(
                f"{case['id']}: expected={expected!r}, got={predicted!r}"
            )
    return MetricResult(len(cases) - len(failures), len(cases), tuple(failures))


def _evaluate_ticket_case(case: dict[str, Any], tickets_path: Path) -> list[str]:
    service = TicketService(tickets_path)
    action = service.draft_ticket(_required_string(case, "summary"))
    failures: list[str] = []

    if action.status.value != "pending" or service.ticket_count != 0:
        failures.append("draft created a ticket or was not pending")

    decisions = case.get("decisions")
    if not isinstance(decisions, list) or not all(
        isinstance(decision, bool) for decision in decisions
    ):
        raise EvaluationDataError(
            f"{case['id']}: decisions must be a list of booleans"
        )

    mode = _required_string(case, "mode")
    target_id = (
        "act_missing"
        if mode == "unknown_action"
        else action.action_id
    )
    if mode == "concurrent":
        with ThreadPoolExecutor(max_workers=len(decisions) or 1) as executor:
            resolutions = list(
                executor.map(
                    lambda decision: service.resolve_action(
                        target_id,
                        confirm=decision,
                    ),
                    decisions,
                )
            )
    elif mode in {"sequential", "unknown_action"}:
        resolutions = [
            service.resolve_action(target_id, confirm=decision)
            for decision in decisions
        ]
    else:
        raise EvaluationDataError(
            f"{case['id']}: unsupported ticket mode {mode!r}"
        )

    actual_statuses = [
        resolution.status.value if resolution is not None else None
        for resolution in resolutions
    ]
    expected_statuses = case.get("expected_statuses")
    if actual_statuses != expected_statuses:
        failures.append(
            f"statuses expected={expected_statuses!r}, got={actual_statuses!r}"
        )

    if "expected_repeated" in case:
        actual_repeated = [
            resolution.repeated if resolution is not None else None
            for resolution in resolutions
        ]
        if actual_repeated != case["expected_repeated"]:
            failures.append(
                "repeated flags "
                f"expected={case['expected_repeated']!r}, got={actual_repeated!r}"
            )

    expected_count = case.get("expected_ticket_count")
    persisted_count = len(load_tickets(tickets_path))
    if service.ticket_count != expected_count or persisted_count != expected_count:
        failures.append(
            f"ticket count expected={expected_count!r}, "
            f"memory={service.ticket_count}, persisted={persisted_count}"
        )

    if case.get("expect_same_ticket_id"):
        ticket_ids = [
            resolution.ticket_id
            for resolution in resolutions
            if resolution is not None and resolution.ticket_id is not None
        ]
        if not ticket_ids or len(set(ticket_ids)) != 1:
            failures.append(f"ticket IDs are not idempotent: {ticket_ids!r}")

    return failures


def evaluate_ticket_guardrail(
    cases: tuple[dict[str, Any], ...],
) -> MetricResult:
    failures: list[str] = []
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="asia-eval-") as directory:
            case_failures = _evaluate_ticket_case(
                case,
                Path(directory) / "demo_tickets.json",
            )
        if case_failures:
            failures.append(f"{case['id']}: {'; '.join(case_failures)}")
    return MetricResult(len(cases) - len(failures), len(cases), tuple(failures))


def _required_string(case: dict[str, Any], field: str) -> str:
    value = case.get(field)
    if not isinstance(value, str):
        raise EvaluationDataError(
            f"{case.get('id', '<unknown>')}: {field} must be a string"
        )
    return value


def run_evaluation() -> dict[str, MetricResult]:
    """Run all current deterministic services against versioned datasets."""
    intent_cases = load_jsonl(DATASET_PATHS["intent"])
    policy_cases = load_jsonl(DATASET_PATHS["policy"])
    order_cases = load_jsonl(DATASET_PATHS["order"])
    ticket_cases = load_jsonl(DATASET_PATHS["ticket"])
    policy_hit_rate, insufficient_precision = evaluate_policies(policy_cases)

    return {
        "intent_accuracy": evaluate_intents(intent_cases),
        "policy_section_hit_rate": policy_hit_rate,
        "insufficient_context_precision": insufficient_precision,
        "order_id_extraction_accuracy": evaluate_order_extraction(order_cases),
        "confirmation_guardrail_pass_rate": evaluate_ticket_guardrail(
            ticket_cases
        ),
    }


def build_snapshot(results: dict[str, MetricResult]) -> dict[str, Any]:
    """Build a deterministic, versioned baseline artifact."""
    return {
        "baseline_id": "deterministic-v0.1",
        "evaluator_schema_version": 1,
        "metrics": {
            name: result.snapshot() for name, result in results.items()
        },
    }


def _print_report(results: dict[str, MetricResult]) -> None:
    print("A.S.I.A deterministic evaluation baseline\n")
    for name, result in results.items():
        print(
            f"{name}: {result.score:.1%} "
            f"({result.passed}/{result.total})"
        )
        for failure in result.failures:
            print(f"  - {failure}")


def _check_baseline(snapshot: dict[str, Any], path: Path) -> bool:
    try:
        expected = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"\nBaseline snapshot not found: {path}", file=sys.stderr)
        return False
    except json.JSONDecodeError as exc:
        print(f"\nInvalid baseline snapshot: {exc}", file=sys.stderr)
        return False

    if snapshot == expected:
        print(f"\nBaseline snapshot matches {path.relative_to(ROOT)}.")
        return True
    print(
        f"\nBaseline drift detected in {path.relative_to(ROOT)}. "
        "Review the metric changes and update the snapshot intentionally.",
        file=sys.stderr,
    )
    return False


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Measure the deterministic v0.1 baseline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the deterministic snapshot as JSON",
    )
    parser.add_argument(
        "--check-baseline",
        type=Path,
        metavar="PATH",
        help="Fail when current metrics differ from a committed snapshot",
    )
    args = parser.parse_args()

    try:
        results = run_evaluation()
    except EvaluationDataError as exc:
        print(f"Evaluation data error: {exc}", file=sys.stderr)
        return 2

    snapshot = build_snapshot(results)
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        _print_report(results)

    if args.check_baseline is not None:
        baseline_path = args.check_baseline
        if not baseline_path.is_absolute():
            baseline_path = ROOT / baseline_path
        return 0 if _check_baseline(snapshot, baseline_path) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
