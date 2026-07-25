from __future__ import annotations

import copy
import math
from pathlib import Path

import numpy as np
import pytest

from camp_core.integrations import diffusion_planner_v25_evaluation_v2 as v2_kernel
from camp_core.integrations.diffusion_planner_v25_evaluation_v2 import (
    ACCELERATION_GRID_MPS2,
    BOXCAR_KERNEL,
    CLEARANCE_GRID_M,
    CLOSING_GRID_MPS,
    DRAC_GRID_MPS2,
    JERK_GRID_MPS3,
    LATENCY_DEADLINE_GRID_MS,
    SPEED_TOLERANCE_GRID_MPS,
    TTC_GRID_S,
    clustered_paired_descriptive,
    build_evaluation_v2_result,
    continuous_sat_ttc_s,
    dynamic_pair_tick,
    evaluation_v2_contract,
    obb_polygon,
    polygon_clearance_m,
    road_outside_fraction,
    stateful_route_projection,
    swept_front_edge_crossing,
    validate_evaluation_v2_contract,
    vehicle_body_planar_kinematic_proxy,
)
from scripts.integrations import (
    review_diffusion_planner_v25_evaluation_v2 as independent_review,
)


def test_contract_is_versioned_exact_and_non_claim_authorizing() -> None:
    contract = evaluation_v2_contract()
    assert contract["schema_version"] == "camp_dp_v25_evaluation_v2_contract_v1"
    assert contract["result_semantics"] == "exploratory_posthoc_not_claim_authorizing"
    assert contract["claim_policy"]["v2_scientific_hard_gate"] == (
        "not_prospectively_defined_for_v2"
    )
    assert contract["claim_policy"]["weighted_total_score_generated"] is False
    assert contract["claim_policy"]["v2_claim_authorized"] is False
    assert contract["legacy_namespace"]["values_mutated"] is False
    assert validate_evaluation_v2_contract(contract) == contract
    mutated = copy.deepcopy(contract)
    mutated["unknown"] = True
    with pytest.raises(ValueError, match="contract drifted"):
        validate_evaluation_v2_contract(mutated)


def test_contract_freezes_all_descriptive_grids_and_sources() -> None:
    contract = evaluation_v2_contract()
    assert contract["grids"]["clearance_le_m"]["values"] == list(CLEARANCE_GRID_M)
    assert contract["grids"]["ttc_le_s"]["values"] == list(TTC_GRID_S)
    assert contract["grids"]["closing_ge_mps"]["values"] == list(CLOSING_GRID_MPS)
    assert contract["grids"]["drac_ge_mps2"]["values"] == list(DRAC_GRID_MPS2)
    assert contract["grids"]["speed_tolerance_mps"]["values"] == list(
        SPEED_TOLERANCE_GRID_MPS
    )
    assert contract["grids"]["acceleration_abs_gt_mps2"]["values"] == list(
        ACCELERATION_GRID_MPS2
    )
    assert contract["grids"]["jerk_abs_gt_mps3"]["values"] == list(JERK_GRID_MPS3)
    assert contract["grids"]["latency_deadline_ms"]["values"] == list(
        LATENCY_DEADLINE_GRID_MS
    )
    assert contract["grids"]["classification"] == (
        "project_descriptive_not_industrial_gate"
    )


def test_obb_geometry_uses_rear_axle_wheelbase_reference() -> None:
    polygon = obb_polygon([0.0, 0.0], 0.0, 4.5, 1.8, wheelbase_m=2.7)
    np.testing.assert_allclose(
        polygon,
        [[-0.9, -0.9], [3.6, -0.9], [3.6, 0.9], [-0.9, 0.9]],
    )


def test_stationary_parallel_1_9m_is_proximity_not_dynamic_risk() -> None:
    ego = obb_polygon([0.0, 0.0], 0.0, 4.0, 1.0)
    actor = obb_polygon([0.0, 2.9], 0.0, 4.0, 1.0)
    row = dynamic_pair_tick(
        ego_polygon=ego,
        actor_polygon=actor,
        ego_position_xy=[0.0, 0.0],
        actor_position_xy=[0.0, 2.9],
        ego_velocity_xy_mps=[0.0, 0.0],
        actor_velocity_xy_mps=[0.0, 0.0],
    )
    assert math.isclose(row["clearance_m"], 1.9)
    assert row["collision"] is False
    assert row["closing_mps"] == 0.0
    assert row["drac_mps2"] is None
    assert row["geometry_ttc_s"] is None


