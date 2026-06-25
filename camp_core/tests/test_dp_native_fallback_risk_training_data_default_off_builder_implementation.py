from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_implementation.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
BUILDER = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_data.py"
)
NEXT_STATIC_CONTRACT_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_default_off_builder_"
    "post_implementation_static_contract_only"
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


def test_implementation_doc_records_current_head_and_boundaries() -> None:
    text = IMPLEMENTATION_DOC.read_text(encoding="utf-8")
    current_head = "e7631084a17e3a520cd7b32e3b4940c38497de12"

    for needle in [
        "status=fallback_risk_training_data_default_off_builder_implementation_current_head_revalidated",
        "authorization_status=fallback_risk_training_data_default_off_builder_implementation_authorization_autodl_verification_passed",
        f"camp_head_at_revalidation={current_head}",
        f"camp_origin_main_at_revalidation={current_head}",
        f"github_refs_heads_main_at_revalidation={current_head}",
        f"autodl_CAMP_HEAD_at_revalidation={current_head}",
        f"autodl_CAMP_origin_main_at_revalidation={current_head}",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "implementation_already_present=True",
        "production_builder_changed_in_this_gate=False",
        "blocking_contract_findings=0",
    ]:
        assert needle in text


def test_builder_is_default_off_before_reading_selection_logs() -> None:
    tree = _tree()
    build = _function(tree, "build_training_data_report")
    source = _source()

    enabled_index = build.args.kwonlyargs.index(
        next(arg for arg in build.args.kwonlyargs if arg.arg == "enabled")
    )
    enabled_default = build.args.kw_defaults[enabled_index]
    assert isinstance(enabled_default, ast.Constant)
    assert enabled_default.value is False

    disabled_return_index = None
    records_from_path_index = None
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
        if isinstance(node, ast.For):
            if ast.unparse(node.iter) == "selection_logs":
                records_from_path_index = index

    assert disabled_return_index is not None
    assert records_from_path_index is not None
    assert disabled_return_index < records_from_path_index
    assert "--enable_default_off_fallback_risk_training_data_builder" in source
    assert "action=\"store_true\"" in source


def test_builder_writes_only_explicit_outputs_and_uses_no_subprocess() -> None:
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


def test_builder_decision_forbids_training_dp_and_promotion() -> None:
    source = _source()
    doc = IMPLEMENTATION_DOC.read_text(encoding="utf-8")

    for needle in [
        '"training_authorized": False',
        '"production_selector_change_authorized": False',
        '"online_selector_change_authorized": False',
        '"feasible_ranking_master_change_authorized": False',
        '"all_infeasible_records_added_to_feasible_training": False',
        '"hard_feasibility_relaxation_authorized": False',
        "for flag in FORBIDDEN_FLAGS",
        "score_k(w)=a_k^T w",
    ]:
        assert needle in source + doc

    for forbidden in [
        "fallback_risk_training_authorized_now=True",
        "fallback_risk_smoke_authorized_now=True",
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in doc


def test_implementation_doc_and_audit_tail_record_latest_revalidation() -> None:
    doc = IMPLEMENTATION_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    tail = "\n".join(audit.splitlines()[-140:])
    current_head = "9095a67320c893995cfcce1026cf4950eb3068b7"

    for payload in (doc, tail):
        for needle in [
            "status=fallback_risk_training_data_default_off_builder_implementation_current_head_revalidated_latest",
            f"camp_head_at_revalidation={current_head}",
            f"camp_origin_main_at_revalidation={current_head}",
            f"github_refs_heads_main_at_revalidation={current_head}",
            f"autodl_CAMP_HEAD_at_revalidation={current_head}",
            f"autodl_CAMP_origin_main_at_revalidation={current_head}",
            "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "authorization_status=fallback_risk_training_data_default_off_builder_implementation_authorization_current_head_revalidated_latest",
            "implementation_required_now=False",
            "implementation_already_present=True",
            "production_builder_changed_in_this_gate=False",
            "local_builder_implementation_pytest=17 passed",
            "github_pushed_commit=c90681332d9a123036af7e507e349a29936d4eed",
            "autodl_CAMP_HEAD_after_sync=c90681332d9a123036af7e507e349a29936d4eed",
            "autodl_CAMP_origin_main_after_sync=c90681332d9a123036af7e507e349a29936d4eed",
            "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "autodl_py_compile_exit=0",
            "autodl_builder_implementation_pytest=17 passed",
            "autodl_git_diff_check_exit=0",
            "autodl_audit_tail_gate=dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_post_implementation_static_contract_only",
            "blocking_contract_findings=0",
            "default_off_required=True",
            "read_only_selection_log_input_only=True",
            "records_scope=records_without_feasible_candidate_only",
            "score_k(w)=a_k^T w",
            "affine_score_boundary_preserved=True",
            "fallback_dataset_separate_from_feasible_master=True",
            "fallback_risk_training_authorized_now=False",
            "training_execution_authorized_now=False",
            NEXT_STATIC_CONTRACT_GATE,
        ]:
            assert needle in payload

    assert tail.rstrip().endswith(f"`{NEXT_STATIC_CONTRACT_GATE}`")
