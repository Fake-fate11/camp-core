from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations.diffusion_planner_v21_native import (
    summarize_route_comfort_native,
)
from camp_core.integrations.diffusion_planner_v22_native import (
    summarize_safety_cost_native_v22,
)
from camp_core.integrations.diffusion_planner_v25_metric_semantics import (
    FILTERED_SAMPLE_COUNT,
    LEGACY_ALIASES,
    METRIC_CLASSIFICATIONS,
    build_amendment,
    metric_semantics_contract,
    summarize_run,
    validate_metric_semantics_contract,
)
from camp_core.integrations.diffusion_planner_v25_signal_safety import (
    summarize_certified_signal_safety,
)


ROOT = Path(__file__).resolve().parents[2]


def test_contract_freezes_industrial_classes_aliases_and_claim_boundary() -> None:
    contract = metric_semantics_contract()
    validate_metric_semantics_contract(contract)
    assert contract["metric_classifications"] == METRIC_CLASSIFICATIONS
    assert METRIC_CLASSIFICATIONS["near_miss"] == "FAIL-industrial"
    assert METRIC_CLASSIFICATIONS["clustered_statistics"] == "PASS"
    assert METRIC_CLASSIFICATIONS["full_polygon_offroad"] == "evidence-missing"
    assert (
        LEGACY_ALIASES["safety.near_miss"]
        == "noncollision_obb_clearance_le_2m_tick_rate"
    )
    assert (
        contract["claim_invariance"]["final_claim_decision"]
        == "honest_no_claim_under_frozen_preregistered_all_gate"
    )
    assert contract["claim_invariance"]["new_confirmatory_claim_authorized"] is False
    assert (
        contract["missing_evidence"]["industrial_occupant_comfort"]
        == "evidence_missing_not_assessed"
    )


def test_contract_rejects_unknown_or_mutated_fields() -> None:
    contract = metric_semantics_contract()
    contract["unexpected"] = True
    with pytest.raises(ValueError, match="contract drifted"):
        validate_metric_semantics_contract(contract)
    contract = metric_semantics_contract()
    contract["body_proxy"]["filter"]["padding"] = True
    with pytest.raises(ValueError, match="contract drifted"):
        validate_metric_semantics_contract(contract)


def test_body_proxy_64_to_62_to_52_and_signed_rotation() -> None:
    native, row = _fixture(acceleration_xy=(1.0, 0.0), heading=np.pi / 2.0)
    result = summarize_run(native, row)
    body = result["vehicle_body_kinematic_comfort_proxy"]
    assert body["sample_count"] == FILTERED_SAMPLE_COUNT == 52
    assert body["discarded_boundary_raw_samples"] == 10
    assert body["longitudinal_mps2"]["signed_mean"] == pytest.approx(0.0, abs=1e-10)
    assert body["lateral_mps2"]["signed_mean"] == pytest.approx(-1.0, abs=1e-10)
    assert body["lateral_mps2"]["rms"] == pytest.approx(1.0, abs=1e-10)
    assert body["filter"] == {
        "kind": "centered_equal_weight_boxcar",
        "width_samples": 11,
        "window_s": 1.0,
        "zero_phase": True,
        "valid_only": True,
        "padding": False,
        "extrapolation": False,
    }


def test_duration_grid_is_count_times_point_one_without_padding() -> None:
    native, row = _fixture(acceleration_xy=(2.5, 0.0), heading=0.0)
    body = summarize_run(native, row)["vehicle_body_kinematic_comfort_proxy"]
    durations = body["duration_s"]["longitudinal_abs_gt"]
    assert durations == {"0_5": 5.2, "1": 5.2, "2": 5.2, "3": 0.0}
    assert body["duration_s"]["signed_deceleration_lt_negative"] == {
        "0_5": 0.0,
        "1": 0.0,
        "2": 0.0,
        "3": 0.0,
    }
    assert body["duration_grid_is_project_sensitivity_not_industrial_threshold"]


