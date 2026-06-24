from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_DOC = (
    REPO_ROOT
    / "docs"
    / "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_plan.md"
)


def _plan() -> str:
    return PLAN_DOC.read_text(encoding="utf-8")


def test_split_manifest_plan_records_validated_dataset_and_no_generation() -> None:
    text = _plan()

    for needle in [
        "validated_fallback_dataset_sha256=1a7593ad2ef4eb138187e56635c597e4537f4533e7033936acf6801a1108e9bf",
        "validated_fallback_records=15",
        "manifest_input=existing_validated_fallback_risk_training_dataset_json_only",
        "records_scope=records_without_feasible_candidate_only",
        "candidate_generation_authorized=False",
        "replay_execution_authorized=False",
        "training_execution_authorized=False",
    ]:
        assert needle in text


def test_split_manifest_plan_defines_group_identity_and_forbidden_split_features() -> None:
    text = _plan()

    for needle in [
        "group_key_fields=source_log,run_id,record_index",
        "split_units=record_identity_groups",
        "training_groups_disjoint_from_validation_groups=True",
        "required_record_fields=source_log,source_log_sha256,run_id,record_index,candidate_count,oracle_index",
        "record_identity_hash_required=True",
        "selected_index_used_as_split_feature=False",
        "candidate_rank_used_as_split_feature=False",
        "closed_loop_outcome_used_as_split_feature=False",
    ]:
        assert needle in text


def test_split_manifest_plan_predeclares_deterministic_policy_and_small_data_boundary() -> None:
    text = _plan()

    for needle in [
        "split_policy=sha256(record_identity_hash + split_salt)",
        "split_salt=fallback_risk_training_split_v1",
        "validation_fraction_target=0.2",
        "min_validation_groups=1",
        "min_training_groups=1",
        "group_collision_fails_closed=True",
        "empty_train_or_validation_fails_closed=True",
        "fixed_15_record_artifact_training_sufficiency_claim=False",
    ]:
        assert needle in text


def test_split_manifest_plan_requires_default_off_builder_and_preflight_fields() -> None:
    text = _plan()

    for needle in [
        "default_off_builder_required=True",
        "enable_flag_required=True",
        "disabled_mode_reads_dataset=False",
        "output_json_or_markdown_only=True",
        "training_split_manifest_json_required=True",
        "preflight_compatible_fields_required=True",
        "top_level_fields=schema_version,dataset_sha256,validator_output_sha256,split_policy,split_salt,group_key_fields,training_groups,validation_groups,record_assignments,record_counts,final_decision",
    ]:
        assert needle in text


def test_split_manifest_plan_forbids_training_dp_and_claims() -> None:
    text = _plan()

    for needle in [
        "camp_training_authorized=False",
        "camp_retraining_authorized=False",
        "formal_seeds_11_12_13_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "all_infeasible_records_added_to_feasible_training=False",
    ]:
        assert needle in text


def test_split_manifest_plan_next_gate_is_static_review_only() -> None:
    text = _plan()

    for needle in [
        "status=fallback_risk_training_split_manifest_plan_ready",
        "training_split_manifest_plan_complete=True",
        "training_split_manifest_builder_authorized=False",
        "dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_split_manifest_static_contract_review_only",
        "may only statically review this split manifest plan",
        "must not",
        "generate the manifest",
        "train CAMP",
        "modify Diffusion Planner",
    ]:
        assert needle in text
