from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import numpy as np


SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_calibration_first_state_diagnostic_receipt_v1"
)
CONTRACT_SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_calibration_first_state_diagnostic_contract_v1"
)
HIGH_AUTHORITY_SHA256 = (
    "3a72e639152b3416f7ef769f20dee05a2334d160b866ada4bd609c0c801277c8"
)
STATE_SPEC_ID = "development_calibration:000"
MODE = "sequential_batch1_x8"
REPEAT_INDEX = 0
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
DTYPE = "<f4"
SUBCONDITIONS = (
    "candidate_tensor_contains_nonfinite_value",
    "neighbor_tensor_contains_nonfinite_value",
    "candidate_row_sha256_not_unique_across_k8",
)
BINDING_FIELDS = {
    "input_manifest_sha256",
    "actual_input_tensor_bundle_sha256",
    "actual_state_sha256",
    "latent_tensor_sha256",
    "model_source_sha256",
    "checkpoint_sha256",
    "fixed_dp_head",
    "forward_ids",
}


def _canonical(value: Any) -> bytes:
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


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _decode(value: bytes, shape: tuple[int, ...]) -> np.ndarray:
    if len(value) != int(np.prod(shape)) * 4:
        raise ValueError("review tensor byte count drifted")
    return np.frombuffer(value, dtype=DTYPE).reshape(shape).copy()


def _indices(value: np.ndarray) -> list[list[int]]:
    return np.argwhere(~np.isfinite(value)).astype(int).tolist()


def _row_shas(candidate: np.ndarray) -> list[str]:
    return [
        _sha(np.ascontiguousarray(row).tobytes(order="C"))
        for row in candidate
    ]


def _groups(shas: list[str]) -> list[list[int]]:
    groups: dict[str, list[int]] = {}
    for index, digest in enumerate(shas):
        groups.setdefault(digest, []).append(index)
    return sorted(
        [indices for indices in groups.values() if len(indices) > 1],
        key=lambda indices: indices[0],
    )


def review_contract_literal(contract: Mapping[str, Any]) -> dict[str, Any]:
    if contract.get("schema_version") != CONTRACT_SCHEMA_VERSION:
        raise ValueError("review contract schema drifted")
    if contract.get("high_authority_sha256") != HIGH_AUTHORITY_SHA256:
        raise ValueError("review High authority drifted")
    authority_json = contract.get("high_authority_json")
    if (
        not isinstance(authority_json, str)
        or _sha(authority_json.encode("ascii")) != HIGH_AUTHORITY_SHA256
    ):
        raise ValueError("review High authority bytes drifted")
    authority = json.loads(authority_json)
    if (
        authority.get("authorized_state_spec_id") != STATE_SPEC_ID
        or authority.get("authorized_mode") != MODE
        or authority.get("authorized_repeat_index") != REPEAT_INDEX
        or authority.get("model_call_count") != 8
        or authority.get("selector_call_count") != 0
        or authority.get("remaining_639_runs_authorized") is not False
        or authority.get("receipt_must_precede_raise") is not True
    ):
        raise ValueError("review High authority semantic drifted")
    tensor = contract.get("tensor_contract")
    if tensor != {
        "candidate_shape": [8, 80, 4],
        "candidate_dtype": DTYPE,
        "neighbor_shape": [8, 32, 80, 4],
        "neighbor_dtype": DTYPE,
        "candidate_row_count": 8,
        "nonfinite_index_enumeration": "numpy_argwhere_c_order",
        "candidate_row_sha256": "sha256_exact_little_endian_float32_row_bytes",
        "duplicate_groups": "equal_row_sha256_grouped_by_ascending_row_index",
    }:
        raise ValueError("review tensor contract drifted")
    if contract.get("required_bindings") != [
        "input_manifest_sha256",
        "actual_input_tensor_bundle_sha256",
        "actual_state_sha256",
        "latent_tensor_sha256",
        "model_source_sha256",
        "checkpoint_sha256",
        "fixed_dp_head",
        "forward_ids",
    ]:
        raise ValueError("review binding contract drifted")
    if contract.get("forward_id_contract") != {
        "hash": "sha256_canonical_json",
        "row_count": 8,
        "fields": [
            "state_spec_id",
            "mode",
            "repeat_index",
            "row_index",
            "input_manifest_sha256",
            "actual_input_tensor_bundle_sha256",
            "actual_state_sha256",
            "latent_tensor_sha256",
            "model_source_sha256",
            "checkpoint_sha256",
            "fixed_dp_head",
            "candidate_row_sha256",
            "neighbor_row_sha256",
        ],
    }:
        raise ValueError("review forward ID contract drifted")
    if contract.get("possible_subconditions") != list(SUBCONDITIONS):
        raise ValueError("review subcondition contract drifted")
    for field in (
        "stop_before_selector",
        "producer_and_reviewer_recompute_from_tensor_bytes",
        "receipt_must_precede_raise",
        "prior_attempt_closeout_immutable",
    ):
        if contract.get(field) is not True:
            raise ValueError(f"review required true field drifted: {field}")
    for field in (
        "remaining_639_runs_authorized",
        "threshold_materialization_authorized",
        "validation_authorized",
        "closed_loop_authorized",
        "fresh_or_holdout_authorized",
        "training_or_retraining_authorized",
        "fixed_dp_weights_atoms_contract_change_authorized",
    ):
        if contract.get(field) is not False:
            raise ValueError(f"review prohibited field drifted: {field}")
    return {
        "status": "passed",
        "literal_contract_rebuilt": True,
        "producer_metric_or_model_imported": False,
    }


