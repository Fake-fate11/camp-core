from __future__ import annotations

import ast
import hashlib
import json
from typing import Any, Mapping

import numpy as np


AUTHORITY_SHA = "f9a91cbeac8f004cbac8b87bf170e51d54a1a09f5bc25fb256c3abd9e5106ba4"
STATE = "development_calibration:000"
MODE = "sequential_batch1_x8"
SEED = 61000
LATENT_SHAPE = (8, 321, 81, 4)
CANDIDATE_SHAPE = (8, 80, 4)
NEIGHBOR_SHAPE = (8, 32, 80, 4)
DTYPE = "<f4"
SOURCE_KEYS = (
    "camp_diagnostic_materializer",
    "camp_input_manifest_v2",
    "fixed_dp_model",
    "fixed_dp_decoder",
)
TAXONOMY = (
    "latent_input_rows_repeated",
    "latent_rows_unique_but_not_consumed",
    "latent_rows_consumed_model_mapping_collapsed",
    "evidence_binding_error",
    "unresolved_requires_minimal_new_model_evidence",
)
EXACT_DIR_KEYS = (
    "contract",
    "contract_review",
    "focused",
    "audit",
    "audit_review",
)
TOKENS = {
    "camp_diagnostic_materializer": (
        "value[1:] = rng.standard_normal(value.shape[1:]).astype(np.float32)",
        'expanded["sampled_trajectories"] = latent_tensor.contiguous()',
        "for row_index in range(8):",
        "value[row_index : row_index + 1].contiguous()",
        "_encoded, outputs = model(row_inputs)",
    ),
    "camp_input_manifest_v2": (
        "latent[1:] = rng.standard_normal(LATENT_SHAPE[1:]).astype(np.float32)",
    ),
    "fixed_dp_model": (
        "encoder_outputs = self.encoder(inputs)",
        "decoder_outputs = self.decoder(encoder_outputs, inputs)",
    ),
    "fixed_dp_decoder": (
        'sampled_trajectories = inputs["sampled_trajectories"].reshape(',
        "x = sampled_trajectories",
        "xT = sampled_trajectories",
        "x0 = dpm_solver.sample(xT, steps=10, prefix_mask=mask, skip_type=\"logSNR\")",
    ),
}


