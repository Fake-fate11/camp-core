# DP Native Training Sufficiency Gap Remediation Plan

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_gap_remediation_plan_only
```

This plan-only gate converts the current training-sufficiency gaps into the
next safe engineering step. It does not run collection, replay, candidate
generation, CAMP training, Diffusion Planner modification, selector/atom
promotion, or claims.

## Heads

```text
local_HEAD=d4091b090ef92aeaac9b6bff2273ffe065147d1c
origin_main=d4091b090ef92aeaac9b6bff2273ffe065147d1c
github_refs_heads_main=d4091b090ef92aeaac9b6bff2273ffe065147d1c
```

The last AutoDL synchronization recorded:

```text
autodl_CAMP_HEAD=d4091b090ef92aeaac9b6bff2273ffe065147d1c
autodl_CAMP_origin_main=d4091b090ef92aeaac9b6bff2273ffe065147d1c
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

## Current Evidence

Clean DP-native logs:

```text
artifact_root=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
selection_log_count=12
total_records=36
routes=sample_tl,sample_normal
seeds=101,102,103
traffic_lights=on,off
max_npcs=0
validator_passed=True
all_candidate_tensor_provenance_clean=True
all_records_closed_loop_outcomes_none=True
```

Static DP-reward smoke:

```text
run_root=/root/autodl-tmp/camp_dp_native_clean_training_log_minimal_static_dp_reward_training_smoke_b46626b4_20260624T062215Z
training_exit=0
smoke_passed=True
label_source=dp_reward
reward_key=quality_without_progress
num_records=31
num_atoms=14
weights_simplex=True
nondeployable_training_smoke_only=True
```

## Gap Classes

The current fixed artifacts close the data-path and provenance gaps, but not
the retraining-readiness gaps:

```text
clean_data_path_gap=False
candidate_tensor_provenance_gap=False
static_trainer_pipeline_smoke_gap=False
coverage_gap=True
label_objective_gap=True
split_and_heldout_gap=True
development_baseline_gap=True
deployment_claim_gap=True
```

Concrete blockers:

```text
only_36_records=True
only_2_routes=True
only_3_nonformal_seeds=True
max_npcs_0_only=True
formal_seeds_11_12_13_absent=True
Full36_absent=True
closed_loop_outcome_labels_absent=True
matched_development_baseline_absent=True
heldout_development_gate_absent=True
```

## Paper-Consistent Remediation Path

Before any future request to run CAMP training, the repo needs a static
sufficiency preflight that fails closed on the current artifact and can later
be reused for any explicitly authorized development collection. The preflight
must be read-only and default-off.

It should check:

```text
fixed_candidate_contract=True
candidate_tensor_provenance_required=True
atom_schema_required=True
approved_atom_schema_only=True
route_group_summary_required=True
seed_group_summary_required=True
traffic_light_group_summary_required=True
candidate_count_summary_required=True
label_source_declared=True
label_source_not_online_input=True
split_plan_required=True
heldout_route_or_seed_group_required=True
formal_seed_use_forbidden_unless_later_authorized=True
Full36_use_forbidden_unless_later_authorized=True
```

The preflight should not hard-code an industrial sample-size claim. Instead it
should accept explicit caller-provided thresholds or a checked-in audit profile
and report pass/fail against that profile. A later gate can decide whether a
profile is sufficient for a particular development run.

Any future development collection proposal must remain DP-native:

```text
reference_blend=False
guidance=False
postprocess_or_postselection_mainline=False
splice_or_materialized_generator=False
closed_loop_outcome_online_input=False
DP_code_config_weight_change=False
selector_or_atom_promotion=False
```

## Decision

```text
status=training_sufficiency_gap_remediation_plan_ready
direct_camp_retraining_blocked=True
training_execution_authorized=False
collection_replay_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
authorized_next_work=dp_native_training_sufficiency_preflight_validator_default_off_implementation
```

## Next Gate

`dp_native_training_sufficiency_preflight_validator_default_off_implementation`

The next gate may only implement a read-only/default-off training-sufficiency
preflight validator and targeted static tests. It must not run collection,
replay, candidate generation, training, promotion, DP changes, or claims.
