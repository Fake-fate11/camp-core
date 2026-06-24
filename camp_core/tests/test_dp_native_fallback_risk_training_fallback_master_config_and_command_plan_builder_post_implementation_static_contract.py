from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_builder_post_implementation_static_contract_review.md"
)
SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_fallback_master_config_and_command_plan.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder.py"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _builder_test() -> str:
    return BUILDER_TEST.read_text(encoding="utf-8")


def test_post_static_review_records_default_off_and_write_boundary() -> None:
    review = _review()
    script = _script()
    tree = ast.parse(script)

    for needle in [
        "default_off_boundary_passed=True",
        "disabled_status=dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder_default_off_disabled",
        "enable_flag=--enable_default_off_fallback_risk_training_master_command_builder",
        "disabled_mode_returns_before_any_manifest_read=True",
        "disabled_mode_reads_inputs=False",
        "disabled_mode_writes_master_or_command=False",
        "writes_master_and_command_only_when_complete=True",
    ]:
        assert needle in review

    assert "if not enabled:\n        return report" in script
    assert script.index("if not enabled:\n        return report") < script.index(
        'dataset = _load_json(dataset_json, "dataset_json", errors)'
    )
    assert "--enable_default_off_fallback_risk_training_master_command_builder" in script

    write_receivers = []
    subprocess_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = ast.unparse(node.func.value)
        if node.func.attr == "write_text":
            write_receivers.append(receiver)
        if receiver == "subprocess":
            subprocess_calls.append(node.func.attr)

    assert write_receivers == [
        "args.output_md",
        "args.output_master_config_json",
        "args.output_training_command_plan_json",
    ]
    assert subprocess_calls == []


def test_post_static_review_records_input_hash_and_scope_boundary() -> None:
    review = _review()
    script = _script()

    for needle in [
        "input_hash_scope_boundary_passed=True",
        "reads_validated_dataset_json_only=True",
        "reads_training_split_manifest_json_only=True",
        "reads_train_only_scale_manifest_json_only=True",
        "requires_expected_dataset_sha256=True",
        "requires_expected_split_manifest_sha256=True",
        "requires_expected_scale_manifest_sha256=True",
        "dataset_sha256_mismatch_fails_closed=True",
        "split_manifest_sha256_mismatch_fails_closed=True",
        "scale_manifest_sha256_mismatch_fails_closed=True",
        "fixed_artifact_master_command_manifest_generation_authorized=False",
    ]:
        assert needle in review

    for needle in [
        'parser.add_argument("--expected_dataset_sha256", required=True)',
        'parser.add_argument("--expected_split_manifest_sha256", required=True)',
        'parser.add_argument("--expected_scale_manifest_sha256", required=True)',
        '"dataset_sha256_mismatch"',
        '"split_manifest_sha256_mismatch"',
        '"scale_manifest_sha256_mismatch"',
    ]:
        assert needle in script


def test_post_static_review_records_fail_closed_split_scale_contracts() -> None:
    review = _review()
    script = _script()
    builder_test = _builder_test()

    for needle in [
        "split_scale_fail_closed_boundary_passed=True",
        "training_validation_overlap_rejected=True",
        "scale_fit_groups_not_training_only_rejected=True",
        "scale_fit_validation_leak_rejected=True",
        "formal_seed_in_split_rejected=True",
        "formal_eval_artifact_rejected=True",
        "scale_fit_formal_seed_leak_rejected=True",
        "scale_fit_formal_eval_leak_rejected=True",
        "dp_camp_v10_14d_required=True",
        "exact_14d_atom_names_required=True",
        "strictly_positive_atom_scales_required=True",
    ]:
        assert needle in review

    for needle in [
        "FORMAL_SEEDS = {11, 12, 13}",
        "APPROVED_ATOM_SCHEMA",
        "APPROVED_ATOM_NAMES",
        'errors.append("training_validation_overlap")',
        'errors.append("scale_fit_groups_not_training_only")',
        'errors.append("scale_fit_validation_leak")',
        'errors.append("formal_seed_in_split")',
        'errors.append("scale_fit_formal_seed_leak")',
        'errors.append("scale_atom_schema_mismatch")',
        'errors.append(f"atom_scale_{name}_not_strictly_positive")',
    ]:
        assert needle in script

    for needle in [
        "scale_fit_groups_not_training_only",
        "scale_fit_validation_leak",
        "formal_seed_in_split",
        "scale_fit_formal_eval_leak",
        "atom_scale_jerk_early_not_strictly_positive",
    ]:
        assert needle in builder_test


def test_post_static_review_records_master_command_preflight_boundary() -> None:
    review = _review()
    script = _script()
    builder_test = _builder_test()

    for needle in [
        "master_command_output_boundary_passed=True",
        "fallback_master_config_schema=dp_native_fallback_risk_fallback_master_config_v1",
        "training_command_plan_schema=dp_native_fallback_risk_training_command_plan_v1",
        "fallback_only=True",
        "score_expression=score_k(w)=a_k^T w",
        "atoms_fixed_nonnegative=True",
        "fallback_label_is_deployed_atom=False",
        "simplex_cvar_l2_convex=True",
        "training_command_authorization=False",
        "training_execution_authorized=False",
        "post_training_nonpromotion_plan_required=True",
        "development_holdout_acceptance_gate_required=True",
        "preflight_shape_compatible=True",
    ]:
        assert needle in review

    for needle in [
        '"score_expression": "score_k(w)=a_k^T w"',
        '"atoms_fixed_nonnegative": True',
        '"fallback_label_is_deployed_atom": False',
        '"simplex_cvar_l2_convex": True',
        '"training_command_authorization": False',
        '"training_execution_authorized": False',
        '"post_training_nonpromotion_plan_required": True',
        '"development_holdout_acceptance_gate_required": True',
    ]:
        assert needle in script

    for needle in [
        "validate_training_sufficiency_preflight",
        'assert preflight["final_decision"]["status"] == PREFLIGHT_COMPLETE_STATUS',
    ]:
        assert needle in builder_test


def test_post_static_review_keeps_training_dp_promotion_and_claims_forbidden() -> None:
    review = _review()
    script = _script()
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        '"replay_executed": False',
        '"candidate_generation_executed": False',
        '"camp_training_executed": False',
        '"diffusion_planner_executed": False',
        '"diffusion_planner_modified": False',
        '"training_authorized": False',
        '"training_execution_authorized": False',
        '"fallback_dataset_training_sufficiency_claim": False',
        '"camp_retraining_authorized_now": False',
        "status=fallback_risk_training_fallback_master_config_and_command_plan_builder_implemented",
    ]:
        assert needle in script + review + audit

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "training_execution_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "training_sufficiency_preflight_execution_authorized=True",
        "master_command_builder_execution_on_fixed_artifact_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_dataset_training_sufficiency_claim=True",
    ]:
        assert forbidden not in review


def test_post_static_review_next_gate_is_fixed_artifact_acceptance_audit_only() -> None:
    review = _review()

    for needle in [
        "status=fallback_risk_training_fallback_master_config_and_command_plan_builder_post_implementation_static_contract_passed",
        "passed=True",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_fallback_master_config_and_command_plan_builder_fixed_artifact_acceptance_audit_only",
        "may only run the default-off builder on the existing accepted fixed artifact manifests",
        "must not run the sufficiency preflight",
        "must not train CAMP",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in review
