# DP Native Base Plus Add-On Static DP Reward Broader Nonformal Fallback Feasibility Attribution

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution_only
```

This artifact is a read-only attribution over the fixed broader nonformal
evaluation artifact. It reads only the existing summary and
`camp_selection_log.json` files under the fixed artifact root. It does not run
replay, generate candidates, train CAMP, modify Diffusion Planner, enable
reference_blend/guidance/postprocess/postselection, promote selector/atoms, or
make safety/CAMP-over-DP claims.

## Fixed Inputs

```text
evaluation_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_broader_nonformal_eval_1c235eb_20260624T092550Z
source_summary=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_broader_nonformal_eval_1c235eb_20260624T092550Z/broader_nonformal_eval_summary.json
source_summary_sha256=c39fa6278431e08ee16b7b45f6645e43fa46f9951981c1fff8fa1809778aea07
```

## HEAD Evidence

```text
local_HEAD_before_result_commit=f9dc1da4b56aada60482f99a18adb800c49b4a7a
origin_main_before_result_commit=f9dc1da4b56aada60482f99a18adb800c49b4a7a
github_refs_heads_main_before_result_commit=f9dc1da4b56aada60482f99a18adb800c49b4a7a
source_eval_autodl_CAMP_HEAD=1c235ebcad52143297852d4873d345710be31680
source_eval_autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required_DP_fixed_commit=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

The source evaluation artifact was produced before commit `f9dc1da`; this
attribution is a post-hoc read-only analysis of that fixed artifact.

## Attribution Scope

```text
records_total=60
records_with_feasible_total=45
records_without_feasible_total=15
routes=sample_normal,sample_tl,nishishinjuku_lane_change
seeds=109,110
traffic_lights=off,on
steps=5
num_candidates=4
candidate_source=dp_native_replay_candidates_from_fixed_source_artifact
attribution_replay_executed=False
attribution_candidate_generation_executed=False
attribution_training_executed=False
attribution_dp_modified=False
```

## Route/TL Attribution

```text
route_records_without_feasible={"nishishinjuku_lane_change": 4, "sample_tl": 11}
route_tl_records_without_feasible={"nishishinjuku_lane_change|off": 2, "nishishinjuku_lane_change|on": 2, "sample_tl|off": 1, "sample_tl|on": 10}
route_seed_tl_records_without_feasible={"nishishinjuku_lane_change|109|off": 1, "nishishinjuku_lane_change|109|on": 1, "nishishinjuku_lane_change|110|off": 1, "nishishinjuku_lane_change|110|on": 1, "sample_tl|109|on": 5, "sample_tl|110|off": 1, "sample_tl|110|on": 5}
sample_normal_records_without_feasible=0
```

Per-run no-feasible counts:

| Run | Records | Records without feasible |
| --- | ---: | ---: |
| `sample_normal_seed109_tl_off_static` | 5 | 0 |
| `sample_normal_seed109_tl_on_static` | 5 | 0 |
| `sample_normal_seed110_tl_off_static` | 5 | 0 |
| `sample_normal_seed110_tl_on_static` | 5 | 0 |
| `sample_tl_seed109_tl_off_static` | 5 | 0 |
| `sample_tl_seed109_tl_on_static` | 5 | 5 |
| `sample_tl_seed110_tl_off_static` | 5 | 1 |
| `sample_tl_seed110_tl_on_static` | 5 | 5 |
| `nishishinjuku_lane_change_seed109_tl_off_static` | 5 | 1 |
| `nishishinjuku_lane_change_seed109_tl_on_static` | 5 | 1 |
| `nishishinjuku_lane_change_seed110_tl_off_static` | 5 | 1 |
| `nishishinjuku_lane_change_seed110_tl_on_static` | 5 | 1 |

## Reason Attribution

For the 15 records where no candidate is feasible, the record-level union of
candidate blockers is:

```text
record_union_reason_counts={"['dp_lane_crossing', 'dp_red_light']": 2, "['dp_lane_crossing']": 5, "['dp_red_light']": 8}
```

The blocker that appears on every candidate within each no-feasible record is:

```text
record_all_candidate_reason_counts={"['dp_lane_crossing']": 5, "['dp_red_light']": 10}
```

Candidate-level blockers across the 60 false candidates inside those 15
no-feasible records are:

```text
candidate_reason_counts_in_no_feasible_records={"dp_lane_crossing": 25, "dp_red_light": 40}
candidate_reason_signature_counts_in_no_feasible_records={"['dp_lane_crossing', 'dp_red_light']": 5, "['dp_lane_crossing']": 20, "['dp_red_light']": 35}
```

