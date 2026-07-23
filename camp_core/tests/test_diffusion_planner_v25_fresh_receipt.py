from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_evaluation import (
    validate_fresh_b2_evaluation_row,
)
from camp_core.integrations.diffusion_planner_v25_fresh_b2 import FIXED_DP_HEAD
from camp_core.integrations.diffusion_planner_v25_fresh_receipt import (
    CANDIDATE0_POOL_SCHEMA_VERSION,
    build_candidate0_pool_evidence,
    build_fresh_b2_complete_row,
    build_fresh_b2_failure_row,
)


def _manifest() -> dict:
    return {
        "source_family": "controlled-synthetic",
        "map_geometry_sha256": "1" * 64,
        "map_file_sha256": "2" * 64,
        "intersection_sha256": None,
        "corridor_sha256": "3" * 64,
        "route_family_sha256": "4" * 64,
        "semantic_parameter_block_sha256": "5" * 64,
        "route_identity_sha256": "6" * 64,
        "benchmark_stratum": "naturalistic",
        "scenario_family": "naturalistic_background",
        "tier": "naturalistic",
        "signal_source_class": "no_signal",
        "phase_authority_mode": None,
        "source_chain": {},
        "route_length_m": 100.0,
        "speed_source_sha256": "7" * 64,
        "static_signal_chain_qualified": True,
        "runtime_same_tick_signal_receipt_required": True,
        "runtime_fixed_dp_k8_support_required": True,
        "preopen_dp_forward_executed": False,
        "outcome_fields_consumed": [],
    }


def _signal() -> dict:
    return {
        "schema_version": "camp_dp_v25_certified_signal_safety_v1",
        "source_class": "no_signal",
        "metrics": {
            "red_light_violation_rate": 0.0,
            "stop_line_crossing_rate": 0.0,
            "stop_line_margin_m": 0.0,
            "crossing_speed_mps": 0.0,
            "false_stop_on_green_rate": 0.0,
        },
        "counts": {
            "red_crossing_intervals": 0,
            "red_violation_intervals": 0,
            "green_false_stop_intervals": 0,
        },
        "denominators": {
            "red_phase_intervals": 0,
            "green_phase_intervals": 0,
            "green_unblocked_approach_intervals": 0,
            "yellow_phase_intervals": 0,
        },
        "thresholds": {},
        "certified_stop_line_used": False,
        "legacy_proximity_heuristic_used": False,
        "future_phase_schedule_consumed": False,
        "phase_remaining_consumed": False,
    }


def _native(arm: str) -> dict:
    native_arm = "dp" if arm == "candidate0" else "camp"
    ticks = []
    for index in range(64):
        selected_index = 0 if arm == "candidate0" else 1
        candidate_rows = [f"{1000 + index * 8 + row:064x}" for row in range(8)]
        tick = {
            "tick_index": index,
            "candidate_tensor_sha256_before": "a" * 64,
            "candidate_tensor_sha256_after": "a" * 64,
            "candidate_row_sha256": candidate_rows,
            "default_output_sha256": candidate_rows[0],
            "selected_trajectory_sha256": candidate_rows[selected_index],
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "max_abs_difference": 0.0,
                "default_output_sha256": candidate_rows[0],
                "candidate0_sha256": candidate_rows[0],
                "native_ranked_k8": False,
            },
            "selected_index": selected_index,
            "source_valid_mask": [True] * 8,
            "physical_feasible_mask": [True, False, False, False, False, False, False, False],
            "pre_decision_speed_mps": 8.0,
            "safety": {
                "speed_mps": 7.9,
                "signal_phase_at_interval_start": "none",
            },
            "latency_ms": {
                "default_inference": 1.0,
                "candidate_inference": 7.0,
                "tracker": 0.5,
                "total_planning": 10.0,
            },
        }
        if arm == "candidate0":
            tick.update(
                candidate0_operational_default=True,
                selection_policy="candidate0_operational_default",
                score_contract="candidate0_operational_default",
                eligibility_mask_name="candidate0_operational_default",
            )
        else:
            tick.update(
                selection_policy="v22_source_valid",
                score_contract="score_k(w)=a_k^T w",
                eligibility_mask_name="source_valid_mask",
            )
        if arm != "candidate0":
            tick["latency_ms"].update(atom_materialization=0.3, selector=0.1)
        if arm == "scene14d":
            tick["latency_ms"].update(context=0.2, scene_weight=0.05)
            tick["v25_scene_selector"] = {
                "schema_version": "camp_dp_v25_scene_weight_receipt_v3",
                "model_name": "CAMP-Scene14D",
                "fixed_dp_head": FIXED_DP_HEAD,
                "training_root_sha256": "b" * 64,
                "training_review_root_sha256": "c" * 64,
                "theta_sha256": "d" * 64,
                "context_scaler_sha256": "e" * 64,
                "phi_sha256": f"{index:064x}",
                "weights_sha256": f"{index + 64:064x}",
                "runtime_projection": False,
                "softmax": False,
            }
        ticks.append(tick)
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "fixed_dp_head": FIXED_DP_HEAD,
        "route_sha256": "8" * 64,
        "logical_map_sha256": "2" * 64,
        "checkpoint_sha256": "9" * 64,
        "args_sha256": "a" * 64,
        "arm": native_arm,
        "scenario_seed": 25001,
        "spawn_config_sha256": "b" * 64,
        "initial_state_sha256": "c" * 64,
        "initial_input_sha256": "d" * 64,
        "ticks": ticks,
        "claim_authorized": False,
        "safety": {
            "schema_version": "safety_cost_native_v22",
            "safety_cost": 0.0,
            "components": {
                "collision_any": 0.0,
                "near_miss_noncollision_rate": 0.0,
                "offroad_rate": 0.0,
                "red_light_violation_any": 0.0,
                "speed_limit_violation_rate": 0.0,
                "wrong_way_rate": 0.0,
            },
        },
        "secondary": {
            "route_progress_m": 50.0,
            "route_completion_rate": 0.5,
            "mean_abs_jerk_mps3": 0.2,
            "max_jerk_mps3": 0.4,
            "mean_abs_lateral_acceleration_mps2": 0.1,
            "max_abs_lateral_acceleration_mps2": 0.3,
        },
        "signal_safety": _signal(),
    }


