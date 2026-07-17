from __future__ import annotations

import copy

import pytest

from camp_core.integrations.diffusion_planner_v25_full_r_authority import (
    CRITICAL_IMPLEMENTATION_PATHS,
)
from scripts.integrations import (
    review_diffusion_planner_v25_controlled_training_corpus as corpus_reviewer,
    review_diffusion_planner_v25_full_config_preflight as full_config_reviewer,
)


def _receipt() -> dict[str, object]:
    authority: dict[str, object] = {
        "schema_version": "camp_dp_v25_full_config_receipt_v1",
        "scenario_id": "a" * 64,
        "family": "lead_vehicle_hard_brake",
        "tier": "easy",
        "route_identity_sha256": "b" * 64,
        "canonical_semantic_clone_sha256": "c" * 64,
        "signal_source_chain_sha256": None,
        "map_sha256": "d" * 64,
        "route_sha256": "e" * 64,
        "fixed_dp_head": full_config_reviewer.FIXED_DP_HEAD,
        "fixed_dp_checkpoint_sha256": "f" * 64,
        "fixed_dp_args_sha256": "1" * 64,
        "generation_scales_sha256": "2" * 64,
        "static_weights_sha256": "3" * 64,
        "selector_role": "static14d",
        "seed": full_config_reviewer.EXPECTED_SEED,
        "corpus_steps": full_config_reviewer.CORPUS_STEPS,
        "context_schema_version": "camp_dp_v25_causal_context_raw_v2",
        "context_mode": "no_v2i",
        "selector_training_execution_authorized": False,
        "calibration_authorized": False,
        "holdout_access_authorized": False,
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
    }
    return {
        **authority,
        "config_authority_sha256": full_config_reviewer._oracle_sha256(authority),
    }


def _snapshot() -> dict[str, object]:
    sha = "a" * 64
    return {
        "schema_version": "camp_dp_v25_controlled_train_snapshot_v4",
        "feature_payload": {
            "atom_matrix": [],
            "source_valid_mask": [True] * 8,
            "atom_source_valid_mask": [],
            "atom_applicable_mask": [],
            "physical_feasible_mask": [True] * 8,
            "candidate_row_sha256": [sha] * 8,
            "candidate_tensor": [],
            "default_output": [],
            "raw_context": {},
            "context_source_complete": {},
        },
        "sidecar": {
            "tick_index": 0,
            "dt_s": 0.1,
            "scenario_id": sha,
            "family": "lead_vehicle_hard_brake",
            "tier": "easy",
            "parameter_block_id": "block",
            "route_identity_sha256": sha,
            "corridor_group_sha256": sha,
            "map_family_id": "map-family",
            "seed": 25001,
            "candidate_tensor_sha256_before": sha,
            "candidate_tensor_sha256_after": sha,
            "default_output_sha256": sha,
            "candidate0_sha256": sha,
            "default_candidate0_identity": {
                "elementwise_equal": True,
                "default_output_sha256": sha,
                "candidate0_sha256": sha,
                "native_ranked_k8": False,
            },
            "candidate0_semantics": "operational_default_alias_from_same_forward",
            "candidate0_independent_second_forward": False,
            "causal_input_sha256": sha,
            "physical_feasible_mask": [True] * 8,
            "source_valid_mask": [True] * 8,
            "all_k_high_risk": False,
            "selected_index": 0,
            "selected_trajectory_sha256": sha,
            "score_contract": "score_k=clip(a_k/s,0,10)^T w",
            "tie_break_contract": "lowest_eligible_candidate_index",
            "normalized_atom_matrix_sha256": sha,
            "context_schema_version": "camp_dp_v25_causal_context_raw_v2",
            "context_source_receipt": {"mode": "no_v2i"},
            "generation_behavior_scale_sha256": sha,
            "canonical_semantic_clone_sha256": None,
            "controlled_signal_source_receipt": None,
            "causal_signal_atom_input": None,
            "offline_label_provenance": "pending_train_only_causal_label",
            "outcome_fields_consumed": [],
            "fresh_b_opened": False,
        },
    }


