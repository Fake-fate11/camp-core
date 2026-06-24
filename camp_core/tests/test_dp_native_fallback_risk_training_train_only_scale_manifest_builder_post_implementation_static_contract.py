from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_builder_post_implementation_static_contract_review.md"
)
SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_train_only_scale_manifest.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_dp_native_fallback_risk_training_train_only_scale_manifest_builder.py"
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
        "disabled_status=dp_native_fallback_risk_training_train_only_scale_manifest_builder_default_off_disabled",
        "enable_flag=--enable_default_off_fallback_risk_training_train_only_scale_manifest_builder",
        "disabled_mode_returns_before_dataset_or_split_read=True",
        "disabled_mode_reads_inputs=False",
        "output_json_or_markdown_only=True",
    ]:
        assert needle in review

    assert "if not enabled:\n        return report" in script
    assert script.index("if not enabled:\n        return report") < script.index(
        'dataset = _load_json(dataset_json, "dataset_json", errors)'
    )
    assert "--enable_default_off_fallback_risk_training_train_only_scale_manifest_builder" in script
    assert 'action="store_true"' in script

    write_receivers = []
    mkdir_receivers = []
    subprocess_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = ast.unparse(node.func.value)
        if node.func.attr == "write_text":
            write_receivers.append(receiver)
        if node.func.attr == "mkdir":
            mkdir_receivers.append(receiver)
        if receiver == "subprocess":
            subprocess_calls.append(node.func.attr)

    assert write_receivers == ["args.output_json", "args.output_md"]
    assert mkdir_receivers == ["args.output_json.parent", "args.output_md.parent"]
    assert subprocess_calls == []


def test_post_static_review_records_existing_artifact_hash_and_scope_boundary() -> None:
    review = _review()
    script = _script()

    for needle in [
        "source_artifact_boundary_passed=True",
        "enabled_input_source=existing_validated_fallback_dataset_json_and_existing_split_manifest_json_only",
        "requires_expected_dataset_sha256=True",
        "requires_expected_split_manifest_sha256=True",
        "requires_validator_output_sha256=True",
        "dataset_sha256_mismatch_fails_closed=True",
        "split_manifest_sha256_mismatch_fails_closed=True",
        "validator_output_sha256_invalid_fails_closed=True",
        "scale_manifest_builder_execution_on_fixed_artifact_authorized=False",
    ]:
        assert needle in review

    for needle in [
        'parser.add_argument("--dataset_json", type=Path, required=True)',
        'parser.add_argument("--expected_dataset_sha256", required=True)',
        'parser.add_argument("--training_split_manifest_json", type=Path, required=True)',
        'parser.add_argument("--expected_split_manifest_sha256", required=True)',
        'parser.add_argument("--validator_output_sha256", required=True)',
        'errors.append("dataset_sha256_mismatch")',
        'errors.append("split_manifest_sha256_mismatch")',
        'errors.append(f"{field}_invalid")',
    ]:
        assert needle in script


def test_post_static_review_records_train_only_scale_policy() -> None:
    review = _review()
    script = _script()
    builder_test = _builder_test()

    for needle in [
        "train_only_scale_policy_passed=True",
        "fit_scope=split_manifest_training_groups_only",
        "validation_groups_excluded_from_fit=True",
        "scale_policy=train_only_positive_finite_p95_or_one_v1",
        "positive_finite_training_values_only=True",
        "no_positive_training_value_scale_defaults_to_one=True",
        "invalid_training_record_contributes_no_partial_scale=True",
        "dataset_record_not_in_split_manifest_fails_closed=True",
        "missing_training_or_validation_group_fails_closed=True",
    ]:
        assert needle in review

    for needle in [
        "SCALE_POLICY = \"train_only_positive_finite_p95_or_one_v1\"",
        '"fit_scope": "split_manifest_training_groups_only"',
        '"validation_groups_excluded": True',
        "if group in validation:",
        "if group not in train:",
        "if float(value) > 0.0:",
        "record_atom_values: dict[str, list[float]]",
        "atom_values[atom].extend(values)",
        "return float(ordered[index])",
        "math.ceil(0.95 * len(ordered)) - 1",
        'errors.append(f"record_{index}:dataset_record_not_in_split_manifest")',
        'errors.append("missing_training_groups")',
        'errors.append("missing_validation_groups")',
    ]:
        assert needle in script

    for needle in [
        'assert report["atom_scales"]["jerk_early"] == 1.0',
        'assert report["atom_scales"][APPROVED_ATOM_NAMES[-1]] == 1.0',
        'assert report["fit_record_counts"]["validation_records_seen"] == 1',
    ]:
        assert needle in builder_test


