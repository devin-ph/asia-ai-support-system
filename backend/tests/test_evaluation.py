"""Contract tests for the versioned deterministic evaluation harness."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def _load_evaluation_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "evaluate.py"
    spec = importlib.util.spec_from_file_location(
        "asia_evaluation_script",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EVALUATION = _load_evaluation_module()


def _tamper_reference(
    reference: dict[str, object],
    path: tuple[str, ...],
    value: object,
) -> dict[str, object]:
    candidate = copy.deepcopy(reference)
    current = candidate
    for field in path[:-1]:
        nested = current[field]
        assert isinstance(nested, dict)
        current = nested
    current[path[-1]] = value
    return candidate


@pytest.fixture(scope="module")
def valid_curated_reference() -> dict[str, object]:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])
    live_artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model=EVALUATION.V02_REFERENCE_MODEL,
        prompt_version="grounded-policy-v4",
        timeout_seconds=15.0,
        duration_ms=2100.0,
        metrics=metrics,
        outcomes=outcomes,
        generated_at=datetime(2026, 7, 15, 1, 2, 3, tzinfo=UTC),
    )
    for case in live_artifact["cases"]:
        case["human_score"] = 2
    return EVALUATION.build_curated_reference(
        live_artifact,
        curated_at=datetime(2026, 7, 15, 2, 3, 4, tzinfo=UTC),
    )


def test_all_evaluation_datasets_are_non_empty_with_unique_ids() -> None:
    ids: set[str] = set()

    for path in EVALUATION.DATASET_PATHS.values():
        cases = EVALUATION.load_jsonl(path)
        assert cases
        case_ids = {case["id"] for case in cases}
        assert len(case_ids) == len(cases)
        assert ids.isdisjoint(case_ids)
        ids.update(case_ids)


def test_current_results_match_committed_v01_baseline() -> None:
    actual = EVALUATION.build_snapshot(EVALUATION.run_evaluation())
    expected = json.loads(EVALUATION.DEFAULT_BASELINE.read_text(encoding="utf-8"))

    assert actual == expected


def test_evaluation_exposes_the_five_documented_metrics() -> None:
    results = EVALUATION.run_evaluation()

    assert set(results) == {
        "intent_accuracy",
        "policy_section_hit_rate",
        "insufficient_context_precision",
        "order_id_extraction_accuracy",
        "confirmation_guardrail_pass_rate",
    }
    assert all(result.total > 0 for result in results.values())
    assert all(0.0 <= result.score <= 1.0 for result in results.values())


def test_v02_datasets_match_the_frozen_schema_counts_and_hashes() -> None:
    datasets = EVALUATION.load_v02_datasets()
    target = EVALUATION.validate_v02_target_contract(datasets)

    assert {name: len(cases) for name, cases in datasets.items()} == {
        "policy_retrieval": 50,
        "grounded_generation": 21,
        "routing_safety": 15,
    }
    all_ids = [case["id"] for cases in datasets.values() for case in cases]
    assert len(all_ids) == len(set(all_ids)) == 86
    assert target["dataset_contract"]["dataset_hash"] == EVALUATION.compute_v02_dataset_hash()
    assert target["dataset_contract"]["v0.1_dataset_hash"] == EVALUATION.compute_dataset_hash(
        EVALUATION.DATASET_PATHS
    )
    assert (
        target["dataset_contract"]["policy_corpus_hash"] == EVALUATION.compute_policy_corpus_hash()
    )


def test_v02_retrieval_and_generation_cover_every_policy_section() -> None:
    datasets = EVALUATION.load_v02_datasets()
    catalog = EVALUATION.load_policy_catalog()
    expected_sections = {
        (source, section) for source, sections in catalog.items() for section in sections
    }

    retrieval_sections = Counter(
        (case["expected_source"], case["expected_section"])
        for case in datasets["policy_retrieval"]
        if case["supported"]
    )
    generation_sections = Counter(
        (case["expected_source"], case["expected_section"])
        for case in datasets["grounded_generation"]
    )

    assert set(retrieval_sections) == expected_sections
    assert set(generation_sections) == expected_sections
    assert set(retrieval_sections.values()) == {5}
    assert set(generation_sections.values()) == {3}
    assert sum(not case["supported"] for case in datasets["policy_retrieval"]) == 15


def test_v02_routing_contract_matches_the_deterministic_authority() -> None:
    datasets = EVALUATION.load_v02_datasets()
    result = EVALUATION.evaluate_v02_routing(datasets["routing_safety"])

    assert result.snapshot() == {"score": 1.0, "passed": 15, "total": 15}


def test_v02_retrieval_meets_the_frozen_gate() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics = EVALUATION.evaluate_v02_retrieval(datasets["policy_retrieval"])

    assert metrics["policy_section_hit_rate"].snapshot() == {
        "score": 1.0,
        "passed": 35,
        "total": 35,
    }
    assert metrics["policy_top_1_hit_rate"].snapshot() == {
        "score": 1.0,
        "passed": 35,
        "total": 35,
    }
    assert metrics["unsupported_query_precision"].snapshot() == {
        "score": 1.0,
        "passed": 15,
        "total": 15,
    }
    assert metrics["unsupported_query_recall"].snapshot() == {
        "score": 1.0,
        "passed": 15,
        "total": 15,
    }

    report = EVALUATION.build_v02_contract_report()
    assert report["retrieval_config"] == {
        "strategy": "normalized_idf_lexical_plus_word_ngrams",
        "top_k": 2,
        "minimum_score": 0.24,
        "minimum_matched_query_tokens": 2,
        "weights": {
            "lexical": 0.66,
            "word_ngram": 0.17,
            "heading": 0.1,
            "exact_phrase": 0.07,
        },
        "external_network": False,
        "external_embeddings": False,
    }


def test_v02_offline_generation_meets_the_automated_frozen_gates() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])

    assert metrics["automated_grounded_response_pass_rate"].snapshot() == {
        "score": 1.0,
        "passed": 21,
        "total": 21,
    }
    assert metrics["citation_coverage_rate"].snapshot() == {
        "score": 1.0,
        "passed": 21,
        "total": 21,
    }
    assert metrics["citation_validity_rate"].snapshot() == {
        "score": 1.0,
        "passed": 21,
        "total": 21,
    }
    assert len(outcomes) == 21
    assert all(outcome["automated_pass"] for outcome in outcomes)

    report = EVALUATION.build_v02_contract_report()
    assert report["status"] == "offline_generation_gate_passed"
    assert (
        report["feature_metrics_status"]
        == "retrieval_and_offline_generation_measured_human_review_pending"
    )
    assert report["human_reference_review_status"] == "pending_external_reference_run"
    assert report["pending_metrics"] == {
        "grounded_response_pass_rate": {
            "status": "pending_live_human_reference_review",
            "minimum_score": 0.95,
        }
    }
    assert report["generation_config"] == {
        "provider": "template",
        "model": None,
        "prompt_version": "grounded-policy-v4",
        "evidence_limit": 1,
        "external_network": False,
        "application_owned_citations": True,
    }


def test_release_report_requires_committed_human_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(EVALUATION, "V02_REFERENCE", tmp_path / "v0.2-reference.json")

    assert EVALUATION.build_v02_contract_report()["human_reference_review_status"] == (
        "pending_external_reference_run"
    )
    with pytest.raises(EVALUATION.EvaluationDataError, match="release gate requires"):
        EVALUATION.build_v02_contract_report(require_reference=True)


def test_live_result_artifact_contains_provenance_without_raw_content() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])
    artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model="test-model-snapshot",
        prompt_version="grounded-policy-v4",
        timeout_seconds=15.0,
        duration_ms=2100.0,
        metrics=metrics,
        outcomes=outcomes,
        generated_at=datetime(2026, 7, 15, 1, 2, 3, tzinfo=UTC),
    )

    assert artifact["schema_version"] == 1
    assert artifact["provider"] == "openai"
    assert artifact["model"] == "test-model-snapshot"
    assert artifact["created_at"] == "2026-07-15T01:02:03+00:00"
    assert artifact["parameters"] == {
        "timeout_seconds": 15.0,
        "case_count": 21,
        "evidence_limit": 1,
        "store": False,
        "max_retries": 0,
    }
    assert artifact["latency_summary"] == {
        "total_ms": 2100.0,
        "average_ms": 100.0,
    }
    assert artifact["fallbacks"] == {"total": 0, "by_reason": {}}
    assert artifact["automated_gate_passed"] is True
    assert artifact["human_review"]["status"] == "pending"
    assert len(artifact["cases"]) == 21
    serialized = json.dumps(artifact, ensure_ascii=False)
    assert "Tôi được đổi trả" not in serialized
    assert "trong vòng 7 ngày" not in serialized
    assert "raw_prompt" not in serialized
    assert "raw_response" not in serialized

    fallback_outcomes = ({**outcomes[0], "fallback_reason": "authentication"}, *outcomes[1:])
    fallback_artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model="test-model-snapshot",
        prompt_version="grounded-policy-v4",
        timeout_seconds=15.0,
        duration_ms=2100.0,
        metrics=metrics,
        outcomes=fallback_outcomes,
    )
    assert fallback_artifact["fallbacks"] == {
        "total": 1,
        "by_reason": {"authentication": 1},
    }
    assert fallback_artifact["automated_gate_passed"] is False


def test_curated_reference_requires_human_scores_and_strips_answer_text() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])
    live_artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model=EVALUATION.V02_REFERENCE_MODEL,
        prompt_version="grounded-policy-v4",
        timeout_seconds=15.0,
        duration_ms=2100.0,
        metrics=metrics,
        outcomes=outcomes,
        generated_at=datetime(2026, 7, 15, 1, 2, 3, tzinfo=UTC),
    )
    for case in live_artifact["cases"]:
        case["answer_text"] = "Local answer retained only before curation."
        case["human_score"] = 2

    curated = EVALUATION.build_curated_reference(
        live_artifact,
        curated_at=datetime(2026, 7, 15, 2, 3, 4, tzinfo=UTC),
    )

    EVALUATION.validate_curated_reference(curated)
    assert curated["artifact_type"] == "v0.2-grounded-generation-reference"
    assert curated["model"] == EVALUATION.V02_REFERENCE_MODEL
    assert curated["curated_at"] == "2026-07-15T02:03:04+00:00"
    assert curated["metrics"]["grounded_response_pass_rate"] == {
        "score": 1.0,
        "passed": 21,
        "total": 21,
        "minimum": 0.95,
        "target_met": True,
    }
    assert curated["human_review"]["status"] == "complete"
    assert all("answer_text" not in case for case in curated["cases"])


def test_curated_reference_requires_exact_top_level_and_nested_schema(
    valid_curated_reference: dict[str, object],
) -> None:
    missing_top_level = copy.deepcopy(valid_curated_reference)
    missing_top_level.pop("source_created_at")
    with pytest.raises(EVALUATION.EvaluationDataError, match="top level"):
        EVALUATION.validate_curated_reference(missing_top_level)

    extra_top_level = {**copy.deepcopy(valid_curated_reference), "raw_prompt": "forbidden"}
    with pytest.raises(EVALUATION.EvaluationDataError, match="top level"):
        EVALUATION.validate_curated_reference(extra_top_level)

    missing_parameter = copy.deepcopy(valid_curated_reference)
    parameters = missing_parameter["parameters"]
    assert isinstance(parameters, dict)
    parameters.pop("store")
    with pytest.raises(EVALUATION.EvaluationDataError, match="parameters"):
        EVALUATION.validate_curated_reference(missing_parameter)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("parameters", "store"), True, "content controls"),
        (("parameters", "max_retries"), 1, "content controls"),
        (("parameters", "evidence_limit"), 2, "content controls"),
        (("parameters", "case_count"), 20, "content controls"),
        (("parameters", "timeout_seconds"), float("inf"), "timeout_seconds"),
        (("latency_summary", "total_ms"), -1.0, "latency values"),
        (("latency_summary", "average_ms"), 99.0, "average_ms"),
        (("source_created_at",), "2026-07-15T01:02:03", "timezone-aware UTC"),
        (("curated_at",), "2026-07-15T01:00:00+00:00", "later than"),
        (("human_review", "rubric"), "2=looks-good", "rubric"),
        (("human_review", "reviewer"), "local-name", "human_review"),
        (("known_limitations",), [], "known limitations"),
        (("metrics", "citation_validity_rate", "raw_output"), "x", "metric"),
        (("metrics", "grounded_response_pass_rate", "minimum"), 0.9, "minimum"),
    ],
)
def test_curated_reference_rejects_tampered_provenance(
    valid_curated_reference: dict[str, object],
    path: tuple[str, ...],
    value: object,
    message: str,
) -> None:
    tampered = _tamper_reference(valid_curated_reference, path, value)

    with pytest.raises(EVALUATION.EvaluationDataError, match=message):
        EVALUATION.validate_curated_reference(tampered)


def test_curated_reference_rejects_unreviewed_or_fallback_run() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])
    live_artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model=EVALUATION.V02_REFERENCE_MODEL,
        prompt_version="grounded-policy-v4",
        timeout_seconds=15.0,
        duration_ms=2100.0,
        metrics=metrics,
        outcomes=outcomes,
    )

    with pytest.raises(EVALUATION.EvaluationDataError, match="human_score"):
        EVALUATION.build_curated_reference(live_artifact)

    live_artifact["fallbacks"] = {"total": 1, "by_reason": {"timeout": 1}}
    with pytest.raises(EVALUATION.EvaluationDataError, match="zero provider fallbacks"):
        EVALUATION.build_curated_reference(live_artifact)


def test_curated_reference_rejects_local_model_override() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])
    live_artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model="local-experiment-model",
        prompt_version="grounded-policy-v4",
        timeout_seconds=15.0,
        duration_ms=2100.0,
        metrics=metrics,
        outcomes=outcomes,
    )
    for case in live_artifact["cases"]:
        case["human_score"] = 2

    with pytest.raises(EVALUATION.EvaluationDataError, match="pinned model"):
        EVALUATION.build_curated_reference(live_artifact)


def test_curated_reference_rejects_tampered_metrics_or_provenance() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])
    live_artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model=EVALUATION.V02_REFERENCE_MODEL,
        prompt_version="grounded-policy-v4",
        timeout_seconds=15.0,
        duration_ms=2100.0,
        metrics=metrics,
        outcomes=outcomes,
    )
    for case in live_artifact["cases"]:
        case["human_score"] = 2

    live_artifact["metrics"]["citation_validity_rate"]["passed"] = 20
    with pytest.raises(EVALUATION.EvaluationDataError, match="does not match case outcomes"):
        EVALUATION.build_curated_reference(live_artifact)

    live_artifact["metrics"]["citation_validity_rate"]["passed"] = 21
    live_artifact["parameters"]["raw_prompt"] = "must not be curated"
    with pytest.raises(EVALUATION.EvaluationDataError, match="versioned provenance fields"):
        EVALUATION.build_curated_reference(live_artifact)

    live_artifact["parameters"].pop("raw_prompt")
    live_artifact["parameters"]["store"] = True
    with pytest.raises(EVALUATION.EvaluationDataError, match="content controls"):
        EVALUATION.build_curated_reference(live_artifact)

    live_artifact["parameters"]["store"] = False
    live_artifact.pop("created_at")
    with pytest.raises(EVALUATION.EvaluationDataError, match="created_at"):
        EVALUATION.build_curated_reference(live_artifact)


def test_live_run_requires_explicit_external_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        EVALUATION,
        "load_settings",
        lambda: SimpleNamespace(response_generator=EVALUATION.ResponseGeneratorName.TEMPLATE),
    )

    with pytest.raises(
        EVALUATION.ProviderConfigurationError,
        match="ASIA_RESPONSE_GENERATOR=openai",
    ):
        EVALUATION.run_v02_live_generation()


def test_v02_retrievers_read_only_hash_locked_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_loader = EVALUATION.load_policy_corpus
    requested: list[tuple[str, ...]] = []

    def spy(**kwargs: object) -> object:
        requested.append(tuple(kwargs["allowed_sources"]))
        return real_loader(**kwargs)

    monkeypatch.setattr(EVALUATION, "load_policy_corpus", spy)
    retriever = EVALUATION._v02_retriever()

    assert requested == [EVALUATION.V02_POLICY_SOURCES]
    assert {item.source for item in retriever.evidence} == set(EVALUATION.V02_POLICY_SOURCES)
