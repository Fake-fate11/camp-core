# DP Native Training Sufficiency Development Additive Clean Collection Result

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_additive_clean_collection_user_authorized_execution
```

This artifact records the user-authorized additive clean collection defined by
`docs/dp_native_training_sufficiency_development_shortfall_remediation_scope_plan.md`.
It used the fixed base artifact and collected only the approved add-on scope.
It then ran only the clean DP-native training data contract validator and the
development sufficiency profile validator against the combined base-plus-add-on
selection logs.

It did not run CAMP retraining, closed-loop outcome collection,
reference_blend, guidance, postprocess/postselection, Full36, formal seeds
11/12/13, Diffusion Planner modification, selector/atom promotion, or any
safety/CAMP-over-DP claim.

## Fixed Artifacts

```text
base_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_development_collection_73aec55_20260624T075109Z
additive_artifact=/root/autodl-tmp/camp_dp_native_training_sufficiency_additive_clean_collection_79343f9_20260624T082432Z
```

## HEAD Evidence

```text
local_HEAD=79343f9f50299849d1d3ebc5b6a49cab86752096
origin_main=79343f9f50299849d1d3ebc5b6a49cab86752096
github_refs_heads_main=79343f9f50299849d1d3ebc5b6a49cab86752096
autodl_CAMP_HEAD=79343f9f50299849d1d3ebc5b6a49cab86752096
autodl_CAMP_origin_main=79343f9f50299849d1d3ebc5b6a49cab86752096
autodl_CAMP_github_main=79343f9f50299849d1d3ebc5b6a49cab86752096
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required_DP_fixed_commit=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

AutoDL status during execution:

```text
CAMP status:
## main...origin/main
untracked unrelated prior-session artifacts remain ignored

DP status:
## tier4-main...origin/tier4-main
```

## Authorized Scope Actually Run

The fixed base artifact remained unchanged:

```text
base_selection_log_count=24
base_records=120
base_usable_feasible_records=72
base_usable_by_route={"sample_normal": 40, "sample_tl": 32}
base_unusable_records=48
```

The add-on collection ran exactly:

```text
addon_routes=sample_normal,sample_tl
sample_normal=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
sample_tl=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
addon_seeds=105,106,107,108
traffic_lights=on,off
steps=5
num_candidates=4
candidate_noise_strategy=iid
candidate_noise_scale=1.0
advance_mode=perfect
max_npcs=0
spawn_probability=0.3
camp_selector_mode=uniform
camp_feasibility_source=dp_reward
must_enable=--camp_candidate_tensor_provenance_logging
addon_expected_run_count=16
addon_expected_max_selection_records=80
```

Forbidden flags/options were not present in the executed commands:

```text
--camp_collect_closed_loop_outcomes
--candidate_reference_blend_steps
--candidate_guidance_config
--candidate_guidance_scale
--camp_perfect_tracker_command_postselection
--camp_traffic_light_hybrid_postselection
--camp_underprogress_relaxation
--camp_splice_shadow_rule
Full36
formal seeds 11/12/13
CAMP retraining
Diffusion Planner code/config/weight change
selector/atom promotion
safety benefit claim
CAMP over DP Top-1 claim
```

## Result

```text
replay_collection_completed=True
addon_run_count=16
addon_expected_run_count=16
addon_all_replay_exits_zero=True
addon_selection_log_count=16
addon_records=80
addon_usable_feasible_records=68
addon_unusable_records=12
combined_selection_log_count=40
combined_records=200
combined_usable_feasible_records=140
combined_required_usable_feasible_records=100
combined_usable_feasible_margin=40
clean_contract_validator_exit=0
clean_contract_validator_passed=True
clean_contract_validator_records=200
clean_contract_validator_failed_records=0
development_profile_exit=0
development_profile_passed=True
development_profile_records=200
development_profile_usable_feasible_records=140
development_profile_failed_checks=[]
```

Add-on coverage counts:

```text
addon_counts_by_route={"sample_normal": 40, "sample_tl": 40}
addon_usable_by_route={"sample_normal": 40, "sample_tl": 28}
addon_counts_by_seed={"105": 20, "106": 20, "107": 20, "108": 20}
addon_counts_by_traffic_lights={"off": 40, "on": 40}
addon_candidate_count_values={"4": 80}
addon_selected_index_counts={"0": 24, "1": 17, "2": 22, "3": 17}
```

Combined base-plus-add-on coverage counts:

```text
combined_counts_by_route={"nishishinjuku_lane_change": 40, "sample_normal": 80, "sample_tl": 80}
combined_usable_by_route={"sample_normal": 80, "sample_tl": 60}
combined_counts_by_seed={"101": 30, "102": 30, "103": 30, "104": 30, "105": 20, "106": 20, "107": 20, "108": 20}
combined_counts_by_traffic_lights={"off": 100, "on": 100}
combined_candidate_count_values={"4": 200}
combined_selected_index_counts={"0": 51, "1": 40, "2": 49, "3": 60}
```

Clean-boundary checks:

