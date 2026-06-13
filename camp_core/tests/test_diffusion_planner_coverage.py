from __future__ import annotations

import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_coverage import (
    compute_atom_coverage_report,
    parse_selection_log_metadata,
)


def test_parse_selection_log_metadata_from_benchmark_layout(tmp_path: Path) -> None:
    log_path = (
        tmp_path
        / "camp_dp_formal_v7_robust_dceeefd"
        / "sample59_86"
        / "seed_12"
        / "npc_4"
        / "spawn_0p3"
        / "tl_on"
        / "static"
        / "camp_selection_log.json"
    )

    metadata = parse_selection_log_metadata(log_path)

    assert metadata.run_root == "camp_dp_formal_v7_robust_dceeefd"
    assert metadata.route == "sample59_86"
    assert metadata.seed == 12
    assert metadata.npc_count == 4
    assert metadata.spawn == "spawn_0p3"
    assert metadata.traffic_light == "on"
    assert metadata.mode == "static"


def test_atom_coverage_report_detects_red_light_augmentation_gain(
    tmp_path: Path,
) -> None:
    log_path = _write_selection_log(
        tmp_path,
        [
            _record(
                scores=[0.1, 0.2],
                feasible=[True, True],
                selected_index=0,
                used_fallback=False,
                reward_total=[0.0, 1.0],
                red_light_cost=[-1.0, 0.0],
                outcome_value=[0.0, 1.0],
                red_light_violation=[True, False],
                lateral_acceleration=[2.0, 0.1],
            )
        ],
    )

    report = compute_atom_coverage_report([log_path], mode_filter={"static"})

    assert report["summary"]["log_count"] == 1
    assert report["summary"]["record_count"] == 1
    assert report["summary"]["atom_dimensions"] == [10]
    prior_shadow = report["shadow_dp_prior_deviation"]
    assert prior_shadow["record_availability_rate"] == 1.0
    assert prior_shadow["reference_zero_records"] == 1
    assert prior_shadow["feasible_records_with_variation"] == 1
    prior_alignment = prior_shadow["target_alignment"]["closed_loop_value"]
    assert prior_alignment["candidate_pairs"] == 2
    assert prior_alignment["selection_records"] == 1
    assert prior_alignment["preference_correlation_all_candidates"] == pytest.approx(
        -1.0
    )
    assert prior_alignment["mean_selected_preference_minus_top1"] == 0.0
    assert prior_alignment["selected_worse_than_top1_rate"] == 0.0
    jerk_shadow = report["shadow_dp_prior_jerk_excess"]
    assert jerk_shadow["record_availability_rate"] == 1.0
    assert jerk_shadow["reference_zero_records"] == 1
    assert jerk_shadow["feasible_records_with_variation"] == 1
    assert jerk_shadow["mean_shadow_latency_ms"] == pytest.approx(0.3)
    jerk_alignment = jerk_shadow["target_alignment"]["closed_loop_value"]
    assert jerk_alignment["candidate_pairs"] == 2
    assert jerk_alignment["preference_correlation_all_candidates"] == pytest.approx(
        -1.0
    )
    jerk_target_alignment = jerk_shadow["target_alignment"]["closed_loop_jerk"]
    assert jerk_target_alignment["candidate_pairs"] == 2
    assert jerk_target_alignment[
        "preference_correlation_all_candidates"
    ] == pytest.approx(1.0)
    acceleration_shadow = report["shadow_dp_prior_acceleration_excess"]
    assert acceleration_shadow["record_availability_rate"] == 1.0
    assert acceleration_shadow["reference_zero_records"] == 1
    assert acceleration_shadow["feasible_records_with_variation"] == 1
    closed_loop = report["alignment"]["closed_loop_value"]
    assert closed_loop["base"]["oracle_match_rate"] == 0.0
    assert closed_loop["plus_planned_red_light"]["oracle_match_rate"] == 1.0
    assert closed_loop["plus_lateral_acceleration_proxy"]["oracle_match_rate"] == 1.0
    red_light = report["alignment"]["closed_loop_red_light_violation"]
    assert red_light["base"]["mean_selected_value"] == 1.0
    assert red_light["plus_planned_red_light"]["mean_selected_value"] == 0.0
    lateral = report["alignment"]["closed_loop_lateral_acceleration"]
    assert lateral["base"]["mean_selected_value"] == 2.0
    assert lateral["plus_lateral_acceleration_proxy"]["mean_selected_value"] == 0.1


