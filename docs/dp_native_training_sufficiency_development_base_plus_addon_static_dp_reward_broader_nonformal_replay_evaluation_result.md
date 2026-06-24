# DP Native Base Plus Add-On Static DP Reward Broader Nonformal Replay Evaluation Result

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_user_authorized_execution
```

This artifact records the user-authorized broader nonformal replay/evaluation
development smoke for the fixed static DP-reward training artifact. The run
used CAMP only as a static fixed-candidate reranker over DP-native replay
candidates. It did not run Full36, did not use formal seeds 11/12/13, did not
modify Diffusion Planner, did not enable reference_blend, guidance,
postprocess/postselection, or closed-loop outcomes as online selector inputs,
and did not promote the selector, atoms, runtime configuration, deployable
checkpoint, safety claim, or CAMP-over-DP claim.

## Fixed Inputs

```text
training_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z
training_dir=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training
offline_weights=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training/offline_weights_dp_static.npy
atom_scales=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training/atom_scales_dp_static.json
evaluation_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_broader_nonformal_eval_1c235eb_20260624T092550Z
```

## HEAD Evidence

```text
local_HEAD_before_result_commit=1c235ebcad52143297852d4873d345710be31680
origin_main_before_result_commit=1c235ebcad52143297852d4873d345710be31680
github_refs_heads_main_before_result_commit=1c235ebcad52143297852d4873d345710be31680
autodl_CAMP_HEAD=1c235ebcad52143297852d4873d345710be31680
autodl_CAMP_origin_main=1c235ebcad52143297852d4873d345710be31680
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

```text
run_count=12
routes=sample_normal,sample_tl,nishishinjuku_lane_change
seeds=109,110
traffic_lights=off,on
steps=5
num_candidates=4
candidate_noise_strategy=iid
candidate_noise_scale=1.0
selector_mode=static
feasibility_source=dp_reward
provenance_logging=True
weights=offline_weights_dp_static.npy
atom_scales=atom_scales_dp_static.json
advance_mode=perfect
max_npcs=0
spawn_probability=0.3
```

Route assets:

```text
sample_normal=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
sample_tl=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
nishishinjuku_lane_change=/root/autodl-tmp/camp_dp_assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl
sample_map=/root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm
nishishinjuku_map=/root/autodl-tmp/camp_dp_assets/nishishinjuku_no_ros.osm
```

The replay command did not include reference_blend, guidance, closed-loop
outcome collection, PerfectTracker command postselection, traffic-light hybrid
postselection, splice/shadow candidate rules, Full36, or formal seeds.
`dp_native_replay_candidate_sampling_executed=True` because replay requested
DP-native K=4 candidates; `new_candidate_generator_executed=False` because no
CAMP-side materialized generator, splice generator, reference blend, guidance,
or postselection route was enabled.

## Result

```text
passed=True
all_replay_exits_zero=True
replay_exit_counts={"0": 12}
run_count=12
total_selection_records=60
expected_selection_records=60
total_provenance_records=60
total_payload_valid_records=60
total_prepost_equal_records=60
total_no_candidate_row_append_records=60
total_no_coordinate_heading_speed_rewrite_records=60
total_selected_index_in_range_records=60
total_records_with_feasible_candidate=45
total_records_without_feasible_candidate=15
total_records_with_selected_feasible_candidate=45
selected_index_counts={"0": 11, "1": 9, "2": 22, "3": 18}
schema_version=dp_native_static_dp_reward_broader_nonformal_eval_development_result_v1
```

Route diagnostics:

| Route | Records | With feasible | Without feasible | Mean candidate feasible rate | Mean fallback rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| `sample_normal` | 20 | 20 | 0 | 1.0 | 0.0 |
| `sample_tl` | 20 | 9 | 11 | 0.3625 | 0.55 |
| `nishishinjuku_lane_change` | 20 | 16 | 4 | 0.7375 | 0.2 |

Per-run diagnostics:

| Run | Exit | Records | With feasible | Without feasible | Candidate feasible rate | Fallback rate | Selection log SHA-256 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `sample_normal_seed109_tl_off_static` | 0 | 5 | 5 | 0 | 1.0 | 0.0 | `81b84a28180b18cc7eb2766ac4b380e82e60c63060eb56e692e430d0ffcf186b` |
| `sample_normal_seed109_tl_on_static` | 0 | 5 | 5 | 0 | 1.0 | 0.0 | `7b2a8d07e7daf6519b97d1c42da6244041b101049bbd2ef25077f8f28a184e38` |
| `sample_normal_seed110_tl_off_static` | 0 | 5 | 5 | 0 | 1.0 | 0.0 | `835d01775e05e48e3634f25f77aa9185d30dcdf3fd9a05301ade5885837b4315` |
| `sample_normal_seed110_tl_on_static` | 0 | 5 | 5 | 0 | 1.0 | 0.0 | `58ba82ef7e810d9eb46f80ce599f8a746c256e603ed1dfa5cb820164f6b86fa1` |
| `sample_tl_seed109_tl_off_static` | 0 | 5 | 5 | 0 | 0.85 | 0.0 | `8845280464fe0ee88d6bc720affbbcdbe4a8030d9f18cc3e482f1472d44bf453` |
| `sample_tl_seed109_tl_on_static` | 0 | 5 | 0 | 5 | 0.0 | 1.0 | `6ab0e6f88d3154973d63b50eae7b233fe90e47ffd2cf8238f3eddaf58e503d8a` |
| `sample_tl_seed110_tl_off_static` | 0 | 5 | 4 | 1 | 0.6 | 0.2 | `a3194ee4ea86a8e34fcb36ba2b0c39625b377c910c6636d1ad3e3e662e83e1d6` |
| `sample_tl_seed110_tl_on_static` | 0 | 5 | 0 | 5 | 0.0 | 1.0 | `1c4d1b610b95769e3f58d60112b7a6d65a8117a0d3d9bd1f7ee01e3f3c933766` |
| `nishishinjuku_lane_change_seed109_tl_off_static` | 0 | 5 | 4 | 1 | 0.7 | 0.2 | `1e3ea2c036de900e9253c5421163c187a3bd7b2da2b8d7966ba58c8b7af2c185` |
| `nishishinjuku_lane_change_seed109_tl_on_static` | 0 | 5 | 4 | 1 | 0.7 | 0.2 | `e193850be69943fe890383e2181460621e25e33eee4dff87a4b2f35ec32b4e5a` |
| `nishishinjuku_lane_change_seed110_tl_off_static` | 0 | 5 | 4 | 1 | 0.8 | 0.2 | `31000b5a955661bd18a2ae7538a80252d7aa038663403e3a7884c402922c4d0b` |
| `nishishinjuku_lane_change_seed110_tl_on_static` | 0 | 5 | 4 | 1 | 0.75 | 0.2 | `e61f901a270540277f69af2a336cb1f6748271900aa7906c44c17b7dd2998fad` |

