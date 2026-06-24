# DP Native Fixed-Artifact Fallback Risk Training Data Design Plan

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_plan_only
```

This plan defines the offline data contract for a possible future
all-infeasible fallback-risk training path. It does not implement a dataset
builder, run replay, generate candidates, train CAMP, retrain CAMP, modify
Diffusion Planner, change the online selector, promote a selector or atom, or
claim safety benefit or CAMP-over-DP Top-1.

## Inputs

```text
fallback_risk_audit=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_audit.md
fallback_risk_extractor=scripts/integrations/extract_diffusion_planner_dp_native_fallback_risk_records.py
extractor_static_contract=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_default_off_extractor_post_implementation_static_contract_review.md
clean_training_data_validator=scripts/integrations/validate_dp_native_training_data_contract.py
mathematical_contract=docs/dp_camp_mathematical_contract.md
benders_formalization=docs/dp_camp_benders_formalization.md
atom_audit=docs/dp_camp_benders_compatible_atom_audit.md
camp_head_at_plan=3fb86a79d8103873e3662c952857d389130f1178
camp_origin_main_at_plan=3fb86a79d8103873e3662c952857d389130f1178
github_refs_heads_main_at_plan=3fb86a79d8103873e3662c952857d389130f1178
autodl_CAMP_HEAD_at_plan=3fb86a79d8103873e3662c952857d389130f1178
autodl_CAMP_origin_main_at_plan=3fb86a79d8103873e3662c952857d389130f1178
autodl_DP_HEAD_at_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The current fixed artifact is useful for contract design but is not sufficient
to authorize training:

```text
fixed_artifact_records_without_feasible_candidate=15
fixed_artifact_training_sufficiency_claim=False
fallback_risk_training_authorized_now=False
```

## Dataset Scope

The fallback-risk dataset, if later implemented, must be a separate
all-infeasible fallback track:

```text
dataset_schema_version=dp_native_fallback_risk_training_data_v1
records_scope=records_without_feasible_candidate_only
source_logs=existing_camp_selection_log_json_only
source_extractor_records=default_off_fallback_risk_extractor_output_only
fixed_candidate_set_only=True
feasible_branch_records_allowed=False
all_infeasible_records_relabelled_feasible=False
all_infeasible_records_added_to_feasible_training=False
feasible_ranking_master_change_authorized=False
hard_feasibility_relaxation_authorized=False
online_selector_change_authorized=False
```

Every future dataset record must retain enough source identity to be audited
back to a fixed selection-log record:

```text
required_source_fields=artifact_sha256,run_id,record_index,selection_step
required_candidate_fields=candidate_count,selected_index,feasible_mask,infeasibility_reasons
required_tensor_contract=camp_candidate_tensor_provenance
required_generation_contract=candidate_generation_contract
required_atom_contract=atom_schema_version,atom_names,atoms,normalized_atoms
```

The record must fail closed when any required source, tensor provenance,
candidate-generation contract, atom schema, cost, or label field is missing.

## Label Contract

Fallback-risk labels may use only current-tick fixed candidate constants
already present in the log:

```text
closed_loop_outcome_label_source_authorized=False
future_replanning_label_source_authorized=False
replay_label_generation_authorized=False
hand_authored_label_fill_authorized=False
```

For candidate `k`, the fixed nonnegative diagnostic costs are:

```text
red_cost_k=max(-dp_candidate_rewards[k].red_light, 0)
lane_cost_k=lane_crossing + static_crossing + off_road_fraction + lane_near_frac + lane_wide_frac + max(-centerline, 0)
quality_cost_k=max(-dp_candidate_rewards[k].total, 0)
```

The default label policy for any later implementation is deterministic and
predeclared:

```text
if union_reasons contains dp_red_light:
  oracle_order=lexicographic(red_cost,lane_cost,quality_cost,candidate_index)
elif union_reasons contains dp_lane_crossing or lane-related hard reason:
  oracle_order=lexicographic(lane_cost,red_cost,quality_cost,candidate_index)
else:
  oracle_order=lexicographic(quality_cost,red_cost,lane_cost,candidate_index)
```

