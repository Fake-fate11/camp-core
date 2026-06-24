# DP Native Base Plus Add-On Static DP Reward Fallback Feasibility Remediation Plan

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_remediation_plan_only
```

This plan-only artifact defines a paper-consistent remediation path for the
fallback/zero-feasible support observed in the fixed broader nonformal
evaluation artifact. It does not run replay, generate candidates, train CAMP,
modify Diffusion Planner, enable reference_blend/guidance/postprocess/
postselection, promote selector/atoms, or make safety/CAMP-over-DP claims.

## Heads

```text
local_HEAD_before_plan_commit=76340fce4c1d84fe48267d55714bed6e8aab1206
origin_main_before_plan_commit=76340fce4c1d84fe48267d55714bed6e8aab1206
github_refs_heads_main_before_plan_commit=76340fce4c1d84fe48267d55714bed6e8aab1206
autodl_CAMP_HEAD_before_plan_commit=76340fce4c1d84fe48267d55714bed6e8aab1206
autodl_CAMP_origin_main_before_plan_commit=76340fce4c1d84fe48267d55714bed6e8aab1206
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required_DP_fixed_commit=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Tracked worktree files were clean before this plan. Existing unrelated
untracked local handoff/session files and unrelated AutoDL untracked files were
left untouched.

## Fixed Inputs

```text
evaluation_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_broader_nonformal_eval_1c235eb_20260624T092550Z
evaluation_summary_sha256=c39fa6278431e08ee16b7b45f6645e43fa46f9951981c1fff8fa1809778aea07
attribution_doc=docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution.md
training_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training
weights=offline_weights_dp_static.npy
atom_scales=atom_scales_dp_static.json
```

## Observed Failure Classes

The fixed attribution found:

```text
records_total=60
records_with_feasible_total=45
records_without_feasible_total=15
route_records_without_feasible={"nishishinjuku_lane_change": 4, "sample_tl": 11}
route_tl_records_without_feasible={"nishishinjuku_lane_change|off": 2, "nishishinjuku_lane_change|on": 2, "sample_tl|off": 1, "sample_tl|on": 10}
record_all_candidate_reason_counts={"['dp_lane_crossing']": 5, "['dp_red_light']": 10}
sample_tl_on_no_feasible_records=10/10
sample_tl_on_all_candidate_blocker=dp_red_light
nishishinjuku_lane_change_no_feasible_records=4/20
nishishinjuku_lane_change_all_candidate_blocker=dp_lane_crossing
sample_normal_no_feasible_records=0/20
```

The primary failure class is therefore
`sample_tl_traffic_light_on_all_candidates_dp_red_light`. The secondary
failure class is the lane-crossing all-candidate tail.

## Mathematical Boundary

The remediation path must preserve these constraints:

```text
hard_feasibility_relaxation_authorized=False
dp_red_light_is_hard_reason=True
dp_lane_crossing_is_hard_reason=True
all_infeasible_records_admissible_for_current_feasible_ranking_master=False
fallback_records_may_not_be_relabelled_feasible=True
fixed_candidate_set_only=True
candidate_trajectory_rewrite_authorized=False
postprocess_postselection_authorized=False
dp_modification_authorized=False
```

Under the current DP-CAMP Benders-style training contract, every feasible
ranking training record must have at least one finite feasible oracle
candidate. A record whose fixed candidate set has no feasible candidate cannot
enter the current feasible-ranking robust-margin master. The selector can only
rank fixed candidates; it cannot turn a DP-red-light or lane-crossing hard
violation into a feasible candidate and cannot prove a safety benefit for an
all-infeasible tick.

Any fallback analysis is therefore a separate diagnostic object over fixed
candidate constants. It may rank lower-risk infeasible fallbacks for debugging,
but it is not a deployment selector, not a feasible-ranking CAMP checkpoint,
and not evidence that CAMP beats DP Top-1.

## Remediation Sequence

### Step 1: Fixed-Artifact Fallback Risk Ranking Audit

The next admissible step is a read-only audit over the fixed evaluation
artifact and existing `camp_selection_log.json` files:

```text
audit_only=True
source=evaluation_artifact
records_scope=records_without_feasible_candidate_only
required_no_feasible_records=15
compare_selected_index_to_min_dp_red_light_cost=True
compare_selected_index_to_min_lane_related_cost=True
compare_selected_index_to_min_dp_reward_cost=True
report_route_tl_seed_step_breakdown=True
report_whether_any_lower_risk_fixed_candidate_exists=True
replay_authorized=False
candidate_generation_authorized=False
training_authorized=False
```

