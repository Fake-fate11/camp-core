from __future__ import annotations

import pytest

from scripts.integrations.analyze_diffusion_planner_material_atom_schema_availability import (
    DEFAULT_REQUIRED_BUCKETS,
    _route_name_for_buckets,
    analyze_records,
    render_markdown,
)


def _context(*, seed: int = 1, buckets: list[str] | None = None) -> dict:
    return {
        "log_path": "/fake/camp_selection_log.json",
        "record_index": 0,
        "route_name": "sample_map_tl_route_59_to_86",
        "seed": seed,
        "max_npcs": 4,
        "traffic_lights": True,
        "advance_mode": "perfect",
        "scenario_buckets": buckets or ["overall", *DEFAULT_REQUIRED_BUCKETS],
    }


def _record() -> dict:
    return {
        "num_candidates": 3,
        "selected_index": 0,
        "feasible_mask": [True, False, True],
        "candidate_route_progress": [10.0, 9.0, 11.0],
        "candidate_perfect_tracker_target_speed_mps": [5.0, 4.0, 6.0],
        "candidate_perfect_tracker_jerk_magnitude_mps3": [1.0, 2.0, 1.5],
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": [
            1.0,
            2.5,
            1.5,
        ],
        "candidate_dp_prior_deviation_cost": [0.0, 1.0, 0.5],
        "candidate_horizon_union_planned_red_light_cost": [0.0, 0.7, 0.2],
        "candidate_full_horizon_planned_red_light_cost": [0.0, 1.0, 0.1],
        "candidate_red_stopping_margin_cost": [0.0, 0.5, 0.0],
        "candidate_closed_loop_outcomes": [
            {"progress_m": 10.0, "collision": False},
            {"progress_m": 9.0, "collision": True},
            {"progress_m": 11.0, "collision": False},
        ],
    }


def test_material_atom_schema_availability_ready_when_all_families_present() -> None:
    report = analyze_records([{"raw": _record(), "context": _context()}])

    assert (
        report["final_decision"]["status"]
        == "material_atom_schema_availability_ready_for_offline_weight_audit"
    )
    assert report["analysis"]["training"] is False
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["records"]["outcome_labels_present_records"] == 1
    assert report["convexity_checks"]["all_available_atoms_finite_and_nonnegative"]
    assert report["field_coverage"]["hard_feasibility_deficit"]["records_available"] == 1
    assert report["atom_summary"]["hard_feasibility_deficit"]["max"] == 1.0
    assert report["atom_summary"]["traffic_rule_exposure"]["max"] == 1.0
    assert report["final_decision"]["closed_loop_smoke_authorized"] is False

    markdown = render_markdown(report)
    assert "Material Atom Schema Availability Audit" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "classical Benders" in markdown


def test_material_atom_schema_availability_blocks_missing_family() -> None:
    record = _record()
    for key in (
        "candidate_horizon_union_planned_red_light_cost",
        "candidate_full_horizon_planned_red_light_cost",
        "candidate_red_stopping_margin_cost",
    ):
        record.pop(key)

    report = analyze_records([{"raw": record, "context": _context()}])

    assert report["final_decision"]["status"] == (
        "material_atom_schema_availability_incomplete"
    )
    assert report["final_decision"]["missing_atom_families"] == [
        "traffic_rule_exposure"
    ]
    assert report["field_coverage"]["traffic_rule_exposure"]["records_missing"] == 1


def test_material_atom_schema_availability_requires_scenario_bucket_coverage() -> None:
    report = analyze_records(
        [{"raw": _record(), "context": _context(buckets=["overall", "normal"])}]
    )

    assert report["final_decision"]["status"] == (
        "material_atom_schema_availability_bucket_incomplete"
    )
    assert "traffic_light" in report["final_decision"]["missing_required_buckets"]


def test_material_atom_schema_availability_skips_scalar_progress_field() -> None:
    record = _record()
    record["candidate_route_progress"] = [10.0]
    record["candidate_step_reach"] = [10.0, 9.5, 10.5]

    report = analyze_records([{"raw": record, "context": _context()}])

    coverage = report["field_coverage"]["support_preservation_deficit"]
    assert coverage["records_available"] == 1
    assert coverage["source_fields"] == {
        "candidate_perfect_tracker_target_speed_mps": 1,
        "candidate_step_reach": 1,
    }


def test_material_atom_schema_availability_prefers_declared_route_family() -> None:
    route = "/assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl"

    assert _route_name_for_buckets(route, "nishishinjuku_lane_change") == (
        "nishishinjuku_lane_change"
    )
    assert _route_name_for_buckets(route, "unknown") == (
        "nishishinjuku_lane_change_route_7_via_8_to_1"
    )


def test_material_atom_schema_availability_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [{"raw": _record(), "context": _context(seed=11)}],
            fail_on_formal_seeds=True,
        )


def test_material_atom_schema_availability_does_not_use_outcomes_for_atoms() -> None:
    base = _record()
    mutated = _record()
    mutated["candidate_closed_loop_outcomes"] = [
        {"progress_m": -100.0, "collision": True},
        {"progress_m": -200.0, "collision": True},
        {"progress_m": -300.0, "collision": True},
    ]

    base_report = analyze_records([{"raw": base, "context": _context()}])
    mutated_report = analyze_records([{"raw": mutated, "context": _context()}])

    assert base_report["atom_summary"] == mutated_report["atom_summary"]
    assert (
        mutated_report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    )