def test_full_config_receipts_are_type_exact_and_bind_actual_root_and_row_sha() -> None:
    expected = [_receipt()]
    root = full_config_reviewer._oracle_sha256(expected)
    full_config_reviewer._validate_config_receipts(expected, expected, root)

    mutations = []
    for field, value in (
        ("selector_training_execution_authorized", 0),
        ("seed", 25001.0),
        ("corpus_steps", 64.0),
    ):
        changed = copy.deepcopy(expected)
        changed[0][field] = value
        mutations.append(changed)
    fake_row_sha = copy.deepcopy(expected)
    fake_row_sha[0]["config_authority_sha256"] = "0" * 64
    mutations.append(fake_row_sha)

    for actual in mutations:
        with pytest.raises(ValueError):
            full_config_reviewer._validate_config_receipts(actual, expected, root)

    resigned_type_drift = copy.deepcopy(expected)
    resigned_type_drift[0]["seed"] = 25001.0
    resigned_authority = dict(resigned_type_drift[0])
    resigned_authority.pop("config_authority_sha256")
    resigned_type_drift[0]["config_authority_sha256"] = (
        full_config_reviewer._oracle_sha256(resigned_authority)
    )
    with pytest.raises(ValueError):
        full_config_reviewer._validate_config_receipts(
            resigned_type_drift,
            expected,
            full_config_reviewer._oracle_sha256(resigned_type_drift),
        )
    with pytest.raises(ValueError):
        full_config_reviewer._validate_config_receipts(expected, expected, "0" * 64)


def test_full_config_integer_and_boolean_authority_rejects_numeric_subtypes() -> None:
    assert full_config_reviewer._require_json_int(25001, "seed") == 25001
    assert full_config_reviewer._require_json_bool(False, "gate") is False
    for value in (25001.0, True):
        with pytest.raises(ValueError):
            full_config_reviewer._require_json_int(value, "seed")
    for value in (0, 0.0):
        with pytest.raises(ValueError):
            full_config_reviewer._require_json_bool(value, "gate")
    assert not full_config_reviewer._strict_json_equal(
        {"seed": 25001, "count": 1500, "gate": False},
        {"seed": 25001.0, "count": 1500.0, "gate": 0},
    )
    assert not full_config_reviewer._strict_json_equal([25001.0], [25001])


def test_snapshot_and_index_schema_reject_extra_future_delete_and_type_drift() -> None:
    snapshot = _snapshot()
    corpus_reviewer._validate_snapshot_field_schema(snapshot)
    corpus_reviewer._validate_snapshot_index_row(
        {
            "scenario_id": "a" * 64,
            "tick_index": 0,
            "relative_path": "snapshots/" + "b" * 64 + ".json",
            "sha256": "b" * 64,
        }
    )

    mutations = []
    extra_top = copy.deepcopy(snapshot)
    extra_top["future_outcome"] = 1
    mutations.append(extra_top)
    extra_feature = copy.deepcopy(snapshot)
    extra_feature["feature_payload"]["holdout_label"] = 1
    mutations.append(extra_feature)
    extra_nested = copy.deepcopy(snapshot)
    extra_nested["sidecar"]["context_source_receipt"]["id_proxy"] = "leak"
    mutations.append(extra_nested)
    deleted = copy.deepcopy(snapshot)
    del deleted["sidecar"]["fresh_b_opened"]
    mutations.append(deleted)
    seed_float = copy.deepcopy(snapshot)
    seed_float["sidecar"]["seed"] = 25001.0
    mutations.append(seed_float)
    fresh_int = copy.deepcopy(snapshot)
    fresh_int["sidecar"]["fresh_b_opened"] = 0
    mutations.append(fresh_int)
    misnamed_hash = copy.deepcopy(snapshot)
    misnamed_hash["feature_payload"]["candidate_rows_sha256"] = (
        misnamed_hash["feature_payload"].pop("candidate_row_sha256")
    )
    mutations.append(misnamed_hash)
    selected_bool = copy.deepcopy(snapshot)
    selected_bool["sidecar"]["selected_index"] = False
    mutations.append(selected_bool)

    for changed in mutations:
        with pytest.raises(ValueError):
            corpus_reviewer._validate_snapshot_field_schema(changed)

    for field, value in (("tick_index", 0.0), ("scenario_id", 1)):
        row = {
            "scenario_id": "a" * 64,
            "tick_index": 0,
            "relative_path": "snapshots/" + "b" * 64 + ".json",
            "sha256": "b" * 64,
        }
        row[field] = value
        with pytest.raises(ValueError):
            corpus_reviewer._validate_snapshot_index_row(row)


def test_final_corpus_reviewer_is_in_critical_implementation_manifest() -> None:
    assert (
        "scripts/integrations/review_diffusion_planner_v25_controlled_training_corpus.py"
        in CRITICAL_IMPLEMENTATION_PATHS
    )
