# DP Native Training Sufficiency Development Collection Usable-Feasible Shortfall Attribution

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_attribution_only
```

This artifact is a read-only attribution of the fixed development collection
shortfall recorded in
`docs/dp_native_training_sufficiency_development_collection_result.md`. It uses
only the fixed AutoDL artifact below. It did not run replay, generate
candidates, train CAMP, modify Diffusion Planner, promote selector/atoms, or
make any safety/CAMP-over-DP claim.

## Fixed Artifact Root

```text
/root/autodl-tmp/camp_dp_native_training_sufficiency_development_collection_73aec55_20260624T075109Z
```

## HEAD Evidence

```text
local_HEAD=b19452b44e4d3ee87c1ba086ac13c3e174c28d26
origin_main=b19452b44e4d3ee87c1ba086ac13c3e174c28d26
github_refs_heads_main=b19452b44e4d3ee87c1ba086ac13c3e174c28d26
autodl_CAMP_HEAD=b19452b44e4d3ee87c1ba086ac13c3e174c28d26
autodl_CAMP_origin_main=b19452b44e4d3ee87c1ba086ac13c3e174c28d26
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

## Code Boundary

`scripts/integrations/validate_dp_native_training_sufficiency_preflight.py`
defines a usable feasible record as a record whose `feasible_mask` list contains
at least one literal `True`. The development profile requires at least 100 such
records.

The collection used `--camp_feasibility_source dp_reward`. In
`scripts/integrations/run_diffusion_planner_camp_replay.py`,
`_candidate_feasibility_from_rewards` marks a candidate infeasible for DP reward
hard gates including:

```text
dp_collision
dp_road_border
dp_lane_crossing
dp_static_collision
dp_kinematic
dp_red_light
dp_underprogress
```

The selector receives that external mask and external reasons; it appends those
reasons and marks a candidate feasible only when no reasons remain. This
attribution does not change that logic.

## Shortfall Summary

```text
records=120
usable_feasible_records=72
required_usable_feasible_records=100
usable_feasible_record_gap=28
unusable_records=48
unusable_definition=feasible_mask_has_no_true_candidate
clean_contract_validator_passed=True
label_source_records_present=True
development_profile_failed_checks=["usable_feasible_records_at_least_min"]
```

Mask pattern counts:

```text
(True, True, True, True)=59
(True, False, True, False)=2
(True, False, True, True)=1
(False, True, False, False)=1
(False, True, False, True)=3
(False, True, True, True)=1
(False, False, True, False)=4
(False, False, True, True)=1
(False, False, False, False)=48
```

Only the 48 `(False, False, False, False)` records fail the usable-feasible
record definition.

## Route Attribution

```text
nishishinjuku_lane_change_records=40
nishishinjuku_lane_change_usable_records=0
nishishinjuku_lane_change_unusable_records=40
nishishinjuku_lane_change_false_candidates=160/160
nishishinjuku_lane_change_record_reasons={"dp_road_border": 40, "dp_lane_crossing": 40}
nishishinjuku_lane_change_candidate_reasons={"dp_road_border": 160, "dp_lane_crossing": 160}

sample_normal_records=40
sample_normal_usable_records=40
sample_normal_unusable_records=0
sample_normal_false_candidates=0/160

sample_tl_records=40
sample_tl_usable_records=32
sample_tl_unusable_records=8
sample_tl_false_candidates=61/160
sample_tl_record_reasons={"dp_red_light": 5, "dp_lane_crossing": 4}
sample_tl_candidate_reasons={"dp_underprogress": 24, "dp_lane_crossing": 20, "dp_red_light": 20}
```

The record-level shortfall is dominated by the lane-change route. All 40
`nishishinjuku_lane_change` records are unusable because every candidate is
blocked by DP road-border and lane-crossing hard gates. `sample_normal`
contributes no unusable records. `sample_tl` contributes 8 unusable records:
4 records with only `dp_red_light`, 3 records with only `dp_lane_crossing`, and
1 record with both `dp_lane_crossing` and `dp_red_light`.

