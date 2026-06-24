from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_implementation_authorization.md"
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
