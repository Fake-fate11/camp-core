"""Generator-only same-ego batch8 calibration contract and pure kernels.

This module is outcome-independent.  It defines the sole 64-state x 5-repeat
batch8 generator calibration authorized by High decision 677c3792... .  It
contains no selector, SafetyCost, scientific-effect, training-support or
closed-loop endpoint.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from camp_core.integrations import (
    diffusion_planner_v25_fair_pool_adaptation_contract_v3 as state_authority,
)


SCHEMA_VERSION = "camp_dp_v25_batch8_generator_calibration_contract_v1"
PREFLIGHT_SCHEMA = "camp_dp_v25_batch8_generator_calibration_preflight_v1"
RAW_SCHEMA = "camp_dp_v25_batch8_generator_calibration_raw_v1"
RAW_REVIEW_SCHEMA = (
    "camp_dp_v25_batch8_generator_calibration_raw_independent_review_v1"
)
THRESHOLD_SCHEMA = "camp_dp_v25_batch8_generator_calibration_threshold_v1"
AUTHORITY_SHA256 = (
    "677c3792f52cd817871b6c9948360edced81198d4207cd59b22050080697ee21"
)
BASE_POINTER_HEAD = "989c9c75c6e90bf11aff92d1429f3daa9e6ee646"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CHECKPOINT_SHA256 = (
    "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
)
MODEL_SOURCE_SHA256 = (
    "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
)
SOURCE_SPEC_MANIFEST_SHA256 = (
    "569718077a1c6c7f5193074ba86e646da4a3a40a2fdc573c7bfa51f3cfaa722f"
)
OLD_PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)
OLD_PREFLIGHT_REVIEW_ROOT = (
    "ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3"
)
OLD_NONHOLDOUT_ROOT = (
    "29688aa7ff4eb5edf43ca2379063f45228faedea80a7a3245e07aba297cc9dfd"
)
INDUSTRIAL_V3_ROOTS = {
    "contract": "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb",
    "review": "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556",
}
BATCH8_PRIMARY_ROOTS = {
    "contract": "15cf642f5abcb1cd44687e8f4298517f47e8c878633602e9b42fcffe7c30e5d7",
    "review": "a0cd179311b5ce1fd18b7e764154d92041bfda57216c0be2365aa20100133978",
}
FIRST_STATE_ROOTS = {
    "diagnostic": "6a9e1a364b6d25716a471d34039553b11521c2d911563df0e3ee0edf1ed3eec5",
    "review": "92e33a3e1747764a65d6d6b8e38645f7faa9825b2b08c980255025ac840073c3",
}
BATCH8_DESIGN_ROOTS = {
    "contract": "f4216e9e59d7cc81cf8d7ebd69e0bdd38b1399ec11d6fe95866994b309d53c1c",
    "review": "8f2b198be18ef01607f4e355e014f3de07f049981ee05c0c18b96017b9237457",
}

STATE_COUNT = 64
REPEAT_COUNT = 5
RUN_COUNT = 320
PAIR_COUNT_PER_STATE = 10
PAIR_COUNT = 640
LATENT_SHAPE = (8, 321, 81, 4)
LATENT_DTYPE = np.dtype("<f4")
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
OUTPUT_DTYPE = np.dtype("<f4")
BOOTSTRAP_SEED = 825071
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_UPPER_INDEX = 9500
CAPACITY_FLOOR_BYTES = 10 * 1024**3

EXACT_DIRS = {
    "contract": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_contract_v1_989c9c75"
    ),
    "contract_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_contract_v1_review_989c9c75"
    ),
    "focused": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_focused_v1_989c9c75"
    ),
    "preflight": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_preflight_v1_989c9c75"
    ),
    "preflight_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_preflight_v1_review_989c9c75"
    ),
    "raw": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_raw_v1_989c9c75"
    ),
    "raw_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_raw_v1_review_989c9c75"
    ),
    "threshold": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_threshold_v1_989c9c75"
    ),
    "threshold_review": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_threshold_v1_review_989c9c75"
    ),
    "final_docs": (
        "/root/autodl-tmp/"
        "camp_dp_v25_batch8_generator_calibration_final_docs_v1_989c9c75"
    ),
}


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
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_specs() -> list[dict[str, Any]]:
    sampler_sha = hashlib.sha256(
        state_authority.INPUT_MANIFEST_MODULE.read_bytes()
    ).hexdigest()
    result = state_authority._state_specs(  # noqa: SLF001
        "development_calibration", sampler_sha
    )
    if sha256_json(result) != SOURCE_SPEC_MANIFEST_SHA256:
        raise RuntimeError("64-state source-spec manifest drifted")
    return deepcopy(result)


def repeat_latent_seed(state_spec_sha256: str, repeat_index: int) -> int:
    _sha(state_spec_sha256, "state spec SHA")
    if type(repeat_index) is not int or not 0 <= repeat_index < REPEAT_COUNT:
        raise ValueError("repeat index drifted")
    digest = hashlib.sha256(
        canonical_bytes(
            {
                "authority_sha256": AUTHORITY_SHA256,
                "purpose": "batch8_generator_calibration_unique_latent_v1",
                "repeat_index": repeat_index,
                "state_spec_sha256": state_spec_sha256,
            }
        )
    ).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def latent_tensor(state_spec_sha256: str, repeat_index: int) -> np.ndarray:
    seed = repeat_latent_seed(state_spec_sha256, repeat_index)
    rng = np.random.Generator(np.random.PCG64(seed))
    latent = np.zeros(LATENT_SHAPE, dtype=LATENT_DTYPE)
    latent[1:] = rng.standard_normal(latent[1:].shape).astype(LATENT_DTYPE)
    return np.ascontiguousarray(latent)


def tensor_summary(value: np.ndarray) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value))
    row_sha = [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in array
    ]
    nonfinite = np.argwhere(~np.isfinite(array)).astype(int).tolist()
    groups: dict[str, list[int]] = {}
    for index, digest in enumerate(row_sha):
        groups.setdefault(digest, []).append(index)
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "byte_count": int(array.nbytes),
        "tensor_sha256": sha256_bytes(array.tobytes(order="C")),
        "row_sha256": row_sha,
        "unique_row_sha256_count": len(set(row_sha)),
        "duplicate_groups": [
            indices
            for indices in sorted(groups.values(), key=lambda row: row[0])
            if len(indices) > 1
        ],
        "nonfinite_indices": nonfinite,
        "nonfinite_count": len(nonfinite),
    }


def latent_manifest(state_spec_sha256: str, repeat_index: int) -> dict[str, Any]:
    latent = latent_tensor(state_spec_sha256, repeat_index)
    summary = tensor_summary(latent)
    result = {
        "schema_version": (
            "camp_dp_v25_batch8_generator_calibration_latent_manifest_v1"
        ),
        "authority_sha256": AUTHORITY_SHA256,
        "state_spec_sha256": state_spec_sha256,
        "repeat_index": repeat_index,
        "seed": repeat_latent_seed(state_spec_sha256, repeat_index),
        "bit_generator": "numpy.random.PCG64",
        "policy": (
            "row0_zero_rows1_7_independent_pcg64_standard_normal_float32"
        ),
        "shape": list(LATENT_SHAPE),
        "dtype": LATENT_DTYPE.str,
        "row0_all_zero": bool(np.count_nonzero(latent[0]) == 0),
        "finite": summary["nonfinite_count"] == 0,
        "tensor_sha256": summary["tensor_sha256"],
        "row_sha256": summary["row_sha256"],
        "unique_row_sha256_count": summary["unique_row_sha256_count"],
        "duplicate_groups": summary["duplicate_groups"],
    }
    result["manifest_sha256"] = sha256_json(result)
    return result


def run_id(state_index: int, repeat_index: int) -> str:
    if type(state_index) is not int or not 0 <= state_index < STATE_COUNT:
        raise ValueError("state index drifted")
    if type(repeat_index) is not int or not 0 <= repeat_index < REPEAT_COUNT:
        raise ValueError("repeat index drifted")
    return (
        f"development_calibration:{state_index:03d}:"
        f"single_invocation_batch8:repeat{repeat_index}"
    )


def planned_run_ids() -> list[str]:
    return [
        run_id(state_index, repeat_index)
        for state_index in range(STATE_COUNT)
        for repeat_index in range(REPEAT_COUNT)
    ]


def endpoint_registry() -> list[dict[str, Any]]:
    rows = [
        (
            "candidate.position_l2_max_m",
            "max(norm(a[...,0:2]-b[...,0:2],axis=-1))",
            "m",
            1e-4,
            "[8,80,4]_float32_pair",
        ),
        (
            "candidate.heading_wrap_abs_max_rad",
            "max(abs(wrap_to_pi(a[...,2]-b[...,2])))",
            "rad",
            1e-5,
            "[8,80,4]_float32_pair",
        ),
        (
            "candidate.speed_abs_max_mps",
            "max(abs(a[...,3]-b[...,3]))",
            "m/s",
            1e-4,
            "[8,80,4]_float32_pair",
        ),
        (
            "neighbor.position_l2_max_m",
            "max(norm(a[...,0:2]-b[...,0:2],axis=-1))",
            "m",
            1e-4,
            "[8,32,80,4]_float32_pair",
        ),
        (
            "neighbor.heading_wrap_abs_max_rad",
            "max(abs(wrap_to_pi(a[...,2]-b[...,2])))",
            "rad",
            1e-5,
            "[8,32,80,4]_float32_pair",
        ),
        (
            "neighbor.speed_abs_max_mps",
            "max(abs(a[...,3]-b[...,3]))",
            "m/s",
            1e-4,
            "[8,32,80,4]_float32_pair",
        ),
    ]
    return [
        {
            "endpoint_id": endpoint_id,
            "source_tensor": (
                "candidate_tensor" if endpoint_id.startswith("candidate.") else "neighbor_tensor"
            ),
            "formula": formula,
            "units": units,
            "input_shape_dtype": shape,
            "direction": "lower",
            "resolution_floor": floor,
            "applicability": (
                "both_repeat_tensors_exact_shape_float32_finite;"
                "neighbor_actor_slot_order_identical_for_neighbor_endpoints"
            ),
            "missing_policy": (
                "typed_missing_retained_and_threshold_unavailable_no_drop"
            ),
            "within_state_aggregation": (
                "10_unordered_repeat_pairs_sorted_higher_q99_index_9"
            ),
            "cross_state_aggregation": (
                "64_state_q99_values_bootstrap_ucb_then_max_resolution_floor"
            ),
            "selector_or_effect_endpoint": False,
        }
        for endpoint_id, formula, units, floor, shape in rows
    ]


def wrap_to_pi(value: np.ndarray) -> np.ndarray:
    return (value + np.pi) % (2.0 * np.pi) - np.pi


def pair_errors(
    candidate_left: np.ndarray,
    neighbor_left: np.ndarray,
    candidate_right: np.ndarray,
    neighbor_right: np.ndarray,
) -> dict[str, float]:
    c0 = _tensor(candidate_left, CANDIDATE_SHAPE, "candidate left")
    c1 = _tensor(candidate_right, CANDIDATE_SHAPE, "candidate right")
    n0 = _tensor(neighbor_left, NEIGHBOR_SHAPE, "neighbor left")
    n1 = _tensor(neighbor_right, NEIGHBOR_SHAPE, "neighbor right")
    values = {
        "candidate.position_l2_max_m": np.linalg.norm(
            c0[..., :2].astype(np.float64) - c1[..., :2].astype(np.float64),
            axis=-1,
        ).max(),
        "candidate.heading_wrap_abs_max_rad": np.abs(
            wrap_to_pi(
                c0[..., 2].astype(np.float64) - c1[..., 2].astype(np.float64)
            )
        ).max(),
        "candidate.speed_abs_max_mps": np.abs(
            c0[..., 3].astype(np.float64) - c1[..., 3].astype(np.float64)
        ).max(),
        "neighbor.position_l2_max_m": np.linalg.norm(
            n0[..., :2].astype(np.float64) - n1[..., :2].astype(np.float64),
            axis=-1,
        ).max(),
        "neighbor.heading_wrap_abs_max_rad": np.abs(
            wrap_to_pi(
                n0[..., 2].astype(np.float64) - n1[..., 2].astype(np.float64)
            )
        ).max(),
        "neighbor.speed_abs_max_mps": np.abs(
            n0[..., 3].astype(np.float64) - n1[..., 3].astype(np.float64)
        ).max(),
    }
    result = {key: float(value) for key, value in values.items()}
    if set(result) != {row["endpoint_id"] for row in endpoint_registry()}:
        raise AssertionError("pair endpoint set drifted")
    if any(not math.isfinite(value) or value < 0.0 for value in result.values()):
        raise ValueError("pair endpoint value invalid")
    return result


def state_q99_higher(values: Sequence[float]) -> float:
    vector = _finite_vector(values, PAIR_COUNT_PER_STATE, "state pair errors")
    return float(np.sort(vector, kind="mergesort")[9])


def bootstrap_ucb(
    state_q99_values: Sequence[float], *, resolution_floor: float
) -> tuple[float, float, str]:
    values = _finite_vector(state_q99_values, STATE_COUNT, "state q99 values")
    floor = _positive(resolution_floor, "resolution floor")
    rng = np.random.Generator(np.random.PCG64DXSM(BOOTSTRAP_SEED))
    indices = rng.integers(
        0,
        STATE_COUNT,
        size=(BOOTSTRAP_RESAMPLES, STATE_COUNT),
        endpoint=False,
        dtype=np.int64,
    )
    statistics = np.sort(values[indices], axis=1, kind="mergesort")[:, 63]
    ordered = np.sort(statistics, kind="mergesort")
    upper = float(ordered[BOOTSTRAP_UPPER_INDEX])
    preimage_sha = sha256_bytes(indices.astype("<i8").tobytes(order="C"))
    return max(upper, floor), upper, preimage_sha


def typed_missing(reason: str) -> dict[str, Any]:
    allowed = {
        "candidate_shape_dtype",
        "candidate_nonfinite",
        "candidate_nondiverse",
        "neighbor_shape_dtype",
        "neighbor_nonfinite",
        "run_receipt_unavailable",
    }
    if reason not in allowed:
        raise ValueError("unknown typed-missing reason")
    return {"status": "evidence_missing", "value": None, "reason": reason}


def typed_value(value: float) -> dict[str, Any]:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise ValueError("typed value must be finite nonnegative")
    return {"status": "computed", "value": numeric, "reason": None}


def validate_typed_scalar(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {"status", "value", "reason"}:
        raise ValueError("typed scalar schema drifted")
    if value["status"] == "computed":
        if value["reason"] is not None:
            raise ValueError("computed scalar reason must be null")
        typed_value(value["value"])
    elif value["status"] == "evidence_missing":
        if value["value"] is not None:
            raise ValueError("missing scalar value must be null")
        typed_missing(value["reason"])
    else:
        raise ValueError("typed scalar status drifted")
    canonical_bytes(dict(value))
    return dict(value)


def contract(
    *,
    implementation_head: str,
    source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    _head(implementation_head, "implementation head")
    expected_source_keys = {
        "producer_module",
        "reviewer_module",
        "freeze_script",
        "contract_review_script",
        "preflight_script",
        "preflight_review_script",
        "raw_script",
        "raw_review_script",
        "threshold_script",
        "threshold_review_script",
        "tests",
    }
    if type(source_sha256) is not dict or set(source_sha256) != expected_source_keys:
        raise ValueError("source SHA keyset drifted")
    sources = {key: _sha(value, key) for key, value in source_sha256.items()}
    specs = source_specs()
    registry = endpoint_registry()
    value = {
        "schema_version": SCHEMA_VERSION,
        "status": "frozen_generator_only_calibration_authorized",
        "authority_sha256": AUTHORITY_SHA256,
        "base_pointer_head": BASE_POINTER_HEAD,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "model_source_sha256": MODEL_SOURCE_SHA256,
        "accepted_roots": {
            "industrial_v3": INDUSTRIAL_V3_ROOTS,
            "batch8_primary": BATCH8_PRIMARY_ROOTS,
            "first_state": FIRST_STATE_ROOTS,
            "batch8_design": BATCH8_DESIGN_ROOTS,
            "old_input_preflight": OLD_PREFLIGHT_ROOT,
            "old_input_preflight_review": OLD_PREFLIGHT_REVIEW_ROOT,
            "old_nonholdout": OLD_NONHOLDOUT_ROOT,
        },
        "source_sha256": sources,
        "exact_dirs": EXACT_DIRS,
        "generator": {
            "name": "new_single_invocation_batched_k8_candidate_pool",
            "mode": "single_invocation_batch8",
            "candidate_axis": "same_ego_expanded_batch_dimension_B_equals_8",
            "formal_model_invocations_per_run": 1,
            "source_ego_state_count_per_run": 1,
            "expanded_batch_size": 8,
            "agent_as_ego_batch": False,
            "sequential_model_call_count": 0,
            "selector_call_count": 0,
            "post_pool_model_dp_latent_candidate_generation_call_count": 0,
            "candidate0_binding": "row0_only_not_executed_as_selector",
        },
        "denominator": {
            "state_count": STATE_COUNT,
            "repeats_per_state": REPEAT_COUNT,
            "planned_run_count": RUN_COUNT,
            "planned_formal_model_call_count": RUN_COUNT,
            "unordered_pairs_per_state": PAIR_COUNT_PER_STATE,
            "pair_receipt_count": PAIR_COUNT,
            "independent_statistical_unit": "state",
            "rows_repeats_ticks_are_not_independent_n": True,
            "failure_retention": (
                "all_320_slots_retained_no_drop_replace_complete_case"
            ),
        },
        "source_specification": {
            "manifest_sha256": SOURCE_SPEC_MANIFEST_SHA256,
            "state_specs": specs,
            "identity_reuse_scope": (
                "authorized_unexecuted_development_calibration_source_specs_only"
            ),
            "future_validation_model_call_count": 0,
        },
        "latent_policy": {
            "shape": list(LATENT_SHAPE),
            "dtype": LATENT_DTYPE.str,
            "policy": (
                "row0_zero_rows1_7_independent_pcg64_standard_normal_float32"
            ),
            "repeat_seed_formula": (
                "uint64_be(sha256(canonical({authority_sha256,purpose,"
                "repeat_index,state_spec_sha256}))[0:8])"
            ),
            "all_320_preimages_sealed_before_model": True,
            "finite_unique8_required": True,
        },
        "output_contract": {
            "candidate_shape": list(CANDIDATE_SHAPE),
            "neighbor_shape": list(NEIGHBOR_SHAPE),
            "dtype": OUTPUT_DTYPE.str,
            "candidate_finite_unique8_required": True,
            "neighbor_finite_required": True,
            "candidate_tensor_immutable_after_pool": True,
        },
        "endpoint_registry": registry,
        "endpoint_registry_sha256": sha256_json(registry),
        "threshold_algorithm": {
            "state_pair_count": PAIR_COUNT_PER_STATE,
            "state_statistic": "q0.99_higher_sorted_index_9",
            "state_count": STATE_COUNT,
            "bootstrap_rng": "numpy.random.Generator(PCG64DXSM(825071))",
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "bootstrap_draw": (
                "integers(0,64,size=(10000,64),endpoint=False,dtype=int64)"
            ),
            "bootstrap_statistic": "q0.99_higher_sorted_index_63",
            "one_sided_95_upper_index_zero_based": BOOTSTRAP_UPPER_INDEX,
            "final_threshold": "max(bootstrap_ucb,resolution_floor)",
            "comparison": "pair_error <= threshold_is_within_envelope",
            "interpretation": (
                "bounded_development_repeatability_envelope_not_validation_"
                "equivalence_or_effect_claim"
            ),
        },
        "preflight": {
            "actual_run_manifest_count": RUN_COUNT,
            "zero_overlap_dimensions": [
                "route",
                "state",
                "geometry",
                "source",
                "scenario_seed",
                "latent_instance",
            ],
            "old_unexecuted_source_spec_identity_reuse_is_authorized": True,
            "training_future_validation_old_executed_nonholdout_fresh_overlap": 0,
            "capacity_floor_bytes": CAPACITY_FLOOR_BYTES,
            "complete_report_serialization_seal_review_dry_run_required": True,
            "model_call_count_before_receipt": 0,
        },
        "review": {
            "reviewer_imports_producer_module": False,
            "rebuilds_320_input_latent_preimages": True,
            "rebuilds_320_raw_tensors_and_640_pair_values": True,
            "rebuilds_threshold_bootstrap_preimage": True,
        },
        "run_and_claim_boundary": {
            "safetycost_or_old_ni_endpoint_count": 0,
            "industrial_v3_effect_endpoint_count": 0,
            "atom_score_weight_selector_endpoint_count": 0,
            "training_support_authorized": False,
            "validation_closed_loop_fresh_holdout_training_authorized": False,
            "outcome_read_authorized": False,
            "old_artifact_or_cas_write_authorized": False,
            "claim_authorized": False,
            "pass_scope": (
                "bounded_64_state_batch8_generator_calibration_full_"
                "denominator_and_independently_reviewed_repeatability_envelope"
            ),
        },
    }
    value["contract_payload_sha256"] = sha256_json(value)
    return value


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("contract must be object")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("contract schema drifted")
    supplied = deepcopy(dict(value))
    digest = supplied.pop("contract_payload_sha256", None)
    if digest != sha256_json(supplied):
        raise ValueError("contract payload SHA drifted")
    expected = contract(
        implementation_head=value["implementation_head"],
        source_sha256=value["source_sha256"],
    )
    if value != expected:
        raise ValueError("contract semantic drifted")
    return deepcopy(dict(value))


def _tensor(value: np.ndarray, shape: tuple[int, ...], label: str) -> np.ndarray:
    array = np.ascontiguousarray(np.asarray(value))
    if array.shape != shape or array.dtype != OUTPUT_DTYPE:
        raise ValueError(f"{label} shape/dtype drifted")
    if not bool(np.isfinite(array).all()):
        raise ValueError(f"{label} nonfinite")
    return array


def _finite_vector(values: Sequence[float], size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.shape != (size,) or not bool(np.isfinite(array).all()):
        raise ValueError(f"{label} must be finite length {size}")
    if bool(np.any(array < 0.0)):
        raise ValueError(f"{label} must be nonnegative")
    return array


def _positive(value: float, label: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise ValueError(f"{label} must be finite positive")
    return numeric


def _sha(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase SHA256")
    return value


def _head(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be lowercase git SHA")
    return value
