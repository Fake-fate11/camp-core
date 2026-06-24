from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_legacy_decision_flag_remediation_post_implementation_static_contract_review.md"
)
SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "build_diffusion_planner_dp_native_fallback_risk_training_split_manifest.py"
)
BUILDER_TEST = (
    REPO_ROOT
    / "camp_core"
    / "tests"
    / "test_dp_native_fallback_risk_training_split_manifest_builder.py"
)


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def _script() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _builder_test() -> str:
    return BUILDER_TEST.read_text(encoding="utf-8")


def test_remediation_post_static_review_records_contract_boundary() -> None:
    text = _review()

    for needle in [
        "legacy_missing_flag_compatibility_passed=True",
        "absent_legacy_final_decision_forbidden_flags_treated_as_false=True",
        "explicit_true_forbidden_flags_rejected=True",
        "present_non_false_forbidden_flags_rejected=True",
        "scope_limited_to_input_dataset_final_decision_validation=True",
        "output_final_decision_forbidden_flags_remain_false=True",
        "fixed_artifact_acceptance_rerun_authorized=False",
        "training_split_manifest_ready_for_preflight=False",
        "blocking_contract_findings=0",
    ]:
        assert needle in text


def test_remediation_post_static_review_matches_implementation_and_tests() -> None:
    script = _script()
    tests = _builder_test()

    assert "if flag in decision and decision.get(flag) is not False:" in script

    for needle in [
        "test_split_builder_accepts_missing_legacy_final_decision_forbidden_flag",
        "payload[\"final_decision\"].pop(\"fallback_risk_training_authorized_now\")",
        "test_split_builder_rejects_explicit_true_or_nonfalse_forbidden_flags",
        "true_payload[\"final_decision\"][\"fallback_risk_training_authorized_now\"] = True",
        "nonfalse_payload[\"final_decision\"][\"candidate_generation_authorized\"] = \"false\"",
        "final_decision_fallback_risk_training_authorized_now_not_false",
        "final_decision_candidate_generation_authorized_not_false",
    ]:
        assert needle in tests


def test_remediation_post_static_review_records_verification() -> None:
    text = _review()

    for needle in [
        "local_py_compile_exit=0",
        "local_target_pytest=8 passed",
        "local_fallback_risk_related_pytest=235 passed",
        "autodl_target_pytest=8 passed",
        "autodl_fallback_risk_related_pytest=235 passed",
    ]:
        assert needle in text


def test_remediation_post_static_review_keeps_forbidden_boundaries() -> None:
    text = _review()

    for needle in [
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_remediation_post_static_review_next_gate_is_acceptance_rerun_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_split_manifest_builder_legacy_decision_flag_remediation_post_implementation_static_contract_passed",
        "passed=True",
        "static_contract_review_complete=True",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_builder_fixed_artifact_acceptance_rerun_audit_only",
        "may only rerun the default-off split manifest builder",
        "same existing validated fixed artifact",
        "must not",
        "train CAMP",
        "run replay",
        "generate candidates",
        "modify Diffusion Planner",
    ]:
        assert needle in text
