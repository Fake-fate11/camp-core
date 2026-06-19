from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_mode_seeking_failure_source import (
    FailureSourceThresholds,
    analyze_record_pairs,
    render_markdown,
)


def _prefix(end_x: float, end_y: float) -> list[list[float]]:
    return [[end_x * step / 4.0, end_y * step / 4.0, 0.0] for step in range(5)]


def _contract(
    *,
    guidance_enabled: bool = True,
    candidate0_preservation_structural: bool = True,
    changes_diffusion_planner_weights: bool = False,
    changes_camp_score: bool = False,
) -> dict[str, object]:
    return {
        "schema_version": "dp_candidate_generation_contract_v1",
        "guidance_enabled": guidance_enabled,
        "candidate0_guidance_policy": "full_batch_unguided_forward",
        "candidate0_preservation_structural": candidate0_preservation_structural,
        "changes_diffusion_planner_weights": changes_diffusion_planner_weights,
        "changes_camp_score": changes_camp_score,
    }


def _record(
    *,
    prefixes: list[list[list[float]]],
    feasible: list[bool],
    reasons: list[list[str]],
    selected_index: int = 1,
    progress: list[float] | None = None,
    speed: list[float] | None = None,
    jerk: list[float] | None = None,
    lateral: list[float] | None = None,
    latency_ms: float = 80.0,
    contract: dict[str, object] | None = None,
) -> dict[str, object]:
    candidate_count = len(prefixes)
    return {
        "num_candidates": candidate_count,
        "selected_index": selected_index,
        "feasible_mask": feasible,
        "infeasibility_reasons": reasons,
        "candidate_generation_contract": contract or _contract(),
        "candidate_perfect_tracker_postprocessed_reference_prefix": prefixes,
        "candidate_route_progress": progress or [10.0] * candidate_count,
        "candidate_perfect_tracker_target_speed_mps": speed or [4.0] * candidate_count,
        "candidate_perfect_tracker_jerk_magnitude_mps3": jerk
        or [0.5] * candidate_count,
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": lateral
        or [0.4] * candidate_count,
        "latency_ms_including_candidate_generation": latency_ms,
    }


def _baseline_record() -> dict[str, object]:
    return _record(
        prefixes=[
            _prefix(10.0, 0.0),
            _prefix(10.02, 0.01),
            _prefix(9.99, -0.01),
            _prefix(10.01, 0.02),
        ],
        feasible=[True, True, True, True],
        reasons=[[], [], [], []],
        contract=_contract(guidance_enabled=False, candidate0_preservation_structural=False),
    )


def _reward_gate_candidate_record() -> dict[str, object]:
    return _record(
        prefixes=[
            _prefix(10.0, 0.0),
            _prefix(10.0, 0.0),
            _prefix(9.96, 0.85),
            _prefix(9.97, -0.80),
        ],
        feasible=[False, False, False, False],
        reasons=[
            ["dp_lane_crossing"],
            ["dp_lane_crossing"],
            ["dp_lane_crossing"],
            ["dp_lane_crossing"],
        ],
        progress=[10.0, 10.0, 9.96, 9.97],
        speed=[4.0, 4.0, 3.96, 3.97],
        jerk=[0.5, 0.5, 0.52, 0.49],
        lateral=[0.4, 0.4, 0.42, 0.39],
    )


def test_failure_source_flags_reward_gate_when_geometry_support_exists() -> None:
    report = analyze_record_pairs(
        [_baseline_record()],
        [_reward_gate_candidate_record()],
        baseline_context={"seed": 3, "formal_seed": False},
        candidate_context={"seed": 3, "formal_seed": False},
        thresholds=FailureSourceThresholds(),
        label="unit",
    )

    decision = report["final_decision"]
    aggregate = report["aggregate"]
    assert decision["status"] == "mode_seeking_failure_source_reward_gate_suspect"
    assert decision["reward_gate_suspect"] is True
    assert decision["closed_loop_smoke_authorized"] is False
    assert decision["online_selector_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert aggregate["candidate_reward_feasible_total"] == 0
    assert aggregate["combined_tracker_support_records"] == 1
    assert aggregate["gates"]["endpoint_pairwise_mean_pass"] is True
    assert aggregate["gates"]["endpoint_gain_pass"] is True

    markdown = render_markdown(report)
    assert "Failure-Source Diagnostic" in markdown
    assert "not classical Benders decomposition" in markdown


def test_failure_source_rejects_when_candidate_support_is_insufficient() -> None:
    candidate = _record(
        prefixes=[
            _prefix(10.0, 0.0),
            _prefix(10.01, 0.01),
            _prefix(9.99, -0.01),
            _prefix(10.02, 0.0),
        ],
        feasible=[False, False, False, False],
        reasons=[
            ["dp_kinematic"],
            ["dp_kinematic"],
            ["dp_kinematic"],
            ["dp_kinematic"],
        ],
        progress=[10.0, 10.0, 9.0, 8.8],
        speed=[4.0, 4.0, 3.0, 2.8],
        jerk=[0.5, 0.5, 1.2, 1.3],
        lateral=[0.4, 0.4, 2.5, 2.6],
        latency_ms=382.0,
    )

    report = analyze_record_pairs(
        [_baseline_record()],
        [candidate],
        baseline_context={"seed": 3, "formal_seed": False},
        candidate_context={"seed": 3, "formal_seed": False},
    )

    decision = report["final_decision"]
    aggregate = report["aggregate"]
    assert (
        decision["status"]
        == "mode_seeking_failure_source_candidate_support_insufficient"
    )
    assert decision["reward_gate_suspect"] is False
    assert decision["geometry_or_tracker_support_insufficient"] is True
    assert decision["latency_blocked"] is True
    assert aggregate["combined_tracker_support_records"] == 0
    assert aggregate["gates"]["endpoint_pairwise_mean_pass"] is False
    assert aggregate["gates"]["endpoint_gain_pass"] is False


def test_failure_source_requires_nonformal_fixed_contract_for_reward_gate() -> None:
    candidate = _reward_gate_candidate_record()
    candidate["candidate_generation_contract"] = _contract(
        guidance_enabled=True,
        changes_camp_score=True,
    )

    report = analyze_record_pairs(
        [_baseline_record()],
        [candidate],
        baseline_context={"seed": 11, "formal_seed": True},
        candidate_context={"seed": 11, "formal_seed": True},
    )

    decision = report["final_decision"]
    assert (
        decision["status"]
        == "mode_seeking_failure_source_candidate_support_insufficient"
    )
    assert decision["reward_gate_suspect"] is False
    assert decision["formal_seeds_absent"] is False
    assert decision["contract_ok"] is False
    assert decision["formal_seeds_authorized"] is False


def test_failure_source_rejects_bad_candidate0_shape() -> None:
    candidate = _reward_gate_candidate_record()
    candidate["candidate_perfect_tracker_postprocessed_reference_prefix"] = [
        _prefix(10.0, 0.0),
        _prefix(10.0, 0.0),
    ]

    with pytest.raises(ValueError, match="candidate prefix must have shape"):
        analyze_record_pairs([_baseline_record()], [candidate])
