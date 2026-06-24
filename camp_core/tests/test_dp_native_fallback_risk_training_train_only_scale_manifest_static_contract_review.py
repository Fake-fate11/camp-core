from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_static_contract_review.md"
)
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_plan.md"
)
PREFLIGHT = (
    REPO_ROOT
    / "scripts"
    / "integrations"
    / "validate_dp_native_fallback_risk_training_sufficiency_preflight.py"
)


def _review() -> str:
    return REVIEW_DOC.read_text(encoding="utf-8")


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def _preflight() -> str:
    return PREFLIGHT.read_text(encoding="utf-8")


def test_scale_static_review_records_source_and_split_boundary() -> None:
    text = _review()
    plan = _plan()

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_plan_ready",
        "train_only_scale_manifest_builder_authorized=False",
    ]:
        assert needle in plan

    for needle in [
        "source_split_boundary_passed=True",
        "scale_manifest_input=existing_validated_fallback_risk_training_dataset_json_and_accepted_split_manifest_json_only",
        "accepted_split_training_records=13",
        "accepted_split_validation_records=2",
        "training_groups_disjoint_validation=True",
        "fit_groups_source=split_manifest.training_groups_only",
        "fit_records_scope=training_groups_only",
        "validation_groups_excluded_from_fit=True",
    ]:
        assert needle in text


def test_scale_static_review_records_leakage_and_formal_boundary() -> None:
    text = _review()

    for needle in [
        "leakage_formal_boundary_passed=True",
        "formal_seeds_11_12_13_excluded=True",
        "formal_eval_artifact_excluded=True",
        "scale_fit_uses_selected_index=False",
        "scale_fit_uses_candidate_rank=False",
        "scale_fit_uses_closed_loop_outcome=False",
        "scale_fit_uses_learned_weights=False",
        "candidate_generation_authorized=False",
        "replay_execution_authorized=False",
        "training_execution_authorized=False",
    ]:
        assert needle in text


def test_scale_static_review_records_atom_schema_and_positive_policy() -> None:
    text = _review()
    preflight = _preflight()

    for needle in [
        "atom_scale_policy_passed=True",
        "atom_schema_version=dp_camp_v10_14d",
        "atom_names_match_preflight_approved_14d_schema=True",
        "scale_policy=train_only_positive_finite_p95_or_one_v1",
        "scale_statistic=per_atom_training_group_positive_finite_p95",
        "scale_epsilon=1e-6",
        "all_zero_or_missing_training_atom_scale=1.0",
        "nonpositive_scales_rejected=True",
        "nonfinite_scales_rejected=True",
        "atom_schema_or_name_mismatch_rejected=True",
    ]:
        assert needle in text

    for atom in [
        "jerk_early",
        "jerk_late",
        "jerk_full",
        "rms_acceleration",
        "speed_limit_margin_0_0",
        "speed_limit_margin_0_5",
        "speed_limit_margin_1_0",
        "lane_deviation",
        "clearance",
        "progress_shortfall",
        "planned_red_light_cost",
        "planned_lateral_acceleration_cost",
        "red_stopping_margin_cost",
        "dp_prior_jerk_excess_cost",
    ]:
        assert atom in preflight


def test_scale_static_review_records_preflight_compatibility() -> None:
    text = _review()
    preflight = _preflight()

    for needle in [
        "preflight_compatibility_passed=True",
        "preflight_required_fields=fit_groups,fit_seeds,formal_eval_artifact_included,atom_schema_version,atom_names,atom_scales",
        "fit_groups_must_equal_split_training_groups=True",
        "excluded_validation_groups_must_equal_split_validation_groups=True",
        "formal_eval_artifact_included=False",
        "fit_seeds_formal_seeds_11_12_13_excluded=True",
        "atom_scales_strictly_positive=True",
    ]:
        assert needle in text

    for needle in [
        "scale_fit_groups_not_training_only",
        "scale_fit_validation_leak",
        "scale_fit_formal_seed_leak",
        "scale_fit_formal_eval_leak",
        "scale_atom_schema_mismatch",
        "scale_atom_names_mismatch",
        "atom_scale_keys_mismatch",
        "not_strictly_positive",
    ]:
        assert needle in preflight


def test_scale_static_review_records_findings_and_forbidden_boundaries() -> None:
    text = _review()

    for needle in [
        "blocking_contract_findings=0",
        "require_train_only_scale_manifest_unit_tests_plan=True",
        "require_default_off_scale_manifest_builder_authorization=True",
        "require_preflight_acceptance_after_scale_manifest_generation=True",
        "local_target_pytest=6 passed",
        "local_fallback_risk_related_pytest=252 passed",
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


def test_scale_static_review_next_gate_is_unit_tests_plan_only() -> None:
    text = _review()

    for needle in [
        "status=fallback_risk_training_train_only_scale_manifest_static_contract_review_passed",
        "passed=True",
        "static_contract_review_complete=True",
        "train_only_scale_manifest_builder_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_unit_tests_plan_only",
        "may only plan synthetic/static unit tests",
        "must not implement a scale builder",
        "fit scales",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text
