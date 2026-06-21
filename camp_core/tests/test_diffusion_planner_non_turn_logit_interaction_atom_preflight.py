from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_non_turn_logit_interaction_atom_preflight import (
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _source_bottleneck(*, ready: bool = True) -> dict:
    return {
        "final_decision": {
            "status": "turn_logit_atom_bottleneck_diagnosed"
            if ready
            else "turn_logit_atom_bottleneck_source_not_rejected",
            "passed": ready,
            "primary_bottleneck": "best_screen_blocks_all_beneficial_candidates",
            "authorized_next_work": (
                "design_non_turn_logit_or_interaction_atoms_before_retraining"
                if ready
                else None
            ),
        }
    }


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


def _record(seed: int = 1) -> dict:
    return {
        "seed": seed,
        "num_candidates": 3,
        "candidate_route_progress": [10.0, 10.2, 7.0],
        "dp_candidate_rewards": [
            {"total": 10.0},
            {"total": 10.4},
            {"total": 4.0},
        ],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.0, 2.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.0, 1.0],
        "candidate_dp_prior_jerk_excess_cost": [0.0, 0.0, 3.0],
        "candidate_horizon_lateral_acceleration_cost": [0.1, 0.1, 0.4],
        "candidate_dp_prior_deviation_cost": [0.0, 0.0, 2.0],
        "candidate_obstacle_clearance": {
            "soft_clearance_violation_cost": [0.0, 0.0, 2.0],
            "near_miss_violation_cost": [0.0, 0.0, 1.0],
        },
        "candidate_closed_loop_outcomes": [
            _outcome(0.0),
            _outcome(1.0, progress_m=10.1),
            _outcome(-1.0, feasible=False, progress_m=7.0),
        ],
    }


def _write_log(tmp_path: Path, rows: list[dict]) -> Path:
    root = tmp_path / "run_seed_1"
    root.mkdir()
    (root / "camp_selection_log.json").write_text(
        json.dumps(rows),
        encoding="utf-8",
    )
    return root


def test_non_turn_logit_interaction_preflight_finds_screen(tmp_path: Path) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        source_bottleneck_report=_source_bottleneck(),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
        max_affine_terms=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["analysis"]["avoids_rejected_direct_turn_logit_atoms"] is True
    assert report["records"]["class_counts"]["beneficial_alternative"] == 2
    assert report["records"]["class_counts"]["harmful_alternative"] == 2
    assert report["final_decision"]["promising_screen_count"] > 0


def test_non_turn_logit_interaction_preflight_requires_source_gate(
    tmp_path: Path,
) -> None:
    root = _write_log(tmp_path, [_record(), _record()])

    report = analyze(
        [root],
        source_bottleneck_report=_source_bottleneck(ready=False),
        expected_logs=1,
        expected_records=2,
        expected_candidates=3,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["source_gate"]["passed"] is False
