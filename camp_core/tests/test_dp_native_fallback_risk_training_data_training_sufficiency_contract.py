from __future__ import annotations

from typing import Any


VALIDATED_DATASET_SHA = "9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018"
APPROVED_SCHEMA = "dp_camp_v10_14d"
APPROVED_ATOMS = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
FORMAL_SEEDS = {11, 12, 13}

FORBIDDEN_COMMAND_FLAGS = (
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "camp_training_authorized",
    "camp_retraining_authorized",
    "Full36_authorized",
    "dp_modification_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_postselection_authorized",
    "closed_loop_outcome_online_input_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "production_selector_change_authorized",
    "online_selector_change_authorized",
)


def _decision(errors: list[str]) -> dict[str, Any]:
    return {
        "passed": not errors,
        "errors": sorted(set(errors)),
        "ready_for_future_training_authorization": not errors,
        "training_authorized": False,
        "fallback_dataset_training_sufficiency_claim": False,
        "camp_retraining_authorized_now": False,
    }


def validate_training_sufficiency_preconditions(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    _validate_dataset(payload.get("validated_dataset"), errors)
    _validate_split(payload.get("split_manifest"), errors)
    _validate_scales(payload.get("scale_manifest"), payload.get("split_manifest"), errors)
    _validate_master(payload.get("fallback_master_config"), errors)
    _validate_command_plan(payload.get("training_command_plan"), errors)
    return _decision(errors)


def _validate_dataset(dataset: Any, errors: list[str]) -> None:
    if not isinstance(dataset, dict):
        errors.append("validated_dataset_missing")
        return
    if dataset.get("sha256") != VALIDATED_DATASET_SHA:
        errors.append("validated_dataset_sha_mismatch")
    if dataset.get("records") != 15:
        errors.append("validated_fallback_record_count_mismatch")
    if dataset.get("validator_status") != "dp_native_fallback_risk_training_data_validator_complete":
        errors.append("validator_status_not_complete")
    if dataset.get("validator_passed") is not True:
        errors.append("validator_not_passed")
    if dataset.get("training_sufficiency_claim") is not False:
        errors.append("training_sufficiency_claim_leak")
    if dataset.get("deployable_checkpoint_claim") is not False:
        errors.append("deployable_checkpoint_claim_leak")


def _validate_split(split: Any, errors: list[str]) -> None:
    if not isinstance(split, dict):
        errors.append("split_manifest_missing")
        return
    if tuple(split.get("group_key_fields") or ()) != ("source_log", "run_id", "record_index"):
        errors.append("split_group_key_invalid")
    train = set(split.get("training_groups") or ())
    validation = set(split.get("validation_groups") or ())
    if not train or not validation:
        errors.append("split_train_or_validation_empty")
    if train & validation:
        errors.append("split_train_validation_overlap")
    seeds = set(split.get("seeds") or ())
    if seeds & FORMAL_SEEDS:
        errors.append("formal_seed_in_development_split")
    if split.get("formal_eval_artifact_included") is not False:
        errors.append("formal_eval_artifact_in_development_split")


def _validate_scales(scales: Any, split: Any, errors: list[str]) -> None:
    if not isinstance(scales, dict):
        errors.append("scale_manifest_missing")
        return
    if not isinstance(split, dict):
        errors.append("scale_manifest_without_split")
        return
    fit_groups = set(scales.get("fit_groups") or ())
    train = set(split.get("training_groups") or ())
    validation = set(split.get("validation_groups") or ())
    if fit_groups != train:
        errors.append("scale_fit_groups_not_training_only")
    if fit_groups & validation:
        errors.append("scale_fit_validation_leak")
    if set(scales.get("fit_seeds") or ()) & FORMAL_SEEDS:
        errors.append("scale_fit_formal_seed_leak")
    if scales.get("formal_eval_artifact_included") is not False:
        errors.append("scale_fit_formal_eval_leak")
    if scales.get("atom_schema_version") != APPROVED_SCHEMA:
        errors.append("scale_atom_schema_mismatch")
    if tuple(scales.get("atom_names") or ()) != APPROVED_ATOMS:
        errors.append("scale_atom_names_mismatch")
    values = scales.get("atom_scales")
    if not isinstance(values, dict) or set(values) != set(APPROVED_ATOMS):
        errors.append("atom_scale_keys_mismatch")
        return
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"atom_scale_{name}_not_strictly_positive")


