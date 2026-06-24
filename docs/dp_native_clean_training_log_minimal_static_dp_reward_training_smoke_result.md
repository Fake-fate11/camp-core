# DP Native Clean Training Log Minimal Static DP Reward Training Smoke Result

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_minimal_nonformal_static_dp_reward_training_smoke
```

This gate executed the user-authorized minimal nonformal static DP-reward
trainer-pipeline smoke. It used only the fixed 12 clean selection logs under the
previous broader nonformal artifact root. It did not run replay, generate
candidates, modify Diffusion Planner, promote a selector/atom, or authorize any
deployable-checkpoint, safety, or CAMP-over-DP claim.

## Fixed Inputs

```text
input_root=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
selection_log_count=12
collection_summary.json_sha256=05c8c7056dbe7460cfac422b0f1081179021a9df80324a4378cec3bf6dc693f0
clean_dp_native_training_data_contract_validation.json_sha256=c2f8f1b10e9d1a8925886255e8ffa3af151ef1ceaab278027a50a9087f39a7f4
```

## Support Implementation

The existing robust trainer already had
`--require_dp_native_training_data_contract`, but the authorized `dp_reward`
label source belongs to `train_diffusion_planner_static_camp.py`. To satisfy
the exact authorized smoke command, the static trainer was extended with
default-off preflight switches:

```text
commit=b46626b4c28b961468825c5b351726d818bc14d8
script=scripts/integrations/train_diffusion_planner_static_camp.py
added=--require_dp_native_training_data_contract
added=--require_atom_schema
default_behavior_change=False
failure_behavior=fail closed before training if clean contract validation fails
summary_behavior=include dp_native_training_data_contract and atom_schema reports
test=camp_core/tests/test_diffusion_planner_static_camp_training_contract_preflight.py
```

Support validation:

```text
local_git_diff_check_exit=0
local_py_compile_exit=0
local_temp_rootdir_target_pytest=14 passed in 1.18s
autodl_py_compile_exit=0
autodl_target_pytest=11 passed in 0.52s
```

## AutoDL Execution

```text
run_root=/root/autodl-tmp/camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_b46626b4_20260624T062215Z
training_output_dir=/root/autodl-tmp/camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_b46626b4_20260624T062215Z/training_output
CAMP_HEAD=b46626b4c28b961468825c5b351726d818bc14d8
CAMP_origin/main=b46626b4c28b961468825c5b351726d818bc14d8
DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
training_exit=0
smoke_passed=True
```

Executed command shape:

```text
script=scripts/integrations/train_diffusion_planner_static_camp.py
input_logs=12 fixed camp_selection_log.json files under input_root
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
must_enable=--require_dp_native_training_data_contract
must_enable=--require_atom_schema
```

Forbidden options were not used:

```text
closed_loop_outcome label source
safety_cost_v1_hard_guarded label source
replay
candidate generation
Full36
formal seeds 11/12/13
Diffusion Planner modification
selector/atom promotion
deployable checkpoint claim
safety claim
CAMP-over-DP claim
```

## Smoke Result

```text
training_summary_exists=True
weights_exists=True
atom_scales_exists=True
label_source_dp_reward=True
reward_key_quality_without_progress=True
reward_progress_weight_2=True
selection_log_count_12=True
num_records=31
dropped_records_without_feasible_candidate=5
num_candidates=4
num_atoms=14
atom_schema_required=True
atom_schema_verified_records=36
dp_native_contract_passed=True
dp_native_contract_records=36
dp_native_contract_failed_records=[]
closed_loop_label_source_used=False
safety_cost_label_source_used=False
```

Static weight checks:

```text
weights_len_14=True
weights_finite=True
weights_nonnegative=True
weights_sum_one=True
trained_weights=[0.04678777248538632, 0.08203766243413003, 0.07317506984819322, 0.07354573640799164, 0.04306213171716468, 0.047387755484607504, 0.0513810287375614, 0.15010557282933143, 0.09689296654128951, 0.047226474441032, 0.09689296654128951, 0.06430357355918646, 0.09689296654128951, 0.030308322431546738]
```

Non-claim metrics:

```text
oracle_match_rate=0.1935483870967742
feasible_candidate_rate=0.8467741935483871
records_with_any_infeasible=8
```

These are pipeline-smoke diagnostics only. They are not evidence of safety
benefit, closed-loop performance, or CAMP superiority over DP Top-1.

Training summary caveat:

```text
Candidate-level DP rewards are model-based preferences, not counterfactual closed-loop outcomes. Closed-loop matched baselines remain required for final claims.
```

## SHA-256 Evidence

| Artifact | SHA-256 |
| --- | --- |
| `preflight.json` | `bb416195e42b2c2d37553c3676b76760dd98acb35e3d9524a39d8228096175e0` |
| `training_command.json` | `e37803f839fb067ef548b72e3950d14fe5c467c7d0f165c83a5bde52579fc63c` |
| `training_stdout_stderr.log` | `d532b0878d4ef01ad5fb931d9d7cb1dca2fbecb85cdf5ed1d1f81cc187cb2732` |
| `training_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `smoke_summary.json` | `54f15b657eec406b4f4f8d42f598c8f7527b881142c6a1e6b4206f6ff8983faa` |
| `smoke_summary.md` | `f97786567f9604808e6b9f231d9a6fc822ba438e32ed9d488eb005172939fcbd` |
| `training_output/training_summary.json` | `1a4019901ed93cc3a89d41984e552b9c263ea51c59d8fd60193b8fadd2acec1a` |
| `training_output/offline_weights_dp_static.npy` | `77c0276b0cebc9f6ed3c88865c1930097a5ce48e266e60b6cbaf65a9ebe849bb` |
| `training_output/atom_scales_dp_static.json` | `8046cac7b1aa43c7c0bcb83136828a813297e598084ff4924c66526b9bb0453c` |

## Decision

```text
status=minimal_nonformal_static_dp_reward_training_smoke_passed
training_smoke_executed=True
nondeployable_training_smoke_only=True
deployable_checkpoint_claimed=False
selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
replay_executed=False
candidate_generation_executed=False
Full36_run=False
formal_seeds_11_12_13_run=False
```

This result proves only that the clean DP-native selection logs can pass the
static trainer preflight and produce a finite 14D simplex static weight vector
under the authorized nonformal DP-reward smoke. It does not make the output
deployable and does not authorize promotion or claims.

## Next Gate

`dp_native_static_dp_reward_training_smoke_artifact_nonpromotion_static_audit_only`

The next gate should be read-only. It should inspect the fixed smoke artifact
and code boundary to confirm that the produced static weights/scales are only a
nondeployable smoke artifact and cannot be treated as a promoted CAMP selector
or evidence of safety/CAMP-over-DP improvement.
