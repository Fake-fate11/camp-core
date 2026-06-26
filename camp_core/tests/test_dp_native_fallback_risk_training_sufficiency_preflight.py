from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
IMPL_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_implementation.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    COMPLETE_STATUS,
    DISABLED_STATUS,
    EXPECTED_VALIDATED_DATASET_SHA256,
    REJECT_STATUS,
    main,
    validate_training_sufficiency_preflight,
)


VALIDATED_DATASET_SHA = EXPECTED_VALIDATED_DATASET_SHA256
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


def test_preflight_dataset_sha_pin_matches_current_fixed_artifact() -> None:
    assert (
        VALIDATED_DATASET_SHA
        == "16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36"
    )


def test_current_head_8d867cc_preflight_implementation_revalidation_is_pinned() -> None:
    doc = IMPL_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    combined = doc + audit
    status = "status=fallback_risk_training_sufficiency_preflight_implementation_head_8d867cc_revalidated"

    assert status in audit

    for needle in [
        status,
        "implementation_base_head=8d867cc5acb9e5ddbe24bcb545b48d931fed9afe",
        "camp_origin_main_at_implementation=8d867cc5acb9e5ddbe24bcb545b48d931fed9afe",
        "github_refs_heads_main_at_implementation=8d867cc5acb9e5ddbe24bcb545b48d931fed9afe",
        "autodl_CAMP_HEAD_at_implementation=8d867cc5acb9e5ddbe24bcb545b48d931fed9afe",
        "autodl_CAMP_origin_main_at_implementation=8d867cc5acb9e5ddbe24bcb545b48d931fed9afe",
        "autodl_DP_HEAD_at_implementation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_authorization_status=fallback_risk_training_sufficiency_preflight_implementation_authorization_head_bc3af24_revalidated",
        "validated_fallback_records=15",
        "expected_validated_dataset_sha_already_current=True",
        "expected_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "validator_output_json_sha256=d719e3b01d17be91ab68ba42cc9349400cc73fa9624fb7fdff0e539fcb6344e2",
        "validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "strict_formal_seed_path_matches=0",
        "implementation_file=scripts/integrations/validate_dp_native_fallback_risk_training_sufficiency_preflight.py",
        "production_preflight_script_modified_in_this_gate=False",
        "implementation_scope=current_default_off_read_only_preflight_revalidation",
        "preflight_default_off=True",
        "preflight_read_only=True",
        "manifest_inputs_only=True",
        "disabled_mode_returns_before_manifest_read=True",
        "writes_only_explicit_output_json_and_output_md=True",
        "subprocess_usage_introduced=False",
        "training_execution_path_introduced=False",
        "diffusion_planner_execution_path_introduced=False",
        "candidate_generation_path_introduced=False",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "local_preflight_pytest=8 passed",
        "local_authorization_pytest=9 passed",
        "local_training_sufficiency_contract_pytest=19 passed",
        "local_unit_tests_plan_pytest=8 passed",
        "local_target_pytest=44 passed",
        "local_py_compile_exit=0",
        "local_git_diff_check_exit=0",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_preflight_impl_8d867cc_verify_20260626T171059Z",
        "autodl_py_compile_exit=0",
        "autodl_preflight_pytest=8 passed",
        "autodl_authorization_pytest=9 passed",
        "autodl_training_sufficiency_contract_pytest=19 passed",
        "autodl_unit_tests_plan_pytest=8 passed",
        "autodl_target_pytest=44 passed",
        "autodl_git_diff_check_exit=0",
        "preflight_implementation_complete=True",
        "expected_validated_dataset_sha_already_current=True",
        "training_not_executed=True",
        "candidate_generation_not_executed=True",
        "dp_not_modified=True",
        "selector_or_atom_not_promoted=True",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_review_only",
    ]:
        assert needle in combined


