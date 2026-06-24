# Clean DP Native Training Data Contract Trainer Preflight Static Audit

Date: 2026-06-24

Gate:

```text
clean_dp_native_training_data_contract_trainer_preflight_static_audit_only
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git rev-parse HEAD origin/main
5d4b007244da0a54f27a8af29be5224f3987b417
5d4b007244da0a54f27a8af29be5224f3987b417

git ls-remote origin refs/heads/main
5d4b007244da0a54f27a8af29be5224f3987b417 refs/heads/main
```

## Audited Artifacts

```text
scripts/integrations/train_diffusion_planner_robust_camp.py
scripts/integrations/validate_dp_native_training_data_contract.py
camp_core/tests/test_diffusion_planner_robust_camp_training_contract_preflight.py
camp_core/tests/test_dp_native_training_data_contract_validator.py
docs/diffusion_planner_v8_iteration_audit.md
```

## Static Findings

The trainer preflight is default-off:

```text
flag=--require_dp_native_training_data_contract
default=False
default_behavior_change=False
```

When disabled, the helper returns `None` and does not touch missing or existing
selection logs. When enabled, it calls the read-only validator before
`load_outcome_weights`, `load_training_records`, `load_candidate_*_outcomes`,
solver setup, output-directory creation, or checkpoint writes.

Failure is fail-closed:

```text
validator passed=False -> ValueError before training
```

The training summary includes `dp_native_training_data_contract` only as the
validator report value; no selector, checkpoint, atom schema, or DP artifact is
promoted by this field.

## Test Evidence

```text
python -m py_compile scripts/integrations/train_diffusion_planner_robust_camp.py camp_core/tests/test_diffusion_planner_robust_camp_training_contract_preflight.py
exit=0

git diff --check
exit=0

direct repo pytest
exit=1
reason=existing Windows collection blocker on missing/too-long residual-comfort test path before target tests ran

temporary rootdir target pytest
3 passed in 0.64s

temporary rootdir combined validator/preflight pytest
11 passed in 0.82s
```

## Decision

```text
status=trainer_preflight_static_audit_passed
training_data_collection_execution_authorized=False
replay_executed=False
candidate_generation_executed=False
outcome_label_generation_authorized=False
camp_retraining_authorized=False
training_execution_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The repo now has a default-off fail-closed path for future clean DP-native CAMP
training inputs. This does not prove that any existing log satisfies the
contract and does not authorize collecting new logs.

## Next Gate

`existing_clean_dp_native_training_log_availability_audit_only`