def _validate_master(master: Any, errors: list[str]) -> None:
    if not isinstance(master, dict):
        errors.append("fallback_master_config_missing")
        return
    expected_false = (
        "feasible_branch_records_allowed",
        "all_infeasible_records_added_to_feasible_training",
        "all_infeasible_records_relabelled_feasible",
        "hard_feasibility_relaxation_authorized",
        "feasible_ranking_master_change_authorized",
    )
    if master.get("fallback_only") is not True:
        errors.append("fallback_master_not_isolated")
    for flag in expected_false:
        if master.get(flag) is not False:
            errors.append(f"{flag}_leak")
    if master.get("score_expression") != "score_k(w)=a_k^T w":
        errors.append("score_expression_not_affine")
    if master.get("atoms_fixed_nonnegative") is not True:
        errors.append("atoms_not_fixed_nonnegative")
    if master.get("fallback_label_is_deployed_atom") is not False:
        errors.append("fallback_label_promoted_to_atom")
    if master.get("margins_nonnegative") is not True:
        errors.append("margins_not_nonnegative")
    if master.get("simplex_cvar_l2_convex") is not True:
        errors.append("convex_master_boundary_missing")


def _validate_command_plan(command: Any, errors: list[str]) -> None:
    if not isinstance(command, dict):
        errors.append("training_command_plan_missing")
        return
    if command.get("training_command_authorization") is not False:
        errors.append("training_command_authorization_leak")
    for flag in FORBIDDEN_COMMAND_FLAGS:
        if command.get(flag) is not False:
            errors.append(f"{flag}_leak")
    if command.get("post_training_nonpromotion_plan_required") is not True:
        errors.append("post_training_nonpromotion_plan_missing")
    if command.get("development_holdout_acceptance_gate_required") is not True:
        errors.append("development_holdout_acceptance_gate_missing")


def _clean_payload() -> dict[str, Any]:
    return {
        "validated_dataset": {
            "sha256": VALIDATED_DATASET_SHA,
            "records": 15,
            "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
            "validator_passed": True,
            "training_sufficiency_claim": False,
            "deployable_checkpoint_claim": False,
        },
        "split_manifest": {
            "group_key_fields": ["source_log", "run_id", "record_index"],
            "training_groups": ["log_a:run_0:0", "log_a:run_0:1"],
            "validation_groups": ["log_b:run_1:0"],
            "seeds": [21, 22],
            "formal_eval_artifact_included": False,
        },
        "scale_manifest": {
            "fit_groups": ["log_a:run_0:0", "log_a:run_0:1"],
            "fit_seeds": [21, 22],
            "formal_eval_artifact_included": False,
            "atom_schema_version": APPROVED_SCHEMA,
            "atom_names": list(APPROVED_ATOMS),
            "atom_scales": {name: 1.0 for name in APPROVED_ATOMS},
        },
        "fallback_master_config": {
            "fallback_only": True,
            "feasible_branch_records_allowed": False,
            "all_infeasible_records_added_to_feasible_training": False,
            "all_infeasible_records_relabelled_feasible": False,
            "hard_feasibility_relaxation_authorized": False,
            "feasible_ranking_master_change_authorized": False,
            "score_expression": "score_k(w)=a_k^T w",
            "atoms_fixed_nonnegative": True,
            "fallback_label_is_deployed_atom": False,
            "margins_nonnegative": True,
            "simplex_cvar_l2_convex": True,
        },
        "training_command_plan": {
            "training_command_authorization": False,
            "post_training_nonpromotion_plan_required": True,
            "development_holdout_acceptance_gate_required": True,
            **{flag: False for flag in FORBIDDEN_COMMAND_FLAGS},
        },
    }


def test_clean_synthetic_preconditions_pass_without_training_authorization() -> None:
    report = validate_training_sufficiency_preconditions(_clean_payload())

    assert report["passed"] is True
    assert report["ready_for_future_training_authorization"] is True
    assert report["training_authorized"] is False
    assert report["fallback_dataset_training_sufficiency_claim"] is False
    assert report["camp_retraining_authorized_now"] is False