The chosen fallback oracle is the first candidate under the applicable
lexicographic order:

```text
oracle_index=o_i
oracle_index_in_range_required=True
tie_breaker=candidate_index
selected_index_used_as_feature=False
candidate_rank_used_as_feature=False
```

Margins for a future separate fallback master must be fixed and nonnegative:

```text
fallback_risk_k=ordered_scalar_or_tuple_defined_by_oracle_order
risk_gap_ik=nonnegative_lexicographic_gap_from_oracle
m_ik=clip(margin_scale * risk_gap_ik, 0, margin_clip)
margin_scale_fixed_before_training=True
margin_clip_fixed_before_training=True
margin_ik_nonnegative=True
```

No alpha values for a weighted cost sum are authorized by this plan. If a later
gate replaces the default lexicographic policy with a weighted scalar label,
all weights must be fixed, nonnegative, and selected before training data
construction.

## Convex Training Boundary

A future fallback-risk training run, if separately authorized, must remain a
finite-candidate robust-margin problem over fixed atoms:

```text
score_k(w)=a_k^T w
a_k_fixed_before_weight_optimization=True
a_k_nonnegative_benders_compatible_atoms_only=True
new_atom_authorized_now=False
fallback_label_is_not_a_deployed_atom=True
simplex_master_convex_if_later_authorized=True
cvar_master_convex_if_later_authorized=True
l2_regularized_master_convex_if_later_authorized=True
```

For a future fallback-only record `i`, the admissible loss shape is:

```text
q_i(w)=max(0, max_k m_ik + (a_i,o_i - a_i,k)^T w)
```

This is convex because it is a finite maximum of affine functions in `w` and
the margins are fixed constants. This fallback-only master is separate from
the current feasible-ranking master.

## Sufficiency Requirements Before Training Authorization

Before any CAMP retraining gate can be authorized, a later gate must prove:

```text
default_off_dataset_builder_implemented=False
dataset_builder_unit_tests_required=True
clean_training_data_validator_extension_required=True
fallback_dataset_static_contract_review_required=True
training_validation_split_predeclaration_required=True
formal_seeds_11_12_13_excluded_required=True
scale_fit_training_groups_only_required=True
fallback_master_isolated_from_feasible_master_required=True
nonpromotion_boundary_required=True
```

The fixed 15-record artifact may support smoke tests and contract validation,
but it cannot by itself justify a deployable checkpoint, a safety claim, or a
CAMP-over-DP Top-1 claim.

## Forbidden

```text
replay_execution_authorized=False
candidate_generation_authorized=False
camp_training_authorized=False
camp_retraining_authorized=False
Full36_authorized=False
formal_seeds_11_12_13_authorized=False
dp_modification_authorized=False
reference_blend_authorized=False
guidance_authorized=False
postprocess_postselection_authorized=False
closed_loop_outcome_online_input_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
fallback_risk_training_authorized_now=False
fallback_risk_smoke_authorized_now=False
```

## Decision

```text
status=fallback_risk_training_data_design_plan_ready_static_contract_review
passed=True
fallback_training_data_design_complete=True
dataset_builder_implementation_authorized=False
fallback_risk_training_authorized_now=False
fallback_risk_smoke_authorized_now=False
feasible_ranking_master_change_authorized=False
hard_feasibility_relaxation_authorized=False
all_infeasible_records_added_to_feasible_training=False
production_selector_change_authorized=False
online_selector_change_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

Next admissible gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_design_static_contract_review_only
```

The next gate may only statically review this training-data design plan. It
must not implement a dataset builder, run replay, generate candidates, train
CAMP, retrain CAMP, modify Diffusion Planner, use formal seeds, relax hard
feasibility, add all-infeasible records to the feasible-ranking master, promote
a selector or atom, or claim safety/CAMP-over-DP benefit.
