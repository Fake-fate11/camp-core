# DP Native Base Plus Add-On Static DP Reward Nonformal Replay Evaluation Result

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_user_authorized_execution
```

This artifact records the user-authorized minimal nonformal replay/evaluation
smoke for the fixed static DP-reward training artifact. The run loaded only the
fixed training outputs listed below and used CAMP as a static fixed-candidate
reranker over DP-native replay candidates. It did not run Full36, did not use
formal seeds 11/12/13, did not modify Diffusion Planner, did not enable
reference_blend, guidance, postprocess/postselection, or closed-loop outcomes
as online selector inputs, and did not promote the selector, atoms, runtime
configuration, deployable checkpoint, safety claim, or CAMP-over-DP claim.

## Fixed Inputs

```text
training_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z
training_dir=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training
offline_weights=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training/offline_weights_dp_static.npy
atom_scales=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_training_e15feaa_20260624T084652Z/training/atom_scales_dp_static.json
evaluation_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_base_plus_addon_static_dp_reward_nonformal_eval_2f9656f_20260624T090404Z
```

## HEAD Evidence

```text
local_HEAD_before_result_commit=2f9656f188d027643573511fb4f8853857af122d
origin_main_before_result_commit=2f9656f188d027643573511fb4f8853857af122d
github_refs_heads_main_before_result_commit=2f9656f188d027643573511fb4f8853857af122d
autodl_CAMP_HEAD=2f9656f188d027643573511fb4f8853857af122d
autodl_CAMP_origin_main=2f9656f188d027643573511fb4f8853857af122d
autodl_CAMP_github_main=2f9656f188d027643573511fb4f8853857af122d
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

The authorized smoke ran two minimal nonformal replay/evaluation jobs:

```text
run_count=2
steps=3
num_candidates=4
candidate_noise_strategy=iid
candidate_noise_scale=1.0
selector_mode=static
feasibility_source=dp_reward
provenance_logging=True
weights=offline_weights_dp_static.npy
atom_scales=atom_scales_dp_static.json
```

Runs:

| Run | Route | Seed | Traffic lights |
| --- | --- | --- | --- |
| `sample_normal_seed109_tl_off_static` | `/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl` | `109` | `off` |
| `sample_tl_seed109_tl_on_static` | `/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl` | `109` | `on` |

The replay command used:

```text
script=scripts/integrations/run_diffusion_planner_camp_replay.py
diffusion_repo=/root/autodl-tmp/Diffusion-Planner
model_path=/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth
model_args=/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json
config=/root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json
device=cuda
advance_mode=perfect
max_npcs=0
spawn_probability=0.3
reward_config=configs/integrations/dp_camp_reward_eval.json
camp_candidate_tensor_provenance_logging=True
```

The command did not include reference_blend, guidance, closed-loop outcome
collection, PerfectTracker command postselection, traffic-light hybrid
postselection, splice/shadow candidate rules, Full36, or formal seeds.
`dp_native_replay_candidate_sampling_executed=True` because replay requested
DP-native K=4 candidates; `new_candidate_generator_executed=False` because no
CAMP-side materialized generator, splice generator, reference blend, guidance,
or postselection route was enabled.

## Result

```text
passed=True
all_replay_exits_zero=True
replay_exit_counts={"0": 2}
run_count=2
total_selection_records=6
total_provenance_records=6
total_prepost_equal_records=6
total_records_with_feasible_candidate=3
schema_version=dp_native_static_dp_reward_nonformal_eval_smoke_result_v1
```

Per-run summary:

| Run | Replay exit | Selection records | Provenance records | Pre/post equal records | Records with feasible candidate | Selected index counts |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `sample_normal_seed109_tl_off_static` | `0` | 3 | 3 | 3 | 3 | `{"0": 1, "2": 1, "3": 1}` |
| `sample_tl_seed109_tl_on_static` | `0` | 3 | 3 | 3 | 0 | `{"2": 2, "3": 1}` |

Validation observations:

```text
sample_normal_candidate_feasible_rate=1.0
sample_normal_fallback_rate=0.0
sample_normal_records_with_feasible_candidate=3
sample_tl_candidate_feasible_rate=0.0
sample_tl_fallback_rate=1.0
sample_tl_records_with_feasible_candidate=0
```

The smoke therefore confirms that the static DP-reward weights can be loaded
into the fixed-candidate replay path, that CAMP records candidate tensor
provenance for every selector step, and that the pre-selector and post-selector
candidate tensor hashes remained equal for every selector step. It also records
that the traffic-light smoke still has zero feasible candidates under the
DP-reward feasibility mask and falls back on all three selector steps. That is
a development finding, not a safety benefit.

## Clean-Boundary Checks

