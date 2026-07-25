from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import t as student_t


SCHEMA_VERSION = "camp_dp_v25_evaluation_v2_contract_v3"
RESULT_SCHEMA_VERSION = "camp_dp_v25_evaluation_v2_artifact_v3"
ARMS = ("candidate0", "static14d", "scene14d")
METHOD_ARMS = ("static14d", "scene14d")
TICK_COUNT = 64
DT_S = 0.1
GEOM_EPS = 1e-9
STATUSES = (
    "computed",
    "benchmark_only",
    "evidence_missing",
    "requires_future_nonholdout_acquisition",
    "ambiguous_evidence_missing",
)
CLEARANCE_GRID_M = (0.0, 0.5, 1.0, 2.0)
TTC_GRID_S = (0.5, 1.0, 2.0, 3.0, 5.0)
CLOSING_GRID_MPS = (0.5, 1.0, 2.0, 5.0)
DRAC_GRID_MPS2 = (0.5, 1.0, 2.0, 3.0, 5.0)
SPEED_TOLERANCE_GRID_MPS = (0.0, 0.05, 0.1, 0.2)
ACCELERATION_GRID_MPS2 = (0.5, 1.0, 2.0, 3.0)
JERK_GRID_MPS3 = (0.5, 1.0, 2.0, 5.0)
LATENCY_DEADLINE_GRID_MS = (50.0, 100.0, 200.0, 500.0, 1000.0)
BOXCAR_KERNEL = tuple([1.0 / 11.0] * 11)
GEOMETRY_TTC_HORIZON_S = 5.0
ROUTE_TRAVEL_EPSILON_M = 1e-6
UNION_BOUNDARY_PROBE_EPS_M = 1e-7

