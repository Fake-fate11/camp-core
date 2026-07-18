from __future__ import annotations

import copy
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_v25_a162_bounded_execution import (
    RESULT_SCHEMA_VERSION,
    RUN_EVIDENCE_SCHEMA_VERSION,
    TICKS_PER_RUN,
    build_route_level_bounded_execution_plan,
    canonical_sha256,
    validate_bounded_terminal_acceptance,
)


ROOT = Path(__file__).resolve().parents[2]


def _actor(speed: float = 4.0) -> dict:
    return {
        "id": "ignored-id",
        "agent_type": "vehicle",
        "initial_heading_rad": 0.0,
        "initial_xy": [10.0, 0.0],
        "lateral_offset_m": 0.0,
        "lateral_speed_mps": 0.0,
        "lateral_target_m": None,
        "length_m": 4.5,
        "longitudinal_acceleration_mps2": 0.0,
        "longitudinal_speed_mps": speed,
        "route_normal": [0.0, 1.0],
        "route_tangent": [1.0, 0.0],
        "trigger_time_s": 1.0,
        "wheelbase_m": 2.7,
        "width_m": 1.8,
    }


def _case(index: int, *, mapped: bool, speed: float = 4.0) -> dict:
    return {
        "scenario_id": f"{index + 1:064x}",
        "runner_eligible": True,
        "seeds": [25001],
        "family": "red_light_phase_timing" if mapped else "lead_vehicle_hard_brake",
        "tier": "easy",
        "semantic_variant": "same",
        "source_map_sha256": "a" * 64,
        "route_identity_sha256": "b" * 64 if not mapped else "c" * 64,
        "corridor_group_sha256": "d" * 64,
        "parameters": {
            "crossing_speed_mps": 1.2,
            "deceleration_mps2": -2.0,
            "ego_speed_mps": 7.0,
            "headway_m": 34.0,
            "lateral_offset_m": 4.0,
            "lateral_speed_mps": 0.6,
            "other_speed_mps": 7.0,
            "trigger_time_s": 2.5,
            "variant": index,
        },
        "actors": [_actor(speed)],
        "signal": {
            "phase": "red" if mapped else "none",
            "phase_remaining_s": 0.0,
            "mapped_source_required": mapped,
        },
        "route_spec": {
            "map_path": "/map.osm",
            "start_pose": [0.0, 0.0, 0.0],
            "goal_pose": [100.0, 0.0, 0.0],
            "lanelet_ids": [1],
            "route_length_m": 100.0,
        },
    }


def _row(case: dict, *, mapped: bool) -> dict:
    chain = {
        "semantic_clone_sha256": "e" * 64 if not mapped else "f" * 64,
        "scenario_id": case["scenario_id"],
        "source_chain_sha256": case["scenario_id"],
        "route_geometry_sha256": "9" * 64,
    }
    return {
        "scenario_id": case["scenario_id"],
        "source_class": "mapped_signal" if mapped else "no_signal",
        "phase_authority_mode": "controlled_same_tick_override" if mapped else None,
        "source_chain": chain,
        "id_free_tensor_layout": {"layout_sha256": "2" * 64},
    }


def _fixture(*, different_tie_physics: bool = False):
    mapped = _case(0, mapped=True)
    first = _case(1, mapped=False)
    second = _case(2, mapped=False, speed=5.0 if different_tie_physics else 4.0)
    cases = [mapped, first, second]
    rows = [
        _row(mapped, mapped=True),
        _row(first, mapped=False),
        _row(second, mapped=False),
    ]
    return cases, rows


def test_route_level_plan_freezes_identity0_repeat_and_equivalent_tie() -> None:
    cases, rows = _fixture()
    plan = build_route_level_bounded_execution_plan(
        formal_train=cases,
        source_rows=rows,
        source_root_sha256="3" * 64,
        source_review_root_sha256="4" * 64,
    )
    assert plan["status"] == "passed_preflight_plan_k8_execute_closed"
    assert plan["unique_identity_count"] == 2
    assert plan["run_count"] == 3
    assert plan["snapshot_capacity"] == 3 * TICKS_PER_RUN
    assert plan["runs"][0]["occurrence"] == "identity0_first"
    assert plan["runs"][-1]["occurrence"] == "identity0_final_repeat"
    assert plan["runs"][0]["scenario_id"] == plan["runs"][-1]["scenario_id"]
    assert plan["tie_equivalence_proofs"][0]["all_terminal_items_equivalent"] is True
    assert plan["k8_executed"] is False


