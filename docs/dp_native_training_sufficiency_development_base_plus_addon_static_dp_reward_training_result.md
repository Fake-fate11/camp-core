# DP Native Training Sufficiency Development Base Plus Add-On Static DP Reward Training Result

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_user_authorized_execution
```

This artifact records the user-authorized static DP-reward training smoke over
the fixed base-plus-add-on clean selection logs. The run used only existing
`camp_selection_log.json` files and did not run replay, generate candidates,
modify Diffusion Planner, use closed-loop outcome labels, use SafetyCost v1
labels, promote selector/atoms, or make any deployable-checkpoint, safety, or
CAMP-over-DP claim.

## Fixed Inputs

```text
base_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_development_collection_73aec55_20260624T075109Z
additive_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_additive_clean_collection_79343f9_20260624T082432Z
training_smoke_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z
training_dir=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training
```

## HEAD Evidence

```text
local_HEAD=e15feaa8f45f9dac5b2c012eccb6997ffbe8df0d
origin_main=e15feaa8f45f9dac5b2c012eccb6997ffbe8df0d
github_refs_heads_main=e15feaa8f45f9dac5b2c012eccb6997ffbe8df0d
autodl_CAMP_HEAD=e15feaa8f45f9dac5b2c012eccb6997ffbe8df0d
autodl_CAMP_origin_main=e15feaa8f45f9dac5b2c012eccb6997ffbe8df0d
autodl_CAMP_github_main=e15feaa8f45f9dac5b2c012eccb6997ffbe8df0d
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required_DP_fixed_commit=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

AutoDL status during execution:

```text
CAMP status:
## main...origin/main
untracked unrelated prior-session artifacts remain ignored

DP status:
## tier4-main...origin/tier4-main
```

## Authorized Scope Actually Run

The authorized command used the static DP-reward trainer:

```text
script=scripts/integrations/train_diffusion_planner_static_camp.py
mode=static
training_scope=feasible_ranking
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
require_dp_native_training_data_contract=True
require_atom_schema=True
```

`mode=static` is implicit in `train_diffusion_planner_static_camp.py`.
`training_scope=feasible_ranking` is implicit in the DP-reward feasible
candidate-preference training path. The command did not pass or enable any
closed-loop outcome label source, SafetyCost v1 label source, replay script,
candidate-generation script, Diffusion Planner setting, selector-promotion
operation, or atom-promotion operation.

Combined fixed-log input:

```text
base_selection_log_count=24
additive_selection_log_count=16
combined_selection_log_count=40
combined_records=200
combined_usable_feasible_records=140
combined_unusable_records=60
combined_counts_by_route={"nishishinjuku_lane_change": 40, "sample_normal": 80, "sample_tl": 80}
combined_usable_by_route={"sample_normal": 80, "sample_tl": 60}
combined_counts_by_seed={"101": 30, "102": 30, "103": 30, "104": 30, "105": 20, "106": 20, "107": 20, "108": 20}
combined_counts_by_traffic_lights={"off": 100, "on": 100}
combined_candidate_count_values={"4": 200}
```

## Result

```text
training_exit=0
training_duration_s=0.691
artifact_static_audit_passed=True
artifact_static_audit_errors=[]
training_type=diffusion_planner_static_candidate_preference
mode=static
training_scope=feasible_ranking
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
selection_log_count=40
training_num_records=140
dropped_records_without_feasible_candidate=60
num_candidates=4
num_atoms=14
atom_schema_version=dp_camp_v10_14d
dp_native_training_data_contract_passed=True
dp_native_training_data_contract_records=200
dp_native_training_data_contract_selection_log_count=40
weights_sum=1.0
weights_min=0.03438328162022459
weights_max=0.11034760681581661
oracle_match_rate=0.3142857142857143
feasible_candidate_rate=0.9107142857142857
records_with_any_infeasible=26
```

The 60 dropped records are the records with no feasible candidate under the
clean DP-reward feasible mask. This matches the preceding data-sufficiency
artifact: 200 combined records and 140 usable feasible records. Dropping those
records is a fixed-log training filter, not new candidate generation or replay.

## Clean-Boundary Checks

