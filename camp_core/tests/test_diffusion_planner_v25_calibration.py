from __future__ import annotations

import copy
import hashlib
import json

import pytest

from camp_core.integrations.diffusion_planner_v25_calibration import (
    CALIBRATION_ROOT_BINDINGS,
    COMPONENT_REGRESSION_MARGINS,
    NONINFERIORITY_ENGINEERING_MARGINS,
    SAFETY_COST_COMPONENT_WEIGHTS,
    estimate_v25_noninferiority_margin_resolvability,
    freeze_v25_calibration_contract,
    project_candidate0_ni_calibration_row,
)


def _native_candidate0() -> dict:
    ticks = []
    for index in range(64):
        ticks.append(
            {
                "tick_index": index,
                "selected_index": 0,
                "input_sha256": f"{index + 1:064x}",
                "default_output_sha256": f"{index + 101:064x}",
                "candidate_tensor_sha256_before": f"{index + 201:064x}",
                "candidate_tensor_sha256_after": f"{index + 201:064x}",
                "pre_decision_speed_mps": 8.0,
                "safety": {"speed_mps": 7.9 if index == 0 else 8.0},
            }
        )
    return {
        "schema_version": "v21_native_arm_receipt_v1",
        "status": "ok",
        "arm": "dp",
        "fixed_dp_head": "7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "route_sha256": "a" * 64,
        "scenario_seed": 25001,
        "spawn_config_sha256": "9" * 64,
        "initial_state_sha256": "b" * 64,
        "initial_input_sha256": ticks[0]["input_sha256"],
        "ticks": ticks,
        "secondary": {
            "route_progress_m": 100.0,
            "route_completion_rate": 0.9,
            "mean_abs_jerk_mps3": 0.5,
            "max_jerk_mps3": 1.0,
            "mean_abs_lateral_acceleration_mps2": 0.2,
            "max_abs_lateral_acceleration_mps2": 0.5,
        },
        "claim_authorized": False,
    }


def test_candidate0_calibration_row_is_mechanical_and_deterministic() -> None:
    native = _native_candidate0()
    first = project_candidate0_ni_calibration_row(
        heterogeneity_cluster_id="map-a",
        run_instance_sha256="1" * 64,
        scenario_identity_sha256="2" * 64,
        route_identity_sha256="3" * 64,
        semantic_parameter_block_sha256="4" * 64,
        native_receipt=native,
    )
    second = project_candidate0_ni_calibration_row(
        heterogeneity_cluster_id="map-a",
        run_instance_sha256="1" * 64,
        scenario_identity_sha256="2" * 64,
        route_identity_sha256="3" * 64,
        semantic_parameter_block_sha256="4" * 64,
        native_receipt=copy.deepcopy(native),
    )
    assert first == second
    assert first["arm"] == "candidate0_operational_default"
    assert first["performance"]["maximum_deceleration"] == pytest.approx(1.0)
    assert first["performance"]["progress"] == 100.0
    assert len(first["measurement_sha256"]) == 64


@pytest.mark.parametrize(
    "mutation",
    ("wrong_fixed_dp", "nonzero_selected", "candidate_modified", "input_unbound"),
)
def test_candidate0_calibration_projection_fails_closed_on_authority_drift(
    mutation: str,
) -> None:
    native = _native_candidate0()
    if mutation == "wrong_fixed_dp":
        native["fixed_dp_head"] = "0" * 40
    elif mutation == "nonzero_selected":
        native["ticks"][5]["selected_index"] = 1
    elif mutation == "candidate_modified":
        native["ticks"][5]["candidate_tensor_sha256_after"] = "f" * 64
    else:
        native["initial_input_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        project_candidate0_ni_calibration_row(
            heterogeneity_cluster_id="map-a",
            run_instance_sha256="1" * 64,
            scenario_identity_sha256="2" * 64,
            route_identity_sha256="3" * 64,
            semantic_parameter_block_sha256="4" * 64,
            native_receipt=native,
        )


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode()
    ).hexdigest()


