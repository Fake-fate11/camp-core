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


def test_current_head_f474ee0_static_contract_revalidation_is_pinned() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_head_f474ee0_revalidated",
        "post_static_contract_base_head=f474ee068de666f450d37c66d1d5a9b53a4f3d8d",
        "camp_origin_main_at_post_static_contract=f474ee068de666f450d37c66d1d5a9b53a4f3d8d",
        "github_refs_heads_main_at_post_static_contract=f474ee068de666f450d37c66d1d5a9b53a4f3d8d",
        "autodl_CAMP_HEAD_at_post_static_contract=f474ee068de666f450d37c66d1d5a9b53a4f3d8d",
        "autodl_CAMP_origin_main_at_post_static_contract=f474ee068de666f450d37c66d1d5a9b53a4f3d8d",
        "autodl_DP_HEAD_at_post_static_contract=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_implementation_status=fallback_risk_training_sufficiency_preflight_implementation_head_be3b522_revalidated",
        "head_f474ee0_validated_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "head_f474ee0_expected_validated_dataset_sha256=79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0",
        "head_f474ee0_source_expected_sha_current=True",
        "head_f474ee0_default_off_boundary_passed=True",
        "head_f474ee0_read_only_manifest_boundary_passed=True",
        "head_f474ee0_training_sufficiency_boundary_passed=True",
        "head_f474ee0_affine_score_boundary_preserved=True",
        "head_f474ee0_approved_atom_names_match_dp_camp_v10_14d=True",
        "head_f474ee0_blocking_contract_findings=0",
        "head_f474ee0_local_target_pytest=37 passed",
        "head_f474ee0_training_not_executed=True",
        "head_f474ee0_candidate_generation_not_executed=True",
        "head_f474ee0_dp_not_modified=True",
        "head_f474ee0_selector_or_atom_not_promoted=True",
        "this_post_static_gate_authorizes_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_current_head_717aba9_static_contract_revalidation_is_pinned() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_head_717aba9_revalidated",
        "post_static_contract_base_head=717aba905f425aacbc4585e2461eafef8c3b8ee8",
        "camp_origin_main_at_post_static_contract=717aba905f425aacbc4585e2461eafef8c3b8ee8",
        "github_refs_heads_main_at_post_static_contract=717aba905f425aacbc4585e2461eafef8c3b8ee8",
        "autodl_CAMP_HEAD_at_post_static_contract=717aba905f425aacbc4585e2461eafef8c3b8ee8",
        "autodl_CAMP_origin_main_at_post_static_contract=717aba905f425aacbc4585e2461eafef8c3b8ee8",
        "autodl_DP_HEAD_at_post_static_contract=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_implementation_status=fallback_risk_training_sufficiency_preflight_implementation_head_9195b3c_revalidated",
        "head_717aba9_validated_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "head_717aba9_expected_validated_dataset_sha256=682d432f742d4ab68a262cf70955981bc1562cf1dbcf2ec094984a12fcd11498",
        "head_717aba9_source_expected_sha_current=True",
        "head_717aba9_default_off_boundary_passed=True",
        "head_717aba9_read_only_manifest_boundary_passed=True",
        "head_717aba9_training_sufficiency_boundary_passed=True",
        "head_717aba9_affine_score_boundary_preserved=True",
        "head_717aba9_approved_atom_names_match_dp_camp_v10_14d=True",
        "head_717aba9_blocking_contract_findings=0",
        "head_717aba9_local_post_static_contract_pytest=9 passed",
        "head_717aba9_local_target_pytest=45 passed",
        "head_717aba9_training_not_executed=True",
        "head_717aba9_candidate_generation_not_executed=True",
        "head_717aba9_dp_not_modified=True",
        "head_717aba9_selector_or_atom_not_promoted=True",
        "this_post_static_gate_authorizes_training_replay_dp_or_claims=False",
    ]:
        assert needle in text


