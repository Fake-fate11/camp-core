# Clean DP Native Training Data Contract Validator Static Audit

Date: 2026-06-24

Gate:

```text
clean_dp_native_training_data_contract_validator_static_audit_only
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git rev-parse HEAD origin/main
cf3126bd98f2c146b5f3c12a954fa1fa195e1457
cf3126bd98f2c146b5f3c12a954fa1fa195e1457

git ls-remote origin refs/heads/main
cf3126bd98f2c146b5f3c12a954fa1fa195e1457 refs/heads/main
```

## Audited Artifacts

```text
scripts/integrations/validate_dp_native_training_data_contract.py
camp_core/tests/test_dp_native_training_data_contract_validator.py
docs/diffusion_planner_v8_iteration_audit.md
```

## Static Findings

The validator is an independent command-line checker. It is not imported by the
trainer and is not on any default training execution path.

The report schema is explicitly non-executing:

```text
read_only=True
replay_executed=False
candidate_generation_executed=False
training_execution_authorized=False
camp_retraining_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The validator requires the newly implemented provenance payload before a log
can satisfy the future training-input contract:

```text
camp_candidate_tensor_provenance present
schema_version=dp_native_candidate_tensor_provenance_payload_v1
payload_valid=True
pre_post_tensor_hash_equal=True
selected_index_in_range=True
no_candidate_row_append=True
no_coordinate_heading_speed_rewrite_by_camp=True
reference_blend_stage_hash_separated=True
outcome_label_input=False
closed_loop_outcome_fields_read=False
```

The validator also rejects non-DP-native candidate-generation routes:

```text
noise_strategy != iid -> reject
reference_blend_steps is not None -> reject
guidance_enabled == True -> reject
changes_diffusion_planner_weights == True -> reject
```

Atom schema enforcement is tied to the audited deployed schemas via
`atom_schema_for_dimension`, not just dimension-only matching.

## Test Evidence

```text
python -m py_compile scripts/integrations/validate_dp_native_training_data_contract.py camp_core/tests/test_dp_native_training_data_contract_validator.py
exit=0

git diff --check
exit=0

python -m pytest camp_core/tests/test_dp_native_training_data_contract_validator.py -q
exit=1
reason=existing Windows collection blocker on missing/too-long residual-comfort test path before target tests ran

temporary rootdir target pytest with copied target test and PYTHONPATH=F:\camp_core-main\camp_core;F:\camp_core-main
8 passed in 0.69s
```

Covered rejection cases:

```text
missing provenance
antithetic/guidance/reference-blend candidate generation routes
tensor mutation
outcome-label input leakage
atom schema mismatch
feasible-mask candidate-count mismatch
provenance candidate-count mismatch
provenance selected-index mismatch
selected-index out of range
```

## Decision

```text
status=validator_static_audit_passed
future_training_input_contract_satisfied_when_validator_passes=True
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

The validator proves only that existing logs meet the clean DP-native training
input contract. It does not create clean logs, authorize replay, authorize label
generation, train CAMP, or justify any performance claim.

## Next Gate

`clean_dp_native_training_data_contract_trainer_preflight_authorization_only`