def _candidate0_rows(
    *,
    count: int = 10,
    excessive_progress_variability: bool = False,
    exact_duplicates: bool = False,
):
    rows = []
    base = {
        "progress": 100.0,
        "completion": 0.9,
        "mean_jerk": 0.5,
        "max_jerk": 1.0,
        "mean_lateral_acceleration": 0.2,
        "max_lateral_acceleration": 0.5,
        "maximum_deceleration": 1.0,
    }
    for index in range(count):
        cluster = index % 5
        repeat = index // 5
        performance = dict(base)
        for name, margin in NONINFERIORITY_ENGINEERING_MARGINS.items():
            performance[name] += (repeat % 2) * margin / 2.0
        if excessive_progress_variability and cluster == 4 and repeat % 2:
            performance["progress"] += 4.0
        identity_index = cluster if exact_duplicates else index
        repeatability_identity = {
            "schema_version": "camp_dp_v25_exact_candidate0_repeatability_identity_v1",
            "route_identity_sha256": f"{identity_index + 1000:064x}",
            "scenario_identity_sha256": f"{identity_index + 2000:064x}",
            "semantic_parameter_block_sha256": f"{identity_index + 3000:064x}",
            "scenario_seed": 25001 + identity_index,
            "spawn_config_sha256": f"{identity_index + 4000:064x}",
            "initial_state_sha256": f"{identity_index + 5000:064x}",
            "initial_input_sha256": f"{identity_index + 6000:064x}",
            "same_initial_state_and_exogenous_schedule_per_pair": True,
        }
        rows.append(
            {
                "schema_version": "camp_dp_v25_candidate0_ni_calibration_row_v2",
                "arm": "candidate0_operational_default",
                "heterogeneity_cluster_id": f"map-{cluster}",
                "run_instance_sha256": f"{index + 7000:064x}",
                "repeatability_identity": repeatability_identity,
                "repeatability_identity_sha256": _canonical_sha(
                    repeatability_identity
                ),
                "measurement_sha256": f"{index + 1:064x}",
                "performance": performance,
                "fresh_b2_opened": False,
                "fresh_outcome_fields_consumed": [],
            }
        )
    return rows


def _freeze(
    *,
    routes: int = 50,
    corridors: int = 5,
    eligible: int = 95,
    excessive_progress_variability: bool = False,
):
    resolution = estimate_v25_noninferiority_margin_resolvability(
        _candidate0_rows(
            count=eligible,
            excessive_progress_variability=excessive_progress_variability
        )
    )
    return freeze_v25_calibration_contract(
        root_bindings={name: "a" * 64 for name in CALIBRATION_ROOT_BINDINGS},
        inventory={
            "map_count": 5,
            "intersection_count": 5,
            "corridor_count": corridors,
            "route_count": routes,
            "planned_paired_run_count": 100,
            "paired_eligible_run_count": eligible,
            "retained_failure_run_count": 100 - eligible,
            "paired_eligible_rate": eligible / 100,
        },
        noninferiority_resolvability=resolution,
        frozen_model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
    )


def test_calibration_freeze_binds_thresholds_margins_and_roots() -> None:
    result = _freeze()
    assert result["status"] == "calibration_freeze_passed"
    assert result["fresh_preopen_qualification_allowed"] is True
    assert result["fresh_open_authorized"] is False
    assert result["repeatability_estimation_status"] == (
        "not_estimable_no_exact_candidate0_duplicates"
    )
    assert result["repeatability_gate_blocks_fresh"] is False
    assert result["one_time_opening_release_required"] is True
    assert result["operational_overspeed_tolerance_mps"] == 0.1
    assert result["safety_cost_contract"]["component_weights"] == (
        SAFETY_COST_COMPONENT_WEIGHTS
    )
    assert result["safety_cost_contract"]["legacy_10m_stop_line_proximity_allowed"] is False
    assert result["signal_safety_contract"]["schema_version"] == (
        "camp_dp_v25_certified_signal_safety_v1"
    )
    assert result["signal_safety_contract"]["future_phase_schedule_consumed"] is False
    assert result["signal_safety_contract"]["phase_remaining_consumed"] is False
    assert result["signal_safety_contract"]["false_stop_green_approach_distance_m"] == 5.0
    assert result["signal_safety_contract"][
        "false_stop_green_minimum_obb_clearance_m"
    ] == 3.0
    assert result["atom_scale_changed_by_calibration"] is False
    assert result["model_parameters_changed_by_calibration"] is False
    assert result["noninferiority_margin_changed_by_calibration"] is False
    assert result["calibration_candidate0_outcomes_consumed"] is True
    assert result["calibration_camp_method_outcomes_consumed"] is False
    assert result["fresh_b2_opened"] is False
    assert result["noninferiority"]["margins"] == NONINFERIORITY_ENGINEERING_MARGINS
    assert result["component_guardrails"]["margins"] == COMPONENT_REGRESSION_MARGINS
    assert result["noninferiority"]["calibration_resolvability"][
        "camp_method_outcomes_consumed"
    ] is False


def test_cross_scenario_heterogeneity_is_not_repeatability_or_opening_veto() -> None:
    result = estimate_v25_noninferiority_margin_resolvability(_candidate0_rows())
    assert result["status"] == "exact_duplicate_repeatability_not_estimable"
    assert result["margins"] == NONINFERIORITY_ENGINEERING_MARGINS
    assert result["heterogeneity_cluster_count"] == 5
    assert result["measurement_count"] == 10
    assert result["exact_duplicate_group_count"] == 0
    assert result["repeatability_status"] == (
        "not_estimable_no_exact_candidate0_duplicates"
    )
    assert result["all_repeatability_margins_resolvable"] is None
    assert result["repeatability_gate_blocks_fresh"] is False
    for name, margin in NONINFERIORITY_ENGINEERING_MARGINS.items():
        assert result["q95_within_map_cross_scenario_heterogeneity"][
            name
        ] == pytest.approx(margin / 4.0)
        assert result["q95_exact_duplicate_repeatability"][name] is None


