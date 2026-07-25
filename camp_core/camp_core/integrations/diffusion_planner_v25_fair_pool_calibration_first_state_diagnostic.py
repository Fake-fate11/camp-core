from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

import numpy as np


SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_calibration_first_state_diagnostic_receipt_v1"
)
CONTRACT_SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_calibration_first_state_diagnostic_contract_v1"
)
AUTHORITY_SCHEMA_VERSION = (
    "camp_dp_v25_fair_pool_calibration_first_state_diagnostic_high_authority_v1"
)
HIGH_AUTHORITY_SHA256 = (
    "3a72e639152b3416f7ef769f20dee05a2334d160b866ada4bd609c0c801277c8"
)
HIGH_AUTHORITY_JSON = (
    '{"authorized_mode":"sequential_batch1_x8","authorized_repeat_index":0,'
    '"authorized_state_spec_id":"development_calibration:000",'
    '"closed_loop_authorized":false,'
    '"control_source_thread_id":"019f6eee-8fc2-75f3-843c-75562f610b13",'
    '"decision":"authorized_after_failed_attempt_closeout",'
    '"executor_thread_id":"019f92f5-eb4e-78d1-88ea-8ee1f4335eb3",'
    '"fixed_dp_weights_atoms_contract_change_authorized":false,'
    '"fresh_holdout_authorized":false,'
    '"full_calibration_restart_requires_new_high_authority":true,'
    '"independent_validation_authorized":false,"model_call_count":8,'
    '"prior_attempt_closeout_required_before_diagnostic":true,'
    '"prior_attempt_status":"failed_pre_selector_pre_outcome_zero_of_640",'
    '"prior_calibration_authority_sha256":'
    '"ed0d298cbde0e66d7ed2b0bdd90e6be5f2ebbc49f4d818a6c97ff47440f88f59",'
    '"producer_and_reviewer_recompute_from_tensor_bytes":true,'
    '"provider_task_id":"019f92d8-c971-7b13-924e-873ae9f24c14",'
    '"receipt_must_precede_raise":true,"remaining_639_runs_authorized":false,'
    '"required_precondition_receipt_fields":["candidate_shape_dtype",'
    '"candidate_nonfinite_indices_count","neighbor_shape_dtype",'
    '"neighbor_nonfinite_indices_count",'
    '"candidate_row_sha256_cardinality_duplicate_groups",'
    '"input_state_latent_model_checkpoint_forward_ids","model_call_count",'
    '"selector_call_count"],'
    '"schema_version":'
    '"camp_dp_v25_fair_pool_calibration_first_state_diagnostic_high_authority_v1",'
    '"selector_call_count":0,"stop_before_selector":true,'
    '"threshold_materialization_authorized":false,'
    '"training_retraining_authorized":false}'
)

AUTHORIZED_STATE_SPEC_ID = "development_calibration:000"
AUTHORIZED_MODE = "sequential_batch1_x8"
AUTHORIZED_REPEAT_INDEX = 0
MODEL_CALL_COUNT = 8
SELECTOR_CALL_COUNT = 0
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
TENSOR_DTYPE = "<f4"
POSSIBLE_SUBCONDITIONS = (
    "candidate_tensor_contains_nonfinite_value",
    "neighbor_tensor_contains_nonfinite_value",
    "candidate_row_sha256_not_unique_across_k8",
)
REQUIRED_BINDINGS = (
    "input_manifest_sha256",
    "actual_input_tensor_bundle_sha256",
    "actual_state_sha256",
    "latent_tensor_sha256",
    "model_source_sha256",
    "checkpoint_sha256",
    "fixed_dp_head",
    "forward_ids",
)
SHA256_RE = set("0123456789abcdef")


def canonical_json_bytes(value: Any) -> bytes:
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


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value) <= SHA256_RE
    )


def is_git_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and set(value) <= SHA256_RE
    )


def canonical_tensor_bytes(value: np.ndarray, *, shape: tuple[int, ...]) -> bytes:
    array = np.asarray(value)
    if tuple(array.shape) != shape or array.dtype.str != TENSOR_DTYPE:
        raise ValueError(
            f"tensor shape/dtype drifted: {array.shape}/{array.dtype.str}"
        )
    return np.ascontiguousarray(array).tobytes(order="C")


def decode_tensor_bytes(value: bytes, *, shape: tuple[int, ...]) -> np.ndarray:
    expected = int(np.prod(shape)) * np.dtype(TENSOR_DTYPE).itemsize
    if len(value) != expected:
        raise ValueError("tensor byte count drifted")
    return np.frombuffer(value, dtype=TENSOR_DTYPE).reshape(shape).copy()


def _nonfinite_indices(value: np.ndarray) -> list[list[int]]:
    return np.argwhere(~np.isfinite(value)).astype(int).tolist()