```text
nonformal_replay_evaluation_smoke_only=True
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

The replay produces evaluation state and validation summaries, but those
closed-loop state transitions are not used as online selector inputs. The
selector remains the static affine atom-score reranker over the immutable
DP-native candidate tensor.

## Verification

Remote fixed-artifact verification:

```text
remote_nonformal_eval_summary_exists=True
remote_nonformal_eval_summary_passed=True
remote_all_replay_exits_zero=True
remote_total_selection_records=6
remote_total_provenance_records=6
remote_total_prepost_equal_records=6
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
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_result.md camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_result.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_result.py
exit=0

python -m pytest camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_result.py -q
exit=1
reason=pre-existing unavailable long-path test node interrupted collection before target test ran

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_nonformal_replay_evaluation_result.py -q
3 passed
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
| `preflight.json` | `685f09432e78da2b233dd63c9d65c93c34122bac5370e01c27e7d5538f7c639e` |
| `run_nonformal_eval_smoke.py` | `38432b930aba817adeadd186eb18197ed006808be63a8cd0a87441cf083f95be` |
| `nonformal_eval_summary.json` | `3e37c620ae9c545be15f2e62c13c8f1c43687990d5e9a4e84770956b6a8d647f` |
| `nonformal_eval_summary.md` | `84bc54bfd4f1360079f96c1baa6334e8bfd856549dcfc6416adfb2c77a1f5cdd` |

Per-run artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `sample_normal_seed109_tl_off_static/command.json` | `13329be6ed8e8f85a499ad2ed2e8d31c9ae5e26d3c20a7013b1bf7db18ca805e` |
| `sample_normal_seed109_tl_off_static/replay_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `sample_normal_seed109_tl_off_static/replay_stdout_stderr.log` | `f5dc4c1d2952921ba4658f6141f63fe49763742eec0370f53543c9966d9e400b` |
| `sample_normal_seed109_tl_off_static/camp_selection_log.json` | `1fb2cce83d2a9bb08366d16e0d0d9cc8daae81b49169c26f0eeaebe940ab0ab4` |
| `sample_normal_seed109_tl_off_static/camp_replay_summary.json` | `e7445f793218410df59d46d0ca568360868b199ff8304d1b5f6de9a807d9c74c` |
| `sample_normal_seed109_tl_off_static/camp_validation_summary.json` | `a52bd09383e22fc7e374f98a088fbfc1d34c91cefc00011d7f53f8a3db63b1e3` |
| `sample_tl_seed109_tl_on_static/command.json` | `45d3faccbf3552b90d75a1f825f7a321aa2e88555e148c758d5b63f31314b809` |
| `sample_tl_seed109_tl_on_static/replay_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `sample_tl_seed109_tl_on_static/replay_stdout_stderr.log` | `53c08e9198a1b7b9afe347b087e00e5a796dc46aa7d63849239eec0508ac74a3` |
| `sample_tl_seed109_tl_on_static/camp_selection_log.json` | `3f6cf3a1d2b02ed0bc4e9a1d9f0bf3971826f837e0c13d229b35e2d34b31b978` |
| `sample_tl_seed109_tl_on_static/camp_replay_summary.json` | `1d8e8b3a940af1be130e3fb49137cddda46ee078421f0ea6228928a9fb2c5c2d` |
| `sample_tl_seed109_tl_on_static/camp_validation_summary.json` | `ea8d051f8a57305d0a32aae7b96efc05d4f6ab71a48c67b7cd8271c37c7a0f78` |

## Decision

```text
status=base_plus_addon_static_dp_reward_nonformal_replay_evaluation_smoke_passed_nonpromotion
nonformal_replay_evaluation_authorized=True
nonformal_replay_evaluation_smoke_passed=True
static_dp_reward_weights_loaded=True
static_dp_reward_atom_scales_loaded=True
candidate_tensor_provenance_logging_verified=True
candidate_tensor_prepost_hash_equal_all_records=True
sample_tl_zero_feasible_candidate_records_observed=True
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

This is a nondeployable nonformal smoke. It proves only that the fixed static
DP-reward training artifact can be exercised in a minimal DP-native replay
path while preserving candidate tensor provenance. It does not prove
closed-loop safety, does not prove CAMP beats DP Top-1, does not authorize
CAMP retraining for deployment, and does not authorize runtime selector or
atom promotion.

## Next Gate

`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_broader_nonformal_replay_evaluation_user_authorization_pending`

The next gate requires explicit user authorization before any additional
replay/evaluation command is run. A broader nonformal evaluation must remain
development-only, avoid Full36 and formal seeds 11/12/13, keep DP fixed at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, avoid reference_blend, guidance,
postprocess/postselection, closed-loop outcomes as online selector inputs,
selector/atom promotion, deployable-checkpoint claims, safety claims, and
CAMP-over-DP claims.
