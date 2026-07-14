"""Contract tests for the versioned deterministic evaluation harness."""

from __future__ import annotations

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
        "prompt_version": "grounded-policy-v2",
        "evidence_limit": 1,
        "external_network": False,
        "application_owned_citations": True,
    }


def test_live_result_artifact_contains_provenance_without_raw_content() -> None:
    datasets = EVALUATION.load_v02_datasets()
    metrics, outcomes = EVALUATION.evaluate_v02_generation(datasets["grounded_generation"])
    artifact = EVALUATION.build_live_result_artifact(
        provider="openai",
        model="test-model-snapshot",
        prompt_version="grounded-policy-v2",
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
        prompt_version="grounded-policy-v2",
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
