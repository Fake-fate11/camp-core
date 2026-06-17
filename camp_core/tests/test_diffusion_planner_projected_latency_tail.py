from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_projected_latency_tail import (
    analyze,
    render_markdown,
)


def test_projected_latency_tail_attributes_remaining_over_budget_runs(tmp_path) -> None:
    root = tmp_path / "grid"
    over = root / "route_a" / "seed_1" / "npc_4" / "tl_off" / "static"
    under = root / "route_b" / "seed_2" / "npc_0" / "tl_on" / "static"
    over.mkdir(parents=True)
    under.mkdir(parents=True)
    (over / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(total=110.0, clearance=10.0, candidate=60.0),
                _record(total=120.0, clearance=20.0, candidate=70.0),
            ]
        ),
        encoding="utf-8",
    )
    (under / "camp_selection_log.json").write_text(
        json.dumps(
            [
                _record(total=95.0, clearance=2.0, candidate=40.0),
                _record(total=96.0, clearance=3.0, candidate=42.0),
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
    assert report["records"]["usable"] == 4

    constant = report["projection_modes"]["constant_new_p95"]
    assert constant["runs_over_budget"] == 1
    assert constant["tail_rows"] == 2
    assert constant["over_budget_run_shortfall_ms"]["p95"] == pytest.approx(1.0)
    assert constant["over_budget_runs"][0]["projected_total_p95_ms"] == pytest.approx(
        101.0
    )
    assert constant["top_tail_primary_components_by_mean_ms"][0]["field"] == (
        "latency_ms_candidate_generation"
    )
    assert constant["top_tail_primary_components_by_mean_ms"][0][
        "mean"
    ] == pytest.approx(65.0)
    assert constant["tail_latency_ms"][
        "projected_latency_ms_including_candidate_generation"
    ]["p95"] == pytest.approx(101.0)

    markdown = render_markdown(report)
    assert "DP-CAMP Projected Latency Tail Attribution" in markdown
    assert "Projection only" in markdown
    assert "not replay-measured latency" in markdown
    assert "Latency components are not CAMP risk atoms" in markdown


def test_projected_latency_tail_rejects_missing_usable_records(tmp_path) -> None:
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


def _record(*, total: float, clearance: float, candidate: float) -> dict:
    return {
        "selection_step": 0,
        "selected_index": 0,
        "used_fallback": False,
        "latency_ms_including_candidate_generation": total,
        "latency_ms_shadow_obstacle_clearance": clearance,
        "latency_ms_candidate_generation": candidate,
        "latency_ms_reward_scoring": 20.0,
        "latency_ms_camp_selection": 10.0,
        "latency_ms_context_and_obstacles": 5.0,
        "latency_ms_shadow_perfect_tracker_open_loop": 2.0,
        "latency_ms_shadow_perfect_tracker_command": 1.0,
        "latency_ms_shadow_lateral_comfort": 1.0,
        "latency_ms_shadow_dp_prior_deviation": 1.0,
        "latency_ms_shadow_dp_prior_comfort_excess": 1.0,
        "latency_ms_outcome_collection": 0.0,
        "latency_ms_red_stopping_margin_atom": 0.5,
        "latency_ms_underprogress_relaxation": 0.0,
        "latency_ms_splice_shadow_rule": 0.0,
        "latency_ms_traffic_light_hybrid_postselection": 0.0,
        "latency_ms_perfect_tracker_command_postselection": 0.0,
        "latency_ms_camp_atom_computation": 3.0,
        "latency_ms_camp_feasibility": 2.0,
        "latency_ms_camp_collision_checks": 4.0,
        "latency_ms_camp_scoring": 1.0,
        "latency_ms_reward_batch_compute": 15.0,
    }
