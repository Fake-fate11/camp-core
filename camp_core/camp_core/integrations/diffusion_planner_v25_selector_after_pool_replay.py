"""Outcome-free selector-after-pool replay contract and pure computations.

This module never loads or invokes Diffusion Planner.  It freezes the exact
inputs and semantics for replaying the production Static14D and Scene14D
selectors on the already sealed corrected batch8 candidate pools.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


AUTHORITY_SHA256 = (
    "e6579ca71ccfdd7e0a94d52450b2473d4b8c52c38e8b0504e0dcb8b35935ab3c"
)
PARENT_AUTHORITY_SHA256 = (
    "9caf4b809b5cba3a21659bea007152e4ed42e78a9f61965b4becdbafa7ee77ad"
)
BASE_POINTER_HEAD = "4c412870118962ee49917bcc2090be18836fe709"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CORRECTED_PREFLIGHT_ROOT = (
    "5be8831533f0a46ecc5439c3eafbff85118689f7696996d825c4b09838189fac"
)
CORRECTED_PREFLIGHT_REVIEW_ROOT = (
    "280e45b18630f286147bfe8796df71085701841d339c602a5cd30de6d7943584"
)
CORRECTED_RAW_ROOT = (
    "731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4"
)
CORRECTED_RAW_REVIEW_ROOT = (
    "c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8"
)
TRAINING_ROOT = (
    "8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9"
)
TRAINING_REVIEW_ROOT = (
    "ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9"
)
TRAINING_SCALE_FILE_SHA256 = (
    "72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb"
)
TRAINING_STATIC_WEIGHTS_FILE_SHA256 = (
    "1d512bc80442e82f6bc5e9dd479670cd17b2954a285ce9f5ab2d2afa828ce49e"
)
TRAINING_MODEL_PARAMETERS_FILE_SHA256 = (
    "62ae9ceb9ebf563025887d8d60734c2c7865e52fb2b01c1b9d7656ff6f78daa8"
)
TENSOR_CONVERTER_SHA256 = (
    "af0a087dcfa910e5f0ad4732c5d1ebabb2fe5c41d2d61a4aa7aaf0f4351d36a7"
)
OBSERVATION_NORMALIZER_SHA256 = (
    "8bd11ee947a9e1eae7e71ba80007e4e66bbf34871b2c416979f8a19c81be2d6a"
)

STATE_COUNT = 64
REPEATS_PER_STATE = 5
RUN_COUNT = STATE_COUNT * REPEATS_PER_STATE
CANDIDATE_COUNT = 8
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
ATOM_COUNT = 14
DT_S = 0.1
TRAINED_SIMPLEX_NONNEGATIVE_ATOL = 1e-9
SIMPLEX_SUM_ATOL = 1e-8

FAILED_REPLAY_ROOT = (
    "7a85ef00c10a79aa1b8e92729f51d9512e5e67d53d1ef44e00da55d19840109d"
)
PARENT_CONTRACT_ROOT = (
    "53c6b6ca62f0ceb8193ff32dadcb793099c77674cfa4f36102f73141b786362c"
)
PARENT_CONTRACT_REVIEW_ROOT = (
    "afd9ad2350594a0db41fa334ae64caaacfa3f857a414a3faf9405d3f2ebbfe37"
)
PARENT_PREFLIGHT_ROOT = (
    "6b7bfc0edfa87e75a64dd82775d4ad8d427a11bdebe5fd24ba995b3ef7a45539"
)
PARENT_PREFLIGHT_REVIEW_ROOT = (
    "0d73790f13fb99137a4e9cfdd67d3830469f71281e1a5b108797ab8894844cec"
)

SCHEMA_VERSION = "camp_dp_v25_selector_after_pool_replay_replacement_contract_v1"
PREFLIGHT_SCHEMA_VERSION = (
    "camp_dp_v25_selector_after_pool_replay_replacement_preflight_v1"
)
REPLAY_SCHEMA_VERSION = "camp_dp_v25_selector_after_pool_replay_replacement_v1"
REVIEW_SCHEMA_VERSION = (
    "camp_dp_v25_selector_after_pool_replay_replacement_review_v1"
)

EXACT_DIRS = {
    "failure_closeout": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_failure_closeout_v1_"
        "4c412870_e6579ca7"
    ),
    "failure_closeout_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_failure_closeout_review_v1_"
        "4c412870_e6579ca7"
    ),
    "contract": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_contract_v1_"
        "4c412870_e6579ca7"
    ),
    "contract_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_contract_review_v1_"
        "4c412870_e6579ca7"
    ),
    "focused": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_focused_v1_"
        "4c412870_e6579ca7"
    ),
    "preflight": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_preflight_v1_"
        "4c412870_e6579ca7"
    ),
    "preflight_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_preflight_review_v1_"
        "4c412870_e6579ca7"
    ),
    "replay": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_v1_"
        "4c412870_e6579ca7"
    ),
    "replay_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_review_v1_"
        "4c412870_e6579ca7"
    ),
    "final_docs": (
        "/root/autodl-tmp/"
        "camp_dp_v25_selector_after_pool_replay_replacement_final_docs_focused_v1_"
        "4c412870_e6579ca7"
    ),
}

ATOM_REGISTRY = (
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

MODEL_INPUT_TENSOR_ORDER = (
    "delay",
    "ego_agent_past",
    "ego_current_state",
    "ego_shape",
    "goal_pose",
    "lanes",
    "lanes_has_speed_limit",
    "lanes_speed_limit",
    "line_strings",
    "neighbor_agents_past",
    "polygons",
    "route_lanes",
    "route_lanes_has_speed_limit",
    "route_lanes_speed_limit",
    "sampled_trajectories",
    "static_objects",
    "turn_indicators",
)


def canonical_bytes(value: Any) -> bytes:
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


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(value: np.ndarray) -> str:
    return sha256_bytes(np.ascontiguousarray(value).tobytes(order="C"))


def pool_id_from_preimages(
    *,
    forward_id: str,
    candidate_tensor_sha256: str,
    neighbor_tensor_sha256: str,
) -> str:
    values = (forward_id, candidate_tensor_sha256, neighbor_tensor_sha256)
    if any(
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
        for value in values
    ):
        raise ValueError("pool binding must contain three lowercase SHA256 values")
    return sha256_json(
        {
            "forward_id": forward_id,
            "candidate_tensor_sha256": candidate_tensor_sha256,
            "neighbor_tensor_sha256": neighbor_tensor_sha256,
        }
    )


def atom_registry() -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "name": name,
            "units": units,
            "formula": formula,
            "source": source,
            "applicability": applicability,
            "scale_source": (
                "accepted_training/runtime_atom_scales.json:"
                f"scales[{index}]"
            ),
        }
        for index, (name, units, formula, source, applicability) in enumerate(
            ATOM_REGISTRY
        )
    ]


def contract(
    *,
    implementation_head: str,
    source_hashes: Mapping[str, str],
    failure_closeout_root: str,
    failure_closeout_review_root: str,
) -> dict[str, Any]:
    if len(implementation_head) != 40 or set(implementation_head) - set(
        "0123456789abcdef"
    ):
        raise ValueError("implementation head must be a lowercase git SHA")
    required_sources = {
        "contract_module",
        "contract_reviewer",
        "contract_freezer",
        "contract_review_runner",
        "preflight_producer",
        "preflight_reviewer",
        "replay_producer",
        "replay_reviewer",
        "failure_closeout_producer",
        "failure_closeout_reviewer",
        "scene_runtime",
    }
    if set(source_hashes) != required_sources or any(
        len(value) != 64 or set(value) - set("0123456789abcdef")
        for value in source_hashes.values()
    ):
        raise ValueError("source hash inventory drifted")
    if any(
        type(value) is not str
        or len(value) != 64
        or set(value) - set("0123456789abcdef")
        for value in (failure_closeout_root, failure_closeout_review_root)
    ):
        raise ValueError("failure closeout root binding drifted")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "authority_sha256": AUTHORITY_SHA256,
        "base_pointer_head": BASE_POINTER_HEAD,
        "parent_authority_sha256": PARENT_AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "exact_dirs": dict(EXACT_DIRS),
        "sealed_inputs": {
            "failed_replay_root_sha256": FAILED_REPLAY_ROOT,
            "parent_contract_root_sha256": PARENT_CONTRACT_ROOT,
            "parent_contract_review_root_sha256": PARENT_CONTRACT_REVIEW_ROOT,
            "parent_preflight_root_sha256": PARENT_PREFLIGHT_ROOT,
            "parent_preflight_review_root_sha256": PARENT_PREFLIGHT_REVIEW_ROOT,
            "failure_closeout_root_sha256": failure_closeout_root,
            "failure_closeout_review_root_sha256": failure_closeout_review_root,
            "corrected_preflight_root_sha256": CORRECTED_PREFLIGHT_ROOT,
            "corrected_preflight_review_root_sha256": (
                CORRECTED_PREFLIGHT_REVIEW_ROOT
            ),
            "corrected_raw_root_sha256": CORRECTED_RAW_ROOT,
            "corrected_raw_review_root_sha256": CORRECTED_RAW_REVIEW_ROOT,
            "training_root_sha256": TRAINING_ROOT,
            "training_review_root_sha256": TRAINING_REVIEW_ROOT,
            "training_files": {
                "runtime_atom_scales.json": TRAINING_SCALE_FILE_SHA256,
                "static14d_runtime_weights.npy": (
                    TRAINING_STATIC_WEIGHTS_FILE_SHA256
                ),
                "model_parameters.npz": (
                    TRAINING_MODEL_PARAMETERS_FILE_SHA256
                ),
            },
            "tensor_converter": {
                "relative_path": "scenario_generation/tensor_converter.py",
                "file_sha256": TENSOR_CONVERTER_SHA256,
                "model_entrypoint": "to_model_tensors",
                "causal_entrypoint": "dump_step_npz",
                "frozen_inverse_transform": (
                    "ObservationNormalizer.inverse_with_zero_row_mask;"
                    "remove_batch_axis;ego_xy_cos_sin_to_xy_heading_atan2;"
                    "goal_xy_cos_sin_to_xy_heading_atan2;"
                    "neighbor_first32;turn_int32;version_int64_1"
                ),
            },
            "observation_normalizer": {
                "relative_path": (
                    "diffusion_planner/diffusion_planner/utils/normalizer.py"
                ),
                "file_sha256": OBSERVATION_NORMALIZER_SHA256,
                "normalization_json_sha256": (
                    "must_be_materialized_and_bound_by_preflight"
                ),
            },
        },
        "denominator": {
            "state_count": STATE_COUNT,
            "repeats_per_state": REPEATS_PER_STATE,
            "run_count": RUN_COUNT,
            "candidate_count": CANDIDATE_COUNT,
            "independent_unit": "state",
            "drop_replace_complete_case_allowed": False,
        },
        "arms": {
            "pool_matched_candidate0": {
                "rule": "immutable_candidate_tensor_row0",
                "selector_executed": False,
            },
            "Static14D": {
                "production_selector_required": True,
                "weights_source": (
                    "accepted_training/static14d_runtime_weights.npy"
                ),
            },
            "Scene14D": {
                "production_selector_required": True,
                "mode": "no_v2i",
                "theta_and_context_source": (
                    "accepted_training/model_parameters.npz"
                ),
                "runtime_projection": False,
                "softmax": False,
            },
        },
        "atoms": {
            "count": ATOM_COUNT,
            "registry": atom_registry(),
            "raw_shape": [8, 14],
            "scaled_formula": "raw_atom/scales",
            "clipped_formula": "clip(raw_atom/scales,0,10)",
            "eligibility_policy": "v22_source_valid",
        },
        "selection": {
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
            "trained_simplex_nonnegative_atol": (
                TRAINED_SIMPLEX_NONNEGATIVE_ATOL
            ),
            "simplex_sum_atol": SIMPLEX_SUM_ATOL,
            "static_and_scene_explicitly_receive_accepted_atol": True,
        },
        "runtime_gates": {
            "candidate_shape_dtype": [list(CANDIDATE_SHAPE), "<f4"],
            "neighbor_shape_dtype": [list(NEIGHBOR_SHAPE), "<f4"],
            "candidate0_is_row0": True,
            "candidate_neighbor_tensor_immutable": True,
            "model_calls": 0,
            "dp_calls": 0,
            "latent_calls": 0,
            "candidate_generation_calls": 0,
            "same_state_five_repeat_exact_determinism": [
                "raw_atoms",
                "scaled_atoms",
                "clipped_atoms",
                "context",
                "weights",
                "scores",
                "masks",
                "tie_set",
                "selected_index",
                "selected_action",
            ],
        },
        "typed_failures": [
            "source_or_applicability_evidence_missing",
            "atom_materialization_failure",
            "context_or_weight_failure",
            "empty_eligibility_mask",
            "fewer_than_two_eligible_for_margin",
            "score_or_mask_failure",
            "tie_or_index_binding_failure",
            "selected_action_binding_failure",
            "runtime_nondeterminism",
        ],
        "interpretation": {
            "pass": (
                "sealed corrected pools runtime selector compatibility, "
                "same-pool immutability, zero-extra-call, and selection "
                "determinism"
            ),
            "training_distribution_support_claimed": False,
            "ood_absence_claimed": False,
            "no_retraining_claimed": False,
            "benefit_or_closed_loop_effect_claimed": False,
            "fresh_or_holdout_outcome_read": False,
        },
        "forbidden": {
            "safetycost_or_old_ni": True,
            "industrial_v3_effect_endpoints": True,
            "fresh_holdout_outcomes": True,
            "model_dp_latent_candidate_generation": True,
            "training_retraining_closed_loop": True,
            "old_artifact_or_cas_write": True,
            "claim_promotion_deployment": True,
        },
        "source_hashes": dict(source_hashes),
        "local_runtime_policy": {
            "windows_executable": (
                "C:\\Users\\lenovo\\.cache\\codex-runtimes\\"
                "codex-primary-runtime\\dependencies\\python\\python.exe"
            ),
            "autodl_executable": "/root/autodl-tmp/dp312_venv/bin/python",
            "minimum_version": [3, 10],
            "autodl_expected_version": [3, 12, 3],
            "bare_python_invocation_for_new_stage_files_allowed": False,
        },
    }
    payload["contract_payload_sha256"] = sha256_json(payload)
    return payload


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("contract must be an object")
    payload = dict(value)
    supplied = payload.pop("contract_payload_sha256", None)
    if supplied != sha256_json(payload):
        raise ValueError("contract payload digest drifted")
    implementation_head = payload.get("implementation_head")
    source_hashes = payload.get("source_hashes")
    if type(implementation_head) is not str or type(source_hashes) is not dict:
        raise ValueError("contract authority fields missing")
    expected = contract(
        implementation_head=implementation_head,
        source_hashes=source_hashes,
        failure_closeout_root=payload.get("sealed_inputs", {}).get(
            "failure_closeout_root_sha256"
        ),
        failure_closeout_review_root=payload.get("sealed_inputs", {}).get(
            "failure_closeout_review_root_sha256"
        ),
    )
    if dict(value) != expected:
        raise ValueError("contract semantic payload drifted")
    return dict(value)


def _single_batch(value: Any, shape: tuple[int, ...], label: str) -> np.ndarray:
    array = np.asarray(value)
    if array.shape != (1, *shape):
        raise ValueError(f"{label} shape drifted")
    return np.ascontiguousarray(array[0])


def _xy_cos_sin_to_xy_heading(value: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float32)
    if array.shape[-1] != 4 or not np.isfinite(array).all():
        raise ValueError(f"{label} xy/cos/sin encoding drifted")
    result = np.empty((*array.shape[:-1], 3), dtype=np.float32)
    result[..., :2] = array[..., :2]
    result[..., 2] = np.arctan2(array[..., 3], array[..., 2]).astype(
        np.float32
    )
    return np.ascontiguousarray(result)


def causal_input_from_model_input(
    arrays: Mapping[str, np.ndarray],
    *,
    normalization: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, np.ndarray]:
    """Invert the pinned tensor-converter representation without a model call."""

    if type(arrays) is not dict or tuple(sorted(arrays)) != tuple(
        sorted(MODEL_INPUT_TENSOR_ORDER)
    ):
        raise ValueError("model-input exact tensor keyset drifted")
    normalized = {
        name: np.ascontiguousarray(np.asarray(value))
        for name, value in arrays.items()
    }
    for name, row in (normalization or {}).items():
        if name not in normalized:
            continue
        if type(row) is not dict or set(row) != {"mean", "std"}:
            raise ValueError(f"{name} normalization schema drifted")
        value = normalized[name]
        mean = np.asarray(row["mean"], dtype=np.float32)
        std = np.asarray(row["std"], dtype=np.float32)
        if (
            not np.isfinite(mean).all()
            or not np.isfinite(std).all()
            or np.any(std <= 0.0)
        ):
            raise ValueError(f"{name} normalization values drifted")
        try:
            restored = value.astype(np.float32, copy=False) * std + mean
        except ValueError as exc:
            raise ValueError(f"{name} normalization shape drifted") from exc
        zero_mask = np.sum(np.not_equal(value, 0), axis=-1) == 0
        restored[zero_mask] = 0
        normalized[name] = np.ascontiguousarray(restored)
    result = {
        "ego_agent_past": _xy_cos_sin_to_xy_heading(
            _single_batch(
                normalized["ego_agent_past"], (31, 4), "ego_agent_past"
            ),
            "ego_agent_past",
        ),
        "ego_current_state": _single_batch(
            normalized["ego_current_state"], (10,), "ego_current_state"
        ).astype(np.float32, copy=False),
        "ego_shape": _single_batch(
            normalized["ego_shape"], (3,), "ego_shape"
        ).astype(np.float32, copy=False),
        "goal_pose": _xy_cos_sin_to_xy_heading(
            _single_batch(normalized["goal_pose"], (4,), "goal_pose"),
            "goal_pose",
        ),
        "lanes": _single_batch(
            normalized["lanes"], (140, 20, 33), "lanes"
        ).astype(np.float32, copy=False),
        "lanes_has_speed_limit": _single_batch(
            normalized["lanes_has_speed_limit"],
            (140, 1),
            "lanes_has_speed_limit",
        ).astype(np.bool_, copy=False),
        "lanes_speed_limit": _single_batch(
            normalized["lanes_speed_limit"], (140, 1), "lanes_speed_limit"
        ).astype(np.float32, copy=False),
        "line_strings": _single_batch(
            normalized["line_strings"], (60, 20, 4), "line_strings"
        ).astype(np.float32, copy=False),
        "neighbor_agents_past": _single_batch(
            normalized["neighbor_agents_past"],
            (320, 31, 11),
            "neighbor_agents_past",
        )[:32].astype(np.float32, copy=False),
        "polygons": _single_batch(
            normalized["polygons"], (10, 40, 3), "polygons"
        ).astype(np.float32, copy=False),
        "route_lanes": _single_batch(
            normalized["route_lanes"], (25, 20, 33), "route_lanes"
        ).astype(np.float32, copy=False),
        "route_lanes_has_speed_limit": _single_batch(
            normalized["route_lanes_has_speed_limit"],
            (25, 1),
            "route_lanes_has_speed_limit",
        ).astype(np.bool_, copy=False),
        "route_lanes_speed_limit": _single_batch(
            normalized["route_lanes_speed_limit"],
            (25, 1),
            "route_lanes_speed_limit",
        ).astype(np.float32, copy=False),
        "static_objects": _single_batch(
            normalized["static_objects"], (5, 10), "static_objects"
        ).astype(np.float32, copy=False),
        "turn_indicators": _single_batch(
            normalized["turn_indicators"], (31,), "turn_indicators"
        ).astype(np.int32, copy=False),
        "version": np.array(1, dtype=np.int64),
    }
    if any(not np.isfinite(value).all() for value in result.values()):
        raise ValueError("causal input contains nonfinite values")
    finalized = {
        key: np.ascontiguousarray(value) for key, value in result.items()
    }
    # np.ascontiguousarray promotes a NumPy scalar to shape (1,).  The frozen
    # causal schema requires version to remain an int64 scalar with shape ().
    finalized["version"] = np.asarray(
        result["version"], dtype=np.int64
    ).reshape(())
    return finalized


def tensor_receipt(value: np.ndarray) -> dict[str, Any]:
    array = np.ascontiguousarray(value)
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "tensor_sha256": array_sha256(array),
    }


def selection_from_preimages(
    *,
    candidates: np.ndarray,
    raw_atoms: np.ndarray,
    scales: np.ndarray,
    weights: np.ndarray,
    eligibility_mask: np.ndarray,
    simplex_nonnegative_atol: float,
) -> dict[str, Any]:
    candidate = np.ascontiguousarray(np.asarray(candidates))
    atoms = np.asarray(raw_atoms, dtype=np.float64)
    scale = np.asarray(scales, dtype=np.float64)
    coefficient = np.asarray(weights, dtype=np.float64)
    raw_mask = np.asarray(eligibility_mask)
    if (
        candidate.shape != CANDIDATE_SHAPE
        or candidate.dtype != np.dtype("<f4")
        or not np.isfinite(candidate).all()
    ):
        raise ValueError("candidate tensor must be finite <f4 [8,80,4]")
    if atoms.shape != (8, 14) or not np.isfinite(atoms).all() or np.any(atoms < 0):
        raise ValueError("raw atoms must be finite nonnegative [8,14]")
    if scale.shape != (14,) or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError("scales must be finite positive [14]")
    if (
        type(simplex_nonnegative_atol) is not float
        or simplex_nonnegative_atol != TRAINED_SIMPLEX_NONNEGATIVE_ATOL
    ):
        raise ValueError("accepted simplex nonnegative tolerance drifted")
    if (
        coefficient.shape != (14,)
        or not np.isfinite(coefficient).all()
        or np.any(coefficient < -simplex_nonnegative_atol)
        or not np.isclose(
            coefficient.sum(), 1.0, rtol=0.0, atol=SIMPLEX_SUM_ATOL
        )
    ):
        raise ValueError("weights must be a finite nonnegative simplex [14]")
    if raw_mask.shape != (8,) or raw_mask.dtype != np.bool_ or not raw_mask.any():
        raise ValueError("eligibility mask must be nonempty native bool [8]")
    scaled = atoms / scale[None, :]
    clipped = np.clip(scaled, 0.0, 10.0)
    scores = clipped @ coefficient
    eligible_indices = np.flatnonzero(raw_mask)
    eligible_scores = scores[eligible_indices]
    ordering = sorted(
        range(len(eligible_indices)),
        key=lambda index: (
            float(eligible_scores[index]),
            int(eligible_indices[index]),
        ),
    )
    best = int(eligible_indices[ordering[0]])
    best_score = float(scores[best])
    ties = [
        int(index)
        for index in eligible_indices
        if float(scores[index]) == best_score
    ]
    if best != min(ties):
        raise AssertionError("lowest-index exact tie rule drifted")
    margin = (
        None
        if len(ordering) < 2
        else float(eligible_scores[ordering[1]] - eligible_scores[ordering[0]])
    )
    return {
        "raw_atoms": atoms.tolist(),
        "scaled_atoms": scaled.tolist(),
        "clipped_atoms": clipped.tolist(),
        "weights": coefficient.tolist(),
        "scores": scores.tolist(),
        "eligibility_mask": raw_mask.tolist(),
        "eligible_indices": eligible_indices.astype(int).tolist(),
        "tie_set": ties,
        "selected_index": best,
        "selected_row_sha256": array_sha256(candidate[best]),
        "selected_action": candidate[best].tolist(),
        "selected_action_sha256": array_sha256(candidate[best]),
        "margin": (
            {
                "status": "computed",
                "value": margin,
                "reason": None,
            }
            if margin is not None
            else {
                "status": "typed_missing",
                "value": None,
                "reason": "fewer_than_two_eligible_for_margin",
            }
        ),
    }


def exact_repeat_fields(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: receipt[key]
        for key in (
            "candidate_tensor_sha256_before",
            "candidate_tensor_sha256_after",
            "neighbor_tensor_sha256_before",
            "neighbor_tensor_sha256_after",
            "atom_receipt_sha256",
            "context_receipt_sha256",
            "static14d",
            "scene14d",
        )
    }


def assert_same_state_determinism(receipts: Sequence[Mapping[str, Any]]) -> None:
    if len(receipts) != REPEATS_PER_STATE:
        raise ValueError("same-state repeat denominator drifted")
    if any(receipt.get("status") != "computed" for receipt in receipts):
        raise ValueError("same-state selector replay contains typed failure")
    expected = exact_repeat_fields(receipts[0])
    if any(exact_repeat_fields(receipt) != expected for receipt in receipts[1:]):
        raise ValueError("same-state selector replay nondeterminism")


def assert_python_runtime(
    *,
    executable: str,
    version_info: Sequence[int],
    prefix: str,
    expected_executable: str,
    expected_prefix: str,
    expected_exact_version: Sequence[int] | None = None,
) -> None:
    if executable != expected_executable or prefix != expected_prefix:
        raise RuntimeError("explicit Python runtime authority mismatch")
    version = tuple(int(value) for value in version_info[:3])
    if version < (3, 10):
        raise RuntimeError("Python >=3.10 is required")
    if expected_exact_version is not None and version != tuple(
        expected_exact_version
    ):
        raise RuntimeError("exact Python runtime version mismatch")
