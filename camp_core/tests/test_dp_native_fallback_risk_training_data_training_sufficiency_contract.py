from __future__ import annotations

from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_TESTS_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_training_sufficiency_unit_tests.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


VALIDATED_DATASET_SHA = "16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36"
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


def _errors_for(payload: dict[str, Any]) -> list[str]:
    return validate_training_sufficiency_preconditions(payload)["errors"]


def test_current_head_bcd85c2_unit_tests_revalidation_is_pinned() -> None:
    doc = UNIT_TESTS_DOC.read_text(encoding="utf-8")
    iteration_tail = ITERATION_AUDIT.read_text(encoding="utf-8")[-24000:]
    combined = doc + iteration_tail
    status = "status=fallback_risk_training_data_training_sufficiency_unit_tests_current_head_bcd85c2_revalidated"

    assert status in iteration_tail

    for needle in [
        status,
        "unit_tests_validation_base_head=bcd85c2c43febd1480b610e05f8c3dccb533304a",
        "camp_origin_main_at_validation=bcd85c2c43febd1480b610e05f8c3dccb533304a",
        "github_refs_heads_main_at_validation=bcd85c2c43febd1480b610e05f8c3dccb533304a",
        "autodl_CAMP_HEAD_at_validation=bcd85c2c43febd1480b610e05f8c3dccb533304a",
        "autodl_CAMP_origin_main_at_validation=bcd85c2c43febd1480b610e05f8c3dccb533304a",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "training_sufficiency_unit_tests_plan_status=fallback_risk_training_data_training_sufficiency_unit_tests_plan_current_head_e6c79f8_revalidated",
        "validated_fallback_records=15",
        "validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "validator_output_json_sha256=d719e3b01d17be91ab68ba42cc9349400cc73fa9624fb7fdff0e539fcb6344e2",
        "validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "strict_formal_seed_path_matches=0",
        "contract_test=camp_core/tests/test_dp_native_fallback_risk_training_data_training_sufficiency_contract.py",
        "validated_dataset_required=True",
        "15_record_artifact_does_not_authorize_training=True",
        "training_sufficiency_claim_without_split_rejected=True",
        "deployable_checkpoint_claim_rejected=True",
        "training_validation_split_manifest_required=True",
        "group_key_source_log_run_id_record_index_required=True",
        "train_validation_group_overlap_rejected=True",
        "formal_seeds_11_12_13_rejected=True",
        "formal_eval_artifact_in_development_split_rejected=True",
        "train_only_scale_manifest_required=True",
        "scale_fit_validation_groups_rejected=True",
        "scale_fit_formal_or_eval_groups_rejected=True",
        "nonpositive_nonfinite_or_non_numeric_atom_scales_rejected=True",
        "atom_schema_or_names_mismatch_rejected=True",
        "fallback_only_master_config_required=True",
        "feasible_branch_records_in_fallback_master_rejected=True",
        "all_infeasible_records_added_to_feasible_training_rejected=True",
        "all_infeasible_records_relabelled_feasible_rejected=True",
        "hard_feasibility_relaxation_rejected=True",
        "feasible_ranking_master_change_rejected=True",
        "score_equals_a_transpose_w_required=True",
        "nonnegative_fixed_atoms_required=True",
        "fallback_label_not_deployed_atom_required=True",
        "nonnegative_margins_required=True",
        "simplex_cvar_l2_convex_boundary_required=True",
        "training_command_without_prior_authorization_rejected=True",
        "replay_or_candidate_generation_commands_rejected=True",
        "dp_weight_or_config_changes_rejected=True",
        "reference_blend_guidance_or_postselection_rejected=True",
        "online_selector_or_atom_promotion_rejected=True",
        "post_training_nonpromotion_plan_required=True",
        "development_holdout_acceptance_gate_required=True",
        "local_py_compile_exit=0",
        "local_target_pytest=19 passed",
        "local_target_pytest_exit=0",
        "local_training_group_pytest=42 passed",
        "local_git_diff_check_exit=0",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_unit_tests_bcd85c2_verify_20260626T165809Z",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=19 passed",
        "autodl_training_group_pytest=42 passed",
        "autodl_git_diff_check_exit=0",
        "training_sufficiency_unit_tests_complete=True",
        "training_sufficiency_preflight_implementation_authorization_gate_authorized_next=True",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "training_authorized=False",
        "camp_training_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_implementation_authorization_only",
    ]:
        assert needle in combined


