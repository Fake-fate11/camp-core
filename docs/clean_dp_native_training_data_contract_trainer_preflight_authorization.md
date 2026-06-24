# Clean DP Native Training Data Contract Trainer Preflight Authorization

Date: 2026-06-24

Gate:

```text
clean_dp_native_training_data_contract_trainer_preflight_authorization_only
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git rev-parse HEAD origin/main
00eb7cf03867697c0e795dc62848c44d52910eab
00eb7cf03867697c0e795dc62848c44d52910eab

git ls-remote origin refs/heads/main
exit=1
reason=GitHub HTTPS/TLS handshake failure after prior push; local origin/main still matches HEAD
```

## Evidence Reviewed

The validator now exists as a read-only implementation:

```text
scripts/integrations/validate_dp_native_training_data_contract.py
schema_version=clean_dp_native_training_data_contract_validator_v1
read_only=True
replay_executed=False
candidate_generation_executed=False
training_execution_authorized=False
```

The robust trainer already supports strict atom schema checking:

```text
scripts/integrations/train_diffusion_planner_robust_camp.py
  --require_atom_schema
  validate_atom_schema(...)
  solve_robust_margin_cutting_plane(...)
```

It does not yet have a switch that requires the DP-native provenance validator
to pass before the trainer loads atoms/outcome labels and starts optimization.

## Authorized Next Implementation

Authorize only a default-off trainer preflight:

```text
flag=--require_dp_native_training_data_contract
default=False
when_enabled=call validate_dp_native_training_data_contract.validate_logs(args.selection_log)
failure_behavior=raise ValueError before atom loading, label loading, optimizer setup, or artifact writing
summary_behavior=include the validator report in training_summary.json only when the flag is enabled and validation passed
default_behavior_change=False
```

The implementation may add unit tests with synthetic logs. It must not run the
trainer on real data, execute replay, generate candidates, collect outcome
labels, save CAMP checkpoints, or modify DP.

## Prohibited By This Gate

```text
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

## Decision

```text
status=trainer_preflight_implementation_authorized
implementation_authorized_now=True
authorized_next_work=clean_dp_native_training_data_contract_trainer_preflight_default_off_implementation
```

## Next Gate

`clean_dp_native_training_data_contract_trainer_preflight_default_off_implementation`
