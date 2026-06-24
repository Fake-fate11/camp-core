# DP Native Candidate Tensor Provenance Payload Authorization Current-Head Revalidation

Date: 2026-06-24

Gate:

```text
dp_native_candidate_tensor_provenance_payload_implementation_authorization_only
```

This authorization-only gate revalidates the current repository state after the
static DP-reward smoke nonpromotion branch returned the audit tail to candidate
tensor provenance. It is read-only/static. It does not run replay, generate
candidates, modify Diffusion Planner, retrain CAMP, promote selectors/atoms, or
make safety or CAMP-over-DP claims.

## Heads

```text
local_HEAD=2726c5948d3d1c5bf6483ef2316b2bf0b2c15555
origin_main=2726c5948d3d1c5bf6483ef2316b2bf0b2c15555
github_refs_heads_main=2726c5948d3d1c5bf6483ef2316b2bf0b2c15555
autodl_CAMP_HEAD=2726c5948d3d1c5bf6483ef2316b2bf0b2c15555
autodl_CAMP_origin_main=2726c5948d3d1c5bf6483ef2316b2bf0b2c15555
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Tracked worktree files were clean before this authorization revalidation.
Existing unrelated untracked handoff/session files remain out of scope.

## Current Evidence

Previous provenance milestones already exist in the tracked repo:

```text
052c326 Authorize DP candidate tensor provenance payload
303b91f Add DP candidate tensor provenance payload
8b863d7 Audit DP candidate tensor provenance contract
```

Current source hashes:

```text
docs/dp_native_candidate_tensor_provenance_payload_authorization.md=6a2019bd9a25d640b14d87105ee969df4abcccb75de4a4bb363a0c0ac150e192
docs/dp_native_candidate_tensor_provenance_payload_static_contract_audit.md=6c1052f2417d9ce0201c9cf1ecb38120d0971234a8355e2804033ad46774a127
scripts/integrations/run_diffusion_planner_camp_replay.py=b6979da506cdb8c124b5147651e93fd626ee73ced887a9d1bfdcc085837cd26c
camp_core/tests/test_diffusion_planner_candidate_tensor_provenance_payload.py=1ea27693085d36a7cf70aea08512b4cb59db019232e087b117895ef9190db9d3
camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py=f96a6c1abbfc407202ea366046852a7caa9baea02830bb8a42df626e840bff16
scripts/integrations/validate_dp_native_training_data_contract.py=9741b410da8723096412a832896e0abf468ba8a9fa24f0ed157d1f8362bd8e5b
camp_core/tests/test_dp_native_training_data_contract_validator.py=3a9f48b894ec1492fd2a098933c7a3c11c8dd48eee3e4c361696a1b88fee9b02
```

The implementation is already present and default-off:

```text
flag=--camp_candidate_tensor_provenance_logging
schema_version=dp_native_candidate_tensor_provenance_payload_v1
helper=_build_candidate_tensor_provenance_payload
validator=validate_dp_native_training_data_contract.py
default_off=True
evidence_only=True
selection_effect=False
candidate_generation_effect=False
candidate_tensor_mutation_effect=False
candidate_generation_authorized=False
trajectory_rewrite_authorized=False
dp_modification_authorized=False
```

The implementation records the required fixed-candidate invariants:

```text
pre_camp_scoring_tensor.sha256
pre_camp_scoring_tensor.shape
pre_camp_scoring_tensor.dtype
post_camp_selector_tensor.sha256
post_camp_selector_tensor.shape
post_camp_selector_tensor.dtype
hash_input=contiguous_candidate_tensor_bytes
nan_policy=preserve_tensor_bytes
pre_post_tensor_hash_equal
selected_index_in_range
candidate_count
post_selector_candidate_count
no_candidate_row_append
no_coordinate_heading_speed_rewrite_by_camp
outcome_label_input=False
closed_loop_outcome_fields_read=False
```

Static tests already cover hash identity, tensor rewrite detection, row append
detection, bad selected-index detection, outcome-label fail-closed behavior,
online selector outcome-label exclusion, and summary aggregation.

## Authorization Boundary

This gate revalidates authorization for the already-present minimal default-off
implementation. It does not authorize a duplicate implementation, replay, new
candidate generation, CAMP retraining, selector promotion, atom promotion, DP
modification, or any safety/CAMP-over-DP claim.

Because implementation already exists at current HEAD, the next admissible gate
should re-run the static contract at current HEAD rather than rewrite the same
code path.

## Decision

```text
status=implementation_authorization_revalidated_current_head
implementation_authorized_now=True
implementation_already_present=True
new_code_required=False
duplicate_implementation_authorized=False
authorized_next_work=dp_native_candidate_tensor_provenance_payload_current_head_static_contract_revalidation_only
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

`dp_native_candidate_tensor_provenance_payload_current_head_static_contract_revalidation_only`

The next gate may only re-run static/contract checks for the current-head
candidate tensor provenance implementation and append current evidence. It must
not run replay, generate candidates, retrain CAMP, promote atoms/selectors,
modify DP, or make claims.