def test_current_head_0506f8c_unit_tests_revalidation_is_pinned() -> None:
    doc = UNIT_TESTS_DOC.read_text(encoding="utf-8")
    iteration_tail = ITERATION_AUDIT.read_text(encoding="utf-8")[-16000:]
    combined = doc + iteration_tail

    assert VALIDATED_DATASET_SHA == (
        "16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36"
    )

    for needle in [
        "status=fallback_risk_training_data_training_sufficiency_unit_tests_current_head_0506f8c_revalidated",
        "unit_tests_validation_base_head=0506f8c6e8b884ab8557917e35dd20b8cbd1c7a3",
        "training_sufficiency_unit_tests_plan_status=fallback_risk_training_data_training_sufficiency_unit_tests_plan_current_head_7ebc103_tail_counts_revalidated",
        "validated_fallback_records=15",
        "validated_fallback_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "validator_output_json_sha256=f8a26e357020022779dc9eb40992b3d1107521e0abd345cd9f498ea988c95114",
        "validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "strict_formal_seed_path_matches=0",
        "contract_test=camp_core/tests/test_dp_native_fallback_risk_training_data_training_sufficiency_contract.py",
        "local_target_pytest=18 passed",
        "local_training_group_pytest=39 passed",
        "local_cumulative_pytest=227 passed",
        "autodl_target_pytest=18 passed",
        "autodl_training_group_pytest=39 passed",
        "autodl_cumulative_pytest=227 passed",
        "training_sufficiency_unit_tests_complete=True",
        "training_sufficiency_preflight_implementation_authorization_gate_authorized_next=True",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_implementation_authorization_only",
    ]:
        assert needle in combined


def test_clean_synthetic_preconditions_pass_without_training_authorization() -> None:
    report = validate_training_sufficiency_preconditions(_clean_payload())

    assert report["passed"] is True
    assert report["ready_for_future_training_authorization"] is True
    assert report["training_authorized"] is False
    assert report["fallback_dataset_training_sufficiency_claim"] is False
    assert report["camp_retraining_authorized_now"] is False


def test_rejects_missing_precondition_inputs() -> None:
    errors = _errors_for({})

    assert "validated_dataset_missing" in errors
    assert "split_manifest_missing" in errors
    assert "scale_manifest_missing" in errors
    assert "fallback_master_config_missing" in errors
    assert "training_command_plan_missing" in errors


def test_rejects_dataset_sufficiency_and_checkpoint_claim_leaks() -> None:
    payload = _clean_payload()
    payload["validated_dataset"]["records"] = 0
    payload["validated_dataset"]["training_sufficiency_claim"] = True
    payload["validated_dataset"]["deployable_checkpoint_claim"] = True

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "validated_fallback_record_count_mismatch" in errors
    assert "training_sufficiency_claim_leak" in errors
    assert "deployable_checkpoint_claim_leak" in errors


def test_rejects_dataset_sha_validator_status_and_failed_validation() -> None:
    payload = _clean_payload()
    payload["validated_dataset"]["sha256"] = "wrong"
    payload["validated_dataset"]["validator_status"] = "incomplete"
    payload["validated_dataset"]["validator_passed"] = False

    errors = _errors_for(payload)

    assert "validated_dataset_sha_mismatch" in errors
    assert "validator_status_not_complete" in errors
    assert "validator_not_passed" in errors


def test_rejects_missing_or_invalid_split_group_key() -> None:
    payload = _clean_payload()
    payload["split_manifest"]["group_key_fields"] = ["source_log", "record_index"]

    errors = _errors_for(payload)

    assert "split_group_key_invalid" in errors


