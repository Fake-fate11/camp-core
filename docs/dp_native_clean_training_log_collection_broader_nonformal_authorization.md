# DP Native Clean Training Log Collection Broader Nonformal Authorization

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_collection_broader_nonformal_authorization_only_user_approval_required
```

This gate is read-only and authorization-only. It does not run replay, generate
candidates, validate new logs, train CAMP, modify Diffusion Planner, or make
safety/CAMP-over-DP claims.

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git fetch --prune origin
exit=0

git rev-parse HEAD origin/main
69b32c4cbfd303caa4ea8dd630751aa970f1922f
69b32c4cbfd303caa4ea8dd630751aa970f1922f

git ls-remote origin refs/heads/main
69b32c4cbfd303caa4ea8dd630751aa970f1922f refs/heads/main
```

AutoDL read-only status:

```text
CAMP HEAD / origin/main:
69b32c4cbfd303caa4ea8dd630751aa970f1922f
69b32c4cbfd303caa4ea8dd630751aa970f1922f

CAMP status:
## main...origin/main
untracked unrelated prior-session artifacts remain ignored

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4

DP status:
## tier4-main...origin/tier4-main
```

Existing successful smoke:

```text
root=/root/autodl-tmp/camp_dp_native_clean_training_log_smoke_f98bc5a_seed101_steps1_k2_dp_reward
camp_selection_log.json sha256=2effb6dcd31caa2fae1b4a82f73150ec943e983d8e9c4fa16272bc6d5c51102d
clean_dp_native_training_data_contract_validation.json sha256=8eaff01898c5b2cf6dfdca25e16de27624d940aefa9cc5260354decf569381d7
records=1
validator_passed=True
```

## Boundary

The one-record smoke proved that the fixed-DP clean logging and validator path
can execute with candidate tensor provenance enabled. It is not enough data for
CAMP retraining and does not authorize a broader replay matrix.

A broader nonformal clean-log collection would execute additional DP-native
candidate generation and replay. That remains outside the standing prohibition
unless the user explicitly authorizes the exact scope.

## Proposed Scope Requiring User Approval

If authorized later, the next execution gate should be a small broader
nonformal collection only:

```text
purpose=collect more DP-native clean selection logs for contract coverage
training_execution=False
camp_retraining=False
selector_promotion=False
atom_promotion=False
dp_modification=False
safety_claim=False
camp_over_dp_top1_claim=False
```

Exact proposed run envelope:

```text
routes:
  sample_tl=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
  sample_normal=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
seeds=101,102,103
traffic_lights=on,off
steps=3
num_candidates=4
candidate_noise_strategy=iid
candidate_noise_scale=1.0
advance_mode=perfect
max_npcs=0
spawn_probability=0.3
camp_selector_mode=uniform
camp_atom_scales=/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json
camp_feasibility_source=dp_reward
reward_config=/root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json
must_enable=--camp_candidate_tensor_provenance_logging
must_validate_every_log=True
expected_max_selection_records=36
```

Forbidden options remain:

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
DP modification/config/weight change
selector/atom promotion
safety or CAMP-over-DP claim
```

The broader collection should use `run_diffusion_planner_camp_replay.py`
directly for each run, not the benchmark matrix comparison path, so no
comparison claim is produced.

## Decision

```text
status=user_authorization_required
broader_nonformal_collection_authorized_now=False
reason=additional replay/candidate generation exceeds the prior one-record smoke authorization
replay_executed=False
candidate_generation_executed=False
clean_log_validator_run=False
training_execution_authorized=False
camp_retraining_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`dp_native_clean_training_log_collection_broader_nonformal_user_authorization_pending`

This gate is pending explicit user approval for the exact broader nonformal
scope above or a stricter subset. Do not run replay, generate candidates, train
CAMP, modify DP, promote selectors/atoms, or make safety/CAMP-over-DP claims
until that approval is present.
