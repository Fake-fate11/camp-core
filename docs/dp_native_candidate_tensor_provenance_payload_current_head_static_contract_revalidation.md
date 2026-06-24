# DP Native Candidate Tensor Provenance Payload Current-Head Static Contract Revalidation

Date: 2026-06-24

Gate:

```text
dp_native_candidate_tensor_provenance_payload_current_head_static_contract_revalidation_only
```

This gate revalidates the already-present default-off candidate tensor
provenance implementation at current HEAD. It is static/test-only. It does not
run replay, generate candidates, retrain CAMP, modify Diffusion Planner,
promote selectors/atoms, or make safety or CAMP-over-DP claims.

## Heads

```text
local_HEAD=b76b90b4aa335e34be501a5fc100c5fd5d53ca21
origin_main=b76b90b4aa335e34be501a5fc100c5fd5d53ca21
github_refs_heads_main=b76b90b4aa335e34be501a5fc100c5fd5d53ca21
autodl_CAMP_HEAD=b76b90b4aa335e34be501a5fc100c5fd5d53ca21
autodl_CAMP_origin_main=b76b90b4aa335e34be501a5fc100c5fd5d53ca21
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

## Audited Sources

```text
scripts/integrations/run_diffusion_planner_camp_replay.py=b6979da506cdb8c124b5147651e93fd626ee73ced887a9d1bfdcc085837cd26c
scripts/integrations/validate_dp_native_training_data_contract.py=9741b410da8723096412a832896e0abf468ba8a9fa24f0ed157d1f8362bd8e5b
camp_core/tests/test_diffusion_planner_candidate_tensor_provenance_payload.py=1ea27693085d36a7cf70aea08512b4cb59db019232e087b117895ef9190db9d3
camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py=f96a6c1abbfc407202ea366046852a7caa9baea02830bb8a42df626e840bff16
camp_core/tests/test_dp_native_training_data_contract_validator.py=3a9f48b894ec1492fd2a098933c7a3c11c8dd48eee3e4c361696a1b88fee9b02
```

## Contract Findings

The replay integration exposes one default-off evidence-only switch:

```text
--camp_candidate_tensor_provenance_logging
```

When enabled, it records:

```text
schema_version=dp_native_candidate_tensor_provenance_payload_v1
selection_effect=False
candidate_generation_effect=False
candidate_tensor_mutation_effect=False
candidate_generation_authorized=False
trajectory_rewrite_authorized=False
dp_modification_authorized=False
pre_camp_scoring_tensor.sha256 present
pre_camp_scoring_tensor.shape present
pre_camp_scoring_tensor.dtype present
post_camp_selector_tensor.sha256 present
post_camp_selector_tensor.shape present
post_camp_selector_tensor.dtype present
hash_input=contiguous_candidate_tensor_bytes
nan_policy=preserve_tensor_bytes
selected_index_in_range recorded
pre_post_tensor_hash_equal recorded
no_candidate_row_append recorded
no_coordinate_heading_speed_rewrite_by_camp recorded
outcome_label_input=False
closed_loop_outcome_fields_read=False
```

The payload fails closed when tensor bytes differ, a row is appended, the
selected index is out of range, a reference-blend stage lacks a separate raw-DP
hash, or outcome labels are presented as online selector inputs.

The online selector call remains free of candidate outcome labels. The payload
is attached to selection-log evidence only and does not change candidates,
atoms, masks, scores, selected index, DP weights/configuration, or runtime
promotion state.

## Verification

```text
python -m py_compile scripts/integrations/run_diffusion_planner_camp_replay.py scripts/integrations/validate_dp_native_training_data_contract.py camp_core/tests/test_diffusion_planner_candidate_tensor_provenance_payload.py camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py camp_core/tests/test_dp_native_training_data_contract_validator.py
exit=0

python -m pytest camp_core/tests/test_diffusion_planner_candidate_tensor_provenance_payload.py camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py camp_core/tests/test_dp_native_training_data_contract_validator.py -q
exit=1
reason=existing Windows long-path collection error before target tests ran

PYTHONPATH=F:\camp_core-main;F:\camp_core-main\camp_core
python -m pytest Y:\test_diffusion_planner_candidate_tensor_provenance_payload.py Y:\test_diffusion_planner_camp_replay_paper_boundary.py Y:\test_dp_native_training_data_contract_validator.py -q -p no:cacheprovider
result=48 passed in 1.81s
```

## Decision

```text
status=current_head_static_contract_revalidation_passed
default_off_provenance_payload_present=True
immutable_candidate_tensor_contract_revalidated=True
pre_camp_scoring_tensor_hash_required=True
post_camp_selector_tensor_hash_required=True
pre_post_tensor_hash_equal_required=True
selected_index_in_range_required=True
candidate_count_unchanged_required=True
no_candidate_row_append_required=True
no_coordinate_heading_speed_rewrite_by_camp_required=True
online_selector_outcome_label_input_forbidden=True
replay_executed=False
candidate_generation_executed=False
camp_retraining_executed=False
selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`dp_native_candidate_tensor_provenance_payload_artifact_audit_only`

The next gate may only inspect fixed existing artifacts/logs that already
contain the provenance payload. It must not run replay, generate candidates,
retrain CAMP, promote atoms/selectors, modify DP, or make claims.
