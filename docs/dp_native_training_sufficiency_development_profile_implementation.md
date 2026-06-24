# DP Native Training Sufficiency Development Profile Implementation

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_profile_default_off_implementation
```

This implementation adds the named development sufficiency profile planned in
`docs/dp_native_training_sufficiency_development_profile_plan.md`. It is
default-off and only affects the read-only preflight validator when explicitly
requested. It does not run collection, replay, candidate generation, training,
Diffusion Planner modification, selector/atom promotion, or any safety/CAMP
over-DP claim.

## Implemented Files

```text
script=scripts/integrations/validate_dp_native_training_sufficiency_preflight.py
test=camp_core/tests/test_dp_native_training_sufficiency_preflight.py
script_sha256=ba312b7b737949bb2178fbab2439d80bd7aa1cf0836b8f7e3920a4489c81df59
test_sha256=111c60b74f744abc8f2f626c7348736c18876b074ec9bfccab6837856969906f
```

## Profile

```text
profile_name=dp_native_feasible_ranking_development_minimal_v1
cli_switch=--development_profile dp_native_feasible_ranking_development_minimal_v1
default_off=True
default_custom_threshold_behavior_preserved=True
training_execution_authorized=False
```

When the profile is enabled, the validator applies:

```text
min_records=100
min_usable_feasible_records=100
min_routes=3
min_seeds=4
min_traffic_light_states=2
required_traffic_light_states=["off", "on"]
min_candidate_count=4
require_heldout_split=True
allow_formal_seeds=False
```

The implementation also reports `usable_feasible_records`, counted only when a
record has at least one `True` entry in `feasible_mask`.

## Fixed Artifact Smoke

Local read-only profile run over cached copies of the fixed AutoDL selection
logs:

```text
source_artifact=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
local_cache=%TEMP%/camp_training_sufficiency_preflight_fixed_logs
selection_log_count=12
profile_exit=1
profile_exit_expected=True
profile=dp_native_feasible_ranking_development_minimal_v1
passed=False
records=36
usable_feasible_records=31
failed_checks=["records_at_least_min", "usable_feasible_records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]
training_execution_authorized=False
```

Local profile artifact SHA-256:

```text
profile_report.json=ea352ae64ad23583f189a9737070339482cb0979c1d2db4c768adcd7b59a64b7
profile_report.md=e8604e53fd98d0e47184894e6b74ff79d4108e557e879b7134000b12e4fa71f9
profile_stdout_stderr.log=ecf23da057b8774710506fe0fea002684cc71b4b65565a61583c02ac8c23b5a7
profile_exit.txt=f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04
```

## Verification

```text
py_compile_exit=0
short_path_target_pytest=7 passed in 1.21s
git_diff_check_exit=0
```

The short-path pytest invocation was used to avoid the existing Windows test
collection blocker on an unrelated long-path residual-comfort test filename.

## Decision

```text
status=development_profile_default_off_implemented
profile_default_off=True
current_fixed_artifact_fails_closed=True
failure_class=coverage_gap
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

`dp_native_training_sufficiency_development_profile_artifact_audit_only`

The next gate may only audit the fixed artifact with this new explicit profile
after the implementation is pushed/synced. It must not run collection, replay,
candidate generation, training, promotion, DP changes, or claims.