def test_clearance_speed_red_and_route_extensions_use_exact_ticks() -> None:
    clearances = [3.0] * 64
    clearances[2:5] = [0.4, 0.4, 0.4]
    clearances[9:11] = [0.4, 0.4]
    progress = [float(i) for i in range(64)]
    progress[32] = progress[31] - 2.0
    native, row = _fixture(
        acceleration_xy=(0.0, 0.0),
        heading=0.0,
        clearances=clearances,
        progress=progress,
        speed_mps=1.2,
        speed_limit_mps=1.0,
    )
    result = summarize_run(native, row)
    clearance = result["clearance_descriptive"]
    assert clearance["thresholds_le_m"]["0_5"] == {
        "sample_count": 5,
        "duration_s": 0.5,
        "episode_count": 2,
    }
    speed = result["speed_protocol_descriptive"]
    assert speed["strict"]["event_count"] == 64
    assert speed["sensitivity"]["0.1"]["event_rate"] == 1.0
    assert speed["continuous"]["maximum_excess_mps"] == pytest.approx(0.2)
    assert speed["continuous"]["excess_duration_s"] == 6.4
    route = result["route_descriptive"]
    assert route["net_route_projection_m"] == pytest.approx(63.0)
    assert route["maximum_route_projection_gain_m"] == pytest.approx(63.0)
    assert route["backtracking_duration_s"] == pytest.approx(0.1)
    assert route["backtracking_distance_m"] == pytest.approx(2.0)
    red = result["certified_signal_descriptive"]
    assert red["certified_phase_line_binding"] is True
    assert red["unthresholded_crossing_count"] == 0
    assert red["legal_or_type_approval_violation_rate_claimed"] is False


def test_legacy_values_are_preserved_and_mutation_fails_closed() -> None:
    native, row = _fixture()
    result = summarize_run(native, row)
    for name, item in result["legacy_namespace"].items():
        assert item["legacy_field"] == name
        assert item["deprecated_industrial_interpretation"] is True
        assert item["source_root_role"] == "sealed_fresh_b4_execution"
    mutated = copy.deepcopy(row)
    mutated["safety"]["near_miss"] += 0.01
    with pytest.raises(ValueError, match="legacy value drifted"):
        summarize_run(native, mutated)


def test_missing_polygon_seat_vertical_and_standard_evidence_fail_closed() -> None:
    native, row = _fixture()
    result = summarize_run(native, row)
    assert result["full_polygon_offroad"] == {
        "status": "evidence_missing",
        "five_point_proxy_used_as_polygon_substitute": False,
    }
    assert result["occupant_comfort"] == {
        "status": "evidence_missing_not_assessed",
        "vehicle_body_proxy_is_seat_or_human_response": False,
    }
    assert (
        result["vehicle_body_kinematic_comfort_proxy"][
            "iso_2631_or_sae_j2834_conformity_claimed"
        ]
        is False
    )


def test_per_run_summary_precedes_cluster_and_does_not_change_claim() -> None:
    native, base_row = _fixture()
    runs = []
    for pair_index in range(500):
        for arm in ("candidate0", "static14d", "scene14d"):
            row = copy.deepcopy(base_row)
            row["pair_key"] = f"pair-{pair_index:03d}"
            row["arm"] = arm
            row["inference_cluster_id"] = f"cluster-{pair_index % 100:03d}"
            runs.append(summarize_run(native, row))
    amendment = build_amendment(
        runs,
        bindings={"synthetic": True},
        contract_root_sha256="a" * 64,
        contract_review_root_sha256="b" * 64,
        source_file_sha256="c" * 64,
    )
    assert amendment["sample_accounting"][
        "per_run_summarized_before_pairing_and_clustering"
    ]
    assert amendment["sample_accounting"]["ticks_pooled_as_independent"] is False
    assert amendment["denominator"]["pair_count"] == 500
    assert (
        amendment["descriptive_paired_cluster_summaries"]["static14d"][
            "route_descriptive.net_route_projection_m"
        ]["independent_cluster_count"]
        == 100
    )
    assert amendment["claim_invariance"]["frozen_claim_recomputed"] is False


def test_pure_formula_path_does_not_write_raw_artifact_or_cas(tmp_path: Path) -> None:
    native, row = _fixture()
    before = list(tmp_path.iterdir())
    summarize_run(native, row)
    assert list(tmp_path.iterdir()) == before


