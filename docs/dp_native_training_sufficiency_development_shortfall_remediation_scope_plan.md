# DP Native Training Sufficiency Development Shortfall Remediation Scope Plan

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_remediation_scope_plan_only
```

This plan-only gate defines a future user-authorized additive clean collection
scope to remediate the usable-feasible shortfall attributed in
`docs/dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_attribution.md`.
It does not run replay, generate candidates, train CAMP, modify Diffusion
Planner, promote selector/atoms, or make any safety/CAMP-over-DP claim.

## Heads

```text
local_HEAD=16221532236bc216370dfec79b1967db973f5259
origin_main=16221532236bc216370dfec79b1967db973f5259
github_refs_heads_main=16221532236bc216370dfec79b1967db973f5259
autodl_CAMP_HEAD=16221532236bc216370dfec79b1967db973f5259
autodl_CAMP_origin_main=16221532236bc216370dfec79b1967db973f5259
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Tracked worktree files were clean before this plan. Existing unrelated
untracked handoff/session files were intentionally left untouched.

## Fixed Base Artifact

The base artifact remains:

```text
base_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_development_collection_73aec55_20260624T075109Z
base_records=120
base_usable_feasible_records=72
base_required_usable_feasible_records=100
base_usable_feasible_record_gap=28
base_routes={"nishishinjuku_lane_change": 40, "sample_normal": 40, "sample_tl": 40}
base_usable_by_route={"nishishinjuku_lane_change": 0, "sample_normal": 40, "sample_tl": 32}
```

The shortfall attribution identified the current `nishishinjuku_lane_change`
route as the primary blocker:

```text
nishishinjuku_lane_change_unusable_records=40/40
nishishinjuku_lane_change_false_candidates=160/160
nishishinjuku_lane_change_record_reasons={"dp_road_border": 40, "dp_lane_crossing": 40}
```

Therefore this plan must not rely on that same lane-change route for usable
record remediation unless a later separate gate proves nonzero support.

## Read-Only Route Asset Inventory

AutoDL route assets observed read-only:

```text
/root/autodl-tmp/camp_dp_assets/nishishinjuku_auto_route.pkl
/root/autodl-tmp/camp_dp_assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl
/root/autodl-tmp/camp_dp_assets/nishishinjuku_release_auto_route.pkl
/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
/root/autodl-tmp/camp_dp_assets/sample_map_smoke_route.pkl
/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_58_to_55.pkl
/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
```

This inventory is not an authorization to run any route. It only prevents the
plan from inventing nonexistent route paths.

## Future Scope Requiring User Authorization

The smallest additive scope with a usable-record buffer should combine the fixed
base artifact with a new add-on collection over routes that already showed
nonzero usable support in the fixed artifact:

```text
base_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_development_collection_73aec55_20260624T075109Z
addon_routes=sample_normal,sample_tl
sample_normal=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
sample_tl=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
addon_seeds=105,106,107,108
traffic_lights=on,off
steps=5
num_candidates=4
candidate_noise_strategy=iid
candidate_noise_scale=1.0
advance_mode=perfect
max_npcs=0
spawn_probability=0.3
camp_selector_mode=uniform
camp_feasibility_source=dp_reward
must_enable=--camp_candidate_tensor_provenance_logging
addon_expected_run_count=16
addon_expected_max_selection_records=80
```

Observed support from the same two routes in the fixed base artifact:

```text
sample_normal_observed_usable=40/40
sample_tl_observed_usable=32/40
combined_observed_usable=72/80
addon_min_usable_needed_to_pass=28/80
combined_expected_usable_if_observed_rate_repeats=144/200
combined_expected_usable_margin_if_observed_rate_repeats=44
```

The observed rate is not a performance or safety claim. It is only a planning
buffer. The later result must use actual clean/profile validator output and
must fail closed if the combined base-plus-add-on artifact has fewer than 100
usable feasible records.

## Validation Requirements For Any Later Result

Any later execution result must validate the combined input:

```text
must_validate_base_plus_addon=True
must_pass_clean_contract=True
must_pass_profile=dp_native_feasible_ranking_development_minimal_v1
required_records_at_least=100
required_usable_feasible_records_at_least=100
required_routes_at_least=3
required_seeds_at_least=4
required_traffic_light_states=["off", "on"]
required_candidate_count_at_least=4
required_candidate_tensor_provenance=True
required_atom_schema=True
must_record_per_route_usable_counts=True
must_record_all_false_reason_counts=True
```

## Forbidden In Any Later Execution

Any later execution request must still forbid:

```text
--camp_collect_closed_loop_outcomes
--candidate_reference_blend_steps
--candidate_guidance_config
--candidate_guidance_scale
--camp_perfect_tracker_command_postselection
--camp_traffic_light_hybrid_postselection
--camp_underprogress_relaxation
--camp_splice_shadow_rule
Full36
formal seeds 11/12/13
CAMP retraining
Diffusion Planner code/config/weight change
selector promotion
atom promotion
safety benefit claim
CAMP over DP Top-1 claim
```

## Authorization Boundary

This plan does not grant replay or collection authorization. A later execution
gate may proceed only if the user explicitly authorizes this exact additive
scope or a stricter subset that still has a plausible usable-feasible buffer.

If the future combined base-plus-add-on validation produces fewer than 100
usable feasible records, or fails any clean-contract/provenance/profile check,
the result must fail closed and must not train CAMP.

## Verification

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_shortfall_remediation_scope_plan.md camp_core/tests/test_dp_native_training_sufficiency_development_shortfall_remediation_scope_plan.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_shortfall_remediation_scope_plan.py
exit=0

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_dp_native_training_sufficiency_development_shortfall_remediation_scope_plan.py -q
3 passed in 0.02s
exit=0
```

The direct Windows repo pytest invocation for the same target aborted before
collecting this test because pytest enumerated a pre-existing unavailable
long-path test node unrelated to this plan-only change. The target test was
therefore run from a temporary copy containing only the target test and target
doc; no repo files were cleaned or modified for that workaround.

## Decision

```text
status=usable_feasible_shortfall_remediation_scope_plan_ready_user_authorization_required
base_artifact_fixed=True
primary_remediation_strategy=additive_proven_support_routes
reuse_zero_support_lane_change_route_for_remediation=False
future_scope_profile_complete_if_validated=True
collection_replay_authorized_now=False
candidate_generation_authorized_now=False
training_execution_authorized=False
camp_retraining_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`dp_native_training_sufficiency_development_additive_clean_collection_user_authorization_pending`

The next gate is pending explicit user approval for the exact additive scope
above or a stricter profile-complete subset. Do not run collection, replay,
candidate generation, training, promotion, DP changes, or claims until that
approval is present.
