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
    current_head = "144fc1f0de7cc80bcdf494d6b7f78b974be05988"

    for needle in [
        "status=fallback_risk_training_data_default_off_builder_implementation_current_head_144fc1f_revalidated",
        "authorization_status=fallback_risk_training_data_default_off_builder_implementation_authorization_current_head_c1658a9_revalidated",
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
    current_head = "e568ce282352a64c38af8e904e8ba0b2db982f44"
    marker = "\n## Current-Head Revalidation After e568ce2 Implementation Authorization\n\nDate: 2026-06-26\n\n"

    for payload in (doc, audit):
        assert marker in payload
        section = payload.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]
        for needle in [
            "status=fallback_risk_training_data_default_off_builder_implementation_current_head_e568ce2_revalidated",
            f"camp_head_at_revalidation={current_head}",
            f"camp_origin_main_at_revalidation={current_head}",
            f"github_refs_heads_main_at_revalidation={current_head}",
            f"autodl_CAMP_HEAD_at_revalidation={current_head}",
            f"autodl_CAMP_origin_main_at_revalidation={current_head}",
            "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "authorization_status=fallback_risk_training_data_default_off_builder_implementation_authorization_current_head_dc85a9f_revalidated",
            "authorization_commit_at_revalidation=e568ce282352a64c38af8e904e8ba0b2db982f44",
            "user_camp_retraining_permission_available_for_future_training_gate=True",
            "implementation_required_now=False",
            "implementation_already_present=True",
            "production_builder_changed_in_this_gate=False",
            "local_py_compile_exit=0",
            "local_target_pytest=23 passed",
            "local_diff_check=0 findings",
            f"autodl_CAMP_HEAD={current_head}",
            f"autodl_CAMP_origin_main={current_head}",
            "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "autodl_py_compile_exit=0",
            "autodl_target_pytest=23 passed",
            "autodl_diff_check=0 findings",
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
            assert needle in section

        assert section.rstrip().endswith(f"`{NEXT_STATIC_CONTRACT_GATE}`")


def test_current_head_144fc1f_builder_implementation_is_pinned() -> None:
    doc = IMPLEMENTATION_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    current_head = "144fc1f0de7cc80bcdf494d6b7f78b974be05988"
    marker = "\n## Current-Head Revalidation After 144fc1f Implementation Authorization\n\nDate: 2026-06-27\n\n"

    for payload in (doc, audit):
        assert marker in payload
        section = payload.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]
        for needle in [
            "status=fallback_risk_training_data_default_off_builder_implementation_current_head_144fc1f_revalidated",
            "builder=scripts/integrations/build_diffusion_planner_dp_native_fallback_risk_training_data.py",
            "behavior_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder.py",
            "contract_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder_contract.py",
            "implementation_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder_implementation.py",
            "authorization_status=fallback_risk_training_data_default_off_builder_implementation_authorization_current_head_c1658a9_revalidated",
            f"authorization_commit_at_revalidation={current_head}",
            "user_camp_retraining_permission_available_for_future_training_gate=True",
            f"camp_head_at_revalidation={current_head}",
            f"camp_origin_main_at_revalidation={current_head}",
            f"github_refs_heads_main_at_revalidation={current_head}",
            f"autodl_CAMP_HEAD_at_revalidation={current_head}",
            f"autodl_CAMP_origin_main_at_revalidation={current_head}",
            "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "implementation_required_now=False",
            "implementation_already_present=True",
            "production_builder_changed_in_this_gate=False",
            "blocking_contract_findings=0",
            "local_py_compile_exit=0",
            "local_target_pytest=7 passed",
            "local_diff_check=0 findings",
            f"autodl_CAMP_HEAD={current_head}",
            f"autodl_CAMP_origin_main={current_head}",
            "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "autodl_py_compile_exit=0",
            "autodl_target_pytest=7 passed",
            "autodl_diff_check=0 findings",
            "default_off_required=True",
            "enabled_default=False",
            "enable_flag_required_before_reading_selection_logs=True",
            "disabled_mode_reads_selection_logs=False",
            "disabled_mode_emits_records=False",
            "read_only_selection_log_input_only=True",
            "read_only_extractor_output_input_only=True",
            "records_scope=records_without_feasible_candidate_only",
            "dataset_schema_version=dp_native_fallback_risk_training_data_v1",
            "output_json_or_markdown_only=True",
            "writes_only_explicit_output_json_and_output_md=True",
            "subprocess_usage_found=False",
            "score_k(w)=a_k^T w",
            "affine_score_boundary_preserved=True",
            "fallback_dataset_separate_from_feasible_master=True",
            "all_infeasible_records_added_to_feasible_training=False",
            "feasible_ranking_master_change_authorized=False",
            "hard_feasibility_relaxation_authorized=False",
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
            NEXT_STATIC_CONTRACT_GATE,
        ]:
            assert needle in section

        assert section.rstrip().endswith(f"`{NEXT_STATIC_CONTRACT_GATE}`")