def test_high_closing_2_01m_is_captured_by_ttc_and_drac() -> None:
    ego = obb_polygon([0.0, 0.0], 0.0, 4.0, 1.0)
    actor = obb_polygon([6.01, 0.0], 0.0, 4.0, 1.0)
    row = dynamic_pair_tick(
        ego_polygon=ego,
        actor_polygon=actor,
        ego_position_xy=[0.0, 0.0],
        actor_position_xy=[6.01, 0.0],
        ego_velocity_xy_mps=[5.0, 0.0],
        actor_velocity_xy_mps=[0.0, 0.0],
    )
    assert math.isclose(row["clearance_m"], 2.01, abs_tol=1e-12)
    assert row["closing_mps"] == 5.0
    assert row["drac_mps2"] > 5.0
    assert math.isclose(row["geometry_ttc_s"], 2.01 / 5.0, abs_tol=1e-12)


def test_continuous_sat_separates_diverging_objects() -> None:
    ego = obb_polygon([0.0, 0.0], 0.0, 4.0, 2.0)
    actor = obb_polygon([10.0, 0.0], 0.0, 4.0, 2.0)
    assert continuous_sat_ttc_s(ego, actor, [-1.0, 0.0], [1.0, 0.0]) is None


def test_full_polygon_detects_outside_even_when_five_samples_are_inside() -> None:
    footprint = np.asarray([[-2.0, -1.0], [2.0, -1.0], [2.0, 1.0], [-2.0, 1.0]])
    five = [[0.0, 0.0], *footprint.tolist()]
    drivable = []
    for x, y in five:
        drivable.append(
            [
                [x - 0.12, y - 0.12],
                [x + 0.12, y - 0.12],
                [x + 0.12, y + 0.12],
                [x - 0.12, y + 0.12],
            ]
        )
    assert all(
        any(
            left <= x <= right and bottom <= y <= top
            for polygon in drivable
            for left, right, bottom, top in [
                (
                    min(point[0] for point in polygon),
                    max(point[0] for point in polygon),
                    min(point[1] for point in polygon),
                    max(point[1] for point in polygon),
                )
            ]
        )
        for x, y in five
    )
    assert road_outside_fraction(footprint, drivable) > 0.9


def test_drivable_union_clipping_does_not_double_count_overlap() -> None:
    footprint = [[-2.0, -1.0], [2.0, -1.0], [2.0, 1.0], [-2.0, 1.0]]
    overlapping_cover = [
        [[-3.0, -2.0], [0.5, -2.0], [0.5, 2.0], [-3.0, 2.0]],
        [[-0.5, -2.0], [3.0, -2.0], [3.0, 2.0], [-0.5, 2.0]],
    ]
    assert road_outside_fraction(footprint, overlapping_cover) == 0.0
    assert (
        independent_review._outside_fraction(
            np.asarray(footprint, dtype=np.float64),
            [np.asarray(row, dtype=np.float64) for row in overlapping_cover],
        )
        == 0.0
    )


def test_red_crossing_at_0_4mps_is_unthresholded_crossing() -> None:
    result = swept_front_edge_crossing(
        [[-0.1, -1.0], [-0.1, 1.0]],
        [[0.1, -1.0], [0.1, 1.0]],
        [[0.0, -2.0], [0.0, 2.0]],
    )
    assert result == {"status": "computed", "crossing": True, "alpha": 0.5}
    pre_speed, post_speed = 0.4, 0.4
    crossing_speed = pre_speed + result["alpha"] * (post_speed - pre_speed)
    assert crossing_speed == 0.4
    assert crossing_speed <= 0.5


def test_rotating_front_edge_multiple_times_is_ambiguous() -> None:
    result = swept_front_edge_crossing(
        [[-1.0, -1.0], [-1.0, 1.0]],
        [[2.0, -1.0], [1.0, 1.0]],
        [[0.0, -2.0], [0.0, 2.0]],
    )
    assert result["status"] == "ambiguous_evidence_missing"
    assert result["crossing"] is None


