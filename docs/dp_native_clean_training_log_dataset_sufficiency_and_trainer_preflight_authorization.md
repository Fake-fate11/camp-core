# DP Native Clean Training Log Dataset Sufficiency And Trainer Preflight Authorization

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_dataset_sufficiency_and_trainer_preflight_authorization_only
```

This is a read-only authorization gate. It audits the fixed broader nonformal
clean-log artifact for dataset sufficiency, label availability, split/leakage
boundaries, and trainer preflight readiness. It does not run training, replay,
candidate generation, DP modification, selector/atom promotion, or any
safety/CAMP-over-DP claim.

## Fixed Input Artifact

```text
run_root=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
collection_summary.json_sha256=05c8c7056dbe7460cfac422b0f1081179021a9df80324a4378cec3bf6dc693f0
clean_dp_native_training_data_contract_validation.json_sha256=c2f8f1b10e9d1a8925886255e8ffa3af151ef1ceaab278027a50a9087f39a7f4
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git fetch --prune origin
exit=0

git rev-parse HEAD origin/main
4dca3dd73a2b554dfce511eb71328ab22955d0d4
4dca3dd73a2b554dfce511eb71328ab22955d0d4

git ls-remote origin refs/heads/main
4dca3dd73a2b554dfce511eb71328ab22955d0d4 refs/heads/main
```

Atom audit boundary remains:

```text
current deployed 9D, 10D, 12D, 13D, and 14D atom schemas are Benders-compatible fixed-candidate atom schemas
non-atom routes remain rejected for replay, training, online promotion, safety-benefit claims, and CAMP-over-DP Top-1 claims
```

## Trainer Preflight Readiness

The robust trainer already has a default-off fail-closed clean-data preflight:

```text
script=scripts/integrations/train_diffusion_planner_robust_camp.py
flag=--require_dp_native_training_data_contract
default=False
enabled_behavior=validate_dp_native_training_data_contract(selection_logs) before atom loading, label loading, optimizer setup, output-dir creation, or checkpoint writes
failure_behavior=raise ValueError before training
summary_behavior=include dp_native_training_data_contract report only when enabled and passed
```

Relevant existing tests:

```text
camp_core/tests/test_diffusion_planner_robust_camp_training_contract_preflight.py
camp_core/tests/test_dp_native_training_data_contract_validator.py
```

## Fixed-Artifact Dataset Analysis

Read-only AutoDL dataset analysis:

```text
analysis_exit=0
records=36
selection_logs=12
unique_groups_for_trainer=12
records_per_group=3
default_val_fraction=0.2
default_split_train_groups=10
default_split_val_groups=2
candidate_counts={"4": 36}
atom_dims={"14": 36}
atom_schema_versions={"dp_camp_v10_14d": 36}
records_with_dp_scene_features=36
records_with_provenance_pre_post_hash_equal=36
unique_pre_camp_candidate_tensor_hashes=27
unique_selection_log_shas=12
selected_index_counts={"0": 7, "1": 8, "2": 7, "3": 14}
```

Feasibility support:

```text
feasible_count_hist={"0": 5, "1": 4, "2": 3, "3": 1, "4": 23}
records_with_at_least_one_selector_feasible_candidate=31
all_infeasible_records=5
```

Label availability:

```text
records_with_candidate_closed_loop_outcomes_list=0
records_with_candidate_closed_loop_outcomes_none=36
label_source_closed_loop_outcome_ready=False
label_source_safety_cost_v1_ready=False
records_with_dp_candidate_rewards=36
finite_reward_records=36
quality_without_progress_ready_records=36
label_source_dp_reward_ready=True
reward_lengths=[4]
```

DP reward fields present for all candidates:

```text
centerline
collision_step
feasibility
kinematic_violated
lane_crossing
lane_near_frac
lane_wide_frac
off_road_fraction
progress
rb_crossing
rb_min_dist
rb_near_penalty
rb_wide_penalty
red_light
safety
sc_cont_penalty
sc_min_dist
sc_n_stopped
sc_near_penalty
sc_wide_penalty
smoothness
static_crossing
total
```

## Sufficiency Decision

```text
clean_contract_satisfied=True
trainer_preflight_available=True
grouped_split_possible=True
dp_reward_label_source_available=True
closed_loop_outcome_label_source_available=False
safety_cost_v1_label_source_available=False
industrial_retraining_sufficient=False
camp_retraining_authorized=False
training_execution_authorized=False
```

Blockers for industrial or deployable retraining:

```text
only_36_records
only_2_routes
only_3_seeds
max_npcs_0_only
nonformal_seeds_only
no_closed_loop_outcome_labels
no_formal_eval
```

Interpretation:

```text
The fixed artifact is sufficient for a clean-data contract and trainer
preflight readiness audit.

