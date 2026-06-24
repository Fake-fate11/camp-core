from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_plan.md"
)


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_train_only_scale_plan_records_accepted_split_inputs() -> None:
    text = _plan()

    for needle in [
        "accepted_split_manifest_json=/root/autodl-tmp/camp_dp_native_fallback_risk_training_split_manifest_builder_acceptance_384c2b7_20260624T154419Z/split_manifest.json",
        "accepted_split_manifest_json_sha256=a4b33c1c14b2ea96f1994e89245cfd27209e98049808fdfd3fbe6c8a732d34fd",
        "source_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validator_output_json_sha256=572888123f53ebe6921a5e9a6fb920c2e425e5a1e578a259d0ce03f76a85a44b",
        "split_training_records=13",
        "split_validation_records=2",
        "training_groups_disjoint_validation=True",
    ]:
        assert needle in text


def test_train_only_scale_plan_scopes_fit_to_training_groups_only() -> None:
    text = _plan()

    for needle in [
        "manifest_schema_version=dp_native_fallback_risk_train_only_scale_manifest_v1",
        "scale_manifest_input=existing_validated_fallback_risk_training_dataset_json_and_accepted_split_manifest_json_only",
        "fit_groups_source=split_manifest.training_groups_only",
        "fit_records_scope=training_groups_only",
        "validation_groups_excluded_from_fit=True",
        "formal_seeds_11_12_13_excluded=True",
        "formal_eval_artifact_excluded=True",
        "fit_groups_must_equal_split_training_groups=True",
        "excluded_validation_groups_must_equal_split_validation_groups=True",
    ]:
        assert needle in text


def test_train_only_scale_plan_forbids_outcome_and_weight_leakage() -> None:
    text = _plan()

    for needle in [
        "scale_fit_uses_selected_index=False",
        "scale_fit_uses_candidate_rank=False",
        "scale_fit_uses_closed_loop_outcome=False",
        "scale_fit_uses_learned_weights=False",
        "candidate_generation_authorized=False",
        "replay_execution_authorized=False",
        "training_execution_authorized=False",
    ]:
        assert needle in text


def test_train_only_scale_plan_pins_atom_schema_and_positive_policy() -> None:
    text = _plan()

    for needle in [
        "atom_schema_version=dp_camp_v10_14d",
        "atom_names=jerk_early,jerk_late,jerk_full,rms_acceleration,speed_limit_margin_0_0,speed_limit_margin_0_5,speed_limit_margin_1_0,lane_deviation,clearance,progress_shortfall,planned_red_light_cost,planned_lateral_acceleration_cost,red_stopping_margin_cost,dp_prior_jerk_excess_cost",
        "scale_policy=train_only_positive_finite_p95_or_one_v1",
        "scale_statistic=per_atom_training_group_positive_finite_p95",
        "scale_epsilon=1e-6",
        "all_zero_or_missing_training_atom_scale=1.0",
        "nonpositive_scales_rejected=True",
        "nonfinite_scales_rejected=True",
        "atom_schema_or_name_mismatch_rejected=True",
    ]:
        assert needle in text


def test_train_only_scale_plan_defines_default_off_output_contract() -> None:
    text = _plan()

    for needle in [
        "default_off_builder_required=True",
        "enable_flag_required=True",
        "disabled_mode_reads_dataset_or_split_manifest=False",
        "output_json_or_markdown_only=True",
        "train_only_scale_manifest_json_required=True",
        "preflight_compatible_fields_required=True",
        "preflight_required_fields=fit_groups,fit_seeds,formal_eval_artifact_included,atom_schema_version,atom_names,atom_scales",
        "formal_eval_artifact_included=False",
        "fit_seeds_formal_seeds_11_12_13_excluded=True",
        "atom_scales_strictly_positive=True",
    ]:
        assert needle in text


def test_train_only_scale_plan_forbids_training_dp_and_claims_and_sets_next_gate() -> None:
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
        "fixed_15_record_artifact_training_sufficiency_claim=False",
        "local_target_pytest=6 passed",
        "local_fallback_risk_related_pytest=246 passed",
        "status=fallback_risk_training_train_only_scale_manifest_plan_ready",
        "train_only_scale_manifest_builder_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_train_only_scale_manifest_static_contract_review_only",
        "may only statically review this train-only scale manifest plan",
        "must not implement a scale builder",
        "fit scales",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text
