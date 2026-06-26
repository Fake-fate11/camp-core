from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_implementation_authorization.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_IMPLEMENTATION_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_training_data_default_off_builder_"
    "implementation_only"
)


def _text() -> str:
    return AUTH_DOC.read_text(encoding="utf-8")


def test_builder_implementation_authorization_preconditions() -> None:
    text = _text()

    for needle in [
        "training_data_design_plan_passed=True",
        "training_data_design_static_contract_review_passed=True",
        "builder_unit_tests_plan_ready=True",
        "builder_unit_tests_contract_pinned=True",
        "blocking_contract_findings=0",
        "local_builder_contract_pytest=5 passed",
        "local_fallback_risk_pytest=72 passed",
        "autodl_builder_contract_pytest=5 passed",
        "autodl_fallback_risk_pytest=72 passed",
        "dp_fixed_commit_verified=True",
    ]:
        assert needle in text


def test_builder_implementation_authorization_is_narrow_and_default_off() -> None:
    text = _text()

    for needle in [
        "implementation_authorized=True",
        "fallback_risk_training_data_builder_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "read_only_extractor_output_input_only=True",
        "synthetic_unit_tests_required=True",
        "existing_contract_tests_must_continue_to_pass=True",
        "records_scope=records_without_feasible_candidate_only",
        "dataset_schema_version=dp_native_fallback_risk_training_data_v1",
        "output_json_or_markdown_only=True",
        "may_add_read_only_script_or_helper=True",
        "may_add_targeted_synthetic_tests=True",
        "must_fail_closed_on_missing_required_fields=True",
        "must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
        "must_keep_fallback_dataset_separate_from_feasible_master=True",
    ]:
        assert needle in text


def test_builder_implementation_authorization_keeps_training_forbidden() -> None:
    text = _text()

    for needle in [
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "training_authorized=False",
        "replay_authorized=False",
        "candidate_generation_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "feasible_ranking_master_change_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "hard_feasibility_relaxation_authorized=False",
        "dp_modification_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
    ]:
        assert needle in text

    for forbidden in [
        "fallback_risk_training_authorized_now=True",
        "fallback_risk_smoke_authorized_now=True",
        "training_authorized=True",
        "replay_authorized=True",
        "candidate_generation_authorized=True",
        "production_selector_change_authorized=True",
        "dp_modification_authorized=True",
        "safety_benefit_claim_authorized=True",
        "camp_over_dp_top1_claim_authorized=True",
    ]:
        assert forbidden not in text


def test_builder_implementation_authorization_next_gate_implementation_only() -> None:
    text = _text()

    for needle in [
        "status=fallback_risk_training_data_default_off_builder_implementation_authorized",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_implementation_only",
        "The next gate may only implement the minimal default-off read-only builder",
        "It must not run replay",
        "train CAMP",
        "modify DP",
    ]:
        assert needle in text


def test_builder_implementation_authorization_records_current_head_revalidation() -> None:
    text = _text()

    current_head = "3ded8e3273445ee8d6a358bbc4825b52ab6694af"
    for needle in [
        f"camp_head_at_revalidation={current_head}",
        f"camp_origin_main_at_revalidation={current_head}",
        f"github_refs_heads_main_at_revalidation={current_head}",
        f"autodl_CAMP_HEAD_at_revalidation={current_head}",
        f"autodl_CAMP_origin_main_at_revalidation={current_head}",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_builder_unit_tests_status=fallback_risk_training_data_default_off_builder_unit_tests_autodl_verification_passed",
        "local_authorization_and_contract_pytest=10 passed",
        "blocking_contract_findings=0",
        "implementation_authorized=True",
        "fallback_risk_training_data_builder_implementation_authorized=True",
        "training_execution_authorized_now=False",
    ]:
        assert needle in text


def test_builder_implementation_authorization_records_latest_tail() -> None:
    text = _text()
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")
    current_head = "becb571aad6d87615f7aba318c26676cb731908c"
    marker = "\n## Current-Head Revalidation After becb571 Builder Unit Tests\n\nDate: 2026-06-26\n\n"

    for payload in (text, audit):
        assert marker in payload
        tail = payload.rsplit(marker, maxsplit=1)[-1]
        for needle in [
            "status=fallback_risk_training_data_default_off_builder_implementation_authorization_current_head_becb571_revalidated",
            "authorization_doc=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_default_off_builder_implementation_authorization.md",
            "authorization_test=camp_core/tests/test_dp_native_fallback_risk_training_data_builder_implementation_authorization.py",
            "contract_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder_contract.py",
            f"camp_head_at_revalidation={current_head}",
            f"camp_origin_main_at_revalidation={current_head}",
            f"github_refs_heads_main_at_revalidation={current_head}",
            f"autodl_CAMP_HEAD_at_revalidation={current_head}",
            f"autodl_CAMP_origin_main_at_revalidation={current_head}",
            "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "prior_builder_unit_tests_status=fallback_risk_training_data_default_off_builder_unit_tests_current_head_96911f0_revalidated",
            "prior_builder_unit_tests_commit_at_revalidation=becb571aad6d87615f7aba318c26676cb731908c",
            "prior_builder_unit_tests_tail_verified=True",
            "prior_builder_unit_tests_autodl_verified=True",
            "user_camp_retraining_permission_available_for_future_training_gate=True",
            "local_py_compile_exit=0",
            "local_target_pytest=21 passed",
            "local_diff_check=0 findings",
            f"autodl_CAMP_HEAD={current_head}",
            f"autodl_CAMP_origin_main={current_head}",
            "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
            "autodl_py_compile_exit=0",
            "autodl_target_pytest=21 passed",
            "autodl_diff_check=0 findings",
            "blocking_contract_findings=0",
            "implementation_authorized=True",
            "fallback_risk_training_data_builder_implementation_authorized=True",
            "fallback_risk_training_authorized_now=False",
            "fallback_risk_smoke_authorized_now=False",
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
            NEXT_IMPLEMENTATION_GATE,
        ]:
            assert needle in tail

        assert tail.rstrip().endswith(f"```text\n{NEXT_IMPLEMENTATION_GATE}\n```")