def test_cross_scenario_heterogeneity_cannot_block_fresh_or_enlarge_margin() -> None:
    result = _freeze(excessive_progress_variability=True)
    resolution = result["noninferiority"]["calibration_resolvability"]
    assert resolution["q95_within_map_cross_scenario_heterogeneity"][
        "progress"
    ] > NONINFERIORITY_ENGINEERING_MARGINS["progress"]
    assert resolution["repeatability_status"] == (
        "not_estimable_no_exact_candidate0_duplicates"
    )
    assert resolution["margins"] == NONINFERIORITY_ENGINEERING_MARGINS
    assert result["status"] == "calibration_freeze_passed"
    assert result["fresh_preopen_qualification_allowed"] is True
    assert result["fresh_open_authorized"] is False


def test_true_exact_duplicate_repeatability_can_block_without_changing_margin() -> None:
    resolution = estimate_v25_noninferiority_margin_resolvability(
        _candidate0_rows(
            exact_duplicates=True,
            excessive_progress_variability=True,
        )
    )
    assert resolution["exact_duplicate_group_count"] == 5
    assert resolution["repeatability_status"] == (
        "exact_duplicate_repeatability_estimated"
    )
    assert resolution["repeatability_margin_resolvable"]["progress"] is False
    assert resolution["repeatability_gate_blocks_fresh"] is True
    frozen = freeze_v25_calibration_contract(
        root_bindings={name: "a" * 64 for name in CALIBRATION_ROOT_BINDINGS},
        inventory={
            "map_count": 5,
            "intersection_count": 5,
            "corridor_count": 5,
            "route_count": 50,
            "planned_paired_run_count": 100,
            "paired_eligible_run_count": 10,
            "retained_failure_run_count": 90,
            "paired_eligible_rate": 0.1,
        },
        noninferiority_resolvability=resolution,
        frozen_model_registry_sha256="b" * 64,
        training_scale_sha256="c" * 64,
        context_scaler_sha256="d" * 64,
    )
    assert frozen["repeatability_gate_blocks_fresh"] is True
    assert frozen["fresh_preopen_qualification_allowed"] is False


def test_repeatability_estimator_rejects_method_fresh_and_cluster_drift() -> None:
    rows = _candidate0_rows()
    rows[0]["arm"] = "scene14d"
    with pytest.raises(ValueError, match="candidate0 rows only"):
        estimate_v25_noninferiority_margin_resolvability(rows)

    rows = _candidate0_rows()
    rows[0]["fresh_b2_opened"] = True
    with pytest.raises(ValueError, match="Fresh outcomes"):
        estimate_v25_noninferiority_margin_resolvability(rows)

    rows = _candidate0_rows()
    rows[0]["heterogeneity_cluster_id"] = rows[2][
        "heterogeneity_cluster_id"
    ]
    rows[5]["heterogeneity_cluster_id"] = rows[2][
        "heterogeneity_cluster_id"
    ]
    with pytest.raises(ValueError, match="five map clusters"):
        estimate_v25_noninferiority_margin_resolvability(rows)


@pytest.mark.parametrize(
    ("routes", "corridors", "eligible"),
    [(49, 5, 95), (50, 4, 95), (50, 5, 94)],
)
def test_calibration_freeze_reports_ineligible_inventory_without_faking_independence(
    routes: int, corridors: int, eligible: int
) -> None:
    result = _freeze(routes=routes, corridors=corridors, eligible=eligible)
    assert result["status"] == "calibration_freeze_scientifically_ineligible"
    assert result["fresh_preopen_qualification_allowed"] is False
    assert result["fresh_open_authorized"] is False


def test_calibration_freeze_rejects_denominator_and_type_drift() -> None:
    with pytest.raises(ValueError, match="denominator"):
        freeze_v25_calibration_contract(
            root_bindings={name: "a" * 64 for name in CALIBRATION_ROOT_BINDINGS},
            inventory={
                "map_count": 5,
                "intersection_count": 5,
                "corridor_count": 5,
                "route_count": 50,
                "planned_paired_run_count": 100,
                "paired_eligible_run_count": 95,
                "retained_failure_run_count": 4,
                "paired_eligible_rate": 0.95,
            },
            noninferiority_resolvability=(
                estimate_v25_noninferiority_margin_resolvability(_candidate0_rows())
            ),
            frozen_model_registry_sha256="b" * 64,
            training_scale_sha256="c" * 64,
            context_scaler_sha256="d" * 64,
        )