def test_reviewer_does_not_import_producer_metric_module() -> None:
    text = (
        ROOT
        / "scripts"
        / "integrations"
        / "review_diffusion_planner_v25_metric_semantics_amendment.py"
    ).read_text(encoding="utf-8")
    assert "diffusion_planner_v25_metric_semantics import" not in text
    assert "producer_metric_module_imported" in text


def _fixture(
    *,
    acceleration_xy: tuple[float, float] = (1.0, 0.0),
    heading: float = 0.0,
    clearances: list[float] | None = None,
    progress: list[float] | None = None,
    speed_mps: float = 1.0,
    speed_limit_mps: float = 2.0,
) -> tuple[dict, dict]:
    clearances = clearances or [3.0] * 64
    progress = progress or [float(i) * 0.1 for i in range(64)]
    positions = [
        [
            0.5 * acceleration_xy[0] * (index * 0.1) ** 2,
            0.5 * acceleration_xy[1] * (index * 0.1) ** 2,
        ]
        for index in range(64)
    ]
    ticks = []
    for index in range(64):
        safety = {
            "tick_index": index,
            "position_xy": [float(v) for v in positions[index]],
            "speed_mps": float(speed_mps),
            "ego_heading_rad": float(heading),
            "route_heading_rad": 0.0,
            "route_progress_m": float(progress[index]),
            "five_point_drivable_coverage": True,
            "min_obb_clearance_m": float(clearances[index]),
            "red_light_at_interval_start": False,
            "front_center_prev_xy": [float(v) for v in positions[max(index - 1, 0)]],
            "front_center_xy": [float(v) for v in positions[index]],
            "red_stop_lines": [],
            "speed_limit_mps": float(speed_limit_mps),
            "constant_velocity_circle_ttc_diagnostic_s": None,
            "source_complete": True,
            "signal_phase_at_interval_start": "none",
            "certified_signal_stop_lines": [],
            "pre_decision_speed_mps": float(speed_mps),
        }
        ticks.append(
            {
                "tick_index": index,
                "pre_decision_speed_mps": float(speed_mps),
                "safety": safety,
            }
        )
    safety_summary = summarize_safety_cost_native_v22(
        [tick["safety"] for tick in ticks]
    )
    secondary = summarize_route_comfort_native(
        [tick["safety"] for tick in ticks],
        dt=0.1,
        route_progress_m=float(progress[-1]),
        route_length_m=100.0,
        termination_reason="horizon",
    )
    signal = summarize_certified_signal_safety(
        [tick["safety"] for tick in ticks]
    )
    performance = {
        "progress": secondary["route_progress_m"],
        "completion": secondary["route_completion_rate"],
        "mean_jerk": secondary["mean_abs_jerk_mps3"],
        "max_jerk": secondary["max_jerk_mps3"],
        "mean_lateral_acceleration": secondary[
            "mean_abs_lateral_acceleration_mps2"
        ],
        "max_lateral_acceleration": secondary[
            "max_abs_lateral_acceleration_mps2"
        ],
        "maximum_deceleration": 0.0,
    }
    row = {
        "pair_key": "pair-000",
        "arm": "candidate0",
        "inference_cluster_id": "cluster-000",
        "benchmark_stratum": "naturalistic",
        "scenario_family": "naturalistic_background",
        "source_class": "no_signal",
        "status": "complete",
        "safety": {
            "total": safety_summary["safety_cost"],
            "collision": safety_summary["components"]["collision_any"],
            "near_miss": safety_summary["components"][
                "near_miss_noncollision_rate"
            ],
            "offroad": safety_summary["components"]["offroad_rate"],
            "wrong_way": safety_summary["components"]["wrong_way_rate"],
            "red_light": safety_summary["components"]["red_light_violation_any"],
            "speed": safety_summary["components"]["speed_limit_violation_rate"],
        },
        "performance": performance,
    }
    native = {
        "ticks": ticks,
        "safety": safety_summary,
        "secondary": secondary,
        "signal_safety": signal,
    }
    return native, row
