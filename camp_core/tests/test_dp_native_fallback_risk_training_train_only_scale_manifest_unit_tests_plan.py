from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_unit_tests_plan.md"
)


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_scale_unit_tests_plan_records_preconditions() -> None:
    text = _plan()

    for needle in [
        "train_only_scale_manifest_plan_ready=True",
        "train_only_scale_manifest_static_contract_review_passed=True",
        "blocking_contract_findings=0",
        "accepted_split_manifest_ready=True",
        "accepted_split_training_records=13",
        "accepted_split_validation_records=2",
        "training_groups_disjoint_validation=True",
        "train_only_scale_manifest_builder_authorized=False",
        "fallback_risk_training_authorized_now=False",
        "camp_retraining_authorized_now=False",
    ]:
        assert needle in text


def test_scale_unit_tests_plan_covers_default_off_and_fit_groups() -> None:
    text = _plan()

    for needle in [
        "test_default_off_scale_builder_requires_enable_flag=True",
        "test_disabled_mode_does_not_read_dataset_or_split_manifest=True",
        "test_enabled_mode_reads_existing_dataset_and_split_manifest_json_only=True",
        "test_output_is_json_and_markdown_only=True",
        "test_requires_accepted_split_manifest_sha256=True",
        "test_fit_groups_equal_split_training_groups=True",
        "test_excluded_validation_groups_equal_split_validation_groups=True",
        "test_rejects_training_validation_group_overlap=True",
        "test_rejects_dataset_record_not_in_split_manifest=True",
    ]:
        assert needle in text


def test_scale_unit_tests_plan_covers_leakage_and_formal_seed_rejections() -> None:
    text = _plan()

    for needle in [
        "test_rejects_fit_on_validation_groups=True",
        "test_rejects_fit_on_formal_seeds_11_12_13=True",
        "test_rejects_formal_eval_artifact_included=True",
        "test_rejects_selected_index_scale_feature=True",
        "test_rejects_candidate_rank_scale_feature=True",
        "test_rejects_closed_loop_outcome_scale_feature=True",
        "test_rejects_learned_weights_scale_feature=True",
    ]:
        assert needle in text


def test_scale_unit_tests_plan_covers_atom_scale_policy() -> None:
    text = _plan()

    for needle in [
        "test_requires_dp_camp_v10_14d_atom_schema=True",
        "test_requires_exact_14d_atom_names=True",
        "test_computes_positive_finite_training_only_p95_or_one_scales=True",
        "test_all_zero_or_missing_training_atom_scale_is_one=True",
        "test_rejects_nonpositive_scale=True",
        "test_rejects_nonfinite_scale=True",
        "test_rejects_missing_or_extra_atom_scale_key=True",
        "test_rejects_bool_atom_scale=True",
    ]:
        assert needle in text


def test_scale_unit_tests_plan_covers_preflight_compatibility_and_forbidden_execution() -> None:
    text = _plan()

    for needle in [
        "test_manifest_contains_preflight_required_fields=True",
        "test_preflight_accepts_clean_synthetic_scale_manifest_with_clean_split=True",
        "test_preflight_rejects_scale_fit_group_not_training_only=True",
        "test_preflight_rejects_scale_validation_leak=True",
        "test_preflight_rejects_scale_formal_seed_leak=True",
        "test_final_decision_never_authorizes_training=True",
        "test_rejects_replay_or_candidate_generation=True",
        "test_rejects_camp_training_or_retraining=True",
        "test_rejects_dp_weight_or_config_changes=True",
        "test_rejects_selector_or_atom_promotion=True",
        "test_rejects_safety_or_camp_over_dp_claim=True",
    ]:
        assert needle in text


def test_scale_unit_tests_plan_uses_synthetic_fixtures_only() -> None:
    text = _plan()

    for needle in [
        "synthetic_dataset_fixtures_only=True",
        "synthetic_split_manifest_fixtures_only=True",
        "fixed_autodl_artifact_required_for_unit_tests=False",
        "formal_seeds_11_12_13_used=False",
        "replay_required_for_unit_tests=False",
        "candidate_generation_required_for_unit_tests=False",
        "training_required_for_unit_tests=False",
        "dp_required_for_unit_tests=False",
    ]:
        assert needle in text


def test_scale_unit_tests_plan_forbids_training_dp_and_sets_next_gate() -> None:
    text = _plan()

    for needle in [
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "status=fallback_risk_training_train_only_scale_manifest_unit_tests_plan_ready",
        "train_only_scale_manifest_unit_tests_authorized=True",
        "train_only_scale_manifest_builder_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_unit_tests_only",
        "may only add synthetic/static unit tests",
        "must not implement a scale builder",
        "fit scales",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text
