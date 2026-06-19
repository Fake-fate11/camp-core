from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_descriptor_selector_screen import (
    analyze_records,
    render_markdown,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (
    _load_record,
)


ATOM_NAMES = [
    "rms_acceleration",
    "jerk_full",
    "planned_lateral_acceleration_cost",
    "dp_prior_jerk_excess_cost",
    "planned_red_light_cost",
    "red_stopping_margin_cost",
    "jerk_early",
]


def _outcome(
    *,
    progress: float = 10.0,
    collision: bool = False,
    near_miss: bool = False,
    lane_violation: bool = False,
    red_light_violation: bool = False,
    jerk: float = 0.5,
    lateral: float = 0.2,
) -> dict[str, object]:
    return {
        "progress_m": progress,
        "collision": collision,
        "near_miss": near_miss,
        "lane_violation": lane_violation,
        "red_light_violation": red_light_violation,
        "mean_jerk_mps3": jerk,
        "mean_lateral_acceleration_mps2": lateral,
    }


def _record(
    *,
    include_schema: bool = True,
    formal_seed: bool = False,
    candidate_outcome: dict[str, object] | None = None,
) -> dict[str, object]:
    selected_atoms = [0.5, 0.5, 0.5, 0.5, 0.0, 0.0, 0.5]
    candidate_atoms = [0.1, 0.2, 0.2, 0.1, 0.0, 0.0, 0.1]
    raw: dict[str, object] = {
        "num_candidates": 3,
        "selected_index": 1,
        "feasible_mask": [True, True, True],
        "candidate_route_progress": [10.0, 10.0, 9.99],
        "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 4.0],
        "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [1.0, 1.0, 0.6],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
            0.5,
            0.5,
            0.3,
        ],
        "selection_scores": [10.0, 0.0, 0.1],
        "candidate_closed_loop_outcomes": [
            _outcome(collision=True, jerk=1.0, lateral=0.5),
            _outcome(near_miss=True, jerk=1.0, lateral=0.4),
            candidate_outcome or _outcome(progress=9.99, jerk=0.5, lateral=0.2),
        ],
    }
    if include_schema:
        raw.update(
            {
                "selection_normalized_atoms": [
                    [1.0 for _ in ATOM_NAMES],
                    selected_atoms,
                    candidate_atoms,
                ],
                "selection_weights": [1.0 for _ in ATOM_NAMES],
                "atom_names": ATOM_NAMES,
            }
        )
    record = _load_record(raw, "unit descriptor selector record")
    record["context"] = {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "route": "nishishinjuku_lane_change",
        "seed": 11 if formal_seed else 1,
        "formal_seed": formal_seed,
        "npc_count": 8,
        "traffic_light": "off",
        "mode": "static",
    }
    return record


def test_descriptor_selector_screen_can_pass_clean_descriptor_candidate() -> None:
    records = [_record() for _ in range(20)]

    report = analyze_records(records, bootstrap_resamples=200, seed=7)

    assert report["final_decision"]["status"] == (
        "descriptor_only_offline_screen_passed"
    )
    strict = next(
        screen
        for screen in report["screens"]
        if screen["name"] == "strict_comfort_atom_guard"
    )
    assert strict["gate"]["pass"] is True
    assert strict["records"]["changed"] == 20
    assert strict["slices"]["dense_lane_change"]["changed_rate"] == pytest.approx(1.0)
    assert (
        strict["slices"]["dense_lane_change"]["safety_cost_delta_vs_current"][
            "ci95_high"
        ]
        < 0.0
    )
    assert strict["slices"]["dense_lane_change"]["hard_nonworse_vs_current"] == pytest.approx(
        1.0
    )

    markdown = render_markdown(report)
    assert "Descriptor-Only Offline Selector Screen" in markdown
    assert "not classical Benders decomposition" in markdown


def test_descriptor_selector_screen_fails_closed_without_required_schema() -> None:
    records = [_record(include_schema=False) for _ in range(4)]

    report = analyze_records(records, bootstrap_resamples=50, seed=3)

    assert report["final_decision"]["status"] == (
        "descriptor_only_offline_screen_rejected"
    )
    for screen in report["screens"]:
        assert screen["records"]["changed"] == 0
        assert screen["stage_counts"] == {"missing_score_schema": 4}


def test_descriptor_selector_screen_records_posterior_regression_without_using_it() -> None:
    records = [
        _record(
            candidate_outcome=_outcome(
                progress=9.99,
                red_light_violation=True,
                jerk=0.5,
                lateral=0.2,
            )
        )
        for _ in range(4)
    ]

    report = analyze_records(records, bootstrap_resamples=50, seed=5)

    strict = next(
        screen
        for screen in report["screens"]
        if screen["name"] == "strict_comfort_atom_guard"
    )
    assert strict["records"]["changed"] == 4
    assert strict["gate"]["pass"] is False
    assert "dense_safety_not_proven" in strict["gate"]["failures"]
    assert "dense_hard_regression" in strict["gate"]["failures"]


def test_descriptor_selector_screen_rejects_formal_seed_records() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records([_record(formal_seed=True)], fail_on_formal_seeds=True)
