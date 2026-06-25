# DP Native Fixed-Artifact Fallback Risk Ranking Remediation Design Plan

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_design_plan_only
```

This plan-only artifact defines a default-off, nondeployable remediation design
for fallback-risk ranking diagnostics over fixed DP candidates. It does not
implement production logic, run replay, generate candidates, train CAMP, retrain
CAMP, modify Diffusion Planner, promote a selector or atom, or claim safety
benefit or CAMP-over-DP Top-1.

## Inputs

```text
prior_audit=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_audit.md
evaluation_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_broader_nonformal_eval_1c235eb_20260624T092550Z
evaluation_summary_sha256=c39fa6278431e08ee16b7b45f6645e43fa46f9951981c1fff8fa1809778aea07
camp_head_at_plan=fcdf067864a0525bfc3361778683c9d59b71cc23
camp_origin_main_at_plan=fcdf067864a0525bfc3361778683c9d59b71cc23
github_refs_heads_main_at_plan=fcdf067864a0525bfc3361778683c9d59b71cc23
autodl_CAMP_HEAD_at_plan=fcdf067864a0525bfc3361778683c9d59b71cc23
autodl_CAMP_origin_main_at_plan=fcdf067864a0525bfc3361778683c9d59b71cc23
autodl_DP_HEAD_at_plan=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The prior fixed-artifact audit found:

```text
records_without_feasible_candidate=15
dp_red_light_cost_selected_min_count=14/15
dp_red_light_cost_lower_cost_fixed_candidate_available_count=1/15
lane_related_cost_selected_min_count=4/15
lane_related_cost_lower_cost_fixed_candidate_available_count=11/15
dp_reward_quality_cost_selected_min_count=15/15
dp_reward_quality_cost_lower_cost_fixed_candidate_available_count=0/15
lower_risk_fixed_candidate_exists_under_logged_costs=True
```

## Problem Statement

The current feasible-ranking CAMP master cannot use all-infeasible records
because there is no feasible oracle candidate in those ticks. The fixed
artifact nevertheless shows that, inside some all-infeasible candidate sets,
the logged fallback selected candidate is not the least-bad fixed candidate
under red-light or lane-related DP reward diagnostics.

This design treats those records as a separate fallback-risk diagnostic track.
It must not relabel any all-infeasible record as feasible and must not mix
fallback-risk diagnostics into the existing feasible-ranking robust-margin
master.

## Design Contract

```text
default_off=True
nondeployable_diagnostic_only=True
fixed_candidate_set_only=True
records_scope=records_without_feasible_candidate_only
all_infeasible_records_relabelled_feasible=False
all_infeasible_records_added_to_feasible_training=False
feasible_ranking_master_change_authorized=False
hard_feasibility_relaxation_authorized=False
candidate_trajectory_rewrite_authorized=False
postprocess_postselection_authorized=False
dp_modification_authorized=False
closed_loop_outcome_label_source_authorized=False
online_selector_change_authorized=False
```

The diagnostic target may only be computed from current-tick logged fixed
candidate constants:

```text
dp_red_light_cost=max(-dp_candidate_rewards[k].red_light, 0)
lane_related_cost=lane_crossing + static_crossing + off_road_fraction + lane_near_frac + lane_wide_frac + max(-centerline, 0)
dp_reward_quality_cost=max(-dp_candidate_rewards[k].total, 0)
```

Any future implementation must fail closed when required cost or provenance
fields are missing. Missing fields must not be filled by replay, closed-loop
outcomes, future labels, candidate generation, DP reruns, or hand-authored
defaults.

## Mathematical Boundary

The fallback-risk diagnostic may rank fixed candidates only. If a later
authorized smoke uses CAMP weights, the score must remain:

```text
score_k(w)=a_k^T w
```

where `a_k` is fixed before scoring and contains only Benders-compatible
nonnegative atoms or masks already admitted by the atom audit. A diagnostic
fallback-risk label may be used as a fixed per-candidate comparison target, but
it is not itself a deployed atom and cannot be promoted without a later atom
gate.

The design preserves convexity boundaries:

```text
candidate_features_fixed_before_weight_optimization=True
candidate_features_independent_of_w_rank_and_selected_index=True
fallback_cost_targets_nonnegative=True
simplex_master_convex_if_later_authorized=True
cvar_master_convex_if_later_authorized=True
l2_regularized_master_convex_if_later_authorized=True
new_atom_authorized_now=False
training_authorized_now=False
```

No selector-only method can make an all-infeasible fixed candidate set feasible.
If every fixed candidate is equally bad under all logged fallback-risk metrics,
selector-only remediation is impossible for that tick. If a lower-risk fixed
candidate exists, a future default-off diagnostic smoke may test whether a
separate fallback-risk ranker can select it, but such a smoke remains
nondeployable unless a later formal fallback contract authorizes more.

