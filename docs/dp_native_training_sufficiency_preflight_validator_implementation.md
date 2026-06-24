# DP Native Training Sufficiency Preflight Validator Implementation

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_preflight_validator_default_off_implementation
```

This implementation adds a read-only/default-off training sufficiency preflight
validator. It does not run collection, replay, candidate generation, CAMP
training, Diffusion Planner modification, selector/atom promotion, or claims.

## Heads

```text
local_HEAD=501521fbbd34c1938605d3ceb55640b2c6087d3f
origin_main=501521fbbd34c1938605d3ceb55640b2c6087d3f
github_refs_heads_main=501521fbbd34c1938605d3ceb55640b2c6087d3f
autodl_CAMP_HEAD=501521fbbd34c1938605d3ceb55640b2c6087d3f
autodl_CAMP_origin_main=501521fbbd34c1938605d3ceb55640b2c6087d3f
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

## Implemented Files

```text
script=scripts/integrations/validate_dp_native_training_sufficiency_preflight.py
test=camp_core/tests/test_dp_native_training_sufficiency_preflight.py
script_sha256=0153a8dbde51f6167047222490c5974b1bfe425c88d2d175f920b6c3098255d9
test_sha256=3afea74af9c1852a733f7c695f32a9e7616181acbf69eb27959748f045c72e34
```

The validator:

```text
schema_version=dp_native_training_sufficiency_preflight_v1
profile=development_minimal_v1
read_only=True
default_off_preflight=True
replay_executed=False
candidate_generation_executed=False
training_execution_authorized=False
camp_retraining_authorized=False
deployable_checkpoint_claim_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

It checks:

```text
clean training-data contract per record
label_source records present
route coverage
seed coverage
traffic-light state coverage
candidate-count coverage
formal seeds absent unless explicitly allowed
heldout route/seed split possible when required
```

Default development-minimal thresholds:

```text
min_records=100
min_routes=3
min_seeds=4
min_traffic_light_states=2
min_candidate_count=2
require_heldout_split=False
allow_formal_seeds=False
```

These thresholds are preflight guards only. They are not industrial sufficiency
claims and can be overridden only by explicit caller input or a later audited
profile.

## Verification

Local:

```text
git_diff_check_exit=0
py_compile_exit=0
default_root_pytest_exit=1
default_root_pytest_blocker=existing Windows long-path collection error before target tests ran
short_path_target_pytest=5 passed in 1.35s
```

Fixed artifact smoke of the validator, using local temporary copies of the
existing AutoDL selection logs:

```text
source_artifact=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
downloaded_logs=12
label_source=dp_reward
preflight_exit=1
records=36
routes={"sample_normal": 18, "sample_tl": 18}
seeds={"101": 12, "102": 12, "103": 12}
traffic_lights={"off": 18, "on": 18}
candidate_count_values={"4": 36}
failed_checks=["records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]
clean_contract_passed=True
label_source_records_present=True
formal_seeds_absent_or_allowed=True
training_execution_authorized=False
```

The current fixed 36-record artifact therefore fails closed for development
training sufficiency for coverage reasons, while preserving the clean contract
and label-source checks.

AutoDL post-push verification:

```text
autodl_CAMP_HEAD=865d681ab157011979654087c2cfa6bcd4390bb5
autodl_CAMP_origin_main=865d681ab157011979654087c2cfa6bcd4390bb5
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
remote_py_compile_exit=0
remote_target_pytest=5 passed in 0.15s
remote_fixed_artifact_preflight_exit=1
remote_fixed_artifact_records=36
remote_fixed_artifact_failed_checks=["records_at_least_min", "routes_at_least_min", "seeds_at_least_min"]
remote_fixed_artifact_clean_contract_passed=True
remote_fixed_artifact_label_source_records_present=True
remote_training_execution_authorized=False
```

## Decision

```text
status=training_sufficiency_preflight_validator_implemented
current_artifact_fails_closed=True
implementation_default_off=True
read_only=True
training_execution_authorized=False
camp_retraining_authorized=False
collection_replay_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`dp_native_training_sufficiency_preflight_artifact_audit_only`

The next gate may only audit the validator output and code boundary. It must
not run collection, replay, candidate generation, training, promotion, DP
changes, or claims.
