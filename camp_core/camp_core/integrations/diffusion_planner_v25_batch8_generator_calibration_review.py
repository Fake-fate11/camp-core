"""Independent oracle for corrected same-input/same-latent repeatability.

This module deliberately does not import the producer calibration module.
It independently rebuilds the state/latent topology, generator-only endpoint
math, and frozen bootstrap threshold algorithm.
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


SCHEMA = "camp_dp_v25_batch8_generator_repeatability_corrected_contract_v1"
AUTHORITY = "eba03c38f8eb6272c9cc31de464b88752a94e622ac352ffe349c70726bbe4f77"
BASE_HEAD = "dc76fbc8ef9fe867cb2e05d7f0c7b44b74190685"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CHECKPOINT = "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
MODEL_SOURCE = "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
STATE_MANIFEST = "569718077a1c6c7f5193074ba86e646da4a3a40a2fdc573c7bfa51f3cfaa722f"
STATE_COUNT = 64
REPEATS = 5
LATENT_SHAPE = (8, 321, 81, 4)
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
F32 = np.dtype("<f4")
SOURCE_KEYS = {
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
ENDPOINT_ROWS = (
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


def source_specs() -> list[dict[str, Any]]:
    sampler_sha = hashlib.sha256(
        state_authority.INPUT_MANIFEST_MODULE.read_bytes()
    ).hexdigest()
    specs = state_authority._state_specs(  # noqa: SLF001
        "development_calibration", sampler_sha
    )
    if sha256_json(specs) != STATE_MANIFEST:
        raise ValueError("review state manifest drifted")
    return deepcopy(specs)


def canonical_seed(clone_key_sha256: str) -> int:
    _sha(clone_key_sha256)
    digest = hashlib.sha256(
        canonical_bytes(
            {
                "authority_sha256": AUTHORITY,
                "canonical_state_clone_key_sha256": clone_key_sha256,
                "purpose": (
                    "batch8_generator_repeatability_corrected_"
                    "canonical_state_latent_v1"
                ),
            }
        )
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def latent(clone_key_sha256: str) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(canonical_seed(
        clone_key_sha256
    )))
    value = np.zeros(LATENT_SHAPE, dtype=F32)
    value[1:] = rng.standard_normal(value[1:].shape).astype(F32)
    return np.ascontiguousarray(value)


def review_canonical_expansion(
    manifests: Sequence[Mapping[str, Any]],
) -> None:
    if len(manifests) != 320:
        raise ValueError("review expansion denominator drifted")
    for state_index in range(64):
        rows = [
            dict(row)
            for row in manifests
            if row.get("state_index") == state_index
        ]
        if len(rows) != 5 or {row.get("repeat_index") for row in rows} != {
            0, 1, 2, 3, 4
        }:
            raise ValueError("review repeat topology drifted")
        fields = (
            "input_npz_sha256",
            "canonical_record_sha256",
            "canonical_state_clone_key_sha256",
        )
        for field in fields:
            values = {row.get(field) for row in rows}
            if len(values) != 1:
                raise ValueError(f"review same-state {field} drifted")
            _sha(next(iter(values)))
        latent_shas = {
            row.get("latent_manifest", {}).get("tensor_sha256")
            for row in rows
        }
        if len(latent_shas) != 1:
            raise ValueError("review same-state latent SHA drifted")
        _sha(next(iter(latent_shas)))


def endpoint_registry() -> list[dict[str, Any]]:
    return [
        {
            "endpoint_id": endpoint_id,
            "source_tensor": (
                "candidate_tensor"
                if endpoint_id.startswith("candidate.")
                else "neighbor_tensor"
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
        for endpoint_id, formula, units, floor, shape in ENDPOINT_ROWS
    ]


def pair_errors(
    candidate_left: np.ndarray,
    neighbor_left: np.ndarray,
    candidate_right: np.ndarray,
    neighbor_right: np.ndarray,
) -> dict[str, float]:
    c0 = _tensor(candidate_left, CANDIDATE_SHAPE)
    c1 = _tensor(candidate_right, CANDIDATE_SHAPE)
    n0 = _tensor(neighbor_left, NEIGHBOR_SHAPE)
    n1 = _tensor(neighbor_right, NEIGHBOR_SHAPE)
    wrap = lambda x: (x + np.pi) % (2.0 * np.pi) - np.pi
    values = {
        "candidate.position_l2_max_m": np.linalg.norm(
            c0[..., :2].astype(np.float64) - c1[..., :2].astype(np.float64),
            axis=-1,
        ).max(),
        "candidate.heading_wrap_abs_max_rad": np.abs(
            wrap(c0[..., 2].astype(np.float64) - c1[..., 2].astype(np.float64))
        ).max(),
        "candidate.speed_abs_max_mps": np.abs(
            c0[..., 3].astype(np.float64) - c1[..., 3].astype(np.float64)
        ).max(),
        "neighbor.position_l2_max_m": np.linalg.norm(
            n0[..., :2].astype(np.float64) - n1[..., :2].astype(np.float64),
            axis=-1,
        ).max(),
        "neighbor.heading_wrap_abs_max_rad": np.abs(
            wrap(n0[..., 2].astype(np.float64) - n1[..., 2].astype(np.float64))
        ).max(),
        "neighbor.speed_abs_max_mps": np.abs(
            n0[..., 3].astype(np.float64) - n1[..., 3].astype(np.float64)
        ).max(),
    }
    return {key: float(value) for key, value in values.items()}


def state_q99(values: Sequence[float]) -> float:
    array = _vector(values, 10)
    return float(np.sort(array, kind="mergesort")[9])


def bootstrap(
    values: Sequence[float], floor: float
) -> tuple[float, float, str]:
    array = _vector(values, 64)
    floor = float(floor)
    if not math.isfinite(floor) or floor <= 0:
        raise ValueError("floor invalid")
    rng = np.random.Generator(np.random.PCG64DXSM(825071))
    indexes = rng.integers(
        0, 64, size=(10000, 64), endpoint=False, dtype=np.int64
    )
    per_draw = np.sort(array[indexes], axis=1, kind="mergesort")[:, 63]
    ucb = float(np.sort(per_draw, kind="mergesort")[9500])
    return (
        max(ucb, floor),
        ucb,
        sha256_bytes(indexes.astype("<i8").tobytes(order="C")),
    )


def review_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    contract = _object(value)
    payload = dict(contract)
    digest = payload.pop("contract_payload_sha256", None)
    if digest != sha256_json(payload):
        raise ValueError("contract payload SHA drifted")
    if (
        contract.get("schema_version") != SCHEMA
        or contract.get("authority_sha256") != AUTHORITY
        or contract.get("base_pointer_head") != BASE_HEAD
        or contract.get("fixed_dp_head") != DP_HEAD
        or contract.get("checkpoint_sha256") != CHECKPOINT
        or contract.get("model_source_sha256") != MODEL_SOURCE
    ):
        raise ValueError("contract identity drifted")
    _head(contract.get("implementation_head"))
    if set(contract.get("source_sha256", {})) != SOURCE_KEYS:
        raise ValueError("source keyset drifted")
    for value_sha in contract["source_sha256"].values():
        _sha(value_sha)
    if contract.get("endpoint_registry") != endpoint_registry():
        raise ValueError("endpoint semantic registry drifted")
    if contract.get("endpoint_registry_sha256") != sha256_json(endpoint_registry()):
        raise ValueError("endpoint registry SHA drifted")
    if contract.get("source_specification", {}).get("state_specs") != source_specs():
        raise ValueError("state specs drifted")
    generator = contract.get("generator", {})
    denominator = contract.get("denominator", {})
    boundary = contract.get("run_and_claim_boundary", {})
    if (
        generator.get("formal_model_invocations_per_run") != 1
        or generator.get("expanded_batch_size") != 8
        or generator.get("agent_as_ego_batch") is not False
        or generator.get("sequential_model_call_count") != 0
        or generator.get("selector_call_count") != 0
        or generator.get(
            "post_pool_model_dp_latent_candidate_generation_call_count"
        ) != 0
        or denominator.get("state_count") != 64
        or denominator.get("repeats_per_state") != 5
        or denominator.get("planned_run_count") != 320
        or denominator.get("pair_receipt_count") != 640
        or boundary.get("safetycost_or_old_ni_endpoint_count") != 0
        or boundary.get("atom_score_weight_selector_endpoint_count") != 0
        or boundary.get("claim_authorized") is not False
    ):
        raise ValueError("generator or denominator semantics drifted")
    latent_policy = contract.get("latent_policy", {})
    if (
        latent_policy.get("canonical_state_latent_record_count") != 64
        or latent_policy.get("expanded_run_manifest_count") != 320
        or latent_policy.get(
            "same_state_five_repeat_input_sha_cardinality"
        ) != 1
        or latent_policy.get(
            "same_state_five_repeat_latent_tensor_sha_cardinality"
        ) != 1
        or "repeat_index" not in latent_policy.get("forbidden_seed_fields", [])
        or "repeat_index" in latent_policy.get(
            "canonical_state_seed_formula", ""
        )
    ):
        raise ValueError("canonical latent reuse semantics drifted")
    threshold = contract.get("threshold_algorithm", {})
    if threshold != {
        "state_pair_count": 10,
        "state_statistic": "q0.99_higher_sorted_index_9",
        "state_count": 64,
        "bootstrap_rng": "numpy.random.Generator(PCG64DXSM(825071))",
        "bootstrap_resamples": 10000,
        "bootstrap_draw": (
            "integers(0,64,size=(10000,64),endpoint=False,dtype=int64)"
        ),
        "bootstrap_statistic": "q0.99_higher_sorted_index_63",
        "one_sided_95_upper_index_zero_based": 9500,
        "final_threshold": "max(bootstrap_ucb,resolution_floor)",
        "comparison": "pair_error <= threshold_is_within_envelope",
        "interpretation": (
            "bounded_development_corrected_same_input_same_latent_"
            "generator_repeatability_envelope_not_validation_"
            "equivalence_or_effect_claim"
        ),
    }:
        raise ValueError("threshold semantics drifted")
    return {
        "schema_version": (
            "camp_dp_v25_batch8_generator_repeatability_corrected_contract_"
            "independent_review_v1"
        ),
        "status": "PASS",
        "authority_sha256": AUTHORITY,
        "contract_payload_sha256": digest,
        "state_manifest_sha256": STATE_MANIFEST,
        "state_count": 64,
        "run_count": 320,
        "pair_count": 640,
        "endpoint_count": 6,
        "producer_module_imported": False,
        "selector_or_effect_endpoint_count": 0,
        "claim_authorized": False,
    }


def review_latent_manifest(
    value: Mapping[str, Any],
    state_spec_sha256: str,
    clone_key_sha256: str,
) -> None:
    expected = latent(clone_key_sha256)
    rows = [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in expected
    ]
    supplied = dict(_object(value))
    manifest_sha = supplied.pop("manifest_sha256", None)
    if manifest_sha != sha256_json(supplied):
        raise ValueError("latent manifest SHA drifted")
    if (
        supplied.get("authority_sha256") != AUTHORITY
        or supplied.get("state_spec_sha256") != state_spec_sha256
        or supplied.get("canonical_state_clone_key_sha256")
        != clone_key_sha256
        or supplied.get("seed") != canonical_seed(clone_key_sha256)
        or supplied.get("shape") != list(LATENT_SHAPE)
        or supplied.get("dtype") != F32.str
        or supplied.get("row0_all_zero") is not True
        or supplied.get("finite") is not True
        or supplied.get("tensor_sha256")
        != sha256_bytes(expected.tobytes(order="C"))
        or supplied.get("row_sha256") != rows
        or supplied.get("unique_row_sha256_count") != 8
        or supplied.get("duplicate_groups") != []
        or supplied.get("repeat_dependent_field_count") != 0
    ):
        raise ValueError("latent manifest semantic drifted")


def _tensor(value: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
    array = np.ascontiguousarray(np.asarray(value))
    if array.shape != shape or array.dtype != F32:
        raise ValueError("tensor shape/dtype drifted")
    if not bool(np.isfinite(array).all()):
        raise ValueError("tensor nonfinite")
    return array


def _vector(value: Sequence[float], size: int) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != (size,) or not bool(np.isfinite(array).all()):
        raise ValueError("vector invalid")
    if bool(np.any(array < 0)):
        raise ValueError("vector negative")
    return array


def _object(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValueError("object required")
    canonical_bytes(value)
    return dict(value)


def _sha(value: Any) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("SHA256 required")
    return value


def _head(value: Any) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("git SHA required")
    return value
