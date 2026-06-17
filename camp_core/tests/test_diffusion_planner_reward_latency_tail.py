from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_reward_latency_tail import (
    analyze,
    render_markdown,
)


def test_reward_latency_tail_attributes_breakdown_and_savings(tmp_path) -> None:
    root = tmp_path / "grid"
    over = root / "route_a" / "seed_1" / "npc_4" / "tl_off" / "static"
    under = root / "route_b" / "seed_2" / "npc_0" / "tl_on" / "static"
    over.mkdir(parents=True)
    under.mkdir(parents=True)
    (over / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(
                    total=120.0,
                    clearance=20.0,
                    reward=40.0,
                    batch=20.0,
                    postprocess=10.0,
                ),
                _record(
                    total=130.0,
                    clearance=20.0,
                    reward=50.0,
                    batch=25.0,
                    postprocess=10.0,
                ),
            ]
        ),
        encoding="utf-8",
    )
    (under / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(
                    total=90.0,
                    clearance=2.0,
                    reward=20.0,
                    batch=8.0,
                    postprocess=4.0,
                ),
                _record(
                    total=95.0,
                    clearance=3.0,
                    reward=20.0,
                    batch=8.0,
                    postprocess=4.0,
                ),
            ]
        ),
        encoding="utf-8",
    )

    report = analyze(
        [root],
        label="unit",
        reference_old_clearance_p95_ms=20.0,
        reference_new_clearance_p95_ms=1.0,
        reference_source="unit-smoke",
    )

    assert report["analysis"]["projection_not_replay_measurement"] is True
    assert report["analysis"]["online_selector_change"] is False
    assert report["records"]["logs"] == 2

    mode = report["projection_modes"]["constant_new_p95"]
    assert mode["runs_over_budget"] == 1
    assert mode["tail_rows"] == 1
    assert mode["tail_reward_scoring_ms"]["mean"] == pytest.approx(50.0)
    assert mode["tail_reward_breakdown_sum_ms"]["mean"] == pytest.approx(35.0)
    assert mode["tail_reward_unattributed_residual_ms"]["mean"] == pytest.approx(
        15.0
    )
    assert mode["top_reward_components_by_tail_mean_ms"][0]["field"] == (
        "latency_ms_reward_batch_compute"
    )

    savings = mode["reward_component_savings"]
    assert savings["latency_ms_reward_batch_compute_25pct_saving"][
        "runs_over_budget"
    ] == 1
    assert savings["latency_ms_reward_batch_compute_50pct_saving"][
        "runs_over_budget"
    ] == 0
    assert savings["all_instrumented_reward_breakdown_50pct_saving"][
        "runs_over_budget"
    ] == 0

    markdown = render_markdown(report)
    assert "DP-CAMP Reward Latency Tail Attribution" in markdown
    assert "reward latency savings are hypothetical" in markdown
    assert "does not change candidates" in markdown


def test_reward_latency_tail_rejects_missing_usable_records(tmp_path) -> None:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(
        json.dumps(
            [
                {
                    "latency_ms_including_candidate_generation": 100.0,
                    "latency_ms_shadow_obstacle_clearance": None,
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="No records had finite"):
        analyze(
            [log_path],
            reference_old_clearance_p95_ms=20.0,
            reference_new_clearance_p95_ms=1.0,
        )


def _record(
    *,
    total: float,
    clearance: float,
    reward: float,
    batch: float,
    postprocess: float,
) -> dict:
    return {
        "selection_step": 0,
        "latency_ms_including_candidate_generation": total,
        "latency_ms_shadow_obstacle_clearance": clearance,
        "latency_ms_reward_scoring": reward,
        "latency_ms_reward_batch_compute": batch,
        "latency_ms_reward_postprocess": postprocess,
        "latency_ms_reward_tensor_setup": 0.0,
        "latency_ms_reward_candidate_tensor_transfer": 0.0,
        "latency_ms_reward_npz_dump": 0.0,
        "latency_ms_reward_full_horizon_red_light": 0.0,
        "latency_ms_reward_red_route_points": 0.0,
        "latency_ms_reward_feasibility": 0.0,
        "latency_ms_reward_field_extraction": 0.0,
        "latency_ms_reward_step_reach_guard": 0.0,
        "latency_ms_reward_route_progress": 0.0,
        "latency_ms_reward_route_progress_guard": 0.0,
        "latency_ms_reward_lexicographic_filter": 0.0,
        "latency_ms_candidate_generation": 60.0,
        "latency_ms_camp_selection": 5.0,
        "latency_ms_camp_atom_computation": 3.0,
        "latency_ms_context_and_obstacles": 1.0,
    }