def review_receipt_from_tensor_bytes(
    receipt: Mapping[str, Any],
    *,
    candidate_bytes: bytes,
    neighbor_bytes: bytes,
) -> dict[str, Any]:
    candidate = _decode(candidate_bytes, CANDIDATE_SHAPE)
    neighbor = _decode(neighbor_bytes, NEIGHBOR_SHAPE)
    candidate_indices = _indices(candidate)
    neighbor_indices = _indices(neighbor)
    row_shas = _row_shas(candidate)
    groups = _groups(row_shas)
    conditions = {
        SUBCONDITIONS[0]: bool(candidate_indices),
        SUBCONDITIONS[1]: bool(neighbor_indices),
        SUBCONDITIONS[2]: bool(groups),
    }
    if (
        receipt.get("schema_version") != SCHEMA_VERSION
        or receipt.get("authority_sha256") != HIGH_AUTHORITY_SHA256
        or receipt.get("state_spec_id") != STATE_SPEC_ID
        or receipt.get("mode") != MODE
        or receipt.get("repeat_index") != REPEAT_INDEX
        or receipt.get("candidate_shape") != list(CANDIDATE_SHAPE)
        or receipt.get("candidate_dtype") != DTYPE
        or receipt.get("candidate_byte_count") != len(candidate_bytes)
        or receipt.get("candidate_tensor_sha256") != _sha(candidate_bytes)
        or receipt.get("candidate_nonfinite_indices") != candidate_indices
        or receipt.get("candidate_nonfinite_count") != len(candidate_indices)
        or receipt.get("candidate_row_sha256") != row_shas
        or receipt.get("candidate_row_sha256_unique_cardinality")
        != len(set(row_shas))
        or receipt.get("candidate_duplicate_groups") != groups
        or receipt.get("neighbor_shape") != list(NEIGHBOR_SHAPE)
        or receipt.get("neighbor_dtype") != DTYPE
        or receipt.get("neighbor_byte_count") != len(neighbor_bytes)
        or receipt.get("neighbor_tensor_sha256") != _sha(neighbor_bytes)
        or receipt.get("neighbor_nonfinite_indices") != neighbor_indices
        or receipt.get("neighbor_nonfinite_count") != len(neighbor_indices)
        or receipt.get("model_call_count") != 8
        or receipt.get("selector_call_count") != 0
        or receipt.get("subconditions") != conditions
        or receipt.get("compound_gate_triggered") != any(conditions.values())
        or receipt.get("resolved_subconditions")
        != [name for name in SUBCONDITIONS if conditions[name]]
        or receipt.get("receipt_formed_before_any_raise") is not True
        or receipt.get("stop_before_selector") is not True
        or receipt.get("remaining_calibration_run_count_authorized") != 0
        or receipt.get("threshold_materialization_authorized") is not False
        or receipt.get("validation_authorized") is not False
        or receipt.get("fresh_or_holdout_authorized") is not False
        or receipt.get("training_or_retraining_authorized") is not False
        or receipt.get("raw_outcome_read") is not False
    ):
        raise ValueError("review receipt semantic reconstruction mismatch")
    bindings = receipt.get("bindings")
    if not isinstance(bindings, dict) or set(bindings) != BINDING_FIELDS:
        raise ValueError("review binding field set drifted")
    for field in BINDING_FIELDS - {"forward_ids"}:
        if not _is_sha(bindings[field]):
            raise ValueError("review binding SHA drifted")
    forward_ids = bindings["forward_ids"]
    if (
        not isinstance(forward_ids, list)
        or len(forward_ids) != 8
        or any(not _is_sha(value) for value in forward_ids)
        or len(set(forward_ids)) != 8
    ):
        raise ValueError("review forward bindings drifted")
    neighbor_row_shas = [
        _sha(np.ascontiguousarray(row).tobytes(order="C")) for row in neighbor
    ]
    expected_forward_ids = []
    for row_index in range(8):
        expected_forward_ids.append(
            _sha(
                _canonical(
                    {
                        "state_spec_id": STATE_SPEC_ID,
                        "mode": MODE,
                        "repeat_index": REPEAT_INDEX,
                        "row_index": row_index,
                        "input_manifest_sha256": bindings[
                            "input_manifest_sha256"
                        ],
                        "actual_input_tensor_bundle_sha256": bindings[
                            "actual_input_tensor_bundle_sha256"
                        ],
                        "actual_state_sha256": bindings["actual_state_sha256"],
                        "latent_tensor_sha256": bindings["latent_tensor_sha256"],
                        "model_source_sha256": bindings["model_source_sha256"],
                        "checkpoint_sha256": bindings["checkpoint_sha256"],
                        "fixed_dp_head": bindings["fixed_dp_head"],
                        "candidate_row_sha256": row_shas[row_index],
                        "neighbor_row_sha256": neighbor_row_shas[row_index],
                    }
                )
            )
        )
    if forward_ids != expected_forward_ids:
        raise ValueError("review forward IDs do not match tensor bytes")
    payload_without_hash = dict(receipt)
    receipt_sha = payload_without_hash.pop("receipt_sha256", None)
    if receipt_sha != _sha(_canonical(payload_without_hash)):
        raise ValueError("review receipt self hash drifted")
    return {
        "status": "passed",
        "candidate_nonfinite_count": len(candidate_indices),
        "neighbor_nonfinite_count": len(neighbor_indices),
        "candidate_row_sha256_unique_cardinality": len(set(row_shas)),
        "candidate_duplicate_groups": groups,
        "compound_gate_triggered": any(conditions.values()),
        "resolved_subconditions": [
            name for name in SUBCONDITIONS if conditions[name]
        ],
        "model_call_count": 8,
        "selector_call_count": 0,
        "tensor_bytes_independently_rebuilt": True,
        "producer_or_model_imported": False,
    }