EXECUTION_ROOT = "e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881"
EXECUTION_REVIEW_ROOT = (
    "f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d"
)
CORRECTED_EVALUATION_ROOT = (
    "4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f"
)
CORRECTED_EVALUATION_REVIEW_ROOT = (
    "94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459"
)
CONTINUATION_LEDGER_SHA256 = (
    "727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
IDENTITY_SHA256 = "5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a"
PROTOCOL_SHA256 = "aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f"
PLAN_SHA256 = "41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0"
NONCE = "8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42"
SUPERSEDED_V2_CONTRACT_ROOT = (
    "2a3c39aea959a9e311859f8af2c4ea81e22ac093b4e62ea48cbca6f4808d5795"
)
SUPERSEDED_V2_CONTRACT_REVIEW_ROOT = (
    "a15edb5cad2279991dec2f091e134cd3a711a1b949eb38523a20125578500fed"
)
SUPERSEDED_V2_MATERIALIZATION_ROOT = (
    "0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d"
)
SUPERSEDED_V2_REVIEW_ROOT = (
    "d1cfb29dbb34e3bb92592f803820a6a0454af89b3b9fc2100b45cbaf8215f91d"
)
SUPERSEDED_CORRECTED_V2_CONTRACT_ROOT = (
    "ab99f6740038136409b9f131c8bd38dd35b1b19c338e85c4df6ba86b25f59306"
)
SUPERSEDED_CORRECTED_V2_CONTRACT_REVIEW_ROOT = (
    "0962b233a2a0391649433233bd4e7fcbd688ddedc28f2d25fa5cf4eda9354628"
)
SUPERSEDED_CORRECTED_V2_MATERIALIZATION_ROOT = (
    "3a4575f346188d87c4c3c18e4cc817540eac09aa38cd0cf886628c3013402588"
)
SUPERSEDED_CORRECTED_V2_REVIEW_ROOT = (
    "372550201df3f62907d7fe247cb9889cecfa2abef91ab7db425613f70c816827"
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def evaluation_v2_contract() -> dict[str, Any]:
    endpoint_catalog = {
        "collision": {
            "formula": (
                "full frozen ego/actor OBB polygon intersection per tick; "
                "run collision_any=any(I), episodes=sum(false_to_true), "
                "duration_s=sum(I)*0.1"
            ),
            "units": {
                "collision_any": "bool",
                "episode_count": "count",
                "duration_s": "s",
            },
            "evidence_class": "benchmark_only",
            "severity": "evidence_missing",
        },
        "dynamic_proximity": {
            "formula": {
                "clearance": "distance(full_ego_polygon,full_actor_polygon)",
                "closing": (
                    "max(0,-dot(p_actor-p_ego,v_actor-v_ego)/"
                    "max(norm(p_actor-p_ego),1e-9))"
                ),
                "drac": (
                    "closing^2/(2*max(clearance,1e-9)) only when closing>0 "
                    "and clearance>0; collision is separate"
                ),
                "geometry_ttc": (
                    "continuous SAT entry time under constant-velocity "
                    "translation of the two frozen OBBs only when centroid "
                    "dot(r,v_rel)<0 and entry_time<=5.0s"
                ),
            },
            "units": {
                "clearance": "m",
                "closing": "m/s",
                "drac": "m/s^2",
                "geometry_ttc": "s",
            },
            "evidence_class": "benchmark_only",
            "pet": "evidence_missing",
            "geometry_ttc_prediction_horizon_s": GEOMETRY_TTC_HORIZON_S,
            "ego_velocity_source": (
                "same_tick_scalar_speed_times_heading_kinematic_reconstruction"
            ),
        },
        "road_containment": {
            "formula": (
                "outside_fraction=area(F_t minus union(D_t))/area(F_t); "
                "offroad_any=any(outside_fraction>1e-9); exposed union boundary "
                "is reconstructed by splitting root-bound polygon edges at all "
                "intersections and removing internal overlap/adjacency seams; "
                "signed clearance is positive minimum full-footprint-boundary "
                "distance when contained and negative maximum footprint-boundary "
                "penetration when outside"
            ),
            "units": {
                "outside_fraction": "fraction",
                "duration_s": "s",
                "episode_count": "count",
                "minimum_signed_boundary_clearance_m": "m",
                "maximum_boundary_penetration_m": "m",
            },
            "evidence_class": "benchmark_only",
            "five_point_substitute_allowed": False,
            "signed_boundary_clearance_or_penetration": {
                "status": "computed",
                "union_boundary_source": (
                    "deterministic_external_boundary_of_root_bound_polygon_union"
                ),
                "internal_overlap_or_adjacency_seams_are_boundary": False,
                "probe_epsilon_m": UNION_BOUNDARY_PROBE_EPS_M,
            },
        },
        "certified_red_crossing": {
            "formula": (
                "same-tick certified red phase and exact route stop-line; "
                "full front-edge swept geometry from interval start to end; "
                "unthresholded crossing independent of speed"
            ),
            "units": {
                "opportunity_count": "encounter_count",
                "red_phase_interval_count": "interval_count",
                "crossing_count": "count",
                "crossing_speed_mps": "m/s",
            },
            "evidence_class": "benchmark_only",
            "future_phase_consumed": False,
        },
        "speed": {
            "formula": {
                "excess": "max(0,same_tick_speed-same_tick_map_limit)",
                "duration": "sum(I(excess>tolerance))*0.1",
                "magnitude_duration": ("sum(max(0,excess-tolerance))*0.1"),
            },
            "units": {
                "excess": "m/s",
                "duration": "s",
                "magnitude_duration": "m",
            },
            "evidence_class": "benchmark_only",
        },
        "route": {
            "formula": (
                "stateful ordered-route segment projection with same/adjacent "
                "forward-or-backward transitions and max(trapezoidal speed "
                "distance,sealed position displacement)+1e-6m travel bound; "
                "completion=clip(max_forward/route_length,0,1)"
            ),
            "units": {
                "s_t": "m",
                "max_forward": "m",
                "net": "m",
                "backtracking_duration": "s",
                "backtracking_distance": "m",
                "completion": "fraction",
            },
            "evidence_class": "benchmark_only",
        },
        "goal": {
            "formula": (
                "independent of route projection; reached when same-tick "
                "distance<=frozen goal_tolerance_m; passed when the same tick "
                "is within frozen goal_pass_window_m and the goal lies behind "
                "the frozen ego heading"
            ),
            "units": {
                "minimum_goal_distance": "m",
                "goal_reached": "bool",
                "goal_passed": "bool",
            },
            "evidence_class": "benchmark_only",
        },
        "vehicle_body_planar_kinematic_proxy": {
            "formula": (
                "64 positions -> 63 interval velocities -> 62 accelerations; "
                "rotate by corresponding heading; 11-point centered equal-weight "
                "zero-phase valid-only boxcar -> 52; filtered jerk diff/0.1 -> 51"
            ),
            "units": {"acceleration": "m/s^2", "jerk": "m/s^3"},
            "evidence_class": "benchmark_only",
            "occupant_or_seat_claim": False,
        },
        "latency": {
            "formula": (
                "per-run empirical mean/median/p95/p99/max by native stage; "
                "deadline exceedance_rate=count(total>D)/64"
            ),
            "units": {"latency": "ms", "exceedance_rate": "fraction"},
            "evidence_class": "benchmark_only",
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark": "fresh_b4",
        "evaluation_role": "additive_read_only_evaluation_v2",
        "result_semantics": "exploratory_posthoc_not_claim_authorizing",
        "status_vocabulary": list(STATUSES),
        "bindings": {
            "execution_root_sha256": EXECUTION_ROOT,
            "execution_review_root_sha256": EXECUTION_REVIEW_ROOT,
            "corrected_evaluation_root_sha256": CORRECTED_EVALUATION_ROOT,
            "corrected_evaluation_review_root_sha256": (
                CORRECTED_EVALUATION_REVIEW_ROOT
            ),
            "continuation_ledger_sha256": CONTINUATION_LEDGER_SHA256,
            "fixed_dp_head": FIXED_DP_HEAD,
            "holdout_identity_sha256": IDENTITY_SHA256,
            "experiment_protocol_sha256": PROTOCOL_SHA256,
            "execution_plan_sha256": PLAN_SHA256,
            "nonce": NONCE,
            "superseded_evaluation_v2_diagnostic": {
                "contract_root_sha256": SUPERSEDED_V2_CONTRACT_ROOT,
                "contract_review_root_sha256": SUPERSEDED_V2_CONTRACT_REVIEW_ROOT,
                "materialization_root_sha256": SUPERSEDED_V2_MATERIALIZATION_ROOT,
                "review_root_sha256": SUPERSEDED_V2_REVIEW_ROOT,
            },
            "superseded_corrected_evaluation_v2_diagnostic": {
                "contract_root_sha256": SUPERSEDED_CORRECTED_V2_CONTRACT_ROOT,
                "contract_review_root_sha256": (
                    SUPERSEDED_CORRECTED_V2_CONTRACT_REVIEW_ROOT
                ),
                "materialization_root_sha256": (
                    SUPERSEDED_CORRECTED_V2_MATERIALIZATION_ROOT
                ),
                "review_root_sha256": SUPERSEDED_CORRECTED_V2_REVIEW_ROOT,
            },
        },
        "denominator": {
            "pair_count": 500,
            "arm_count": 1500,
            "ticks_per_arm": 64,
            "tick_count": 96000,
            "fresh_execution_reused": True,
            "fresh_execution_rerun": False,
            "complete_case_denominator_shrinkage_allowed": False,
        },
        "claim_policy": {
            "legacy_benchmark_v1_values_mutable": False,
            "legacy_preregistration_or_claim_mutable": False,
            "weighted_total_score_generated": False,
            "different_denominators_mixed": False,
            "v2_scientific_hard_gate": "not_prospectively_defined_for_v2",
            "integrity_hard_gates": [
                "complete_denominator",
                "finite_values",
                "exact_schema",
                "root_binding",
                "sealed_source_no_mutation",
            ],
            "future_confirmatory_claim_requires": (
                "separate prospective preregistration of endpoints, thresholds, "
                "multiplicity, and hard gates on new nonholdout evidence"
            ),
            "v2_claim_authorized": False,
        },
        "endpoint_catalog": endpoint_catalog,
        "grids": {
            "clearance_le_m": {
                "values": list(CLEARANCE_GRID_M),
                "source": "accepted_metric_semantics_amendment_v1",
            },
            "ttc_le_s": {
                "values": list(TTC_GRID_S),
                "source": (
                    "High-authorized Evaluation v2 descriptive coverage grid "
                    "2026-07-25"
                ),
            },
            "closing_ge_mps": {
                "values": list(CLOSING_GRID_MPS),
                "source": (
                    "High-authorized Evaluation v2 descriptive coverage grid "
                    "2026-07-25"
                ),
            },
            "drac_ge_mps2": {
                "values": list(DRAC_GRID_MPS2),
                "source": (
                    "High-authorized Evaluation v2 descriptive coverage grid "
                    "2026-07-25"
                ),
            },
            "speed_tolerance_mps": {
                "values": list(SPEED_TOLERANCE_GRID_MPS),
                "source": "frozen_native_speed_protocol",
                "project_operational_tolerance": 0.1,
            },
            "acceleration_abs_gt_mps2": {
                "values": list(ACCELERATION_GRID_MPS2),
                "source": "accepted_metric_semantics_amendment_v1",
            },
            "jerk_abs_gt_mps3": {
                "values": list(JERK_GRID_MPS3),
                "source": (
                    "High-authorized Evaluation v2 descriptive coverage grid "
                    "2026-07-25"
                ),
            },
            "latency_deadline_ms": {
                "values": list(LATENCY_DEADLINE_GRID_MS),
                "source": (
                    "High-authorized Evaluation v2 descriptive coverage grid "
                    "2026-07-25"
                ),
                "100ms_label": "hypothetical_10Hz_budget",
            },
            "classification": "project_descriptive_not_industrial_gate",
        },
        "geometry": {
            "dt_s": DT_S,
            "geom_eps": GEOM_EPS,
            "ego_reference": (
                "rear_axle_pose_with_frozen_wheelbase_and_symmetric_overhangs"
            ),
            "obb_order": [
                "rear_right",
                "front_right",
                "front_left",
                "rear_left",
            ],
            "route_transition": (
                "same segment or frozen ordered forward-or-backward adjacent segment"
            ),
            "route_travel_bound": (
                "max(0.5*(speed[t-1]+speed[t])*0.1,"
                "norm(position[t]-position[t-1])) + 1e-6m"
            ),
            "geometry_ttc_approach_condition": "centroid dot(r,v_rel)<0",
            "geometry_ttc_prediction_horizon_s": GEOMETRY_TTC_HORIZON_S,
            "geometry_ttc_horizon_classification": (
                "project_descriptive_not_industrial_gate"
            ),
            "road_union_boundary_probe_epsilon_m": UNION_BOUNDARY_PROBE_EPS_M,
            "road_internal_overlap_or_adjacency_seams_are_boundary": False,
            "boxcar_kernel": list(BOXCAR_KERNEL),
            "boxcar_padding": False,
        },
        "source_capability_policy": {
            "map_and_route_assets": (
                "must be present, SHA-bound by sealed run_config, and loaded "
                "without executing DP/K8"
            ),
            "candidate0_supplementary_actor_state": (
                "usable only after exact per-tick primary/supplementary "
                "header,input,action,selected-trajectory,ego-state and source "
                "equivalence; otherwise candidate0 dynamic-pair endpoints and "
                "paired inference are evidence_missing"
            ),
            "pet": "requires frozen conflict zone and both passage times",
            "collision_severity": (
                "requires physical impact relative velocity/delta-v/contact evidence"
            ),
            "occupant_comfort": (
                "seat/body-contact/vertical/roll/pitch/human-transfer evidence missing"
            ),
            "production_latency": (
                "controlled warm-up, concurrent load and deadline scheduler missing"
            ),
        },
        "statistics": {
            "per_run_first": True,
            "paired_unit_count": 500,
            "independent_cluster_count": 100,
            "cluster_definition": "corridor/intersection equal-mass cluster",
            "estimator": "equal_mass_cluster_mean_student_t",
            "report": [
                "CI95",
                "better_tie_worse_for_directional_scalars",
                "variance_decomposition_descriptive",
            ],
            "tie_rule": "exact_zero_delta",
            "tie_rule_source": "High-authorized Evaluation v2 correction 2026-07-25",
            "actual_scalar_path_direction_coverage": (
                "exhaustive_exactly_once_and_unknown_path_fail_closed"
            ),
            "unclassified_policy": (
                "signed means, sample-accounting and opportunity counts are "
                "descriptive_unclassified"
            ),
            "direction_rules": {
                "collision": "lower_except_unclassified_metadata",
                "dynamic_proximity": (
                    "min_clearance_and_min_finite_geometry_ttc_higher;"
                    "other_risk_scalars_lower_except_unclassified_metadata"
                ),
                "road_containment": (
                    "exposure_and_maximum_penetration_lower;minimum_signed_"
                    "boundary_clearance_higher;geometry_metadata_"
                    "descriptive_unclassified"
                ),
                "certified_red_crossing": (
                    "crossing_scalars_lower;opportunity_and_interval_counts_"
                    "descriptive_unclassified"
                ),
                "speed": "lower_except_unclassified_metadata",
                "route": (
                    "backtracking_lower;forward_progress_completion_final_arc_"
                    "higher;distance_traveled_and_route_length_"
                    "descriptive_unclassified"
                ),
                "goal": (
                    "minimum_distance_lower;reached_passed_higher;"
                    "native_and_threshold_metadata_descriptive_unclassified"
                ),
                "vehicle_body_planar_kinematic_proxy": (
                    "unsigned_magnitude_deceleration_rms_percentile_duration_"
                    "lower;signed_acceleration_mean_min_max_"
                    "descriptive_unclassified"
                ),
                "latency": "lower_except_unclassified_metadata",
            },
            "ticks_seeds_or_arms_independent": False,
            "missing_arm_policy": (
                "report full missing denominator and cancel paired inference"
            ),
        },
        "legacy_namespace": {
            "source_root_sha256": CORRECTED_EVALUATION_ROOT,
            "label": "immutable_legacy_benchmark_v1",
            "values_recomputed": False,
            "values_mutated": False,
            "safetycost_is_v2_score": False,
        },
        "not_modeled": [
            "collision_severity",
            "PET_without_conflict_zone_and_passage_times",
            "seat_response",
            "occupant_response",
            "vertical_acceleration",
            "roll",
            "pitch",
            "ISO_2631_conformity",
            "SAE_J2834_conformity",
        ],
    }


def validate_evaluation_v2_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = evaluation_v2_contract()
    if type(value) is not dict or value != expected:
        raise ValueError("Evaluation v2 contract drifted")
    return copy.deepcopy(expected)


def obb_polygon(
    position_xy: Sequence[float],
    heading_rad: float,
    length_m: float,
    width_m: float,
    *,
    wheelbase_m: float | None = None,
) -> np.ndarray:
    xy = _finite_vector(position_xy, 2, "position_xy")
    heading = _finite(heading_rad, "heading_rad")
    length = _positive(length_m, "length_m")
    width = _positive(width_m, "width_m")
    if wheelbase_m is not None:
        wheelbase = _positive(wheelbase_m, "wheelbase_m")
        rear_overhang = (length - wheelbase) / 2.0
        dx_lo, dx_hi = -rear_overhang, length - rear_overhang
    else:
        dx_lo, dx_hi = -length / 2.0, length / 2.0
    local = np.asarray(
        [
            [dx_lo, -width / 2.0],
            [dx_hi, -width / 2.0],
            [dx_hi, width / 2.0],
            [dx_lo, width / 2.0],
        ],
        dtype=np.float64,
    )
    c, s = math.cos(heading), math.sin(heading)
    rotation = np.asarray([[c, -s], [s, c]], dtype=np.float64)
    return local @ rotation.T + xy


def polygons_intersect(
    a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]
) -> bool:
    first = _polygon(a, "polygon_a")
    second = _polygon(b, "polygon_b")
    return _convex_polygons_intersect(first, second)


def polygon_clearance_m(
    a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]
) -> float:
    first = _polygon(a, "polygon_a")
    second = _polygon(b, "polygon_b")
    if _convex_polygons_intersect(first, second):
        return 0.0
    distances = [
        _point_segment_distance(
            first[index],
            second[other],
            second[(other + 1) % second.shape[0]],
        )
        for index in range(first.shape[0])
        for other in range(second.shape[0])
    ]
    distances.extend(
        _point_segment_distance(
            second[index],
            first[other],
            first[(other + 1) % first.shape[0]],
        )
        for index in range(second.shape[0])
        for other in range(first.shape[0])
    )
    return float(min(distances))


def continuous_sat_ttc_s(
    ego_polygon: Sequence[Sequence[float]],
    actor_polygon: Sequence[Sequence[float]],
    ego_velocity_xy_mps: Sequence[float],
    actor_velocity_xy_mps: Sequence[float],
    *,
    prediction_horizon_s: float = GEOMETRY_TTC_HORIZON_S,
) -> float | None:
    ego = _vertices(ego_polygon, "ego_polygon")
    actor = _vertices(actor_polygon, "actor_polygon")
    relative_velocity = _finite_vector(
        actor_velocity_xy_mps, 2, "actor_velocity_xy_mps"
    ) - _finite_vector(ego_velocity_xy_mps, 2, "ego_velocity_xy_mps")
    if polygons_intersect(ego, actor):
        return 0.0
    if (
        not math.isfinite(prediction_horizon_s)
        or prediction_horizon_s <= 0.0
    ):
        raise ValueError("geometry TTC prediction horizon drifted")
    relative_position = actor.mean(axis=0) - ego.mean(axis=0)
    if float(np.dot(relative_position, relative_velocity)) >= 0.0:
        return None
    entry = 0.0
    exit_time = math.inf
    for polygon in (ego, actor):
        for index in range(polygon.shape[0]):
            edge = polygon[(index + 1) % polygon.shape[0]] - polygon[index]
            axis = np.asarray([-edge[1], edge[0]], dtype=np.float64)
            norm = float(np.linalg.norm(axis))
            if norm <= GEOM_EPS:
                continue
            axis /= norm
            a_min, a_max = float((ego @ axis).min()), float((ego @ axis).max())
            b_min, b_max = float((actor @ axis).min()), float((actor @ axis).max())
            speed = float(np.dot(relative_velocity, axis))
            if abs(speed) <= GEOM_EPS:
                if a_max < b_min or b_max < a_min:
                    return None
                continue
            first = (a_min - b_max) / speed
            second = (a_max - b_min) / speed
            axis_entry, axis_exit = min(first, second), max(first, second)
            entry = max(entry, axis_entry)
            exit_time = min(exit_time, axis_exit)
            if entry - exit_time > GEOM_EPS:
                return None
    if exit_time < -GEOM_EPS:
        return None
    result = float(max(0.0, entry))
    return result if result <= prediction_horizon_s else None


def dynamic_pair_tick(
    *,
    ego_polygon: Sequence[Sequence[float]],
    actor_polygon: Sequence[Sequence[float]],
    ego_position_xy: Sequence[float],
    actor_position_xy: Sequence[float],
    ego_velocity_xy_mps: Sequence[float],
    actor_velocity_xy_mps: Sequence[float],
) -> dict[str, Any]:
    ego_position = _finite_vector(ego_position_xy, 2, "ego_position_xy")
    actor_position = _finite_vector(actor_position_xy, 2, "actor_position_xy")
    ego_velocity = _finite_vector(ego_velocity_xy_mps, 2, "ego_velocity_xy_mps")
    actor_velocity = _finite_vector(actor_velocity_xy_mps, 2, "actor_velocity_xy_mps")
    clearance = polygon_clearance_m(ego_polygon, actor_polygon)
    collision = polygons_intersect(ego_polygon, actor_polygon)
    relative_position = actor_position - ego_position
    relative_velocity = actor_velocity - ego_velocity
    norm = max(float(np.linalg.norm(relative_position)), GEOM_EPS)
    closing = max(0.0, -float(np.dot(relative_position, relative_velocity)) / norm)
    drac = (
        closing * closing / (2.0 * max(clearance, GEOM_EPS))
        if closing > 0.0 and clearance > 0.0
        else None
    )
    ttc = continuous_sat_ttc_s(ego_polygon, actor_polygon, ego_velocity, actor_velocity)
    return {
        "collision": bool(collision),
        "clearance_m": float(clearance),
        "closing_mps": float(closing),
        "drac_mps2": None if drac is None else float(drac),
        "geometry_ttc_s": None if ttc is None else float(ttc),
        "geometry_ttc_prediction_horizon_s": GEOMETRY_TTC_HORIZON_S,
        "geometry_ttc_approach_required": True,
    }


def road_outside_fraction(
    footprint: Sequence[Sequence[float]],
    drivable_polygons: Sequence[Sequence[Sequence[float]]],
) -> float:
    ego = _polygon(footprint, "footprint")
    if not drivable_polygons:
        raise ValueError("drivable polygons are missing")
    drivable = [_polygon(row, "drivable_polygon") for row in drivable_polygons]
    ego_area = _polygon_area(ego)
    inside_area = _convex_union_intersection_area(ego, drivable)
    value = float(1.0 - inside_area / ego_area)
    if value < 0.0 or value > 1.0 + 1e-12:
        raise ValueError("outside fraction drifted")
    return float(np.clip(value, 0.0, 1.0))


def road_signed_boundary_metrics(
    footprint: Sequence[Sequence[float]],
    drivable_polygons: Sequence[Sequence[Sequence[float]]],
) -> dict[str, Any]:
    ego = _polygon(footprint, "footprint")
    if not drivable_polygons:
        raise ValueError("drivable polygons are missing")
    drivable = [_polygon(row, "drivable_polygon") for row in drivable_polygons]
    boundary = _union_boundary_segments(drivable)
    return _road_signed_boundary_metrics_normalized(ego, drivable, boundary)


def _road_signed_boundary_metrics_normalized(
    ego: np.ndarray,
    drivable: Sequence[np.ndarray],
    boundary: Sequence[tuple[np.ndarray, np.ndarray]],
) -> dict[str, Any]:
    if not boundary:
        raise ValueError("drivable polygon union has no determinate boundary")
    footprint_edges = [
        (ego[index], ego[(index + 1) % ego.shape[0]])
        for index in range(ego.shape[0])
    ]
    minimum_boundary_distance = min(
        _segment_segment_distance(start, end, other_start, other_end)
        for start, end in footprint_edges
        for other_start, other_end in boundary
    )
    outside_fraction = float(
        1.0 - _convex_union_intersection_area(ego, drivable) / _polygon_area(ego)
    )
    outside_fraction = float(np.clip(outside_fraction, 0.0, 1.0))
    if outside_fraction <= GEOM_EPS:
        penetration = 0.0
        signed = minimum_boundary_distance
    else:
        penetration = max(
            _maximum_outside_distance_on_segment(start, end, boundary, drivable)
            for start, end in footprint_edges
        )
        if penetration <= GEOM_EPS:
            raise ValueError(
                "outside footprint has no determinate union-boundary penetration"
            )
        signed = -penetration
    return {
        "status": "computed",
        "minimum_signed_boundary_clearance_m": float(signed),
        "maximum_boundary_penetration_m": float(penetration),
        "union_boundary_segment_count": len(boundary),
        "internal_overlap_or_adjacency_seams_are_boundary": False,
        "probe_epsilon_m": UNION_BOUNDARY_PROBE_EPS_M,
        "units": "m",
    }


def _union_boundary_segments(
    polygons: Sequence[np.ndarray],
) -> list[tuple[np.ndarray, np.ndarray]]:
    result: list[tuple[np.ndarray, np.ndarray]] = []
    for polygon_index, polygon in enumerate(polygons):
        for edge_index in range(polygon.shape[0]):
            start = polygon[edge_index]
            end = polygon[(edge_index + 1) % polygon.shape[0]]
            delta = end - start
            length = float(np.linalg.norm(delta))
            if length <= GEOM_EPS:
                raise ValueError("drivable polygon boundary edge is degenerate")
            ratios = [0.0, 1.0]
            for other_index, other in enumerate(polygons):
                if other_index == polygon_index:
                    continue
                for index in range(other.shape[0]):
                    ratios.extend(
                        _segment_split_ratios(
                            start,
                            end,
                            other[index],
                            other[(index + 1) % other.shape[0]],
                        )
                    )
            ratios = _sorted_unique_ratios(ratios)
            outward = np.asarray([delta[1], -delta[0]], dtype=np.float64) / length
            for lo, hi in zip(ratios[:-1], ratios[1:], strict=True):
                if hi - lo <= GEOM_EPS:
                    continue
                first = start + lo * delta
                second = start + hi * delta
                midpoint = 0.5 * (first + second)
                probe = max(UNION_BOUNDARY_PROBE_EPS_M, length * 1e-9)
                inner = midpoint - probe * outward
                outer = midpoint + probe * outward
                if _point_in_polygon_union(inner, polygons) and not _point_in_polygon_union(
                    outer, polygons
                ):
                    result.append((first, second))
    deduplicated: list[tuple[np.ndarray, np.ndarray]] = []
    for start, end in result:
        if any(
            (
                np.linalg.norm(start - other_start) <= GEOM_EPS
                and np.linalg.norm(end - other_end) <= GEOM_EPS
            )
            or (
                np.linalg.norm(start - other_end) <= GEOM_EPS
                and np.linalg.norm(end - other_start) <= GEOM_EPS
            )
            for other_start, other_end in deduplicated
        ):
            continue
        deduplicated.append((start, end))
    return deduplicated


def _segment_split_ratios(
    start: np.ndarray,
    end: np.ndarray,
    other_start: np.ndarray,
    other_end: np.ndarray,
) -> list[float]:
    delta = end - start
    other_delta = other_end - other_start
    denominator = _cross_2d(delta, other_delta)
    if abs(denominator) > GEOM_EPS:
        ratio = _cross_2d(other_start - start, other_delta) / denominator
        other_ratio = _cross_2d(other_start - start, delta) / denominator
        if (
            -GEOM_EPS <= ratio <= 1.0 + GEOM_EPS
            and -GEOM_EPS <= other_ratio <= 1.0 + GEOM_EPS
        ):
            return [float(np.clip(ratio, 0.0, 1.0))]
        return []
    if abs(_cross_2d(other_start - start, delta)) > GEOM_EPS:
        return []
    length_squared = float(np.dot(delta, delta))
    return [
        float(np.clip(np.dot(point - start, delta) / length_squared, 0.0, 1.0))
        for point in (other_start, other_end)
        if -GEOM_EPS
        <= float(np.dot(point - start, delta) / length_squared)
        <= 1.0 + GEOM_EPS
    ]


def _sorted_unique_ratios(values: Sequence[float]) -> list[float]:
    result: list[float] = []
    for value in sorted(float(np.clip(row, 0.0, 1.0)) for row in values):
        if not result or abs(value - result[-1]) > GEOM_EPS:
            result.append(value)
    return result


def _point_in_polygon_union(point: np.ndarray, polygons: Sequence[np.ndarray]) -> bool:
    return any(_point_in_convex_polygon(point, polygon) for polygon in polygons)


def _segment_segment_distance(
    first_start: np.ndarray,
    first_end: np.ndarray,
    second_start: np.ndarray,
    second_end: np.ndarray,
) -> float:
    if _segments_intersect(first_start, first_end, second_start, second_end):
        return 0.0
    return min(
        _point_segment_distance(first_start, second_start, second_end),
        _point_segment_distance(first_end, second_start, second_end),
        _point_segment_distance(second_start, first_start, first_end),
        _point_segment_distance(second_end, first_start, first_end),
    )


def _maximum_outside_distance_on_segment(
    start: np.ndarray,
    end: np.ndarray,
    boundary: Sequence[tuple[np.ndarray, np.ndarray]],
    polygons: Sequence[np.ndarray],
) -> float:
    pieces: list[tuple[float, float, float, float, float]] = []
    candidate_ratios = [0.0, 1.0]
    delta = end - start
    endpoint_upper_bound = min(
        max(
            _point_segment_distance(start, boundary_start, boundary_end),
            _point_segment_distance(end, boundary_start, boundary_end),
        )
        for boundary_start, boundary_end in boundary
    )
    local_boundary = [
        (boundary_start, boundary_end)
        for boundary_start, boundary_end in boundary
        if _segment_segment_distance(
            start, end, boundary_start, boundary_end
        )
        <= endpoint_upper_bound + GEOM_EPS
    ]
    if not local_boundary:
        raise ValueError("union boundary local candidate set is empty")
    for boundary_start, boundary_end in local_boundary:
        candidate_ratios.extend(
            _segment_split_ratios(start, end, boundary_start, boundary_end)
        )
        pieces.extend(
            _point_to_segment_squared_pieces(
                start, delta, boundary_start, boundary_end
            )
        )
    for index, first in enumerate(pieces):
        candidate_ratios.extend((first[0], first[1]))
        for second in pieces[index + 1 :]:
            lo = max(first[0], second[0])
            hi = min(first[1], second[1])
            if hi - lo <= GEOM_EPS:
                continue
            candidate_ratios.extend(
                _quadratic_roots_in_interval(
                    first[2] - second[2],
                    first[3] - second[3],
                    first[4] - second[4],
                    lo,
                    hi,
                )
            )
    maximum = 0.0
    for ratio in _sorted_unique_ratios(candidate_ratios):
        point = start + ratio * delta
        if _point_in_polygon_union(point, polygons):
            continue
        maximum = max(
            maximum,
            min(
                _point_segment_distance(point, other_start, other_end)
                for other_start, other_end in local_boundary
            ),
        )
    return float(maximum)


def _point_to_segment_squared_pieces(
    start: np.ndarray,
    delta: np.ndarray,
    segment_start: np.ndarray,
    segment_end: np.ndarray,
) -> list[tuple[float, float, float, float, float]]:
    segment = segment_end - segment_start
    length_squared = float(np.dot(segment, segment))
    if length_squared <= GEOM_EPS:
        raise ValueError("union boundary segment is degenerate")
    u0 = float(np.dot(start - segment_start, segment) / length_squared)
    u1 = float(np.dot(delta, segment) / length_squared)
    splits = [0.0, 1.0]
    if abs(u1) > GEOM_EPS:
        splits.extend((-u0 / u1, (1.0 - u0) / u1))
    ratios = _sorted_unique_ratios(
        [value for value in splits if -GEOM_EPS <= value <= 1.0 + GEOM_EPS]
    )
    pieces: list[tuple[float, float, float, float, float]] = []
    for lo, hi in zip(ratios[:-1], ratios[1:], strict=True):
        midpoint = 0.5 * (lo + hi)
        u = u0 + midpoint * u1
        if u <= 0.0:
            offset = start - segment_start
            linear = delta
        elif u >= 1.0:
            offset = start - segment_end
            linear = delta
        else:
            projection = np.outer(segment, segment) / length_squared
            normal = np.eye(2) - projection
            offset = normal @ (start - segment_start)
            linear = normal @ delta
        pieces.append(
            (
                lo,
                hi,
                float(np.dot(linear, linear)),
                float(2.0 * np.dot(offset, linear)),
                float(np.dot(offset, offset)),
            )
        )
    return pieces


def _quadratic_roots_in_interval(
    a: float, b: float, c: float, lo: float, hi: float
) -> list[float]:
    if abs(a) <= GEOM_EPS:
        if abs(b) <= GEOM_EPS:
            return []
        root = -c / b
        return [float(root)] if lo - GEOM_EPS <= root <= hi + GEOM_EPS else []
    discriminant = b * b - 4.0 * a * c
    if discriminant < -GEOM_EPS:
        return []
    square_root = math.sqrt(max(0.0, discriminant))
    roots = ((-b - square_root) / (2.0 * a), (-b + square_root) / (2.0 * a))
    return [
        float(root)
        for root in roots
        if lo - GEOM_EPS <= root <= hi + GEOM_EPS
    ]


def swept_front_edge_crossing(
    start_edge: Sequence[Sequence[float]],
    end_edge: Sequence[Sequence[float]],
    stop_line: Sequence[Sequence[float]],
) -> dict[str, Any]:
    start = _edge(start_edge, "start_edge")
    end = _edge(end_edge, "end_edge")
    stop = _edge(stop_line, "stop_line")
    swept = np.asarray([start[0], start[1], end[1], end[0]], dtype=np.float64)
    boundary_intersection = (
        _segments_intersect(start[0], start[1], stop[0], stop[1])
        or _segments_intersect(end[0], end[1], stop[0], stop[1])
        or _segments_intersect(start[0], end[0], stop[0], stop[1])
        or _segments_intersect(start[1], end[1], stop[0], stop[1])
    )
    if _polygon_self_intersects(swept) or abs(_signed_polygon_area(swept)) <= GEOM_EPS:
        if not boundary_intersection:
            return {"status": "computed", "crossing": False, "alpha": None}
        return {"status": "ambiguous_evidence_missing", "crossing": None, "alpha": None}
    if not _segment_intersects_polygon(stop[0], stop[1], swept):
        return {"status": "computed", "crossing": False, "alpha": None}
    alphas: list[float] = []
    for index in range(2):
        value = _segment_intersection_parameter(
            start[index], end[index], stop[0], stop[1]
        )
        if value is not None:
            alphas.append(value)
    if not alphas:
        if _segments_intersect(start[0], start[1], stop[0], stop[1]) or (
            _segments_intersect(end[0], end[1], stop[0], stop[1])
        ):
            return {
                "status": "ambiguous_evidence_missing",
                "crossing": None,
                "alpha": None,
            }
        return {"status": "computed", "crossing": False, "alpha": None}
    unique: list[float] = []
    for value in sorted(alphas):
        if not unique or abs(value - unique[-1]) <= 1e-7:
            if not unique:
                unique.append(value)
        else:
            unique.append(value)
    if len(unique) != 1:
        return {"status": "ambiguous_evidence_missing", "crossing": None, "alpha": None}
    return {"status": "computed", "crossing": True, "alpha": float(unique[0])}


def stateful_route_projection(
    positions_xy: Sequence[Sequence[float]],
    speeds_mps: Sequence[float],
    segments: Sequence[Mapping[str, Any]],
    *,
    dt_s: float = DT_S,
    travel_epsilon_m: float = ROUTE_TRAVEL_EPSILON_M,
) -> dict[str, Any]:
    positions = np.asarray(positions_xy, dtype=np.float64)
    speeds = np.asarray(speeds_mps, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[1] != 2 or positions.shape[0] < 2:
        raise ValueError("route positions must have shape [N,2]")
    if speeds.shape != (positions.shape[0],) or not np.isfinite(speeds).all():
        raise ValueError("route speeds drifted")
    if not np.isfinite(positions).all() or np.any(speeds < 0.0):
        raise ValueError("route inputs must be finite and nonnegative")
    route_segments = [_route_segment(row, index) for index, row in enumerate(segments)]
    states: dict[int, tuple[float, tuple[int, ...], list[float]]] = {}
    first_candidates = _projection_candidates(positions[0], route_segments)
    minimum_initial = min(
        candidate["lateral_distance_m"] for candidate in first_candidates
    )
    eligible_initial = [
        candidate
        for candidate in first_candidates
        if abs(candidate["lateral_distance_m"] - minimum_initial) <= GEOM_EPS
    ]
    if len(eligible_initial) != 1:
        return _ambiguous_route("multiple_equal_initial_route_projections")
    for candidate in eligible_initial:
        states[candidate["index"]] = (
            candidate["lateral_distance_m"],
            (candidate["index"],),
            [candidate["s_m"]],
        )
    if not states:
        return _ambiguous_route("no_initial_projection_candidate")
    for tick in range(1, positions.shape[0]):
        candidates = _projection_candidates(positions[tick], route_segments)
        minimum_lateral = min(
            candidate["lateral_distance_m"] for candidate in candidates
        )
        candidates = [
            candidate
            for candidate in candidates
            if candidate["lateral_distance_m"] - minimum_lateral
            <= travel_epsilon_m
        ]
        next_states: dict[int, tuple[float, tuple[int, ...], list[float]]] = {}
        speed_bound = 0.5 * (speeds[tick - 1] + speeds[tick]) * dt_s
        sealed_displacement = float(
            np.linalg.norm(positions[tick] - positions[tick - 1])
        )
        bound = max(speed_bound, sealed_displacement) + travel_epsilon_m
        for candidate in candidates:
            options: list[tuple[float, tuple[int, ...], list[float]]] = []
            for previous_index, previous in states.items():
                previous_s = previous[2][-1]
                allowed = (
                    candidate["index"] == previous_index
                    or candidate["index"]
                    in route_segments[previous_index]["next_indices"]
                    or previous_index
                    in route_segments[candidate["index"]]["next_indices"]
                )
                delta = candidate["s_m"] - previous_s
                if allowed and delta >= -bound and delta <= bound:
                    options.append(
                        (
                            previous[0] + candidate["lateral_distance_m"],
                            (*previous[1], candidate["index"]),
                            [*previous[2], candidate["s_m"]],
                        )
                    )
            if options:
                options.sort(key=lambda row: (row[0], row[1]))
                if len(options) > 1 and abs(options[0][0] - options[1][0]) <= GEOM_EPS:
                    return _ambiguous_route("multiple_equal_cost_route_paths")
                next_states[candidate["index"]] = options[0]
        if not next_states:
            return _ambiguous_route("no_unique_kinematically_feasible_route_path")
        states = next_states
    final = sorted(states.values(), key=lambda row: (row[0], row[1]))
    if len(final) > 1 and abs(final[0][0] - final[1][0]) <= GEOM_EPS:
        return _ambiguous_route("multiple_equal_cost_route_paths")
    s_values = np.asarray(final[0][2], dtype=np.float64)
    deltas = np.diff(s_values)
    backwards = np.maximum(0.0, -deltas)
    route_length = max(row["arc_end_m"] for row in route_segments)
    max_forward = float(np.max(s_values))
    return {
        "status": "benchmark_only",
        "substatus": "computed",
        "s_t_m": s_values.tolist(),
        "final_nearest_route_polyline_projection_m": float(s_values[-1]),
        "net_m": float(s_values[-1] - s_values[0]),
        "max_forward_m": float(max_forward - s_values[0]),
        "backtracking_duration_s": float(np.count_nonzero(backwards > 0.0) * dt_s),
        "backtracking_distance_m": float(np.sum(backwards)),
        "distance_traveled_m": float(
            np.linalg.norm(np.diff(positions, axis=0), axis=1).sum()
        ),
        "route_length_m": float(route_length),
        "completion_fraction": float(
            np.clip((max_forward - s_values[0]) / route_length, 0.0, 1.0)
        ),
        "travel_bound": (
            "max(trapezoidal_speed_distance,sealed_position_displacement)+1e-6m"
        ),
    }


def vehicle_body_planar_kinematic_proxy(
    positions_xy: Sequence[Sequence[float]],
    headings_rad: Sequence[float],
    *,
    dt_s: float = DT_S,
) -> dict[str, Any]:
    positions = np.asarray(positions_xy, dtype=np.float64)
    headings = np.asarray(headings_rad, dtype=np.float64)
    if positions.shape != (64, 2) or headings.shape != (64,):
        raise ValueError("vehicle-body proxy requires 64 positions/headings")
    if not np.isfinite(positions).all() or not np.isfinite(headings).all():
        raise ValueError("vehicle-body proxy inputs must be finite")
    interval_velocity = np.diff(positions, axis=0) / dt_s
    acceleration_world = np.diff(interval_velocity, axis=0) / dt_s
    corresponding_heading = headings[1:-1]
    c, s = np.cos(corresponding_heading), np.sin(corresponding_heading)
    longitudinal = acceleration_world[:, 0] * c + acceleration_world[:, 1] * s
    lateral = -acceleration_world[:, 0] * s + acceleration_world[:, 1] * c
    kernel = np.asarray(BOXCAR_KERNEL, dtype=np.float64)
    filtered_longitudinal = np.convolve(longitudinal, kernel, mode="valid")
    filtered_lateral = np.convolve(lateral, kernel, mode="valid")
    jerk_longitudinal = np.diff(filtered_longitudinal) / dt_s
    jerk_lateral = np.diff(filtered_lateral) / dt_s
    return {
        "status": "benchmark_only",
        "name": "vehicle_body_planar_kinematic_proxy",
        "sample_accounting": {
            "position_samples": 64,
            "interval_velocity_samples": int(interval_velocity.shape[0]),
            "raw_acceleration_samples": int(acceleration_world.shape[0]),
            "filtered_acceleration_samples": int(filtered_longitudinal.size),
            "filtered_jerk_samples": int(jerk_longitudinal.size),
            "padding_used": False,
        },
        "filtered_acceleration": {
            "longitudinal": _signed_summary(filtered_longitudinal),
            "lateral": _signed_summary(filtered_lateral),
            "longitudinal_deceleration": _unsigned_summary(
                np.maximum(0.0, -filtered_longitudinal)
            ),
            "duration_abs_gt_s": {
                _number_key(threshold): {
                    "longitudinal": float(
                        np.count_nonzero(np.abs(filtered_longitudinal) > threshold)
                        * dt_s
                    ),
                    "lateral": float(
                        np.count_nonzero(np.abs(filtered_lateral) > threshold) * dt_s
                    ),
                }
                for threshold in ACCELERATION_GRID_MPS2
            },
            "signed_deceleration_duration_lt_s": {
                _number_key(-threshold): float(
                    np.count_nonzero(filtered_longitudinal < -threshold) * dt_s
                )
                for threshold in ACCELERATION_GRID_MPS2
            },
        },
        "filtered_jerk": {
            "longitudinal": _jerk_summary(jerk_longitudinal),
            "lateral": _jerk_summary(jerk_lateral),
            "duration_abs_gt_s": {
                _number_key(threshold): {
                    "longitudinal": float(
                        np.count_nonzero(np.abs(jerk_longitudinal) > threshold) * dt_s
                    ),
                    "lateral": float(
                        np.count_nonzero(np.abs(jerk_lateral) > threshold) * dt_s
                    ),
                }
                for threshold in JERK_GRID_MPS3
            },
        },
        "not_modeled": [
            "seat_response",
            "occupant_response",
            "vertical_acceleration",
            "roll",
            "pitch",
            "ISO_2631",
            "SAE_J2834",
        ],
    }


def speed_endpoint(ticks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _ticks(ticks)
    excess: list[float] = []
    missing = 0
    for tick in ticks:
        safety = _mapping(tick, "safety")
        limit = safety.get("speed_limit_mps")
        if limit is None:
            missing += 1
            continue
        excess.append(
            max(0.0, _finite(safety["speed_mps"], "speed") - _positive(limit, "limit"))
        )
    if missing:
        return {
            "status": "evidence_missing",
            "missing_interval_count": missing,
            "required_interval_count": TICK_COUNT,
        }
    values = np.asarray(excess, dtype=np.float64)
    positives = values[values > 0.0]
    return {
        "status": "benchmark_only",
        "max_excess_mps": float(values.max()),
        "mean_positive_excess_mps": (
            float(positives.mean()) if positives.size else 0.0
        ),
        "tolerance_grid": {
            _number_key(tolerance): {
                "duration_s": float(np.count_nonzero(values > tolerance) * DT_S),
                "magnitude_duration_m": float(
                    np.maximum(0.0, values - tolerance).sum() * DT_S
                ),
            }
            for tolerance in SPEED_TOLERANCE_GRID_MPS
        },
    }


def latency_endpoint(ticks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    _ticks(ticks)
    stages = sorted(
        {str(stage) for tick in ticks for stage in _mapping(tick, "latency_ms")}
    )
    per_stage: dict[str, Any] = {}
    for stage in stages:
        values = [
            _finite(_mapping(tick, "latency_ms")[stage], f"latency.{stage}")
            for tick in ticks
            if stage in _mapping(tick, "latency_ms")
        ]
        per_stage[stage] = (
            _distribution(np.asarray(values, dtype=np.float64))
            if len(values) == TICK_COUNT
            else {
                "status": "evidence_missing",
                "available_count": len(values),
                "required_count": TICK_COUNT,
            }
        )
    total = np.asarray(
        [
            _finite(
                _mapping(tick, "latency_ms").get("total_planning"),
                "latency.total_planning",
            )
            for tick in ticks
        ],
        dtype=np.float64,
    )
    return {
        "status": "benchmark_only",
        "stages": per_stage,
        "total": _distribution(total),
        "deadline_grid": {
            _number_key(deadline): {
                "exceedance_rate": float(
                    np.count_nonzero(total > deadline) / TICK_COUNT
                ),
                "max_exceedance_ms": float(np.maximum(0.0, total - deadline).max()),
                "label": (
                    "hypothetical_10Hz_budget"
                    if deadline == 100.0
                    else "project_sensitivity"
                ),
            }
            for deadline in LATENCY_DEADLINE_GRID_MS
        },
        "production_deadline_certification": "evidence_missing",
    }


def candidate0_supplementary_equivalence(
    primary: Mapping[str, Any], supplementary: Mapping[str, Any]
) -> dict[str, Any]:
    if type(primary) is not dict or type(supplementary) is not dict:
        raise ValueError("candidate0 equivalence inputs must be objects")
    header_fields = (
        "route_sha256",
        "logical_map_sha256",
        "fixed_dp_head",
        "checkpoint_sha256",
        "args_sha256",
        "scenario_seed",
        "spawn_config_sha256",
        "initial_state_sha256",
        "initial_input_sha256",
    )
    if any(primary.get(name) != supplementary.get(name) for name in header_fields):
        return {"equivalent": False, "reason": "header_drift"}
    primary_ticks = primary.get("ticks")
    supplementary_ticks = supplementary.get("ticks")
    if (
        type(primary_ticks) is not list
        or type(supplementary_ticks) is not list
        or len(primary_ticks) != TICK_COUNT
        or len(supplementary_ticks) != TICK_COUNT
    ):
        return {"equivalent": False, "reason": "tick_denominator_drift"}
    for index, (left, right) in enumerate(
        zip(primary_ticks, supplementary_ticks, strict=True)
    ):
        if (
            left.get("tick_index") != index
            or right.get("tick_index") != index
            or left.get("input_sha256") != right.get("input_sha256")
            or left.get("default_output_sha256") != right.get("default_output_sha256")
            or left.get("selected_trajectory_sha256")
            != right.get("selected_trajectory_sha256")
            or left.get("selected_index") != 0
            or right.get("selected_index") != 0
        ):
            return {"equivalent": False, "reason": f"action_binding_drift_at_{index}"}
        left_safety = left.get("safety")
        right_safety = right.get("safety")
        if type(left_safety) is not dict or type(right_safety) is not dict:
            return {"equivalent": False, "reason": f"safety_missing_at_{index}"}
        for name in (
            "position_xy",
            "speed_mps",
            "ego_heading_rad",
            "route_heading_rad",
            "route_progress_m",
            "signal_phase_at_interval_start",
            "certified_signal_stop_lines",
            "speed_limit_mps",
        ):
            if left_safety.get(name) != right_safety.get(name):
                return {
                    "equivalent": False,
                    "reason": f"ego_or_source_drift_{name}_at_{index}",
                }
        controlled = right.get("controlled_scene")
        if (
            type(controlled) is not dict
            or controlled.get("tick_index") != index
            or controlled.get("outcome_fields_consumed") != []
            or controlled.get("candidate_tensor_consumed") is not False
            or controlled.get("selected_trajectory_consumed") is not False
        ):
            return {
                "equivalent": False,
                "reason": f"controlled_source_drift_at_{index}",
            }
    return {
        "equivalent": True,
        "reason": None,
        "tick_count": TICK_COUNT,
        "proof_fields": [
            *header_fields,
            "tick_index",
            "input_sha256",
            "default_output_sha256",
            "selected_trajectory_sha256",
            "selected_index",
            "safety.position_xy",
            "safety.speed_mps",
            "safety.ego_heading_rad",
            "safety.route_heading_rad",
            "safety.route_progress_m",
            "safety.signal_phase_at_interval_start",
            "safety.certified_signal_stop_lines",
            "safety.speed_limit_mps",
            "controlled_scene.source_nonconsumption",
        ],
    }


def summarize_run_v2(
    *,
    native_receipt: Mapping[str, Any],
    evaluation_row: Mapping[str, Any],
    run_config: Mapping[str, Any],
    geometry: Mapping[str, Any],
    supplementary_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if any(
        type(value) is not dict
        for value in (native_receipt, evaluation_row, run_config, geometry)
    ):
        raise ValueError("Evaluation v2 run inputs must be objects")
    ticks = native_receipt.get("ticks")
    _ticks(ticks)
    arm = evaluation_row.get("arm")
    if arm not in ARMS or evaluation_row.get("status") != "complete":
        raise ValueError("Evaluation v2 frozen evaluation-row identity drifted")
    config_runtime = _mapping(run_config, "signal_complete_runtime")
    case = _mapping(config_runtime, "case")
    actors = case.get("actors")
    if type(actors) is not list:
        raise ValueError("Evaluation v2 actor inventory drifted")
    spawn = _mapping(run_config, "spawn_config")
    ego_length = _positive(spawn.get("ego_length"), "ego_length")
    ego_width = _positive(spawn.get("ego_width"), "ego_width")
    ego_wheelbase = _positive(spawn.get("ego_wheelbase"), "ego_wheelbase")
    positions = np.asarray(
        [_mapping(tick, "safety")["position_xy"] for tick in ticks],
        dtype=np.float64,
    )
    headings = np.asarray(
        [_mapping(tick, "safety")["ego_heading_rad"] for tick in ticks],
        dtype=np.float64,
    )
    speeds = np.asarray(
        [_mapping(tick, "safety")["speed_mps"] for tick in ticks],
        dtype=np.float64,
    )
    actor_source_ticks: Sequence[Mapping[str, Any]] | None
    equivalence: dict[str, Any] | None = None
    if not actors:
        actor_source_ticks = []
    elif arm == "candidate0":
        if supplementary_receipt is None:
            actor_source_ticks = None
            equivalence = {
                "equivalent": False,
                "reason": "supplementary_receipt_missing",
            }
        else:
            equivalence = candidate0_supplementary_equivalence(
                native_receipt, supplementary_receipt
            )
            actor_source_ticks = (
                supplementary_receipt["ticks"]
                if equivalence["equivalent"] is True
                else None
            )
    else:
        actor_source_ticks = ticks
    actor_specs = {str(row["id"]): row for row in actors}
    collision, proximity = _collision_and_proximity(
        ticks=ticks,
        actor_source_ticks=actor_source_ticks,
        actor_specs=actor_specs,
        ego_length=ego_length,
        ego_width=ego_width,
        ego_wheelbase=ego_wheelbase,
    )
    road = _road_endpoint(
        ticks,
        geometry.get("drivable_polygons"),
        ego_length=ego_length,
        ego_width=ego_width,
        ego_wheelbase=ego_wheelbase,
    )
    red = _red_endpoint(
        ticks,
        actor_source_ticks,
        ego_width=ego_width,
        initial_heading_rad=_finite(
            geometry.get("initial_heading_rad"), "initial heading"
        ),
    )
    route = stateful_route_projection(
        positions,
        speeds,
        geometry.get("route_segments"),
    )
    goal = _goal_endpoint(
        positions,
        headings,
        geometry.get("goal_pose"),
        _positive(spawn.get("goal_tolerance_m"), "goal tolerance"),
        _positive(spawn.get("goal_pass_window_m"), "goal pass window"),
        _mapping(native_receipt, "native_result"),
    )
    if route.get("substatus") == "computed":
        route["geometry_source_sha256"] = _sha(
            geometry.get("route_geometry_sha256"), "route geometry SHA"
        )
    if road.get("status") == "benchmark_only":
        road["geometry_source_sha256"] = _sha(
            geometry.get("map_geometry_sha256"), "map geometry SHA"
        )
    return {
        "pair_key": _nonempty(evaluation_row.get("pair_key"), "pair_key"),
        "arm": arm,
        "inference_cluster_id": _nonempty(
            evaluation_row.get("inference_cluster_id"), "inference_cluster_id"
        ),
        "benchmark_stratum": _nonempty(
            evaluation_row.get("benchmark_stratum"), "benchmark_stratum"
        ),
        "scenario_family": _nonempty(
            evaluation_row.get("scenario_family"), "scenario_family"
        ),
        "source_class": _nonempty(evaluation_row.get("source_class"), "source_class"),
        "source_receipt_sha256": canonical_sha256(native_receipt),
        "run_config_sha256": canonical_sha256(run_config),
        "candidate0_supplementary_equivalence": equivalence,
        "endpoints": {
            "collision": collision,
            "dynamic_proximity": proximity,
            "road_containment": road,
            "certified_red_crossing": red,
            "speed": speed_endpoint(ticks),
            "route": route,
            "goal": goal,
            "vehicle_body_planar_kinematic_proxy": (
                vehicle_body_planar_kinematic_proxy(positions, headings)
            ),
            "latency": latency_endpoint(ticks),
        },
        "missing_evidence": {
            "collision_severity": "evidence_missing",
            "PET": "evidence_missing",
            "seat_occupant_vertical_roll_pitch": "evidence_missing",
            "production_latency_certification": "evidence_missing",
        },
    }


def build_evaluation_v2_result(
    run_summaries: Sequence[Mapping[str, Any]],
    *,
    bindings: Mapping[str, Any],
    contract_root_sha256: str,
    contract_review_root_sha256: str,
    legacy_evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    runs = [copy.deepcopy(row) for row in run_summaries]
    if len(runs) != 1500:
        raise ValueError("Evaluation v2 requires 1500 run summaries")
    pairs: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in runs:
        pair = _nonempty(row.get("pair_key"), "pair_key")
        arm = row.get("arm")
        if arm not in ARMS or arm in pairs[pair]:
            raise ValueError("Evaluation v2 pair/arm denominator drifted")
        pairs[pair][arm] = row
    if len(pairs) != 500 or any(set(row) != set(ARMS) for row in pairs.values()):
        raise ValueError("Evaluation v2 full paired denominator drifted")
    contract = evaluation_v2_contract()
    endpoint_vector: dict[str, Any] = {}
    ordered_pairs = [pairs[key] for key in sorted(pairs)]
    for endpoint_name, catalog in contract["endpoint_catalog"].items():
        per_run = [
            {
                "pair_key": row["pair_key"],
                "arm": row["arm"],
                "status": row["endpoints"][endpoint_name]["status"],
                "per_run_value": row["endpoints"][endpoint_name],
                "source_sha256": row["source_receipt_sha256"],
            }
            for row in runs
        ]
        status_counts: dict[str, int] = defaultdict(int)
        for row in per_run:
            status_counts[row["status"]] += 1
        full = all(row["status"] in {"computed", "benchmark_only"} for row in per_run)
        endpoint_vector[endpoint_name] = {
            "formula": catalog["formula"],
            "units": catalog["units"],
            "source_root_sha256": EXECUTION_ROOT,
            "evidence_class": catalog["evidence_class"],
            "denominator": {
                "required_arm_count": 1500,
                "available_arm_count": sum(
                    count
                    for status, count in status_counts.items()
                    if status in {"computed", "benchmark_only"}
                ),
                "missing_arm_count": sum(
                    count
                    for status, count in status_counts.items()
                    if status not in {"computed", "benchmark_only"}
                ),
                "status_counts": dict(sorted(status_counts.items())),
            },
            "opportunity": _endpoint_opportunity(endpoint_name, per_run),
            "per_run_values": per_run,
            "aggregate": _endpoint_aggregate(
                endpoint_name, ordered_pairs, full_denominator=full
            ),
            "status": "benchmark_only" if full else "evidence_missing",
        }
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": "sealed_exploratory_evaluation_v2",
        "benchmark": "fresh_b4",
        "result_semantics": "exploratory_posthoc_not_claim_authorizing",
        "bindings": dict(bindings),
        "contract_root_sha256": _sha(contract_root_sha256, "contract root"),
        "contract_review_root_sha256": _sha(
            contract_review_root_sha256, "contract review root"
        ),
        "denominator": contract["denominator"],
        "endpoint_vector": endpoint_vector,
        "run_summary_inventory_sha256": canonical_sha256(runs),
        "legacy_benchmark_v1": {
            "source_root_sha256": CORRECTED_EVALUATION_ROOT,
            "evaluation_sha256": canonical_sha256(legacy_evaluation),
            "evaluation": copy.deepcopy(legacy_evaluation),
            "values_mutated": False,
            "values_recomputed": False,
            "legacy_claim_changed": False,
            "legacy_safetycost_is_v2_score": False,
        },
        "sample_accounting": {
            "pairs": 500,
            "arms": 1500,
            "ticks": 96000,
            "body_proxy": "64_to_63_to_62_to_52_to_51",
            "per_run_before_pairing_and_clustering": True,
            "ticks_seeds_or_arms_independent": False,
        },
        "claim_invariance": {
            "v2_scientific_hard_gate": "not_prospectively_defined_for_v2",
            "v2_claim_authorized": False,
            "fresh_benefit_claim_authorized": False,
            "industrial_claim_authorized": False,
            "legacy_claim_changed": False,
            "final_legacy_claim": "honest_no_claim_under_frozen_preregistered_all_gate",
        },
        "execution_written": False,
        "corrected_evaluation_written": False,
        "scientific_or_continuation_cas_written": False,
        "fresh_execution_rerun": False,
        "corrected_evaluation_rerun": False,
    }


def _collision_and_proximity(
    *,
    ticks: Sequence[Mapping[str, Any]],
    actor_source_ticks: Sequence[Mapping[str, Any]] | None,
    actor_specs: Mapping[str, Mapping[str, Any]],
    ego_length: float,
    ego_width: float,
    ego_wheelbase: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if actor_source_ticks is None:
        missing = {
            "status": "evidence_missing",
            "reason": "candidate0_supplementary_primary_equivalence_not_proven",
        }
        return copy.deepcopy(missing), copy.deepcopy(missing)
    collision_mask: list[bool] = []
    min_clearance: list[float] = []
    min_ttc: list[float | None] = []
    max_closing: list[float] = []
    max_drac: list[float | None] = []
    actor_opportunity_count = 0
    for index, tick in enumerate(ticks):
        safety = _mapping(tick, "safety")
        position = _finite_vector(safety["position_xy"], 2, "ego position")
        heading = _finite(safety["ego_heading_rad"], "ego heading")
        speed = _finite(safety["speed_mps"], "ego speed")
        ego_velocity = speed * np.asarray([math.cos(heading), math.sin(heading)])
        ego_polygon = obb_polygon(
            position,
            heading,
            ego_length,
            ego_width,
            wheelbase_m=ego_wheelbase,
        )
        if actor_source_ticks == []:
            actor_rows: list[Mapping[str, Any]] = []
        else:
            source = actor_source_ticks[index]
            actor_rows = _mapping(source, "controlled_scene").get("actors")
            if type(actor_rows) is not list:
                raise ValueError("Evaluation v2 controlled actor rows drifted")
        tick_rows: list[dict[str, Any]] = []
        for actor in actor_rows:
            actor_id = str(actor.get("id"))
            spec = actor_specs.get(actor_id)
            if type(spec) is not dict:
                raise ValueError("Evaluation v2 controlled actor geometry is missing")
            actor_polygon = obb_polygon(
                actor["position_xy"],
                actor["heading_rad"],
                spec["length_m"],
                spec["width_m"],
                wheelbase_m=spec.get("wheelbase_m"),
            )
            tick_rows.append(
                dynamic_pair_tick(
                    ego_polygon=ego_polygon,
                    actor_polygon=actor_polygon,
                    ego_position_xy=position,
                    actor_position_xy=actor["position_xy"],
                    ego_velocity_xy_mps=ego_velocity,
                    actor_velocity_xy_mps=actor["velocity_xy_mps"],
                )
            )
        actor_opportunity_count += len(tick_rows)
        collision_mask.append(any(row["collision"] for row in tick_rows))
        min_clearance.append(
            min((row["clearance_m"] for row in tick_rows), default=math.inf)
        )
        finite_ttc = [
            row["geometry_ttc_s"]
            for row in tick_rows
            if row["geometry_ttc_s"] is not None and not row["collision"]
        ]
        min_ttc.append(min(finite_ttc) if finite_ttc else None)
        max_closing.append(max((row["closing_mps"] for row in tick_rows), default=0.0))
        finite_drac = [
            row["drac_mps2"] for row in tick_rows if row["drac_mps2"] is not None
        ]
        max_drac.append(max(finite_drac) if finite_drac else None)
    collision = {
        "status": "benchmark_only",
        "collision_any": any(collision_mask),
        "episode_count": _episode_count(collision_mask),
        "duration_s": float(sum(collision_mask) * DT_S),
        "collision_severity": "evidence_missing",
        "kinematic_relative_speed_proxy_is_severity": False,
    }
    clearance_array = np.asarray(min_clearance, dtype=np.float64)
    finite_clearance = clearance_array[np.isfinite(clearance_array)]
    ttc_values = np.asarray(
        [math.inf if value is None else value for value in min_ttc],
        dtype=np.float64,
    )
    closing_values = np.asarray(max_closing, dtype=np.float64)
    drac_values = np.asarray(
        [0.0 if value is None else value for value in max_drac],
        dtype=np.float64,
    )
    proximity = {
        "status": "benchmark_only",
        "actor_tick_opportunity_count": actor_opportunity_count,
        "min_clearance_m": (
            float(finite_clearance.min()) if finite_clearance.size else None
        ),
        "min_finite_geometry_ttc_s": (
            float(ttc_values[np.isfinite(ttc_values)].min())
            if np.isfinite(ttc_values).any()
            else None
        ),
        "max_closing_mps": float(closing_values.max()),
        "max_drac_mps2": float(drac_values.max()),
        "clearance_grid": _duration_episode_grid(
            clearance_array, CLEARANCE_GRID_M, comparison="le"
        ),
        "geometry_ttc_grid": _duration_episode_grid(
            ttc_values, TTC_GRID_S, comparison="le"
        ),
        "closing_grid": _duration_episode_grid(
            closing_values, CLOSING_GRID_MPS, comparison="ge"
        ),
        "drac_grid": _duration_episode_grid(
            drac_values, DRAC_GRID_MPS2, comparison="ge"
        ),
        "stationary_proximity_is_dynamic_risk": False,
        "point_cv_proxy_used_as_geometry_ttc": False,
        "geometry_ttc_approach_condition": "centroid dot(r,v_rel)<0",
        "geometry_ttc_prediction_horizon_s": GEOMETRY_TTC_HORIZON_S,
        "geometry_ttc_horizon_classification": (
            "project_descriptive_not_industrial_gate"
        ),
        "ego_velocity_source": (
            "same_tick_scalar_speed_times_heading_kinematic_reconstruction"
        ),
        "PET": "evidence_missing",
    }
    return collision, proximity


def _road_endpoint(
    ticks: Sequence[Mapping[str, Any]],
    drivable_polygons: Any,
    *,
    ego_length: float,
    ego_width: float,
    ego_wheelbase: float,
) -> dict[str, Any]:
    if drivable_polygons is None or (
        type(drivable_polygons) is list and not drivable_polygons
    ):
        return {
            "status": "requires_future_nonholdout_acquisition",
            "reason": "root_bound_drivable_polygon_union_missing",
            "five_point_proxy_used": False,
        }
    if type(drivable_polygons) is not list:
        raise ValueError("Evaluation v2 drivable polygon inventory drifted")
    drivable = [_polygon(row, "drivable_polygon") for row in drivable_polygons]
    boundary = _union_boundary_segments(drivable)
    if not boundary:
        raise ValueError("drivable polygon union has no determinate boundary")
    values = []
    signed_clearances = []
    penetrations = []
    boundary_segment_counts = []
    for tick in ticks:
        safety = _mapping(tick, "safety")
        footprint = obb_polygon(
            safety["position_xy"],
            safety["ego_heading_rad"],
            ego_length,
            ego_width,
            wheelbase_m=ego_wheelbase,
        )
        normalized_footprint = _polygon(footprint, "footprint")
        values.append(
            float(
                np.clip(
                    1.0
                    - _convex_union_intersection_area(
                        normalized_footprint, drivable
                    )
                    / _polygon_area(normalized_footprint),
                    0.0,
                    1.0,
                )
            )
        )
        boundary_metric = _road_signed_boundary_metrics_normalized(
            normalized_footprint, drivable, boundary
        )
        signed_clearances.append(
            boundary_metric["minimum_signed_boundary_clearance_m"]
        )
        penetrations.append(boundary_metric["maximum_boundary_penetration_m"])
        boundary_segment_counts.append(
            boundary_metric["union_boundary_segment_count"]
        )
    if len(set(boundary_segment_counts)) != 1:
        raise ValueError("drivable union boundary segment count drifted within run")
    array = np.asarray(values, dtype=np.float64)
    mask = array > GEOM_EPS
    return {
        "status": "benchmark_only",
        "offroad_any": bool(mask.any()),
        "duration_s": float(mask.sum() * DT_S),
        "episode_count": _episode_count(mask.tolist()),
        "max_outside_fraction": float(array.max()),
        "geom_eps": GEOM_EPS,
        "five_point_proxy_used": False,
        "signed_boundary_clearance_or_penetration": {
            "status": "computed",
            "minimum_signed_boundary_clearance_m": float(
                np.min(np.asarray(signed_clearances, dtype=np.float64))
            ),
            "maximum_boundary_penetration_m": float(
                np.max(np.asarray(penetrations, dtype=np.float64))
            ),
            "union_boundary_segment_count": int(boundary_segment_counts[0]),
            "internal_overlap_or_adjacency_seams_are_boundary": False,
            "probe_epsilon_m": UNION_BOUNDARY_PROBE_EPS_M,
            "units": "m",
        },
    }


def _red_endpoint(
    ticks: Sequence[Mapping[str, Any]],
    actor_source_ticks: Sequence[Mapping[str, Any]] | None,
    *,
    ego_width: float,
    initial_heading_rad: float,
) -> dict[str, Any]:
    opportunities = 0
    red_intervals = 0
    crossing_count = 0
    legacy_over_0_5_count = 0
    crossing_speeds: list[float] = []
    ambiguity_count = 0
    seen_identities: set[str] = set()
    for index, tick in enumerate(ticks):
        safety = _mapping(tick, "safety")
        phase = safety.get("signal_phase_at_interval_start")
        lines = safety.get("certified_signal_stop_lines")
        if phase != "red" or type(lines) is not list or not lines:
            continue
        red_intervals += 1
        identities = [_stop_line_identity(line) for line in lines]
        if actor_source_ticks not in (None, []):
            controlled = _mapping(actor_source_ticks[index], "controlled_scene")
            source = _mapping(_mapping(controlled, "signal"), "source_receipt")
            stop_id = source.get("certified_stop_line_id")
            if type(stop_id) is str and stop_id:
                identities = [stop_id]
        for identity in identities:
            if identity not in seen_identities:
                opportunities += 1
                seen_identities.add(identity)
        previous_heading = (
            initial_heading_rad
            if index == 0
            else _finite(
                _mapping(ticks[index - 1], "safety")["ego_heading_rad"],
                "previous heading",
            )
        )
        current_heading = _finite(safety["ego_heading_rad"], "current heading")
        start_edge = _front_edge_from_center(
            safety["front_center_prev_xy"], previous_heading, ego_width
        )
        end_edge = _front_edge_from_center(
            safety["front_center_xy"], current_heading, ego_width
        )
        results = [
            swept_front_edge_crossing(start_edge, end_edge, line) for line in lines
        ]
        if any(result["status"] == "ambiguous_evidence_missing" for result in results):
            ambiguity_count += 1
            continue
        crossings = [result for result in results if result["crossing"] is True]
        if len(crossings) > 1:
            ambiguity_count += 1
            continue
        if crossings:
            alpha = crossings[0]["alpha"]
            speed = _finite(safety["pre_decision_speed_mps"], "pre speed") + alpha * (
                _finite(safety["speed_mps"], "post speed")
                - _finite(safety["pre_decision_speed_mps"], "pre speed")
            )
            crossing_count += 1
            crossing_speeds.append(float(speed))
            if speed > 0.5:
                legacy_over_0_5_count += 1
    if ambiguity_count:
        return {
            "status": "ambiguous_evidence_missing",
            "maps_to_status": "evidence_missing",
            "red_opportunity_count": opportunities,
            "red_phase_interval_count": red_intervals,
            "ambiguous_interval_count": ambiguity_count,
            "unthresholded_crossing_count": None,
        }
    return {
        "status": "benchmark_only",
        "red_opportunity_count": opportunities,
        "red_phase_interval_count": red_intervals,
        "unthresholded_crossing_count": crossing_count,
        "unthresholded_crossing_any": crossing_count > 0,
        "crossing_speed_mps": crossing_speeds,
        "legacy_gt_0_5mps_crossing_count": legacy_over_0_5_count,
        "future_phase_consumed": False,
    }


def _goal_endpoint(
    positions: np.ndarray,
    headings: np.ndarray,
    goal_pose: Any,
    tolerance_m: float,
    pass_window_m: float,
    native_result: Mapping[str, Any],
) -> dict[str, Any]:
    goal = _finite_vector(goal_pose, 3, "goal pose")
    distances = np.linalg.norm(positions - goal[:2], axis=1)
    reached = bool(np.any(distances <= tolerance_m))
    passed = False
    for position, heading, distance in zip(positions, headings, distances, strict=True):
        forward = np.asarray([math.cos(float(heading)), math.sin(float(heading))])
        if (
            float(np.dot(goal[:2] - position, forward)) < 0.0
            and float(distance) <= pass_window_m
        ):
            passed = True
            break
    reconstructed = reached or passed
    native_goal = native_result.get("goal_reached")
    native_reason = native_result.get("reason")
    if type(native_goal) is not bool or type(native_reason) is not str:
        raise ValueError("native goal result drifted")
    return {
        "status": "benchmark_only",
        "goal_pose": goal.tolist(),
        "goal_tolerance_m": tolerance_m,
        "goal_pass_window_m": pass_window_m,
        "minimum_goal_distance_m": float(distances.min()),
        "goal_reached_by_literal_tolerance": reached,
        "goal_passed_by_literal_heading_and_window": passed,
        "goal_pass_uses_same_tick_distance_and_heading": True,
        "historical_minimum_coupled_to_later_heading_used": False,
        "reconstructed_goal_reached_or_passed": reconstructed,
        "native_goal_reached": native_goal,
        "native_reason": native_reason,
        "native_literal_semantics_bound": True,
    }


def _endpoint_aggregate(
    endpoint_name: str,
    pairs: Sequence[Mapping[str, Mapping[str, Any]]],
    *,
    full_denominator: bool,
) -> dict[str, Any]:
    if not full_denominator:
        return {
            "status": "evidence_missing",
            "paired_inference": "cancelled_missing_full_paired_denominator",
            "complete_case_shrinkage_used": False,
        }
    path_sets = []
    for pair in pairs:
        for arm in ARMS:
            path_sets.append(
                set(
                    _numeric_paths(
                        pair[arm]["endpoints"][endpoint_name],
                        prefix="",
                    )
                )
            )
    common_paths = sorted(set.intersection(*path_sets)) if path_sets else []
    directions = {
        path: _scalar_direction(endpoint_name, path) for path in common_paths
    }
    arm_means: dict[str, dict[str, float]] = {}
    paired: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        arm_means[arm] = {
            path: float(
                np.mean(
                    [
                        _path_number(pair[arm]["endpoints"][endpoint_name], path)
                        for pair in pairs
                    ]
                )
            )
            for path in common_paths
        }
    for method in METHOD_ARMS:
        paired[method] = {}
        clusters = [pair[method]["inference_cluster_id"] for pair in pairs]
        for path in common_paths:
            deltas = [
                _path_number(pair[method]["endpoints"][endpoint_name], path)
                - _path_number(pair["candidate0"]["endpoints"][endpoint_name], path)
                for pair in pairs
            ]
            paired[method][path] = clustered_paired_descriptive(
                deltas,
                clusters,
                direction=directions[path],
            )
    return {
        "status": "benchmark_only",
        "descriptive_scalar_paths": common_paths,
        "scalar_path_directions": directions,
        "arm_means": arm_means,
        "paired_cluster_summaries": paired,
        "claim_authorized": False,
    }


def _endpoint_opportunity(
    endpoint_name: str, per_run: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    field = {
        "dynamic_proximity": "actor_tick_opportunity_count",
        "certified_red_crossing": "red_opportunity_count",
    }.get(endpoint_name)
    if field is None:
        return {"definition": "one complete 64-tick run", "required_count": 1500}
    values = [
        row["per_run_value"].get(field)
        for row in per_run
        if type(row["per_run_value"].get(field)) in {int, float}
    ]
    return {
        "definition": field,
        "available_run_count": len(values),
        "total_opportunity_count": float(sum(values)),
    }


def _numeric_paths(value: Any, *, prefix: str) -> list[str]:
    result: list[str] = []
    if type(value) is dict:
        for name in sorted(value):
            if name in {
                "status",
                "substatus",
                "maps_to_status",
                "reason",
                "name",
                "not_modeled",
                "crossing_speed_mps",
                "s_t_m",
                "goal_pose",
                "geometry_source_sha256",
            }:
                continue
            token = str(name).replace("~", "~0").replace("/", "~1")
            path = f"{prefix}/{token}"
            result.extend(_numeric_paths(value[name], prefix=path))
    elif type(value) in {int, float, bool} and math.isfinite(float(value)):
        result.append(prefix)
    return result


def _path_number(value: Mapping[str, Any], path: str) -> float:
    current: Any = value
    if not path.startswith("/"):
        raise ValueError(f"Evaluation v2 scalar path is not JSON Pointer: {path}")
    for token in path.split("/")[1:]:
        name = token.replace("~1", "/").replace("~0", "~")
        current = current[name]
    if type(current) not in {int, float, bool} or not math.isfinite(float(current)):
        raise ValueError(f"Evaluation v2 scalar path drifted: {path}")
    return float(current)


def _duration_episode_grid(
    values: np.ndarray, thresholds: Sequence[float], *, comparison: str
) -> dict[str, Any]:
    result = {}
    for threshold in thresholds:
        if comparison == "le":
            mask = values <= threshold
        elif comparison == "ge":
            mask = values >= threshold
        else:
            raise ValueError("unsupported threshold comparison")
        result[_number_key(threshold)] = {
            "duration_s": float(mask.sum() * DT_S),
            "episode_count": _episode_count(mask.tolist()),
        }
    return result


def _episode_count(mask: Sequence[bool]) -> int:
    count = 0
    previous = False
    for value in mask:
        current = bool(value)
        if current and not previous:
            count += 1
        previous = current
    return count


def _front_edge_from_center(
    center_xy: Any, heading_rad: float, width_m: float
) -> np.ndarray:
    center = _finite_vector(center_xy, 2, "front center")
    normal = np.asarray([-math.sin(heading_rad), math.cos(heading_rad)])
    return np.asarray(
        [center - 0.5 * width_m * normal, center + 0.5 * width_m * normal],
        dtype=np.float64,
    )


def _stop_line_identity(line: Any) -> str:
    return canonical_sha256(_edge(line, "stop line").tolist())


def clustered_paired_descriptive(
    deltas: Sequence[float],
    cluster_ids: Sequence[str],
    *,
    direction: str = "descriptive_unclassified",
) -> dict[str, Any]:
    values = np.asarray(deltas, dtype=np.float64)
    if values.shape != (500,) or len(cluster_ids) != 500:
        raise ValueError("paired descriptive summary requires all 500 pairs")
    groups: dict[str, list[float]] = defaultdict(list)
    for value, cluster in zip(values, cluster_ids, strict=True):
        if type(cluster) is not str or not cluster:
            raise ValueError("cluster id drifted")
        groups[cluster].append(float(value))
    if len(groups) != 100 or any(len(rows) != 5 for rows in groups.values()):
        raise ValueError("independent cluster denominator drifted")
    means = np.asarray(
        [np.mean(groups[key]) for key in sorted(groups)], dtype=np.float64
    )
    mean = float(means.mean())
    standard_error = float(means.std(ddof=1) / math.sqrt(means.size))
    critical = float(student_t.ppf(0.975, df=means.size - 1))
    between = float(means.var(ddof=1))
    total = float(values.var(ddof=1))
    within = float(np.mean([np.var(groups[key], ddof=1) for key in sorted(groups)]))
    if direction not in {"lower", "higher", "descriptive_unclassified"}:
        raise ValueError("paired scalar direction drifted")
    result: dict[str, Any] = {
        "status": "benchmark_only",
        "estimator": "equal_mass_cluster_mean_student_t",
        "pair_count": 500,
        "cluster_count": 100,
        "mean_delta": mean,
        "ci95": [mean - critical * standard_error, mean + critical * standard_error],
        "between_variance": between,
        "total_variance": total,
        "within_variance": within,
        "variance_fields_are_not_better_tie_worse": True,
        "direction": direction,
        "claim_authorized": False,
    }
    if direction == "descriptive_unclassified":
        result["better_tie_worse"] = {
            "status": "descriptive_unclassified",
            "reason": "no_outcome_independent_natural_direction",
        }
    else:
        better = int(np.count_nonzero(values < 0.0 if direction == "lower" else values > 0.0))
        tie = int(np.count_nonzero(values == 0.0))
        worse = int(values.size - better - tie)
        result["better_tie_worse"] = {
            "status": "benchmark_only",
            "direction": direction,
            "tie_rule": "exact_zero_delta",
            "better": better,
            "tie": tie,
            "worse": worse,
            "sum": better + tie + worse,
        }
    return result


def _scalar_direction(endpoint_name: str, path: str) -> str:
    if endpoint_name == "collision":
        if path in {"/collision_any", "/duration_s", "/episode_count"}:
            return "lower"
        if path == "/kinematic_relative_speed_proxy_is_severity":
            return "descriptive_unclassified"
    elif endpoint_name == "dynamic_proximity":
        if path in {"/min_clearance_m", "/min_finite_geometry_ttc_s"}:
            return "higher"
        if path in {
            "/actor_tick_opportunity_count",
            "/geometry_ttc_prediction_horizon_s",
            "/point_cv_proxy_used_as_geometry_ttc",
            "/stationary_proximity_is_dynamic_risk",
        }:
            return "descriptive_unclassified"
        if _matches_grid_metric(
            path,
            {
                "clearance_grid": CLEARANCE_GRID_M,
                "geometry_ttc_grid": TTC_GRID_S,
                "closing_grid": CLOSING_GRID_MPS,
                "drac_grid": DRAC_GRID_MPS2,
            },
            {"duration_s", "episode_count"},
        ) or path in {"/max_closing_mps", "/max_drac_mps2"}:
            return "lower"
    elif endpoint_name == "road_containment":
        if path in {
            "/duration_s",
            "/episode_count",
            "/max_outside_fraction",
            "/offroad_any",
            (
                "/signed_boundary_clearance_or_penetration/"
                "maximum_boundary_penetration_m"
            ),
        }:
            return "lower"
        if path == (
            "/signed_boundary_clearance_or_penetration/"
            "minimum_signed_boundary_clearance_m"
        ):
            return "higher"
        if path in {
            "/five_point_proxy_used",
            "/geom_eps",
            (
                "/signed_boundary_clearance_or_penetration/"
                "internal_overlap_or_adjacency_seams_are_boundary"
            ),
            "/signed_boundary_clearance_or_penetration/probe_epsilon_m",
            "/signed_boundary_clearance_or_penetration/union_boundary_segment_count",
        }:
            return "descriptive_unclassified"
    elif endpoint_name == "certified_red_crossing":
        if path in {
            "/unthresholded_crossing_count",
            "/unthresholded_crossing_any",
            "/legacy_gt_0_5mps_crossing_count",
        }:
            return "lower"
        if path in {
            "/red_opportunity_count",
            "/red_phase_interval_count",
            "/future_phase_consumed",
        }:
            return "descriptive_unclassified"
    elif endpoint_name == "speed":
        if path in {"/max_excess_mps", "/mean_positive_excess_mps"} or (
            _matches_grid_metric(
                path,
                {"tolerance_grid": SPEED_TOLERANCE_GRID_MPS},
                {"duration_s", "magnitude_duration_m"},
            )
        ):
            return "lower"
    elif endpoint_name == "route":
        if path in {"/backtracking_duration_s", "/backtracking_distance_m"}:
            return "lower"
        if path in {
            "/final_nearest_route_polyline_projection_m",
            "/net_m",
            "/max_forward_m",
            "/completion_fraction",
        }:
            return "higher"
        if path in {"/distance_traveled_m", "/route_length_m"}:
            return "descriptive_unclassified"
    elif endpoint_name == "goal":
        if path == "/minimum_goal_distance_m":
            return "lower"
        if path in {
            "/goal_reached_by_literal_tolerance",
            "/goal_passed_by_literal_heading_and_window",
            "/native_goal_reached",
            "/reconstructed_goal_reached_or_passed",
        }:
            return "higher"
        if path in {
            "/goal_tolerance_m",
            "/goal_pass_window_m",
            "/native_literal_semantics_bound",
            "/historical_minimum_coupled_to_later_heading_used",
            "/goal_pass_uses_same_tick_distance_and_heading",
        }:
            return "descriptive_unclassified"
    elif endpoint_name == "vehicle_body_planar_kinematic_proxy":
        if path.startswith("/sample_accounting/"):
            if path.rsplit("/", 1)[-1] in {
                "position_samples",
                "interval_velocity_samples",
                "raw_acceleration_samples",
                "filtered_acceleration_samples",
                "filtered_jerk_samples",
                "padding_used",
            }:
                return "descriptive_unclassified"
        signed_prefixes = (
            "/filtered_acceleration/longitudinal/",
            "/filtered_acceleration/lateral/",
        )
        if path.startswith(signed_prefixes):
            leaf = path.rsplit("/", 1)[-1]
            if leaf in {"signed_mean", "min", "max"}:
                return "descriptive_unclassified"
            if leaf in {"rms", "peak_abs", "abs_p50", "abs_p90", "abs_p95", "abs_p99"}:
                return "lower"
        if path.startswith("/filtered_acceleration/longitudinal_deceleration/"):
            if path.rsplit("/", 1)[-1] in {
                "mean",
                "rms",
                "max",
                "p50",
                "p90",
                "p95",
                "p99",
            }:
                return "lower"
        if path.startswith(
            "/filtered_acceleration/duration_abs_gt_s/"
        ) or path.startswith(
            "/filtered_acceleration/signed_deceleration_duration_lt_s/"
        ):
            return "lower"
        if path.startswith(
            (
                "/filtered_jerk/longitudinal/",
                "/filtered_jerk/lateral/",
            )
        ):
            if path.rsplit("/", 1)[-1] in {"rms", "peak_abs", "abs_p95"}:
                return "lower"
        if path.startswith("/filtered_jerk/duration_abs_gt_s/"):
            return "lower"
    elif endpoint_name == "latency":
        if path.startswith("/deadline_grid/"):
            if path.rsplit("/", 1)[-1] in {
                "exceedance_rate",
                "max_exceedance_ms",
            }:
                return "lower"
        if path.startswith("/stages/") or path.startswith("/total/"):
            leaf = path.rsplit("/", 1)[-1]
            if leaf == "count":
                return "descriptive_unclassified"
            if leaf in {"mean", "median", "p95", "p99", "max"}:
                return "lower"
    raise ValueError(
        f"unknown Evaluation v2 scalar direction path: {endpoint_name}{path}"
    )


def _matches_grid_metric(
    path: str,
    grids: Mapping[str, Sequence[float]],
    leaves: set[str],
) -> bool:
    parts = path.strip("/").split("/")
    if len(parts) != 3 or parts[0] not in grids or parts[2] not in leaves:
        return False
    return parts[1] in {_number_key(value) for value in grids[parts[0]]}


def _signed_summary(values: np.ndarray) -> dict[str, float]:
    array = _finite_array(values, "signed summary")
    absolute = np.abs(array)
    return {
        "signed_mean": float(array.mean()),
        "rms": float(np.sqrt(np.mean(array * array))),
        "min": float(array.min()),
        "max": float(array.max()),
        "peak_abs": float(absolute.max()),
        "abs_p50": float(np.percentile(absolute, 50)),
        "abs_p90": float(np.percentile(absolute, 90)),
        "abs_p95": float(np.percentile(absolute, 95)),
        "abs_p99": float(np.percentile(absolute, 99)),
    }


def _unsigned_summary(values: np.ndarray) -> dict[str, float]:
    array = _finite_array(values, "unsigned summary")
    return {
        "mean": float(array.mean()),
        "rms": float(np.sqrt(np.mean(array * array))),
        "max": float(array.max()),
        "p50": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)),
        "p95": float(np.percentile(array, 95)),
        "p99": float(np.percentile(array, 99)),
    }


def _jerk_summary(values: np.ndarray) -> dict[str, float]:
    array = _finite_array(values, "jerk summary")
    absolute = np.abs(array)
    return {
        "rms": float(np.sqrt(np.mean(array * array))),
        "peak_abs": float(absolute.max()),
        "abs_p95": float(np.percentile(absolute, 95)),
    }


def _distribution(values: np.ndarray) -> dict[str, Any]:
    array = _finite_array(values, "distribution")
    return {
        "status": "benchmark_only",
        "count": int(array.size),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "p95": float(np.percentile(array, 95)),
        "p99": float(np.percentile(array, 99)),
        "max": float(array.max()),
    }


def _route_segment(value: Mapping[str, Any], index: int) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "index",
        "start_xy",
        "end_xy",
        "arc_start_m",
        "arc_end_m",
        "next_indices",
    }:
        raise ValueError("route segment schema drifted")
    if value["index"] != index:
        raise ValueError("route segment index drifted")
    start = _finite_vector(value["start_xy"], 2, "route start")
    end = _finite_vector(value["end_xy"], 2, "route end")
    arc_start = _finite(value["arc_start_m"], "arc start")
    arc_end = _finite(value["arc_end_m"], "arc end")
    if arc_end <= arc_start or not math.isclose(
        float(np.linalg.norm(end - start)),
        arc_end - arc_start,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise ValueError("route segment arc drifted")
    next_indices = value["next_indices"]
    if type(next_indices) is not list or any(
        type(item) is not int for item in next_indices
    ):
        raise ValueError("route adjacency drifted")
    return {
        "index": index,
        "start_xy": start,
        "end_xy": end,
        "arc_start_m": arc_start,
        "arc_end_m": arc_end,
        "next_indices": tuple(next_indices),
    }


def _projection_candidates(
    point: np.ndarray, segments: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    result = []
    for segment in segments:
        start = segment["start_xy"]
        delta = segment["end_xy"] - start
        length_squared = float(np.dot(delta, delta))
        ratio = float(np.clip(np.dot(point - start, delta) / length_squared, 0.0, 1.0))
        projected = start + ratio * delta
        result.append(
            {
                "index": segment["index"],
                "s_m": float(
                    segment["arc_start_m"]
                    + ratio * (segment["arc_end_m"] - segment["arc_start_m"])
                ),
                "lateral_distance_m": float(np.linalg.norm(point - projected)),
            }
        )
    return result


def _ambiguous_route(reason: str) -> dict[str, Any]:
    return {
        "status": "ambiguous_evidence_missing",
        "maps_to_status": "evidence_missing",
        "reason": reason,
    }


def _segment_intersection_parameter(
    a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray
) -> float | None:
    r = b - a
    s = d - c
    denominator = float(r[0] * s[1] - r[1] * s[0])
    delta = c - a
    if abs(denominator) <= GEOM_EPS:
        return None
    t = float((delta[0] * s[1] - delta[1] * s[0]) / denominator)
    u = float((delta[0] * r[1] - delta[1] * r[0]) / denominator)
    if -GEOM_EPS <= t <= 1.0 + GEOM_EPS and -GEOM_EPS <= u <= 1.0 + GEOM_EPS:
        return float(np.clip(t, 0.0, 1.0))
    return None


def _ticks(value: Sequence[Mapping[str, Any]]) -> None:
    if type(value) is not list or len(value) != TICK_COUNT:
        raise ValueError("Evaluation v2 requires exactly 64 ticks")
    if any(
        type(row) is not dict or row.get("tick_index") != index
        for index, row in enumerate(value)
    ):
        raise ValueError("Evaluation v2 tick identity drifted")


def _mapping(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    result = value.get(name)
    if type(result) is not dict:
        raise ValueError(f"{name} must be an object")
    return result


def _finite(value: Any, label: str) -> float:
    if (
        type(value) not in {int, float}
        or isinstance(value, bool)
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _positive(value: Any, label: str) -> float:
    result = _finite(value, label)
    if result <= 0.0:
        raise ValueError(f"{label} must be positive")
    return result


def _finite_vector(value: Any, size: int, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"{label} must have shape ({size},) and be finite")
    return result


def _finite_array(value: Any, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64).reshape(-1)
    if not result.size or not np.isfinite(result).all():
        raise ValueError(f"{label} must be nonempty and finite")
    return result


def _vertices(value: Any, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if (
        result.ndim != 2
        or result.shape[0] < 3
        or result.shape[1] != 2
        or not np.isfinite(result).all()
    ):
        raise ValueError(f"{label} must be finite polygon vertices")
    return result


def _polygon(value: Any, label: str) -> np.ndarray:
    result = _vertices(value, label)
    if (
        _polygon_self_intersects(result)
        or abs(_signed_polygon_area(result)) <= GEOM_EPS
        or not _polygon_is_convex(result)
    ):
        raise ValueError(f"{label} is not a valid convex polygon")
    if _signed_polygon_area(result) < 0.0:
        result = result[::-1].copy()
    return result


def _signed_polygon_area(vertices: np.ndarray) -> float:
    shifted = np.roll(vertices, -1, axis=0)
    return float(
        0.5 * np.sum(vertices[:, 0] * shifted[:, 1] - vertices[:, 1] * shifted[:, 0])
    )


def _polygon_area(vertices: np.ndarray) -> float:
    return abs(_signed_polygon_area(vertices))


def _polygon_is_convex(vertices: np.ndarray) -> bool:
    signs: list[float] = []
    for index in range(vertices.shape[0]):
        first = vertices[(index + 1) % vertices.shape[0]] - vertices[index]
        second = (
            vertices[(index + 2) % vertices.shape[0]]
            - vertices[(index + 1) % vertices.shape[0]]
        )
        cross = _cross_2d(first, second)
        if abs(cross) > GEOM_EPS:
            signs.append(cross)
    return bool(signs) and (
        all(value > 0.0 for value in signs) or all(value < 0.0 for value in signs)
    )


def _polygon_self_intersects(vertices: np.ndarray) -> bool:
    count = vertices.shape[0]
    for first in range(count):
        first_next = (first + 1) % count
        for second in range(first + 1, count):
            second_next = (second + 1) % count
            if first in {second, second_next} or first_next in {second, second_next}:
                continue
            if _segments_intersect(
                vertices[first],
                vertices[first_next],
                vertices[second],
                vertices[second_next],
            ):
                return True
    return False


def _cross_2d(first: np.ndarray, second: np.ndarray) -> float:
    return float(first[0] * second[1] - first[1] * second[0])


def _segments_intersect(
    first_start: np.ndarray,
    first_end: np.ndarray,
    second_start: np.ndarray,
    second_end: np.ndarray,
) -> bool:
    def orientation(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        return _cross_2d(b - a, c - a)

    def on_segment(a: np.ndarray, b: np.ndarray, point: np.ndarray) -> bool:
        return (
            min(a[0], b[0]) - GEOM_EPS <= point[0] <= max(a[0], b[0]) + GEOM_EPS
            and min(a[1], b[1]) - GEOM_EPS <= point[1] <= max(a[1], b[1]) + GEOM_EPS
            and abs(orientation(a, b, point)) <= GEOM_EPS
        )

    values = (
        orientation(first_start, first_end, second_start),
        orientation(first_start, first_end, second_end),
        orientation(second_start, second_end, first_start),
        orientation(second_start, second_end, first_end),
    )
    if values[0] * values[1] < -GEOM_EPS and values[2] * values[3] < -GEOM_EPS:
        return True
    return (
        on_segment(first_start, first_end, second_start)
        or on_segment(first_start, first_end, second_end)
        or on_segment(second_start, second_end, first_start)
        or on_segment(second_start, second_end, first_end)
    )


def _convex_polygons_intersect(first: np.ndarray, second: np.ndarray) -> bool:
    for polygon in (first, second):
        for index in range(polygon.shape[0]):
            edge = polygon[(index + 1) % polygon.shape[0]] - polygon[index]
            axis = np.asarray([-edge[1], edge[0]], dtype=np.float64)
            first_projection = first @ axis
            second_projection = second @ axis
            if (
                float(first_projection.max())
                < float(second_projection.min()) - GEOM_EPS
                or float(second_projection.max())
                < float(first_projection.min()) - GEOM_EPS
            ):
                return False
    return True


def _point_segment_distance(
    point: np.ndarray, start: np.ndarray, end: np.ndarray
) -> float:
    delta = end - start
    denominator = float(np.dot(delta, delta))
    if denominator <= GEOM_EPS:
        return float(np.linalg.norm(point - start))
    ratio = float(np.clip(np.dot(point - start, delta) / denominator, 0.0, 1.0))
    return float(np.linalg.norm(point - (start + ratio * delta)))


def _segment_intersects_polygon(
    start: np.ndarray, end: np.ndarray, polygon: np.ndarray
) -> bool:
    if _point_in_convex_polygon(start, polygon) or _point_in_convex_polygon(
        end, polygon
    ):
        return True
    return any(
        _segments_intersect(
            start,
            end,
            polygon[index],
            polygon[(index + 1) % polygon.shape[0]],
        )
        for index in range(polygon.shape[0])
    )


def _point_in_convex_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
    return all(
        _cross_2d(
            polygon[(index + 1) % polygon.shape[0]] - polygon[index],
            point - polygon[index],
        )
        >= -GEOM_EPS
        for index in range(polygon.shape[0])
    )


def _convex_clip(subject: np.ndarray, clipper: np.ndarray) -> np.ndarray | None:
    output = subject.copy()
    for index in range(clipper.shape[0]):
        edge_start = clipper[index]
        edge_end = clipper[(index + 1) % clipper.shape[0]]
        if not output.size:
            return None
        input_vertices = output
        clipped: list[np.ndarray] = []
        previous = input_vertices[-1]
        previous_inside = (
            _cross_2d(edge_end - edge_start, previous - edge_start) >= -GEOM_EPS
        )
        for current in input_vertices:
            current_inside = (
                _cross_2d(edge_end - edge_start, current - edge_start) >= -GEOM_EPS
            )
            if current_inside != previous_inside:
                intersection = _line_intersection(
                    previous, current, edge_start, edge_end
                )
                if intersection is not None:
                    clipped.append(intersection)
            if current_inside:
                clipped.append(current)
            previous = current
            previous_inside = current_inside
        if len(clipped) < 3:
            return None
        output = _deduplicate_vertices(np.asarray(clipped, dtype=np.float64))
        if output.shape[0] < 3 or _polygon_area(output) <= GEOM_EPS:
            return None
    return output


def _line_intersection(
    first_start: np.ndarray,
    first_end: np.ndarray,
    second_start: np.ndarray,
    second_end: np.ndarray,
) -> np.ndarray | None:
    first_delta = first_end - first_start
    second_delta = second_end - second_start
    denominator = _cross_2d(first_delta, second_delta)
    if abs(denominator) <= GEOM_EPS:
        return None
    ratio = _cross_2d(second_start - first_start, second_delta) / denominator
    return first_start + ratio * first_delta


def _deduplicate_vertices(vertices: np.ndarray) -> np.ndarray:
    result: list[np.ndarray] = []
    for vertex in vertices:
        if not result or float(np.linalg.norm(vertex - result[-1])) > GEOM_EPS:
            result.append(vertex)
    if len(result) > 1 and float(np.linalg.norm(result[0] - result[-1])) <= GEOM_EPS:
        result.pop()
    return np.asarray(result, dtype=np.float64)


def _convex_union_intersection_area(
    footprint: np.ndarray, drivable_polygons: Sequence[np.ndarray]
) -> float:
    candidates = [
        clipped
        for polygon in drivable_polygons
        if (clipped := _convex_clip(footprint, polygon)) is not None
    ]

    def accumulate(start: int, current: np.ndarray | None, depth: int) -> float:
        total = 0.0
        for index in range(start, len(candidates)):
            intersection = (
                candidates[index]
                if current is None
                else _convex_clip(current, candidates[index])
            )
            if intersection is None:
                continue
            area = _polygon_area(intersection)
            total += area if depth % 2 == 0 else -area
            total += accumulate(index + 1, intersection, depth + 1)
        return total

    value = accumulate(0, None, 0)
    return float(np.clip(value, 0.0, _polygon_area(footprint)))


def _edge(value: Any, label: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (2, 2) or not np.isfinite(result).all():
        raise ValueError(f"{label} must have shape (2,2)")
    if float(np.linalg.norm(result[1] - result[0])) <= GEOM_EPS:
        raise ValueError(f"{label} is degenerate")
    return result


def _number_key(value: float) -> str:
    return format(float(value), ".15g")


def _nonempty(value: Any, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _sha(value: Any, label: str) -> str:
    result = _nonempty(value, label)
    if len(result) != 64 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise ValueError(f"{label} must be a lowercase SHA256")
    return result
