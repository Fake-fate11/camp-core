from __future__ import annotations

import ast
import hashlib
import json
from typing import Any, Mapping

import numpy as np


SCHEMA_VERSION = "camp_dp_v25_sequential_latent_injection_source_audit_v1"
CONTRACT_SCHEMA_VERSION = (
    "camp_dp_v25_sequential_latent_injection_source_audit_contract_v1"
)
AUTHORITY_SCHEMA_VERSION = (
    "camp_dp_v25_sequential_latent_injection_source_audit_high_authority_v1"
)
HIGH_AUTHORITY_SHA256 = (
    "f9a91cbeac8f004cbac8b87bf170e51d54a1a09f5bc25fb256c3abd9e5106ba4"
)
HIGH_AUTHORITY_JSON = (
    '{"allowed_inputs":["sealed_first_state_preimage_and_receipt",'
    '"fixed_dp_source_at_pinned_head","camp_source_at_pinned_head"],'
    '"calibration_640_authorized":false,'
    '"control_source_thread_id":"019f6eee-8fc2-75f3-843c-75562f610b13",'
    '"decision":"authorized_zero_model_call_source_and_sealed_evidence_audit",'
    '"diagnostic_implementation_head":'
    '"bacc9d2a795c471f1547823528a4c06d5372ea18",'
    '"diagnostic_review_root_sha256":'
    '"8767856884b6597668a22c9c3dc1db8aa3dfacce329d29fe5002b26fa77c95ca",'
    '"diagnostic_root_sha256":'
    '"685c1529a95409f9f92220ac40d02c054d939bc93410e2ce4c0608e0e6dbffb8",'
    '"engineering_fix_allowed":'
    '"proposal_and_tdd_only_no_model_execution_before_high_review",'
    '"executor_thread_id":"019f92f5-eb4e-78d1-88ea-8ee1f4335eb3",'
    '"fixed_dp_head":"7a1d33da277a1992ec474b5383a0c963c72e04e4",'
    '"fixed_dp_weights_change_authorized":false,'
    '"mode":"sequential_batch1_x8","new_model_pool_selector_call_count":0,'
    '"old_artifact_cas_write_authorized":false,'
    '"pointer_head":"c1c4a19a5d3e93605fb46f1a4fe529fac3458f8d",'
    '"precondition_receipt_sha256":'
    '"d97fc4bbcfdb1ccf8fed517b8c47b89e7401952b1a9b5b5f1766ae50f38f3a45",'
    '"provider_task_id":"019f92d8-c971-7b13-924e-873ae9f24c14",'
    '"repeat_index":0,"requested_latent_row_count":8,'
    '"required_latent_checks":["raw_bytes_sha256","shape_dtype_finite",'
    '"unique_cardinality_duplicate_groups",'
    '"row_to_call_to_forward_to_output_binding"],'
    '"required_static_dataflow":["latent_construction","batch_and_input_assembly",'
    '"Diffusion_Planner.forward","decoder_consumption",'
    '"clone_broadcast_index_seed_overwrite_default_ignored_argument"],'
    '"schema_version":'
    '"camp_dp_v25_sequential_latent_injection_source_audit_high_authority_v1",'
    '"single_invocation_batch8_scope":"source_contract_only_no_runtime_conclusion",'
    '"state_spec_id":"development_calibration:000",'
    '"stop_if_new_model_evidence_required":true,'
    '"taxonomy":["latent_input_rows_repeated",'
    '"latent_rows_unique_but_not_consumed",'
    '"latent_rows_consumed_model_mapping_collapsed","evidence_binding_error",'
    '"unresolved_requires_minimal_new_model_evidence"],'
    '"taxonomy_mutually_exclusive_exhaustive":true,'
    '"threshold_validation_closed_loop_fresh_training_authorized":false}'
)

STATE_SPEC_ID = "development_calibration:000"
MODE = "sequential_batch1_x8"
REPEAT_INDEX = 0
LATENT_SEED = 61000
LATENT_SHAPE = (8, 321, 81, 4)
LATENT_DTYPE = "<f4"
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
TENSOR_DTYPE = "<f4"
TAXONOMY = (
    "latent_input_rows_repeated",
    "latent_rows_unique_but_not_consumed",
    "latent_rows_consumed_model_mapping_collapsed",
    "evidence_binding_error",
    "unresolved_requires_minimal_new_model_evidence",
)
SOURCE_KEYS = (
    "camp_diagnostic_materializer",
    "camp_input_manifest_v2",
    "fixed_dp_model",
    "fixed_dp_decoder",
)
EXACT_DIR_KEYS = (
    "contract",
    "contract_review",
    "focused",
    "audit",
    "audit_review",
)
SHA_HEX = set("0123456789abcdef")