def test_current_head_537c69c_static_contract_revalidation_is_pinned() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")
    audit_tail = AUDIT_DOC.read_text(encoding="utf-8")[-16000:]
    combined = text + audit_tail
    status = (
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_head_537c69c_revalidated"
    )

    for needle in [
        status,
        "post_static_contract_base_head=537c69cbe98cc0584543e2691d13751a0f4b1e84",
        "camp_origin_main_at_post_static_contract=537c69cbe98cc0584543e2691d13751a0f4b1e84",
        "github_refs_heads_main_at_post_static_contract=537c69cbe98cc0584543e2691d13751a0f4b1e84",
        "autodl_CAMP_HEAD_at_post_static_contract=537c69cbe98cc0584543e2691d13751a0f4b1e84",
        "autodl_CAMP_origin_main_at_post_static_contract=537c69cbe98cc0584543e2691d13751a0f4b1e84",
        "autodl_DP_HEAD_at_post_static_contract=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_implementation_status=fallback_risk_training_sufficiency_preflight_implementation_head_f77b4c1_revalidated",
        "head_537c69c_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_537c69c_expected_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_537c69c_source_expected_sha_current=True",
        "head_537c69c_default_off_boundary_passed=True",
        "head_537c69c_read_only_manifest_boundary_passed=True",
        "head_537c69c_training_sufficiency_boundary_passed=True",
        "head_537c69c_affine_score_boundary_preserved=True",
        "head_537c69c_score_k(w)=a_k^T w",
        "head_537c69c_a_k_fixed_before_weight_optimization=True",
        "head_537c69c_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_537c69c_approved_atom_names_match_dp_camp_v10_14d=True",
        "head_537c69c_blocking_contract_findings=0",
        "head_537c69c_local_preflight_pytest=7 passed",
        "head_537c69c_local_post_static_contract_pytest=10 passed",
        "head_537c69c_local_authorization_pytest=8 passed",
        "head_537c69c_local_training_sufficiency_contract_pytest=18 passed",
        "head_537c69c_local_unit_tests_plan_pytest=8 passed",
        "head_537c69c_local_target_pytest=51 passed",
        "head_537c69c_autodl_preflight_pytest=7 passed",
        "head_537c69c_autodl_post_static_contract_pytest=10 passed",
        "head_537c69c_autodl_authorization_pytest=8 passed",
        "head_537c69c_autodl_training_sufficiency_contract_pytest=18 passed",
        "head_537c69c_autodl_unit_tests_plan_pytest=8 passed",
        "head_537c69c_autodl_target_pytest=51 passed",
        "head_537c69c_training_not_executed=True",
        "head_537c69c_candidate_generation_not_executed=True",
        "head_537c69c_dp_not_modified=True",
        "head_537c69c_selector_or_atom_not_promoted=True",
        "this_post_static_gate_authorizes_training_replay_dp_or_claims=False",
        "head_537c69c_camp_training_authorized=False",
        "head_537c69c_camp_retraining_authorized=False",
        "head_537c69c_formal_seeds_11_12_13_authorized=False",
        "head_537c69c_safety_benefit_claim_authorized=False",
        "head_537c69c_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan_only",
    ]:
        assert needle in combined


