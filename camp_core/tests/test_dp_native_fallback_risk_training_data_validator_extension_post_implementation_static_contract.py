from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_post_implementation_static_contract_review.md"
)
VALIDATOR = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "validate_dp_native_fallback_risk_training_data_contract.py"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _source() -> str:
    return VALIDATOR.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def test_review_doc_records_validator_post_implementation_contract() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off_boundary_passed=True",
        "read_only_fixed_artifact_boundary_passed=True",
        "dataset_contract_passed=True",
        "affine_score_boundary_preserved=True",
        "training_sufficiency_boundary_passed=True",
        "implementation_hardening_required=False",
        "blocking_contract_findings=0",
        "post_implementation_static_contract_review_complete=True",
        "fallback_risk_training_authorized_now=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "latest_post_static_revalidation_base_head=f0f9fa088052bb3c55fea51d918aec9f60a5ce1e",
        "latest_autodl_CAMP_HEAD_at_revalidation=f0f9fa088052bb3c55fea51d918aec9f60a5ce1e",
        "latest_autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_validator_implementation_status=fallback_risk_training_data_validator_extension_implementation_autodl_verification_passed",
        "latest_local_target_pytest=18 passed",
        "latest_autodl_target_pytest=18 passed",
        "user_broad_execution_permission_recorded=True",
        "this_post_static_gate_authorizes_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_validator_is_default_off_before_reading_dataset_json() -> None:
    tree = _tree()
    source = _source()
    validate = _function(tree, "validate_fallback_risk_training_data")

    enabled_index = validate.args.kwonlyargs.index(
        next(arg for arg in validate.args.kwonlyargs if arg.arg == "enabled")
    )
    enabled_default = validate.args.kw_defaults[enabled_index]
    assert isinstance(enabled_default, ast.Constant)
    assert enabled_default.value is False

    disabled_return_index = None
    dataset_read_index = None
    for index, node in enumerate(validate.body):
        if isinstance(node, ast.If) and isinstance(node.test, ast.UnaryOp):
            operand = node.test.operand
            if (
                isinstance(node.test.op, ast.Not)
                and isinstance(operand, ast.Name)
                and operand.id == "enabled"
                and any(isinstance(item, ast.Return) for item in node.body)
            ):
                disabled_return_index = index
        if isinstance(node, ast.Try) and "dataset_json.read_text" in ast.unparse(node):
            dataset_read_index = index

    assert disabled_return_index is not None
    assert dataset_read_index is not None
    assert disabled_return_index < dataset_read_index
    assert "--enable_default_off_fallback_risk_training_data_validator" in source
    assert "action=\"store_true\"" in source


def test_validator_writes_only_explicit_reports_and_uses_no_subprocess() -> None:
    tree = _tree()
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


def test_validator_fail_closed_source_readback_and_atom_contracts() -> None:
    source = _source()

    for needle in [
        "source_log_readback_required_for_acceptance",
        "source_log_readback_required_for_acceptance",
        "source_log_missing_on_disk",
        "source_log_hash_mismatch",
        "source_feasible_mask_non_bool",
        "source_feasible_mask_any_true",
        "source_candidate_count_mismatch",
        "source_selected_index_mismatch",
        "source_candidate_generation_contract_rechecked=True",
        "contract.get(\"reference_blend_steps\") is not None",
        "contract.get(\"guidance_enabled\") is not False",
        "contract.get(\"changes_diffusion_planner_weights\") is not False",
        "pre_post_tensor_hash_equal",
        "candidate_generation_authorized",
        "dp_modification_authorized",
        "source_provenance_{field}_not_true",
        "source_provenance_{field}_not_false",
        "atom_schema_for_dimension(atom_dim)",
        "_validate_matrix(atoms, candidate_count, atom_dim, f\"{prefix}_atoms\")",
        "_validate_matrix(normalized, candidate_count, atom_dim, f\"{prefix}_normalized_atoms\")",
    ]:
        assert needle in source + REVIEW_DOC.read_text(encoding="utf-8")


def test_validator_decision_forbids_training_dp_and_promotion() -> None:
    source = _source()
    review = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        '"training_authorized": False',
        '"fallback_dataset_training_sufficiency_claim": False',
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "feasible_ranking_master_change_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "for flag in FORBIDDEN_FLAGS",
        "status=fallback_risk_training_data_validator_extension_implemented",
    ]:
        assert needle in source + review + audit

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


def test_review_next_gate_is_validator_fixed_artifact_acceptance_audit_only() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_fixed_artifact_acceptance_audit_only",
        "may only run the default-off validator",
        "existing non-formal fallback-risk training dataset artifact",
        "must not run replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