_REQUIRED_FUNCTIONS = {
    "camp_diagnostic_materializer": (
        "_latent",
        "_expanded_inputs",
        "_forward_id",
        "main",
    ),
    "camp_input_manifest_v2": ("materialize_latent_manifest",),
    "fixed_dp_model": ("forward",),
    "fixed_dp_decoder": (
        "_inference_flow_matching",
        "_inference_x_start",
        "_forward_inference",
        "forward",
    ),
}
_REQUIRED_TOKENS = {
    "camp_diagnostic_materializer": (
        "value[1:] = rng.standard_normal(value.shape[1:]).astype(np.float32)",
        'expanded["sampled_trajectories"] = latent_tensor.contiguous()',
        "for row_index in range(8):",
        "value[row_index : row_index + 1].contiguous()",
        "_encoded, outputs = model(row_inputs)",
        '"latent_tensor_sha256": bindings["latent_tensor_sha256"]',
    ),
    "camp_input_manifest_v2": (
        "latent[1:] = rng.standard_normal(LATENT_SHAPE[1:]).astype(np.float32)",
        '"tensor_sha256": hashlib.sha256(raw).hexdigest()',
    ),
    "fixed_dp_model": (
        "encoder_outputs = self.encoder(inputs)",
        "decoder_outputs = self.decoder(encoder_outputs, inputs)",
    ),
    "fixed_dp_decoder": (
        'sampled_trajectories = inputs["sampled_trajectories"].reshape(',
        "x = sampled_trajectories",
        "x = euler_integration(func, x, NUM_STEP)",
        "xT = sampled_trajectories",
        "x0 = dpm_solver.sample(xT, steps=10, prefix_mask=mask, skip_type=\"logSNR\")",
    ),
}


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


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - SHA_HEX:
        raise ValueError(f"{label} must be lowercase SHA256")
    return value


def _git_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or set(value) - SHA_HEX:
        raise ValueError(f"{label} must be lowercase Git SHA")
    return value


def _exact_keys(value: Mapping[str, Any], expected: tuple[str, ...], label: str) -> None:
    if set(value) != set(expected):
        raise ValueError(f"{label} field set drifted")


def _duplicate_groups(row_sha256: list[str]) -> list[list[int]]:
    groups: dict[str, list[int]] = {}
    for index, digest in enumerate(row_sha256):
        groups.setdefault(digest, []).append(index)
    return [indices for indices in groups.values() if len(indices) > 1]


def reconstruct_requested_latent() -> tuple[np.ndarray, bytes, dict[str, Any]]:
    rng = np.random.default_rng(LATENT_SEED)
    latent = np.zeros(LATENT_SHAPE, dtype=np.float32)
    # This exactly reconstructs the sealed v5/diagnostic source.  The RHS has
    # no candidate axis and NumPy broadcasts one draw to rows 1 through 7.
    latent[1:] = rng.standard_normal(LATENT_SHAPE[1:]).astype(np.float32)
    latent = np.ascontiguousarray(latent, dtype=LATENT_DTYPE)
    raw = latent.tobytes(order="C")
    row_sha256 = [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in latent
    ]
    summary = {
        "shape": list(LATENT_SHAPE),
        "dtype": LATENT_DTYPE,
        "finite": bool(np.isfinite(latent).all()),
        "nonfinite_indices": np.argwhere(~np.isfinite(latent)).astype(int).tolist(),
        "tensor_sha256": sha256_bytes(raw),
        "row_sha256": row_sha256,
        "unique_cardinality": len(set(row_sha256)),
        "duplicate_groups": _duplicate_groups(row_sha256),
        "seed": LATENT_SEED,
        "bit_generator": "PCG64",
        "construction_rhs_shape": list(LATENT_SHAPE[1:]),
        "assignment_lhs_shape": list(latent[1:].shape),
        "numpy_broadcast_applied": True,
    }
    return latent, raw, summary


