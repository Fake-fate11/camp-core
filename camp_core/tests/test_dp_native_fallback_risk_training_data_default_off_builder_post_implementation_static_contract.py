from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_post_implementation_static_contract_review.md"
)
AUDIT_DOC = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
BUILDER = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_data.py"
)
NEXT_FIXED_ARTIFACT_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_default_off_builder_"
    "fixed_artifact_acceptance_audit_only"
)
CURRENT_HEAD = "7dfa9d900f8d5cd219f8a54c5774d87be501e6a2"
MARKER = (
    "\n## Current-Head Revalidation After 7dfa9d9 Builder Implementation"
    "\n\nDate: 2026-06-27\n\n"
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


def _latest_sections() -> list[str]:
    sections = []
    for path in (REVIEW_DOC, AUDIT_DOC):
        payload = path.read_text(encoding="utf-8")
        assert MARKER in payload
        sections.append(payload.rsplit(MARKER, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0])
    return sections


def test_current_head_post_static_contract_revalidation_is_pinned() -> None:
    for section in _latest_sections():
        for needle in [
            "status=fallback_risk_training_data_default_off_builder_post_implementation_static_contract_current_head_7dfa9d9_revalidated",
            "passed=True",
            f"camp_head_at_current_head_revalidation={CURRENT_HEAD}",
            f"camp_origin_main_at_current_head_revalidation={CURRENT_HEAD}",
            f"github_refs_heads_main_at_current_head_revalidation={CURRENT_HEAD}",
            f"autodl_CAMP_HEAD_at_current_head_revalidation={CURRENT_HEAD}",
            f"autodl_CAMP_origin_main_at_current_head_revalidation={CURRENT_HEAD}",
            "autodl_DP_HEAD_at_current_head_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "prior_builder_implementation_status=fallback_risk_training_data_default_off_builder_implementation_current_head_144fc1f_revalidated",
            f"prior_builder_implementation_commit_at_revalidation={CURRENT_HEAD}",
            "prior_builder_implementation_tail_verified=True",
            "prior_builder_implementation_autodl_verified=True",
            "user_camp_retraining_permission_available_for_future_training_gate=True",
            "local_py_compile_exit=0",
            "local_target_pytest=6 passed",
            "local_related_target_pytest=46 passed",
            "local_diff_check=0 findings",
            f"autodl_CAMP_HEAD={CURRENT_HEAD}",
            f"autodl_CAMP_origin_main={CURRENT_HEAD}",
            "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "autodl_py_compile_exit=0",
            "autodl_target_pytest=6 passed",
            "autodl_related_target_pytest=46 passed",
            "autodl_diff_check=0 findings",
            "post_implementation_static_contract_review_complete=True",
            "blocking_contract_findings=0",
            "default_off_boundary_passed=True",
            "read_only_fixed_artifact_boundary_passed=True",
            "affine_score_boundary_preserved=True",
            "training_sufficiency_boundary_passed=True",
            "fixed_artifact_acceptance_audit_authorized_next=True",
            "this_static_contract_gate_authorizes_broad_execution=False",
            NEXT_FIXED_ARTIFACT_GATE,
        ]:
            assert needle in section


def test_builder_is_default_off_before_reading_fixed_artifact_inputs() -> None:
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
    selection_log_loop_index = None
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
        if isinstance(node, ast.For) and ast.unparse(node.iter) == "selection_logs":
            selection_log_loop_index = index

    assert disabled_return_index is not None
    assert selection_log_loop_index is not None
    assert disabled_return_index < selection_log_loop_index
    assert "--enable_default_off_fallback_risk_training_data_builder" in source
    assert "action=\"store_true\"" in source


def test_builder_writes_only_explicit_reports_and_uses_no_subprocess() -> None:
    write_receivers = []
    mkdir_receivers = []
    subprocess_calls = []

    for node in ast.walk(_tree()):
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


def test_static_review_pins_fail_closed_fixed_candidate_contracts() -> None:
    source = _source()
    combined = source + REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "_as_bool_list(record.get(\"feasible_mask\"))",
        "if any(feasible):",
        "errors.append(\"margin_scale_invalid\")",
        "errors.append(\"margin_clip_invalid\")",
        "extractor_json_not_passed",
        "candidate_generation_contract_schema_mismatch",
        "candidate_generation_contract_reference_blend_enabled",
        "candidate_generation_contract_guidance_enabled",
        "candidate_generation_contract_changes_dp_weights",
        "pre_post_tensor_hash_equal",
        "no_coordinate_heading_speed_rewrite_by_camp",
        "atom_schema_for_dimension(atom_dim)",
        "number < 0.0",
        "record_identity_hash",
        "score_k(w)=a_k^T w",
        "all_infeasible_records_added_to_feasible_training=False",
    ]:
        assert needle in combined


def test_static_review_forbids_training_dp_and_promotion() -> None:
    source = _source()
    for section in _latest_sections():
        combined = source + section
        for needle in [
            '"training_authorized": False',
            '"production_selector_change_authorized": False',
            '"online_selector_change_authorized": False',
            '"feasible_ranking_master_change_authorized": False',
            '"all_infeasible_records_added_to_feasible_training": False',
            '"hard_feasibility_relaxation_authorized": False',
            "for flag in FORBIDDEN_FLAGS",
            "fallback_risk_training_authorized_now=False",
            "training_execution_authorized_now=False",
            "camp_training_authorized=False",
            "camp_retraining_authorized=False",
            "replay_execution_authorized=False",
            "candidate_generation_authorized=False",
            "dp_modification_authorized=False",
            "selector_promotion_authorized=False",
            "atom_promotion_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
        ]:
            assert needle in combined

        for forbidden in [
            "fallback_risk_training_authorized_now=True",
            "training_execution_authorized_now=True",
            "camp_training_authorized=True",
            "camp_retraining_authorized=True",
            "candidate_generation_authorized=True",
            "dp_modification_authorized=True",
            "selector_promotion_authorized=True",
            "atom_promotion_authorized=True",
            "safety_benefit_claim_authorized=True",
            "camp_over_dp_top1_claim_authorized=True",
        ]:
            assert forbidden not in section


def test_next_gate_is_fixed_artifact_acceptance_audit_only() -> None:
    review = REVIEW_DOC.read_text(encoding="utf-8")
    for section in _latest_sections():
        assert section.rstrip().endswith(f"`{NEXT_FIXED_ARTIFACT_GATE}`")

    for needle in [
        NEXT_FIXED_ARTIFACT_GATE,
        "The next gate may only run the default-off builder",
        "existing non-formal fixed-artifact selection logs",
        "must not run replay",
        "generate candidates",
        "train CAMP",
        "modify Diffusion Planner",
        "use formal seeds",
        "relax hard feasibility",
        "all-infeasible records",
        "feasible-ranking master",
        "promote a selector or atom",
        "safety/CAMP-over-DP benefit",
    ]:
        assert needle in review
