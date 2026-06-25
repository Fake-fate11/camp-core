from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_implementation.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
VALIDATOR_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "validate_dp_native_fallback_risk_training_data_contract.py"
)


def _doc() -> str:
    return IMPLEMENTATION_DOC.read_text(encoding="utf-8")


def _tail() -> str:
    return ITERATION_AUDIT.read_text(encoding="utf-8")[-20000:]


def _source() -> str:
    return VALIDATOR_SCRIPT.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def test_implementation_doc_records_current_head_and_next_gate() -> None:
    text = _doc()

    for needle in [
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_40a6940_revalidated",
        "implementation_validation_head=40a6940e4dcc87314ce1e7c875f4853cb40ba621",
        "github_refs_heads_main_at_validation=40a6940e4dcc87314ce1e7c875f4853cb40ba621",
        "autodl_CAMP_HEAD_at_validation=40a6940e4dcc87314ce1e7c875f4853cb40ba621",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_autodl_verification_passed",
        "validator_script=scripts/integrations/validate_dp_native_fallback_risk_training_data_contract.py",
        "production_validator_modified_in_this_gate=False",
        "implementation_already_present_at_head=True",
        "local_target_pytest=24 passed",
        "status=fallback_risk_training_data_validator_extension_implementation_autodl_verification_passed",
        "github_pushed_commit=5d8d68db7cf13a5d03de41da708cc9543693dcca",
        "autodl_CAMP_HEAD_after_sync=5d8d68db7cf13a5d03de41da708cc9543693dcca",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=24 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_post_implementation_static_contract_only",
    ]:
        assert needle in text


def test_validator_script_is_default_off_and_output_only() -> None:
    source = _source()

    for needle in [
        "--enable_default_off_fallback_risk_training_data_validator",
        "default_off",
        "enabled=False",
        "args.output_json.write_text",
        "args.output_md.write_text",
        "dataset_json=args.dataset_json",
        "source_log_readback_required_for_acceptance",
    ]:
        assert needle in source


def test_validator_script_reports_no_execution_or_dp_modification() -> None:
    source = _source()

    for needle in [
        '"replay_executed": False',
        '"candidate_generation_executed": False',
        '"camp_training_executed": False',
        '"diffusion_planner_executed": False',
        '"diffusion_planner_modified": False',
        '"training_authorized=False"',
        '"candidate_generation_authorized=False"',
        '"dp_modification_authorized=False"',
    ]:
        assert needle in source


def test_validator_script_contains_fail_closed_contract_checks() -> None:
    tree = _tree()
    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    for name in [
        "_validate_top_level",
        "_validate_record",
        "_validate_source_readback",
        "_validate_generation",
        "_validate_provenance",
        "_validate_atoms",
        "_record_identity_hash",
    ]:
        assert name in function_names

    source = _source()
    for needle in [
        "dataset_schema_version_mismatch",
        "source_log_hash_mismatch",
        "source_feasible_mask_any_true",
        "source_feasible_mask_non_bool",
        "source_candidate_generation_schema_mismatch",
        "source_provenance_candidate_count_mismatch",
        "record_identity_hash_mismatch",
        "{prefix}_atoms_candidate_count_mismatch",
        '_validate_matrix(atoms, candidate_count, atom_dim, f"{prefix}_atoms")',
        '_validate_matrix(normalized, candidate_count, atom_dim, f"{prefix}_normalized_atoms")',
        "final_decision_{flag}_not_false",
    ]:
        assert needle in source


def test_iteration_audit_tail_records_implementation_gate() -> None:
    tail = _tail()

    for needle in [
        "Current Tail Confirmation After Current HEAD Fallback Risk Training Data Validator Extension Implementation",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_40a6940_revalidated",
        "implementation_validation_head=40a6940e4dcc87314ce1e7c875f4853cb40ba621",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "production_validator_modified_in_this_gate=False",
        "default_off_required=True",
        "read_only_dataset_json_input_only=True",
        "source_log_readback_required_for_acceptance=True",
        "diffusion_planner_modified=False",
        "local_target_pytest=24 passed",
        "validator_extension_implementation_complete=True",
        "status=fallback_risk_training_data_validator_extension_implementation_autodl_verification_passed",
        "github_pushed_commit=5d8d68db7cf13a5d03de41da708cc9543693dcca",
        "autodl_CAMP_HEAD_after_sync=5d8d68db7cf13a5d03de41da708cc9543693dcca",
        "autodl_DP_HEAD_after_sync=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "autodl_target_pytest_result=24 passed",
        "autodl_py_compile_exit=0",
        "autodl_git_diff_check_exit=0",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_post_implementation_static_contract_only",
    ]:
        assert needle in tail
