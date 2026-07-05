"""Contract tests for the versioned deterministic evaluation harness."""

from __future__ import annotations

import importlib.util
import json
import sys
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
    expected = json.loads(
        EVALUATION.DEFAULT_BASELINE.read_text(encoding="utf-8")
    )

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
