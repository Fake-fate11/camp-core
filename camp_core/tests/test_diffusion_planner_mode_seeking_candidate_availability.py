from __future__ import annotations

import json

import pytest

from scripts.integrations.analyze_diffusion_planner_mode_seeking_candidate_availability import (
    GateThresholds,
    analyze,
    render_markdown,
)


def _prefix(end_x: float, end_y: float) -> list[list[float]]:
    return [[end_x * step / 4.0, end_y * step / 4.0, 0.0] for step in range(5)]


def _contract(
    *,
    guidance_enabled: bool,
    changes_diffusion_planner_weights: bool = False,
    changes_camp_score: bool = False,
) -> dict[str, object]:
    return {
        "schema_version": "dp_candidate_generation_contract_v1",
        "num_candidates": 4,
        "guidance_enabled": guidance_enabled,
        "guidance_policy": (
            "preserve_official_dp_guidance_for_candidate_generation"
            if guidance_enabled
            else "disabled_for_camp_candidate_generation"
        ),
        "changes_diffusion_planner_weights": changes_diffusion_planner_weights,
        "changes_camp_score": changes_camp_score,
        "noise_strategy": "iid",
        "guidance": {
            "enabled": guidance_enabled,
            "policy": (
                "preserve_official_dp_guidance_for_candidate_generation"
                if guidance_enabled
                else "disabled_for_camp_candidate_generation"
            ),
        },
    }


def _record(
    *,
    guidance_enabled: bool,
    prefixes: list[list[list[float]]],
    selected_index: int = 1,
    latency_ms: float = 80.0,
    changes_diffusion_planner_weights: bool = False,
    changes_camp_score: bool = False,
) -> dict[str, object]:
    return {
        "num_candidates": 4,
        "selected_index": selected_index,
        "feasible_mask": [True, True, True, True],
        "candidate_generation_contract": _contract(
            guidance_enabled=guidance_enabled,
            changes_diffusion_planner_weights=changes_diffusion_planner_weights,
            changes_camp_score=changes_camp_score,
        ),
        "candidate_perfect_tracker_postprocessed_reference_prefix": prefixes,
        "candidate_route_progress": [10.0, 10.0, 9.95, 9.96],
        "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 3.95, 3.96],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [1.0, 1.0, 1.02, 0.9],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
            0.5,
            0.5,
            0.52,
            0.4,
        ],
        "latency_ms_including_candidate_generation": latency_ms,
    }


def _write_run(tmp_path, records: list[dict[str, object]]):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "camp_selection_log.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    summary = {
        "benchmark": {
            "route": "/maps/nishishinjuku_lane_change.pkl",
            "seed": 3,
            "max_npcs": 8,
        }
    }
    (tmp_path / "camp_validation_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    return path


def test_mode_seeking_candidate_availability_passes_predeclared_gate(tmp_path) -> None:
    baseline_prefixes = [
        _prefix(10.0, 0.0),
        _prefix(10.02, 0.01),
        _prefix(9.99, -0.01),
        _prefix(10.01, 0.02),
    ]
    candidate_prefixes = [
        _prefix(10.0, 0.0),
        _prefix(10.0, 0.0),
        _prefix(9.95, 0.80),
        _prefix(9.96, -0.75),
    ]
    baseline = _write_run(
        tmp_path / "baseline",
        [_record(guidance_enabled=False, prefixes=baseline_prefixes)],
    )
    candidate = _write_run(
        tmp_path / "candidate",
        [_record(guidance_enabled=True, prefixes=candidate_prefixes)],
    )

    report = analyze(
        baseline_paths=[baseline],
        candidate_paths=[candidate],
        thresholds=GateThresholds(latency_p95_limit_ms=100.0),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == "mode_seeking_candidate_availability_passed"
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["gates"]["candidate0_preserved"] is True
    assert decision["gates"]["fixed_dp_weights"] is True
    assert decision["gates"]["camp_score_unchanged"] is True
    assert decision["gates"]["non_top1_dense_lane_change_support_pass"] is True
    assert report["dense_lane_change_support"]["support_rate"] == pytest.approx(1.0)
    assert report["spatial_diversity"]["candidate"]["mode_count"]["mean"] >= 2.0
    assert report["spatial_diversity"]["gain"]["endpoint_pairwise_mean_m"] >= 0.25

    markdown = render_markdown(report)
    assert "Mode-Seeking Candidate Availability Diagnostic" in markdown
    assert "not classical Benders decomposition" in markdown


def test_mode_seeking_candidate_availability_rejects_candidate0_drift(tmp_path) -> None:
    baseline_prefixes = [
        _prefix(10.0, 0.0),
        _prefix(10.02, 0.01),
        _prefix(9.99, -0.01),
        _prefix(10.01, 0.02),
    ]
    candidate_prefixes = [
        _prefix(10.1, 0.0),
        _prefix(10.0, 0.0),
        _prefix(9.95, 0.80),
        _prefix(9.96, -0.75),
    ]
    baseline = _write_run(
        tmp_path / "baseline",
        [_record(guidance_enabled=False, prefixes=baseline_prefixes)],
    )
    candidate = _write_run(
        tmp_path / "candidate",
        [_record(guidance_enabled=True, prefixes=candidate_prefixes)],
    )

    report = analyze(baseline_paths=[baseline], candidate_paths=[candidate])

    assert (
        report["final_decision"]["status"]
        == "mode_seeking_candidate_availability_rejected"
    )
    assert report["final_decision"]["gates"]["candidate0_preserved"] is False
    assert report["candidate0_preservation"]["max"] > 1e-6


def test_mode_seeking_candidate_availability_requires_guided_candidate_log(
    tmp_path,
) -> None:
    prefixes = [
        _prefix(10.0, 0.0),
        _prefix(10.02, 0.01),
        _prefix(9.99, -0.01),
        _prefix(10.01, 0.02),
    ]
    baseline = _write_run(
        tmp_path / "baseline",
        [_record(guidance_enabled=False, prefixes=prefixes)],
    )
    candidate = _write_run(
        tmp_path / "candidate",
        [_record(guidance_enabled=False, prefixes=prefixes)],
    )

    with pytest.raises(ValueError, match="guidance_enabled=False; expected True"):
        analyze(baseline_paths=[baseline], candidate_paths=[candidate])


def test_mode_seeking_candidate_availability_rejects_contract_mutation(
    tmp_path,
) -> None:
    baseline_prefixes = [
        _prefix(10.0, 0.0),
        _prefix(10.02, 0.01),
        _prefix(9.99, -0.01),
        _prefix(10.01, 0.02),
    ]
    candidate_prefixes = [
        _prefix(10.0, 0.0),
        _prefix(10.0, 0.0),
        _prefix(9.95, 0.80),
        _prefix(9.96, -0.75),
    ]
    baseline = _write_run(
        tmp_path / "baseline",
        [_record(guidance_enabled=False, prefixes=baseline_prefixes)],
    )
    candidate = _write_run(
        tmp_path / "candidate",
        [
            _record(
                guidance_enabled=True,
                prefixes=candidate_prefixes,
                changes_diffusion_planner_weights=True,
                changes_camp_score=True,
            )
        ],
    )

    report = analyze(baseline_paths=[baseline], candidate_paths=[candidate])

    assert (
        report["final_decision"]["status"]
        == "mode_seeking_candidate_availability_rejected"
    )
    assert report["final_decision"]["gates"]["fixed_dp_weights"] is False
    assert report["final_decision"]["gates"]["camp_score_unchanged"] is False