def test_post_static_review_records_forbidden_feature_formal_and_atom_boundary() -> None:
    review = _review()
    script = _script()
    builder_test = _builder_test()

    for needle in [
        "forbidden_feature_formal_atom_boundary_passed=True",
        "selected_index_feature_leak_rejected=True",
        "candidate_rank_feature_leak_rejected=True",
        "closed_loop_outcome_feature_leak_rejected=True",
        "learned_weights_feature_leak_rejected=True",
        "formal_seeds_11_12_13_rejected=True",
        "formal_eval_artifact_rejected=True",
        "atom_schema_version=dp_camp_v10_14d",
        "atom_count=14",
        "nonfinite_atom_rejected=True",
        "negative_atom_rejected=True",
    ]:
        assert needle in review

    for needle in [
        "FORMAL_SEEDS = {11, 12, 13}",
        '"selected_index_used_as_feature"',
        '"candidate_rank_used_as_feature"',
        '"closed_loop_outcome_used_as_feature"',
        '"learned_weights_used_as_feature"',
        '"selected_index_scale_feature"',
        '"candidate_rank_scale_feature"',
        '"closed_loop_outcome_scale_feature"',
        '"learned_weights_scale_feature"',
        "APPROVED_ATOM_SCHEMA",
        "APPROVED_ATOM_NAMES",
        'errors.append("formal_seed_record_leak")',
        'errors.append("formal_eval_artifact_record_leak")',
        'errors.append("atom_schema_mismatch")',
        'errors.append("atom_names_mismatch")',
        'errors.append(f"{atom}_not_finite_numeric")',
        'errors.append(f"{atom}_negative")',
    ]:
        assert needle in script

    for needle in [
        "record_0:selected_index_scale_feature_leak",
        "record_0:candidate_rank_scale_feature_leak",
        "record_1:closed_loop_outcome_scale_feature_leak",
        "record_1:learned_weights_scale_feature_leak",
        "record_0:atom_schema_mismatch",
        "record_1:atom_names_mismatch",
        "record_0:jerk_early_not_finite_numeric",
        "record_1:jerk_late_negative",
    ]:
        assert needle in builder_test


def test_post_static_review_records_preflight_and_no_training_boundary() -> None:
    review = _review()
    script = _script()
    builder_test = _builder_test()
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        "output_preflight_boundary_passed=True",
        "preflight_shape_compatible=True",
        "validate_training_sufficiency_preflight",
        "final_decision_training_authorized=False",
        "final_decision_fallback_dataset_training_sufficiency_claim=False",
        "final_decision_camp_retraining_authorized_now=False",
        "local_target_pytest=6 passed",
        "local_fallback_risk_related_pytest=281 passed",
        "autodl_target_pytest=6 passed",
        "autodl_fallback_risk_related_pytest=281 passed",
    ]:
        assert needle in review

    for needle in [
        '"training_authorized": False',
        '"fallback_dataset_training_sufficiency_claim": False',
        '"camp_retraining_authorized_now": False',
        '"replay_executed": False',
        '"candidate_generation_executed": False',
        '"camp_training_executed": False',
        '"diffusion_planner_executed": False',
        '"diffusion_planner_modified": False',
    ]:
        assert needle in script

    for needle in [
        "validate_training_sufficiency_preflight",
        "PREFLIGHT_COMPLETE_STATUS",
        'assert preflight["final_decision"]["status"] == PREFLIGHT_COMPLETE_STATUS',
    ]:
        assert needle in builder_test

    for forbidden in [
        "fallback_risk_training_authorized_now=True",
        "fallback_dataset_training_sufficiency_claim=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in review

    assert "status=fallback_risk_training_train_only_scale_manifest_builder_implemented" in audit


def test_post_static_review_next_gate_is_fixed_artifact_acceptance_audit_only() -> None:
    review = _review()

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_builder_post_implementation_static_contract_passed",
        "passed=True",
        "static_contract_review_complete=True",
        "blocking_contract_findings=0",
        "scale_manifest_builder_execution_on_fixed_artifact_authorized=False",
        "scale_fitting_on_fixed_artifact_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_builder_fixed_artifact_acceptance_audit_only",
        "may only run the default-off scale manifest builder on the",
        "existing validated fixed artifact dataset and split manifest",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in review