def source_semantics(source_texts: Mapping[str, str]) -> dict[str, Any]:
    _exact_keys(source_texts, SOURCE_KEYS, "source text")
    result: dict[str, Any] = {}
    for key in SOURCE_KEYS:
        text = source_texts[key]
        if not isinstance(text, str):
            raise ValueError(f"{key} source must be text")
        tree = ast.parse(text)
        functions = {
            node.name: [int(node.lineno), int(node.end_lineno or node.lineno)]
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        required = _REQUIRED_FUNCTIONS[key]
        if any(name not in functions for name in required):
            raise ValueError(f"{key} required function missing")
        tokens = _REQUIRED_TOKENS[key]
        if any(token not in text for token in tokens):
            raise ValueError(f"{key} dataflow token drifted")
        result[key] = {
            "sha256": sha256_bytes(text.encode("utf-8")),
            "function_spans": {name: functions[name] for name in required},
            "required_tokens_sha256": sha256_bytes(
                canonical_json_bytes(list(tokens))
            ),
        }
    result["dataflow"] = {
        "latent_construction": (
            "PCG64 seed 61000; row0 zeros; one [321,81,4] draw is NumPy-"
            "broadcast to requested rows1-7"
        ),
        "batch_and_input_assembly": (
            "batch1 base tensors expand to 8; sampled_trajectories is overwritten "
            "by reconstructed latent; sequential call i slices row i"
        ),
        "Diffusion_Planner.forward": (
            "the unchanged inputs mapping is passed encoder then decoder"
        ),
        "decoder_consumption": (
            "inference reshapes inputs.sampled_trajectories; flow matching consumes "
            "it as x and x-start consumes it as xT"
        ),
        "clone_broadcast_index_seed_overwrite_default_ignored_argument": (
            "no formal latent argument exists; sampled_trajectories is the consumed "
            "input key; broadcast happens during latent construction before overwrite"
        ),
    }
    return result


def source_audit_contract(
    *,
    implementation_head: str,
    exact_dirs: Mapping[str, str],
    source_sha256: Mapping[str, str],
    producer_source_sha256: str,
    reviewer_source_sha256: str,
) -> dict[str, Any]:
    _git_sha(implementation_head, "implementation HEAD")
    _exact_keys(exact_dirs, EXACT_DIR_KEYS, "exact dirs")
    _exact_keys(source_sha256, SOURCE_KEYS, "source SHA")
    if any(not isinstance(value, str) or not value for value in exact_dirs.values()):
        raise ValueError("exact dir invalid")
    for key, value in source_sha256.items():
        _sha256(value, f"{key} source")
    _sha256(producer_source_sha256, "producer source")
    _sha256(reviewer_source_sha256, "reviewer source")
    authority = json.loads(HIGH_AUTHORITY_JSON)
    if (
        list(authority) != sorted(authority)
        or authority["schema_version"] != AUTHORITY_SCHEMA_VERSION
        or sha256_bytes(HIGH_AUTHORITY_JSON.encode("ascii"))
        != HIGH_AUTHORITY_SHA256
    ):
        raise ValueError("canonical High authority drifted")
    return {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "status": "outcome_independent_zero_model_call_source_audit_contract_frozen",
        "high_authority_json": HIGH_AUTHORITY_JSON,
        "high_authority_sha256": HIGH_AUTHORITY_SHA256,
        "implementation_head": implementation_head,
        "pointer_head": authority["pointer_head"],
        "fixed_dp_head": authority["fixed_dp_head"],
        "diagnostic_root_sha256": authority["diagnostic_root_sha256"],
        "diagnostic_review_root_sha256": authority[
            "diagnostic_review_root_sha256"
        ],
        "precondition_receipt_sha256": authority[
            "precondition_receipt_sha256"
        ],
        "exact_dirs": dict(exact_dirs),
        "source_sha256": dict(source_sha256),
        "required_source_functions": {
            key: list(_REQUIRED_FUNCTIONS[key]) for key in SOURCE_KEYS
        },
        "required_source_tokens_sha256": {
            key: sha256_bytes(canonical_json_bytes(list(_REQUIRED_TOKENS[key])))
            for key in SOURCE_KEYS
        },
        "latent_contract": {
            "seed": LATENT_SEED,
            "shape": list(LATENT_SHAPE),
            "dtype": LATENT_DTYPE,
            "requested_row_count": 8,
            "row0_zero": True,
            "rows1_7_rhs_shape": list(LATENT_SHAPE[1:]),
            "assignment_lhs_shape": [7, *LATENT_SHAPE[1:]],
            "broadcast_semantics": "numpy_trailing_axis_broadcast",
        },
        "row_binding_contract": [
            "latent_row_sha256",
            "sequential_call_index",
            "forward_id",
            "candidate_output_row_sha256",
            "neighbor_output_row_sha256",
        ],
        "taxonomy": list(TAXONOMY),
        "taxonomy_mutually_exclusive_exhaustive": True,
        "new_model_pool_selector_call_count": 0,
        "single_invocation_batch8_runtime_conclusion_authorized": False,
        "calibration_640_authorized": False,
        "threshold_validation_closed_loop_fresh_training_authorized": False,
        "fixed_dp_weights_or_latent_policy_change_authorized": False,
        "engineering_fix_scope": (
            "proposal_and_tdd_only_no_model_execution_before_high_review"
        ),
        "producer_source_sha256": producer_source_sha256,
        "reviewer_source_sha256": reviewer_source_sha256,
    }


def validate_source_audit_contract(contract: Mapping[str, Any]) -> None:
    expected = source_audit_contract(
        implementation_head=contract["implementation_head"],
        exact_dirs=contract["exact_dirs"],
        source_sha256=contract["source_sha256"],
        producer_source_sha256=contract["producer_source_sha256"],
        reviewer_source_sha256=contract["reviewer_source_sha256"],
    )
    if dict(contract) != expected:
        raise ValueError("source-audit contract drifted")


def _decode(raw: bytes, shape: tuple[int, ...]) -> np.ndarray:
    expected = int(np.prod(shape)) * np.dtype(TENSOR_DTYPE).itemsize
    if len(raw) != expected:
        raise ValueError("sealed tensor byte count drifted")
    return np.frombuffer(raw, dtype=TENSOR_DTYPE).reshape(shape).copy()


def _forward_id(
    *,
    index: int,
    bindings: Mapping[str, Any],
    candidate_row_sha256: str,
    neighbor_row_sha256: str,
) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "state_spec_id": STATE_SPEC_ID,
                "mode": MODE,
                "repeat_index": REPEAT_INDEX,
                "row_index": index,
                "input_manifest_sha256": bindings["input_manifest_sha256"],
                "actual_input_tensor_bundle_sha256": bindings[
                    "actual_input_tensor_bundle_sha256"
                ],
                "actual_state_sha256": bindings["actual_state_sha256"],
                "latent_tensor_sha256": bindings["latent_tensor_sha256"],
                "model_source_sha256": bindings["model_source_sha256"],
                "checkpoint_sha256": bindings["checkpoint_sha256"],
                "fixed_dp_head": bindings["fixed_dp_head"],
                "candidate_row_sha256": candidate_row_sha256,
                "neighbor_row_sha256": neighbor_row_sha256,
            }
        )
    )