def _segments() -> list[dict[str, object]]:
    return [
        {
            "index": 0,
            "start_xy": [0.0, 0.0],
            "end_xy": [10.0, 0.0],
            "arc_start_m": 0.0,
            "arc_end_m": 10.0,
            "next_indices": [1],
        },
        {
            "index": 1,
            "start_xy": [10.0, 0.0],
            "end_xy": [20.0, 0.0],
            "arc_start_m": 10.0,
            "arc_end_m": 20.0,
            "next_indices": [],
        },
    ]


def test_stateful_route_projection_handles_parallel_self_near_geometry() -> None:
    segments = _segments()
    segments.append(
        {
            "index": 2,
            "start_xy": [0.0, 0.2],
            "end_xy": [10.0, 0.2],
            "arc_start_m": 20.0,
            "arc_end_m": 30.0,
            "next_indices": [],
        }
    )
    positions = [[float(index), 0.01] for index in range(10)]
    result = stateful_route_projection(positions, [10.0] * 10, segments)
    assert result["substatus"] == "computed"
    assert max(result["s_t_m"]) < 10.0


def test_route_fork_jump_is_rejected_by_adjacency_and_travel_bound() -> None:
    segments = _segments()
    segments.append(
        {
            "index": 2,
            "start_xy": [100.0, 0.0],
            "end_xy": [110.0, 0.0],
            "arc_start_m": 20.0,
            "arc_end_m": 30.0,
            "next_indices": [],
        }
    )
    result = stateful_route_projection([[0.0, 0.0], [100.0, 0.0]], [1.0, 1.0], segments)
    assert result["status"] == "ambiguous_evidence_missing"
    assert result["maps_to_status"] == "evidence_missing"


def test_vehicle_body_sample_accounting_and_boxcar_are_frozen() -> None:
    positions = [[0.1 * index, 0.0] for index in range(64)]
    result = vehicle_body_planar_kinematic_proxy(positions, [0.0] * 64)
    assert result["sample_accounting"] == {
        "position_samples": 64,
        "interval_velocity_samples": 63,
        "raw_acceleration_samples": 62,
        "filtered_acceleration_samples": 52,
        "filtered_jerk_samples": 51,
        "padding_used": False,
    }
    assert BOXCAR_KERNEL == tuple([1.0 / 11.0] * 11)
    assert result["filtered_acceleration"]["longitudinal"]["peak_abs"] < 1e-12


def test_scalar_speed_spike_does_not_enter_position_derived_proxy() -> None:
    positions = [[0.1 * index, 0.0] for index in range(64)]
    legacy_scalar_speed = [1.0] * 64
    legacy_scalar_speed[31] = 50.0
    assert max(legacy_scalar_speed) == 50.0
    result = vehicle_body_planar_kinematic_proxy(positions, [0.0] * 64)
    assert result["filtered_jerk"]["longitudinal"]["peak_abs"] < 1e-10


def test_missing_industrial_evidence_is_fail_closed_in_contract() -> None:
    missing = set(evaluation_v2_contract()["not_modeled"])
    assert {
        "collision_severity",
        "PET_without_conflict_zone_and_passage_times",
        "seat_response",
        "vertical_acceleration",
        "ISO_2631_conformity",
        "SAE_J2834_conformity",
    }.issubset(missing)


def test_clustered_summary_requires_full_500_and_100x5() -> None:
    values = np.arange(500, dtype=np.float64)
    clusters = [f"cluster_{index // 5:03d}" for index in range(500)]
    result = clustered_paired_descriptive(values, clusters)
    assert result["pair_count"] == 500
    assert result["cluster_count"] == 100
    assert result["claim_authorized"] is False
    with pytest.raises(ValueError, match="all 500 pairs"):
        clustered_paired_descriptive(values[:-1], clusters[:-1])


def test_polygon_clearance_is_zero_for_intersection() -> None:
    first = obb_polygon([0.0, 0.0], 0.0, 4.0, 2.0)
    second = obb_polygon([1.0, 0.0], 0.0, 4.0, 2.0)
    assert polygon_clearance_m(first, second) == 0.0