def test_rejects_dataset_sufficiency_and_checkpoint_claim_leaks() -> None:
    payload = _clean_payload()
    payload["validated_dataset"]["records"] = 0
    payload["validated_dataset"]["training_sufficiency_claim"] = True
    payload["validated_dataset"]["deployable_checkpoint_claim"] = True

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "validated_fallback_record_count_mismatch" in errors
    assert "training_sufficiency_claim_leak" in errors
    assert "deployable_checkpoint_claim_leak" in errors


def test_rejects_split_overlap_formal_seed_and_formal_eval_leakage() -> None:
    payload = _clean_payload()
    payload["split_manifest"]["training_groups"].append("log_b:run_1:0")
    payload["split_manifest"]["seeds"] = [11, 21]
    payload["split_manifest"]["formal_eval_artifact_included"] = True

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "split_train_validation_overlap" in errors
    assert "formal_seed_in_development_split" in errors
    assert "formal_eval_artifact_in_development_split" in errors


def test_rejects_scale_fit_leakage_and_bad_atom_scale_contract() -> None:
    payload = _clean_payload()
    payload["scale_manifest"]["fit_groups"] = ["log_a:run_0:0", "log_b:run_1:0"]
    payload["scale_manifest"]["fit_seeds"] = [12]
    payload["scale_manifest"]["formal_eval_artifact_included"] = True
    payload["scale_manifest"]["atom_schema_version"] = "wrong"
    payload["scale_manifest"]["atom_scales"]["jerk_early"] = 0.0

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "scale_fit_groups_not_training_only" in errors
    assert "scale_fit_validation_leak" in errors
    assert "scale_fit_formal_seed_leak" in errors
    assert "scale_fit_formal_eval_leak" in errors
    assert "scale_atom_schema_mismatch" in errors
    assert "atom_scale_jerk_early_not_strictly_positive" in errors


def test_rejects_fallback_master_leaking_into_feasible_master() -> None:
    payload = _clean_payload()
    master = payload["fallback_master_config"]
    master["fallback_only"] = False
    master["feasible_branch_records_allowed"] = True
    master["all_infeasible_records_added_to_feasible_training"] = True
    master["hard_feasibility_relaxation_authorized"] = True
    master["score_expression"] = "score_k(w)=a_k^T w + selected_index"
    master["fallback_label_is_deployed_atom"] = True

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "fallback_master_not_isolated" in errors
    assert "feasible_branch_records_allowed_leak" in errors
    assert "all_infeasible_records_added_to_feasible_training_leak" in errors
    assert "hard_feasibility_relaxation_authorized_leak" in errors
    assert "score_expression_not_affine" in errors
    assert "fallback_label_promoted_to_atom" in errors


def test_rejects_training_command_execution_dp_changes_and_promotions() -> None:
    payload = _clean_payload()
    command = payload["training_command_plan"]
    command["training_command_authorization"] = True
    command["camp_training_authorized"] = True
    command["replay_execution_authorized"] = True
    command["candidate_generation_authorized"] = True
    command["dp_modification_authorized"] = True
    command["reference_blend_authorized"] = True
    command["guidance_authorized"] = True
    command["selector_promotion_authorized"] = True
    command["atom_promotion_authorized"] = True
    command["safety_benefit_claim_authorized"] = True
    command["camp_over_dp_top1_claim_authorized"] = True

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    for needle in [
        "training_command_authorization_leak",
        "camp_training_authorized_leak",
        "replay_execution_authorized_leak",
        "candidate_generation_authorized_leak",
        "dp_modification_authorized_leak",
        "reference_blend_authorized_leak",
        "guidance_authorized_leak",
        "selector_promotion_authorized_leak",
        "atom_promotion_authorized_leak",
        "safety_benefit_claim_authorized_leak",
        "camp_over_dp_top1_claim_authorized_leak",
    ]:
        assert needle in errors


def test_rejects_missing_post_training_nonpromotion_and_holdout_gates() -> None:
    payload = _clean_payload()
    payload["training_command_plan"]["post_training_nonpromotion_plan_required"] = False
    payload["training_command_plan"]["development_holdout_acceptance_gate_required"] = False

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "post_training_nonpromotion_plan_missing" in errors
    assert "development_holdout_acceptance_gate_missing" in errors
