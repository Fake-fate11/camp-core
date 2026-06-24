from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_post_implementation_static_contract_review.md"
)
EXTRACTOR = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "extract_diffusion_planner_dp_native_fallback_risk_records.py"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _source() -> str:
    return EXTRACTOR.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def test_review_doc_records_post_implementation_contract() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off_boundary_passed=True",
        "read_only_fixed_artifact_boundary_passed=True",
        "output_boundary_passed=True",
        "affine_score_boundary_preserved=True",
        "feasible_master_separation_passed=True",
        "blocking_contract_findings=0",
        "implementation_change_required=False",
        "post_implementation_static_contract_review_complete=True",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
    ]:
        assert needle in text


def test_extractor_is_static_default_off_before_reading_artifact() -> None:
    tree = _tree()
    source = _source()
    build = _function(tree, "build_extraction_report")

    enabled_index = build.args.kwonlyargs.index(
        next(arg for arg in build.args.kwonlyargs if arg.arg == "enabled")
    )
    enabled_default = build.args.kw_defaults[enabled_index]
    assert isinstance(enabled_default, ast.Constant)
    assert enabled_default.value is False

    disabled_return_index = None
    audit_call_index = None
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
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if getattr(node.value.func, "id", None) == "build_audit_report":
                audit_call_index = index

    assert disabled_return_index is not None
    assert audit_call_index is not None
    assert disabled_return_index < audit_call_index
    assert "--enable_default_off_fallback_risk_extractor" in source
    assert "action=\"store_true\"" in source


def test_extractor_writes_only_explicit_outputs() -> None:
    tree = _tree()
    write_receivers = []
    mkdir_receivers = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = ast.unparse(node.func.value)
        if node.func.attr == "write_text":
            write_receivers.append(receiver)
        if node.func.attr == "mkdir":
            mkdir_receivers.append(receiver)

    assert write_receivers == ["args.output_json", "args.output_md"]
    assert mkdir_receivers == ["args.output_json.parent", "args.output_md.parent"]


def test_extractor_subprocess_is_limited_to_git_head_probe() -> None:
    tree = _tree()
    subprocess_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and ast.unparse(func.value) == "subprocess":
            subprocess_calls.append((func.attr, node))

    assert [name for name, _ in subprocess_calls] == ["check_output"]
    command = subprocess_calls[0][1].args[0]
    assert isinstance(command, ast.List)
    command_values = [
        item.value for item in command.elts if isinstance(item, ast.Constant)
    ]
    assert command_values == ["git", "-C", "rev-parse", "HEAD"]


def test_extractor_decision_forbids_training_dp_and_promotion() -> None:
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
        "status=fallback_risk_ranking_default_off_extractor_implemented",
    ]:
        assert needle in source + review + audit

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
        assert forbidden not in review


def test_review_next_gate_is_training_data_design_plan_only() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_plan_only",
        "may only design the offline data contract",
        "must not implement training",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text