def test_result_vector_cancels_inference_instead_of_shrinking_denominator() -> None:
    endpoint_names = set(evaluation_v2_contract()["endpoint_catalog"])
    runs = []
    for pair_index in range(500):
        for arm in ("candidate0", "static14d", "scene14d"):
            runs.append(
                {
                    "pair_key": f"pair_{pair_index:03d}",
                    "arm": arm,
                    "inference_cluster_id": f"cluster_{pair_index // 5:03d}",
                    "benchmark_stratum": "corridor",
                    "scenario_family": "synthetic",
                    "source_class": "synthetic",
                    "source_receipt_sha256": "a" * 64,
                    "run_config_sha256": "b" * 64,
                    "candidate0_supplementary_equivalence": None,
                    "endpoints": {
                        name: {
                            "status": "evidence_missing",
                            "reason": "synthetic_missing",
                        }
                        for name in endpoint_names
                    },
                    "missing_evidence": {},
                }
            )
    result = build_evaluation_v2_result(
        runs,
        bindings={},
        contract_root_sha256="c" * 64,
        contract_review_root_sha256="d" * 64,
        legacy_evaluation={"status": "synthetic"},
    )
    for endpoint in result["endpoint_vector"].values():
        assert endpoint["aggregate"] == {
            "status": "evidence_missing",
            "paired_inference": "cancelled_missing_full_paired_denominator",
            "complete_case_shrinkage_used": False,
        }
        assert endpoint["denominator"]["required_arm_count"] == 1500


def test_scalar_paths_use_json_pointer_for_decimal_and_reserved_keys() -> None:
    value = {"grid": {"0.5": {"a/b~c": 7.0}}}
    producer_paths = v2_kernel._numeric_paths(value, prefix="")
    reviewer_paths = independent_review._numeric_paths(value)
    assert producer_paths == ["/grid/0.5/a~1b~0c"]
    assert reviewer_paths == producer_paths
    assert v2_kernel._path_number(value, producer_paths[0]) == 7.0
    assert independent_review._path(value, reviewer_paths[0]) == 7.0


def test_independent_reviewer_does_not_import_producer_metric_module() -> None:
    source = independent_review.Path(independent_review.__file__).read_text(
        encoding="utf-8"
    )
    assert (
        "from camp_core.integrations.diffusion_planner_v25_evaluation_v2 import"
        not in source
    )
    assert 'producer_metric_module_imported": False' in source
    assert 'producer_threshold_tables_imported": False' in source


def test_evaluation_v2_geometry_has_no_optional_shapely_dependency() -> None:
    paths = (
        Path(__file__).parents[1]
        / "camp_core"
        / "integrations"
        / "diffusion_planner_v25_evaluation_v2.py",
        Path(__file__).parents[2]
        / "scripts"
        / "integrations"
        / "materialize_diffusion_planner_v25_evaluation_v2.py",
        Path(independent_review.__file__),
    )
    for path in paths:
        assert "shapely" not in path.read_text(encoding="utf-8").lower()


def test_independent_reviewer_literal_geometry_and_body_match_synthetic_kernel() -> (
    None
):
    producer_obb = obb_polygon([1.0, 2.0], 0.3, 4.5, 1.8, wheelbase_m=2.7)
    reviewer_obb = independent_review._obb([1.0, 2.0], 0.3, 4.5, 1.8, 2.7)
    np.testing.assert_allclose(producer_obb, reviewer_obb)
    ticks = []
    for index in range(64):
        ticks.append(
            {
                "safety": {
                    "position_xy": [0.1 * index, 0.001 * index * index],
                    "ego_heading_rad": 0.01 * index,
                }
            }
        )
    producer = vehicle_body_planar_kinematic_proxy(
        [row["safety"]["position_xy"] for row in ticks],
        [row["safety"]["ego_heading_rad"] for row in ticks],
    )
    reviewer = independent_review._body(ticks)
    independent_review._assert_equal(producer, reviewer, "synthetic body")


def test_candidate0_equivalence_is_not_applicable_without_dynamic_actors() -> None:
    assert (
        independent_review._candidate_equivalence_for_actor_inventory({}, {}, [])
        is None
    )


def test_independent_reviewer_unknown_field_fails_closed() -> None:
    with pytest.raises(ValueError, match="fields drifted"):
        independent_review._assert_equal(
            {"status": "benchmark_only"},
            {"status": "benchmark_only", "unknown": 1},
            "synthetic endpoint",
        )
