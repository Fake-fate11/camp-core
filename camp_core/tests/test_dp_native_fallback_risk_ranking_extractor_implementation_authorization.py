from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_implementation_authorization.md"
)
ITERATION_AUDIT = REPO_ROOT / "docs" / "diffusion_planner_v8_iteration_audit.md"
NEXT_IMPLEMENTATION_GATE = (
    "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_"
    "fixed_artifact_fallback_risk_ranking_default_off_extractor_implementation_only"
)


def test_extractor_implementation_authorization_preconditions() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")

    for needle in [
        "fixed_artifact_audit_passed=True",
        "lower_risk_fixed_candidate_exists_under_logged_costs=True",
        "remediation_design_plan_passed=True",
        "static_contract_review_passed=True",
        "blocking_contract_findings=0",
        "unit_tests_plan_ready=True",
        "default_off_contract_tests_pinned=True",
        "local_default_off_contract_pytest=5 passed",
        "autodl_default_off_contract_pytest=5 passed",
        "dp_fixed_commit_verified=True",
    ]:
        assert needle in text


def test_extractor_implementation_authorization_is_narrow_and_default_off() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")

    for needle in [
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "synthetic_unit_tests_required=True",
        "existing_contract_tests_must_continue_to_pass=True",
        "output_json_or_markdown_only=True",
        "may_add_read_only_script_or_helper=True",
        "may_add_targeted_synthetic_tests=True",
        "must_fail_closed_on_missing_required_fields=True",
        "must_preserve_score_k_equals_a_k_transpose_w_boundary=True",
    ]:
        assert needle in text


def test_extractor_implementation_authorization_keeps_training_forbidden() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")

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


def test_extractor_implementation_authorization_next_gate_implementation_only() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_implementation_only",
        "The next gate may only implement the minimal default-off read-only extractor",
        "It must not run replay",
        "train CAMP",
        "modify DP",
    ]:
        assert needle in text


def test_extractor_implementation_authorization_current_head_revalidation() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")
    tail = text.split(
        "## Current-Head Revalidation After 91d4327 Default-Off Unit Tests"
    )[-1]

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head",
        "camp_head_at_revalidation=950b0c829ec880b5feb5b5c7b863cd3c39f33664",
        "camp_origin_main_at_revalidation=950b0c829ec880b5feb5b5c7b863cd3c39f33664",
        "github_refs_heads_main_at_revalidation=950b0c829ec880b5feb5b5c7b863cd3c39f33664",
        "autodl_CAMP_HEAD_at_revalidation=950b0c829ec880b5feb5b5c7b863cd3c39f33664",
        "autodl_CAMP_origin_main_at_revalidation=950b0c829ec880b5feb5b5c7b863cd3c39f33664",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_status=fallback_risk_ranking_default_off_unit_tests_current_head_revalidated",
        "prior_unit_tests_head_at_revalidation=3512ae0e883952ff2342c8ea714fbcd811ac5b37",
        "camp_head_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "camp_origin_main_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "github_refs_heads_main_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "autodl_CAMP_HEAD_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "prior_unit_tests_head_at_revalidation=91d4327200995903d2a2bbf0b5545033a6ed9cd7",
        "prior_unit_tests_eof_tail_verified=True",
        "default_off_contract_tests_pinned=True",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "local_target_pytest=54 passed",
        "autodl_target_pytest=54 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
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


def test_iteration_audit_records_extractor_implementation_authorization() -> None:
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head",
        "authorization_doc=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_implementation_authorization.md",
        "authorization_test=camp_core/tests/test_dp_native_fallback_risk_ranking_extractor_implementation_authorization.py",
        "camp_head_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "camp_origin_main_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "github_refs_heads_main_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "autodl_CAMP_HEAD_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "autodl_CAMP_origin_main_at_revalidation=9d92c1bb2221d208ed2d035eb92b5c8f8f91c4ef",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_status=fallback_risk_ranking_default_off_unit_tests_current_head_revalidated",
        "prior_unit_tests_head_at_revalidation=91d4327200995903d2a2bbf0b5545033a6ed9cd7",
        "prior_unit_tests_eof_tail_verified=True",
        "default_off_contract_tests_pinned=True",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "local_target_pytest=54 passed",
        "autodl_target_pytest=54 passed",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_IMPLEMENTATION_GATE,
    ]:
        assert needle in audit

    assert f"`{NEXT_IMPLEMENTATION_GATE}`" in audit