```text
closed_loop_outcome_label_source_used=False
safety_cost_v1_label_source_used=False
replay_executed=False
candidate_generation_executed=False
full36_executed=False
formal_seeds_executed=False
dp_modified=False
selector_promotion_executed=False
atom_promotion_executed=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The generated `offline_weights_dp_static.npy` and `atom_scales_dp_static.json`
are training-smoke artifacts only. They are not promoted into runtime
configuration and are not deployable-checkpoint evidence without later
separate audit and matched evaluation gates.

## Verification

Remote fixed-artifact verification:

```text
remote_training_exit=0
remote_artifact_static_audit_passed=True
remote_training_summary_exists=True
remote_offline_weights_exists=True
remote_atom_scales_exists=True
remote_weights_simplex_nonnegative=True
remote_atom_schema_version=dp_camp_v10_14d
remote_dp_native_training_data_contract_passed=True
remote_replay_executed=False
remote_candidate_generation_executed=False
remote_dp_modified=False
```

Local narrow checks:

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_result.md camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_result.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_result.py
exit=0

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_result.py -q
3 passed in 0.02s
exit=0
```

The direct Windows repo pytest invocation for the same target aborted before
collecting this test because pytest enumerated a pre-existing unavailable
long-path test node unrelated to this documentation-only change:
`test_diffusion_planner_residual_comfort_remediation_followup_materially_different_generator_guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_implementation_plan.py`.
The target test was therefore run from a temporary copy containing only the
target test and target doc; no repo files were cleaned or modified for that
workaround.

## Remote SHA-256 Evidence

Fixed root files and training artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `preflight.json` | `33800dab9a078b8fd463bc233c80599ede06f82eccb296e6d82923a563cc1e02` |
| `run_static_training_smoke.py` | `76d44af4d4ffe823f050c79243cb0bcbf271d7a5cc72901e4c9ac68e366b8247` |
| `training_smoke_summary.json` | `632b4012db653f9c71cfdcd8731e14fe75cc06c91de75d41af03636f772f1cb8` |
| `training_smoke_summary.md` | `3f8193eff6bafd10d3374cfeddc997712fda102c9c7bb050ea24ac289943e2ab` |
| `training_stdout_stderr.log` | `44b938cd653b988250803d225c97f6232f2b431332c2369e8496635d15103bc2` |
| `training_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `artifact_static_audit.json` | `fcdd0b504f4fae1e46c20ce1bb7854559b9b2879d83451af2a6c52e457e3ef34` |
| `training/training_summary.json` | `9f1b7031d97d769f8e9e75d31ed9883c089eb28781d9f65d7e6d5f195fd2d92f` |
| `training/offline_weights_dp_static.npy` | `01d80d8ccdfd68b23f86b2ed376a2f2dbd5c8ae986b5cebe8f8a59b0c2bdb5c5` |
| `training/atom_scales_dp_static.json` | `7c0327ea6f1f534ca4f4d69d423ecc68def14d5498748f803e644818d4e17e7c` |

## Decision

```text
status=base_plus_addon_static_dp_reward_training_smoke_passed_nonpromotion
training_execution_authorized=True
training_execution_scope=static_dp_reward_feasible_ranking_smoke
training_smoke_passed=True
artifact_static_audit_passed=True
clean_dp_native_training_data_contract_passed=True
atom_schema_required_and_verified=True
static_weights_created=True
atom_scales_created=True
camp_retraining_for_deployment_authorized=False
camp_retraining_for_deployment_executed=False
replay_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This is a nondeployable static training smoke. It proves that the fixed clean
base-plus-add-on DP-native logs can produce a finite nonnegative simplex static
weight vector under the DP-reward feasible-ranking label contract. It does not
prove closed-loop safety, does not prove CAMP beats DP Top-1, and does not
authorize runtime selector promotion.

## Next Gate

`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_user_authorization_pending`

The next gate requires explicit user authorization before any replay or
evaluation command is run. A later evaluation scope must remain nonformal,
avoid Full36 and formal seeds 11/12/13, keep DP fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, avoid reference_blend, guidance,
postprocess/postselection, closed-loop outcome labels for online selection,
selector/atom promotion, deployable-checkpoint claims, safety claims, and
CAMP-over-DP claims.
