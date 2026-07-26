"""Independent literal/byte reviewer for the V25 batch8 first-state diagnostic.

This module does not import the producer diagnostic, model, selector, fairness,
or threshold implementation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import numpy as np


AUTHORITY_SHA = (
    "8b63c3564fa3f0ae1f87c5a97794eb01cc172fc6567814411d739aa0a6e7ed14"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
STATE = "development_calibration:000"
MODE = "single_invocation_batch8"
LATENT_SHAPE = (8, 321, 81, 4)
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
DTYPE = "<f4"
TAXONOMY = (
    "batch8_pool_valid_diverse",
    "latent_precondition_invalid",
    "input_batch_not_same_ego",
    "candidate_or_neighbor_nonfinite",
    "candidate_rows_not_unique",
    "output_batch_or_binding_invalid",
    "runtime_or_authority_failure",
)
BASE_KEYS = (
    "input_manifest_sha256",
    "actual_input_tensor_bundle_sha256",
    "actual_state_sha256",
    "latent_manifest_sha256",
    "latent_tensor_sha256",
    "model_source_sha256",
    "checkpoint_sha256",
    "fixed_dp_head",
    "runtime_fingerprint_sha256",
)


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


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _summary(value: np.ndarray) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value))
    rows = [
        _sha_bytes(np.ascontiguousarray(row).tobytes(order="C")) for row in array
    ]
    grouped: dict[str, list[int]] = {}
    for index, digest in enumerate(rows):
        grouped.setdefault(digest, []).append(index)
    missing = np.argwhere(~np.isfinite(array)).astype(int).tolist()
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "byte_count": int(array.nbytes),
        "tensor_sha256": _sha_bytes(array.tobytes(order="C")),
        "nonfinite_indices": missing,
        "nonfinite_count": len(missing),
        "row_sha256": rows,
        "unique_row_sha256_count": len(set(rows)),
        "duplicate_groups": sorted(
            (indices for indices in grouped.values() if len(indices) > 1),
            key=lambda row: row[0],
        ),
    }


def _input_summary(
    arrays: Mapping[str, np.ndarray], latent: np.ndarray
) -> dict[str, Any]:
    rows = []
    same = True
    if type(arrays) is not dict or "sampled_trajectories" not in arrays:
        raise ValueError("review input bundle missing")
    for name in sorted(arrays):
        array = np.ascontiguousarray(np.asarray(arrays[name]))
        if array.shape[0] != 8:
            raise ValueError("review input batch drifted")
        if name == "sampled_trajectories":
            if not np.array_equal(array, latent):
                raise ValueError("review latent/input binding drifted")
        else:
            same = same and all(
                np.array_equal(array[0], array[index]) for index in range(1, 8)
            )
        rows.append(
            {
                "name": name,
                "shape": list(array.shape),
                "dtype": array.dtype.str,
                "tensor_sha256": _sha_bytes(array.tobytes(order="C")),
                "row_sha256": [
                    _sha_bytes(np.ascontiguousarray(row).tobytes(order="C"))
                    for row in array
                ],
            }
        )
    result = {
        "tensor_order": [row["name"] for row in rows],
        "tensors": rows,
        "batch_size": 8,
        "source_ego_state_count": 1,
        "agent_as_ego_batch": False,
        "all_nonlatent_input_rows_exact_equal": same,
    }
    result["bundle_sha256"] = _sha_bytes(_canonical(result))
    return result


def independent_receipt_review(
    *,
    receipt: Mapping[str, Any],
    latent: np.ndarray,
    expanded_inputs: Mapping[str, np.ndarray],
    candidate: np.ndarray,
    neighbor: np.ndarray,
) -> dict[str, Any]:
    if type(receipt) is not dict:
        raise TypeError("receipt must be plain object")
    supplied = dict(receipt)
    supplied_hash = supplied.pop("receipt_sha256", None)
    if supplied_hash != _sha_bytes(_canonical(supplied)):
        raise ValueError("receipt canonical hash drifted")
    latent_summary = _summary(latent)
    input_summary = _input_summary(expanded_inputs, latent)
    candidate_summary = _summary(candidate)
    neighbor_summary = _summary(neighbor)
    if supplied.get("latent_summary") != latent_summary:
        raise ValueError("latent summary does not match raw bytes")
    if supplied.get("expanded_input_summary") != input_summary:
        raise ValueError("input summary does not match raw bytes")
    if supplied.get("candidate_summary") != candidate_summary:
        raise ValueError("candidate summary does not match raw bytes")
    if supplied.get("neighbor_summary") != neighbor_summary:
        raise ValueError("neighbor summary does not match raw bytes")
    base = supplied.get("base_bindings")
    if type(base) is not dict or tuple(base) != BASE_KEYS:
        raise ValueError("base binding order/keyset drifted")
    for key, value in base.items():
        length = 40 if key == "fixed_dp_head" else 64
        if type(value) is not str or len(value) != length:
            raise ValueError("base binding digest drifted")
        int(value, 16)
    if base["fixed_dp_head"] != FIXED_DP_HEAD:
        raise ValueError("fixed DP binding drifted")
    forward = _sha_bytes(
        _canonical(
            {
                **base,
                "state_spec_id": STATE,
                "mode": MODE,
                "repeat_index": 0,
                "source_ego_state_count": 1,
                "expanded_model_batch_size": 8,
                "formal_model_invocation_count": supplied["model_call_count"],
                "expanded_input_bundle_sha256": input_summary["bundle_sha256"],
                "candidate_tensor_sha256": candidate_summary["tensor_sha256"],
                "neighbor_tensor_sha256": neighbor_summary["tensor_sha256"],
            }
        )
    )
    pool = _sha_bytes(
        _canonical(
            {
                "formal_forward_id": forward,
                "candidate_tensor_sha256": candidate_summary["tensor_sha256"],
                "neighbor_tensor_sha256": neighbor_summary["tensor_sha256"],
                "candidate_count": 8,
            }
        )
    )
    if supplied.get("formal_forward_id") != forward:
        raise ValueError("formal forward ID drifted")
    if supplied.get("pool_id") != pool:
        raise ValueError("pool ID drifted")
    if (
        supplied.get("candidate0_rule") != "candidate_tensor_row0"
        or supplied.get("candidate0_row_sha256")
        != candidate_summary["row_sha256"][0]
        or supplied.get("row0_candidate0_binding") is not True
    ):
        raise ValueError("row0 candidate0 binding drifted")
    latent_valid = (
        tuple(latent.shape) == LATENT_SHAPE
        and latent.dtype.str == DTYPE
        and latent_summary["nonfinite_count"] == 0
        and latent_summary["unique_row_sha256_count"] == 8
        and np.count_nonzero(latent[0]) == 0
    )
    same = input_summary["all_nonlatent_input_rows_exact_equal"]
    finite = (
        candidate_summary["nonfinite_count"] == 0
        and neighbor_summary["nonfinite_count"] == 0
    )
    shape = (
        tuple(candidate.shape) == CANDIDATE_SHAPE
        and candidate.dtype.str == DTYPE
        and tuple(neighbor.shape) == NEIGHBOR_SHAPE
        and neighbor.dtype.str == DTYPE
    )
    topology = (
        supplied.get("model_call_count") == 1
        and supplied.get("sequential_model_call_count") == 0
        and supplied.get("selector_call_count") == 0
        and input_summary["agent_as_ego_batch"] is False
        and input_summary["source_ego_state_count"] == 1
    )
    if not latent_valid:
        taxonomy = TAXONOMY[1]
    elif not same:
        taxonomy = TAXONOMY[2]
    elif not finite:
        taxonomy = TAXONOMY[3]
    elif not shape or not topology:
        taxonomy = TAXONOMY[5]
    elif candidate_summary["unique_row_sha256_count"] != 8:
        taxonomy = TAXONOMY[4]
    else:
        taxonomy = TAXONOMY[0]
    if supplied.get("taxonomy") != taxonomy:
        raise ValueError("taxonomy drifted")
    if (
        supplied.get("schema_version")
        != "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_receipt_v1"
        or supplied.get("high_authority_sha256") != AUTHORITY_SHA
        or supplied.get("state_spec_id") != STATE
        or supplied.get("mode") != MODE
        or supplied.get("repeat_index") != 0
        or supplied.get("stop_before_selector") is not True
        or supplied.get("pool_generation_latency_ns", 0) <= 0
        or supplied.get("raw_outcome_read") is not False
        or supplied.get("remaining_calibration_run_count") != 0
        or supplied.get(
            "threshold_validation_closed_loop_fresh_holdout_training_count"
        )
        != 0
        or supplied.get("old_artifact_cas_write_count") != 0
    ):
        raise ValueError("receipt boundary drifted")
    return {
        "status": "passed_independent_raw_byte_review",
        "taxonomy": taxonomy,
        "formal_forward_id": forward,
        "pool_id": pool,
        "latent_unique_row_count": latent_summary["unique_row_sha256_count"],
        "candidate_unique_row_count": candidate_summary[
            "unique_row_sha256_count"
        ],
        "model_call_count": 1,
        "sequential_model_call_count": 0,
        "selector_call_count": 0,
        "producer_model_oracle_imported": False,
    }


def independent_contract_review(
    contract: Mapping[str, Any],
    *,
    implementation_head: str,
    exact_dirs: Mapping[str, str],
    source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    if type(contract) is not dict:
        raise TypeError("contract must be object")
    unhashed = dict(contract)
    supplied_contract_sha = unhashed.pop("contract_sha256", None)
    if supplied_contract_sha != _sha_bytes(_canonical(unhashed)):
        raise ValueError("contract canonical hash drifted")
    if (
        contract.get("schema_version")
        != "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_contract_v1"
        or contract.get("status")
        != "outcome_independent_batch8_first_state_contract_frozen"
        or contract.get("high_authority_sha256") != AUTHORITY_SHA
        or hashlib.sha256(
            contract.get("high_authority_json", "").encode("ascii")
        ).hexdigest()
        != AUTHORITY_SHA
        or contract.get("implementation_head") != implementation_head
        or contract.get("exact_dirs") != dict(exact_dirs)
        or contract.get("source_sha256") != dict(source_sha256)
        or contract.get("fixed_dp_head") != FIXED_DP_HEAD
    ):
        raise ValueError("contract authority binding drifted")
    identity = contract.get("authorized_identity")
    if identity != {
        "state_spec_id": STATE,
        "mode": MODE,
        "repeat_index": 0,
        "source_ego_state_count": 1,
        "expanded_model_batch_size": 8,
        "agent_as_ego_batch": False,
        "formal_model_invocation_count": 1,
        "sequential_model_call_count": 0,
        "selector_call_count": 0,
        "stop_before_selector": True,
    }:
        raise ValueError("single invocation identity drifted")
    latent = contract.get("latent_contract")
    if (
        latent.get("seed") != 61000
        or latent.get("shape") != [8, 321, 81, 4]
        or latent.get("dtype") != "<f4"
        or latent.get("rows1_7_draw_shape") != [7, 321, 81, 4]
        or latent.get("unique_row_sha256_count_required") != 8
    ):
        raise ValueError("latent contract drifted")
    output = contract.get("output_contract")
    if (
        output.get("candidate_shape") != [8, 80, 4]
        or output.get("neighbor_shape") != [8, 32, 80, 4]
        or output.get("candidate0_rule") != "candidate_tensor_row0"
    ):
        raise ValueError("output contract drifted")
    if contract.get("taxonomy") != list(TAXONOMY):
        raise ValueError("taxonomy drifted")
    if set(contract.get("scientific_boundary", {}).values()) != {False, True}:
        raise ValueError("scientific boundary malformed")
    boundary = contract["scientific_boundary"]
    if any(
        boundary[key] is not False
        for key in (
            "full_calibration_authorized",
            "threshold_validation_closed_loop_fresh_holdout_training_authorized",
            "fixed_dp_model_weights_atoms_change_authorized",
            "old_artifact_cas_write_authorized",
            "outcome_read_authorized",
            "claim_authorized",
        )
    ) or boundary.get("return_to_high_after_diagnostic") is not True:
        raise ValueError("scientific boundary drifted")
    return {
        "status": "passed_independent_literal_contract_review",
        "single_invocation_same_ego_topology_rebuilt": True,
        "latent_policy_rebuilt": True,
        "raw_byte_review_required": True,
        "producer_oracle_imported": False,
    }


def independent_preflight_review(
    receipt: Mapping[str, Any],
    *,
    old_receipt: Mapping[str, Any],
    contract_root: str,
    contract_review_root: str,
) -> dict[str, Any]:
    """Rebuild the one-state input-only preflight without producer imports."""
    if type(receipt) is not dict or type(old_receipt) is not dict:
        raise TypeError("preflight receipts must be objects")
    supplied = dict(receipt)
    receipt_sha = supplied.pop("receipt_sha256", None)
    if receipt_sha != _sha_bytes(_canonical(supplied)):
        raise ValueError("preflight receipt hash drifted")
    for value in (contract_root, contract_review_root):
        if type(value) is not str or len(value) != 64:
            raise ValueError("contract root drifted")
        int(value, 16)
    if (
        receipt.get("schema_version")
        != "camp_dp_v25_single_invocation_batch8_first_state_input_preflight_v1"
        or receipt.get("status") != "passed_before_first_batch8_model_call"
        or receipt.get("high_authority_sha256") != AUTHORITY_SHA
        or receipt.get("contract_root_sha256") != contract_root
        or receipt.get("contract_review_root_sha256") != contract_review_root
        or receipt.get("old_preflight_root_sha256")
        != "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
        or receipt.get("old_preflight_review_root_sha256")
        != "ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3"
        or receipt.get("state_spec_id") != STATE
        or receipt.get("mode") != MODE
        or receipt.get("repeat_index") != 0
        or receipt.get("seed_state_route_geometry_unchanged") is not True
        or receipt.get("no_drop_no_replacement") is not True
        or receipt.get("model_pool_selector_call_count_before_receipt") != 0
    ):
        raise ValueError("preflight authority boundary drifted")
    old_calibration = old_receipt.get("calibration_manifests")
    old_validation = old_receipt.get("validation_manifests")
    if (
        old_receipt.get("status") != "passed_before_first_model_pool_selector_call"
        or type(old_calibration) is not list
        or len(old_calibration) != 64
        or type(old_validation) is not list
        or len(old_validation) != 64
        or any(
            old_receipt.get(key) != 0
            for key in (
                "within_calibration_overlap_count",
                "within_validation_overlap_count",
                "cross_split_overlap_count",
                "b4_overlap_count",
                "model_pool_selector_call_count_before_receipt",
            )
        )
        or old_receipt.get("no_drop_no_replacement") is not True
    ):
        raise ValueError("old input-only preflight drifted")
    matches = [row for row in old_calibration if row.get("state_spec_id") == STATE]
    if len(matches) != 1:
        raise ValueError("first-state source manifest cardinality drifted")
    source = matches[0]
    if source.get("latent_seed") != 61000:
        raise ValueError("first-state source manifest drifted")
    latent = np.zeros(LATENT_SHAPE, dtype=np.float32)
    rng = np.random.Generator(np.random.PCG64(61000))
    latent[1:] = rng.standard_normal(latent[1:].shape).astype(np.float32)
    latent_summary = _summary(latent)
    if (
        latent_summary["nonfinite_count"] != 0
        or latent_summary["unique_row_sha256_count"] != 8
        or np.count_nonzero(latent[0]) != 0
    ):
        raise ValueError("literal latent policy failed")
    manifest = receipt.get("new_manifest")
    if type(manifest) is not dict:
        raise ValueError("new manifest missing")
    unhashed_manifest = dict(manifest)
    manifest_sha = unhashed_manifest.pop("manifest_sha256", None)
    if manifest_sha != _sha_bytes(_canonical(unhashed_manifest)):
        raise ValueError("new manifest hash drifted")
    expected_latent = {
        "schema_version": "camp_dp_v25_unique_batch8_latent_manifest_v1",
        "policy": "row0_zero_rows1_7_independent_pcg64_standard_normal_float32",
        "bit_generator": "PCG64",
        "seed": 61000,
        "shape": list(LATENT_SHAPE),
        "dtype": DTYPE,
        "row0_all_zero": True,
        "rows1_7_draw_shape": [7, 321, 81, 4],
        "finite": True,
        "row_sha256": latent_summary["row_sha256"],
        "unique_row_sha256_count": 8,
        "duplicate_groups": [],
        "tensor_sha256": latent_summary["tensor_sha256"],
    }
    expected_latent["manifest_sha256"] = _sha_bytes(_canonical(expected_latent))
    expected_manifest = json.loads(json.dumps(source))
    expected_manifest["schema_version"] = (
        "camp_dp_v25_batch8_first_state_input_only_manifest_v1"
    )
    expected_manifest["actual_latent_tensor_manifest"] = expected_latent
    expected_manifest.pop("manifest_sha256", None)
    expected_manifest["manifest_sha256"] = _sha_bytes(_canonical(expected_manifest))
    if manifest != expected_manifest:
        raise ValueError("new input-only manifest drifted")

    def instance_key(row: Mapping[str, Any]) -> str:
        return _sha_bytes(
            _canonical(
                {
                    "state_spec_id": row["state_spec_id"],
                    "clone_key_sha256": row["clone_key_sha256"],
                    "actual_state_sha256": row["actual_state_sha256"],
                    "actual_input_tensor_bundle_sha256": row[
                        "actual_input_tensor_manifest"
                    ]["bundle_sha256"],
                    "latent_tensor_sha256": row[
                        "actual_latent_tensor_manifest"
                    ]["tensor_sha256"],
                }
            )
        )

    old_instances = {instance_key(row) for row in old_calibration + old_validation}
    new_instance = instance_key(manifest)
    b4 = old_receipt.get("b4_forbidden_manifest_authority")
    if (
        new_instance in old_instances
        or receipt.get("new_instance_key_sha256") != new_instance
        or receipt.get("old_nonholdout_instance_count") != len(old_instances)
        or receipt.get("old_manifest_sha256") != source.get("manifest_sha256")
        or receipt.get("fresh_b2_b3_b4_forbidden_inventory") != b4
        or type(b4) is not dict
        or b4.get("derived_inside_validator_from_exact_bytes") is not True
        or b4.get("derived_forbidden_clone_key_count") != 100
        or any(
            receipt.get(key) != 0
            for key in (
                "old_nonholdout_instance_overlap_count",
                "future_validation_instance_overlap_count",
                "training_instance_overlap_count",
                "fresh_b2_b3_b4_clone_overlap_count",
            )
        )
    ):
        raise ValueError("zero-overlap preflight drifted")
    return {
        "status": "passed_independent_input_only_preflight_review",
        "new_instance_key_sha256": new_instance,
        "latent_tensor_sha256": latent_summary["tensor_sha256"],
        "latent_unique_row_count": 8,
        "old_nonholdout_instance_count": len(old_instances),
        "fresh_b2_b3_b4_forbidden_clone_count": 100,
        "model_pool_selector_call_count": 0,
        "producer_preflight_oracle_imported": False,
    }
