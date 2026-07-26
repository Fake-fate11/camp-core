"""Outcome-independent contract for the V25 batch8-primary pool generator.

This additive amendment supersedes the *decision role* of sequential_batch1_x8
without mutating any historical artifact.  It does not execute a model, pool,
selector, calibration, validation, or closed-loop workload.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import numpy as np


SCHEMA_VERSION = (
    "camp_dp_v25_single_invocation_batch8_primary_generator_contract_amendment_v1"
)
ARTIFACT_SCHEMA = (
    "camp_dp_v25_single_invocation_batch8_primary_generator_contract_artifact_v1"
)
AUTHORITY_SCHEMA = (
    "camp_dp_v25_single_invocation_batch8_primary_generator_contract_"
    "amendment_high_authority_v1"
)
GENERATOR_NAME = "new_single_invocation_batched_k8_candidate_pool"
LATENT_POLICY = (
    "eight_prefrozen_unique_rows_row0_zero_rows1_7_independent_"
    "pcg64_standard_normal_float32"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_AUDIT_ROOT = (
    "ef7fed1d077aa2edcdfe4114daaf1904b936ead23d713fc4ba96acbcb8cedc3e"
)
SOURCE_AUDIT_REVIEW_ROOT = (
    "bd81175f3088755e41f799854bcc84d09deca8da1e443b1e20ad7cbd3dd09ef6"
)
SUPERSEDED_AUTHORITY_SHA256 = (
    "f7d90c476de74f0122bce8ffeeab80260d17ad8cd040035ee97c81040e964aef"
)
HIGH_AUTHORITY_JSON = (
    '{"amendment_new_model_pool_selector_call_count":0,'
    '"candidate_axis":"same_ego_expanded_batch_dimension_B_equals_8",'
    '"claim_authorized":false,'
    '"control_source_thread_id":"019f6eee-8fc2-75f3-843c-75562f610b13",'
    '"decision":"authorized_outcome_independent_contract_amendment_and_'
    'independent_review_only",'
    '"executor_thread_id":"019f92f5-eb4e-78d1-88ea-8ee1f4335eb3",'
    '"fixed_dp_model_weights_atoms_change_authorized":false,'
    '"formal_model_invocation_count_per_pool":1,'
    '"full_calibration_threshold_validation_closed_loop_fresh_holdout_training_'
    'authorized":false,'
    '"future_batch8_model_diagnostic_requires_new_high_authority":true,'
    '"latent_policy":"eight_prefrozen_unique_rows_row0_zero_rows1_7_independent_'
    'pcg64_standard_normal_float32",'
    '"native_output_schema_has_independent_K_axis":false,'
    '"old_artifacts_roots_cas_immutable":true,'
    '"operational_batch_size_1_already_has_k8":false,'
    '"primary_generator":"new_single_invocation_batched_k8_candidate_pool",'
    '"provider_task_id":"019f92d8-c971-7b13-924e-873ae9f24c14",'
    '"required_pool_bindings":["same_input_state_model_checkpoint_forward_pool_'
    'tensor_ids","candidate0_is_row0","static_scene_consume_same_tensor",'
    '"post_pool_model_dp_latent_generation_calls_zero"],'
    '"schema_version":"camp_dp_v25_single_invocation_batch8_primary_generator_'
    'contract_amendment_high_authority_v1",'
    '"sequential_batch1_x8_scope":"legacy_non_gating_diagnostic_reference_only",'
    '"sequential_excluded_from":["formal_denominator","hard_pass",'
    '"primary_latency","qualification_decision"],'
    '"source_audit_review_root_sha256":"bd81175f3088755e41f799854bcc84d09'
    'deca8da1e443b1e20ad7cbd3dd09ef6",'
    '"source_audit_root_sha256":"ef7fed1d077aa2edcdfe4114daaf1904b936ead'
    '23d713fc4ba96acbcb8cedc3e",'
    '"superseded_authority_model_execution_allowed":false,'
    '"superseded_authority_sha256":"f7d90c476de74f0122bce8ffeeab80260d17ad'
    '8cd040035ee97c81040e964aef"}'
)
HIGH_AUTHORITY_SHA256 = (
    "16f63578b401a2bb5079035f3c047874dde6adc35cb162a71ed4d5016f197690"
)

EXACT_DIR_KEYS = ("contract", "contract_review", "focused", "final_docs_focused")
SOURCE_KEYS = (
    "producer",
    "reviewer",
    "freeze_script",
    "review_script",
    "tests",
)
POOL_BINDINGS = (
    "input_id",
    "state_id",
    "model_sha256",
    "checkpoint_sha256",
    "forward_invocation_id",
    "pool_id",
    "candidate_tensor_sha256",
)
SEQUENTIAL_EXCLUSIONS = (
    "formal_denominator",
    "hard_pass",
    "primary_latency",
    "qualification_decision",
)
ARMS = ("pool_matched_candidate0", "Static14D", "Scene14D")
POST_POOL_ZERO_CALL_FIELDS = (
    "model_call_count",
    "dp_call_count",
    "latent_generation_count",
    "candidate_generation_count",
)
PROHIBITED_RUNS = (
    "model",
    "pool",
    "selector",
    "calibration",
    "threshold",
    "validation",
    "closed_loop",
    "fresh",
    "holdout",
    "training",
    "retraining",
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
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def materialize_prefrozen_latents(seed: int) -> np.ndarray:
    """Materialize the contract's latent policy without invoking a model."""

    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)):
        raise TypeError("latent seed must be an integer")
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    latent = np.zeros((8, 321, 81, 4), dtype=np.float32)
    latent[1:] = rng.standard_normal(latent[1:].shape).astype(np.float32)
    return latent


