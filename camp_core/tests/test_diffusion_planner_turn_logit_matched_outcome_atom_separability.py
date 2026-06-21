from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_turn_logit_matched_outcome_atom_separability import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _source_broader_smoke(*, passed: bool = True) -> dict:
    return {
        "final_decision": {
            "status": "turn_logit_payload_smoke_passed"
            if passed
            else "turn_logit_payload_smoke_rejected",
            "passed": passed,
        }
    }


def _matched_dataset(*, passed: bool = True) -> dict:
    return {
        "passed": passed,
        "checks": {
            "closed_loop_outcomes_required": True,
            "finite_candidate_contract_verified": True,
            "forbidden_seed_check": True,
        },
    }


def _outcome(
    value: float,
    *,
    feasible: bool = True,
    progress_m: float = 10.0,
    collision: bool = False,
    lane: bool = False,
    red: bool = False,
) -> dict:
    return {
        "value": value,
        "feasible": feasible,
        "progress_m": progress_m,
        "collision": collision,
        "near_miss": False,
        "lane_violation": lane,
        "red_light_violation": red,
    }


def _turn_logit_payload() -> dict:
    probabilities = [
        [0.60, 0.40],
        [0.95, 0.05],
        [0.50, 0.50],
    ]
    return {
        "schema_version": "dp_camp_turn_logit_payload_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "online_selector_change": False,
        "classical_benders_claim": False,
        "candidate_count": 3,
        "available": True,
        "candidate_turn_indicator_logits": [
            [0.20, -0.20],
            [2.00, -1.00],
            [0.00, 0.00],
        ],
        "candidate_turn_indicator_probabilities": probabilities,
        "candidate_turn_indicator_top_class": [0, 0, 0],
        "field_shapes": {
            "candidate_turn_indicator_logits": [3, 2],
            "candidate_turn_indicator_probabilities": [3, 2],
            "candidate_turn_indicator_top_class": [3],
        },
        "finite_checks": {
            "payload_valid": True,
            "candidate_count_matches": True,
            "candidate_turn_indicator_logits_finite": True,
            "candidate_turn_indicator_probabilities_finite": True,
            "candidate_turn_indicator_probabilities_row_sum_one": True,
            "candidate_turn_indicator_top_class_finite": True,
        },
        "turn_logit_atomization_candidate_names": [
            "turn_logit_entropy_cost_v1",
            "turn_logit_margin_shortfall_v1",
            "turn_logit_non_top1_disagreement_v1",
        ],
        "turn_logit_atomization_candidates_available": True,
    }


def _record(seed: int = 1) -> dict:
    return {
        "seed": seed,
        "num_candidates": 3,
        "turn_logit_payload_logging": _turn_logit_payload(),
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            _outcome(1.0),
            _outcome(-1.0, feasible=False),
        ],
    }


def _write_log(tmp_path: Path, rows: list[dict]) -> Path:
    root = tmp_path / "run_seed_1"
    root.mkdir()
    path = root / "camp_selection_log.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return root


def test_turn_logit_atom_separability_finds_promising_screen(tmp_path: Path) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        source_broader_smoke_report=_source_broader_smoke(),
        matched_dataset_report=_matched_dataset(),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
        max_affine_terms=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["analysis"]["future_outcome_labels_used_for_classification"] is True
    assert report["records"]["class_counts"]["beneficial_alternative"] == 2
    assert report["records"]["class_counts"]["harmful_alternative"] == 2
    coverage = report["descriptor_coverage"]
    assert coverage["turn_logit_entropy_cost_v1"]["finite"] == 4
    assert coverage["turn_logit_margin_shortfall_v1"]["finite"] == 4
    assert coverage["turn_logit_non_top1_disagreement_v1"]["finite"] == 4


def test_turn_logit_atom_separability_blocks_failed_source_gate(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        source_broader_smoke_report=_source_broader_smoke(passed=False),
        matched_dataset_report=_matched_dataset(),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["source_gate"]["source_passed"] is False


def test_turn_logit_atom_separability_rejects_outcome_inside_payload(
    tmp_path: Path,
) -> None:
    record = _record()
    record["turn_logit_payload_logging"]["candidate_closed_loop_outcomes"] = []
    root = _write_log(tmp_path, [record])

    with pytest.raises(ValueError, match="embeds outcome labels"):
        analyze(
            [root],
            source_broader_smoke_report=_source_broader_smoke(),
            matched_dataset_report=_matched_dataset(),
            expected_logs=1,
            expected_records=1,
            expected_candidates=3,
        )


def test_turn_logit_atom_separability_forbids_formal_seed(tmp_path: Path) -> None:
    root = _write_log(tmp_path, [_record(seed=11)])

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze(
            [root],
            source_broader_smoke_report=_source_broader_smoke(),
            matched_dataset_report=_matched_dataset(),
            expected_logs=1,
            expected_records=1,
            expected_candidates=3,
            fail_on_formal_seeds=True,
        )
