from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_observable_interaction_coverage_smoke import (
    NEXT_WORK_REJECT,
    REJECT_STATUS,
)
from scripts.integrations.analyze_diffusion_planner_observable_interaction_scenario_support import (
    BOTTLENECK_STATUS,
    FOUND_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
)


def _source_smoke_rejected() -> dict:
    return {
        "final_decision": {
            "status": REJECT_STATUS,
            "passed": False,
            "authorized_next_work": NEXT_WORK_REJECT,
            "offline_separability_authorized": False,
            "CAMP_retraining_authorized": False,
            "Full36_authorized": False,
        }
    }


def _source_smoke_passed() -> dict:
    source = deepcopy(_source_smoke_rejected())
    source["final_decision"]["status"] = "observable_interaction_coverage_passed"
    source["final_decision"]["passed"] = True
    return source


def _payload(kind: str) -> dict:
    if kind == "supported":
        red_distance = [[4.0, 4.5], [8.0, 9.0]]
        red_alignment = [[0.75, 0.5], [-0.2, -0.1]]
        clearance = [10.0, 1.0]
        obstacle_slots = [0, 1]
    elif kind == "unsupported":
        red_distance = [[4.0, 4.5], [6.0, 7.0]]
        red_alignment = [[-0.3, -0.2], [0.0, 0.0]]
        clearance = [4.0, 5.0]
        obstacle_slots = [1, 1]
    elif kind == "no_obstacles":
        red_distance = [[6.0, 6.5], [7.0, 7.5]]
        red_alignment = [[0.5, 0.4], [0.2, 0.1]]
        clearance = [100.0, 100.0]
        obstacle_slots = [0, 0]
    else:
        raise AssertionError(kind)
    return {
        "candidate_count": 2,
        "candidate_red_stopline_distance_m": red_distance,
        "candidate_red_heading_alignment": red_alignment,
        "candidate_min_obstacle_clearance_lower_bound_m": clearance,
        "candidate_obstacle_slot_count": obstacle_slots,
    }


def _write_log(root: Path, *, seed: int, kind: str) -> Path:
    log_dir = root / "route" / f"seed_{seed}" / "npc_0" / "spawn_0p3" / "tl_on" / "static"
    log_dir.mkdir(parents=True)
    rows = [
        {"observable_state_logging": None},
        {"observable_state_logging": _payload(kind)},
    ]
    path = log_dir / "camp_selection_log.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_scenario_support_found_authorizes_design_only_next_step(tmp_path: Path) -> None:
    _write_log(tmp_path, seed=1, kind="supported")

    report = analyze([tmp_path], source_smoke_report=_source_smoke_rejected())

    assert report["final_decision"]["status"] == FOUND_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["final_decision"]["offline_separability_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert report["support"]["red_context_supported"] is True
    assert report["support"]["clearance_context_supported"] is True
    assert report["support"]["red_context_candidate_count"] == 1
    assert report["support"]["clearance_context_candidate_count"] == 1
    assert report["inventory_diagnosis"]["red_bottleneck"] == "red_context_supported"
    assert (
        report["inventory_diagnosis"]["clearance_bottleneck"]
        == "clearance_context_supported"
    )


def test_scenario_support_records_bottleneck_when_contexts_absent(
    tmp_path: Path,
) -> None:
    _write_log(tmp_path, seed=1, kind="unsupported")

    report = analyze([tmp_path], source_smoke_report=_source_smoke_rejected())

    assert report["final_decision"]["status"] == BOTTLENECK_STATUS
    assert report["final_decision"]["passed"] is False
    assert report["final_decision"]["primary_gap"] == (
        "red_context_support_absent,clearance_context_support_absent"
    )
    assert report["support"]["red_context_supported"] is False
    assert report["support"]["clearance_context_supported"] is False
    assert report["support"]["min_red_distance_m"] == 4.0
    assert report["support"]["records_with_red_distance_payload"] == 1
    assert report["support"]["records_with_red_distance_inside_budget"] == 1
    assert report["support"]["records_with_positive_red_alignment"] == 0
    assert report["support"]["records_with_finite_clearance"] == 1
    assert report["support"]["records_with_clearance_inside_budget"] == 0
    assert report["inventory_diagnosis"]["red_bottleneck"] == (
        "nonpositive_red_alignment_collapses_risk"
    )
    assert (
        report["inventory_diagnosis"]["clearance_bottleneck"]
        == "clearance_budget_never_active"
    )


def test_scenario_support_excludes_formal_seed_logs(tmp_path: Path) -> None:
    _write_log(tmp_path, seed=11, kind="supported")
    _write_log(tmp_path, seed=1, kind="unsupported")

    report = analyze([tmp_path], source_smoke_report=_source_smoke_rejected())

    assert report["counts"]["input_log_paths"] == 2
    assert report["counts"]["excluded_formal_seed_logs"] == 1
    assert report["counts"]["scanned_logs"] == 1
    assert report["counts"]["formal_seed_records"] == 0
    assert report["final_decision"]["status"] == BOTTLENECK_STATUS


def test_scenario_support_blocks_when_source_smoke_was_not_rejected(
    tmp_path: Path,
) -> None:
    _write_log(tmp_path, seed=1, kind="supported")

    report = analyze([tmp_path], source_smoke_report=_source_smoke_passed())

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["passed"] is False
    assert report["source_gate"]["passed"] is False


def test_scenario_support_distinguishes_missing_obstacle_slots(
    tmp_path: Path,
) -> None:
    _write_log(tmp_path, seed=1, kind="no_obstacles")

    report = analyze([tmp_path], source_smoke_report=_source_smoke_rejected())

    assert report["final_decision"]["status"] == BOTTLENECK_STATUS
    assert report["support"]["records_with_positive_obstacle_slots"] == 0
    assert report["inventory_diagnosis"]["clearance_bottleneck"] == (
        "no_positive_obstacle_slots_and_clearance_budget_never_active"
    )
    assert report["inventory_diagnosis"]["red_bottleneck"] == (
        "red_distance_budget_never_active"
    )
