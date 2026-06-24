# DP Native Training Sufficiency Development Profile Artifact Audit

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_profile_artifact_audit_only
```

This gate audits the fixed clean-log artifact under the newly implemented
explicit development profile. It is read-only/static. It does not run
collection, replay, candidate generation, training, Diffusion Planner
modification, selector/atom promotion, or any safety/CAMP-over-DP claim.

## Heads

```text
local_HEAD=f4f0a9cfc597de052a48804de2a146396380fbbe
origin_main=f4f0a9cfc597de052a48804de2a146396380fbbe
github_refs_heads_main=f4f0a9cfc597de052a48804de2a146396380fbbe
autodl_CAMP_HEAD=f4f0a9cfc597de052a48804de2a146396380fbbe
autodl_CAMP_origin_main=f4f0a9cfc597de052a48804de2a146396380fbbe
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Tracked worktree files were clean before this audit. Existing unrelated
untracked handoff/session files were intentionally left untouched.

## Fixed Artifact

```text
source_artifact=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
selection_log_count=12
profile=dp_native_feasible_ranking_development_minimal_v1
label_source=dp_reward
reward_key=quality_without_progress
```

Remote audit run:

```text
run_root=/root/autodl-tmp/camp_dp_native_training_sufficiency_development_profile_impl_f4f0a9c_20260624T073700Z
profile_exit=1
profile_exit_expected=True
passed=False
records=36
usable_feasible_records=31
failed_checks=["records_at_least_min", "usable_feasible_records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]
training_execution_authorized=False
```

Remote artifact SHA-256:

```text
profile_exit.txt=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865
profile_report.json=00795d3afcc16b284acf0ff6de01f960e16c3d75c1704c4cfc1e9608ce10714b
profile_report.md=9c091157c5fc45d26042f2c476d9f4aabc3aea61c040a42360810e516aa6d8f6
profile_stdout_stderr.log=3c2e6cdce89df2421d41aa7045a70b6d964f1aa23d5957a884c3753454e48fae
```

## Profile Result

The fixed artifact satisfies the clean contract, DP-reward label presence,
traffic-light state coverage, candidate count, and candidate tensor
provenance boundaries already audited by prior gates. It fails the
development profile on coverage:

```text
raw_record_gap=64
usable_feasible_record_gap=69
route_gap=1
seed_gap=1
traffic_light_state_gap=0
candidate_count_gap=0
```

This fail-closed result is the expected profile outcome. It confirms that the
current fixed 36-record artifact remains useful as clean data-path evidence
and a trainer smoke input, but not as sufficient development training data.

## Verification

Remote verification after synchronizing CAMP to `f4f0a9c`:

```text
remote_diff_check_exit=0
remote_py_compile_exit=0
remote_target_pytest=7 passed in 0.35s
remote_profile_exit=1
remote_profile_exit_expected=True
autodl_CAMP_HEAD=f4f0a9cfc597de052a48804de2a146396380fbbe
autodl_CAMP_origin_main=f4f0a9cfc597de052a48804de2a146396380fbbe
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Forbidden execution flags:

```text
replay_executed=False
candidate_generation_executed=False
training_execution_authorized=False
camp_retraining_authorized=False
collection_replay_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Decision

```text
status=development_profile_artifact_audit_passed_fail_closed
profile_artifact_fixed=True
profile_artifact_sha_verified=True
current_artifact_passes_profile=False
failure_class=coverage_gap
hard_blocking_reasons=["records_at_least_min", "usable_feasible_records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]
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

`dp_native_training_sufficiency_development_clean_collection_scope_plan_only`

The next gate may only plan the minimal clean DP-native development collection
scope and authorization conditions needed to close the profile gaps. It must
not run collection, replay, candidate generation, training, promotion, DP
changes, or claims.
