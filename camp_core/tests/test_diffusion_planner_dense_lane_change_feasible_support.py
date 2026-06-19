from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_dense_lane_change_feasible_support import (
    _load_record,
    analyze_run_records,
    render_markdown,
)


def _record(
    *,
    selected: int,
    feasible: list[bool],
    progress: list[float],
    speed: list[float],
    dp_prior: list[float],
    jerk: list[float],
    lateral: list[float],
    scores: list[float],
) -> dict[str, object]:
    return _load_record(
        {
            "num_candidates": len(feasible),
            "selected_index": selected,
            "feasible_mask": feasible,
            "candidate_route_progress": progress,
            "candidate_perfect_tracker_target_speed_mps": speed,
            "candidate_dp_prior_deviation_cost": dp_prior,
            "candidate_perfect_tracker_jerk_magnitude_mps3": jerk,
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": lateral,
            "selection_scores": scores,
        },
        "unit record",
    )


def _run_record(
    *,
    route_name: str,
    max_npcs: int,
    safety_delta: float,
    lane_delta: float,
    records: list[dict[str, object]],
    seed: int = 1,
    formal_seed: bool | None = None,
) -> dict[str, object]:
    is_formal_seed = seed in (11, 12, 13) if formal_seed is None else formal_seed
    return {
        "run": {
            "route_name": route_name,
            "run_key": route_name,
            "max_npcs": max_npcs,
            "seed": seed,
        },
        "context": {"seed": seed, "formal_seed": is_formal_seed},
        "baseline": {"variant": "top1"},
        "delta": {
            "safety_cost_v1": safety_delta,
            "lane_violation_rate": lane_delta,
            "route_completion_rate": 0.0,
            "static_p95_selection_latency_ms": 102.0,
        },
        "log_path": f"/fake/{route_name}/camp_selection_log.json",
        "records": records,
    }


def _rule(report: dict[str, object], name: str) -> dict[str, object]:
    rules = {item["name"]: item for item in report["rules"]}
    return rules[name]


