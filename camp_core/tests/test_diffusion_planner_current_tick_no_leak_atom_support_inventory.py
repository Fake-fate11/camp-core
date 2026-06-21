from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_current_tick_no_leak_atom_support_inventory import (
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze_records,
    main,
    render_markdown,
)


def _plan(status: str = "no_leak_atom_or_proof_objective_redesign_plan_ready") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "no_leak_atom_or_proof_objective_redesign_plan_ready",
            "authorized_next_work": (
                "current_tick_no_leak_atom_support_inventory_preflight_only"
                if status == "no_leak_atom_or_proof_objective_redesign_plan_ready"
                else None
            ),
            "recommended_first_action": "support_inventory_refresh",
            "training_execution_authorized": False,
            "closed_loop_replay_authorized": False,
            "online_selector_authorized": False,
            "formal_seeds_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "seed": seed,
        "scenario_buckets": ["overall", "traffic_light"],
    }


def _record(*, with_new_state: bool) -> dict:
    record = {
        "num_candidates": 2,
        "feasible_mask": [True, True],
        "candidate_dp_prior_deviation_cost": [0.0, 1.0],
        "candidate_step_reach": [10.0, 9.5],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [1.0, 1.1],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [1.0, 1.2],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 1.0],
        "candidate_red_stopping_margin_cost": [0.0, 0.5],
        "dp_candidate_rewards": [
            {"centerline": -0.1, "lane_crossing": False, "sc_min_dist": 99.0},
            {"centerline": -0.2, "lane_crossing": True, "sc_min_dist": 8.0},
        ],
        "dp_scene_feature_names": [
            "route_lanes.present",
            "traffic_lights.present",
            "neighbor_agents_past.present",
        ],
        "dp_scene_features": [1.0, 1.0, 1.0],
        "candidate_closed_loop_outcomes": [
            {"collision": False, "progress_m": 10.0},
            {"collision": True, "progress_m": 9.0},
        ],
    }
    if with_new_state:
        record["candidate_lanelet_ids"] = [[10, 11], [10, 12]]
    return record


def _items(record: dict, *, seed: int = 1) -> list[dict]:
    return [{"raw": record, "context": _context(seed=seed)}]


def test_current_tick_inventory_finds_admissible_candidate_state() -> None:
    report = analyze_records(
        _items(_record(with_new_state=True)),
        redesign_plan_report=_plan(),
        fail_on_formal_seeds=True,
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == (
        "predeclare_no_leak_atom_schema_from_inventory_design_only"
    )
    assert "candidate_lane_topology" in (
        decision["admissible_unclosed_candidate_families"]
    )
    assert decision["closed_loop_replay_authorized"] is False
    assert report["analysis"]["future_outcome_labels_inspected"] is False
    assert "score_k(w)=a_k^T w" in report["analysis"]["math_boundary"]

    markdown = render_markdown(report)
    assert "Current-Tick No-Leak Atom Support Inventory" in markdown
    assert "not authorize training" in markdown


def test_current_tick_inventory_rejects_existing_proxies_only() -> None:
    report = analyze_records(
        _items(_record(with_new_state=False)),
        redesign_plan_report=_plan(),
        fail_on_formal_seeds=True,
    )

    decision = report["final_decision"]
    assert decision["status"] == REJECT_STATUS
    assert decision["primary_gap"] == (
        "no_admissible_unclosed_current_tick_candidate_support"
    )
    assert decision["authorized_next_work"] == (
        "proof_objective_v2_or_default_off_logging_preflight_design_only"
    )
    assert "existing_shape_support_proxy" in (
        decision["available_existing_or_closed_proxy_families"]
    )


def test_current_tick_inventory_blocks_wrong_source_gate() -> None:
    report = analyze_records(
        _items(_record(with_new_state=True)),
        redesign_plan_report=_plan(
            status="no_leak_atom_or_proof_objective_redesign_plan_blocked"
        ),
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] is None


def test_current_tick_inventory_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            _items(_record(with_new_state=True), seed=11),
            redesign_plan_report=_plan(),
            fail_on_formal_seeds=True,
        )


def test_current_tick_inventory_ignores_outcomes() -> None:
    base = _record(with_new_state=True)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][0]["collision"] = True
    mutated["candidate_closed_loop_outcomes"][1]["collision"] = False
    mutated["candidate_closed_loop_outcomes"][1]["progress_m"] = 100.0

    base_report = analyze_records(_items(base), redesign_plan_report=_plan())
    mutated_report = analyze_records(_items(mutated), redesign_plan_report=_plan())

    assert base_report["field_inventory"] == mutated_report["field_inventory"]


def test_current_tick_inventory_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_path = tmp_path / "plan.json"
    log_path = tmp_path / "camp_selection_log.json"
    output_json = tmp_path / "inventory.json"
    output_md = tmp_path / "inventory.md"
    plan_path.write_text(json.dumps(_plan()), encoding="utf-8")
    log_path.write_text(json.dumps([_record(with_new_state=True)]), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "inventory",
            "--redesign_plan_json",
            str(plan_path),
            "--selection_log",
            str(log_path),
            "--label",
            "unit_cli",
            "--fail_on_formal_seeds",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Current-Tick No-Leak" in output_md.read_text(encoding="utf-8")