def test_rejects_empty_training_or_validation_groups() -> None:
    payload = _clean_payload()
    payload["split_manifest"]["training_groups"] = []
    payload["split_manifest"]["validation_groups"] = []

    errors = _errors_for(payload)

    assert "split_train_or_validation_empty" in errors


def test_rejects_split_overlap_formal_seed_and_formal_eval_leakage() -> None:
    payload = _clean_payload()
    payload["split_manifest"]["training_groups"].append("log_b:run_1:0")
    payload["split_manifest"]["seeds"] = [11, 21]
    payload["split_manifest"]["formal_eval_artifact_included"] = True

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "split_train_validation_overlap" in errors
    assert "formal_seed_in_development_split" in errors
    assert "formal_eval_artifact_in_development_split" in errors


def test_rejects_scale_manifest_without_split_manifest() -> None:
    payload = _clean_payload()
    del payload["split_manifest"]

    errors = _errors_for(payload)

    assert "split_manifest_missing" in errors
    assert "scale_manifest_without_split" in errors


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


def test_rejects_scale_atom_name_and_key_mismatch() -> None:
    payload = _clean_payload()
    payload["scale_manifest"]["atom_names"] = list(APPROVED_ATOMS[:-1])
    payload["scale_manifest"]["atom_scales"].pop("jerk_late")

    errors = _errors_for(payload)

    assert "scale_atom_names_mismatch" in errors
    assert "atom_scale_keys_mismatch" in errors


def test_rejects_non_numeric_boolean_and_negative_atom_scales() -> None:
    payload = _clean_payload()
    payload["scale_manifest"]["atom_scales"]["jerk_early"] = True
    payload["scale_manifest"]["atom_scales"]["jerk_late"] = "bad"
    payload["scale_manifest"]["atom_scales"]["jerk_full"] = -1.0

    errors = _errors_for(payload)

    assert "atom_scale_jerk_early_not_strictly_positive" in errors
    assert "atom_scale_jerk_late_not_strictly_positive" in errors
    assert "atom_scale_jerk_full_not_strictly_positive" in errors


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


def test_rejects_fallback_master_relabelling_and_feasible_master_changes() -> None:
    payload = _clean_payload()
    master = payload["fallback_master_config"]
    master["all_infeasible_records_relabelled_feasible"] = True
    master["feasible_ranking_master_change_authorized"] = True

    errors = _errors_for(payload)

    assert "all_infeasible_records_relabelled_feasible_leak" in errors
    assert "feasible_ranking_master_change_authorized_leak" in errors


def test_rejects_nonnegative_margin_and_convex_boundary_breaks() -> None:
    payload = _clean_payload()
    master = payload["fallback_master_config"]
    master["atoms_fixed_nonnegative"] = False
    master["margins_nonnegative"] = False
    master["simplex_cvar_l2_convex"] = False

    errors = _errors_for(payload)

    assert "atoms_not_fixed_nonnegative" in errors
    assert "margins_not_nonnegative" in errors
    assert "convex_master_boundary_missing" in errors


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


def test_rejects_all_forbidden_command_flags() -> None:
    payload = _clean_payload()
    command = payload["training_command_plan"]
    for flag in FORBIDDEN_COMMAND_FLAGS:
        command[flag] = True

    errors = _errors_for(payload)

    for flag in FORBIDDEN_COMMAND_FLAGS:
        assert f"{flag}_leak" in errors


def test_rejects_missing_post_training_nonpromotion_and_holdout_gates() -> None:
    payload = _clean_payload()
    payload["training_command_plan"]["post_training_nonpromotion_plan_required"] = False
    payload["training_command_plan"]["development_holdout_acceptance_gate_required"] = False

    errors = validate_training_sufficiency_preconditions(payload)["errors"]

    assert "post_training_nonpromotion_plan_missing" in errors
    assert "development_holdout_acceptance_gate_missing" in errors
