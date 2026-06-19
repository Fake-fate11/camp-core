from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_descriptor_audit import (
    analyze_records,
    render_markdown,
)
from scripts.integrations.analyze_diffusion_planner_dense_lane_change_score_calibration import (
    _load_record,
)


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
    clean: bool,
    formal_seed: bool = False,
) -> dict[str, object]:
    if clean:
        selected_norm = [0.2, 0.2]
        candidate_norm = [0.0, 0.0]
        selected_outcome = _outcome(near_miss=True, jerk=1.0, lateral=0.4)
        candidate_outcome = _outcome(progress=9.99, jerk=0.5, lateral=0.2)
    else:
        selected_norm = [0.1, 0.1]
        candidate_norm = [0.5, 0.3]
        selected_outcome = _outcome(collision=True, jerk=0.5, lateral=0.2)
        candidate_outcome = _outcome(progress=9.99, jerk=1.0, lateral=0.4)
    top1_norm = [1.0, 1.0]
    record = _load_record(
        {
            "num_candidates": 3,
            "selected_index": 1,
            "feasible_mask": [True, True, True],
            "candidate_route_progress": [10.0, 10.0, 9.99],
            "candidate_perfect_tracker_target_speed_mps": [4.0, 4.0, 4.0],
            "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.4],
            "candidate_perfect_tracker_jerk_magnitude_mps3": [0.8, 0.8, 0.8],
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
                0.4,
                0.4,
                0.4,
            ],
            "selection_normalized_atoms": [top1_norm, selected_norm, candidate_norm],
            "selection_weights": [1.0, 1.0],
            "selection_scores": [
                sum(top1_norm),
                sum(selected_norm),
                sum(candidate_norm),
            ],
            "atom_names": ["dp_prior_jerk_excess_cost", "jerk_early"],
            "candidate_closed_loop_outcomes": [
                _outcome(collision=True),
                selected_outcome,
                candidate_outcome,
            ],
        },
        "unit descriptor audit record",
    )
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


def test_candidate_descriptor_audit_reports_clean_vs_comfort_regressing_separation() -> None:
    records = [_record(clean=True) for _ in range(4)]
    records.extend(_record(clean=False) for _ in range(4))

    report = analyze_records(records)

    assert report["final_decision"]["status"] == "descriptor_audit_complete"
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["records"]["clean_outcome_support_rows"] == 4
    assert report["records"]["guarded_comfort_regressing_rows"] >= 4

    groups = report["groups"]
    assert groups["clean_outcome_support"]["records"] == 4
    assert (
        groups["strict_progress005_speed010_comfort_nonworse_comfort_regressing"][
            "records"
        ]
        == 4
    )

    top_descriptors = report["separation"]["top_descriptors"]
    assert top_descriptors[0]["descriptor"] in {
        "protective_margin",
        "atom_margin:dp_prior_jerk_excess_cost",
        "atom_margin:jerk_early",
        "atom_norm_delta:dp_prior_jerk_excess_cost",
        "atom_norm_delta:jerk_early",
    }
    separator = {
        row["descriptor"]: row for row in report["separation"]["all_descriptors"]
    }
    assert separator["protective_margin"]["clean_mean"] == pytest.approx(-0.4)
    assert separator["protective_margin"][
        "guarded_comfort_regressing_mean"
    ] == pytest.approx(0.6)

    markdown = render_markdown(report)
    assert "Candidate Descriptor Separation Audit" in markdown
    assert "not classical Benders decomposition" in markdown


def test_candidate_descriptor_audit_rejects_formal_seed_records() -> None:
    record = _record(clean=True, formal_seed=True)

    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records([record], fail_on_formal_seeds=True)