This audit should answer whether the existing static DP-reward scorer, when
forced into the current fallback path, already selects the least-bad fixed
candidate under logged DP-reward diagnostics. It must fail closed if a required
cost/provenance field is absent.

For the `sample_tl|on` blocker, the audit should prioritize red-light
diagnostics:

```text
sample_tl_on_records_without_feasible=10
primary_compare_metric=dp_red_light_cost
must_not_relax_dp_red_light=True
must_not_claim_red_light_candidate_safe=True
```

For the lane-crossing tail, the audit should prioritize lane-related
diagnostics already present in the log:

```text
lane_crossing_records_without_feasible=5
primary_compare_metric=lane_related_dp_reward_or_atom_cost
must_not_relax_dp_lane_crossing=True
must_not_claim_lane_crossing_candidate_safe=True
```

### Step 2: Optional Future Fallback-Risk Training Smoke

Only after Step 1, and only with explicit user authorization, a nondeployable
static fallback-risk ranking smoke may be considered:

```text
mode=static
training_scope=fallback_risk_ranking
label_source=dp_reward
source_records=fixed_no_feasible_records_only
require_dp_native_training_data_contract=True
require_atom_schema=True
closed_loop_outcome_label_source_authorized=False
safety_cost_v1_label_source_authorized=False
deployment_authorized=False
```

This future smoke would be a diagnostic training object for all-infeasible
fallback ranking only. It must not be merged into the feasible-ranking CAMP
checkpoint, must not be used online, and must not be described as a deployable
checkpoint unless a later formal fallback contract and matched evaluation
explicitly authorize that path.

### Step 3: Selector-Only Impossibility Check

Every fallback remediation result must record the selector-only boundary:

```text
if_no_lower_risk_fixed_candidate_exists_then_selector_only_remediation_impossible=True
repair_would_require_candidate_generation_or_hard_feasibility_or_fallback_policy_change=True
camp_selector_improvement_claim_allowed=False
```

If the fixed all-infeasible candidate set contains no candidate with lower
logged red-light or lane-related cost than the selected fallback candidate, a
selector-only CAMP remediation cannot improve that tick. Repairing such a case
would require an explicitly separate candidate-generation, hard-feasibility,
fallback-policy, or upstream-planner change, all of which remain forbidden by
this gate.

## Forbidden

This plan does not authorize:

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

The following mechanisms remain outside the paper-consistent CAMP-DP reranker
path unless a later separately authorized contract proves otherwise:

```text
--candidate_reference_blend_steps
--candidate_guidance_config
--candidate_guidance_scale
--camp_perfect_tracker_command_postselection
--camp_traffic_light_hybrid_postselection
--camp_underprogress_relaxation
--camp_splice_shadow_rule
```

## Authorization Boundary

This plan grants no execution authorization beyond the next read-only
fixed-artifact audit. Any fallback-risk training smoke, replay, collection,
candidate generation, deployment selector change, DP change, atom promotion,
or safety/CAMP-over-DP claim requires a later explicit user authorization and a
separate audit entry.

## Verification

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_remediation_plan.md camp_core/tests/test_dp_native_fallback_feasibility_remediation_plan.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_fallback_feasibility_remediation_plan.py
exit=0

python -m pytest camp_core/tests/test_dp_native_fallback_feasibility_remediation_plan.py -q
exit=1
reason=pre-existing unavailable long-path test node interrupted collection before target test ran

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_plan.py -q
4 passed
exit=0
```

The temporary-root test used a short copied test filename to avoid adding a
second Windows path-length failure on top of the existing collection blocker;
the copied test content and target document were unchanged.

## Decision

```text
status=fallback_feasibility_remediation_plan_ready_read_only_next_gate
primary_remediation_strategy=fixed_artifact_fallback_risk_ranking_audit_first
fallback_risk_training_authorized_now=False
feasible_ranking_master_change_authorized=False
hard_feasibility_relaxation_authorized=False
all_infeasible_records_added_to_feasible_training=False
candidate_generation_authorized=False
camp_training_authorized=False
dp_modification_authorized=False
reference_blend_authorized=False
guidance_authorized=False
postprocess_postselection_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fixed_artifact_fallback_risk_ranking_audit_only`

The next gate is read-only. It may inspect only the fixed broader nonformal
evaluation artifact and existing logs. It must not run replay, generate
candidates, train CAMP, modify DP, enable reference_blend/guidance/
postprocess/postselection, promote selector/atoms, or make safety/CAMP-over-DP
claims.
