# DP Native Training Sufficiency Development Clean Collection Scope Plan

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_clean_collection_scope_plan_only
```

This plan-only gate defines a future clean DP-native development collection
scope that could close the current development profile gaps. It does not run
collection, replay, candidate generation, training, Diffusion Planner
modification, selector/atom promotion, or any safety/CAMP-over-DP claim.

## Heads

```text
local_HEAD=8728a2100f1af2548c13da25a00d7b65b7644f36
origin_main=8728a2100f1af2548c13da25a00d7b65b7644f36
github_refs_heads_main=8728a2100f1af2548c13da25a00d7b65b7644f36
autodl_CAMP_HEAD=8728a2100f1af2548c13da25a00d7b65b7644f36
autodl_CAMP_origin_main=8728a2100f1af2548c13da25a00d7b65b7644f36
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Tracked worktree files were clean before this plan. Existing unrelated
untracked handoff/session files were intentionally left untouched.

## Current Gap

The fixed clean-log artifact remains:

```text
artifact_root=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
records=36
usable_feasible_records=31
routes=2
seeds=3
traffic_light_states=2
candidate_count=4
profile=dp_native_feasible_ranking_development_minimal_v1
```

The development profile gap is:

```text
raw_record_gap=64
usable_feasible_record_gap=69
route_gap=1
seed_gap=1
traffic_light_state_gap=0
candidate_count_gap=0
```

## Future Scope Requiring User Authorization

The smallest profile-complete future scope should produce a single clean
development artifact with the minimum route/seed counts required by the
profile plus a usable-record buffer:

```text
routes=sample_normal,sample_tl,nishishinjuku_lane_change
sample_normal=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
sample_tl=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
nishishinjuku_lane_change=/root/autodl-tmp/camp_dp_assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl
route_buckets=normal,traffic_light,lane_change_or_merge
seeds=101,102,103,104
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
must_validate_every_log=True
expected_run_count=24
expected_max_selection_records=120
```

This is still only a proposed future collection scope. It is not authorized by
this gate. The eventual profile decision must use actual validator output:

```text
must_pass_profile=dp_native_feasible_ranking_development_minimal_v1
required_records_at_least=100
required_usable_feasible_records_at_least=100
required_routes_at_least=3
required_seeds_at_least=4
required_traffic_light_states=["off", "on"]
required_candidate_count_at_least=4
required_clean_contract=True
required_candidate_tensor_provenance=True
required_atom_schema=True
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

This plan does not grant the required replay/collection authorization. A later
execution gate may proceed only if the user explicitly authorizes this exact
scope or a stricter subset that still satisfies the profile.

If the future run produces fewer than 100 usable feasible records, or fails
any clean-contract/provenance/profile check, the result must fail closed and
must not train CAMP.

## Decision

```text
status=development_clean_collection_scope_plan_ready_user_authorization_required
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

`dp_native_training_sufficiency_development_collection_user_authorization_pending`

The next gate is pending explicit user approval for the exact scope above or a
stricter profile-complete subset. Do not run collection, replay, candidate
generation, training, promotion, DP changes, or claims until that approval is
present.
