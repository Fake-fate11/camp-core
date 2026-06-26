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
    return ITERATION_AUDIT.read_text(encoding="utf-8")


def _source() -> str:
    return VALIDATOR_SCRIPT.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def test_implementation_doc_records_current_head_and_next_gate() -> None:
    text = _doc()

    for needle in [
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_93ddd14_revalidated",
        "implementation_validation_head=93ddd14b145f681a5773420645ff9b7326d16589",
        "github_refs_heads_main_at_validation=93ddd14b145f681a5773420645ff9b7326d16589",
        "autodl_CAMP_HEAD_at_validation=93ddd14b145f681a5773420645ff9b7326d16589",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_8ee65b2_revalidated",
        "validator_script=scripts/integrations/validate_dp_native_fallback_risk_training_data_contract.py",
        "production_validator_modified_in_this_gate=False",
        "implementation_already_present_at_head=True",
        "local_target_pytest=24 passed",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_edeec5b_revalidated",
        "implementation_validation_head=edeec5bbf1d56c1e054285e41cbbe90f5f01ec62",
        "github_refs_heads_main_at_validation=edeec5bbf1d56c1e054285e41cbbe90f5f01ec62",
        "autodl_CAMP_HEAD_at_validation=edeec5bbf1d56c1e054285e41cbbe90f5f01ec62",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_e5a7779_revalidated",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_5b12ce8_revalidated",
        "implementation_validation_head=5b12ce820d478430eeebc82474f384cd0b2eb47b",
        "github_refs_heads_main_at_validation=5b12ce820d478430eeebc82474f384cd0b2eb47b",
        "autodl_CAMP_HEAD_at_validation=5b12ce820d478430eeebc82474f384cd0b2eb47b",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_da9a7de_revalidated",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_4f7a782_revalidated",
        "implementation_validation_head=4f7a782c8d95fd3d4c2221955c2b7b9ac523ad52",
        "github_refs_heads_main_at_validation=4f7a782c8d95fd3d4c2221955c2b7b9ac523ad52",
        "autodl_CAMP_HEAD_at_validation=4f7a782c8d95fd3d4c2221955c2b7b9ac523ad52",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_bb7a534_revalidated",
        "autodl_target_pytest=24 passed",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_b14ce09_revalidated",
        "implementation_validation_head=b14ce09b0b05c13058d59b6b15cfa271ad856c80",
        "github_refs_heads_main_at_validation=b14ce09b0b05c13058d59b6b15cfa271ad856c80",
        "autodl_CAMP_HEAD_at_validation=b14ce09b0b05c13058d59b6b15cfa271ad856c80",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_b8ee682_revalidated",
        "local_target_pytest=26 passed",
        "autodl_target_pytest=26 passed",
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
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_edeec5b_revalidated",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_5b12ce8_revalidated",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_4f7a782_revalidated",
        "implementation_validation_head=5b12ce820d478430eeebc82474f384cd0b2eb47b",
        "implementation_validation_head=edeec5bbf1d56c1e054285e41cbbe90f5f01ec62",
        "implementation_validation_head=4f7a782c8d95fd3d4c2221955c2b7b9ac523ad52",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_bb7a534_revalidated",
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_b14ce09_revalidated",
        "implementation_validation_head=b14ce09b0b05c13058d59b6b15cfa271ad856c80",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_b8ee682_revalidated",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "production_validator_modified_in_this_gate=False",
        "default_off_required=True",
        "read_only_dataset_json_input_only=True",
        "source_log_readback_required_for_acceptance=True",
        "diffusion_planner_modified=False",
        "local_target_pytest=24 passed",
        "local_target_pytest=26 passed",
        "autodl_target_pytest=26 passed",
        "validator_extension_implementation_complete=True",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_post_implementation_static_contract_only",
    ]:
        assert needle in tail


def test_implementation_doc_eof_records_current_head_9cd9022() -> None:
    marker = "\n## Current-Head Implementation Revalidation After bff96df Authorization Sync\n\n"
    doc = _doc()
    assert marker in doc
    section = doc.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]

    for needle in [
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_9cd9022_revalidated",
        "implementation_validation_head=9cd90227e3689b5f6db84cecea562c05b82ee537",
        "camp_origin_main_at_validation=9cd90227e3689b5f6db84cecea562c05b82ee537",
        "github_refs_heads_main_at_validation=9cd90227e3689b5f6db84cecea562c05b82ee537",
        "autodl_CAMP_HEAD_at_validation=9cd90227e3689b5f6db84cecea562c05b82ee537",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_bff96df_revalidated",
        "validator_script=scripts/integrations/validate_dp_native_fallback_risk_training_data_contract.py",
        "production_validator_modified_in_this_gate=False",
        "implementation_already_present_at_head=True",
        "default_off_enable_flag=--enable_default_off_fallback_risk_training_data_validator",
        "source_log_readback_required_for_acceptance=True",
        "schema_status_count_and_hash_mismatch_fails_closed=True",
        "source_feasible_mask_any_true_or_non_bool_fails_closed=True",
        "candidate_generation_or_provenance_violation_fails_closed=True",
        "atom_schema_or_nonnegative_matrix_violation_fails_closed=True",
        "score_k_equals_a_k_transpose_w_boundary_preserved=True",
        "fallback_dataset_kept_separate_from_feasible_master=True",
        "diffusion_planner_modified=False",
        "local_target_pytest=32 passed",
        "autodl_target_pytest=32 passed",
        "validator_extension_implementation_complete=True",
        "fallback_risk_training_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_post_implementation_static_contract_only",
    ]:
        assert needle in section

    for forbidden in [
        "camp_training_authorized=True",
        "camp_retraining_authorized=True",
        "replay_execution_authorized=True",
        "candidate_generation_authorized=True",
        "dp_modification_authorized=True",
        "selector_promotion_authorized=True",
        "atom_promotion_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
        "fallback_risk_training_authorized_now=True",
    ]:
        assert forbidden not in section


def test_iteration_audit_eof_records_current_head_9cd9022_implementation() -> None:
    marker = (
        "\n## Current Tail Confirmation After 9cd9022 Fallback Risk Training "
        "Data Validator Extension Implementation\n\n"
    )
    audit = _tail()
    assert marker in audit
    section = audit.rsplit(marker, maxsplit=1)[-1].split("\n## ", maxsplit=1)[0]

    for needle in [
        "status=fallback_risk_training_data_validator_extension_implementation_current_head_9cd9022_revalidated",
        "implementation_validation_head=9cd90227e3689b5f6db84cecea562c05b82ee537",
        "latest_implementation_authorization_status=fallback_risk_training_data_validator_extension_implementation_authorization_current_head_bff96df_revalidated",
        "autodl_DP_HEAD_at_validation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "production_validator_modified_in_this_gate=False",
        "implementation_already_present_at_head=True",
        "default_off_required=True",
        "read_only_dataset_json_input_only=True",
        "source_log_readback_required_for_acceptance=True",
        "score_k_equals_a_k_transpose_w_boundary_preserved=True",
        "fallback_dataset_kept_separate_from_feasible_master=True",
        "diffusion_planner_modified=False",
        "local_target_pytest=32 passed",
        "autodl_target_pytest=32 passed",
        "validator_extension_implementation_complete=True",
        "fallback_risk_training_authorized_now=False",
        "training_execution_authorized_now=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_validator_extension_post_implementation_static_contract_only",
    ]:
        assert needle in section