def latent_policy_receipt(seed: int) -> dict[str, Any]:
    latent = materialize_prefrozen_latents(seed)
    rows = [hashlib.sha256(row.tobytes(order="C")).hexdigest() for row in latent]
    return {
        "policy": LATENT_POLICY,
        "rng_algorithm": "numpy.random.PCG64",
        "seed": int(seed),
        "shape": [8, 321, 81, 4],
        "dtype": "<f4",
        "row0_all_zero": bool(np.count_nonzero(latent[0]) == 0),
        "rows1_7_draw_shape": [7, 321, 81, 4],
        "rows1_7_single_rhs_broadcast_allowed": False,
        "finite": bool(np.all(np.isfinite(latent))),
        "row_sha256": rows,
        "unique_row_sha256_count": len(set(rows)),
        "tensor_sha256": hashlib.sha256(latent.tobytes(order="C")).hexdigest(),
    }


def contract_amendment(
    *,
    implementation_head: str,
    exact_dirs: Mapping[str, str],
    source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    _head(implementation_head, "implementation_head")
    exact = _exact_map(exact_dirs, EXACT_DIR_KEYS, "exact_dirs")
    sources = _exact_map(source_sha256, SOURCE_KEYS, "source_sha256", sha=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "scientific_contract_review_required",
        "high_authority": {
            "schema_version": AUTHORITY_SCHEMA,
            "canonical_json_ascii": HIGH_AUTHORITY_JSON,
            "sha256": HIGH_AUTHORITY_SHA256,
            "supersedes_authority_sha256": SUPERSEDED_AUTHORITY_SHA256,
            "superseded_authority_model_execution_allowed": False,
        },
        "implementation": {
            "head": implementation_head,
            "source_sha256": sources,
            "exact_dirs": exact,
        },
        "source_audit_binding": {
            "root_sha256": SOURCE_AUDIT_ROOT,
            "review_root_sha256": SOURCE_AUDIT_REVIEW_ROOT,
            "resolved_taxonomy": "latent_input_rows_repeated",
            "historical_sequential_finding_mutated": False,
        },
        "primary_generator_contract": {
            "name": GENERATOR_NAME,
            "formal_model_invocation_count_per_pool": 1,
            "candidate_count": 8,
            "candidate_axis": "same_ego_expanded_batch_dimension_B_equals_8",
            "source_ego_state_count": 1,
            "expanded_model_batch_size": 8,
            "agent_as_ego_batch": False,
            "native_output_schema_has_independent_K_axis": False,
            "operational_batch_size_1_already_has_k8": False,
            "operational_default_batch_size": 1,
            "operational_batch1_role": "architecture_reference_only",
            "future_runtime_diagnostic_requires_new_high_authority": True,
        },
        "latent_policy_contract": {
            "name": LATENT_POLICY,
            "shape": [8, 321, 81, 4],
            "dtype": "<f4",
            "rng_algorithm": "numpy.random.PCG64",
            "seed_source": "prefrozen_state_manifest_latent_seed",
            "row0": "all_zero",
            "rows1_7_assignment": (
                "rng.standard_normal(latent[1:].shape).astype(float32)"
            ),
            "rows1_7_draw_shape": [7, 321, 81, 4],
            "all_eight_rows_unique_required_before_model": True,
            "broadcast_single_rhs_across_rows1_7_allowed": False,
            "row_permutation_after_freeze_allowed": False,
        },
        "pool_binding_contract": {
            "required_exact_bindings": list(POOL_BINDINGS),
            "same_nonlatent_input_across_expanded_batch_required": True,
            "same_model_checkpoint_and_forward_for_all_rows_required": True,
            "candidate_tensor_frozen_before_selector": True,
            "candidate_tensor_immutable_after_freeze": True,
            "candidate0_rule": "candidate_tensor_row0",
            "candidate0_outcome_selected": False,
            "arms": list(ARMS),
            "all_arms_same_pool_id_and_tensor_sha_required": True,
            "post_pool_required_zero_call_fields": list(
                POST_POOL_ZERO_CALL_FIELDS
            ),
            "static_scene_may_consume_only_frozen_tensor": True,
        },
        "latency_contract": {
            "common_pool_generation_cost_included_for_all_three_arms": True,
            "incremental_stages": ["atoms", "context", "weights", "selector"],
            "end_to_end_formula": (
                "pool_generation_plus_atoms_plus_context_plus_weights_plus_selector"
            ),
            "pool_matched_candidate0_selector_increment": (
                "row0_selection_bookkeeping_only"
            ),
            "operational_batch1_latency_separate_architecture_reference": True,
            "operational_batch1_may_be_called_pool_baseline": False,
        },
        "sequential_legacy_contract": {
            "mode": "sequential_batch1_x8",
            "scope": "legacy_non_gating_diagnostic_reference_only",
            "known_rows1_7_repeated_finding_preserved": True,
            "excluded_from": list(SEQUENTIAL_EXCLUSIONS),
            "contributes_thresholds": False,
            "contributes_denominator": False,
            "may_pass_or_block_primary_generator": False,
            "may_contribute_primary_latency": False,
        },
        "decision_topology": {
            "contract_amendment_only": True,
            "runtime_qualification_status": "not_run_not_authorized",
            "formal_denominator": "not_formed_not_authorized",
            "hard_pass": "not_evaluated_not_authorized",
            "claim_authorized": False,
            "old_artifacts_roots_cas_immutable": True,
            "fixed_dp_model_weights_atoms_changed": False,
        },
        "run_counters": {key: 0 for key in PROHIBITED_RUNS},
        "prohibitions": {
            "batch8_or_sequential_model_diagnostic": True,
            "old_artifact_or_cas_write": True,
            "fixed_dp_model_weights_atoms_change": True,
            "claim_promotion_deployment": True,
        },
    }


def validate_contract_amendment(value: Mapping[str, Any]) -> dict[str, Any]:
    candidate = _object(value, "contract")
    implementation = _object(candidate.get("implementation"), "implementation")
    expected = contract_amendment(
        implementation_head=implementation.get("head"),
        exact_dirs=implementation.get("exact_dirs"),
        source_sha256=implementation.get("source_sha256"),
    )
    if candidate != expected:
        raise ValueError("batch8-primary contract literal drifted")
    authority = json.loads(HIGH_AUTHORITY_JSON)
    if (
        json.dumps(
            authority,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        != HIGH_AUTHORITY_JSON
        or hashlib.sha256(HIGH_AUTHORITY_JSON.encode("ascii")).hexdigest()
        != HIGH_AUTHORITY_SHA256
    ):
        raise ValueError("High authority canonical hash drifted")
    if candidate["run_counters"] != {key: 0 for key in PROHIBITED_RUNS}:
        raise ValueError("forbidden run count drifted")
    return candidate


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _exact_map(
    value: Mapping[str, str],
    keys: tuple[str, ...],
    label: str,
    *,
    sha: bool = False,
) -> dict[str, str]:
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{label} keyset drifted")
    result = {key: value[key] for key in keys}
    for key, item in result.items():
        if type(item) is not str or not item:
            raise ValueError(f"{label}.{key} must be nonempty")
        if sha:
            _sha(item, f"{label}.{key}")
    return result


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 64:
        raise ValueError(f"{label} must be SHA256")
    int(value, 16)
    return value


def _head(value: Any, label: str) -> str:
    if type(value) is not str or len(value) != 40:
        raise ValueError(f"{label} must be a git SHA")
    int(value, 16)
    return value
