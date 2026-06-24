# DP Native Static DP Reward Training Smoke Artifact Nonpromotion Audit

Date: 2026-06-24

Gate:

```text
dp_native_static_dp_reward_training_smoke_artifact_nonpromotion_static_audit_only
```

This gate is a read-only/static audit of the fixed minimal static DP-reward
training smoke artifact. It does not run replay, generate candidates, retrain
CAMP, modify Diffusion Planner, promote a selector/atom, or authorize any
safety or CAMP-over-DP claim.

## Heads

```text
local_HEAD=7470a60ee502d01dbf1d24703fd2960cfa655f27
origin_main=7470a60ee502d01dbf1d24703fd2960cfa655f27
github_refs_heads_main=7470a60ee502d01dbf1d24703fd2960cfa655f27
autodl_CAMP_HEAD=7470a60ee502d01dbf1d24703fd2960cfa655f27
autodl_CAMP_origin_main=7470a60ee502d01dbf1d24703fd2960cfa655f27
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Tracked worktree files were clean before this audit. Existing unrelated
untracked handoff/session files were intentionally left untouched.

## Source Hashes

```text
docs/dp_camp_mathematical_contract.md=d52cec8159b0ff46f0abde2c6c492806fbc3db25a2f3b89e1886c0828b1cafd2
docs/dp_camp_benders_formalization.md=5fe5e6830af84ac9dd1477c44a4db8be317c6f807b226be4af851de24dbbdf12
docs/dp_camp_benders_compatible_atom_audit.md=2b42e35f2199603589f7df074c40e627858051bd23190ff0c42002df817a5f0b
docs/dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_result.md=3a9b6494fe2b5ff4e2c9677f45ddb196da76739609ba8db910d8b2eabd65dfa4
scripts/integrations/train_diffusion_planner_static_camp.py=c9e87b2b9b0359bd7fde9afdfb1746f7a5b77eaa1814af427d3798a97e575b13
camp_core/camp_core/integrations/diffusion_planner.py=6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7
```

## Fixed Smoke Artifact

```text
run_root=/root/autodl-tmp/camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_b46626b4_20260624T062215Z
fixed_input_root=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
selection_log_count=12
training_exit=0
smoke_passed=True
```

Remote artifact SHA-256 evidence, re-read with Paramiko/SFTP:

```text
preflight.json=bb416195e42b2c2d37553c3676b76760dd98acb35e3d9524a39d8228096175e0
training_command.json=e37803f839fb067ef548b72e3950d14fe5c467c7d0f165c83a5bde52579fc63c
training_stdout_stderr.log=d532b0878d4ef01ad5fb931d9d7cb1dca2fbecb85cdf5ed1d1f81cc187cb2732
training_exit.txt=9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa
smoke_summary.json=54f15b657eec406b4f4f8d42f598c8f7527b881142c6a1e6b4206f6ff8983faa
smoke_summary.md=f97786567f9604808e6b9f231d9a6fc822ba438e32ed9d488eb005172939fcbd
training_output/training_summary.json=1a4019901ed93cc3a89d41984e552b9c263ea51c59d8fd60193b8fadd2acec1a
training_output/offline_weights_dp_static.npy=77c0276b0cebc9f6ed3c88865c1930097a5ce48e266e60b6cbaf65a9ebe849bb
training_output/atom_scales_dp_static.json=8046cac7b1aa43c7c0bcb83136828a813297e598084ff4924c66526b9bb0453c
```

The command artifact contains only the authorized static trainer invocation:

```text
script=scripts/integrations/train_diffusion_planner_static_camp.py
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
enabled=--require_dp_native_training_data_contract
enabled=--require_atom_schema
forbidden_hits=[]
nondeployable_training_smoke_only=True
```

## Nonpromotion Boundary

The training summary reports:

```text
training_type=diffusion_planner_static_candidate_preference
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
num_records=31
dropped_records_without_feasible_candidate=5
num_candidates=4
num_atoms=14
atom_schema_version=dp_camp_v10_14d
weights_path=/root/autodl-tmp/camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_b46626b4_20260624T062215Z/training_output/offline_weights_dp_static.npy
atom_scales_path=/root/autodl-tmp/camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_b46626b4_20260624T062215Z/training_output/atom_scales_dp_static.json
```

The smoke summary records the nonpromotion flags:

```text
nondeployable_training_smoke_only=True
deployable_checkpoint_claimed=False
selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
replay_executed=False
candidate_generation_executed=False
full36_run=False
formal_seeds_11_12_13_run=False
```

The produced `offline_weights_dp_static.npy` and
`atom_scales_dp_static.json` are remote training-output files only. They are not
present as repo-tracked runtime assets. The online `CAMPSelector` loads static
weights only when a caller explicitly supplies `checkpoint_path` or
`static_weights_path`; this smoke run does not modify those call sites,
Diffusion Planner, or any deployment configuration.

The local code boundary therefore remains:

```text
DP fixed candidates -> CAMP atoms/masks -> normalized atoms @ explicit weights -> argmin selected_index
```

The smoke artifact is evidence that the trainer pipeline can write a finite
14D simplex vector from clean DP-native logs. It is not evidence that this
vector is deployable, promoted, safe, or superior to DP Top-1.

## Verification

Local/static:

```text
git status --short --branch
git fetch --prune origin
git rev-parse HEAD origin/main
git ls-remote origin refs/heads/main
rg --files | rg "(offline_weights_dp_static|atom_scales_dp_static|camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke|static_dp_reward_training_smoke|redstop|checkpoint|weights.*\\.npy|atom_scales.*\\.json)$"
result: no repo artifact path match
```

Remote/read-only:

```text
Paramiko/SFTP read fixed run_root JSON and binary artifacts
sha256 verified for all 9 fixed smoke files
autodl_CAMP_HEAD=7470a60ee502d01dbf1d24703fd2960cfa655f27
autodl_CAMP_origin_main=7470a60ee502d01dbf1d24703fd2960cfa655f27
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Static contract test:

```text
test=camp_core/tests/test_diffusion_planner_static_dp_reward_smoke_nonpromotion_audit.py
purpose=prove the local audit records nonpromotion flags and the runtime selector has no hard-coded smoke artifact path
git_diff_check_exit=0
local_py_compile_exit=0
local_pytest_default_root_exit=1
local_pytest_default_root_blocker=existing Windows long-path collection error before target tests ran
local_short_path_target_pytest=3 passed in 0.28s
```

## Decision

```text
status=static_dp_reward_training_smoke_artifact_nonpromotion_audit_passed
artifact_nonpromotion_confirmed=True
smoke_artifact_fixed=True
smoke_artifact_sha_verified=True
repo_tracked_runtime_artifact_present=False
runtime_selector_hardcodes_smoke_artifact=False
deployable_checkpoint_claimed=False
selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
replay_executed=False
candidate_generation_executed=False
camp_retraining_executed=False
```

This closes the static DP-reward smoke branch as a nonpromotion training-pipe
smoke only.

## Next Gate

`dp_native_candidate_tensor_provenance_payload_implementation_authorization_only`

The next gate may only decide whether the minimal default-off candidate tensor
provenance payload implementation is authorized. It must not run replay,
generate candidates, retrain CAMP, promote atoms/selectors, modify DP, or make
claims.
