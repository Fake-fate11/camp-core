# DP Native Candidate Tensor Provenance Payload Static Contract Audit

Date: 2026-06-24

Gate:

```text
dp_native_candidate_tensor_provenance_payload_static_contract_audit_only
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git rev-parse HEAD origin/main
303b91f9fc6f9c07f692e3f68162d6b0888a6fde
303b91f9fc6f9c07f692e3f68162d6b0888a6fde

git ls-remote origin refs/heads/main
303b91f9fc6f9c07f692e3f68162d6b0888a6fde refs/heads/main
```

## Audited Artifacts

```text
scripts/integrations/run_diffusion_planner_camp_replay.py
camp_core/tests/test_diffusion_planner_candidate_tensor_provenance_payload.py
camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py
docs/diffusion_planner_v8_iteration_audit.md
```

## Static Contract Findings

The implementation adds one default-off flag:

```text
--camp_candidate_tensor_provenance_logging
```

The flag is evidence-only. It is not part of the rejected non-atom route list,
because it records immutable provenance rather than adding a candidate feature,
trajectory transformation, postselector, or atom promotion.

Payload fields preserve the fixed-candidate reranker contract:

```text
schema_version=dp_native_candidate_tensor_provenance_payload_v1
selection_effect=False
candidate_generation_effect=False
candidate_tensor_mutation_effect=False
candidate_generation_authorized=False
trajectory_rewrite_authorized=False
dp_modification_authorized=False
```

Tensor identity is checked by contiguous tensor bytes plus explicit shape and
dtype:

```text
hash_input=contiguous_candidate_tensor_bytes
nan_policy=preserve_tensor_bytes
pre_camp_scoring_tensor.stage=camp_scoring_input_after_dp_postprocess_before_camp_scoring
post_camp_selector_tensor.stage=post_camp_selector_candidate_tensor_reference
pre_post_tensor_hash_equal requires sha256, shape, and dtype equality
```

The payload fails closed when any required immutability condition is false:

```text
selected_index_in_range=False -> payload_valid=False
pre_post_tensor_hash_equal=False -> payload_valid=False
no_candidate_row_append=False -> payload_valid=False
no_coordinate_heading_speed_rewrite_by_camp=False -> payload_valid=False
reference_blend_stage_hash_separated=False -> payload_valid=False
outcome_label_input=True -> payload_valid=False
```

The online selector call remains free of closed-loop outcome labels:

```text
selector.select(...) does not receive candidate_outcomes
_build_candidate_tensor_provenance_payload(..., outcome_label_input=False)
```

## Test Coverage

```text
test_candidate_tensor_hash_payload_preserves_tensor_bytes
test_candidate_tensor_provenance_payload_proves_immutable_selector_input
test_candidate_tensor_provenance_payload_detects_tensor_rewrite
test_candidate_tensor_provenance_payload_detects_row_append_and_bad_index
test_reference_blend_stage_requires_separate_raw_dp_hash_when_present
test_outcome_label_inputs_fail_closed
test_online_selector_path_does_not_receive_outcome_label_inputs
test_candidate_tensor_provenance_summary_tracks_static_contract
test_candidate_tensor_hash_rejects_non_numeric_payloads
test_replay_paper_boundary_accepts_evidence_only_provenance_logging
```

Verification inherited from the implementation gate:

```text
python -m py_compile scripts/integrations/run_diffusion_planner_camp_replay.py camp_core/tests/test_diffusion_planner_candidate_tensor_provenance_payload.py camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py
exit=0

git diff --check
exit=0

direct repo pytest
exit=1
reason=existing Windows collection blocker on missing/too-long residual-comfort test path before target tests ran

temporary rootdir target pytest with copied target tests and PYTHONPATH=F:\camp_core-main\camp_core;F:\camp_core-main
40 passed in 0.54s
```

## Decision

```text
status=static_contract_audit_passed
runtime_replay_artifact_present=False
runtime_replay_artifact_required_for_this_gate=False
replay_executed=False
candidate_generation_executed=False
trajectory_rewrite_authorized=False
candidate_tensor_mutation_authorized=False
formal_seeds_authorized=False
full36_authorized=False
camp_retraining_authorized=False
training_execution_authorized=False
atom_promotion_authorized=False
online_selector_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The static contract is sufficient to move to a clean data-path authorization
gate. It is not evidence of runtime safety improvement, CAMP superiority over
DP Top-1, or training readiness.

## Next Gate

`clean_dp_native_training_data_collection_authorization_only`