The broader smoke confirms that the fixed static DP-reward weights can be
loaded across the three development routes while preserving candidate tensor
provenance. It also narrows the fallback/feasibility problem: `sample_tl`
traffic-light-on runs have zero records with a feasible candidate, `sample_tl`
traffic-light-off has partial support, `nishishinjuku_lane_change` has a
smaller recurring no-feasible tail, and `sample_normal` is clean in this
scope. This is a development diagnostic, not safety evidence.

## Clean-Boundary Checks

```text
nonformal_replay_evaluation_development_smoke_only=True
full36_executed=False
formal_seeds_executed=False
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
new_candidate_generator_executed=False
dp_native_replay_candidate_sampling_executed=True
```

The replay produces validation summaries from closed-loop state transitions,
but those transitions are not used as online selector inputs. The selector
remains the static affine atom-score reranker over the immutable DP-native
candidate tensor.

## Verification

Remote fixed-artifact verification:

```text
remote_broader_nonformal_eval_summary_exists=True
remote_broader_nonformal_eval_summary_passed=True
remote_all_replay_exits_zero=True
remote_total_selection_records=60
remote_total_provenance_records=60
remote_total_prepost_equal_records=60
remote_total_no_candidate_row_append_records=60
remote_total_no_coordinate_heading_speed_rewrite_records=60
remote_total_selected_index_in_range_records=60
remote_total_closed_loop_outcome_online_input_records=0
remote_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
remote_reference_blend_enabled=False
remote_guidance_enabled=False
remote_postprocess_postselection_enabled=False
remote_closed_loop_outcome_online_input_used=False
remote_dp_modified=False
remote_selector_promotion_executed=False
remote_atom_promotion_executed=False
```

Local narrow checks:

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_result.md camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_result.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_result.py
exit=0

python -m pytest camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_result.py -q
exit=1
reason=pre-existing unavailable long-path test node interrupted collection before target test ran

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_result.py -q
4 passed
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

Fixed root files:

| Artifact | SHA-256 |
| --- | --- |
| `preflight.json` | `dd30470be47b81c15382b2bdfddb1fdaea5aa76b99805f83d24cfa74058d5476` |
| `run_broader_nonformal_eval.py` | `66cfb0479b7b6e050f22e4d2f96323048464bd2cf63cd3eb58a684d978d2025d` |
| `broader_nonformal_eval_summary.json` | `c39fa6278431e08ee16b7b45f6645e43fa46f9951981c1fff8fa1809778aea07` |
| `broader_nonformal_eval_summary.md` | `738c91623cd344f53cbf8ea76e1706f82272f267619fbc91404a29d7c7070f62` |

## Decision

```text
status=base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_passed_fallback_feasibility_diagnostic_nonpromotion
broader_nonformal_replay_evaluation_authorized=True
broader_nonformal_replay_evaluation_development_smoke_passed=True
static_dp_reward_weights_loaded=True
static_dp_reward_atom_scales_loaded=True
candidate_tensor_provenance_logging_verified=True
candidate_tensor_prepost_hash_equal_all_records=True
sample_normal_clean_feasible_support_observed=True
sample_tl_fallback_feasibility_blocker_observed=True
nishishinjuku_lane_change_partial_fallback_feasibility_blocker_observed=True
camp_retraining_for_deployment_authorized=False
camp_retraining_for_deployment_executed=False
full36_authorized=False
formal_seed_authorized=False
dp_modification_authorized=False
reference_blend_authorized=False
guidance_authorized=False
postprocess_postselection_authorized=False
closed_loop_outcome_online_input_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This is a nondeployable broader nonformal development smoke. It proves only
that the fixed static DP-reward training artifact can be exercised over a
broader DP-native replay scope while preserving candidate tensor provenance.
It does not prove closed-loop safety, does not prove CAMP beats DP Top-1, does
not authorize CAMP retraining for deployment, and does not authorize runtime
selector or atom promotion.

## Next Gate

`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_fallback_feasibility_attribution_only`

The next gate is read-only and must use only the fixed broader nonformal
evaluation artifact above. It may attribute why `sample_tl` and
`nishishinjuku_lane_change` produce records without any feasible candidate
under the DP-reward feasibility mask, but it must not run replay, generate
candidates, train CAMP, modify DP, enable reference_blend/guidance/postprocess
or postselection, promote selector/atoms, or make safety/CAMP-over-DP claims.
