# DP Native Training Sufficiency Preflight Artifact Audit

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_preflight_artifact_audit_only
```

This gate is a read-only audit of the fixed preflight validator output for the
existing clean DP-native selection logs. It does not run replay, generate
candidates, train CAMP, modify Diffusion Planner, promote a selector/atom, or
authorize any deployable checkpoint, safety, or CAMP-over-DP claim.

## Heads

```text
local_HEAD=4dec4d270bcbb7144f3b60ae999f3d05b37a0921
origin_main=4dec4d270bcbb7144f3b60ae999f3d05b37a0921
github_refs_heads_main=4dec4d270bcbb7144f3b60ae999f3d05b37a0921
autodl_CAMP_HEAD=4dec4d270bcbb7144f3b60ae999f3d05b37a0921
autodl_CAMP_origin_main=4dec4d270bcbb7144f3b60ae999f3d05b37a0921
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Tracked worktree files were clean before this audit. Existing unrelated
untracked handoff/session files were intentionally left untouched.

## Fixed Input

```text
source_artifact=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
selection_log_count=12
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
mode=static_preflight_only
training_scope=feasible_ranking_preflight_only
```

The `reward_progress_weight` value is recorded as command metadata for the
same DP-reward label family used by the prior static smoke. This preflight
does not recompute labels or train weights.

## Source Hashes

```text
scripts/integrations/validate_dp_native_training_sufficiency_preflight.py=0153a8dbde51f6167047222490c5974b1bfe425c88d2d175f920b6c3098255d9
camp_core/tests/test_dp_native_training_sufficiency_preflight.py=3afea74af9c1852a733f7c695f32a9e7616181acbf69eb27959748f045c72e34
docs/dp_native_training_sufficiency_preflight_validator_implementation.md=6c914f2b1599a73d111b5a8573e7bbfb9fad5cd47f55023be6b9c8f40e27101b
```

## Remote Audit Artifact

```text
run_root=/root/autodl-tmp/camp_dp_native_training_sufficiency_preflight_artifact_audit_4dec4d2_20260624T072311Z
python=/root/miniconda3/envs/camp/bin/python
validator_exit=1
validator_exit_expected=True
report_passed=False
```

The nonzero validator exit is the expected fail-closed result for an
insufficient development-training coverage profile. It is not a replay,
training, or runtime failure.

Remote SHA-256 evidence:

```text
heads.json=1f8e43ff9c19c6d4cb3d39a18ef12e13f8cb0a3f6d1838d6179d3750ade274c0
preflight_command.json=bea8d134588f54e53b1878f0a5a395a35a2534feb6bacc2b1161ff0c6636ca9f
preflight_exit.txt=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865
preflight_report.json=7fb3328894a080ab6012ead5a3847bbb3742a4e6cfac1159e4fc9307fa875c9d
preflight_report.md=0812d28939e79d343dc1e4a7202a54652032abe244cdc345d6e7d4c1cdc303f2
preflight_stdout_stderr.log=0b110e06da69a89156b5576ad4748e819d457df4a6e59ea580c694367dab42ca
```

## Report Summary

```text
schema_version=dp_native_training_sufficiency_preflight_v1
profile=development_minimal_v1
records=36
routes={"sample_normal": 18, "sample_tl": 18}
seeds={"101": 12, "102": 12, "103": 12}
traffic_lights={"off": 18, "on": 18}
candidate_count_values={"4": 36}
formal_seed_records=0
```

Thresholds:

```text
min_records=100
min_routes=3
min_seeds=4
min_traffic_light_states=2
min_candidate_count=2
require_heldout_split=False
allow_formal_seeds=False
```

Checks:

```text
records_at_least_min=False
routes_at_least_min=False
seeds_at_least_min=False
traffic_light_states_at_least_min=True
candidate_count_at_least_min=True
clean_contract_passed=True
label_source_records_present=True
formal_seeds_absent_or_allowed=True
heldout_split_possible=True
failed_checks=["records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]
failed_records=[]
label_failed_records=[]
```

## Boundary

The current fixed logs remain useful for:

```text
clean_dp_native_contract_evidence=True
candidate_tensor_provenance_evidence=True
static_trainer_pipeline_smoke_evidence=True
```

They remain insufficient for:

```text
development_training_profile_passed=False
industrial_retraining_sufficient=False
deployable_checkpoint_claim_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The preflight report therefore preserves the current block on direct CAMP
retraining. It does not overturn the prior nondeployable static DP-reward smoke;
it only records that the fixed 36-record, 2-route, 3-seed artifact is below the
development-minimal coverage profile.

## Verification

Remote/read-only:

```text
autodl_report_generation_exit=0
validator_exit=1
validator_exit_expected=True
autodl_CAMP_HEAD=4dec4d270bcbb7144f3b60ae999f3d05b37a0921
autodl_CAMP_origin_main=4dec4d270bcbb7144f3b60ae999f3d05b37a0921
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Forbidden execution flags:

```text
replay_executed=False
candidate_generation_executed=False
training_execution_authorized=False
camp_retraining_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Decision

```text
status=training_sufficiency_preflight_artifact_audit_passed_fail_closed
preflight_artifact_fixed=True
preflight_artifact_sha_verified=True
current_artifact_fails_development_minimal_profile=True
failure_class=coverage_gap
hard_blocking_reasons=["records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]
training_execution_authorized=False
camp_retraining_authorized=False
collection_replay_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`dp_native_training_sufficiency_development_profile_plan_only`

The next gate may only define a paper-consistent development sufficiency
profile and the smallest admissible clean DP-native evidence gap to fill. It
must not run collection, replay, candidate generation, training, promotion, DP
changes, or claims.