```text
forbidden_flags_present_in_commands=[]
closed_loop_outcome_collection_enabled=False
reference_blend_enabled=False
guidance_enabled=False
postprocess_postselection_enabled=False
full36_executed=False
formal_seeds_executed=False
camp_training_executed=False
dp_modified=False
selector_promotion_executed=False
atom_promotion_executed=False
safety_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The validator `training_execution_authorized=False`,
`camp_retraining_authorized=False`, `dp_modification_authorized=False`,
`safety_benefit_claim_authorized=False`, and
`camp_over_dp_top1_claim_authorized=False` fields remain part of the profile
report. Passing the development profile makes this combined artifact eligible
for a later explicitly authorized static training smoke, not for automatic
CAMP retraining or deployment.

## Verification

Remote fixed-artifact verification:

```text
remote_addon_replay_run_count=16
remote_addon_all_replay_exits_zero=True
remote_addon_selection_log_count=16
remote_combined_selection_log_count=40
remote_clean_contract_validator_exit=0
remote_clean_contract_validator_passed=True
remote_development_profile_exit=0
remote_development_profile_passed=True
remote_development_profile_failed_checks=[]
```

Local narrow checks:

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_additive_clean_collection_result.md camp_core/tests/test_dp_native_training_sufficiency_development_additive_clean_collection_result.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_additive_clean_collection_result.py
exit=0

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_dp_native_training_sufficiency_development_additive_clean_collection_result.py -q
3 passed in 0.02s
exit=0
```

The direct Windows repo pytest invocation for the same target aborted before
collecting this test because pytest enumerated a pre-existing unavailable
long-path test node unrelated to this documentation-only change:
`test_diffusion_planner_residual_comfort_remediation_followup_materially_different_generator_guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_guarded_fixed_snapshot_screen_rerun_failure_attribution_remediation_implementation_plan.py`.
The target test was therefore run from a temporary copy containing only the
target test and target doc; no repo files were cleaned or modified for that
workaround.

## Remote SHA-256 Evidence

Fixed root files:

| Artifact | SHA-256 |
| --- | --- |
| `preflight.json` | `5cfbfc23132b8ab7c7457a29342cf562a61d1bfba5ba91d7b2f33aa0a532abf3` |
| `collection_summary.json` | `4247b91acd9a6af8db83b8ad55f31e13a4f0c708f80c8ecfbd8cfdfdfc9b1eb3` |
| `collection_summary.md` | `33ea263ef3e803ede9ceed1b64765964d7dafe066e1fad5f0d41a665714c11a1` |
| `run_additive_collection.py` | `9a1fb90a014e2958336e6591869c908a0a2c2ec4c1aadc9fd5d7a43f996625c2` |
| `sha256.json` | `9afd13d7a6cfe21c30d21ff4f3e95afc9764a92890318d41c94b2091b0df5b46` |
| `combined_clean_dp_native_training_data_contract_validation.json` | `f481a26294a30f2c2bea74349857fe388151f721a6172fa192a41bf2f4f96755` |
| `combined_clean_dp_native_training_data_contract_validation.md` | `55fc594c70d20fad2223c88c8d474ea96785f073bf3b8620b0c2ac551bfdd14a` |
| `combined_clean_validator_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `combined_clean_validator_stdout_stderr.log` | `f481a26294a30f2c2bea74349857fe388151f721a6172fa192a41bf2f4f96755` |
| `combined_development_profile_validation.json` | `227f4e7580e229377ecd711b2e3b5ea3648017d4f0d94aed055a0ff2a89a87d1` |
| `combined_development_profile_validation.md` | `0e4e2086ef565868d32d7569ce9769bfebb07ed57a191bc6d0c7722d3c8b587a` |
| `combined_development_profile_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `combined_development_profile_stdout_stderr.log` | `227f4e7580e229377ecd711b2e3b5ea3648017d4f0d94aed055a0ff2a89a87d1` |

Each add-on run directory under the additive artifact contains
`command.json`, `replay_exit.txt`, `replay_stdout_stderr.log`,
`camp_selection_log.json`, and `run_result.json`. The top-level `sha256.json`
records the per-run command, exit, replay log, selection log, and summary
hashes generated before `collection_summary.md` was written; the hash for
`collection_summary.md` above was computed in the post-run read-only
inspection.

## Decision

```text
status=development_additive_collection_clean_contract_and_profile_passed_training_still_blocked
clean_dp_native_training_data_contract_passed=True
development_profile=dp_native_feasible_ranking_development_minimal_v1
development_profile_passed=True
development_profile_failed_checks=[]
usable_feasible_records_sufficient=True
combined_records_sufficient=True
route_count_sufficient=True
seed_count_sufficient=True
traffic_light_state_count_sufficient=True
candidate_count_sufficient=True
training_execution_authorized=False
camp_retraining_authorized=False
collection_replay_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The combined base-plus-add-on artifact now satisfies the clean contract and
the development profile for static DP-reward feasible-ranking training data.
This is only a data-sufficiency result. It does not prove CAMP improves safety
or beats DP Top-1, and it does not authorize retraining, online promotion, atom
promotion, deployment, or any Diffusion Planner change.

## Next Gate

`dp_native_training_sufficiency_development_base_plus_addon_static_dp_reward_training_user_authorization_pending`

The next gate requires explicit user authorization before any training command
is run. If authorized, the training scope should be static, use only the fixed
base-plus-add-on `camp_selection_log.json` files above, use
`label_source=dp_reward`, `reward_key=quality_without_progress`,
`reward_progress_weight=2.0`, and require both
`--require_dp_native_training_data_contract` and `--require_atom_schema`.
It must still forbid closed-loop outcome labels, replay, candidate generation,
Full36, formal seeds 11/12/13, Diffusion Planner modification,
selector/atom promotion, deployable-checkpoint claims, safety claims, and
CAMP-over-DP claims.