def test_identity_variant_and_identity_bound_chain_sha_do_not_fake_physical_drift() -> None:
    cases, rows = _fixture()
    assert cases[1]["parameters"]["variant"] != cases[2]["parameters"]["variant"]
    assert (
        rows[1]["source_chain"]["source_chain_sha256"]
        != rows[2]["source_chain"]["source_chain_sha256"]
    )
    plan = build_route_level_bounded_execution_plan(
        formal_train=cases,
        source_rows=rows,
        source_root_sha256="3" * 64,
        source_review_root_sha256="4" * 64,
    )
    proof = plan["tie_equivalence_proofs"][0]
    assert proof["all_terminal_items_equivalent"] is True
    assert len(set(proof["k8_relevant_physical_payload_sha256"])) == 1


def test_physical_source_chain_change_is_not_treated_as_equivalent() -> None:
    cases, rows = _fixture()
    rows[2]["source_chain"]["route_geometry_sha256"] = "8" * 64
    plan = build_route_level_bounded_execution_plan(
        formal_train=cases,
        source_rows=rows,
        source_root_sha256="3" * 64,
        source_review_root_sha256="4" * 64,
    )
    assert plan["status"].startswith("requires_ultra_review")
    assert plan["unique_identity_count"] == 3


def test_non_equivalent_scenario_id_tie_includes_every_terminal_item() -> None:
    cases, rows = _fixture(different_tie_physics=True)
    plan = build_route_level_bounded_execution_plan(
        formal_train=cases,
        source_rows=rows,
        source_root_sha256="3" * 64,
        source_review_root_sha256="4" * 64,
    )
    assert plan["status"].startswith("requires_ultra_review")
    assert plan["unique_identity_count"] == 3
    assert plan["tie_equivalence_proofs"][0]["non_equivalent_items_all_included"] is True


def test_bounded_terminal_requires_all_runs_exactly_64_and_zero_failures() -> None:
    cases, rows = _fixture()
    plan = build_route_level_bounded_execution_plan(
        formal_train=cases,
        source_rows=rows,
        source_root_sha256="3" * 64,
        source_review_root_sha256="4" * 64,
    )
    results = [
        {
            "schema_version": RESULT_SCHEMA_VERSION,
            "run_ordinal": run["run_ordinal"],
            "scenario_id": run["scenario_id"],
            "occurrence": run["occurrence"],
            "status": "complete",
            "tick_count": 64,
            "retained_capability_failure": None,
            "failure_class": "none",
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
        for run in plan["runs"]
    ]
    run_evidence = [
        {
            "schema_version": RUN_EVIDENCE_SCHEMA_VERSION,
            "run_ordinal": run["run_ordinal"],
            "scenario_id": run["scenario_id"],
            "occurrence": run["occurrence"],
            "tick_count": 64,
            "candidate0_sha256_sequence": ["1" * 64] * 64,
            "k8_row_sha256_sequence": [[f"{index:x}" * 64 for index in range(8)]] * 64,
            "atom_matrix_sha256_sequence": ["2" * 64] * 64,
            "context_sha256_sequence": ["3" * 64] * 64,
            "selected_index_sequence": [0] * 64,
            "failure_class": "none",
            "closed_loop_trajectory_sha256": "4" * 64,
            "speed_probe_sha256": "5" * 64,
        }
        for run in plan["runs"]
    ]
    terminal = validate_bounded_terminal_acceptance(
        plan, results, run_evidence=run_evidence
    )
    assert terminal["retained_capability_failure_count"] == 0
    assert terminal["tick_count"] == len(results) * 64

    failed = copy.deepcopy(results)
    failed[1]["status"] = "failed"
    failed[1]["tick_count"] = 0
    failed[1]["retained_capability_failure"] = {
        "reason": "mapped_current_signal_source_unavailable"
    }
    failed[1]["failure_class"] = "mapped_runtime_source_failure"
    with pytest.raises(ValueError, match="64-tick completion"):
        validate_bounded_terminal_acceptance(
            plan, failed, run_evidence=run_evidence
        )

    drifted = copy.deepcopy(run_evidence)
    drifted[-1]["selected_index_sequence"][-1] = 1
    with pytest.raises(ValueError, match="determinism comparison"):
        validate_bounded_terminal_acceptance(
            plan, results, run_evidence=drifted
        )


def test_plan_preflight_and_reviewer_are_k8_execution_free_and_independent() -> None:
    producer = (
        ROOT
        / "scripts"
        / "integrations"
        / "preflight_diffusion_planner_v25_a162_bounded_execution.py"
    ).read_text(encoding="utf-8")
    reviewer = (
        ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v25_a162_bounded_execution.py"
    ).read_text(encoding="utf-8")
    assert "build_native_arm_runner" not in producer
    assert "build_native_arm_runner" not in reviewer
    assert "diffusion_planner_v25_a162_bounded_execution import" not in reviewer
    assert canonical_sha256({"a": 1}) == (
        "e346432021b04179518d9614f3560ccd71354a4ee101ddcb893d6959a9d6301c"
    )
