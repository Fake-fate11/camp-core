from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_turn_logit_atom_bottleneck import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _outcome(value: float, *, feasible: bool = True, progress_m: float = 10.0) -> dict:
    return {
        "value": value,
        "feasible": feasible,
        "progress_m": progress_m,
        "collision": False,
        "near_miss": False,
        "lane_violation": False,
        "red_light_violation": False,
    }


def _payload() -> dict:
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
        "candidate_turn_indicator_logits": [[0.2, -0.2], [1.0, 0.0], [0.0, 0.0]],
        "candidate_turn_indicator_probabilities": [
            [0.60, 0.40],
            [0.73, 0.27],
            [0.50, 0.50],
        ],
        "candidate_turn_indicator_top_class": [0, 0, 0],
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


def _record() -> dict:
    return {
        "seed": 1,
        "num_candidates": 3,
        "turn_logit_payload_logging": _payload(),
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            _outcome(1.0),
            _outcome(-1.0, feasible=False),
        ],
    }


def _write_log(tmp_path: Path) -> Path:
    root = tmp_path / "run_seed_1"
    root.mkdir()
    (root / "camp_selection_log.json").write_text(
        json.dumps([_record(), _record()]),
        encoding="utf-8",
    )
    return root


def _separability_report(*, rejected: bool = True) -> dict:
    return {
        "final_decision": {
            "status": "turn_logit_atom_separability_rejected"
            if rejected
            else "turn_logit_atom_separability_promising_for_certificate_design",
            "passed": not rejected,
            "primary_gap": "turn_logit_atoms_do_not_separate_candidates",
            "authorized_next_work": "diagnose_turn_logit_atom_bottleneck_before_retraining",
        },
        "failure_gap": {
            "best_screen": {
                "screen_name": "turn_logit_entropy_cost_v1:allow_low",
                "beneficial_count": 2,
                "beneficial_retain_rate": 0.0,
                "harmful_block_rate": 1.0,
                "allowed_harmful_rate": 1.0,
            }
        },
    }


def test_turn_logit_bottleneck_diagnoses_rejected_separability(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path)

    report = analyze(
        [root],
        separability_report=_separability_report(),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
        min_value_gain=0.25,
        min_value_loss=0.25,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["primary_bottleneck"] == (
        "best_screen_blocks_all_beneficial_candidates"
    )
    assert report["records"]["class_counts"]["beneficial_alternative"] == 2
    assert "turn_logit_entropy_cost_v1" in report["feature_summaries"]


def test_turn_logit_bottleneck_requires_rejected_source(tmp_path: Path) -> None:
    root = _write_log(tmp_path)

    report = analyze(
        [root],
        separability_report=_separability_report(rejected=False),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["source_gate"]["passed"] is False