def test_atom_coverage_report_keeps_all_infeasible_fallback_separate(
    tmp_path: Path,
) -> None:
    log_path = _write_selection_log(
        tmp_path,
        [
            _record(
                scores=[0.1, 0.2],
                feasible=[True, True],
                selected_index=0,
                used_fallback=False,
                reward_total=[1.0, 0.0],
                red_light_cost=[0.0, 0.0],
                outcome_value=[1.0, 0.0],
                red_light_violation=[False, False],
                lateral_acceleration=[0.2, 0.3],
            ),
            _record(
                scores=[0.5, 0.1],
                feasible=[False, False],
                selected_index=1,
                used_fallback=True,
                reward_total=[0.0, 1.0],
                red_light_cost=[0.0, 0.0],
                outcome_value=[0.0, 1.0],
                red_light_violation=[False, False],
                lateral_acceleration=[0.3, 0.1],
            ),
        ],
    )

    report = compute_atom_coverage_report([log_path], mode_filter={"static"})

    assert report["summary"]["fallback_rate"] == 0.5
    shadow = report["shadow_red_stopping_margin"]
    assert shadow["record_availability_rate"] == 1.0
    assert shadow["feasible_records_with_variation"] == 1
    assert shadow["feasible_candidates_nonzero"] == 1
    assert shadow["fallback_records_with_variation"] == 1
    prior_shadow = report["shadow_dp_prior_deviation"]
    assert prior_shadow["selected_top1_rate"] == 0.5
    assert prior_shadow["mean_selected_cost"] == pytest.approx(0.5)
    assert prior_shadow["fallback_records_with_variation"] == 1
    assert (
        report["consistency_checks"]["fallback_flag_matches_all_infeasible_rate"]
        == 1.0
    )
    fallback_rows = report["scenario_breakdown"]["by_used_fallback"]
    counts = {row["value"]: row["record_count"] for row in fallback_rows}
    assert counts == {"False": 1, "True": 1}
    fallback_modes = report["scenario_breakdown"]["by_fallback_mode"]
    assert fallback_modes[0]["value"] == "uniform"
    assert fallback_modes[0]["record_count"] == 2
    assert fallback_modes[0]["fallback_rate"] == 0.5
    assert fallback_modes[0]["feasible_any_rate"] == 0.5
    assert fallback_modes[0]["selected_red_light_violation_rate"] == 0.0
    assert fallback_modes[0]["mean_selected_lateral_acceleration"] == pytest.approx(
        0.15
    )


def _write_selection_log(tmp_path: Path, records: list[dict]) -> Path:
    log_path = (
        tmp_path
        / "camp_dp_formal_v7_robust_dceeefd"
        / "sample59_86"
        / "seed_12"
        / "npc_4"
        / "spawn_0p3"
        / "tl_on"
        / "static"
        / "camp_selection_log.json"
    )
    log_path.parent.mkdir(parents=True)
    log_path.write_text(json.dumps(records), encoding="utf-8")
    summary_path = log_path.with_name("camp_validation_summary.json")
    summary_path.write_text(
        json.dumps({"red_light_exposure_steps": 1, "fallback_rate": 0.5}),
        encoding="utf-8",
    )
    return log_path


def _record(
    *,
    scores: list[float],
    feasible: list[bool],
    selected_index: int,
    used_fallback: bool,
    camp_fallback_mode: str = "uniform",
    reward_total: list[float],
    red_light_cost: list[float],
    outcome_value: list[float],
    red_light_violation: list[bool],
    lateral_acceleration: list[float],
    mean_jerk: list[float] | None = None,
    red_stopping_margin: list[float] | None = None,
    dp_prior_deviation: list[float] | None = None,
    dp_prior_jerk_excess: list[float] | None = None,
    dp_prior_acceleration_excess: list[float] | None = None,
) -> dict:
    candidate_count = len(scores)
    atoms = [[float(idx + 1)] * 10 for idx in range(candidate_count)]
    record = {
        "atoms": atoms,
        "normalized_atoms": atoms,
        "scores": scores,
        "weights": [0.1] * 10,
        "feasible_mask": feasible,
        "selected_index": selected_index,
        "used_fallback": used_fallback,
        "camp_fallback_mode": camp_fallback_mode,
        "dp_candidate_rewards": [
            {"total": reward_total[idx], "red_light": red_light_cost[idx]}
            for idx in range(candidate_count)
        ],
        "candidate_closed_loop_outcomes": [
            {
                "value": outcome_value[idx],
                "red_light_violation": red_light_violation[idx],
                "mean_jerk_mps3": (
                    mean_jerk[idx] if mean_jerk is not None else float(idx)
                ),
                "mean_lateral_acceleration_mps2": lateral_acceleration[idx],
            }
            for idx in range(candidate_count)
        ],
    }
    record["candidate_red_stopping_margin_cost"] = (
        red_stopping_margin
        if red_stopping_margin is not None
        else [float(idx) for idx in range(candidate_count)]
    )
    record["candidate_dp_prior_deviation_cost"] = (
        dp_prior_deviation
        if dp_prior_deviation is not None
        else [float(idx) for idx in range(candidate_count)]
    )
    record["candidate_dp_prior_jerk_excess_cost"] = (
        dp_prior_jerk_excess
        if dp_prior_jerk_excess is not None
        else [float(idx) for idx in range(candidate_count)]
    )
    record["candidate_dp_prior_acceleration_excess_cost"] = (
        dp_prior_acceleration_excess
        if dp_prior_acceleration_excess is not None
        else [float(idx) for idx in range(candidate_count)]
    )
    record["red_route_point_count"] = 3
    record["latency_ms_shadow_red_stopping_margin"] = 0.2
    record["latency_ms_shadow_dp_prior_deviation"] = 0.1
    record["latency_ms_shadow_dp_prior_comfort_excess"] = 0.3
    return record
