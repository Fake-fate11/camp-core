# DP Native Fixed-Artifact Fallback Risk Training Data Record Identity Hash Remediation Implementation

Date: 2026-06-25

Gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_implementation_only
```

This gate implements the minimal default-off `record_identity_hash` remediation
authorized for the fallback-risk training data builder and validator contract.
It does not rebuild fixed artifacts, run replay, generate candidates, train
CAMP, retrain CAMP, modify Diffusion Planner, change the online selector,
promote a selector or atom, or claim safety benefit or CAMP-over-DP Top-1.

## Changed Artifacts

```text
implementation_start_head=e910585d310cbd2610afaa01a2a9dda040e35304
training_data_builder=scripts/integrations/build_diffusion_planner_dp_native_fallback_risk_training_data.py
training_data_validator=scripts/integrations/validate_dp_native_fallback_risk_training_data_contract.py
builder_unit_test=camp_core/tests/test_dp_native_fallback_risk_training_data_default_off_builder.py
validator_unit_test=camp_core/tests/test_dp_native_fallback_risk_training_data_validator_extension.py
validator_reference_contract_test=camp_core/tests/test_dp_native_fallback_risk_training_data_validator_extension_contract.py
split_manifest_contract_test=camp_core/tests/test_dp_native_fallback_risk_training_split_manifest_contract.py
```

## Implemented Contract

```text
builder_emits_record_identity_hash=True
validator_requires_record_identity_hash=True
validator_recomputes_record_identity_hash=True
validator_rejects_missing_record_identity_hash=True
validator_rejects_invalid_record_identity_hash=True
validator_rejects_mismatched_record_identity_hash=True
record_identity_hash_formula_matches_split_manifest_builder=True
record_identity_hash_inputs=source_log,source_log_sha256,run_id,record_index
new_runtime_dependencies=False
default_off_boundaries_preserved=True
```

The hash formula is the same JSON serialization and SHA-256 contract used by
the split manifest builder:

```text
sha256(json({source_log,source_log_sha256,run_id,record_index}, sort_keys=True, separators=(",", ":")))
```

## Verification

```text
local_python=py -3.12
local_py_compile_exit=0
local_implementation_target_pytest=48 passed
```

## Forbidden

```text
replay_execution_authorized=False
candidate_generation_authorized=False
camp_training_authorized=False
camp_retraining_authorized=False
training_execution_authorized_now=False
fixed_artifact_rebuild_authorized_now=False
Full36_authorized=False
formal_seeds_11_12_13_authorized=False
dp_modification_authorized=False
reference_blend_authorized=False
guidance_authorized=False
postprocess_postselection_authorized=False
closed_loop_outcome_online_input_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
fallback_risk_training_authorized_now=False
fallback_dataset_training_sufficiency_claim=False
feasible_ranking_master_change_authorized=False
hard_feasibility_relaxation_authorized=False
all_infeasible_records_added_to_feasible_training=False
production_selector_change_authorized=False
online_selector_change_authorized=False
```

## Decision

```text
status=fallback_risk_training_data_record_identity_hash_remediation_implemented
passed=True
implementation_complete=True
record_identity_hash_remediation_implemented=True
fixed_artifact_rebuild_authorized_now=False
training_split_manifest_ready_for_preflight=False
fallback_risk_training_authorized_now=False
camp_retraining_authorized_now=False
fallback_dataset_training_sufficiency_claim=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

Next admissible gate:

```text
dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_fixed_artifact_fallback_risk_training_data_record_identity_hash_remediation_post_implementation_static_contract_only
```

The next gate may only perform a post-implementation static contract review of
this remediation. It must not rebuild fixed artifacts, run replay, generate
candidates, train CAMP, modify Diffusion Planner, use formal seeds, relax hard
feasibility, add all-infeasible records to the feasible-ranking master, promote
a selector or atom, or claim safety/CAMP-over-DP benefit.
