"""Independent literal review for the V25 batch8-primary contract.

This module deliberately does not import the producer contract module.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


SCHEMA = (
    "camp_dp_v25_single_invocation_batch8_primary_generator_contract_amendment_v1"
)
AUTHORITY_SHA = (
    "16f63578b401a2bb5079035f3c047874dde6adc35cb162a71ed4d5016f197690"
)
SUPERSEDED_SHA = (
    "f7d90c476de74f0122bce8ffeeab80260d17ad8cd040035ee97c81040e964aef"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_AUDIT_ROOT = (
    "ef7fed1d077aa2edcdfe4114daaf1904b936ead23d713fc4ba96acbcb8cedc3e"
)
SOURCE_AUDIT_REVIEW_ROOT = (
    "bd81175f3088755e41f799854bcc84d09deca8da1e443b1e20ad7cbd3dd09ef6"
)
EXACT_DIR_KEYS = {"contract", "contract_review", "focused", "final_docs_focused"}
SOURCE_KEYS = {"producer", "reviewer", "freeze_script", "review_script", "tests"}
REQUIRED_BINDINGS = [
    "input_id",
    "state_id",
    "model_sha256",
    "checkpoint_sha256",
    "forward_invocation_id",
    "pool_id",
    "candidate_tensor_sha256",
]
SEQUENTIAL_EXCLUSIONS = [
    "formal_denominator",
    "hard_pass",
    "primary_latency",
    "qualification_decision",
]
ZERO_FIELDS = [
    "model_call_count",
    "dp_call_count",
    "latent_generation_count",
    "candidate_generation_count",
]
RUN_KEYS = {
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
}


def independent_literal_review(
    value: Mapping[str, Any],
    *,
    expected_implementation_head: str,
    expected_exact_dirs: Mapping[str, str],
    expected_source_sha256: Mapping[str, str],
) -> dict[str, Any]:
    contract = _object(value, "contract")
    _keys(
        contract,
        {
            "schema_version",
            "status",
            "high_authority",
            "implementation",
            "source_audit_binding",
            "primary_generator_contract",
            "latent_policy_contract",
            "pool_binding_contract",
            "latency_contract",
            "sequential_legacy_contract",
            "decision_topology",
            "run_counters",
            "prohibitions",
        },
        "contract",
    )
    if (
        contract["schema_version"] != SCHEMA
        or contract["status"] != "scientific_contract_review_required"
    ):
        raise ValueError("contract identity drifted")
    authority = _object(contract["high_authority"], "authority")
    authority_json = authority.get("canonical_json_ascii")
    if (
        type(authority_json) is not str
        or hashlib.sha256(authority_json.encode("ascii")).hexdigest()
        != AUTHORITY_SHA
        or authority.get("sha256") != AUTHORITY_SHA
        or authority.get("supersedes_authority_sha256") != SUPERSEDED_SHA
        or authority.get("superseded_authority_model_execution_allowed")
        is not False
    ):
        raise ValueError("authority binding drifted")
    decoded = json.loads(authority_json)
    if (
        decoded.get("primary_generator")
        != "new_single_invocation_batched_k8_candidate_pool"
        or decoded.get("formal_model_invocation_count_per_pool") != 1
        or decoded.get("candidate_axis")
        != "same_ego_expanded_batch_dimension_B_equals_8"
        or decoded.get("sequential_excluded_from") != SEQUENTIAL_EXCLUSIONS
        or decoded.get("superseded_authority_model_execution_allowed") is not False
    ):
        raise ValueError("authority semantic oracle failed")
    implementation = _object(contract["implementation"], "implementation")
    if (
        implementation.get("head") != expected_implementation_head
        or set(implementation.get("exact_dirs", {})) != EXACT_DIR_KEYS
        or implementation.get("exact_dirs") != dict(expected_exact_dirs)
        or set(implementation.get("source_sha256", {})) != SOURCE_KEYS
        or implementation.get("source_sha256") != dict(expected_source_sha256)
    ):
        raise ValueError("implementation binding drifted")
    _git_head(expected_implementation_head)
    for sha in expected_source_sha256.values():
        _sha(sha)
    source = _object(contract["source_audit_binding"], "source audit")
    if source != {
        "root_sha256": SOURCE_AUDIT_ROOT,
        "review_root_sha256": SOURCE_AUDIT_REVIEW_ROOT,
        "resolved_taxonomy": "latent_input_rows_repeated",
        "historical_sequential_finding_mutated": False,
    }:
        raise ValueError("source audit binding drifted")
    primary = _object(contract["primary_generator_contract"], "primary")
    if (
        primary.get("name")
        != "new_single_invocation_batched_k8_candidate_pool"
        or primary.get("formal_model_invocation_count_per_pool") != 1
        or primary.get("candidate_count") != 8
        or primary.get("candidate_axis")
        != "same_ego_expanded_batch_dimension_B_equals_8"
        or primary.get("source_ego_state_count") != 1
        or primary.get("expanded_model_batch_size") != 8
        or primary.get("agent_as_ego_batch") is not False
        or primary.get("native_output_schema_has_independent_K_axis") is not False
        or primary.get("operational_batch_size_1_already_has_k8") is not False
        or primary.get("operational_default_batch_size") != 1
        or primary.get("future_runtime_diagnostic_requires_new_high_authority")
        is not True
    ):
        raise ValueError("primary generator semantic oracle failed")
    latent = _object(contract["latent_policy_contract"], "latent")
    if (
        latent.get("shape") != [8, 321, 81, 4]
        or latent.get("dtype") != "<f4"
        or latent.get("rng_algorithm") != "numpy.random.PCG64"
        or latent.get("row0") != "all_zero"
        or latent.get("rows1_7_assignment")
        != "rng.standard_normal(latent[1:].shape).astype(float32)"
        or latent.get("rows1_7_draw_shape") != [7, 321, 81, 4]
        or latent.get("all_eight_rows_unique_required_before_model") is not True
        or latent.get("broadcast_single_rhs_across_rows1_7_allowed") is not False
        or latent.get("row_permutation_after_freeze_allowed") is not False
    ):
        raise ValueError("latent policy semantic oracle failed")
    pool = _object(contract["pool_binding_contract"], "pool")
    if (
        pool.get("required_exact_bindings") != REQUIRED_BINDINGS
        or pool.get("same_nonlatent_input_across_expanded_batch_required") is not True
        or pool.get("same_model_checkpoint_and_forward_for_all_rows_required")
        is not True
        or pool.get("candidate_tensor_frozen_before_selector") is not True
        or pool.get("candidate_tensor_immutable_after_freeze") is not True
        or pool.get("candidate0_rule") != "candidate_tensor_row0"
        or pool.get("candidate0_outcome_selected") is not False
        or pool.get("arms")
        != ["pool_matched_candidate0", "Static14D", "Scene14D"]
        or pool.get("all_arms_same_pool_id_and_tensor_sha_required") is not True
        or pool.get("post_pool_required_zero_call_fields") != ZERO_FIELDS
        or pool.get("static_scene_may_consume_only_frozen_tensor") is not True
    ):
        raise ValueError("pool/selector semantic oracle failed")
    latency = _object(contract["latency_contract"], "latency")
    if (
        latency.get("common_pool_generation_cost_included_for_all_three_arms")
        is not True
        or latency.get("incremental_stages")
        != ["atoms", "context", "weights", "selector"]
        or latency.get("end_to_end_formula")
        != "pool_generation_plus_atoms_plus_context_plus_weights_plus_selector"
        or latency.get("operational_batch1_latency_separate_architecture_reference")
        is not True
        or latency.get("operational_batch1_may_be_called_pool_baseline") is not False
    ):
        raise ValueError("latency semantic oracle failed")
    sequential = _object(contract["sequential_legacy_contract"], "sequential")
    if (
        sequential.get("mode") != "sequential_batch1_x8"
        or sequential.get("scope") != "legacy_non_gating_diagnostic_reference_only"
        or sequential.get("known_rows1_7_repeated_finding_preserved") is not True
        or sequential.get("excluded_from") != SEQUENTIAL_EXCLUSIONS
        or sequential.get("contributes_thresholds") is not False
        or sequential.get("contributes_denominator") is not False
        or sequential.get("may_pass_or_block_primary_generator") is not False
        or sequential.get("may_contribute_primary_latency") is not False
    ):
        raise ValueError("sequential exclusion semantic oracle failed")
    decision = _object(contract["decision_topology"], "decision")
    if (
        decision.get("contract_amendment_only") is not True
        or decision.get("runtime_qualification_status") != "not_run_not_authorized"
        or decision.get("formal_denominator") != "not_formed_not_authorized"
        or decision.get("hard_pass") != "not_evaluated_not_authorized"
        or decision.get("claim_authorized") is not False
        or decision.get("old_artifacts_roots_cas_immutable") is not True
        or decision.get("fixed_dp_model_weights_atoms_changed") is not False
    ):
        raise ValueError("decision topology semantic oracle failed")
    counters = _object(contract["run_counters"], "run counters")
    if set(counters) != RUN_KEYS or any(counters[key] != 0 for key in RUN_KEYS):
        raise ValueError("forbidden run counter drifted")
    prohibitions = _object(contract["prohibitions"], "prohibitions")
    if set(prohibitions.values()) != {True}:
        raise ValueError("prohibition drifted")
    return {
        "schema_version": (
            "camp_dp_v25_single_invocation_batch8_primary_generator_contract_"
            "independent_review_v1"
        ),
        "status": "passed_independent_literal_contract_review",
        "candidate_axis_rebuilt": True,
        "single_invocation_topology_rebuilt": True,
        "latent_uniqueness_policy_rebuilt": True,
        "pool_selector_bindings_rebuilt": True,
        "sequential_exclusion_rebuilt": True,
        "latency_accounting_rebuilt": True,
        "run_count_verified_zero": True,
        "claim_authorized": False,
        "producer_oracle_imported": False,
    }


def _object(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain object")
    return dict(value)


def _keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} keyset drifted")


def _sha(value: Any) -> None:
    if type(value) is not str or len(value) != 64:
        raise ValueError("invalid SHA256")
    int(value, 16)


def _git_head(value: Any) -> None:
    if type(value) is not str or len(value) != 40:
        raise ValueError("invalid git HEAD")
    int(value, 16)
