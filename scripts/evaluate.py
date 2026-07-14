"""Evaluate v0.1 behavior and validate the frozen v0.2 evaluation contract."""

from __future__ import annotations

import argparse
import hashlib
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
V02_TARGET = EVAL_DIR / "baseline.v0.2.target.json"
V02_MANIFEST = EVAL_DIR / "v0.2" / "manifest.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.order_service import extract_order_reference  # noqa: E402
from app.policy_retrieval import (  # noqa: E402
    DEFAULT_TOP_K,
    EXACT_PHRASE_WEIGHT,
    HEADING_WEIGHT,
    LEXICAL_WEIGHT,
    MIN_RETRIEVAL_SCORE,
    NGRAM_WEIGHT,
    LocalPolicyRetriever,
)
from app.providers import default_chat_providers  # noqa: E402
from app.providers.tickets import LocalTicketProvider  # noqa: E402
from app.storage import load_tickets  # noqa: E402

DATASET_PATHS = {
    "intent": EVAL_DIR / "intent_cases.vi.jsonl",
    "policy": EVAL_DIR / "policy_queries.vi.jsonl",
    "order": EVAL_DIR / "order_queries.vi.jsonl",
    "ticket": EVAL_DIR / "ticket_flow_cases.jsonl",
}

V02_DATASET_PATHS = {
    "policy_retrieval": EVAL_DIR / "v0.2" / "policy_retrieval.vi.jsonl",
    "grounded_generation": EVAL_DIR / "v0.2" / "grounded_generation.vi.jsonl",
    "routing_safety": EVAL_DIR / "v0.2" / "routing_safety.vi.jsonl",
}

V02_POLICY_SOURCES = (
    "docs/policies/return_policy.md",
    "docs/policies/shipping_policy.md",
    "docs/policies/warranty_policy.md",
)

V02_EXPECTED_CASE_COUNTS = {
    "policy_retrieval": 50,
    "grounded_generation": 21,
    "routing_safety": 15,
}

V02_LOCKED_MINIMUMS = {
    "policy_section_hit_rate": 0.9,
    "unsupported_query_precision": 0.9,
    "unsupported_query_recall": 1.0,
    "grounded_response_pass_rate": 0.95,
    "citation_coverage_rate": 1.0,
    "citation_validity_rate": 1.0,
    "routing_precedence_contract_pass_rate": 1.0,
    "order_id_extraction_accuracy": 0.928571,
    "order_privacy_guardrail_pass_rate": 1.0,
    "confirmation_guardrail_pass_rate": 1.0,
    "provider_config_contract_pass_rate": 1.0,
    "fixture_immutability_pass_rate": 1.0,
}