def _pool() -> dict:
    return build_candidate0_pool_evidence(_native("candidate0"))


def test_complete_rows_are_mechanical_and_bind_scene_authority() -> None:
    rows = []
    for order, arm in enumerate(("candidate0", "static14d", "scene14d")):
        row = build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-1",
            arm=arm,
            arm_order_index=order,
            native_receipt=_native(arm),
            candidate0_pool_evidence=_pool() if arm == "candidate0" else None,
        )
        rows.append(validate_fresh_b2_evaluation_row(row))
    assert rows[0]["selected_index_sequence"] == [0] * 64
    assert rows[1]["selected_index_sequence"] == [1] * 64
    assert rows[0]["latency_ms"]["atoms"] == [0.0] * 64
    assert rows[2]["latency_ms"]["scene_weight"] == [0.05] * 64
    assert abs(rows[2]["performance"]["maximum_deceleration"] - 1.0) < 1e-12


def test_candidate0_pool_and_scene_authority_fail_closed() -> None:
    wrong_native_dp = _native("candidate0")
    wrong_native_dp["fixed_dp_head"] = "0" * 40
    with pytest.raises(ValueError, match="fixed DP authority"):
        build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-1",
            arm="candidate0",
            arm_order_index=0,
            native_receipt=wrong_native_dp,
            candidate0_pool_evidence=_pool(),
        )

    missing_mask = _native("candidate0")
    missing_mask["ticks"][0].pop("source_valid_mask")
    with pytest.raises(ValueError, match="source_valid_mask"):
        build_candidate0_pool_evidence(missing_mask)

    wrong_identity = _native("candidate0")
    wrong_identity["ticks"][0]["default_candidate0_identity"][
        "native_ranked_k8"
    ] = True
    with pytest.raises(ValueError, match="candidate0/default identity"):
        build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-a",
            arm="candidate0",
            arm_order_index=0,
            native_receipt=wrong_identity,
            candidate0_pool_evidence=_pool(),
        )

    wrong_selected = _native("static14d")
    wrong_selected["ticks"][0]["selected_trajectory_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="candidate0/default identity"):
        build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-a",
            arm="static14d",
            arm_order_index=1,
            native_receipt=wrong_selected,
        )

    swapped_pool = _pool()
    swapped_pool["ticks"][0]["candidate_tensor_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="same-forward K8"):
        build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-a",
            arm="candidate0",
            arm_order_index=0,
            native_receipt=_native("candidate0"),
            candidate0_pool_evidence=swapped_pool,
        )

    bad_pool = _pool()
    bad_pool["ticks"][0]["source_valid_mask"] = [False] * 8
    try:
        build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-1",
            arm="candidate0",
            arm_order_index=0,
            native_receipt=_native("candidate0"),
            candidate0_pool_evidence=bad_pool,
        )
    except ValueError as exc:
        assert "source/physical" in str(exc)
    else:
        raise AssertionError("empty candidate0 source-valid set was accepted")

    scene = _native("scene14d")
    scene["ticks"][1]["v25_scene_selector"]["training_root_sha256"] = "f" * 64
    try:
        build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-1",
            arm="scene14d",
            arm_order_index=2,
            native_receipt=scene,
        )
    except ValueError as exc:
        assert "authority changed" in str(exc)
    else:
        raise AssertionError("Scene authority drift was accepted")

    wrong_dp = _native("scene14d")
    wrong_dp["ticks"][0]["v25_scene_selector"]["fixed_dp_head"] = "0" * 40
    with pytest.raises(ValueError, match="selector receipt drifted"):
        build_fresh_b2_complete_row(
            qualification_row=_manifest(),
            pair_key="pair-1",
            arm="scene14d",
            arm_order_index=2,
            native_receipt=wrong_dp,
        )


