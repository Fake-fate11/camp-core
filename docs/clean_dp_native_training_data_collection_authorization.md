# Clean DP Native Training Data Collection Authorization

Date: 2026-06-24

Gate:

```text
clean_dp_native_training_data_collection_authorization_only
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git rev-parse HEAD origin/main
8b863d77f3f2d8b2fe6b901956e44e8173ec5873
8b863d77f3f2d8b2fe6b901956e44e8173ec5873

git ls-remote origin refs/heads/main
8b863d77f3f2d8b2fe6b901956e44e8173ec5873 refs/heads/main
```

## Evidence Reviewed

The mathematical contract requires a fixed DP candidate set before CAMP
training:

```text
Y_i fixed before CAMP atom extraction
a_ik fixed finite nonnegative candidate constants
score=a_ik^T w
closed-loop outcome labels forbidden as online inputs
offline labels allowed only to build training oracle/margins
```

The robust DP-CAMP trainer already uses the finite-candidate robust-margin
master:

```text
scripts/integrations/train_diffusion_planner_robust_camp.py
  load_training_records(...)
  load_candidate_closed_loop_outcomes(...) or load_candidate_safety_cost_v1_values(...)
  outcome_oracle_and_margins(...)
  solve_robust_margin_cutting_plane(...)
```

The current loader path still lacks a required DP-native provenance gate. It
loads atoms, feasible masks, and offline labels, but does not yet reject logs
whose candidate tensors lack the new provenance payload.

## Authorized Next Implementation

Authorize only a read-only, default-off training-data contract validator. The
validator may inspect existing `camp_selection_log.json` files and emit a JSON
or Markdown report. It must not run replay, generate candidates, collect new
labels, train CAMP, modify DP, or write selector/checkpoint artifacts.

Required per-record checks:

```text
selected_index in range
atoms finite nonnegative [K,R]
feasible_mask shape [K]
atom_schema_version and ordered atom_names match an audited deployed schema
candidate_generation_contract present
candidate_generation_contract.noise_strategy == iid
candidate_generation_contract.guidance_enabled == False
candidate_generation_contract.reference_blend_steps is None
candidate_generation_contract.changes_diffusion_planner_weights == False
camp_candidate_tensor_provenance present
camp_candidate_tensor_provenance.schema_version == dp_native_candidate_tensor_provenance_payload_v1
camp_candidate_tensor_provenance.selection_effect == False
camp_candidate_tensor_provenance.candidate_generation_effect == False
camp_candidate_tensor_provenance.candidate_tensor_mutation_effect == False
camp_candidate_tensor_provenance.payload_valid == True
camp_candidate_tensor_provenance.pre_post_tensor_hash_equal == True
camp_candidate_tensor_provenance.selected_index_in_range == True
camp_candidate_tensor_provenance.no_candidate_row_append == True
camp_candidate_tensor_provenance.no_coordinate_heading_speed_rewrite_by_camp == True
camp_candidate_tensor_provenance.reference_blend_stage_hash_separated == True
camp_candidate_tensor_provenance.outcome_label_input == False
camp_candidate_tensor_provenance.closed_loop_outcome_fields_read == False
provenance candidate_count matches atoms/feasible/outcome label candidate count when labels are present
candidate_closed_loop_outcomes, when present, are treated as offline labels only
```

The validator may be reused later by the robust trainer, but this gate does not
authorize editing the trainer to execute training or saving new CAMP artifacts.

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
status=validator_implementation_authorized
implementation_authorized_now=True
authorized_next_work=clean_dp_native_training_data_contract_validator_default_off_implementation
```

## Next Gate

`clean_dp_native_training_data_contract_validator_default_off_implementation`