Route-level all-candidate blockers:

```text
route_all_candidate_reason_counts={"nishishinjuku_lane_change": {"['dp_lane_crossing']": 4}, "sample_tl": {"['dp_lane_crossing']": 1, "['dp_red_light']": 10}}
route_candidate_reason_counts={"nishishinjuku_lane_change": {"dp_lane_crossing": 16}, "sample_tl": {"dp_lane_crossing": 9, "dp_red_light": 40}}
```

## Red-Light Cost Attribution

```text
red_cost_stats_by_route={"nishishinjuku_lane_change": {"max": 0.0, "mean": 0.0, "min": 0.0}, "sample_tl": {"max": 50.0, "mean": 37.51136363636363, "min": 0.0}}
red_cost_stats_by_route_tl={"nishishinjuku_lane_change|off": {"max": 0.0, "mean": 0.0, "min": 0.0}, "nishishinjuku_lane_change|on": {"max": 0.0, "mean": 0.0, "min": 0.0}, "sample_tl|off": {"max": 0.0, "mean": 0.0, "min": 0.0}, "sample_tl|on": {"max": 50.0, "mean": 41.2625, "min": 20.5}}
```

This separates the two failure classes:

- `sample_tl|on`: 10/10 records have no feasible candidate, and every
  candidate in each such record has `dp_red_light`; red-light cost is strictly
  positive for all those false candidates.
- `sample_tl|off`: 1/10 records has no feasible candidate, and every
  candidate in that record has `dp_lane_crossing`; red-light cost is zero.
- `nishishinjuku_lane_change`: 4/20 records have no feasible candidate, one
  record per run, and every candidate in each such record has
  `dp_lane_crossing`; red-light cost is zero.
- `sample_normal`: 0/20 records without a feasible candidate in this fixed
  artifact.

## Boundary Checks

```text
attribution_only=True
fixed_source_artifact_only=True
replay_executed=False
candidate_generation_executed=False
camp_training_executed=False
dp_modified=False
reference_blend_enabled=False
guidance_enabled=False
postprocess_postselection_enabled=False
closed_loop_outcome_online_input_used=False
selector_promotion_executed=False
atom_promotion_executed=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Verification

Local narrow checks:

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution.md camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution.py
exit=0

python -m pytest camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution.py -q
exit=1
reason=pre-existing unavailable long-path test node interrupted collection before target test ran

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_attr.py -q
4 passed
exit=0
```

The temporary-root test used a short copied test filename to avoid adding a
second Windows path-length failure on top of the existing collection blocker;
the copied test content and target document were unchanged.

## Decision

```text
status=base_plus_addon_static_dp_reward_broader_nonformal_fallback_feasibility_attribution_passed_read_only
primary_failure_class=sample_tl_traffic_light_on_all_candidates_dp_red_light
secondary_failure_class=lane_crossing_all_candidate_no_feasible_tail
sample_tl_on_no_feasible_records=10/10
sample_tl_on_all_candidate_blocker=dp_red_light
sample_tl_off_no_feasible_records=1/10
sample_tl_off_all_candidate_blocker=dp_lane_crossing
nishishinjuku_lane_change_no_feasible_records=4/20
nishishinjuku_lane_change_all_candidate_blocker=dp_lane_crossing
sample_normal_no_feasible_records=0/20
attribution_replay_executed=False
attribution_candidate_generation_executed=False
attribution_training_executed=False
dp_modification_authorized=False
dp_modification_executed=False
reference_blend_authorized=False
guidance_authorized=False
postprocess_postselection_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This attribution supports a fail-closed conclusion: the current static
DP-reward reranker can load and preserve fixed candidates, but broader
fallback/feasibility support is still bottlenecked by DP-reward hard
feasibility masks. In this fixed artifact, the largest blocker is red-light
infeasibility on `sample_tl` traffic-light-on records; the smaller recurring
tail is lane-crossing infeasibility on `nishishinjuku_lane_change` and one
`sample_tl` traffic-light-off record.

It does not prove safety, does not prove CAMP beats DP Top-1, and does not
authorize deployment, selector promotion, atom promotion, DP modification, or
CAMP retraining for deployment.

## Next Gate

`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_remediation_plan_only`

The next gate is plan-only. It may propose a paper-consistent, fixed-candidate
development remediation path for the observed DP-reward feasibility blocker,
but it must not run replay, generate candidates, train CAMP, modify DP, enable
reference_blend/guidance/postprocess/postselection, promote selector/atoms, or
make safety/CAMP-over-DP claims.
