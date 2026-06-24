from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_post_implementation_static_contract_review.md"
)
MATERIALIZER = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_validated_dataset_summary.py"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"


def _source() -> str:
    return MATERIALIZER.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def test_review_doc_records_materializer_static_contract() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "default_off_boundary_passed=True",
        "read_only_artifact_boundary_passed=True",
        "summary_shape_boundary_passed=True",
        "fail_closed_boundary_passed=True",
        "training_preflight_dp_boundary_passed=True",
        "blocking_contract_findings=0",
        "fixed_artifact_summary_materialization_authorized=False",
        "training_sufficiency_preflight_execution_authorized=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_materializer_is_default_off_before_reading_inputs() -> None:
    tree = _tree()
    source = _source()
    build = _function(tree, "build_validated_dataset_summary_report")

    enabled_index = build.args.kwonlyargs.index(
        next(arg for arg in build.args.kwonlyargs if arg.arg == "enabled")
    )
    enabled_default = build.args.kw_defaults[enabled_index]
    assert isinstance(enabled_default, ast.Constant)
    assert enabled_default.value is False

    disabled_return_index = None
    load_index = None
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
        if isinstance(node, ast.Assign) and "_load_json" in ast.unparse(node):
            load_index = index

    assert disabled_return_index is not None
    assert load_index is not None
    assert disabled_return_index < load_index
    assert "--enable_default_off_fallback_risk_training_validated_dataset_summary_materializer" in source
    assert "action=\"store_true\"" in source


def test_materializer_writes_only_explicit_outputs_and_uses_no_subprocess() -> None:
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

    assert write_receivers == ["args.output_md", "args.output_summary_json"]
    assert mkdir_receivers == ["args.output_md.parent", "args.output_summary_json.parent"]
    assert subprocess_calls == []


def test_materializer_fail_closed_checks_are_present() -> None:
    source = _source()

    for needle in [
        "dataset_sha256_mismatch",
        "validator_output_sha256_mismatch",
        "dataset_record_count_mismatch",
        "validator_records_checked_mismatch",
        "validator_failed_records_nonzero",
        "validator_status_not_complete",
        "validator_not_passed",
        "validator_errors_not_empty",
        "dataset_validator_record_count_mismatch",
        '"training_sufficiency_claim"',
        '"deployable_checkpoint_claim"',
        'f"{field}_leak"',
        'f"validator_{field}_leak"',
        "for flag in FORBIDDEN_FLAGS",
    ]:
        assert needle in source


def test_materializer_summary_shape_and_next_gate_are_pinned() -> None:
    source = _source()
    review = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")

    for needle in [
        '"schema_version": SUMMARY_SCHEMA_VERSION',
        '"sha256": dataset_sha',
        '"records": int(records)',
        '"validator_status": VALIDATOR_COMPLETE_STATUS',
        '"validator_passed": True',
        '"training_sufficiency_claim": False',
        '"deployable_checkpoint_claim": False',
        '"source_validator_output_sha256": validator_sha',
        '"training_sufficiency_preflight_executed": False',
        '"training_sufficiency_preflight_execution_authorized": False',
        '"training_authorized": False',
        '"camp_retraining_authorized_now": False',
        "status=fallback_risk_training_validated_dataset_summary_materializer_post_implementation_static_contract_passed",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_validated_dataset_summary_materializer_fixed_artifact_acceptance_audit_only",
    ]:
        assert needle in source + review + audit

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in review