def test_current_head_19b6ecc_preflight_implementation_eof_revalidation_is_pinned() -> None:
    marker = "\n## Current Tail Confirmation After 19b6ecc Fallback Risk Training Sufficiency Preflight Implementation\n\n"
    doc = IMPL_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    assert marker in doc
    assert marker in audit
    combined = (
        doc.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]
        + audit.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]
    )

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_implementation_head_19b6ecc_revalidated",
        "implementation_base_head=19b6ecc3ddbc2b3605870b0553f3a2467cc7f2fa",
        "camp_origin_main_at_implementation=19b6ecc3ddbc2b3605870b0553f3a2467cc7f2fa",
        "github_refs_heads_main_at_implementation=19b6ecc3ddbc2b3605870b0553f3a2467cc7f2fa",
        "autodl_CAMP_HEAD_at_implementation=19b6ecc3ddbc2b3605870b0553f3a2467cc7f2fa",
        "autodl_CAMP_origin_main_at_implementation=19b6ecc3ddbc2b3605870b0553f3a2467cc7f2fa",
        "autodl_DP_HEAD_at_implementation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_authorization_status=fallback_risk_training_sufficiency_preflight_implementation_authorization_head_e3b27b7_revalidated",
        "validated_fallback_records=15",
        "expected_validated_dataset_sha_already_current=True",
        "expected_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "validator_output_json_sha256=4f3a0be2dbf070b4d94262111e3c9b68618732efd64f54355722dbfbe61f2d40",
        "validator_output_md_sha256=e57c15b6772e0202fe76fec20d220e435c1010aab7bc410fb45230277fc9ab6a",
        "strict_formal_seed_path_matches=0",
        "implementation_file=scripts/integrations/validate_dp_native_fallback_risk_training_sufficiency_preflight.py",
        "production_preflight_script_modified_in_this_gate=False",
        "implementation_scope=current_default_off_read_only_preflight_revalidation",
        "preflight_default_off=True",
        "preflight_read_only=True",
        "manifest_inputs_only=True",
        "disabled_mode_returns_before_manifest_read=True",
        "writes_only_explicit_output_json_and_output_md=True",
        "subprocess_usage_introduced=False",
        "training_execution_path_introduced=False",
        "diffusion_planner_execution_path_introduced=False",
        "candidate_generation_path_introduced=False",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "fallback_label_is_not_a_deployed_atom=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "ready_for_future_training_authorization_is_not_training_authorization=True",
        "local_preflight_pytest=9 passed",
        "local_authorization_pytest=10 passed",
        "local_training_sufficiency_contract_pytest=20 passed",
        "local_unit_tests_plan_pytest=9 passed",
        "local_target_pytest=48 passed",
        "local_py_compile_exit=0",
        "local_git_diff_check_exit=0",
        "autodl_temp_worktree=/root/autodl-tmp/camp_core_preflight_impl_19b6ecc_verify_20260627T080000Z",
        "autodl_py_compile_exit=0",
        "autodl_preflight_pytest=9 passed",
        "autodl_authorization_pytest=10 passed",
        "autodl_training_sufficiency_contract_pytest=20 passed",
        "autodl_unit_tests_plan_pytest=9 passed",
        "autodl_target_pytest=48 passed",
        "autodl_git_diff_check_exit=0",
        "preflight_implementation_complete=True",
        "expected_validated_dataset_sha_already_current=True",
        "training_not_executed=True",
        "candidate_generation_not_executed=True",
        "dp_not_modified=True",
        "selector_or_atom_not_promoted=True",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "Full36_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "reference_blend_authorized=False",
        "guidance_authorized=False",
        "postprocess_postselection_authorized=False",
        "closed_loop_outcome_online_input_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "training_execution_authorized_now=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_review_only",
    ]:
        assert needle in combined


def test_current_head_f77b4c1_preflight_implementation_revalidation_is_pinned() -> None:
    doc = IMPL_DOC.read_text(encoding="utf-8")
    audit_text = ITERATION_AUDIT.read_text(encoding="utf-8")
    audit_tail = audit_text[-16000:]
    combined = doc + audit_tail
    status = "status=fallback_risk_training_sufficiency_preflight_implementation_head_f77b4c1_revalidated"

    assert status in audit_text

    for needle in [
        status,
        "implementation_base_head=f77b4c151dbca03eb8b381561182f66f9f5c88ec",
        "prior_authorization_status=fallback_risk_training_sufficiency_preflight_implementation_authorization_head_193ce66_revalidated",
        "old_expected_validated_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "new_expected_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "implementation_scope=expected_validated_dataset_sha_only",
        "preflight_default_off=True",
        "preflight_read_only=True",
        "manifest_inputs_only=True",
        "disabled_mode_returns_before_manifest_read=True",
        "training_execution_path_introduced=False",
        "diffusion_planner_execution_path_introduced=False",
        "candidate_generation_path_introduced=False",
        "score_k(w)=a_k^T w",
        "a_k_fixed_before_weight_optimization=True",
        "a_k_nonnegative_benders_compatible_atoms_only=True",
        "simplex_master_convex_if_later_authorized=True",
        "cvar_master_convex_if_later_authorized=True",
        "l2_regularized_master_convex_if_later_authorized=True",
        "local_preflight_pytest=7 passed",
        "local_authorization_pytest=8 passed",
        "local_training_sufficiency_contract_pytest=18 passed",
        "local_unit_tests_plan_pytest=8 passed",
        "local_target_pytest=41 passed",
        "autodl_preflight_pytest=7 passed",
        "autodl_authorization_pytest=8 passed",
        "autodl_training_sufficiency_contract_pytest=18 passed",
        "autodl_unit_tests_plan_pytest=8 passed",
        "autodl_target_pytest=41 passed",
        "preflight_implementation_complete=True",
        "expected_validated_dataset_sha_updated=True",
        "training_not_executed=True",
        "candidate_generation_not_executed=True",
        "dp_not_modified=True",
        "selector_or_atom_not_promoted=True",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_review_only",
    ]:
        assert needle in combined


