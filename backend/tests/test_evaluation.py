"""Contract tests for the versioned deterministic evaluation harness."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType


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
    assert report["status"] == "retrieval_gate_passed"
    assert report["feature_metrics_status"] == "retrieval_measured_generation_pending"
    assert report["retrieval_config"] == {
        "strategy": "normalized_idf_lexical_plus_word_ngrams",
        "top_k": 2,
        "minimum_score": 0.24,
        "weights": {
            "lexical": 0.68,
            "word_ngram": 0.17,
            "heading": 0.1,
            "exact_phrase": 0.05,
        },
        "external_network": False,
        "external_embeddings": False,
    }