`dp_underprogress` appears only on false candidates inside otherwise usable
`sample_tl` records. It reduces candidate-level support but does not explain
any of the 48 unusable records counted against the development profile.

## Traffic-Light Attribution

```text
traffic_lights_off_unusable_records=22
traffic_lights_off_record_reasons={"dp_road_border": 20, "dp_lane_crossing": 22}
traffic_lights_on_unusable_records=26
traffic_lights_on_record_reasons={"dp_road_border": 20, "dp_lane_crossing": 22, "dp_red_light": 5}
```

Traffic-light `on` has 4 more unusable records than `off`; that difference
comes from `sample_tl` red-light/lane-crossing records. It is secondary to the
lane-change route failure, which contributes 20 unusable records under each
traffic-light setting.

## Candidate-Level Reason Counts

Across all false candidates in the 120-record artifact:

```text
dp_lane_crossing=180
dp_road_border=160
dp_underprogress=24
dp_red_light=20
```

False-candidate reason combinations:

```text
("dp_road_border", "dp_lane_crossing")=160
("dp_underprogress")=24
("dp_lane_crossing")=17
("dp_red_light")=17
("dp_lane_crossing", "dp_red_light")=3
```

## Remote Evidence

Root SHA-256 evidence from the fixed artifact:

```text
collection_summary.json=363dcc3a81cc737e6962c983d77425f59e56f4acccd56200bb15397edbe05dc8
clean_dp_native_training_data_contract_validation.json=056262e969d4084e5ecd971c2c9bddafd0d9b63c0049744069aacffde5773014
development_profile_validation.json=2f62ab3575f5264faed34d6110fbba9ff8d552ea1b76585b0b488f5c61ce0259
development_profile_exit.txt=4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865
```

Read-only attribution extraction:

```text
remote_shortfall_attribution_analysis_exit=0
remote_replay_executed_now=False
remote_candidate_generation_executed_now=False
remote_training_executed_now=False
```

## Verification

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_attribution.md camp_core/tests/test_dp_native_training_sufficiency_development_collection_shortfall_attribution.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_collection_shortfall_attribution.py
exit=0

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_dp_native_training_sufficiency_development_collection_shortfall_attribution.py -q
4 passed in 0.03s
exit=0
```

The direct Windows repo pytest invocation for the same target aborted before
collecting this test because pytest enumerated a pre-existing unavailable
long-path test node unrelated to this attribution-only change. The target test
was therefore run from a temporary copy containing only the target test and
target doc; no repo files were cleaned or modified for that workaround.

## Decision

```text
status=usable_feasible_shortfall_attributed_fail_closed
failure_class=dp_reward_hard_gate_route_support_shortfall
primary_blocker=nishishinjuku_lane_change_all_candidates_dp_road_border_and_dp_lane_crossing
secondary_blocker=sample_tl_red_light_and_lane_crossing_all_false_records
clean_contract_failure=False
label_source_failure=False
raw_record_count_sufficient=True
route_count_sufficient=True
seed_count_sufficient=True
traffic_light_state_count_sufficient=True
candidate_count_sufficient=True
usable_feasible_records_sufficient=False
training_execution_authorized=False
camp_retraining_authorized=False
replay_authorized_now=False
candidate_generation_authorized_now=False
dp_modification_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This gate does not justify CAMP retraining. The fixed collection is clean but
not development-profile sufficient because it has only 72 usable feasible
records. Any remediation must avoid changing DP, reference_blend, guidance,
postprocess/postselection, closed-loop outcome labels, selector/atom promotion,
and safety/CAMP-over-DP claims.

## Next Gate

`dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_remediation_scope_plan_only`

The next gate may only plan a stricter future collection or artifact selection
scope to obtain at least 100 usable feasible DP-native records. It must not run
replay, generate candidates, train CAMP, modify DP, promote selector/atoms, or
make safety/CAMP-over-DP claims.