def review_source_audit_contract(
    contract: Mapping[str, Any],
    *,
    expected_implementation_head: str,
    expected_exact_dirs: Mapping[str, str],
    expected_source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    if (
        set(contract) != {
            "schema_version",
            "status",
            "high_authority_json",
            "high_authority_sha256",
            "implementation_head",
            "pointer_head",
            "fixed_dp_head",
            "diagnostic_root_sha256",
            "diagnostic_review_root_sha256",
            "precondition_receipt_sha256",
            "exact_dirs",
            "source_sha256",
            "required_source_functions",
            "required_source_tokens_sha256",
            "latent_contract",
            "row_binding_contract",
            "taxonomy",
            "taxonomy_mutually_exclusive_exhaustive",
            "new_model_pool_selector_call_count",
            "single_invocation_batch8_runtime_conclusion_authorized",
            "calibration_640_authorized",
            "threshold_validation_closed_loop_fresh_training_authorized",
            "fixed_dp_weights_or_latent_policy_change_authorized",
            "engineering_fix_scope",
            "producer_source_sha256",
            "reviewer_source_sha256",
        }
        or contract["schema_version"]
        != "camp_dp_v25_sequential_latent_injection_source_audit_contract_v1"
        or contract["high_authority_sha256"] != AUTHORITY_SHA
        or _sha(contract["high_authority_json"].encode("ascii")) != AUTHORITY_SHA
        or contract["implementation_head"] != expected_implementation_head
        or contract["pointer_head"]
        != "c1c4a19a5d3e93605fb46f1a4fe529fac3458f8d"
        or contract["fixed_dp_head"]
        != "7a1d33da277a1992ec474b5383a0c963c72e04e4"
        or contract["diagnostic_root_sha256"]
        != "685c1529a95409f9f92220ac40d02c054d939bc93410e2ce4c0608e0e6dbffb8"
        or contract["diagnostic_review_root_sha256"]
        != "8767856884b6597668a22c9c3dc1db8aa3dfacce329d29fe5002b26fa77c95ca"
        or contract["precondition_receipt_sha256"]
        != "d97fc4bbcfdb1ccf8fed517b8c47b89e7401952b1a9b5b5f1766ae50f38f3a45"
        or set(contract["exact_dirs"]) != set(EXACT_DIR_KEYS)
        or dict(contract["exact_dirs"]) != dict(expected_exact_dirs)
        or set(contract["source_sha256"]) != set(SOURCE_KEYS)
        or dict(contract["source_sha256"]) != dict(expected_source_sha256)
    ):
        raise ValueError("independent contract authority/binding drifted")
    authority = json.loads(contract["high_authority_json"])
    if (
        authority["decision"]
        != "authorized_zero_model_call_source_and_sealed_evidence_audit"
        or authority["new_model_pool_selector_call_count"] != 0
        or authority["state_spec_id"] != STATE
        or authority["mode"] != MODE
        or authority["repeat_index"] != 0
        or authority["taxonomy"] != list(TAXONOMY)
        or authority["taxonomy_mutually_exclusive_exhaustive"] is not True
        or authority["calibration_640_authorized"] is not False
        or authority[
            "threshold_validation_closed_loop_fresh_training_authorized"
        ]
        is not False
    ):
        raise ValueError("independent contract authority semantics drifted")
    if (
        contract["latent_contract"]
        != {
            "seed": 61000,
            "shape": [8, 321, 81, 4],
            "dtype": "<f4",
            "requested_row_count": 8,
            "row0_zero": True,
            "rows1_7_rhs_shape": [321, 81, 4],
            "assignment_lhs_shape": [7, 321, 81, 4],
            "broadcast_semantics": "numpy_trailing_axis_broadcast",
        }
        or contract["row_binding_contract"]
        != [
            "latent_row_sha256",
            "sequential_call_index",
            "forward_id",
            "candidate_output_row_sha256",
            "neighbor_output_row_sha256",
        ]
        or contract["taxonomy"] != list(TAXONOMY)
        or contract["taxonomy_mutually_exclusive_exhaustive"] is not True
        or contract["new_model_pool_selector_call_count"] != 0
        or contract["single_invocation_batch8_runtime_conclusion_authorized"]
        is not False
        or contract["calibration_640_authorized"] is not False
        or contract[
            "threshold_validation_closed_loop_fresh_training_authorized"
        ]
        is not False
        or contract["fixed_dp_weights_or_latent_policy_change_authorized"]
        is not False
    ):
        raise ValueError("independent contract scientific boundary drifted")
    return {
        "schema_version": (
            "camp_dp_v25_sequential_latent_injection_source_audit_"
            "contract_review_v1"
        ),
        "status": "passed_independent_literal_contract_review",
        "implementation_head": expected_implementation_head,
        "high_authority_sha256": AUTHORITY_SHA,
        "source_count": 4,
        "taxonomy_count": 5,
        "new_model_pool_selector_call_count": 0,
        "calibration_640_authorized": False,
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


def _rows(array: np.ndarray) -> list[str]:
    return [_sha(np.ascontiguousarray(row).tobytes(order="C")) for row in array]


def _groups(rows: list[str]) -> list[list[int]]:
    buckets: dict[str, list[int]] = {}
    for index, digest in enumerate(rows):
        buckets.setdefault(digest, []).append(index)
    return [indices for indices in buckets.values() if len(indices) > 1]


def _decode(raw: bytes, shape: tuple[int, ...]) -> np.ndarray:
    if len(raw) != int(np.prod(shape)) * 4:
        raise ValueError("review tensor byte count drifted")
    return np.frombuffer(raw, dtype=DTYPE).reshape(shape).copy()


def _latent() -> tuple[bytes, dict[str, Any]]:
    generator = np.random.Generator(np.random.PCG64(SEED))
    value = np.zeros(LATENT_SHAPE, dtype=np.float32)
    draw = generator.standard_normal(LATENT_SHAPE[1:]).astype(np.float32)
    for index in range(1, 8):
        value[index] = draw
    value = np.ascontiguousarray(value, dtype=DTYPE)
    raw = value.tobytes(order="C")
    rows = _rows(value)
    return raw, {
        "shape": list(LATENT_SHAPE),
        "dtype": DTYPE,
        "finite": bool(np.isfinite(value).all()),
        "nonfinite_indices": [],
        "tensor_sha256": _sha(raw),
        "row_sha256": rows,
        "unique_cardinality": len(set(rows)),
        "duplicate_groups": _groups(rows),
        "seed": SEED,
        "bit_generator": "PCG64",
        "construction_rhs_shape": [321, 81, 4],
        "assignment_lhs_shape": [7, 321, 81, 4],
        "numpy_broadcast_applied": True,
    }


def _forward(
    index: int,
    bindings: Mapping[str, Any],
    candidate_sha: str,
    neighbor_sha: str,
) -> str:
    return _sha(
        _canonical(
            {
                "state_spec_id": STATE,
                "mode": MODE,
                "repeat_index": 0,
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
                "candidate_row_sha256": candidate_sha,
                "neighbor_row_sha256": neighbor_sha,
            }
        )
    )


def review_source_audit(
    *,
    contract: Mapping[str, Any],
    audit_report: Mapping[str, Any],
    requested_latent_bytes: bytes,
    candidate_bytes: bytes,
    neighbor_bytes: bytes,
    precondition_receipt: Mapping[str, Any],
    first_state_manifest: Mapping[str, Any],
    source_texts: Mapping[str, str],
) -> dict[str, Any]:
    if (
        contract.get("high_authority_sha256") != AUTHORITY_SHA
        or contract.get("new_model_pool_selector_call_count") != 0
        or contract.get("calibration_640_authorized") is not False
        or contract.get("taxonomy") != list(TAXONOMY)
    ):
        raise ValueError("review contract authority drifted")
    if set(source_texts) != set(SOURCE_KEYS):
        raise ValueError("review source set drifted")
    local_spans: dict[str, Any] = {}
    for key in SOURCE_KEYS:
        text = source_texts[key]
        if _sha(text.encode("utf-8")) != contract["source_sha256"][key]:
            raise ValueError("review source SHA drifted")
        if any(token not in text for token in TOKENS[key]):
            raise ValueError("review source dataflow semantics drifted")
        tree = ast.parse(text)
        spans = {
            node.name: [int(node.lineno), int(node.end_lineno or node.lineno)]
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        if not spans:
            raise ValueError("review source AST lacks functions")
        local_spans[key] = spans

    local_latent, latent_summary = _latent()
    if local_latent != requested_latent_bytes:
        raise ValueError("review requested latent bytes drifted")
    manifest = first_state_manifest["actual_latent_tensor_manifest"]
    if (
        manifest["seed"] != SEED
        or manifest["tensor_sha256"] != latent_summary["tensor_sha256"]
        or precondition_receipt["bindings"]["latent_tensor_sha256"]
        != latent_summary["tensor_sha256"]
    ):
        raise ValueError("review latent authority binding drifted")
    receipt_preimage = dict(precondition_receipt)
    receipt_sha256 = receipt_preimage.pop("receipt_sha256", None)
    if (
        receipt_sha256 != contract["precondition_receipt_sha256"]
        or _sha(_canonical(receipt_preimage)) != receipt_sha256
    ):
        raise ValueError("review precondition receipt drifted")

    candidate = _decode(candidate_bytes, CANDIDATE_SHAPE)
    neighbor = _decode(neighbor_bytes, NEIGHBOR_SHAPE)
    candidate_rows = _rows(candidate)
    neighbor_rows = _rows(neighbor)
    bindings = precondition_receipt["bindings"]
    forward = [
        _forward(index, bindings, candidate_rows[index], neighbor_rows[index])
        for index in range(8)
    ]
    if (
        forward != bindings["forward_ids"]
        or candidate_rows != precondition_receipt["candidate_row_sha256"]
    ):
        raise ValueError("review row/call/forward/output binding drifted")
    row_bindings = [
        {
            "latent_row_index": index,
            "latent_row_sha256": latent_summary["row_sha256"][index],
            "sequential_call_index": index,
            "forward_id": forward[index],
            "candidate_output_row_sha256": candidate_rows[index],
            "neighbor_output_row_sha256": neighbor_rows[index],
        }
        for index in range(8)
    ]
    if latent_summary["duplicate_groups"] != [[1, 2, 3, 4, 5, 6, 7]]:
        raise ValueError("review latent taxonomy precondition drifted")
    if (
        audit_report.get("classification") != "latent_input_rows_repeated"
        or audit_report.get("latent_summary") != latent_summary
        or audit_report.get("row_bindings") != row_bindings
        or audit_report.get("new_model_call_count") != 0
        or audit_report.get("new_pool_call_count") != 0
        or audit_report.get("new_selector_call_count") != 0
        or audit_report.get("raw_outcome_read") is not False
        or audit_report.get("old_artifact_or_cas_write_count") != 0
    ):
        raise ValueError("review producer result disagrees with local reconstruction")
    return {
        "schema_version": (
            "camp_dp_v25_sequential_latent_injection_source_audit_review_v1"
        ),
        "status": "passed_independent_literal_source_and_preimage_reconstruction",
        "classification": "latent_input_rows_repeated",
        "latent_tensor_sha256": latent_summary["tensor_sha256"],
        "latent_row_unique_cardinality": 2,
        "latent_duplicate_groups": [[1, 2, 3, 4, 5, 6, 7]],
        "candidate_row_unique_cardinality": len(set(candidate_rows)),
        "row_binding_count": len(row_bindings),
        "source_ast_file_count": len(local_spans),
        "new_model_pool_selector_call_count": 0,
        "calibration_640_authorized": False,
        "claim_authorized": False,
    }