def _row_sha256(candidate: np.ndarray) -> list[str]:
    return [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in candidate
    ]


def _duplicate_groups(row_sha256: list[str]) -> list[list[int]]:
    grouped: dict[str, list[int]] = {}
    for index, digest in enumerate(row_sha256):
        grouped.setdefault(digest, []).append(index)
    return sorted(
        (indices for indices in grouped.values() if len(indices) > 1),
        key=lambda indices: indices[0],
    )


def _validate_bindings(bindings: Mapping[str, Any]) -> dict[str, Any]:
    if set(bindings) != set(REQUIRED_BINDINGS):
        raise ValueError("diagnostic binding field set drifted")
    result = dict(bindings)
    for field in REQUIRED_BINDINGS[:-1]:
        if not is_sha256(result[field]):
            raise ValueError(f"invalid binding SHA256: {field}")
    forward_ids = result["forward_ids"]
    if (
        not isinstance(forward_ids, list)
        or len(forward_ids) != MODEL_CALL_COUNT
        or any(not is_sha256(value) for value in forward_ids)
        or len(set(forward_ids)) != MODEL_CALL_COUNT
    ):
        raise ValueError("forward ID binding drifted")
    return result


def build_precondition_receipt(
    *,
    candidate: np.ndarray,
    neighbor: np.ndarray,
    bindings: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_bytes = canonical_tensor_bytes(candidate, shape=CANDIDATE_SHAPE)
    neighbor_bytes = canonical_tensor_bytes(neighbor, shape=NEIGHBOR_SHAPE)
    candidate_array = decode_tensor_bytes(candidate_bytes, shape=CANDIDATE_SHAPE)
    neighbor_array = decode_tensor_bytes(neighbor_bytes, shape=NEIGHBOR_SHAPE)
    candidate_nonfinite = _nonfinite_indices(candidate_array)
    neighbor_nonfinite = _nonfinite_indices(neighbor_array)
    row_sha256 = _row_sha256(candidate_array)
    duplicate_groups = _duplicate_groups(row_sha256)
    subconditions = {
        POSSIBLE_SUBCONDITIONS[0]: bool(candidate_nonfinite),
        POSSIBLE_SUBCONDITIONS[1]: bool(neighbor_nonfinite),
        POSSIBLE_SUBCONDITIONS[2]: bool(duplicate_groups),
    }
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "authority_sha256": HIGH_AUTHORITY_SHA256,
        "state_spec_id": AUTHORIZED_STATE_SPEC_ID,
        "mode": AUTHORIZED_MODE,
        "repeat_index": AUTHORIZED_REPEAT_INDEX,
        "candidate_shape": list(CANDIDATE_SHAPE),
        "candidate_dtype": TENSOR_DTYPE,
        "candidate_byte_count": len(candidate_bytes),
        "candidate_tensor_sha256": sha256_bytes(candidate_bytes),
        "candidate_nonfinite_indices": candidate_nonfinite,
        "candidate_nonfinite_count": len(candidate_nonfinite),
        "candidate_row_sha256": row_sha256,
        "candidate_row_sha256_unique_cardinality": len(set(row_sha256)),
        "candidate_duplicate_groups": duplicate_groups,
        "neighbor_shape": list(NEIGHBOR_SHAPE),
        "neighbor_dtype": TENSOR_DTYPE,
        "neighbor_byte_count": len(neighbor_bytes),
        "neighbor_tensor_sha256": sha256_bytes(neighbor_bytes),
        "neighbor_nonfinite_indices": neighbor_nonfinite,
        "neighbor_nonfinite_count": len(neighbor_nonfinite),
        "bindings": _validate_bindings(bindings),
        "model_call_count": MODEL_CALL_COUNT,
        "selector_call_count": SELECTOR_CALL_COUNT,
        "subconditions": subconditions,
        "compound_gate_triggered": any(subconditions.values()),
        "resolved_subconditions": [
            name for name in POSSIBLE_SUBCONDITIONS if subconditions[name]
        ],
        "receipt_formed_before_any_raise": True,
        "stop_before_selector": True,
        "remaining_calibration_run_count_authorized": 0,
        "threshold_materialization_authorized": False,
        "validation_authorized": False,
        "fresh_or_holdout_authorized": False,
        "training_or_retraining_authorized": False,
        "raw_outcome_read": False,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json_bytes(receipt))
    return receipt


def validate_precondition_receipt(
    receipt: Mapping[str, Any],
    *,
    candidate_bytes: bytes,
    neighbor_bytes: bytes,
    expected_bindings: Mapping[str, Any],
) -> None:
    candidate = decode_tensor_bytes(candidate_bytes, shape=CANDIDATE_SHAPE)
    neighbor = decode_tensor_bytes(neighbor_bytes, shape=NEIGHBOR_SHAPE)
    expected = build_precondition_receipt(
        candidate=candidate,
        neighbor=neighbor,
        bindings=expected_bindings,
    )
    if dict(receipt) != expected:
        raise ValueError("diagnostic receipt does not match tensor-byte preimage")


