"""Independent literal oracle for V25 selector-after-pool replay.

This module intentionally does not import the producer contract or its score,
selection, context, or decision helpers.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np


AUTHORITY_SHA256 = (
    "9caf4b809b5cba3a21659bea007152e4ed42e78a9f61965b4becdbafa7ee77ad"
)
BASE_POINTER_HEAD = "59874f4a5453f91c17f6575b6a13e7660e99790a"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
EXPECTED_ROOTS = {
    "corrected_preflight_root_sha256": (
        "5be8831533f0a46ecc5439c3eafbff85118689f7696996d825c4b09838189fac"
    ),
    "corrected_preflight_review_root_sha256": (
        "280e45b18630f286147bfe8796df71085701841d339c602a5cd30de6d7943584"
    ),
    "corrected_raw_root_sha256": (
        "731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4"
    ),
    "corrected_raw_review_root_sha256": (
        "c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8"
    ),
    "training_root_sha256": (
        "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
    ),
    "training_review_root_sha256": (
        "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9"
    ),
}
EXPECTED_TRAINING_FILES = {
    "runtime_atom_scales.json": (
        "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
    ),
    "static14d_runtime_weights.npy": (
        "1d512bc80442e82f6bc5e9dd479670cd17b2954a285ce9f5ab2d2afa828ce49e"
    ),
    "model_parameters.npz": (
        "62ae9ceb9ebf563025887d8d60734c2c7865e52fb2b01c1b9d7656ff6f78daa8"
    ),
}
EXPECTED_TENSOR_CONVERTER = {
    "relative_path": "scenario_generation/tensor_converter.py",
    "file_sha256": (
        "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
    ),
    "model_entrypoint": "to_model_tensors",
    "causal_entrypoint": "dump_step_npz",
    "frozen_inverse_transform": (
        "ObservationNormalizer.inverse_with_zero_row_mask;"
        "remove_batch_axis;ego_xy_cos_sin_to_xy_heading_atan2;"
        "goal_xy_cos_sin_to_xy_heading_atan2;"
        "neighbor_first32;turn_int32;version_int64_1"
    ),
}
EXPECTED_OBSERVATION_NORMALIZER = {
    "relative_path": (
        "diffusion_planner/diffusion_planner/utils/normalizer.py"
    ),
    "file_sha256": (
        "8bd11ee947a9e1eae7e71ba80007e4e66bbf34871b2c416979f8a19c81be2d6a"
    ),
    "normalization_json_sha256": "must_be_materialized_and_bound_by_preflight",
}
EXPECTED_ATOMS = (
    (
        "jerk_early",
        "m^2/s^5",
        "dt * sum(||third_difference(candidate_xy)/dt^3||^2) over first third",
        "fixed DP candidate_xy[K,80,2];dt=0.1 s",
        "available after fixed DP produces causal K=8 candidates",
    ),
    (
        "jerk_late",
        "m^2/s^5",
        "dt * sum(||third_difference(candidate_xy)/dt^3||^2) after first third",
        "fixed DP candidate_xy[K,80,2];dt=0.1 s",
        "available after fixed DP produces causal K=8 candidates",
    ),
    (
        "jerk_full",
        "m^2/s^5",
        "dt * sum(||third_difference(candidate_xy)/dt^3||^2) over full horizon",
        "fixed DP candidate_xy[K,80,2];dt=0.1 s",
        "available after fixed DP produces causal K=8 candidates",
    ),
    (
        "rms_acceleration",
        "m/s2",
        "sqrt(mean_t(||diff2(candidate_xy)/dt^2||2))",
        "fixed DP candidate_xy[K,80,2];dt=0.1 s",
        "available after fixed DP produces causal K=8 candidates",
    ),
    (
        "speed_limit_margin_0_0",
        "m^2/s",
        "dt * sum(max(speed_t - (route_limit_t - 0.0), 0)^2)",
        "fixed DP candidate_xy[K,80,2];ordered route;route speed limit;dt=0.1 s",
        "requires decision-time speed limit for every projected route segment",
    ),
    (
        "speed_limit_margin_0_5",
        "m^2/s",
        "dt * sum(max(speed_t - (route_limit_t - 0.5), 0)^2)",
        "fixed DP candidate_xy[K,80,2];ordered route;route speed limit;dt=0.1 s",
        "requires decision-time speed limit for every projected route segment",
    ),
    (
        "speed_limit_margin_1_0",
        "m^2/s",
        "dt * sum(max(speed_t - (route_limit_t - 1.0), 0)^2)",
        "fixed DP candidate_xy[K,80,2];ordered route;route speed limit;dt=0.1 s",
        "requires decision-time speed limit for every projected route segment",
    ),
    (
        "lane_deviation",
        "m^2*s",
        "dt * sum(where(offset>=0,max(offset-left_width,0),max(-offset-right_width,0))^2)",
        "fixed DP candidate_xy[K,80,2];ordered route centerline;left/right boundary offsets",
        "requires decision-time topology route and measured lane boundaries",
    ),
    (
        "clearance",
        "m^2*s",
        "dt * sum(max(3m-candidate_specific_minimum_OBB_surface_clearance_t,0)^2)",
        "fixed DP candidate_xy[K,80,2];candidate neighbor predictions[K,32,80,4];current static obstacles",
        "requires same-call candidate-specific neighbor predictions and observable obstacles",
    ),
    (
        "progress_shortfall",
        "m",
        "max(max_progress_over_source_valid_K-route_progress_k,0)",
        "fixed DP candidate set K=8;ordered route centerline;source_valid mask",
        "requires a decision-time topology route and all K candidates",
    ),
    (
        "planned_red_light_cost",
        "dimensionless_dp_reward_cost",
        "max(-fixed_dp_planned_red_light_reward_k,0)",
        "fixed DP candidate set K=8;certified same-tick route signal receipt",
        "legal zero only when the certified signal input is not applicable",
    ),
    (
        "planned_lateral_acceleration_cost",
        "m/s2",
        "mean(abs(candidate_acceleration dot candidate_lateral_axis))",
        "fixed DP candidate_xy[K,80,2];dt=0.1 s",
        "available after fixed DP produces causal K=8 candidates",
    ),
    (
        "red_stopping_margin_cost",
        "m^2/s",
        "dt * sum(proximity * max(speed - sqrt(2*a*max(distance-buffer,0)),0)^2)",
        "fixed DP candidate_xy[K,80,2];certified route stop line/tangent/arc/same-tick phase",
        "legal zero only when the certified signal input is not applicable",
    ),
    (
        "dp_prior_jerk_excess_cost",
        "m/s^3",
        "max(mean_jerk_norm_k-mean_jerk_norm_candidate0,0)",
        "fixed DP candidate_xy[K,80,2];structural candidate0 row0;dt=0.1 s",
        "candidate0 is structural row0;native-ranked Top1 is not claimed",
    ),
)

RAW_FEATURE_NAMES = (
    "ego_speed_mps",
    "ego_longitudinal_acceleration_mps2",
    "ego_lateral_acceleration_mps2",
    "ego_yaw_rate_radps",
    "route_curvature_mean_abs_radpm",
    "route_curvature_max_abs_radpm",
    "route_lane_width_min_m",
    "route_lane_width_p50_m",
    "route_speed_limit_min_mps",
    "route_speed_limit_current_mps",
    "traffic_phase_red",
    "traffic_phase_yellow",
    "traffic_phase_green",
    "traffic_phase_unknown",
    "traffic_signal_distance_m",
    "traffic_signal_phase_remaining_s",
    "neighbor_count",
    "neighbor_min_distance_m",
    "neighbor_min_ttc_s",
    "neighbor_closing_speed_mps",
    "neighbor_lateral_gap_min_m",
    "candidate_consensus_rms_median_m",
    "candidate_consensus_rms_mad_m",
    "candidate_endpoint_xy_std_m",
    "candidate_progress_std_m",
    "candidate_source_valid_fraction",
)
ATOM_NAMES = tuple(row[0] for row in EXPECTED_ATOMS)
NO_NEIGHBOR_DISTANCE_M = 100.0
NO_NEIGHBOR_TTC_S = 30.0
EXPECTED_SCHEMA_VERSION = (
    "camp_dp_v25_selector_after_pool_replay_contract_v3"
)
EXPECTED_EXACT_DIRS = {
    "contract": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_contract_v3_59874f4a"
    ),
    "contract_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_contract_review_v3_59874f4a"
    ),
    "focused": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_focused_v3_59874f4a"
    ),
    "preflight": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_preflight_v3_59874f4a"
    ),
    "preflight_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_preflight_review_v3_59874f4a"
    ),
    "replay": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_v3_59874f4a"
    ),
    "replay_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_review_v3_59874f4a"
    ),
    "final_docs": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_final_docs_v3_59874f4a"
    ),
}
EXPECTED_SOURCE_KEYS = {
    "contract_module",
    "contract_reviewer",
    "contract_freezer",
    "contract_review_runner",
    "preflight_producer",
    "preflight_reviewer",
    "replay_producer",
    "replay_reviewer",
}


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def review_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("reviewed contract must be object")
    payload = dict(value)
    supplied = payload.pop("contract_payload_sha256", None)
    if supplied != _sha256(_canonical_bytes(payload)):
        raise ValueError("reviewed contract digest mismatch")
    implementation_head = payload.get("implementation_head")
    source_hashes = payload.get("source_hashes")
    if (
        payload.get("schema_version") != EXPECTED_SCHEMA_VERSION
        or payload.get("exact_dirs") != EXPECTED_EXACT_DIRS
        or type(implementation_head) is not str
        or len(implementation_head) != 40
        or set(implementation_head) - set("0123456789abcdef")
        or type(source_hashes) is not dict
        or set(source_hashes) != EXPECTED_SOURCE_KEYS
        or any(
            type(value) is not str
            or len(value) != 64
            or set(value) - set("0123456789abcdef")
            for value in source_hashes.values()
        )
        or payload.get("authority_sha256") != AUTHORITY_SHA256
        or payload.get("base_pointer_head") != BASE_POINTER_HEAD
        or payload.get("fixed_dp_head") != FIXED_DP_HEAD
        or payload.get("sealed_inputs", {}).get(
            "corrected_preflight_root_sha256"
        )
        != EXPECTED_ROOTS["corrected_preflight_root_sha256"]
        or payload.get("sealed_inputs", {}).get(
            "corrected_preflight_review_root_sha256"
        )
        != EXPECTED_ROOTS["corrected_preflight_review_root_sha256"]
        or payload.get("sealed_inputs", {}).get("corrected_raw_root_sha256")
        != EXPECTED_ROOTS["corrected_raw_root_sha256"]
        or payload.get("sealed_inputs", {}).get(
            "corrected_raw_review_root_sha256"
        )
        != EXPECTED_ROOTS["corrected_raw_review_root_sha256"]
        or payload.get("sealed_inputs", {}).get("training_root_sha256")
        != EXPECTED_ROOTS["training_root_sha256"]
        or payload.get("sealed_inputs", {}).get("training_review_root_sha256")
        != EXPECTED_ROOTS["training_review_root_sha256"]
        or payload.get("sealed_inputs", {}).get("training_files")
        != EXPECTED_TRAINING_FILES
        or payload.get("sealed_inputs", {}).get("tensor_converter")
        != EXPECTED_TENSOR_CONVERTER
        or payload.get("sealed_inputs", {}).get("observation_normalizer")
        != EXPECTED_OBSERVATION_NORMALIZER
    ):
        raise ValueError("reviewed authority/root/file binding drifted")
    denominator = payload.get("denominator")
    if denominator != {
        "state_count": 64,
        "repeats_per_state": 5,
        "run_count": 320,
        "candidate_count": 8,
        "independent_unit": "state",
        "drop_replace_complete_case_allowed": False,
    }:
        raise ValueError("reviewed denominator drifted")
    registry = payload.get("atoms", {}).get("registry")
    if not isinstance(registry, list) or len(registry) != 14:
        raise ValueError("reviewed atom registry count drifted")
    for index, (name, units, formula, source, applicability) in enumerate(
        EXPECTED_ATOMS
    ):
        row = registry[index]
        if (
            set(row)
            != {
                "index",
                "name",
                "units",
                "formula",
                "source",
                "applicability",
                "scale_source",
            }
            or row.get("index") != index
            or row.get("name") != name
            or row.get("units") != units
            or row.get("formula") != formula
            or row.get("source") != source
            or row.get("applicability") != applicability
            or row.get("scale_source")
            != f"accepted_training/runtime_atom_scales.json:scales[{index}]"
        ):
            raise ValueError(f"reviewed atom semantic drift: {name}")
    selection = payload.get("selection")
    if selection != {
        "score_formula": "clipped_atom_matrix@weights",
        "score_direction": "lower_is_better",
        "mask": "source_valid_mask",
        "mask_nonempty_required": True,
        "margin_formula": (
            "second_lowest_eligible_score-lowest_eligible_score"
        ),
        "margin_requires_two_eligible": True,
        "tie_definition": "exact_float64_score_equality_at_best_score",
        "tie_break": "lowest_eligible_candidate_index",
        "selected_action_binding": "candidate[selected_index]_exact_bytes",
    }:
        raise ValueError("reviewed selection semantics drifted")
    runtime = payload.get("runtime_gates", {})
    if (
        runtime.get("model_calls") != 0
        or runtime.get("dp_calls") != 0
        or runtime.get("latent_calls") != 0
        or runtime.get("candidate_generation_calls") != 0
        or runtime.get("candidate0_is_row0") is not True
        or runtime.get("candidate_neighbor_tensor_immutable") is not True
    ):
        raise ValueError("reviewed zero-call/immutability topology drifted")
    interpretation = payload.get("interpretation", {})
    if any(
        interpretation.get(key) is not False
        for key in (
            "training_distribution_support_claimed",
            "ood_absence_claimed",
            "no_retraining_claimed",
            "benefit_or_closed_loop_effect_claimed",
            "fresh_or_holdout_outcome_read",
        )
    ):
        raise ValueError("reviewed interpretation overclaims")
    if payload.get("local_runtime_policy", {}).get(
        "bare_python_invocation_for_new_stage_files_allowed"
    ) is not False:
        raise ValueError("reviewed runtime policy permits bare Python")
    return dict(value)


def _route_projection(
    candidates: np.ndarray,
    route_lanes: np.ndarray,
    route_speed_limits: np.ndarray,
    route_has_speed_limits: np.ndarray,
) -> dict[str, np.ndarray]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    route = np.asarray(route_lanes, dtype=np.float64)
    limits = np.asarray(route_speed_limits, dtype=np.float64).reshape(-1)
    has_limits = np.asarray(route_has_speed_limits, dtype=np.bool_).reshape(-1)
    if (
        trajectories.shape != (8, 80, 4)
        or route.shape != (25, 20, 33)
        or limits.shape != (25,)
        or has_limits.shape != (25,)
        or not np.isfinite(trajectories).all()
        or not np.isfinite(route).all()
    ):
        raise ValueError("reviewer route projection input drifted")
    point_groups: list[np.ndarray] = []
    left_groups: list[np.ndarray] = []
    right_groups: list[np.ndarray] = []
    speed_groups: list[np.ndarray] = []
    for slot in range(25):
        valid = np.any(np.abs(route[slot, :, :8]) > 1e-8, axis=1)
        if not valid.any():
            continue
        if (
            not bool(has_limits[slot])
            or not np.isfinite(limits[slot])
            or float(limits[slot]) <= 0.0
        ):
            raise ValueError("reviewer route speed source missing")
        rows = route[slot, valid]
        if rows.shape[0] < 2:
            raise ValueError("reviewer route slot too short")
        point_groups.append(rows[:, :2])
        left_groups.append(rows[:, 4:6])
        right_groups.append(rows[:, 6:8])
        speed_groups.append(
            np.full(rows.shape[0], float(limits[slot]), dtype=np.float64)
        )
    if not point_groups:
        raise ValueError("reviewer route is empty")
    centers = np.concatenate(point_groups)
    left = np.concatenate(left_groups)
    right = np.concatenate(right_groups)
    point_speeds = np.concatenate(speed_groups)
    deltas = np.diff(centers, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    valid_segments = lengths > 1e-6
    if not valid_segments.any():
        raise ValueError("reviewer route has no nonzero segment")
    starts = centers[:-1][valid_segments]
    directions = deltas[valid_segments] / lengths[valid_segments, None]
    segment_lengths = lengths[valid_segments]
    left_start = left[:-1][valid_segments]
    left_end = left[1:][valid_segments]
    right_start = right[:-1][valid_segments]
    right_end = right[1:][valid_segments]
    speed_start = point_speeds[:-1][valid_segments]
    speed_end = point_speeds[1:][valid_segments]
    arc_starts = np.r_[0.0, np.cumsum(segment_lengths[:-1])]
    shape = trajectories.shape[:2]
    lateral = np.empty(shape, dtype=np.float64)
    left_width = np.empty(shape, dtype=np.float64)
    right_width = np.empty(shape, dtype=np.float64)
    speed_limit = np.empty(shape, dtype=np.float64)
    projected_arc = np.empty(shape, dtype=np.float64)
    for candidate_index, trajectory in enumerate(trajectories):
        for step, point in enumerate(trajectory[:, :2]):
            relative = point - starts
            along = np.clip(
                np.einsum("ij,ij->i", relative, directions),
                0.0,
                segment_lengths,
            )
            projections = starts + directions * along[:, None]
            segment = int(
                np.argmin(np.linalg.norm(point - projections, axis=1))
            )
            fraction = along[segment] / segment_lengths[segment]
            normal = np.asarray(
                [-directions[segment, 1], directions[segment, 0]],
                dtype=np.float64,
            )
            left_offset = left_start[segment] + fraction * (
                left_end[segment] - left_start[segment]
            )
            right_offset = right_start[segment] + fraction * (
                right_end[segment] - right_start[segment]
            )
            lateral[candidate_index, step] = np.dot(
                point - projections[segment], normal
            )
            left_width[candidate_index, step] = np.dot(left_offset, normal)
            right_width[candidate_index, step] = -np.dot(right_offset, normal)
            speed_limit[candidate_index, step] = speed_start[
                segment
            ] + fraction * (speed_end[segment] - speed_start[segment])
            projected_arc[candidate_index, step] = (
                arc_starts[segment] + along[segment]
            )
    if np.any(left_width <= 0.0) or np.any(right_width <= 0.0):
        raise ValueError("reviewer route boundary width invalid")
    eligible = np.isfinite(speed_limit).all(axis=1) & (
        speed_limit > 0.0
    ).all(axis=1)
    if not eligible.all():
        raise ValueError("reviewer full route speed source incomplete")
    return {
        "centers": centers,
        "lateral_offset": lateral,
        "left_width": left_width,
        "right_width": right_width,
        "speed_limit": speed_limit,
        "projected_arc": projected_arc,
        "route_progress": np.maximum.accumulate(projected_arc, axis=1)[:, -1],
        "route_speed_source_eligible_mask": eligible,
    }


def _obb_corners(
    x: float,
    y: float,
    heading: float,
    length: float,
    width: float,
    wheelbase: float | None = None,
) -> np.ndarray:
    cos_h, sin_h = math.cos(heading), math.sin(heading)
    if wheelbase is not None and np.isfinite(wheelbase) and wheelbase > 0:
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
    rotation = np.asarray(
        [[cos_h, -sin_h], [sin_h, cos_h]], dtype=np.float64
    )
    return local @ rotation.T + np.asarray([x, y], dtype=np.float64)


def _obb_center_radius(
    x: float,
    y: float,
    heading: float,
    length: float,
    width: float,
    wheelbase: float | None = None,
) -> tuple[np.ndarray, float]:
    offset = (
        float(wheelbase) / 2.0
        if wheelbase is not None and np.isfinite(wheelbase) and wheelbase > 0
        else 0.0
    )
    center = np.asarray(
        [
            x + offset * math.cos(heading),
            y + offset * math.sin(heading),
        ],
        dtype=np.float64,
    )
    return center, math.hypot(length / 2.0, width / 2.0)


def _obb_collides(a: np.ndarray, b: np.ndarray) -> bool:
    for corners in (a, b):
        for index in range(4):
            edge = corners[(index + 1) % 4] - corners[index]
            axis = np.asarray([-edge[1], edge[0]], dtype=np.float64)
            norm = float(np.linalg.norm(axis))
            if norm < 1e-9:
                continue
            axis /= norm
            projection_a = a @ axis
            projection_b = b @ axis
            if (
                float(projection_a.max()) < float(projection_b.min())
                or float(projection_b.max()) < float(projection_a.min())
            ):
                return False
    return True


def _point_segment_distance(
    point: np.ndarray, start: np.ndarray, end: np.ndarray
) -> float:
    segment = end - start
    denominator = float(np.dot(segment, segment))
    if denominator <= 1e-12:
        return float(np.linalg.norm(point - start))
    fraction = float(
        np.clip(np.dot(point - start, segment) / denominator, 0.0, 1.0)
    )
    return float(np.linalg.norm(point - (start + fraction * segment)))


def _obb_distance(a: np.ndarray, b: np.ndarray) -> float:
    if _obb_collides(a, b):
        return 0.0
    distances = []
    for corners, other in ((a, b), (b, a)):
        for point in corners:
            for index in range(4):
                distances.append(
                    _point_segment_distance(
                        point, other[index], other[(index + 1) % 4]
                    )
                )
    return float(min(distances))


def _minimum_clearance_and_physical(
    candidates: np.ndarray,
    neighbor: np.ndarray,
    causal: Mapping[str, np.ndarray],
    projection: Mapping[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    predictions = np.asarray(neighbor, dtype=np.float64)
    history = np.asarray(causal["neighbor_agents_past"], dtype=np.float64)
    static = np.asarray(causal["static_objects"], dtype=np.float64)
    shape = np.asarray(causal["ego_shape"], dtype=np.float64).reshape(-1)
    valid = np.any(np.abs(history) > 1e-8, axis=(1, 2))
    if (
        predictions.shape != (8, 32, 80, 4)
        or history.shape != (32, 31, 11)
        or static.shape != (5, 10)
        or shape.shape != (3,)
        or not np.isfinite(predictions).all()
        or not np.isfinite(history).all()
        or not np.isfinite(static).all()
        or not np.isfinite(shape).all()
        or np.any(shape <= 0)
    ):
        raise ValueError("reviewer obstacle input drifted")
    obstacle = np.zeros((8, 37, 80, 5), dtype=np.float64)
    for slot in np.flatnonzero(valid):
        width, length = history[slot, -1, 6:8]
        headings = predictions[:, slot, :, 2:4]
        if (
            width <= 0
            or length <= 0
            or np.any(np.linalg.norm(headings, axis=2) < 1e-6)
        ):
            raise ValueError("reviewer dynamic obstacle invalid")
        obstacle[:, slot, :, :2] = predictions[:, slot, :, :2]
        obstacle[:, slot, :, 2] = np.arctan2(
            headings[:, :, 1], headings[:, :, 0]
        )
        obstacle[:, slot, :, 3] = length
        obstacle[:, slot, :, 4] = width
    for static_slot, row in enumerate(static):
        if not np.any(np.abs(row[:6]) > 1e-8):
            continue
        width, length = row[4:6]
        if (
            np.linalg.norm(row[2:4]) < 0.5
            or width <= 0
            or length <= 0
        ):
            raise ValueError("reviewer static obstacle invalid")
        obstacle[:, 32 + static_slot, :, :] = np.asarray(
            [
                row[0],
                row[1],
                np.arctan2(row[3], row[2]),
                length,
                width,
            ]
        )
    lateral = np.asarray(projection["lateral_offset"])
    left = np.asarray(projection["left_width"])
    right = np.asarray(projection["right_width"])
    lane_feasible = ~(
        (lateral > left + 1.0) | (lateral < -(right + 1.0))
    ).any(axis=1)
    heading_vectors = trajectories[:, :, 2:4]
    if np.any(np.linalg.norm(heading_vectors, axis=2) < 0.5):
        raise ValueError("reviewer candidate heading invalid")
    headings = np.arctan2(
        heading_vectors[:, :, 1], heading_vectors[:, :, 0]
    )
    wheelbase, ego_length, ego_width = shape
    collision_free = np.ones(8, dtype=np.bool_)
    clearance = np.full((8, 80), 3.0, dtype=np.float64)
    for candidate_index in range(8):
        for step in range(80):
            center, radius = _obb_center_radius(
                trajectories[candidate_index, step, 0],
                trajectories[candidate_index, step, 1],
                headings[candidate_index, step],
                ego_length,
                ego_width,
                wheelbase,
            )
            ego_box = _obb_corners(
                trajectories[candidate_index, step, 0],
                trajectories[candidate_index, step, 1],
                headings[candidate_index, step],
                ego_length,
                ego_width,
                wheelbase,
            )
            for row in obstacle[candidate_index, :, step]:
                if row[3] <= 0 or row[4] <= 0:
                    continue
                other_center, other_radius = _obb_center_radius(*row)
                if (
                    float(np.linalg.norm(center - other_center))
                    - radius
                    - other_radius
                    >= 3.0
                ):
                    continue
                distance = _obb_distance(ego_box, _obb_corners(*row))
                clearance[candidate_index, step] = min(
                    clearance[candidate_index, step], distance
                )
                if distance <= 1e-12:
                    collision_free[candidate_index] = False
    return clearance, lane_feasible & collision_free


def literal_atoms(
    *,
    candidates: np.ndarray,
    neighbor: np.ndarray,
    causal: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    projection = _route_projection(
        trajectories,
        causal["route_lanes"],
        causal["route_lanes_speed_limit"],
        causal["route_lanes_has_speed_limit"],
    )
    source_valid = np.asarray(
        projection["route_speed_source_eligible_mask"], dtype=np.bool_
    )
    clearance_values, physical = _minimum_clearance_and_physical(
        trajectories, neighbor, causal, projection
    )
    xy = trajectories[:, :, :2]
    velocity = np.diff(xy, axis=1) / 0.1
    acceleration = np.diff(velocity, axis=1) / 0.1
    jerk = np.diff(acceleration, axis=1) / 0.1
    jerk_squared = np.sum(jerk**2, axis=2)
    split = max(1, jerk_squared.shape[1] // 3)
    jerk_atoms = np.column_stack(
        (
            0.1 * np.sum(jerk_squared[:, :split], axis=1),
            0.1 * np.sum(jerk_squared[:, split:], axis=1),
            0.1 * np.sum(jerk_squared, axis=1),
        )
    )
    rms_acceleration = np.sqrt(
        np.mean(np.sum(acceleration**2, axis=2), axis=1)
    )
    speeds = np.linalg.norm(velocity, axis=2)
    speed_atoms = np.column_stack(
        [
            0.1
            * np.sum(
                np.maximum(
                    speeds
                    - (
                        np.asarray(projection["speed_limit"])[:, 1:]
                        - margin
                    ),
                    0.0,
                )
                ** 2,
                axis=1,
            )
            for margin in (0.0, 0.5, 1.0)
        ]
    )
    lateral = np.asarray(projection["lateral_offset"], dtype=np.float64)
    left = np.asarray(projection["left_width"], dtype=np.float64)
    right = np.asarray(projection["right_width"], dtype=np.float64)
    boundary_overrun = np.where(
        lateral >= 0.0,
        np.maximum(lateral - left, 0.0),
        np.maximum(-lateral - right, 0.0),
    )
    lane_deviation = 0.1 * np.sum(boundary_overrun**2, axis=1)
    clearance = 0.1 * np.sum(
        np.maximum(3.0 - clearance_values, 0.0) ** 2, axis=1
    )
    progress = np.asarray(projection["route_progress"], dtype=np.float64)
    if not source_valid.any():
        raise ValueError("reviewer source-valid set empty")
    progress_reference = float(np.max(progress[source_valid]))
    progress_shortfall = np.maximum(progress_reference - progress, 0.0)
    lateral_acceleration = np.empty(8, dtype=np.float64)
    for index, trajectory in enumerate(trajectories):
        headings = np.arctan2(trajectory[:, 3], trajectory[:, 2])
        lateral_axes = np.column_stack(
            (-np.sin(headings[2:]), np.cos(headings[2:]))
        )
        lateral_acceleration[index] = float(
            np.mean(np.abs(np.sum(acceleration[index] * lateral_axes, axis=1)))
        )
    mean_jerk = np.mean(np.linalg.norm(jerk, axis=2), axis=1)
    dp_prior_jerk = np.maximum(mean_jerk - float(mean_jerk[0]), 0.0)
    matrix = np.column_stack(
        (
            jerk_atoms,
            rms_acceleration,
            speed_atoms,
            lane_deviation,
            clearance,
            progress_shortfall,
            np.zeros(8, dtype=np.float64),
            lateral_acceleration,
            np.zeros(8, dtype=np.float64),
            dp_prior_jerk,
        )
    )
    if matrix.shape != (8, 14) or not np.isfinite(matrix).all():
        raise ValueError("reviewer atom matrix invalid")
    atom_source = np.ones((8, 14), dtype=np.bool_)
    applicable = np.ones((8, 14), dtype=np.bool_)
    applicable[:, 10] = False
    applicable[:, 12] = False
    availability = {name: True for name in ATOM_NAMES}
    return {
        "raw_atoms": matrix,
        "source_valid_mask": source_valid,
        "physical_feasible_mask": physical & source_valid,
        "atom_source_valid_mask": atom_source,
        "atom_applicable_mask": applicable,
        "availability": availability,
        "route_projection": projection,
    }


def _ordered_route_rows(route_lanes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    route = np.asarray(route_lanes, dtype=np.float64)
    rows = []
    for slot in route:
        valid = np.any(np.abs(slot[:, :8]) > 1e-8, axis=1)
        if valid.any():
            rows.extend(slot[valid])
    values = np.asarray(rows, dtype=np.float64)
    keep = np.r_[
        True, np.linalg.norm(np.diff(values[:, :2], axis=0), axis=1) > 1e-8
    ]
    values = values[keep]
    if values.shape[0] < 3:
        raise ValueError("reviewer ordered route too short")
    arc = np.r_[
        0.0,
        np.cumsum(np.linalg.norm(np.diff(values[:, :2], axis=0), axis=1)),
    ]
    return values, arc


def _route_curvature(points: np.ndarray) -> np.ndarray:
    deltas = np.diff(points, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    if np.any(lengths <= 1e-8):
        raise ValueError("reviewer route contains zero segment")
    headings = np.unwrap(np.arctan2(deltas[:, 1], deltas[:, 0]))
    curvature = np.zeros(points.shape[0], dtype=np.float64)
    if headings.size > 1:
        interior = np.abs(np.diff(headings)) / np.maximum(
            0.5 * (lengths[:-1] + lengths[1:]), 1e-8
        )
        curvature[1:-1] = interior
        curvature[0] = interior[0]
        curvature[-1] = interior[-1]
    return curvature


def _candidate_progress(candidates_xy: np.ndarray, route_xy: np.ndarray) -> np.ndarray:
    deltas = np.diff(route_xy, axis=0)
    lengths = np.linalg.norm(deltas, axis=1)
    valid = lengths > 1e-8
    starts = route_xy[:-1][valid]
    directions = deltas[valid] / lengths[valid, None]
    segment_lengths = lengths[valid]
    full_arc = np.r_[0.0, np.cumsum(lengths)]
    arc_starts = full_arc[:-1][valid]
    result = np.empty(candidates_xy.shape[0], dtype=np.float64)
    for candidate_index, points in enumerate(candidates_xy):
        relative = points[:, None, :] - starts[None, :, :]
        along = np.clip(
            np.einsum("tsd,sd->ts", relative, directions),
            0.0,
            segment_lengths[None, :],
        )
        projections = (
            starts[None, :, :]
            + directions[None, :, :] * along[:, :, None]
        )
        nearest = np.argmin(
            np.linalg.norm(points[:, None, :] - projections, axis=2), axis=1
        )
        projected = arc_starts[nearest] + along[
            np.arange(points.shape[0]), nearest
        ]
        result[candidate_index] = float(np.max(projected))
    return result


def literal_context(
    *,
    candidates: np.ndarray,
    causal: Mapping[str, np.ndarray],
    source_valid_mask: np.ndarray,
) -> dict[str, Any]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    source_valid = np.asarray(source_valid_mask, dtype=np.bool_)
    ego = np.asarray(causal["ego_current_state"], dtype=np.float64).reshape(-1)
    route_rows, route_arc = _ordered_route_rows(causal["route_lanes"])
    curvature = _route_curvature(route_rows[:, :2])
    lane_widths = np.linalg.norm(route_rows[:, 4:6], axis=1) + np.linalg.norm(
        route_rows[:, 6:8], axis=1
    )
    limits = np.asarray(
        causal["route_lanes_speed_limit"], dtype=np.float64
    ).reshape(-1)
    has_limits = np.asarray(
        causal["route_lanes_has_speed_limit"], dtype=np.bool_
    ).reshape(-1)
    available_limits = limits[has_limits]
    history = np.asarray(causal["neighbor_agents_past"], dtype=np.float64)
    current = history[:, -1]
    active = (current[:, 6] > 0.0) & (current[:, 7] > 0.0)
    ego_speed = max(float(ego[4]), 0.0)
    if not active.any():
        neighbor_values = (
            0.0,
            NO_NEIGHBOR_DISTANCE_M,
            NO_NEIGHBOR_TTC_S,
            0.0,
            NO_NEIGHBOR_DISTANCE_M,
        )
    else:
        rows = current[active]
        positions = rows[:, :2]
        distances = np.linalg.norm(positions, axis=1)
        relative_velocity = rows[:, 4:6] - np.asarray([ego_speed, 0.0])
        closing = -np.einsum(
            "ij,ij->i", positions, relative_velocity
        ) / np.maximum(distances, 1e-6)
        ttc = np.where(
            closing > 1e-6, distances / closing, NO_NEIGHBOR_TTC_S
        )
        closest = int(np.argmin(distances))
        neighbor_values = (
            float(rows.shape[0]),
            float(np.min(distances)),
            float(min(np.min(ttc), NO_NEIGHBOR_TTC_S)),
            float(closing[closest]),
            float(np.min(np.abs(positions[:, 1]))),
        )
    xy = trajectories[:, :, :2]
    center = np.median(xy, axis=0)
    rms = np.sqrt(np.mean(np.sum((xy - center[None, :, :]) ** 2, axis=2), axis=1))
    median_rms = float(np.median(rms))
    mad_rms = float(np.median(np.abs(rms - median_rms)))
    endpoints = trajectories[:, -1, :2]
    endpoint_std = float(
        np.sqrt(np.var(endpoints[:, 0]) + np.var(endpoints[:, 1]))
    )
    progress_std = float(
        np.std(_candidate_progress(xy, route_rows[:, :2]))
    )
    raw = np.asarray(
        [
            ego_speed,
            float(ego[6]),
            ego_speed * float(ego[9]),
            float(ego[9]),
            float(np.mean(curvature)),
            float(np.max(curvature)),
            float(np.min(lane_widths)),
            float(np.median(lane_widths)),
            float(np.min(available_limits)),
            float(available_limits[0]),
            0.0,
            0.0,
            0.0,
            1.0,
            float(route_arc[-1]),
            0.0,
            *neighbor_values,
            median_rms,
            mad_rms,
            endpoint_std,
            progress_std,
            float(np.mean(source_valid)),
        ],
        dtype=np.float64,
    )
    complete = np.asarray(
        [
            *(True for _ in range(10)),
            *(False for _ in range(5)),
            False,
            *(True for _ in range(5)),
            *(True for _ in range(5)),
        ],
        dtype=np.bool_,
    )
    if raw.shape != (26,) or complete.shape != (26,):
        raise AssertionError("reviewer context dimension drifted")
    return {
        "raw": raw,
        "source_complete": complete,
        "payload": {
            "schema_version": "camp_dp_v25_causal_context_raw_v2",
            "raw_context": {
                name: float(value)
                for name, value in zip(RAW_FEATURE_NAMES, raw)
            },
            "source_complete": {
                name: bool(value)
                for name, value in zip(RAW_FEATURE_NAMES, complete)
            },
            "source_receipt": {
                "mode": "no_v2i",
                "phase_remaining_available": False,
                "regulatory_signal_mapped": False,
            },
        },
    }


def literal_scene_weights(
    *,
    raw_context: np.ndarray,
    source_complete: np.ndarray,
    q05: np.ndarray,
    q95: np.ndarray,
    theta: np.ndarray,
) -> dict[str, np.ndarray]:
    raw = np.asarray(raw_context, dtype=np.float64)
    source = np.asarray(source_complete, dtype=np.bool_)
    low = np.asarray(q05, dtype=np.float64)
    high = np.asarray(q95, dtype=np.float64)
    matrix = np.asarray(theta, dtype=np.float64)
    if (
        raw.shape != (26,)
        or source.shape != (26,)
        or low.shape != (26,)
        or high.shape != (26,)
        or matrix.shape != (14, 53)
        or not np.isfinite(
            np.r_[raw, low, high, matrix.reshape(-1)]
        ).all()
        or np.any(high <= low)
    ):
        raise ValueError("reviewer scene-weight preimage invalid")
    unit = np.clip((raw - low) / (high - low), 0.0, 1.0)
    phi = np.zeros(53, dtype=np.float64)
    phi[0] = 1.0
    phi[1::2] = np.where(source, unit, 0.0)
    phi[2::2] = np.where(source, 1.0 - unit, 0.0)
    phi /= 1.0 + float(np.sum(source))
    weights = matrix @ phi
    if (
        not np.isclose(phi.sum(), 1.0, rtol=0.0, atol=1e-10)
        or np.any(phi < -1e-10)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-8)
        or np.any(weights < -1e-9)
    ):
        raise ValueError("reviewer scene simplex drifted")
    return {"phi": phi, "weights": weights}


def validate_slot_authority(
    *,
    receipt: Mapping[str, Any],
    binding: Mapping[str, Any],
    candidate: np.ndarray,
    neighbor: np.ndarray,
) -> None:
    candidate_value = np.ascontiguousarray(np.asarray(candidate))
    neighbor_value = np.ascontiguousarray(np.asarray(neighbor))
    if (
        candidate_value.shape != (8, 80, 4)
        or candidate_value.dtype != np.dtype("<f4")
        or neighbor_value.shape != (8, 32, 80, 4)
        or neighbor_value.dtype != np.dtype("<f4")
        or not np.isfinite(candidate_value).all()
        or not np.isfinite(neighbor_value).all()
    ):
        raise ValueError("reviewer slot tensor schema drifted")
    candidate_sha = _sha256(candidate_value.tobytes(order="C"))
    neighbor_sha = _sha256(neighbor_value.tobytes(order="C"))
    expected_pool = _sha256(
        _canonical_bytes(
            {
                "forward_id": binding.get("forward_id"),
                "candidate_tensor_sha256": candidate_sha,
                "neighbor_tensor_sha256": neighbor_sha,
            }
        )
    )
    expected_rows = [
        _sha256(
            np.ascontiguousarray(candidate_value[index]).tobytes(order="C")
        )
        for index in range(8)
    ]
    if (
        receipt.get("status") != "computed"
        or receipt.get("slot") != binding.get("slot")
        or receipt.get("run_id") != binding.get("run_id")
        or receipt.get("state_index") != binding.get("state_index")
        or receipt.get("repeat_index") != binding.get("repeat_index")
        or receipt.get("forward_id") != binding.get("forward_id")
        or receipt.get("pool_id") != expected_pool
        or binding.get("pool_id") != expected_pool
        or receipt.get("candidate_tensor_sha256") != candidate_sha
        or receipt.get("neighbor_tensor_sha256") != neighbor_sha
        or receipt.get("candidate_row_sha256") != expected_rows
        or receipt.get("candidate_tensor_sha256_before") != candidate_sha
        or receipt.get("candidate_tensor_sha256_after") != candidate_sha
        or receipt.get("neighbor_tensor_sha256_before") != neighbor_sha
        or receipt.get("neighbor_tensor_sha256_after") != neighbor_sha
        or receipt.get("formal_model_call_count") != 0
        or receipt.get("dp_call_count") != 0
        or receipt.get("latent_generation_call_count") != 0
        or receipt.get("candidate_generation_call_count") != 0
        or receipt.get("selector_call_count") != 2
    ):
        raise ValueError("reviewer slot authority/call/tensor binding drifted")


def literal_selection(
    *,
    candidates: np.ndarray,
    raw_atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    eligibility_mask: np.ndarray,
) -> dict[str, Any]:
    candidate = np.ascontiguousarray(np.asarray(candidates))
    atoms = np.asarray(raw_atoms, dtype=np.float64)
    scale = np.asarray(scales, dtype=np.float64)
    coefficient = np.asarray(weights, dtype=np.float64)
    mask = np.asarray(eligibility_mask)
    if (
        candidate.shape != (8, 80, 4)
        or candidate.dtype != np.dtype("<f4")
        or not np.isfinite(candidate).all()
        or atoms.shape != (8, 14)
        or not np.isfinite(atoms).all()
        or np.any(atoms < 0)
        or scale.shape != (14,)
        or not np.isfinite(scale).all()
        or np.any(scale <= 0)
        or coefficient.shape != (14,)
        or not np.isfinite(coefficient).all()
        or np.any(coefficient < -1e-9)
        or not np.isclose(coefficient.sum(), 1.0, rtol=0.0, atol=1e-8)
        or mask.shape != (8,)
        or mask.dtype != np.bool_
        or not mask.any()
    ):
        raise ValueError("reviewer literal selection preimage invalid")
    scaled = atoms / scale[None, :]
    clipped = np.minimum(np.maximum(scaled, 0.0), 10.0)
    # The frozen production selector evaluates its affine score with the
    # NumPy matrix-multiply operation.  Rebuild the operands independently,
    # then use that exact numerical operation so the sealed float64 values are
    # byte-for-byte comparable rather than merely tolerance-close.
    scores = clipped @ coefficient
    eligible = np.flatnonzero(mask)
    ordered = sorted(eligible.tolist(), key=lambda i: (float(scores[i]), i))
    selected = int(ordered[0])
    best = float(scores[selected])
    ties = [int(index) for index in eligible if float(scores[index]) == best]
    second = None if len(ordered) < 2 else float(scores[ordered[1]])
    selected_bytes = np.ascontiguousarray(candidate[selected]).tobytes(order="C")
    return {
        "raw_atoms": atoms.tolist(),
        "scaled_atoms": scaled.tolist(),
        "clipped_atoms": clipped.tolist(),
        "weights": coefficient.tolist(),
        "scores": scores.tolist(),
        "eligibility_mask": mask.tolist(),
        "eligible_indices": eligible.astype(int).tolist(),
        "tie_set": ties,
        "selected_index": selected,
        "selected_row_sha256": _sha256(selected_bytes),
        "selected_action": candidate[selected].tolist(),
        "selected_action_sha256": _sha256(selected_bytes),
        "margin": (
            {
                "status": "typed_missing",
                "value": None,
                "reason": "fewer_than_two_eligible_for_margin",
            }
            if second is None
            else {
                "status": "computed",
                "value": second - best,
                "reason": None,
            }
        ),
    }


def verify_same_state(receipts: Sequence[Mapping[str, Any]]) -> None:
    if len(receipts) != 5:
        raise ValueError("reviewer same-state denominator drifted")
    fields = (
        "candidate_tensor_sha256_before",
        "candidate_tensor_sha256_after",
        "neighbor_tensor_sha256_before",
        "neighbor_tensor_sha256_after",
        "atom_receipt_sha256",
        "context_receipt_sha256",
        "static14d",
        "scene14d",
    )
    reference = {field: receipts[0][field] for field in fields}
    for receipt in receipts[1:]:
        if {field: receipt[field] for field in fields} != reference:
            raise ValueError("reviewer detected same-state nondeterminism")