def test_current_head_6c1625d_extractor_implementation_authorization_is_pinned() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head_6c1625d",
        "camp_head_at_revalidation=6c1625df44e9922988ec8a70150e0d26ae2c2a7f",
        "camp_origin_main_at_revalidation=6c1625df44e9922988ec8a70150e0d26ae2c2a7f",
        "github_refs_heads_main_at_revalidation=6c1625df44e9922988ec8a70150e0d26ae2c2a7f",
        "autodl_CAMP_HEAD_at_revalidation=6c1625df44e9922988ec8a70150e0d26ae2c2a7f",
        "autodl_CAMP_origin_main_at_revalidation=6c1625df44e9922988ec8a70150e0d26ae2c2a7f",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_status=fallback_risk_ranking_default_off_unit_tests_current_head_83b73af_revalidated",
        "prior_unit_tests_head_at_revalidation=83b73afb014188df67c524dd33cbab4a84abf411",
        "prior_unit_tests_eof_tail_verified=True",
        "default_off_contract_tests_pinned=True",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "synthetic_unit_tests_required=True",
        "existing_contract_tests_must_continue_to_pass=True",
        "output_json_or_markdown_only=True",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_IMPLEMENTATION_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head_6c1625d",
        "prior_unit_tests_head_at_revalidation=83b73afb014188df67c524dd33cbab4a84abf411",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_IMPLEMENTATION_GATE,
    ]:
        assert needle in audit


def test_current_head_1bc34fe_extractor_implementation_authorization_is_pinned() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head_1bc34fe",
        "camp_head_at_revalidation=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "camp_origin_main_at_revalidation=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "github_refs_heads_main_at_revalidation=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "autodl_CAMP_HEAD_at_revalidation=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "autodl_CAMP_origin_main_at_revalidation=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_status=fallback_risk_ranking_default_off_unit_tests_current_head_f6381dd_revalidated",
        "prior_unit_tests_head_at_revalidation=f6381dd743c47aaa07aaeff3c6372453b69da445",
        "prior_unit_tests_eof_tail_verified=True",
        "default_off_contract_tests_pinned=True",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "synthetic_unit_tests_required=True",
        "existing_contract_tests_must_continue_to_pass=True",
        "output_json_or_markdown_only=True",
        "local_py_compile_exit=0",
        "local_target_pytest=36 passed",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=36 passed",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_IMPLEMENTATION_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head_1bc34fe",
        "current_camp_head=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "github_refs_heads_main=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "autodl_CAMP_HEAD=1bc34fefffe58dff0b007ec70fceb32258c3ffa6",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_status=fallback_risk_ranking_default_off_unit_tests_current_head_f6381dd_revalidated",
        "prior_unit_tests_head_at_revalidation=f6381dd743c47aaa07aaeff3c6372453b69da445",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "local_target_pytest=36 passed",
        "autodl_target_pytest=36 passed",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_IMPLEMENTATION_GATE,
    ]:
        assert needle in audit


def test_current_head_47860dc_extractor_implementation_authorization_is_pinned() -> None:
    text = AUTH_DOC.read_text(encoding="utf-8")
    audit = ITERATION_AUDIT.read_text(encoding="utf-8")

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head_47860dc",
        "camp_head_at_revalidation=47860dca0835af5588eec95e5eb16cde13938cf1",
        "camp_origin_main_at_revalidation=47860dca0835af5588eec95e5eb16cde13938cf1",
        "github_refs_heads_main_at_revalidation=47860dca0835af5588eec95e5eb16cde13938cf1",
        "autodl_CAMP_HEAD_at_revalidation=47860dca0835af5588eec95e5eb16cde13938cf1",
        "autodl_CAMP_origin_main_at_revalidation=47860dca0835af5588eec95e5eb16cde13938cf1",
        "autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_status=fallback_risk_ranking_default_off_unit_tests_current_head_088ee39_revalidated",
        "prior_unit_tests_head_at_revalidation=088ee3948c43d238d346729f802e3946f3830f3a",
        "prior_unit_tests_eof_tail_verified=True",
        "default_off_contract_tests_pinned=True",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "records_scope=records_without_feasible_candidate_only",
        "synthetic_unit_tests_required=True",
        "existing_contract_tests_must_continue_to_pass=True",
        "output_json_or_markdown_only=True",
        "local_py_compile_exit=0",
        "local_target_pytest=9 passed",
        "autodl_py_compile_exit=0",
        "autodl_target_pytest=9 passed",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "fallback_risk_smoke_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "online_selector_change_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_IMPLEMENTATION_GATE,
    ]:
        assert needle in text

    for needle in [
        "status=fallback_risk_ranking_default_off_extractor_implementation_authorized_current_head_47860dc",
        "current_camp_head=47860dca0835af5588eec95e5eb16cde13938cf1",
        "github_refs_heads_main=47860dca0835af5588eec95e5eb16cde13938cf1",
        "autodl_CAMP_HEAD=47860dca0835af5588eec95e5eb16cde13938cf1",
        "autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4",
        "prior_unit_tests_status=fallback_risk_ranking_default_off_unit_tests_current_head_088ee39_revalidated",
        "prior_unit_tests_head_at_revalidation=088ee3948c43d238d346729f802e3946f3830f3a",
        "implementation_authorized=True",
        "fallback_risk_extractor_implementation_authorized=True",
        "default_off_required=True",
        "read_only_selection_log_input_only=True",
        "local_target_pytest=9 passed",
        "autodl_target_pytest=9 passed",
        "training_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        NEXT_IMPLEMENTATION_GATE,
    ]:
        assert needle in audit