def write_precondition_receipt_atomic(
    path: Path, receipt: Mapping[str, Any]
) -> str:
    if path.exists():
        raise FileExistsError(path)
    payload = canonical_json_bytes(dict(receipt))
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return sha256_bytes(payload)


def enforce_compound_gate_after_receipt(
    receipt_path: Path, receipt: Mapping[str, Any]
) -> None:
    if (
        not receipt_path.is_file()
        or sha256_bytes(receipt_path.read_bytes())
        != sha256_bytes(canonical_json_bytes(dict(receipt)))
    ):
        raise RuntimeError("precondition receipt was not durably formed before gate")
    if receipt["compound_gate_triggered"]:
        raise RuntimeError("calibration K8 invalid")


def diagnostic_contract(
    *,
    implementation_head: str,
    exact_dirs: Mapping[str, str],
    producer_source_sha256: str,
    reviewer_source_sha256: str,
) -> dict[str, Any]:
    if not is_git_sha(implementation_head):
        raise ValueError("implementation HEAD must be a 40-hex git object ID")
    if set(exact_dirs) != {
        "contract",
        "contract_review",
        "focused",
        "diagnostic",
        "diagnostic_review",
    }:
        raise ValueError("diagnostic exact-dir set drifted")
    if any(not isinstance(value, str) or not value for value in exact_dirs.values()):
        raise ValueError("diagnostic exact dir invalid")
    if not is_sha256(producer_source_sha256) or not is_sha256(
        reviewer_source_sha256
    ):
        raise ValueError("diagnostic source SHA invalid")
    authority = json.loads(HIGH_AUTHORITY_JSON)
    if (
        list(authority) != sorted(authority)
        or authority["schema_version"] != AUTHORITY_SCHEMA_VERSION
        or sha256_bytes(HIGH_AUTHORITY_JSON.encode("ascii"))
        != HIGH_AUTHORITY_SHA256
    ):
        raise ValueError("canonical diagnostic High authority drifted")
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "status": "outcome_independent_first_state_diagnostic_contract_frozen",
        "high_authority_json": HIGH_AUTHORITY_JSON,
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "exact_dirs": dict(exact_dirs),
        "authorized_run_identity": {
            "state_spec_id": AUTHORIZED_STATE_SPEC_ID,
            "mode": AUTHORIZED_MODE,
            "repeat_index": AUTHORIZED_REPEAT_INDEX,
            "model_call_count": MODEL_CALL_COUNT,
            "selector_call_count": SELECTOR_CALL_COUNT,
        },
        "tensor_contract": {
            "candidate_shape": list(CANDIDATE_SHAPE),
            "candidate_dtype": TENSOR_DTYPE,
            "neighbor_shape": list(NEIGHBOR_SHAPE),
            "neighbor_dtype": TENSOR_DTYPE,
            "candidate_row_count": 8,
            "nonfinite_index_enumeration": "numpy_argwhere_c_order",
            "candidate_row_sha256": "sha256_exact_little_endian_float32_row_bytes",
            "duplicate_groups": "equal_row_sha256_grouped_by_ascending_row_index",
        },
        "required_bindings": list(REQUIRED_BINDINGS),
        "forward_id_contract": {
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
        },
        "possible_subconditions": list(POSSIBLE_SUBCONDITIONS),
        "receipt_must_precede_raise": True,
        "producer_and_reviewer_recompute_from_tensor_bytes": True,
        "stop_before_selector": True,
        "remaining_639_runs_authorized": False,
        "threshold_materialization_authorized": False,
        "validation_authorized": False,
        "closed_loop_authorized": False,
        "fresh_or_holdout_authorized": False,
        "training_or_retraining_authorized": False,
        "fixed_dp_weights_atoms_contract_change_authorized": False,
        "prior_attempt_closeout_immutable": True,
        "prior_attempt_status": "failed_pre_selector_pre_outcome_zero_of_640",
        "producer_source_sha256": producer_source_sha256,
        "reviewer_source_sha256": reviewer_source_sha256,
    }


def validate_diagnostic_contract(contract: Mapping[str, Any]) -> None:
    expected = diagnostic_contract(
        implementation_head=contract["implementation_head"],
        exact_dirs=contract["exact_dirs"],
        producer_source_sha256=contract["producer_source_sha256"],
        reviewer_source_sha256=contract["reviewer_source_sha256"],
    )
    if dict(contract) != expected:
        raise ValueError("diagnostic contract drifted")
