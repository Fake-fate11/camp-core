from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_post_implementation_static_contract_review.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_split_manifest.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_dp_native_fallback_risk_training_split_manifest_builder.py"
)


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _builder_test() -> str:
    return BUILDER_TEST.read_text(encoding="utf-8")


def test_post_static_review_records_default_off_boundary() -> None:
    review = _review()
    script = _script()

    for needle in [
        "default_off_boundary_passed=True",
        "disabled_status=dp_native_fallback_risk_training_split_manifest_builder_default_off_disabled",
        "enable_flag=--enable_default_off_fallback_risk_training_split_manifest_builder",
        "disabled_mode_returns_before_dataset_read=True",
        "output_json_or_markdown_only=True",
    ]:
        assert needle in review

    assert "if not enabled:\n        return report" in script
    assert "--enable_default_off_fallback_risk_training_split_manifest_builder" in script


def test_post_static_review_records_dataset_source_and_hash_boundary() -> None:
    review = _review()
    script = _script()

    for needle in [
        "dataset_source_boundary_passed=True",
        "enabled_input_source=existing_validated_fallback_risk_training_dataset_json_only",
        "requires_expected_dataset_sha256=True",
        "requires_validator_output_sha256=True",
        "dataset_sha256_mismatch_fails_closed=True",
        "validator_output_sha256_invalid_fails_closed=True",
        "records_scope=records_without_feasible_candidate_only",
        "fixed_artifact_manifest_generation_authorized=False",
    ]:
        assert needle in review

    for needle in [
        "parser.add_argument(\"--dataset_json\", type=Path, required=True)",
        "parser.add_argument(\"--expected_dataset_sha256\", required=True)",
        "parser.add_argument(\"--validator_output_sha256\", required=True)",
        "errors.append(\"dataset_sha256_mismatch\")",
        "errors.append(f\"{field}_invalid\")",
    ]:
        assert needle in script


def test_post_static_review_records_identity_and_deterministic_split_policy() -> None:
    review = _review()
    script = _script()

    for needle in [
        "split_identity_policy_passed=True",
        "manifest_schema_version=dp_native_fallback_risk_training_split_manifest_v1",
        "group_key_fields=source_log,run_id,record_index",
        "record_identity_hash_required_input_field=True",
        "record_identity_hash_derived_from_source_log_sha256_run_id_record_index=True",
        "missing_record_identity_hash_fails_closed=True",
        "source_log_sha256_mismatch_fails_closed=True",
        "group_key_collision_fails_closed=True",
        "duplicate_record_identity_fails_closed=True",
        "split_policy=sha256(record_identity_hash + split_salt)",
        "split_salt=fallback_risk_training_split_v1",
        "validation_fraction_target=0.2",
        "empty_train_or_validation_fails_closed=True",
    ]:
        assert needle in review

    for needle in [
        "SPLIT_POLICY = \"sha256(record_identity_hash + split_salt)\"",
        "SPLIT_SALT = \"fallback_risk_training_split_v1\"",
        "VALIDATION_FRACTION_TARGET = 0.2",
        "GROUP_KEY_FIELDS = (\"source_log\", \"run_id\", \"record_index\")",
        "\"record_identity_hash\",",
        "errors.append(f\"{field}_missing\")",
        "errors.append(\"group_key_collision\")",
        "errors.append(\"duplicate_record_identity\")",
        "errors.append(\"split_train_or_validation_empty\")",
    ]:
        assert needle in script


def test_post_static_review_records_forbidden_feature_and_formal_rejections() -> None:
    review = _review()
    script = _script()
    builder_test = _builder_test()

    for needle in [
        "forbidden_feature_formal_boundary_passed=True",
        "selected_index_used_as_feature_rejected=True",
        "candidate_rank_used_as_feature_rejected=True",
        "closed_loop_outcome_used_as_feature_rejected=True",
        "learned_weights_used_as_feature_rejected=True",
        "formal_seeds_11_12_13_rejected=True",
        "formal_eval_artifact_rejected=True",
        "training_authorized_leak_rejected=True",
    ]:
        assert needle in review

    for needle in [
        "FORMAL_SEEDS = {11, 12, 13}",
        "\"selected_index_used_as_feature\"",
        "\"candidate_rank_used_as_feature\"",
        "\"closed_loop_outcome_used_as_feature\"",
        "\"learned_weights_used_as_feature\"",
        "errors.append(\"formal_seed_in_split_manifest\")",
        "errors.append(\"formal_eval_artifact_record_included\")",
        "errors.append(\"training_authorized_leak\")",
    ]:
        assert needle in script

    for needle in [
        "record_5:formal_seed_in_split_manifest",
        "record_6:formal_eval_artifact_record_included",
        "record_7:selected_index_used_as_feature_leak",
        "record_8:candidate_rank_used_as_feature_leak",
    ]:
        assert needle in builder_test


def test_post_static_review_records_output_preflight_boundary_and_verification() -> None:
    review = _review()
    builder_test = _builder_test()

    for needle in [
        "output_preflight_boundary_passed=True",
        "top_level_fields=schema_version,dataset_sha256,validator_output_sha256,split_policy,split_salt,group_key_fields,training_groups,validation_groups,record_assignments,record_counts,final_decision",
        "preflight_shape_compatible=True",
        "synthetic_preflight_rejection_limited_to_expected_dataset_sha_mismatch=True",
        "final_decision_training_authorized=False",
        "final_decision_fallback_dataset_training_sufficiency_claim=False",
        "final_decision_camp_retraining_authorized_now=False",
        "local_post_static_target_pytest=7 passed",
        "local_builder_target_pytest=9 passed",
        "local_combined_target_pytest=16 passed",
        "autodl_python=/root/miniconda3/envs/camp/bin/python",
        "autodl_verified_camp_head=7084d69a66893d313d3e9a35f30f9446f830b2a5",
        "autodl_py_compile_exit=0",
        "autodl_combined_target_pytest=16 passed",
        "autodl_git_diff_check_exit=0",
    ]:
        assert needle in review

    for needle in [
        "assert preflight[\"final_decision\"][\"errors\"] == [\"validated_dataset_sha_mismatch\"]",
        "assert decision[\"training_authorized\"] is False",
        "assert decision[\"fallback_dataset_training_sufficiency_claim\"] is False",
        "assert decision[\"camp_retraining_authorized_now\"] is False",
    ]:
        assert needle in builder_test


def test_post_static_review_next_gate_is_fixed_artifact_acceptance_audit_only() -> None:
    review = _review()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_passed",
        "passed=True",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "record_identity_hash_missing_fails_closed=True",
        "fixed_artifact_manifest_generation_authorized=False",
        "training_split_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_audit_only",
        "may only run the default-off split manifest builder on the",
        "existing validated fixed artifact for acceptance evidence",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in review


def test_audit_tail_records_post_static_contract_next_gate() -> None:
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-180:])

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_post_implementation_static_contract_passed",
        "record_identity_hash_missing_fails_closed=True",
        "local_post_static_target_pytest=7 passed",
        "local_builder_target_pytest=9 passed",
        "autodl_combined_target_pytest=16 passed",
        "training_execution_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in audit

    assert "status=fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_rejected_missing_record_identity_hash" in tail

    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_authorization_only`"
    )
