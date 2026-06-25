from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_review.md"
)
PREFLIGHT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "validate_dp_native_fallback_risk_training_sufficiency_preflight.py"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _source() -> str:
    return PREFLIGHT.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def test_review_doc_records_preflight_post_implementation_contract() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off_boundary_passed=True",
        "read_only_manifest_boundary_passed=True",
        "training_sufficiency_boundary_passed=True",
        "affine_score_boundary_preserved=True",
        "approved_atom_names_match_dp_camp_v10_14d=True",
        "atom_schema_name_hardening_completed=True",
        "implementation_hardening_completed=True",
        "current_head_revalidation_passed=True",
        "camp_head_at_review_start=6d2ccc4349c3253d383c719f555e845a74d2febd",
        "blocking_contract_findings=0",
        "user_camp_retraining_permission_available=True",
        "training_execution_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "latest_validated_dataset_sha256=9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018",
        "camp_head_at_latest_review_start=c3e2eb5eb9750d4c5c10017f9ee4f4a1ffa13f3e",
        "autodl_DP_HEAD_at_latest_review_start=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_default_off_boundary_passed=True",
        "latest_read_only_manifest_boundary_passed=True",
        "latest_training_sufficiency_boundary_passed=True",
        "latest_affine_score_boundary_preserved=True",
        "latest_approved_atom_names_match_dp_camp_v10_14d=True",
        "latest_implementation_hardening_completed=True",
        "latest_blocking_contract_findings=0",
    ]:
        assert needle in text


def test_preflight_is_default_off_before_reading_any_manifest() -> None:
    tree = _tree()
    source = _source()
    validate = _function(tree, "validate_training_sufficiency_preflight")

    enabled_index = validate.args.kwonlyargs.index(
        next(arg for arg in validate.args.kwonlyargs if arg.arg == "enabled")
    )
    enabled_default = validate.args.kw_defaults[enabled_index]
    assert isinstance(enabled_default, ast.Constant)
    assert enabled_default.value is False

    disabled_return_index = None
    load_loop_index = None
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
        if isinstance(node, ast.For) and "_load_json" in ast.unparse(node):
            load_loop_index = index

    assert disabled_return_index is not None
    assert load_loop_index is not None
    assert disabled_return_index < load_loop_index
    assert "--enable_default_off_fallback_risk_training_sufficiency_preflight" in source
    assert "action=\"store_true\"" in source


def test_preflight_writes_only_explicit_reports_and_uses_no_subprocess() -> None:
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


def test_preflight_uses_exact_14d_atom_schema_names() -> None:
    source = _source()

    for needle in [
        'APPROVED_ATOM_SCHEMA = "dp_camp_v10_14d"',
        '"jerk_early"',
        '"jerk_late"',
        '"jerk_full"',
        '"rms_acceleration"',
        '"speed_limit_margin_0_0"',
        '"speed_limit_margin_0_5"',
        '"speed_limit_margin_1_0"',
        '"lane_deviation"',
        '"clearance"',
        '"progress_shortfall"',
        '"planned_red_light_cost"',
        '"planned_lateral_acceleration_cost"',
        '"red_stopping_margin_cost"',
        '"dp_prior_jerk_excess_cost"',
        "scale_atom_names_mismatch",
        "atom_scale_keys_mismatch",
        'EXPECTED_VALIDATED_DATASET_SHA256 = (',
        '"9dae6215f7b35cd142c37da80c92b38cac1263ee229a5ecb9c4e7c7cd4785018"',
    ]:
        assert needle in source


def test_preflight_decision_forbids_training_dp_and_promotion() -> None:
    source = _source()
    review = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        '"training_authorized": False',
        '"fallback_dataset_training_sufficiency_claim": False',
        '"camp_retraining_authorized_now": False',
        "for flag in FORBIDDEN_FLAGS",
        "status=fallback_risk_training_sufficiency_preflight_implemented",
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


def test_review_next_gate_is_training_split_manifest_plan_only() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_passed",
        "post_implementation_static_contract_review_complete=True",
        "implementation_hardening_completed=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan_only",
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_latest_head_revalidated",
        "may only plan the fallback-risk training split manifest",
        "must not train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
        "promote a selector or atom",
    ]:
        assert needle in text


def test_audit_tail_records_split_manifest_plan_as_next_gate() -> None:
    tail = "\n".join(AUDIT_DOC.read_text(encoding="utf-8").splitlines()[-120:])

    assert (
        "status=fallback_risk_training_split_manifest_builder_implementation_autodl_verification_passed"
        in tail
    )
    assert "implementation_complete=True" in tail
    assert "training_execution_authorized_now=False" in tail
    assert tail.rstrip().endswith(
        "`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_post_implementation_static_contract_only`"
    )
