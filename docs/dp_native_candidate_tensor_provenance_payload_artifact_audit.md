# DP Native Candidate Tensor Provenance Payload Artifact Audit

Date: 2026-06-24

Gate:

```text
dp_native_candidate_tensor_provenance_payload_artifact_audit_only
```

This gate inspects only fixed existing artifacts that already contain the
default-off candidate tensor provenance payload. It does not run replay,
generate candidates, retrain CAMP, modify Diffusion Planner, promote
selectors/atoms, or make safety or CAMP-over-DP claims.

## Heads

```text
local_HEAD=7b0ec22d7720b1d4e3f92e38677fc433f14cc48b
origin_main=7b0ec22d7720b1d4e3f92e38677fc433f14cc48b
github_refs_heads_main=7b0ec22d7720b1d4e3f92e38677fc433f14cc48b
autodl_CAMP_HEAD=7b0ec22d7720b1d4e3f92e38677fc433f14cc48b
autodl_CAMP_origin_main=7b0ec22d7720b1d4e3f92e38677fc433f14cc48b
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

## Fixed Artifact

```text
artifact_root=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
collection_summary.json_sha256=05c8c7056dbe7460cfac422b0f1081179021a9df80324a4378cec3bf6dc693f0
clean_dp_native_training_data_contract_validation.json_sha256=c2f8f1b10e9d1a8925886255e8ffa3af151ef1ceaab278027a50a9087f39a7f4
selection_log_sha256_list_digest=4cbc032191fa62bd6c9e3e0f03646ae618aee8678f85bbafd096ccbf3139188b
```

The fixed artifact root was created by an earlier explicitly authorized
broader nonformal clean-log collection. This gate did not create or mutate it.

## Read-Only Artifact Audit Result

```text
file_count=187
selection_log_count=12
record_count=36
collection_passed=True
validator_passed=True
validator_records=36
validator_failed_records=[]
payload_failure_count=0
schema_versions={"dp_native_candidate_tensor_provenance_payload_v1": 36}
candidate_count_values={"4": 36}
selected_index_counts={"0": 7, "1": 8, "2": 7, "3": 14}
route_counts={"sample_normal": 18, "sample_tl": 18}
seed_counts={"101": 12, "102": 12, "103": 12}
traffic_light_counts={"off": 18, "on": 18}
```

Required provenance invariants were checked on all 36 records:

```text
payload_present=True
schema_version=dp_native_candidate_tensor_provenance_payload_v1
selection_effect=False
candidate_generation_effect=False
candidate_tensor_mutation_effect=False
candidate_generation_authorized=False
trajectory_rewrite_authorized=False
dp_modification_authorized=False
payload_valid=True
pre_camp_scoring_tensor.sha256 valid
pre_camp_scoring_tensor.shape valid
pre_camp_scoring_tensor.dtype valid
post_camp_selector_tensor.sha256 valid
post_camp_selector_tensor.shape valid
post_camp_selector_tensor.dtype valid
hash_input=contiguous_candidate_tensor_bytes
nan_policy=preserve_tensor_bytes
pre_post_tensor_hash_equal=True
selected_index_in_range=True
candidate_count matches atoms row count
post_selector_candidate_count matches atoms row count
no_candidate_row_append=True
no_coordinate_heading_speed_rewrite_by_camp=True
reference_blend_present=False
reference_blend_stage_hash_separated=True
outcome_label_input=False
closed_loop_outcome_fields_read=False
candidate_generation_contract.reference_blend_steps=None
candidate_generation_contract.guidance_enabled=False
candidate_generation_contract.changes_diffusion_planner_weights=False
```

Selection log SHA-256 values:

```text
sample_normal_seed101_tl_off=7d301ab9ec5b03874f3e82ed03869970f3cdedeca5bf3d82d03637f6967a02f5
sample_normal_seed101_tl_on=06df752425bc048985c130d877bf6ec853fc54e4bddff43b0fa65f7ca14aba0f
sample_normal_seed102_tl_off=f74e5e953c64f8bc84ce884aa5e52686f9a19b878dcf61b9485925a6e5464f96
sample_normal_seed102_tl_on=a021db9bb46f0c10b84b5a3b253a6e8ea118595c1161330d726ebc49de40fbfa
sample_normal_seed103_tl_off=67dbccdf11a3dcc7da05e3e0c1db6fb185f1b6a4d5fdb6dc3eae066d47aa0e1e
sample_normal_seed103_tl_on=7ad23dda677f039b64bbede492a67865b498570f110c4826dd5689430dd88b24
sample_tl_seed101_tl_off=722f7e70330fe08cc42d92c3ab3b4c00d4c24e825d493607e26ce07272bcb0a1
sample_tl_seed101_tl_on=a3b7cddfcfb3b877c1210f957dc8656b5bcb7747ecdfe1993b04fbef17b32ea6
sample_tl_seed102_tl_off=466bb7a242fe7fb75d98a8b315eb1ffdb47947048f322e921ead27401107667c
sample_tl_seed102_tl_on=712b4d0bca44077bd8db9b365e96089ce6b4d0cc2fb61adcde3f7615e9f84ec9
sample_tl_seed103_tl_off=d3a140040b16e2715ebbcb56d58b908233bb37796d4a6f385bdbb4ec45a7fe86
sample_tl_seed103_tl_on=598eca1e7b68cd70d2bdc2ac4006cc85e8d3601357b61b4d5aeff6e71e5ffa44
```

## Boundary

This artifact proves only that the fixed broader nonformal logs carry valid
candidate tensor provenance payloads under the clean DP-native data contract.
It does not prove safety improvement, CAMP superiority over DP Top-1,
industrial retraining sufficiency, formal evaluation readiness, or deployable
selector readiness.

## Decision

```text
status=provenance_payload_artifact_audit_passed
fixed_artifact_inspected=True
selection_log_count=12
record_count=36
all_payloads_present=True
all_payloads_valid=True
all_pre_post_tensor_hash_equal=True
all_candidate_count_unchanged=True
all_no_candidate_row_append=True
all_no_coordinate_heading_speed_rewrite_by_camp=True
all_outcome_label_input_false=True
all_closed_loop_outcome_fields_read_false=True
reference_blend_present=False
guidance_enabled=False
dp_modification_authorized=False
replay_executed_by_this_gate=False
candidate_generation_executed_by_this_gate=False
camp_retraining_executed=False
selector_promotion_authorized=False
atom_promotion_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`clean_dp_native_training_data_collection_authorization_only`

The next gate may only decide whether clean DP-native training data collection
is authorized or already sufficiently satisfied by fixed existing artifacts. It
must not run collection/replay unless a later audit explicitly authorizes it.
