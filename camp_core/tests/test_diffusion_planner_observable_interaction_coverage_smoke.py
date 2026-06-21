from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_observable_interaction_coverage_smoke import (
    PASS_STATUS,
    REJECT_STATUS,
    analyze,
)


def _plan() -> dict:
    runs = [
        {
            "run_id": "red_seed1",
            "seed": 1,
            "target_context_families": ["red_context"],
        },
        {
            "run_id": "clearance_turn_seed2",
            "seed": 2,
            "target_context_families": [
                "clearance_context",
                "turn_lateral_context",
            ],
        },
        {
            "run_id": "normal_seed3",
            "seed": 3,
            "target_context_families": ["normal_control"],
        },
    ]
    return {
        "plan_spec": {
            "root": "",
            "steps": 2,
            "num_candidates": 2,
            "red_distance_budget_m": 5.0,
            "clearance_budget_m": 2.0,
            "lateral_error_budget_m": 0.5,
            "min_red_context_records": 1,
            "min_clearance_context_records": 1,
            "min_turn_lateral_context_records": 1,
            "runs": runs,
        },
        "final_decision": {
            "status": "observable_interaction_coverage_broader_nonformal_plan_ready",
            "passed": True,
            "authorized_next_work": (
                "observable_interaction_coverage_broader_nonformal_paired_smoke_only"
            ),
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
    }


def _selection_fields() -> dict:
    return {
        "selected_index": 0,
        "camp_selected_index_before_tracker_postselection": None,
        "camp_selected_index_before_traffic_light_hybrid_postselection": None,
        "used_fallback": False,
        "camp_fallback_mode": "learned",
        "feasible_mask": [True, True],
        "infeasibility_reasons": [[], []],
        "scores": [0.1, 0.2],
        "weights": [0.25, 0.75],
        "selection_scores": [0.1, 0.2],
        "selection_weights": [0.25, 0.75],
        "atoms": [[0.0, 0.1], [0.2, 0.3]],
        "normalized_atoms": [[0.0, 0.1], [0.2, 0.3]],
        "selection_normalized_atoms": [[0.0, 0.1], [0.2, 0.3]],
        "atom_schema_version": "unit",
        "atom_names": ["a", "b"],
        "num_candidates": 2,
    }


def _payload(kind: str) -> dict:
    if kind == "red":
        red_distance = [[4.0, 4.0], [3.0, 3.0]]
        red_alignment = [[1.0, 1.0], [1.0, 1.0]]
        clearance = [5.0, 5.0]
        heading = [[0.0, 0.0], [0.0, 0.0]]
        lateral = [[0.0, 0.0], [0.0, 0.0]]
    elif kind == "clearance_turn":
        red_distance = None
        red_alignment = None
        clearance = [1.5, 0.5]
        heading = [[0.1, 0.2], [0.4, 0.6]]
        lateral = [[0.0, 0.1], [1.0, 1.2]]
    elif kind == "normal":
        red_distance = None
        red_alignment = None
        clearance = [5.0, 5.0]
        heading = [[0.0, 0.0], [0.0, 0.0]]
        lateral = [[0.0, 0.0], [0.0, 0.0]]
    else:
        raise AssertionError(kind)
    return {
        "schema_version": "dp_camp_observable_state_logging_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "candidate_count": 2,
        "finite_checks": {
            "candidate_route_segment_index": True,
            "candidate_route_projection_s_m": True,
            "candidate_route_lateral_error_m": True,
            "candidate_red_stopline_distance_m": True,
            "candidate_red_heading_alignment": True,
            "candidate_route_heading_change_rad": True,
            "route_curvature_context_abs": True,
            "candidate_min_obstacle_clearance_lower_bound_m": True,
            "candidate_obstacle_slot_count": True,
        },
        "latency_ms": {
            "latency_ms_observable_state_route_topology": 0.1,
            "latency_ms_observable_state_traffic_light_relation": 0.1,
            "latency_ms_observable_state_route_turn": 0.1,
            "latency_ms_observable_state_neighbor_clearance": 0.1,
        },
        "candidate_route_projection_s_m": [[0.0, 1.0], [0.0, 1.5]],
        "candidate_route_lateral_error_m": lateral,
        "candidate_route_segment_index": [[0.0, 1.0], [0.0, 1.0]],
        "candidate_route_heading_change_rad": heading,
        "route_curvature_context_abs": [0.0, 0.0],
        "candidate_red_stopline_distance_m": red_distance,
        "candidate_red_heading_alignment": red_alignment,
        "candidate_min_obstacle_clearance_lower_bound_m": clearance,
        "candidate_obstacle_slot_count": [0, 0],
    }


def _summary(enabled: bool, records: int) -> dict:
    return {
        "camp_observable_state_logging": {
            "schema_version": "dp_camp_observable_state_logging_v1",
            "enabled": enabled,
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "records": records if enabled else 0,
        }
    }


def _write_run(root: Path, run_id: str, kind: str) -> None:
    baseline_dir = root / "logs" / run_id / "baseline"
    candidate_dir = root / "logs" / run_id / "observable_logging"
    baseline_dir.mkdir(parents=True)
    candidate_dir.mkdir(parents=True)
    baseline_rows = []
    candidate_rows = []
    for _ in range(2):
        baseline = _selection_fields()
        baseline["observable_state_logging"] = None
        candidate = deepcopy(baseline)
        candidate["observable_state_logging"] = _payload(kind)
        candidate["candidate_closed_loop_outcomes"] = None
        baseline_rows.append(baseline)
        candidate_rows.append(candidate)
    (baseline_dir / "camp_selection_log.json").write_text(
        json.dumps(baseline_rows),
        encoding="utf-8",
    )
    (candidate_dir / "camp_selection_log.json").write_text(
        json.dumps(candidate_rows),
        encoding="utf-8",
    )
    (baseline_dir / "camp_validation_summary.json").write_text(
        json.dumps(_summary(False, 0)),
        encoding="utf-8",
    )
    (candidate_dir / "camp_validation_summary.json").write_text(
        json.dumps(_summary(True, 2)),
        encoding="utf-8",
    )


def _write_all(root: Path) -> None:
    _write_run(root, "red_seed1", "red")
    _write_run(root, "clearance_turn_seed2", "clearance_turn")
    _write_run(root, "normal_seed3", "normal")


def test_observable_interaction_coverage_smoke_passes(tmp_path: Path) -> None:
    _write_all(tmp_path)

    report = analyze(plan=_plan(), root=tmp_path)

    assert report["final_decision"]["status"] == PASS_STATUS
    assert report["final_decision"]["offline_separability_authorized"] is True
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["counts"]["equivalence_mismatches"] == 0
    assert report["coverage"]["records_with_red_risk_candidate_variation"] >= 1
    assert report["coverage"]["records_with_clearance_deficit_candidate_variation"] >= 1
    assert report["coverage"]["records_with_lateral_excess_candidate_variation"] >= 1
    assert report["coverage"]["normal_control_red_risk_nonzero_records"] == 0
    assert report["coverage"]["min_red_distance_m"] == 3.0
    assert report["coverage"]["min_clearance_m"] == 0.5
    assert report["coverage"]["max_lateral_excess_m"] > 0.0
    assert report["coverage_by_run"]["red_seed1"][
        "records_with_red_risk_candidate_variation"
    ] >= 1
    assert report["coverage_by_run"]["clearance_turn_seed2"][
        "records_with_clearance_deficit_candidate_variation"
    ] >= 1


def test_observable_interaction_coverage_smoke_rejects_selection_drift(
    tmp_path: Path,
) -> None:
    _write_all(tmp_path)
    path = (
        tmp_path
        / "logs"
        / "red_seed1"
        / "observable_logging"
        / "camp_selection_log.json"
    )
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows[0]["selected_index"] = 1
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = analyze(plan=_plan(), root=tmp_path)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["counts"]["equivalence_mismatches"] >= 1
    assert any("equivalence_mismatch=selected_index" in item for item in report["errors"])


def test_observable_interaction_coverage_smoke_rejects_missing_red_materiality(
    tmp_path: Path,
) -> None:
    _write_all(tmp_path)
    path = (
        tmp_path
        / "logs"
        / "red_seed1"
        / "observable_logging"
        / "camp_selection_log.json"
    )
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        row["observable_state_logging"]["candidate_red_stopline_distance_m"] = None
        row["observable_state_logging"]["candidate_red_heading_alignment"] = None
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = analyze(plan=_plan(), root=tmp_path)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["materiality"]["red_context"] is False
    assert "red_context_materiality_not_reached" in report["errors"]


def test_observable_interaction_coverage_smoke_rejects_future_label_payload(
    tmp_path: Path,
) -> None:
    _write_all(tmp_path)
    path = (
        tmp_path
        / "logs"
        / "red_seed1"
        / "observable_logging"
        / "camp_selection_log.json"
    )
    rows = json.loads(path.read_text(encoding="utf-8"))
    rows[0]["candidate_closed_loop_outcomes"] = [{"value": 1.0}]
    path.write_text(json.dumps(rows), encoding="utf-8")

    report = analyze(plan=_plan(), root=tmp_path)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any("candidate_closed_loop_outcomes present" in item for item in report["errors"])