def test_failure_row_retains_denominator_without_outcome_imputation() -> None:
    row = build_fresh_b2_failure_row(
        qualification_row=_manifest(),
        pair_key="pair-1",
        arm="static14d",
        arm_order_index=1,
        status="fixed_dp_candidate_generation_capability_failure",
        failure_class="invalid_k8_heading_norm_envelope",
        signal_phase="none",
        pair_authority={
            "route_identity_sha256": "6" * 64,
            "semantic_parameter_block_sha256": "5" * 64,
            "native_route_sha256": "8" * 64,
            "logical_map_sha256": "2" * 64,
            "scenario_seed": 25001,
            "spawn_config_sha256": "b" * 64,
            "initial_state_sha256": "c" * 64,
            "initial_input_sha256": "d" * 64,
        },
    )
    validated = validate_fresh_b2_evaluation_row(copy.deepcopy(row))
    assert validated["safety"] is None
    assert validated["selected_index_sequence"] is None

    with pytest.raises(ValueError, match="failure taxonomy drifted"):
        build_fresh_b2_failure_row(
            qualification_row=_manifest(),
            pair_key="pair-1",
            arm="static14d",
            arm_order_index=1,
            status="fixed_dp_candidate_generation_capability_failure",
            failure_class="generic_failure",
            signal_phase="none",
            pair_authority={
                "route_identity_sha256": "6" * 64,
                "semantic_parameter_block_sha256": "5" * 64,
                "native_route_sha256": "8" * 64,
                "logical_map_sha256": "2" * 64,
                "scenario_seed": 25001,
                "spawn_config_sha256": "b" * 64,
                "initial_state_sha256": "c" * 64,
                "initial_input_sha256": "d" * 64,
            },
        )


def test_mapped_source_ineligible_row_is_retained_without_outcome_values() -> None:
    manifest = _manifest()
    manifest.update(
        benchmark_stratum="controlled_stress",
        scenario_family="red_light_phase_timing",
        tier="borderline",
        signal_source_class="mapped_signal",
        phase_authority_mode="observe_same_tick_request",
        intersection_sha256="9" * 64,
    )
    row = build_fresh_b2_failure_row(
        qualification_row=manifest,
        pair_key="pair-source",
        arm="candidate0",
        arm_order_index=0,
        status="source_ineligible",
        failure_class="preregistered_source_ineligible",
        signal_phase="unavailable",
        pair_authority={
            "route_identity_sha256": "6" * 64,
            "semantic_parameter_block_sha256": "5" * 64,
            "native_route_sha256": "8" * 64,
            "logical_map_sha256": "2" * 64,
            "scenario_seed": 25001,
            "spawn_config_sha256": "b" * 64,
            "initial_state_sha256": "c" * 64,
            "initial_input_sha256": "d" * 64,
        },
    )
    validated = validate_fresh_b2_evaluation_row(row)
    assert validated["status"] == "source_ineligible"
    assert validated["signal_phase"] == "unavailable"
    assert validated["safety"] is None

    wrong = copy.deepcopy(row)
    wrong["failure_class"] = "generic_source_failure"
    with pytest.raises(ValueError, match="evidence contract"):
        validate_fresh_b2_evaluation_row(wrong)