## Proposed Default-Off Components

### Read-Only Fallback-Risk Extractor

The extractor would read existing `camp_selection_log.json` records only when
`any(feasible_mask) == False`, then emit per-candidate diagnostic costs and
argmin indices:

```text
extractor_default_off=True
input=existing_camp_selection_log_json
output=fallback_risk_cost_vectors
candidate_count_must_match=True
selected_index_must_be_in_range=True
provenance_payload_must_be_valid=True
pre_post_tensor_hash_equal_required=True
no_candidate_row_append_required=True
no_coordinate_heading_speed_rewrite_required=True
```

### Nondeployable Fallback-Risk Ranking Smoke

Only after a later explicit authorization gate, a smoke may train or evaluate a
separate fallback-risk ranking diagnostic. It must remain isolated from the
feasible-ranking master:

```text
fallback_risk_smoke_default_off=True
fallback_risk_smoke_nondeployable=True
fallback_risk_smoke_training_authorized_now=False
uses_formal_seeds_11_12_13=False
uses_closed_loop_outcomes_as_online_input=False
uses_safety_cost_v1_label_source=False
changes_online_selector=False
changes_deployable_checkpoint=False
```

The smoke target must be fixed before scoring. A later contract may choose one
of these read-only labels, but this plan does not authorize the choice:

```text
label_option_red_first=lexicographic(dp_red_light_cost, lane_related_cost, dp_reward_quality_cost)
label_option_lane_first=lexicographic(lane_related_cost, dp_red_light_cost, dp_reward_quality_cost)
label_option_weighted_sum=alpha_red*dp_red_light_cost + alpha_lane*lane_related_cost + alpha_quality*dp_reward_quality_cost
alpha_values_authorized_now=False
```

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
```

## Decision

```text
status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review
passed=True
fallback_risk_extractor_implementation_authorized=False
fallback_risk_training_authorized_now=False
fallback_risk_smoke_authorized_now=False
feasible_ranking_master_change_authorized=False
hard_feasibility_relaxation_authorized=False
all_infeasible_records_added_to_feasible_training=False
candidate_generation_authorized=False
camp_training_authorized=False
camp_retraining_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

Next admissible gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_static_contract_review_only
```

## Current-Head Revalidation After Current Ranking Audit Closure

Date: 2026-06-25

The plan remains valid after the current fixed-artifact fallback-risk ranking
audit closure on the synchronized CAMP/GitHub/AutoDL HEAD. This is still a
plan-only gate over existing fixed artifacts.

```text
camp_head_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1
camp_origin_main_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1
github_refs_heads_main_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1
autodl_CAMP_HEAD_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1
autodl_CAMP_origin_main_at_revalidation=30e16f3e132064366720ff58af9549de10f5d9d1
autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4
prior_ranking_revalidation_status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete
prior_ranking_revalidation_failed_checks=[]
prior_ranking_revalidation_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_61fc525_20260625T053215Z
prior_ranking_revalidation_json_sha256=52bb6f5168483cf6843a98214a21f1d597e31030eb1dbb47387a827e87732fcc
prior_ranking_revalidation_md_sha256=843236dd8f0cdfaad4a3c52252bce922faed04aa0c8a05c97ddadc9276f5e75c
```

Decision:

```text
status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review
passed=True
current_head_design_plan_revalidated=True
local_py_compile_exit=0
local_target_pytest=16 passed
local_git_diff_check_exit=0
autodl_py_compile_exit=0
autodl_target_pytest=16 passed
autodl_git_diff_check_exit=0
score_expression=score_k(w)=a_k^T w
fallback_cost_targets_nonnegative=True
simplex_master_convex_if_later_authorized=True
cvar_master_convex_if_later_authorized=True
l2_regularized_master_convex_if_later_authorized=True
fallback_risk_extractor_implementation_authorized=False
fallback_risk_training_authorized_now=False
fallback_risk_smoke_authorized_now=False
camp_training_authorized=False
camp_retraining_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This remains a plan-only gate. It does not implement the extractor, run replay,
generate candidates, train CAMP, retrain CAMP, modify DP, use formal seeds,
promote a selector or atom, deploy, or claim safety/CAMP-over-DP benefit.