def materialize_source_audit(
    *,
    contract: Mapping[str, Any],
    precondition_receipt: Mapping[str, Any],
    first_state_manifest: Mapping[str, Any],
    candidate_bytes: bytes,
    neighbor_bytes: bytes,
    source_texts: Mapping[str, str],
) -> dict[str, Any]:
    validate_source_audit_contract(contract)
    semantics = source_semantics(source_texts)
    for key in SOURCE_KEYS:
        if semantics[key]["sha256"] != contract["source_sha256"][key]:
            raise ValueError(f"{key} source binding drifted")
    receipt_preimage = dict(precondition_receipt)
    receipt_sha256 = receipt_preimage.pop("receipt_sha256", None)
    if (
        receipt_sha256 != contract["precondition_receipt_sha256"]
        or sha256_bytes(canonical_json_bytes(receipt_preimage)) != receipt_sha256
    ):
        raise ValueError("precondition receipt bytes drifted")
    if (
        precondition_receipt.get("state_spec_id") != STATE_SPEC_ID
        or precondition_receipt.get("mode") != MODE
        or precondition_receipt.get("repeat_index") != REPEAT_INDEX
        or precondition_receipt.get("model_call_count") != 8
        or precondition_receipt.get("selector_call_count") != 0
    ):
        raise ValueError("precondition receipt identity drifted")

    latent, latent_bytes, latent_summary = reconstruct_requested_latent()
    latent_manifest = first_state_manifest["actual_latent_tensor_manifest"]
    if (
        latent_manifest["seed"] != LATENT_SEED
        or latent_manifest["shape"] != list(LATENT_SHAPE)
        or latent_manifest["dtype"] != LATENT_DTYPE
        or latent_manifest["tensor_sha256"] != latent_summary["tensor_sha256"]
        or precondition_receipt["bindings"]["latent_tensor_sha256"]
        != latent_summary["tensor_sha256"]
    ):
        raise ValueError("sealed requested latent binding drifted")
    if first_state_manifest["manifest_sha256"] != precondition_receipt["bindings"][
        "input_manifest_sha256"
    ]:
        raise ValueError("first-state manifest binding drifted")

    candidate = _decode(candidate_bytes, CANDIDATE_SHAPE)
    neighbor = _decode(neighbor_bytes, NEIGHBOR_SHAPE)
    candidate_rows = [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in candidate
    ]
    neighbor_rows = [
        sha256_bytes(np.ascontiguousarray(row).tobytes(order="C"))
        for row in neighbor
    ]
    if (
        sha256_bytes(candidate_bytes)
        != precondition_receipt["candidate_tensor_sha256"]
        or sha256_bytes(neighbor_bytes)
        != precondition_receipt["neighbor_tensor_sha256"]
        or candidate_rows != precondition_receipt["candidate_row_sha256"]
    ):
        raise ValueError("sealed output tensor binding drifted")
    bindings = precondition_receipt["bindings"]
    expected_forward = [
        _forward_id(
            index=index,
            bindings=bindings,
            candidate_row_sha256=candidate_rows[index],
            neighbor_row_sha256=neighbor_rows[index],
        )
        for index in range(8)
    ]
    if expected_forward != bindings["forward_ids"]:
        raise ValueError("row/call/forward/output binding drifted")

    row_bindings = [
        {
            "latent_row_index": index,
            "latent_row_sha256": latent_summary["row_sha256"][index],
            "sequential_call_index": index,
            "forward_id": expected_forward[index],
            "candidate_output_row_sha256": candidate_rows[index],
            "neighbor_output_row_sha256": neighbor_rows[index],
        }
        for index in range(8)
    ]
    if latent_summary["duplicate_groups"]:
        taxonomy = "latent_input_rows_repeated"
    else:
        # The pinned source shows direct consumption.  If unique inputs had
        # collapsed outputs this would be the model-mapping category.
        candidate_duplicates = _duplicate_groups(candidate_rows)
        neighbor_duplicates = _duplicate_groups(neighbor_rows)
        taxonomy = (
            "latent_rows_consumed_model_mapping_collapsed"
            if candidate_duplicates or neighbor_duplicates
            else "unresolved_requires_minimal_new_model_evidence"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "zero_model_call_source_and_sealed_evidence_audit_complete",
        "classification": taxonomy,
        "taxonomy": list(TAXONOMY),
        "taxonomy_mutually_exclusive_exhaustive": True,
        "latent_summary": latent_summary,
        "latent_tensor_byte_count": len(latent_bytes),
        "candidate_summary": {
            "tensor_sha256": sha256_bytes(candidate_bytes),
            "row_sha256": candidate_rows,
            "unique_cardinality": len(set(candidate_rows)),
            "duplicate_groups": _duplicate_groups(candidate_rows),
        },
        "neighbor_summary": {
            "tensor_sha256": sha256_bytes(neighbor_bytes),
            "row_sha256": neighbor_rows,
            "unique_cardinality": len(set(neighbor_rows)),
            "duplicate_groups": _duplicate_groups(neighbor_rows),
        },
        "row_bindings": row_bindings,
        "source_semantics": semantics,
        "evidence_binding_complete": True,
        "new_model_call_count": 0,
        "new_pool_call_count": 0,
        "new_selector_call_count": 0,
        "single_invocation_batch8_runtime_conclusion": "not_authorized",
        "engineering_finding": (
            "sealed_v5_latent_constructor_draws_one_rows1_7_preimage_and_"
            "numpy_broadcasts_it_to_seven_sequential_calls"
        ),
        "minimal_fix_status": (
            "proposal_only_requires_new_versioned_latent_policy_contract_before_execution"
        ),
        "calibration_640_authorized": False,
        "threshold_validation_closed_loop_fresh_training_authorized": False,
        "claim_authorized": False,
        "raw_outcome_read": False,
        "old_artifact_or_cas_write_count": 0,
    }