def test_current_head_bdfc3dd_static_contract_revalidation_is_pinned() -> None:
    text = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    combined = text + audit
    status = (
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_head_bdfc3dd_revalidated"
    )

    assert status in audit

    for needle in [
        status,
        "post_static_contract_base_head=bdfc3dd6f416ee07f3d578fd777f217ea1b4f773",
        "camp_origin_main_at_post_static_contract=bdfc3dd6f416ee07f3d578fd777f217ea1b4f773",
        "github_refs_heads_main_at_post_static_contract=bdfc3dd6f416ee07f3d578fd777f217ea1b4f773",
        "autodl_CAMP_HEAD_at_post_static_contract=bdfc3dd6f416ee07f3d578fd777f217ea1b4f773",
        "autodl_CAMP_origin_main_at_post_static_contract=bdfc3dd6f416ee07f3d578fd777f217ea1b4f773",
        "autodl_DP_HEAD_at_post_static_contract=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_implementation_status=fallback_risk_training_sufficiency_preflight_implementation_head_8d867cc_revalidated",
        "head_bdfc3dd_expected_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_bdfc3dd_source_expected_sha_current=True",
        "head_bdfc3dd_default_off_boundary_passed=True",
        "head_bdfc3dd_read_only_manifest_boundary_passed=True",
        "head_bdfc3dd_training_sufficiency_boundary_passed=True",
        "head_bdfc3dd_affine_score_boundary_preserved=True",
        "head_bdfc3dd_score_k(w)=a_k^T w",
        "head_bdfc3dd_a_k_fixed_before_weight_optimization=True",
        "head_bdfc3dd_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_bdfc3dd_approved_atom_names_match_dp_camp_v10_14d=True",
        "head_bdfc3dd_blocking_contract_findings=0",
        "head_bdfc3dd_production_preflight_script_modified_in_this_gate=False",
        "head_bdfc3dd_local_post_static_contract_pytest=11 passed",
        "head_bdfc3dd_local_target_pytest=55 passed",
        "head_bdfc3dd_autodl_temp_worktree=/root/autodl-tmp/camp_core_preflight_post_static_bdfc3dd_verify_20260626T172043Z",
        "head_bdfc3dd_autodl_post_static_contract_pytest=11 passed",
        "head_bdfc3dd_autodl_target_pytest=55 passed",
        "head_bdfc3dd_training_not_executed=True",
        "head_bdfc3dd_candidate_generation_not_executed=True",
        "head_bdfc3dd_dp_not_modified=True",
        "head_bdfc3dd_selector_or_atom_not_promoted=True",
        "this_post_static_gate_authorizes_training_replay_dp_or_claims=False",
        "head_bdfc3dd_camp_training_authorized=False",
        "head_bdfc3dd_camp_retraining_authorized=False",
        "head_bdfc3dd_formal_seeds_11_12_13_authorized=False",
        "head_bdfc3dd_safety_benefit_claim_authorized=False",
        "head_bdfc3dd_camp_over_dp_top1_claim_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan_only",
    ]:
        assert needle in combined


