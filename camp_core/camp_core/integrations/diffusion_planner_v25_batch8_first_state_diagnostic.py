"""Versioned contract and byte-level receipt for one V25 batch8 diagnostic."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import numpy as np


CONTRACT_SCHEMA = (
    "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_contract_v1"
)
PREFLIGHT_SCHEMA = (
    "camp_dp_v25_single_invocation_batch8_first_state_input_preflight_v1"
)
RECEIPT_SCHEMA = (
    "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_receipt_v1"
)
AUTHORITY_SCHEMA = (
    "camp_dp_v25_single_invocation_batch8_first_state_diagnostic_high_authority_v1"
)
HIGH_AUTHORITY_JSON = (
    '{"agent_as_ego_batch":false,'
    '"contract_final_docs_root_sha256":"6cce170feedbbdaa463e6314cac82486a0ba163d088264660abd787fda2c54ae",'
    '"contract_focused_root_sha256":"bb012e5800fbc37e4106a11032f03c166fb793f34366fe5165068f5daa00ba20",'
    '"contract_review_root_sha256":"a0cd179311b5ce1fd18b7e764154d92041bfda57216c0be2365aa20100133978",'
    '"contract_root_sha256":"15cf642f5abcb1cd44687e8f4298517f47e8c878633602e9b42fcffe7c30e5d7",'
    '"control_source_thread_id":"019f6eee-8fc2-75f3-843c-75562f610b13",'
    '"decision":"authorized_one_development_batch8_preselector_diagnostic",'
    '"executor_thread_id":"019f92f5-eb4e-78d1-88ea-8ee1f4335eb3",'
    '"expanded_model_batch_size":8,'
    '"fixed_dp_head":"7a1d33da277a1992ec474b5383a0c963c72e04e4",'
    '"fixed_dp_model_weights_atoms_change_authorized":false,'
    '"formal_model_invocation_count":1,'
    '"full_calibration_threshold_validation_closed_loop_fresh_holdout_training_authorized":false,'
    '"implementation_head":"bcc847870dacbf986ad5aac66b052660b7197696",'
    '"independent_reviewer_rebuilds_from_raw_bytes_and_source":true,'
    '"latent_policy":"row0_zero_rows1_7_independent_pcg64_standard_normal_float32",'
    '"mode":"single_invocation_batch8",'
    '"old_artifact_cas_write_authorized":false,'
    '"outcome_read_authorized":false,'
    '"pointer_head":"b2300991949c26b212891f9e838e064bd36bc76d",'
    '"provider_task_id":"019f92d8-c971-7b13-924e-873ae9f24c14",'
    '"repeat_index":0,'
    '"required_outputs":["candidate_shape_8x80x4_dtype_finite_row_sha_cardinality",'
    '"neighbor_shape_8xAx80x4_dtype_finite","single_forward_id","pool_id",'
    '"candidate_tensor_sha256","row0_candidate0_binding","pool_generation_latency"],'
    '"required_preconditions":["latent_shape_dtype_finite_unique8",'
    '"all_nonlatent_input_rows_exact_equal",'
    '"input_state_model_checkpoint_source_runtime_bindings"],'
    '"return_to_high_after_diagnostic":true,'
    '"schema_version":"camp_dp_v25_single_invocation_batch8_first_state_diagnostic_high_authority_v1",'
    '"selector_call_count":0,'
    '"sequential_model_calls_authorized":false,'
    '"source_ego_state_count":1,'
    '"state_spec_id":"development_calibration:000",'
    '"stop_before_selector":true,'
    '"taxonomy":["batch8_pool_valid_diverse","latent_precondition_invalid",'
    '"input_batch_not_same_ego","candidate_or_neighbor_nonfinite",'
    '"candidate_rows_not_unique","output_batch_or_binding_invalid",'
    '"runtime_or_authority_failure"]}'
)
HIGH_AUTHORITY_SHA256 = (
    "8b63c3564fa3f0ae1f87c5a97794eb01cc172fc6567814411d739aa0a6e7ed14"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
CHECKPOINT_SHA256 = (
    "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75"
)
MODEL_SOURCE_SHA256 = (
    "341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d"
)
STATE_SPEC_ID = "development_calibration:000"
MODE = "single_invocation_batch8"
REPEAT_INDEX = 0
LATENT_SEED = 61000
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
EXACT_DIR_KEYS = (
    "contract",
    "contract_review",
    "focused",
    "preflight",
    "preflight_review",
    "diagnostic",
    "diagnostic_review",
)
SOURCE_KEYS = (
    "producer",
    "reviewer",
    "freeze_script",
    "contract_review_script",
    "preflight_script",
    "preflight_review_script",
    "diagnostic_script",
    "diagnostic_review_script",
    "tests",
)
BASE_BINDING_KEYS = (
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
OLD_PREFLIGHT_ROOT = (
    "5156f98f0172fbd22ed2c21dfd79d236ce53544bf796006e41e29918ec667a22"
)
OLD_PREFLIGHT_REVIEW_ROOT = (
    "ece7c80b6e764598ff867606f225a29a40f8ddededc641e7f22032b4b5d49ef3"
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


def unique_latent(seed: int = LATENT_SEED) -> np.ndarray:
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("latent seed must be integer")
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    latent = np.zeros(LATENT_SHAPE, dtype=np.float32)
    latent[1:] = rng.standard_normal(latent[1:].shape).astype(np.float32)
    return latent


def tensor_summary(value: np.ndarray) -> dict[str, Any]:
    array = np.ascontiguousarray(np.asarray(value))
    rows = [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in array
    ]
    nonfinite = np.argwhere(~np.isfinite(array)).astype(int).tolist()
    groups: dict[str, list[int]] = {}
    for index, digest in enumerate(rows):
        groups.setdefault(digest, []).append(index)
    result = {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "byte_count": int(array.nbytes),
        "tensor_sha256": sha256_bytes(array.tobytes(order="C")),
        "nonfinite_indices": nonfinite,
        "nonfinite_count": len(nonfinite),
        "row_sha256": rows,
        "unique_row_sha256_count": len(set(rows)),
        "duplicate_groups": sorted(
            (indices for indices in groups.values() if len(indices) > 1),
            key=lambda row: row[0],
        ),
    }
    return result


def latent_manifest(seed: int = LATENT_SEED) -> dict[str, Any]:
    latent = unique_latent(seed)
    summary = tensor_summary(latent)
    result = {
        "schema_version": "camp_dp_v25_unique_batch8_latent_manifest_v1",
        "policy": (
            "row0_zero_rows1_7_independent_pcg64_standard_normal_float32"
        ),
        "bit_generator": "PCG64",
        "seed": int(seed),
        "shape": list(LATENT_SHAPE),
        "dtype": DTYPE,
        "row0_all_zero": bool(np.count_nonzero(latent[0]) == 0),
        "rows1_7_draw_shape": [7, 321, 81, 4],
        "finite": summary["nonfinite_count"] == 0,
        "row_sha256": summary["row_sha256"],
        "unique_row_sha256_count": summary["unique_row_sha256_count"],
        "duplicate_groups": summary["duplicate_groups"],
        "tensor_sha256": summary["tensor_sha256"],
    }
    result["manifest_sha256"] = sha256_bytes(canonical_bytes(result))
    return result


def expanded_input_summary(
    arrays: Mapping[str, np.ndarray],
    *,
    latent: np.ndarray,
) -> dict[str, Any]:
    if type(arrays) is not dict or "sampled_trajectories" not in arrays:
        raise ValueError("expanded input tensor dictionary drifted")
    rows = []
    same_ego = True
    for name in sorted(arrays):
        array = np.ascontiguousarray(np.asarray(arrays[name]))
        if array.shape[0] != 8:
            raise ValueError("expanded input batch must be exactly 8")
        if name == "sampled_trajectories":
            if not np.array_equal(array, np.asarray(latent)):
                raise ValueError("expanded latent input bytes drifted")
        else:
            same_ego = same_ego and all(
                np.array_equal(array[0], array[index]) for index in range(1, 8)
            )
        rows.append(
            {
                "name": name,
                "shape": list(array.shape),
                "dtype": array.dtype.str,
                "tensor_sha256": sha256_bytes(array.tobytes(order="C")),
                "row_sha256": [
                    sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
                    for row in array
                ],
            }
        )
    bundle = {
        "tensor_order": [row["name"] for row in rows],
        "tensors": rows,
        "batch_size": 8,
        "source_ego_state_count": 1,
        "agent_as_ego_batch": False,
        "all_nonlatent_input_rows_exact_equal": same_ego,
    }
    bundle["bundle_sha256"] = sha256_bytes(canonical_bytes(bundle))
    return bundle


def _instance_key(manifest: Mapping[str, Any]) -> str:
    return sha256_bytes(
        canonical_bytes(
            {
                "state_spec_id": manifest["state_spec_id"],
                "clone_key_sha256": manifest["clone_key_sha256"],
                "actual_state_sha256": manifest["actual_state_sha256"],
                "actual_input_tensor_bundle_sha256": manifest[
                    "actual_input_tensor_manifest"
                ]["bundle_sha256"],
                "latent_tensor_sha256": manifest["actual_latent_tensor_manifest"][
                    "tensor_sha256"
                ],
            }
        )
    )


def build_preflight_receipt(
    *,
    old_receipt: Mapping[str, Any],
    contract_root: str,
    contract_review_root: str,
) -> dict[str, Any]:
    if (
        old_receipt.get("status") != "passed_before_first_model_pool_selector_call"
        or old_receipt.get("within_calibration_overlap_count") != 0
        or old_receipt.get("within_validation_overlap_count") != 0
        or old_receipt.get("cross_split_overlap_count") != 0
        or old_receipt.get("b4_overlap_count") != 0
        or old_receipt.get("model_pool_selector_call_count_before_receipt") != 0
        or old_receipt.get("no_drop_no_replacement") is not True
        or len(old_receipt.get("calibration_manifests", [])) != 64
        or len(old_receipt.get("validation_manifests", [])) != 64
    ):
        raise ValueError("sealed v5 preflight prerequisite drifted")
    old_manifest = old_receipt["calibration_manifests"][0]
    if (
        old_manifest.get("state_spec_id") != STATE_SPEC_ID
        or old_manifest.get("latent_seed") != LATENT_SEED
    ):
        raise ValueError("first state prerequisite drifted")
    new_manifest = json.loads(json.dumps(old_manifest))
    new_manifest["schema_version"] = (
        "camp_dp_v25_batch8_first_state_input_only_manifest_v1"
    )
    new_manifest["actual_latent_tensor_manifest"] = latent_manifest()
    new_manifest.pop("manifest_sha256", None)
    new_manifest["manifest_sha256"] = sha256_bytes(canonical_bytes(new_manifest))
    old_instances = {
        _instance_key(row)
        for row in (
            list(old_receipt["calibration_manifests"])
            + list(old_receipt["validation_manifests"])
        )
    }
    new_instance = _instance_key(new_manifest)
    if new_instance in old_instances:
        raise ValueError("new batch8 instance overlaps old nonholdout instance")
    b4 = old_receipt.get("b4_forbidden_manifest_authority")
    if (
        type(b4) is not dict
        or b4.get("derived_inside_validator_from_exact_bytes") is not True
        or b4.get("derived_forbidden_clone_key_count") != 100
    ):
        raise ValueError("B2/B3/B4 forbidden inventory authority drifted")
    receipt = {
        "schema_version": PREFLIGHT_SCHEMA,
        "status": "passed_before_first_batch8_model_call",
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "contract_root_sha256": _sha(contract_root),
        "contract_review_root_sha256": _sha(contract_review_root),
        "old_preflight_root_sha256": OLD_PREFLIGHT_ROOT,
        "old_preflight_review_root_sha256": OLD_PREFLIGHT_REVIEW_ROOT,
        "state_spec_id": STATE_SPEC_ID,
        "mode": MODE,
        "repeat_index": REPEAT_INDEX,
        "seed_state_route_geometry_unchanged": True,
        "old_manifest_sha256": old_manifest["manifest_sha256"],
        "new_manifest": new_manifest,
        "new_instance_key_sha256": new_instance,
        "old_nonholdout_instance_count": len(old_instances),
        "old_nonholdout_instance_overlap_count": 0,
        "future_validation_instance_overlap_count": 0,
        "training_instance_overlap_count": 0,
        "fresh_b2_b3_b4_clone_overlap_count": 0,
        "fresh_b2_b3_b4_forbidden_inventory": b4,
        "no_drop_no_replacement": True,
        "model_pool_selector_call_count_before_receipt": 0,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    return receipt


def build_diagnostic_receipt(
    *,
    latent: np.ndarray,
    expanded_inputs: Mapping[str, np.ndarray],
    candidate: np.ndarray,
    neighbor: np.ndarray,
    base_bindings: Mapping[str, Any],
    pool_generation_latency_ns: int,
    model_call_count: int,
    sequential_model_call_count: int,
    selector_call_count: int,
) -> dict[str, Any]:
    if set(base_bindings) != set(BASE_BINDING_KEYS):
        raise ValueError("base binding keyset drifted")
    bindings = dict(base_bindings)
    for key in BASE_BINDING_KEYS:
        if key == "fixed_dp_head":
            _head(bindings[key])
        else:
            _sha(bindings[key])
    latent_summary = tensor_summary(latent)
    input_summary = expanded_input_summary(expanded_inputs, latent=latent)
    candidate_summary = tensor_summary(candidate)
    neighbor_summary = tensor_summary(neighbor)
    if (
        isinstance(pool_generation_latency_ns, bool)
        or not isinstance(pool_generation_latency_ns, (int, np.integer))
        or pool_generation_latency_ns <= 0
    ):
        raise ValueError("pool latency must be a positive integer nanoseconds")
    forward_id = sha256_bytes(
        canonical_bytes(
            {
                **bindings,
                "state_spec_id": STATE_SPEC_ID,
                "mode": MODE,
                "repeat_index": REPEAT_INDEX,
                "source_ego_state_count": 1,
                "expanded_model_batch_size": 8,
                "formal_model_invocation_count": int(model_call_count),
                "expanded_input_bundle_sha256": input_summary["bundle_sha256"],
                "candidate_tensor_sha256": candidate_summary["tensor_sha256"],
                "neighbor_tensor_sha256": neighbor_summary["tensor_sha256"],
            }
        )
    )
    pool_id = sha256_bytes(
        canonical_bytes(
            {
                "formal_forward_id": forward_id,
                "candidate_tensor_sha256": candidate_summary["tensor_sha256"],
                "neighbor_tensor_sha256": neighbor_summary["tensor_sha256"],
                "candidate_count": 8,
            }
        )
    )
    output_shape_valid = (
        tuple(candidate.shape) == CANDIDATE_SHAPE
        and candidate.dtype.str == DTYPE
        and tuple(neighbor.shape) == NEIGHBOR_SHAPE
        and neighbor.dtype.str == DTYPE
    )
    latent_valid = (
        tuple(latent.shape) == LATENT_SHAPE
        and latent.dtype.str == DTYPE
        and latent_summary["nonfinite_count"] == 0
        and latent_summary["unique_row_sha256_count"] == 8
        and np.count_nonzero(latent[0]) == 0
    )
    same_ego = input_summary["all_nonlatent_input_rows_exact_equal"]
    finite = (
        candidate_summary["nonfinite_count"] == 0
        and neighbor_summary["nonfinite_count"] == 0
    )
    topology_valid = (
        model_call_count == 1
        and sequential_model_call_count == 0
        and selector_call_count == 0
        and input_summary["batch_size"] == 8
        and input_summary["source_ego_state_count"] == 1
        and input_summary["agent_as_ego_batch"] is False
    )
    if not latent_valid:
        taxonomy = TAXONOMY[1]
    elif not same_ego:
        taxonomy = TAXONOMY[2]
    elif not finite:
        taxonomy = TAXONOMY[3]
    elif not output_shape_valid or not topology_valid:
        taxonomy = TAXONOMY[5]
    elif candidate_summary["unique_row_sha256_count"] != 8:
        taxonomy = TAXONOMY[4]
    else:
        taxonomy = TAXONOMY[0]
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "state_spec_id": STATE_SPEC_ID,
        "mode": MODE,
        "repeat_index": REPEAT_INDEX,
        "latent_summary": latent_summary,
        "expanded_input_summary": input_summary,
        "candidate_summary": candidate_summary,
        "neighbor_summary": neighbor_summary,
        "base_bindings": bindings,
        "formal_forward_id": forward_id,
        "pool_id": pool_id,
        "candidate0_rule": "candidate_tensor_row0",
        "candidate0_row_sha256": candidate_summary["row_sha256"][0]
        if candidate_summary["row_sha256"]
        else None,
        "row0_candidate0_binding": True,
        "pool_generation_latency_ns": int(pool_generation_latency_ns),
        "pool_generation_latency_scope": (
            "expanded_input_clone_through_formal_forward_and_cpu_output_materialization"
        ),
        "model_call_count": int(model_call_count),
        "sequential_model_call_count": int(sequential_model_call_count),
        "selector_call_count": int(selector_call_count),
        "stop_before_selector": True,
        "taxonomy": taxonomy,
        "raw_outcome_read": False,
        "remaining_calibration_run_count": 0,
        "threshold_validation_closed_loop_fresh_holdout_training_count": 0,
        "old_artifact_cas_write_count": 0,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    return receipt


def diagnostic_contract(
    *,
    implementation_head: str,
    exact_dirs: Mapping[str, str],
    source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    _head(implementation_head)
    if type(exact_dirs) is not dict or set(exact_dirs) != set(EXACT_DIR_KEYS):
        raise ValueError("exact dir keyset drifted")
    if type(source_sha256) is not dict or set(source_sha256) != set(SOURCE_KEYS):
        raise ValueError("source SHA keyset drifted")
    for value in exact_dirs.values():
        if type(value) is not str or not value.startswith("/root/autodl-tmp/"):
            raise ValueError("exact dir must be under /root/autodl-tmp")
    for value in source_sha256.values():
        _sha(value)
    decoded = json.loads(HIGH_AUTHORITY_JSON)
    if (
        json.dumps(decoded, sort_keys=True, separators=(",", ":"))
        != HIGH_AUTHORITY_JSON
        or sha256_bytes(HIGH_AUTHORITY_JSON.encode("ascii"))
        != HIGH_AUTHORITY_SHA256
    ):
        raise ValueError("High authority canonical bytes drifted")
    result = {
        "schema_version": CONTRACT_SCHEMA,
        "status": "outcome_independent_batch8_first_state_contract_frozen",
        "high_authority_json": HIGH_AUTHORITY_JSON,
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "model_source_sha256": MODEL_SOURCE_SHA256,
        "exact_dirs": dict(exact_dirs),
        "source_sha256": dict(source_sha256),
        "authorized_identity": {
            "state_spec_id": STATE_SPEC_ID,
            "mode": MODE,
            "repeat_index": REPEAT_INDEX,
            "source_ego_state_count": 1,
            "expanded_model_batch_size": 8,
            "agent_as_ego_batch": False,
            "formal_model_invocation_count": 1,
            "sequential_model_call_count": 0,
            "selector_call_count": 0,
            "stop_before_selector": True,
        },
        "latent_contract": {
            "seed": LATENT_SEED,
            "shape": list(LATENT_SHAPE),
            "dtype": DTYPE,
            "policy": (
                "row0_zero_rows1_7_independent_pcg64_standard_normal_float32"
            ),
            "rows1_7_draw_shape": [7, 321, 81, 4],
            "unique_row_sha256_count_required": 8,
        },
        "output_contract": {
            "candidate_shape": list(CANDIDATE_SHAPE),
            "neighbor_shape": list(NEIGHBOR_SHAPE),
            "dtype": DTYPE,
            "candidate0_rule": "candidate_tensor_row0",
            "pool_latency_scope": (
                "expanded_input_clone_through_formal_forward_and_cpu_output_materialization"
            ),
        },
        "taxonomy": list(TAXONOMY),
        "old_preflight_roots": {
            "preflight": OLD_PREFLIGHT_ROOT,
            "preflight_review": OLD_PREFLIGHT_REVIEW_ROOT,
        },
        "scientific_boundary": {
            "full_calibration_authorized": False,
            "threshold_validation_closed_loop_fresh_holdout_training_authorized": False,
            "fixed_dp_model_weights_atoms_change_authorized": False,
            "old_artifact_cas_write_authorized": False,
            "outcome_read_authorized": False,
            "claim_authorized": False,
            "return_to_high_after_diagnostic": True,
        },
    }
    result["contract_sha256"] = sha256_bytes(canonical_bytes(result))
    return result


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError("contract must be plain object")
    expected = diagnostic_contract(
        implementation_head=value.get("implementation_head"),
        exact_dirs=value.get("exact_dirs"),
        source_sha256=value.get("source_sha256"),
    )
    if dict(value) != expected:
        raise ValueError("batch8 diagnostic contract drifted")
    return dict(value)


def _sha(value: Any) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError("expected SHA256")
    int(value, 16)
    return value


def _head(value: Any) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError("expected git SHA")
    int(value, 16)
    return value