def test_dense_lane_change_support_finds_non_top1_alternative() -> None:
    dense_records = [
        _record(
            selected=1,
            feasible=[True, True, True],
            progress=[10.0, 10.0, 9.97],
            speed=[4.0, 4.0, 3.95],
            dp_prior=[0.2, 0.9, 0.4],
            jerk=[0.8, 0.9, 0.8],
            lateral=[0.4, 0.5, 0.5],
            scores=[0.0, 0.1, 0.2],
        ),
        _record(
            selected=1,
            feasible=[True, True, True],
            progress=[10.0, 10.0, 8.5],
            speed=[4.0, 4.0, 3.0],
            dp_prior=[0.1, 1.0, 0.2],
            jerk=[0.7, 0.8, 0.7],
            lateral=[0.3, 0.4, 0.3],
            scores=[0.0, 0.1, 0.2],
        ),
        _record(
            selected=0,
            feasible=[True, True, True],
            progress=[10.0, 9.9, 9.8],
            speed=[4.0, 4.0, 4.0],
            dp_prior=[0.1, 0.3, 0.4],
            jerk=[0.7, 0.7, 0.7],
            lateral=[0.3, 0.3, 0.3],
            scores=[0.0, 0.1, 0.2],
        ),
    ]
    normal_records = [
        _record(
            selected=1,
            feasible=[True, True, True],
            progress=[8.0, 8.0, 7.99],
            speed=[3.0, 3.0, 3.0],
            dp_prior=[0.2, 0.8, 0.3],
            jerk=[0.5, 0.6, 0.5],
            lateral=[0.2, 0.2, 0.2],
            scores=[0.0, 0.1, 0.2],
        )
    ]
    report = analyze_run_records(
        [
            _run_record(
                route_name="nishishinjuku_lane_change",
                max_npcs=8,
                safety_delta=0.2,
                lane_delta=0.01,
                records=dense_records,
            ),
            _run_record(
                route_name="sample_map_normal",
                max_npcs=4,
                safety_delta=-0.1,
                lane_delta=0.0,
                records=normal_records,
            ),
        ],
        label="unit",
    )

    assert report["records"]["static_runs"] == 2
    assert report["records"]["dense_lane_change_runs"] == 1
    assert report["records"]["bad_dense_lane_change_runs"] == 1
    assert report["dense_lane_change_baseline"]["target_records"] == 2

    non_top1_rule = _rule(
        report,
        "non_top1_progress005_speed010_comfort_nonworse",
    )
    bad_non_top1 = non_top1_rule["bad_dense_lane_change"]
    assert bad_non_top1["support_rate"] == pytest.approx(0.5)
    assert bad_non_top1["chosen_non_top1_rate"] == pytest.approx(1.0)
    assert bad_non_top1["mean_dp_prior_gain"] == pytest.approx(0.5)

    top1_rule = _rule(report, "top1_progress005_speed010_comfort_nonworse")
    assert top1_rule["bad_dense_lane_change"]["support_rate"] == pytest.approx(1.0)
    assert top1_rule["bad_dense_lane_change"]["chosen_top1_rate"] == pytest.approx(1.0)

    decision = report["final_decision"]
    assert decision["status"] == "non_top1_candidate_support_present"
    assert (
        "non_top1_progress005_speed010_comfort_nonworse"
        in decision["passing_non_top1_rules"]
    )
    assert "top1_progress005_speed010_comfort_nonworse" in decision[
        "top1_dependent_rules"
    ]
    assert decision["online_selector_authorized"] is False
    assert decision["full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["camp_retraining_authorized"] is False

    markdown = render_markdown(report)
    assert "Dense Lane-Change Feasible-Tick Support Audit" in markdown
    assert "read-only" in markdown
    assert "not classical Benders decomposition" in markdown


def test_dense_lane_change_support_rejects_formal_seed_runs() -> None:
    record = _record(
        selected=1,
        feasible=[True, True],
        progress=[10.0, 10.0],
        speed=[4.0, 4.0],
        dp_prior=[0.0, 1.0],
        jerk=[0.5, 0.5],
        lateral=[0.2, 0.2],
        scores=[0.0, 0.1],
    )

    with pytest.raises(ValueError, match="Formal seed runs are forbidden"):
        analyze_run_records(
            [
                _run_record(
                    route_name="nishishinjuku_lane_change",
                    max_npcs=8,
                    safety_delta=0.1,
                    lane_delta=0.0,
                    records=[record],
                    seed=11,
                    formal_seed=True,
                )
            ],
            fail_on_formal_seeds=True,
        )


def test_dense_lane_change_support_reports_formal_seeds_without_flag() -> None:
    record = _record(
        selected=1,
        feasible=[True, True],
        progress=[10.0, 10.0],
        speed=[4.0, 4.0],
        dp_prior=[0.0, 1.0],
        jerk=[0.5, 0.5],
        lateral=[0.2, 0.2],
        scores=[0.0, 0.1],
    )

    report = analyze_run_records(
        [
            _run_record(
                route_name="nishishinjuku_lane_change",
                max_npcs=8,
                safety_delta=0.1,
                lane_delta=0.0,
                records=[record],
                seed=11,
            )
        ],
    )

    assert report["analysis"]["formal_seed_policy"] == "reported_only"
    assert report["records"]["formal_seed_runs"] == 1
    assert report["records"]["formal_seed_selection_records"] == 1


def test_dense_lane_change_record_parser_uses_step_reach_and_default_comfort() -> None:
    record = _load_record(
        {
            "num_candidates": 2,
            "selected_index": 1,
            "feasible_mask": [True, True],
            "candidate_step_reach": [9.0, 10.0],
            "candidate_dp_prior_deviation_cost": [0.1, 0.7],
            "selection_scores": [0.0, float("inf")],
        },
        "unit fallback record",
    )

    assert record["features"]["planned_progress"].tolist() == [9.0, 10.0]
    assert record["features"]["target_speed"].tolist() == [0.0, 0.0]
    assert record["features"]["tracker_jerk"].tolist() == [0.0, 0.0]
    assert record["features"]["tracker_lateral"].tolist() == [0.0, 0.0]
    assert record["features"]["selection_score"][1] == float("inf")


def test_dense_lane_change_record_parser_rejects_bad_vector_shape() -> None:
    with pytest.raises(ValueError, match="candidate_route_progress must have shape"):
        _load_record(
            {
                "num_candidates": 2,
                "selected_index": 0,
                "feasible_mask": [True, True],
                "candidate_route_progress": [1.0],
                "candidate_dp_prior_deviation_cost": [0.1, 0.2],
            },
            "bad unit record",
        )