Next admissible gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_static_contract_review_only
```

The next gate may only statically review whether this fallback-risk remediation
design preserves the fixed-candidate affine scoring, nonnegative cost, and
convex master boundaries. It must not implement the extractor, run replay,
generate candidates, train CAMP, retrain CAMP, modify DP, use formal seeds, or
promote a selector or atom.

## Current-Head Revalidation

Date: 2026-06-25

The plan remains valid after current-head fixed-artifact ranking revalidation:

```text
camp_head_at_revalidation=2b7fcc4f2d10c925c8afdb1d86a11601b276a0b9
camp_origin_main_at_revalidation=2b7fcc4f2d10c925c8afdb1d86a11601b276a0b9
github_refs_heads_main_at_revalidation=2b7fcc4f2d10c925c8afdb1d86a11601b276a0b9
autodl_CAMP_HEAD_at_revalidation=2b7fcc4f2d10c925c8afdb1d86a11601b276a0b9
autodl_CAMP_origin_main_at_revalidation=2b7fcc4f2d10c925c8afdb1d86a11601b276a0b9
autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4
prior_ranking_revalidation_status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete
prior_ranking_revalidation_failed_checks=[]
```

This revalidation does not newly authorize training. The user-level procedural
blocker for future CAMP retraining is lifted, but this gate remains plan-only:

```text
fallback_risk_extractor_implementation_authorized=False
fallback_risk_training_authorized_now=False
fallback_risk_smoke_authorized_now=False
camp_training_executed=False
camp_retraining_executed=False
candidate_generation_executed=False
dp_modification_executed=False
```

## Current-Head Revalidation After Ranking Audit Revalidation

Date: 2026-06-25

The plan remains valid after the fixed-artifact fallback-risk ranking audit was
revalidated on the current synchronized CAMP HEAD:

```text
camp_head_at_revalidation=9ded474572c30ff75d1afe15f65f5c1e5b2f769e
camp_origin_main_at_revalidation=9ded474572c30ff75d1afe15f65f5c1e5b2f769e
github_refs_heads_main_at_revalidation=9ded474572c30ff75d1afe15f65f5c1e5b2f769e
autodl_CAMP_HEAD_at_revalidation=9ded474572c30ff75d1afe15f65f5c1e5b2f769e
autodl_CAMP_origin_main_at_revalidation=9ded474572c30ff75d1afe15f65f5c1e5b2f769e
autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4
prior_ranking_revalidation_status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete
prior_ranking_revalidation_failed_checks=[]
prior_ranking_revalidation_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_7a2d490_20260624T231111Z
prior_ranking_revalidation_json_sha256=fe57dc19a8f0371fe3f4f5ea469e39c0934a9bc8e76f205a046f2a29cfdaaa33
prior_ranking_revalidation_md_sha256=34fd32059d306725931cce948c4146c83d14d34555293b1c87cb58916c7352af
```

This remains a plan-only gate. It does not implement the extractor, run replay,
generate candidates, train CAMP, retrain CAMP, modify DP, use formal seeds,
promote a selector or atom, deploy, or claim safety/CAMP-over-DP benefit.

Next admissible gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_static_contract_review_only
```

## Current-Head Revalidation After Tail-Corrected Ranking Audit

Date: 2026-06-25

The plan remains valid after the tail-corrected fixed-artifact fallback-risk
ranking audit was revalidated on the current synchronized CAMP HEAD. This
remains a plan-only gate over existing fixed artifacts.

```text
camp_head_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4
camp_origin_main_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4
github_refs_heads_main_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4
autodl_CAMP_HEAD_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4
autodl_CAMP_origin_main_at_revalidation=123ea3d24be9120cbe3251e89ec054a0e641eae4
autodl_DP_HEAD_at_revalidation=7a1d33da277a1992ec474b5383a0c963c72e04e4
prior_ranking_revalidation_status=dp_native_fixed_artifact_fallback_risk_ranking_audit_complete
prior_ranking_revalidation_failed_checks=[]
prior_ranking_revalidation_output_dir=/root/autodl-tmp/camp_dp_native_broader_nonformal_fixed_artifact_fallback_risk_ranking_audit_5dbb8df_20260625T_current_tail
prior_ranking_revalidation_json_sha256=14c5bf7dfb6204ba8c47983f38cc326f5a4cca29ff63fb8f85a23cfef4437dd4
prior_ranking_revalidation_md_sha256=3124737477f1d6b5721dcdf585fcb382096b4e3bf29921283a3ad11695280746
```

Decision:

```text
status=fallback_risk_ranking_remediation_design_plan_ready_static_contract_review
passed=True
current_head_design_plan_revalidated=True
score_expression=score_k(w)=a_k^T w
fallback_cost_targets_nonnegative=True
simplex_master_convex_if_later_authorized=True
cvar_master_convex_if_later_authorized=True
l2_regularized_master_convex_if_later_authorized=True
fallback_risk_extractor_implementation_authorized=False
fallback_risk_training_authorized_now=False
fallback_risk_smoke_authorized_now=False
camp_training_authorized=False
camp_retraining_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This remains a plan-only gate. It does not implement the extractor, run replay,
generate candidates, train CAMP, retrain CAMP, modify DP, use formal seeds,
promote a selector or atom, deploy, or claim safety/CAMP-over-DP benefit.

Next admissible gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_ranking_remediation_static_contract_review_only
```