def _write(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _payloads() -> dict[str, dict[str, Any]]:
    train = ["log_a:run_0:0", "log_a:run_0:1"]
    validation = ["log_b:run_1:0"]
    return {
        "validated_dataset": {
            "sha256": VALIDATED_DATASET_SHA,
            "records": 15,
            "validator_status": "dp_native_fallback_risk_training_data_validator_complete",
            "validator_passed": True,
            "training_sufficiency_claim": False,
            "deployable_checkpoint_claim": False,
        },
        "split": {
            "group_key_fields": ["source_log", "run_id", "record_index"],
            "training_groups": train,
            "validation_groups": validation,
            "seeds": [21, 22],
            "formal_eval_artifact_included": False,
        },
        "scales": {
            "fit_groups": train,
            "fit_seeds": [21, 22],
            "formal_eval_artifact_included": False,
            "atom_schema_version": APPROVED_SCHEMA,
            "atom_names": list(APPROVED_ATOMS),
            "atom_scales": {name: 1.0 for name in APPROVED_ATOMS},
        },
        "master": {
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
        "command": {
            "training_command_authorization": False,
            "replay_execution_authorized": False,
            "candidate_generation_authorized": False,
            "camp_training_authorized": False,
            "camp_retraining_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_11_12_13_authorized": False,
            "dp_modification_authorized": False,
            "reference_blend_authorized": False,
            "guidance_authorized": False,
            "postprocess_postselection_authorized": False,
            "closed_loop_outcome_online_input_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "fallback_risk_training_authorized_now": False,
            "feasible_ranking_master_change_authorized": False,
            "hard_feasibility_relaxation_authorized": False,
            "all_infeasible_records_added_to_feasible_training": False,
            "production_selector_change_authorized": False,
            "online_selector_change_authorized": False,
            "post_training_nonpromotion_plan_required": True,
            "development_holdout_acceptance_gate_required": True,
        },
    }


def _write_inputs(tmp_path: Path, payloads: dict[str, dict[str, Any]] | None = None) -> dict[str, Path]:
    data = payloads or _payloads()
    return {
        "validated_dataset_summary_json": _write(tmp_path / "validated_dataset.json", data["validated_dataset"]),
        "training_split_manifest_json": _write(tmp_path / "split.json", data["split"]),
        "train_only_scale_manifest_json": _write(tmp_path / "scales.json", data["scales"]),
        "fallback_master_config_json": _write(tmp_path / "master.json", data["master"]),
        "training_command_plan_json": _write(tmp_path / "command.json", data["command"]),
    }


def _run(paths: dict[str, Path], *, enabled: bool = True) -> dict[str, Any]:
    return validate_training_sufficiency_preflight(
        enabled=enabled,
        **paths,
    )


def test_preflight_is_default_off_and_does_not_read_missing_inputs(tmp_path: Path) -> None:
    missing = {
        "validated_dataset_summary_json": tmp_path / "missing_dataset.json",
        "training_split_manifest_json": tmp_path / "missing_split.json",
        "train_only_scale_manifest_json": tmp_path / "missing_scales.json",
        "fallback_master_config_json": tmp_path / "missing_master.json",
        "training_command_plan_json": tmp_path / "missing_command.json",
    }

    report = _run(missing, enabled=False)

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True
    assert report["source_hashes"] == {}


def test_preflight_accepts_clean_synthetic_manifests_and_cli_writes_outputs(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "preflight.json"
    output_md = tmp_path / "out" / "preflight.md"

    report = _run(paths)
    exit_code = main(
        [
            "--validated_dataset_summary_json",
            str(paths["validated_dataset_summary_json"]),
            "--training_split_manifest_json",
            str(paths["training_split_manifest_json"]),
            "--train_only_scale_manifest_json",
            str(paths["train_only_scale_manifest_json"]),
            "--fallback_master_config_json",
            str(paths["fallback_master_config_json"]),
            "--training_command_plan_json",
            str(paths["training_command_plan_json"]),
            "--enable_default_off_fallback_risk_training_sufficiency_preflight",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )
    written = json.loads(output_json.read_text(encoding="utf-8"))

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["final_decision"]["ready_for_future_training_authorization"] is True
    assert report["final_decision"]["training_authorized"] is False
    assert report["final_decision"]["fallback_dataset_training_sufficiency_claim"] is False
    assert exit_code == 0
    assert written["final_decision"]["status"] == COMPLETE_STATUS
    assert "training_authorized=False" in output_md.read_text(encoding="utf-8")


def test_preflight_rejects_dataset_claims_split_and_formal_seed_leaks(tmp_path: Path) -> None:
    payloads = _payloads()
    payloads["validated_dataset"]["training_sufficiency_claim"] = True
    payloads["validated_dataset"]["deployable_checkpoint_claim"] = True
    payloads["split"]["training_groups"].append("log_b:run_1:0")
    payloads["split"]["seeds"] = [11]
    payloads["split"]["formal_eval_artifact_included"] = True

    report = _run(_write_inputs(tmp_path, payloads))
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "training_sufficiency_claim_leak",
        "deployable_checkpoint_claim_leak",
        "split_train_validation_overlap",
        "formal_seed_in_development_split",
        "formal_eval_artifact_in_development_split",
    ]:
        assert needle in errors


def test_preflight_rejects_scale_master_and_affine_contract_violations(tmp_path: Path) -> None:
    payloads = _payloads()
    payloads["scales"]["fit_groups"] = ["log_a:run_0:0", "log_b:run_1:0"]
    payloads["scales"]["fit_seeds"] = [12]
    payloads["scales"]["atom_schema_version"] = "wrong"
    payloads["scales"]["atom_scales"]["jerk_early"] = 0.0
    payloads["master"]["feasible_branch_records_allowed"] = True
    payloads["master"]["hard_feasibility_relaxation_authorized"] = True
    payloads["master"]["score_expression"] = "score_k(w)=a_k^T w + rank"
    payloads["master"]["fallback_label_is_deployed_atom"] = True

    errors = _run(_write_inputs(tmp_path, payloads))["final_decision"]["errors"]

    for needle in [
        "scale_fit_groups_not_training_only",
        "scale_fit_validation_leak",
        "scale_fit_formal_seed_leak",
        "scale_atom_schema_mismatch",
        "atom_scale_jerk_early_not_strictly_positive",
        "feasible_branch_records_allowed_leak",
        "hard_feasibility_relaxation_authorized_leak",
        "score_expression_not_affine",
        "fallback_label_promoted_to_atom",
    ]:
        assert needle in errors


def test_preflight_rejects_training_commands_dp_changes_promotions_and_claims(tmp_path: Path) -> None:
    payloads = _payloads()
    command = payloads["command"]
    command["training_command_authorization"] = True
    command["camp_training_authorized"] = True
    command["camp_retraining_authorized"] = True
    command["replay_execution_authorized"] = True
    command["candidate_generation_authorized"] = True
    command["dp_modification_authorized"] = True
    command["selector_promotion_authorized"] = True
    command["atom_promotion_authorized"] = True
    command["safety_benefit_claim_authorized"] = True
    command["camp_over_dp_top1_claim_authorized"] = True
    command["post_training_nonpromotion_plan_required"] = False
    command["development_holdout_acceptance_gate_required"] = False

    errors = _run(_write_inputs(tmp_path, payloads))["final_decision"]["errors"]

    for needle in [
        "training_command_authorization_leak",
        "camp_training_authorized_leak",
        "camp_retraining_authorized_leak",
        "replay_execution_authorized_leak",
        "candidate_generation_authorized_leak",
        "dp_modification_authorized_leak",
        "selector_promotion_authorized_leak",
        "atom_promotion_authorized_leak",
        "safety_benefit_claim_authorized_leak",
        "camp_over_dp_top1_claim_authorized_leak",
        "post_training_nonpromotion_plan_missing",
        "development_holdout_acceptance_gate_missing",
    ]:
        assert needle in errors
