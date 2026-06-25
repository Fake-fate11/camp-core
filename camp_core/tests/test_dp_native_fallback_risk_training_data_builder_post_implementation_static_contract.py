from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_post_implementation_static_contract_review.md"
)
BUILDER = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_data.py"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_FIXED_ARTIFACT_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_default_off_builder_"
    "fixed_artifact_acceptance_audit_only"
)


def _source() -> str:
    return BUILDER.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def test_review_doc_records_builder_post_implementation_contract() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")
    current_head = "1ea5cb0e76559bd00b469ae68616412b4194c8c3"

    for needle in [
        "default_off_boundary_passed=True",
        "read_only_fixed_artifact_boundary_passed=True",
        "affine_score_boundary_preserved=True",
        "training_sufficiency_boundary_passed=True",
        "implementation_hardening_completed=True",
        "blocking_contract_findings=0",
        "post_implementation_static_contract_review_complete=True",
        "fallback_risk_training_authorized_now=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "status=fallback_risk_training_data_default_off_builder_post_implementation_static_contract_current_head_revalidated",
        f"camp_head_at_current_head_revalidation={current_head}",
        f"camp_origin_main_at_current_head_revalidation={current_head}",
        f"github_refs_heads_main_at_current_head_revalidation={current_head}",
        f"autodl_CAMP_HEAD_at_current_head_revalidation={current_head}",
        f"autodl_CAMP_origin_main_at_current_head_revalidation={current_head}",
        "autodl_DP_HEAD_at_current_head_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "local_target_pytest=21 passed",
        "autodl_target_pytest=21 passed",
        "user_broad_execution_permission_recorded=True",
        "this_static_contract_gate_authorizes_broad_execution=False",
        "fixed_artifact_acceptance_audit_authorized_next=True",
    ]:
        assert needle in text


def test_builder_is_default_off_before_loading_any_input() -> None:
    tree = _tree()
    source = _source()
    build = _function(tree, "build_training_data_report")

    enabled_index = build.args.kwonlyargs.index(
        next(arg for arg in build.args.kwonlyargs if arg.arg == "enabled")
    )
    enabled_default = build.args.kw_defaults[enabled_index]
    assert isinstance(enabled_default, ast.Constant)
    assert enabled_default.value is False

    disabled_return_index = None
    extractor_load_index = None
    selection_read_index = None
    for index, node in enumerate(build.body):
        if isinstance(node, ast.If) and isinstance(node.test, ast.UnaryOp):
            operand = node.test.operand
            if (
                isinstance(node.test.op, ast.Not)
                and isinstance(operand, ast.Name)
                and operand.id == "enabled"
                and any(isinstance(item, ast.Return) for item in node.body)
            ):
                disabled_return_index = index
        if isinstance(node, ast.If) and "extractor_json" in ast.unparse(node.test):
            extractor_load_index = index
        if isinstance(node, ast.For) and "_records_from_path" in ast.unparse(node):
            selection_read_index = index

    assert disabled_return_index is not None
    assert extractor_load_index is not None
    assert selection_read_index is not None
    assert disabled_return_index < extractor_load_index < selection_read_index
    assert "--enable_default_off_fallback_risk_training_data_builder" in source
    assert "action=\"store_true\"" in source


def test_builder_writes_only_explicit_reports_and_uses_no_subprocess() -> None:
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


def test_builder_hardens_strict_type_and_matrix_contracts() -> None:
    source = _source()

    for needle in [
        "def _strict_int(",
        "isinstance(value, bool) or not isinstance(value, int)",
        "def _validate_nonnegative_matrix(",
        "row_dimension_mismatch",
        "normalized_atoms_atom_dimension_mismatch",
        "all(isinstance(item, bool) for item in value)",
        "contract.get(\"guidance_enabled\") is not False",
        "contract.get(\"changes_diffusion_planner_weights\") is not False",
        "\"reference_blend_steps\" not in contract",
    ]:
        assert needle in source

    for forbidden in [
        "return [bool(item) for item in value]",
        "index = int(value)",
        "bool(contract.get(\"guidance_enabled\"))",
        "bool(contract.get(\"changes_diffusion_planner_weights\"))",
    ]:
        assert forbidden not in source


def test_builder_decision_forbids_training_dp_and_promotion() -> None:
    source = _source()
    review = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        '"training_authorized": False',
        '"production_selector_change_authorized": False',
        '"online_selector_change_authorized": False',
        '"feasible_ranking_master_change_authorized": False',
        '"all_infeasible_records_added_to_feasible_training": False',
        "for flag in FORBIDDEN_FLAGS",
        "status=fallback_risk_training_data_default_off_builder_implemented",
    ]:
        assert needle in source + review + audit

    for forbidden in [
        "fallback_risk_training_authorized_now=True",
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


def test_review_next_gate_is_fixed_artifact_acceptance_audit_only() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_audit_only",
        "may only run the default-off builder",
        "existing non-formal fixed-artifact selection logs",
        "must not run replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text


def test_review_doc_and_audit_tail_record_latest_revalidation() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-140:])
    current_head = "8cbd4a23a907f19425df9ae09227d62c1edf2bbe"

    for payload in (text, tail):
        for needle in [
            "status=fallback_risk_training_data_default_off_builder_post_implementation_static_contract_current_head_revalidated_latest",
            f"camp_head_at_current_head_revalidation={current_head}",
            f"camp_origin_main_at_current_head_revalidation={current_head}",
            f"github_refs_heads_main_at_current_head_revalidation={current_head}",
            f"autodl_CAMP_HEAD_at_current_head_revalidation={current_head}",
            f"autodl_CAMP_origin_main_at_current_head_revalidation={current_head}",
            "autodl_DP_HEAD_at_current_head_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "prior_builder_implementation_status=fallback_risk_training_data_default_off_builder_implementation_current_head_revalidated_latest",
            "prior_builder_implementation_autodl_verified=True",
            "local_target_pytest=24 passed",
            "github_pushed_commit=bb98d8e7b4af7e2f4f0b1fce93f011c9222a73ca",
            "autodl_CAMP_HEAD_after_sync=bb98d8e7b4af7e2f4f0b1fce93f011c9222a73ca",
            "autodl_CAMP_origin_main_after_sync=bb98d8e7b4af7e2f4f0b1fce93f011c9222a73ca",
            "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "autodl_py_compile_exit=0",
            "autodl_target_pytest=24 passed",
            "autodl_git_diff_check_exit=0",
            "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_fixed_artifact_acceptance_audit_only",
            "post_implementation_static_contract_review_complete=True",
            "blocking_contract_findings=0",
            "default_off_boundary_passed=True",
            "read_only_fixed_artifact_boundary_passed=True",
            "affine_score_boundary_preserved=True",
            "training_sufficiency_boundary_passed=True",
            "fixed_artifact_acceptance_audit_authorized_next=True",
            "this_static_contract_gate_authorizes_broad_execution=False",
            "fallback_risk_training_authorized_now=False",
            "training_execution_authorized_now=False",
            NEXT_FIXED_ARTIFACT_GATE,
        ]:
            assert needle in payload

    assert tail.rstrip().endswith(f"`{NEXT_FIXED_ARTIFACT_GATE}`")