_ROUTE_BY_INTENT = {
    "ticket_request": "ticket",
    "order_lookup": "order",
    "shipping_policy": "policy",
    "return_refund": "policy",
    "warranty": "policy",
    "other": "other",
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
            raise EvaluationDataError(f"{path.name}:{line_number}: each case must be an object")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise EvaluationDataError(f"{path.name}:{line_number}: id must be a non-empty string")
        if case_id in seen_ids:
            raise EvaluationDataError(f"{path.name}:{line_number}: duplicate id {case_id!r}")
        seen_ids.add(case_id)
        cases.append(case)

    if not cases:
        raise EvaluationDataError(f"Dataset is empty: {path}")
    return tuple(cases)


def _required_non_empty_string(case: dict[str, Any], field: str) -> str:
    value = _required_string(case, field)
    if not value.strip():
        raise EvaluationDataError(f"{case.get('id', '<unknown>')}: {field} must not be empty")
    return value


def _required_string_list(case: dict[str, Any], field: str) -> tuple[str, ...]:
    value = case.get(field)
    if not isinstance(value, list) or not value:
        raise EvaluationDataError(
            f"{case.get('id', '<unknown>')}: {field} must be a non-empty list"
        )
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise EvaluationDataError(
            f"{case.get('id', '<unknown>')}: {field} entries must be non-empty strings"
        )
    if len(set(value)) != len(value):
        raise EvaluationDataError(f"{case.get('id', '<unknown>')}: {field} entries must be unique")
    return tuple(value)


def _require_exact_fields(
    case: dict[str, Any],
    expected_fields: set[str],
) -> None:
    actual_fields = set(case)
    if actual_fields != expected_fields:
        missing = sorted(expected_fields - actual_fields)
        extra = sorted(actual_fields - expected_fields)
        raise EvaluationDataError(
            f"{case.get('id', '<unknown>')}: schema mismatch; missing={missing}, extra={extra}"
        )


def load_policy_catalog() -> dict[str, set[str]]:
    """Return repository-relative policy sources and their exact H2 sections."""
    catalog: dict[str, set[str]] = {}
    for source in V02_POLICY_SOURCES:
        path = ROOT / source
        if not path.is_file():
            raise EvaluationDataError(f"Allowlisted policy not found: {source}")
        sections = {
            line.removeprefix("## ").strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        }
        if not sections:
            raise EvaluationDataError(f"Policy has no H2 sections: {path.relative_to(ROOT)}")
        catalog[source] = sections
    return catalog


def _validate_evidence_reference(
    case: dict[str, Any],
    catalog: dict[str, set[str]],
) -> None:
    source = _required_non_empty_string(case, "expected_source")
    section = _required_non_empty_string(case, "expected_section")
    if source not in catalog:
        raise EvaluationDataError(f"{case['id']}: source is not allowlisted: {source}")
    if section not in catalog[source]:
        raise EvaluationDataError(f"{case['id']}: section {section!r} does not exist in {source}")


def _validate_policy_retrieval_cases(
    cases: tuple[dict[str, Any], ...],
    catalog: dict[str, set[str]],
) -> None:
    for case in cases:
        _required_non_empty_string(case, "query")
        _required_string_list(case, "tags")
        supported = case.get("supported")
        if not isinstance(supported, bool):
            raise EvaluationDataError(f"{case['id']}: supported must be a boolean")
        if supported:
            _require_exact_fields(
                case,
                {"id", "query", "supported", "expected_source", "expected_section", "tags"},
            )
            _validate_evidence_reference(case, catalog)
        else:
            _require_exact_fields(case, {"id", "query", "supported", "tags"})


def _validate_grounded_generation_cases(
    cases: tuple[dict[str, Any], ...],
    catalog: dict[str, set[str]],
) -> None:
    expected_fields = {
        "id",
        "query",
        "expected_source",
        "expected_section",
        "required_claims",
        "forbidden_patterns",
        "tags",
    }
    for case in cases:
        _require_exact_fields(case, expected_fields)
        _required_non_empty_string(case, "query")
        _required_string_list(case, "forbidden_patterns")
        _required_string_list(case, "tags")
        _validate_evidence_reference(case, catalog)

        claims = case.get("required_claims")
        if not isinstance(claims, list) or not claims:
            raise EvaluationDataError(f"{case['id']}: required_claims must be a non-empty list")
        claim_ids: set[str] = set()
        for claim in claims:
            if not isinstance(claim, dict) or set(claim) != {"id", "any_of"}:
                raise EvaluationDataError(
                    f"{case['id']}: each required claim needs only id and any_of"
                )
            claim_id = _required_non_empty_string(claim, "id")
            if claim_id in claim_ids:
                raise EvaluationDataError(f"{case['id']}: duplicate claim id {claim_id!r}")
            claim_ids.add(claim_id)
            _required_string_list(claim, "any_of")


def _validate_routing_cases(cases: tuple[dict[str, Any], ...]) -> None:
    expected_fields = {"id", "text", "expected_intent", "expected_route", "tags"}
    for case in cases:
        _require_exact_fields(case, expected_fields)
        _required_non_empty_string(case, "text")
        _required_string_list(case, "tags")
        intent = _required_non_empty_string(case, "expected_intent")
        route = _required_non_empty_string(case, "expected_route")
        if intent not in _ROUTE_BY_INTENT:
            raise EvaluationDataError(f"{case['id']}: unsupported intent {intent!r}")
        expected_route = _ROUTE_BY_INTENT[intent]
        if route != expected_route:
            raise EvaluationDataError(
                f"{case['id']}: route {route!r} does not match intent {intent!r}"
            )


def load_v02_datasets() -> dict[str, tuple[dict[str, Any], ...]]:
    """Load and validate every frozen v0.2 dataset without running new features."""
    datasets = {name: load_jsonl(path) for name, path in V02_DATASET_PATHS.items()}
    all_ids: set[str] = set()
    for name, cases in datasets.items():
        expected_count = V02_EXPECTED_CASE_COUNTS[name]
        if len(cases) != expected_count:
            raise EvaluationDataError(
                f"{name}: expected {expected_count} cases, found {len(cases)}"
            )
        case_ids = {case["id"] for case in cases}
        overlap = all_ids.intersection(case_ids)
        if overlap:
            raise EvaluationDataError(
                f"v0.2 case IDs must be globally unique; duplicates={sorted(overlap)}"
            )
        all_ids.update(case_ids)

    catalog = load_policy_catalog()
    _validate_policy_retrieval_cases(datasets["policy_retrieval"], catalog)
    _validate_grounded_generation_cases(datasets["grounded_generation"], catalog)
    _validate_routing_cases(datasets["routing_safety"])
    return datasets


def compute_dataset_hash(paths: dict[str, Path]) -> str:
    """Hash sorted paths and LF-normalized UTF-8 content for cross-platform stability."""
    digest = hashlib.sha256()
    for path in sorted(paths.values(), key=lambda item: item.relative_to(ROOT).as_posix()):
        relative_path = path.relative_to(ROOT).as_posix()
        content = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def compute_file_content_hash(path: Path) -> str:
    """Hash one UTF-8 file after newline normalization."""
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


def compute_v02_dataset_hash() -> str:
    """Return the canonical hash of all frozen v0.2 JSONL inputs."""
    return compute_dataset_hash(V02_DATASET_PATHS)


def compute_policy_corpus_hash() -> str:
    """Return the canonical hash of the explicitly allowlisted policy corpus."""
    return compute_dataset_hash({source: ROOT / source for source in V02_POLICY_SOURCES})


def build_v02_manifest_snapshot(
    datasets: dict[str, tuple[dict[str, Any], ...]],
) -> dict[str, Any]:
    """Build the exact manifest expected for the current frozen inputs."""
    return {
        "manifest_schema_version": 1,
        "suite": "v0.2",
        "frozen_on": "2026-07-14",
        "files": [
            {
                "name": name,
                "path": path.relative_to(ROOT).as_posix(),
                "cases": len(datasets[name]),
                "content_hash": compute_file_content_hash(path),
            }
            for name, path in V02_DATASET_PATHS.items()
        ],
        "combined_dataset_hash": compute_v02_dataset_hash(),
        "policy_sources": list(V02_POLICY_SOURCES),
        "policy_corpus_hash": compute_policy_corpus_hash(),
    }


def validate_v02_manifest(
    datasets: dict[str, tuple[dict[str, Any], ...]],
) -> dict[str, Any]:
    """Reject unreviewed drift between JSONL inputs and their committed manifest."""
    try:
        actual = json.loads(V02_MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationDataError(f"v0.2 manifest not found: {V02_MANIFEST}") from exc
    except json.JSONDecodeError as exc:
        raise EvaluationDataError(f"Invalid v0.2 manifest JSON: {exc}") from exc
    expected = build_v02_manifest_snapshot(datasets)
    if actual != expected:
        raise EvaluationDataError(
            "v0.2 manifest differs from its JSONL inputs or policy corpus; review drift first"
        )
    return actual


def validate_v02_target_contract(
    datasets: dict[str, tuple[dict[str, Any], ...]],
) -> dict[str, Any]:
    """Ensure the committed target still describes the frozen datasets and gates."""
    validate_v02_manifest(datasets)
    try:
        target = json.loads(V02_TARGET.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationDataError(f"Target contract not found: {V02_TARGET}") from exc
    except json.JSONDecodeError as exc:
        raise EvaluationDataError(f"Invalid v0.2 target JSON: {exc}") from exc
    if not isinstance(target, dict) or target.get("target_schema_version") != 2:
        raise EvaluationDataError("v0.2 target_schema_version must be 2")
    if target.get("baseline_reference") != "eval/baseline.v0.1.json":
        raise EvaluationDataError("v0.2 target must preserve the v0.1 baseline reference")

    contract = target.get("dataset_contract")
    if not isinstance(contract, dict):
        raise EvaluationDataError("v0.2 target dataset_contract must be an object")
    if contract.get("manifest") != "eval/v0.2/manifest.json":
        raise EvaluationDataError("v0.2 target must reference the frozen dataset manifest")
    if contract.get("expected_case_counts") != V02_EXPECTED_CASE_COUNTS:
        raise EvaluationDataError("v0.2 target case counts differ from the frozen evaluator")
    if contract.get("policy_sources") != list(V02_POLICY_SOURCES):
        raise EvaluationDataError("v0.2 target policy allowlist differs from the evaluator")
    actual_counts = {name: len(cases) for name, cases in datasets.items()}
    if actual_counts != V02_EXPECTED_CASE_COUNTS:
        raise EvaluationDataError("loaded v0.2 case counts differ from the target contract")
    dataset_hash = compute_v02_dataset_hash()
    if contract.get("dataset_hash") != dataset_hash:
        raise EvaluationDataError(
            "v0.2 dataset hash differs from baseline.v0.2.target.json; "
            "review dataset changes before updating the lock"
        )
    v01_dataset_hash = compute_dataset_hash(DATASET_PATHS)
    if contract.get("v0.1_dataset_hash") != v01_dataset_hash:
        raise EvaluationDataError(
            "frozen v0.1 dataset inputs changed; restore them instead of moving the baseline"
        )
    if contract.get("policy_corpus_hash") != compute_policy_corpus_hash():
        raise EvaluationDataError(
            "allowlisted policy corpus changed; review facts and datasets before updating the lock"
        )

    metrics = target.get("metrics")
    if not isinstance(metrics, dict):
        raise EvaluationDataError("v0.2 target metrics must be an object")
    actual_minimums = {
        name: details.get("minimum_score") if isinstance(details, dict) else None
        for name, details in metrics.items()
    }
    if actual_minimums != V02_LOCKED_MINIMUMS:
        raise EvaluationDataError("v0.2 metric minimums differ from the frozen evaluator")
    return target


def evaluate_v02_routing(cases: tuple[dict[str, Any], ...]) -> MetricResult:
    """Confirm frozen mixed-intent labels match the existing routing authority."""
    analyzer = default_chat_providers().analyzer
    failures: list[str] = []
    for case in cases:
        actual = analyzer.analyze(_required_string(case, "text")).intent.value
        expected = _required_string(case, "expected_intent")
        if actual != expected:
            failures.append(f"{case['id']}: expected={expected}, got={actual}")
    return MetricResult(len(cases) - len(failures), len(cases), tuple(failures))


def evaluate_v02_retrieval(
    cases: tuple[dict[str, Any], ...],
) -> dict[str, MetricResult]:
    """Measure the local retriever against the frozen supported/refusal set."""
    retriever = LocalPolicyRetriever()
    section_failures: list[str] = []
    top_one_failures: list[str] = []
    false_refusals: list[str] = []
    missed_refusals: list[str] = []
    supported_total = 0
    unsupported_total = 0
    predicted_refusals = 0
    correct_refusals = 0

    for case in cases:
        query = _required_string(case, "query")
        result = retriever.retrieve(query)
        ranked = retriever.rank(query)
        supported = case["supported"]

        if supported:
            supported_total += 1
            expected = (
                _required_string(case, "expected_source"),
                _required_string(case, "expected_section"),
            )
            returned = {(item.source, item.section) for item in result.evidence}
            if expected not in returned:
                shown = [
                    f"{candidate.evidence.evidence_id}@{candidate.score:.6f}"
                    for candidate in ranked[:DEFAULT_TOP_K]
                ]
                section_failures.append(
                    f"{case['id']}: expected={expected!r}, got={shown or ['refused']}"
                )
            if (
                not ranked
                or (
                    ranked[0].evidence.source,
                    ranked[0].evidence.section,
                )
                != expected
            ):
                actual = ranked[0].evidence.evidence_id if ranked else "refused"
                top_one_failures.append(f"{case['id']}: expected={expected!r}, top_1={actual}")
        else:
            unsupported_total += 1

        if not result.sufficient:
            predicted_refusals += 1
            if supported:
                false_refusals.append(f"{case['id']}: refused a supported query")
            else:
                correct_refusals += 1
        elif not supported:
            returned_ids = [item.evidence_id for item in result.evidence]
            missed_refusals.append(
                f"{case['id']}: returned evidence for unsupported query: {returned_ids}"
            )

    return {
        "policy_section_hit_rate": MetricResult(
            supported_total - len(section_failures),
            supported_total,
            tuple(section_failures),
        ),
        "policy_top_1_hit_rate": MetricResult(
            supported_total - len(top_one_failures),
            supported_total,
            tuple(top_one_failures),
        ),
        "unsupported_query_precision": MetricResult(
            correct_refusals,
            predicted_refusals,
            tuple(false_refusals),
        ),
        "unsupported_query_recall": MetricResult(
            correct_refusals,
            unsupported_total,
            tuple(missed_refusals),
        ),
    }


def _metric_report(result: MetricResult) -> dict[str, Any]:
    return {**result.snapshot(), "failures": list(result.failures)}


def build_v02_contract_report() -> dict[str, Any]:
    """Validate the frozen contract and measure implemented retrieval behavior."""
    datasets = load_v02_datasets()
    validate_v02_target_contract(datasets)
    routing = evaluate_v02_routing(datasets["routing_safety"])
    if routing.score != 1.0:
        raise EvaluationDataError(
            "v0.2 routing labels disagree with the current deterministic analyzer: "
            + "; ".join(routing.failures)
        )
    retrieval = evaluate_v02_retrieval(datasets["policy_retrieval"])
    for name in (
        "policy_section_hit_rate",
        "unsupported_query_precision",
        "unsupported_query_recall",
    ):
        result = retrieval[name]
        minimum = V02_LOCKED_MINIMUMS[name]
        if result.score < minimum:
            raise EvaluationDataError(
                f"{name}={result.score:.6f} is below locked minimum {minimum:.6f}: "
                + "; ".join(result.failures)
            )
    return {
        "suite_id": "v0.2-evaluation-contract",
        "evaluator_schema_version": 3,
        "status": "retrieval_gate_passed",
        "feature_metrics_status": "retrieval_measured_generation_pending",
        "dataset_hash": compute_v02_dataset_hash(),
        "policy_corpus_hash": compute_policy_corpus_hash(),
        "datasets": {
            name: {
                "path": path.relative_to(ROOT).as_posix(),
                "cases": len(datasets[name]),
            }
            for name, path in V02_DATASET_PATHS.items()
        },
        "contract_checks": {
            "schema_valid": True,
            "manifest_valid": True,
            "case_counts_locked": True,
            "global_case_ids_unique": True,
            "policy_provenance_valid": True,
            "policy_allowlist_and_corpus_locked": True,
            "target_hash_matches": True,
            "v0.1_datasets_unchanged": True,
            "routing_precedence_contract": routing.snapshot(),
        },
        "retrieval_config": {
            "strategy": "normalized_idf_lexical_plus_word_ngrams",
            "top_k": DEFAULT_TOP_K,
            "minimum_score": MIN_RETRIEVAL_SCORE,
            "weights": {
                "lexical": LEXICAL_WEIGHT,
                "word_ngram": NGRAM_WEIGHT,
                "heading": HEADING_WEIGHT,
                "exact_phrase": EXACT_PHRASE_WEIGHT,
            },
            "external_network": False,
            "external_embeddings": False,
        },
        "feature_metrics": {name: _metric_report(result) for name, result in retrieval.items()},
    }


def evaluate_intents(cases: tuple[dict[str, Any], ...]) -> MetricResult:
    analyzer = default_chat_providers().analyzer
    failures: list[str] = []
    for case in cases:
        predicted = analyzer.analyze(_required_string(case, "text")).intent.value
        expected = _required_string(case, "expected_intent")
        if predicted != expected:
            failures.append(f"{case['id']}: expected={expected}, got={predicted}")
    return MetricResult(len(cases) - len(failures), len(cases), tuple(failures))


def evaluate_policies(
    cases: tuple[dict[str, Any], ...],
) -> tuple[MetricResult, MetricResult]:
    policy = default_chat_providers().policy
    section_total = 0
    section_hits = 0
    section_failures: list[str] = []
    predicted_insufficient = 0
    correct_insufficient = 0
    insufficient_failures: list[str] = []

    for case in cases:
        result = policy.search(_required_string(case, "query"))
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
            Path(citation.source).name == expected_policy and citation.section == expected_section
            for citation in result.citations
        )
        if hit:
            section_hits += 1
        else:
            returned = [
                f"{Path(citation.source).name}#{citation.section}" for citation in result.citations
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
            raise EvaluationDataError(f"{case['id']}: expected_order_id must be a string or null")
        predicted = extract_order_reference(_required_string(case, "text"))
        if predicted != expected:
            failures.append(f"{case['id']}: expected={expected!r}, got={predicted!r}")
    return MetricResult(len(cases) - len(failures), len(cases), tuple(failures))


def _evaluate_ticket_case(case: dict[str, Any], tickets_path: Path) -> list[str]:
    provider = LocalTicketProvider(tickets_path)
    action = provider.draft_ticket(_required_string(case, "summary"))
    failures: list[str] = []

    if action.status.value != "pending" or provider.ticket_count != 0:
        failures.append("draft created a ticket or was not pending")

    decisions = case.get("decisions")
    if not isinstance(decisions, list) or not all(
        isinstance(decision, bool) for decision in decisions
    ):
        raise EvaluationDataError(f"{case['id']}: decisions must be a list of booleans")

    mode = _required_string(case, "mode")
    target_id = "act_missing" if mode == "unknown_action" else action.action_id
    if mode == "concurrent":
        with ThreadPoolExecutor(max_workers=len(decisions) or 1) as executor:
            resolutions = list(
                executor.map(
                    lambda decision: provider.resolve_action(
                        target_id,
                        confirm=decision,
                    ),
                    decisions,
                )
            )
    elif mode in {"sequential", "unknown_action"}:
        resolutions = [
            provider.resolve_action(target_id, confirm=decision) for decision in decisions
        ]
    else:
        raise EvaluationDataError(f"{case['id']}: unsupported ticket mode {mode!r}")

    actual_statuses = [
        resolution.status.value if resolution is not None else None for resolution in resolutions
    ]
    expected_statuses = case.get("expected_statuses")
    if actual_statuses != expected_statuses:
        failures.append(f"statuses expected={expected_statuses!r}, got={actual_statuses!r}")

    if "expected_repeated" in case:
        actual_repeated = [
            resolution.repeated if resolution is not None else None for resolution in resolutions
        ]
        if actual_repeated != case["expected_repeated"]:
            failures.append(
                f"repeated flags expected={case['expected_repeated']!r}, got={actual_repeated!r}"
            )

    expected_count = case.get("expected_ticket_count")
    persisted_count = len(load_tickets(tickets_path))
    if provider.ticket_count != expected_count or persisted_count != expected_count:
        failures.append(
            f"ticket count expected={expected_count!r}, "
            f"memory={provider.ticket_count}, persisted={persisted_count}"
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
        raise EvaluationDataError(f"{case.get('id', '<unknown>')}: {field} must be a string")
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
        "confirmation_guardrail_pass_rate": evaluate_ticket_guardrail(ticket_cases),
    }


def build_snapshot(results: dict[str, MetricResult]) -> dict[str, Any]:
    """Build a deterministic, versioned baseline artifact."""
    return {
        "baseline_id": "deterministic-v0.1",
        "evaluator_schema_version": 1,
        "metrics": {name: result.snapshot() for name, result in results.items()},
    }


def _print_report(results: dict[str, MetricResult]) -> None:
    print("A.S.I.A deterministic evaluation baseline\n")
    for name, result in results.items():
        print(f"{name}: {result.score:.1%} ({result.passed}/{result.total})")
        for failure in result.failures:
            print(f"  - {failure}")


def _print_v02_contract_report(report: dict[str, Any]) -> None:
    print("A.S.I.A v0.2 evaluation contract\n")
    print(f"status: {report['status']}")
    print(f"feature metrics: {report['feature_metrics_status']}")
    print(f"dataset hash: {report['dataset_hash']}")
    print("datasets:")
    for name, details in report["datasets"].items():
        print(f"  - {name}: {details['cases']} cases ({details['path']})")
    routing = report["contract_checks"]["routing_precedence_contract"]
    print(
        "routing_precedence_contract_pass_rate: "
        f"{routing['score']:.1%} ({routing['passed']}/{routing['total']})"
    )
    config = report["retrieval_config"]
    print(
        "retrieval: "
        f"top_k={config['top_k']}, minimum_score={config['minimum_score']}, "
        f"strategy={config['strategy']}"
    )
    print("retrieval metrics:")
    for name, metric in report["feature_metrics"].items():
        print(f"  - {name}: {metric['score']:.1%} ({metric['passed']}/{metric['total']})")
        for failure in metric["failures"]:
            print(f"      {failure}")
    print("\nGrounded-generation metrics begin after route integration is implemented.")


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
        description="Measure v0.1 behavior or validate the frozen v0.2 contract",
    )
    parser.add_argument(
        "--suite",
        choices=("v0.1", "v0.2"),
        default="v0.1",
        help="Evaluation suite to run (default: v0.1)",
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

    if args.suite == "v0.2" and args.check_baseline is not None:
        parser.error("--check-baseline applies only to the v0.1 measured baseline")

    if args.suite == "v0.2":
        try:
            report = build_v02_contract_report()
        except EvaluationDataError as exc:
            print(f"Evaluation data error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            _print_v02_contract_report(report)
        return 0

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