def test_current_head_2bf3740_builder_implementation_is_pinned() -> None:
    doc = IMPLEMENTATION_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    current_head = "2bf3740152323e8b9c50a7319b586d8a4291f1dd"
    marker = "\n## Current-Head Revalidation After 2bf3740 Implementation Authorization\n\nDate: 2026-06-26\n\n"

    for payload in (doc, audit):
        assert marker in payload
        section = payload.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]
        for needle in [
            "status=fallback_risk_training_data_default_off_builder_implementation_current_head_2bf3740_revalidated",
            "builder=scripts/integrations/build_diffusion_planner_dp_native_fallback_risk_training_data.py",
            "behavior_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder.py",
            "contract_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder_contract.py",
            "implementation_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder_implementation.py",
            "authorization_status=fallback_risk_training_data_default_off_builder_implementation_authorization_current_head_3a59d3a_revalidated",
            f"authorization_commit_at_revalidation={current_head}",
            "user_camp_retraining_permission_available_for_future_training_gate=True",
            f"camp_head_at_revalidation={current_head}",
            f"camp_origin_main_at_revalidation={current_head}",
            f"github_refs_heads_main_at_revalidation={current_head}",
            f"autodl_CAMP_HEAD_at_revalidation={current_head}",
            f"autodl_CAMP_origin_main_at_revalidation={current_head}",
            "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "implementation_required_now=False",
            "implementation_already_present=True",
            "production_builder_changed_in_this_gate=False",
            "blocking_contract_findings=0",
            "local_py_compile_exit=0",
            "local_target_pytest=26 passed",
            "local_diff_check=0 findings",
            f"autodl_CAMP_HEAD={current_head}",
            f"autodl_CAMP_origin_main={current_head}",
            "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "autodl_py_compile_exit=0",
            "autodl_target_pytest=26 passed",
            "autodl_diff_check=0 findings",
            "default_off_required=True",
            "enabled_default=False",
            "enable_flag_required_before_reading_selection_logs=True",
            "read_only_selection_log_input_only=True",
            "read_only_extractor_output_input_only=True",
            "records_scope=records_without_feasible_candidate_only",
            "dataset_schema_version=dp_native_fallback_risk_training_data_v1",
            "output_json_or_markdown_only=True",
            "writes_only_explicit_output_json_and_output_md=True",
            "subprocess_usage_found=False",
            "score_k(w)=a_k^T w",
            "affine_score_boundary_preserved=True",
            "fallback_dataset_separate_from_feasible_master=True",
            "all_infeasible_records_added_to_feasible_training=False",
            "feasible_ranking_master_change_authorized=False",
            "hard_feasibility_relaxation_authorized=False",
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
            NEXT_STATIC_CONTRACT_GATE,
        ]:
            assert needle in section

        assert NEXT_STATIC_CONTRACT_GATE in section