The fixed artifact is not sufficient for industrial CAMP retraining,
deployment, selector promotion, atom promotion, safety claims, or CAMP-over-DP
claims.

Because dp_candidate_rewards are present and finite for all 36 records, a
minimal nonformal static DP-reward trainer smoke could be proposed as the next
user-authorization gate. That would be a trainer-pipeline smoke only, not a
deployable CAMP checkpoint and not evidence of safety improvement.
```

## Authorized Next Work

This gate authorizes only the next authorization request/proposal, not training
execution:

```text
authorized_next_work=dp_native_clean_training_log_minimal_nonformal_static_dp_reward_training_smoke_user_authorization_required
training_execution_authorized_now=False
camp_retraining_authorized_now=False
```

Exact proposed future run envelope if the user explicitly authorizes it later:

```text
purpose=minimal nonformal trainer-pipeline smoke only
input_logs=the 12 fixed camp_selection_log.json files under run_root
mode=static
training_scope=feasible_ranking
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
must_enable=--require_dp_native_training_data_contract
must_enable=--require_atom_schema
must_not_enable=closed_loop_outcome label source
must_not_enable=safety_cost_v1 label source
must_not_run=Full36
must_not_run=formal seeds 11/12/13
must_not_modify=Diffusion Planner
must_not_promote=selector/atom
must_not_claim=safety or CAMP-over-DP
```

## Verification

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_clean_training_log_dataset_sufficiency_and_trainer_preflight_authorization.md
exit=0

python -m py_compile scripts/integrations/train_diffusion_planner_robust_camp.py scripts/integrations/validate_dp_native_training_data_contract.py camp_core/tests/test_diffusion_planner_robust_camp_training_contract_preflight.py camp_core/tests/test_dp_native_training_data_contract_validator.py
exit=0

python -m pytest --rootdir=<temp> <temp>/tests/test_dp_native_training_data_contract_validator.py <temp>/tests/test_diffusion_planner_robust_camp_training_contract_preflight.py -q
11 passed in 1.03s
exit=0

PYTHONDONTWRITEBYTECODE=1 /root/autodl-tmp/dp312_venv/bin/python -m py_compile scripts/integrations/train_diffusion_planner_robust_camp.py scripts/integrations/validate_dp_native_training_data_contract.py camp_core/tests/test_diffusion_planner_robust_camp_training_contract_preflight.py camp_core/tests/test_dp_native_training_data_contract_validator.py
REMOTE_PY_COMPILE_EXIT=0

PYTHONDONTWRITEBYTECODE=1 /root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests/test_diffusion_planner_robust_camp_training_contract_preflight.py camp_core/tests/test_dp_native_training_data_contract_validator.py -q
11 passed in 0.54s
REMOTE_PYTEST_EXIT=0
```

## Prohibited By This Gate

```text
training_execution_authorized=False
camp_retraining_authorized=False
replay_executed=False
candidate_generation_executed=False
closed_loop_outcome_collection_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

## Next Gate

`dp_native_clean_training_log_minimal_nonformal_static_dp_reward_training_smoke_user_authorization_required`