def test_current_head_75cc265_static_contract_eof_revalidation_is_pinned() -> None:
    marker = "\n## Current Tail Confirmation After 75cc265 Fallback Risk Training Sufficiency Preflight Post-Implementation Static Contract Review\n\n"
    text = REVIEW_DOC.read_text(encoding="utf-8")
    audit = AUDIT_DOC.read_text(encoding="utf-8")
    assert marker in text
    assert marker in audit
    combined = (
        text.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]
        + audit.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]
    )

    for needle in [
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_head_75cc265_revalidated",
        "post_static_contract_base_head=75cc2659397fb9311853565cd43151218c20787b",
        "camp_origin_main_at_post_static_contract=75cc2659397fb9311853565cd43151218c20787b",
        "github_refs_heads_main_at_post_static_contract=75cc2659397fb9311853565cd43151218c20787b",
        "autodl_CAMP_HEAD_at_post_static_contract=75cc2659397fb9311853565cd43151218c20787b",
        "autodl_CAMP_origin_main_at_post_static_contract=75cc2659397fb9311853565cd43151218c20787b",
        "autodl_DP_HEAD_at_post_static_contract=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_implementation_status=fallback_risk_training_sufficiency_preflight_implementation_head_19b6ecc_revalidated",
        "preflight_script=scripts/integrations/validate_dp_native_fallback_risk_training_sufficiency_preflight.py",
        "preflight_tests=camp_core/tests/test_dp_native_fallback_risk_training_sufficiency_preflight.py",
        "review_test=camp_core/tests/test_dp_native_fallback_risk_training_sufficiency_preflight_post_implementation_static_contract.py",
        "authorization_tests=camp_core/tests/test_dp_native_fallback_risk_training_sufficiency_preflight_implementation_authorization.py",
        "contract_tests=camp_core/tests/test_dp_native_fallback_risk_training_data_training_sufficiency_contract.py",
        "head_75cc265_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_75cc265_expected_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36",
        "head_75cc265_source_expected_sha_current=True",
        "head_75cc265_default_off_boundary_passed=True",
        "head_75cc265_validate_training_sufficiency_preflight_enabled_default=False",
        "head_75cc265_enable_flag_required_before_reading_any_manifest=True",
        "head_75cc265_disabled_mode_returns_before_manifest_read=True",
        "head_75cc265_disabled_mode_reads_inputs=False",
        "head_75cc265_read_only_manifest_boundary_passed=True",
        "head_75cc265_enabled_input_source=existing_json_manifests_only",
        "head_75cc265_writes_only_explicit_output_json_and_output_md=True",
        "head_75cc265_subprocess_usage_found=False",
        "head_75cc265_training_command_execution_path_found=False",
        "head_75cc265_diffusion_planner_execution_path_found=False",
        "head_75cc265_candidate_generation_path_found=False",
        "head_75cc265_training_sufficiency_boundary_passed=True",
        "head_75cc265_preflight_implementation_is_not_training=True",
        "head_75cc265_ready_for_future_training_authorization_is_not_training_authorization=True",
        "head_75cc265_fallback_dataset_training_sufficiency_claim=False",
        "head_75cc265_affine_score_boundary_preserved=True",
        "head_75cc265_score_k(w)=a_k^T w",
        "head_75cc265_a_k_fixed_before_weight_optimization=True",
        "head_75cc265_a_k_nonnegative_benders_compatible_atoms_only=True",
        "head_75cc265_approved_atom_schema=dp_camp_v10_14d",
        "head_75cc265_approved_atom_names_match_dp_camp_v10_14d=True",
        "head_75cc265_approved_atom_name_count=14",
        "head_75cc265_blocking_contract_findings=0",
        "head_75cc265_production_preflight_script_modified_in_this_gate=False",
        "head_75cc265_local_preflight_pytest=9 passed",
        "head_75cc265_local_post_static_contract_pytest=12 passed",
        "head_75cc265_local_authorization_pytest=10 passed",
        "head_75cc265_local_training_sufficiency_contract_pytest=20 passed",
        "head_75cc265_local_unit_tests_plan_pytest=9 passed",
        "head_75cc265_local_target_pytest=60 passed",
        "head_75cc265_local_py_compile_exit=0",
        "head_75cc265_local_git_diff_check_exit=0",
        "head_75cc265_autodl_temp_worktree=/root/autodl-tmp/camp_core_preflight_post_static_75cc265_verify_20260627T083000Z",
        "head_75cc265_autodl_preflight_pytest=9 passed",
        "head_75cc265_autodl_post_static_contract_pytest=12 passed",
        "head_75cc265_autodl_authorization_pytest=10 passed",
        "head_75cc265_autodl_training_sufficiency_contract_pytest=20 passed",
        "head_75cc265_autodl_unit_tests_plan_pytest=9 passed",
        "head_75cc265_autodl_target_pytest=60 passed",
        "head_75cc265_autodl_py_compile_exit=0",
        "head_75cc265_autodl_git_diff_check_exit=0",
        "head_75cc265_training_not_executed=True",
        "head_75cc265_candidate_generation_not_executed=True",
        "head_75cc265_dp_not_modified=True",
        "head_75cc265_selector_or_atom_not_promoted=True",
        "this_post_static_gate_authorizes_training_replay_dp_or_claims=False",
        "head_75cc265_camp_training_authorized=False",
        "head_75cc265_camp_retraining_authorized=False",
        "head_75cc265_formal_seeds_11_12_13_authorized=False",
        "head_75cc265_safety_benefit_claim_authorized=False",
        "head_75cc265_camp_over_dp_top1_claim_authorized=False",
        "training_execution_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan_only",
    ]:
        assert needle in combined


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
        '"16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36"',
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


def test_audit_tail_records_current_split_manifest_plan_as_static_review_next() -> None:
    tail = "\n".join(AUDIT_DOC.read_text(encoding="utf-8").splitlines()[-320:])

    assert (
        "status=fallback_risk_training_sufficiency_preflight_post_implementation_static_contract_head_75cc265_revalidated"
        in tail
    )
    assert (
        "head_75cc265_expected_validated_dataset_sha256=16f74d494ec371f5d888eead946dbd448ad4375107da75f8e3dbcdd57435dc36"
        in tail
    )
    assert (
        "prior_implementation_status=fallback_risk_training_sufficiency_preflight_implementation_head_19b6ecc_revalidated"
        in tail
    )
    assert "training_execution_authorized_now=False" in tail
    assert (
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan_only"
        in tail
    )
