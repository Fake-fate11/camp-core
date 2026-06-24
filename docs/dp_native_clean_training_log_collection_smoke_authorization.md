# DP Native Clean Training Log Collection Smoke Authorization

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_collection_smoke_authorization_only_user_approval_required
```

## Ref Evidence

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git fetch --prune origin
exit=0

git rev-parse HEAD origin/main
0e0dc0cafef3eb9719e606314f8d670e4ef7f793
0e0dc0cafef3eb9719e606314f8d670e4ef7f793

git ls-remote origin refs/heads/main
0e0dc0cafef3eb9719e606314f8d670e4ef7f793 refs/heads/main
```

## Boundary Evidence

The repo now has the pieces required to validate a future clean DP-native
training log:

```text
scripts/integrations/run_diffusion_planner_camp_replay.py
  --camp_candidate_tensor_provenance_logging
  writes camp_selection_log.json

scripts/integrations/validate_dp_native_training_data_contract.py
  --selection_log
  read-only validator for existing camp_selection_log.json files

scripts/integrations/train_diffusion_planner_robust_camp.py
  --require_dp_native_training_data_contract
  default-off fail-closed trainer preflight
```

The previous availability audit found no tracked clean DP-native training log:

```text
existing_tracked_camp_selection_logs=0
existing_tracked_logs_with_candidate_tensor_provenance=0
```

Creating a new clean log would require running the replay integration, which
enters the DP candidate-generation path. That action is outside the permanent
default prohibition unless a later audit and the user explicitly authorize the
exact scope.

## Current Authorization State

The current user turn continued the active goal, but did not separately
authorize a concrete replay/collection smoke scope. Therefore this gate cannot
authorize execution.

```text
user_explicit_collection_smoke_authorization_present=False
collection_smoke_execution_authorized_now=False
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

## Minimal Scope Requiring User Approval

If the user authorizes this gate later, the minimal permissible smoke scope
should be nonformal and evidence-only:

```text
purpose=produce one small DP-native camp_selection_log.json with provenance enabled
selector=no promotion; existing configured CAMP selector only
must_enable=--camp_candidate_tensor_provenance_logging
must_disable=--camp_collect_closed_loop_outcomes
must_keep=candidate_noise_strategy iid
must_not_set=--candidate_reference_blend_steps
must_not_set=--candidate_guidance_config
must_not_set=--candidate_guidance_scale
must_not_run=Full36
must_not_run=formal seeds 11/12/13
must_not_train=True
must_not_modify_dp=True
post_smoke_required=run validate_dp_native_training_data_contract.py on produced log
claim_scope=provenance/log-contract evidence only; no safety or DP-superiority claim
```

No command is authorized by this document.

## Decision

```text
status=user_authorization_required
implementation_authorized_now=False
execution_authorized_now=False
reason=collection smoke would run replay/candidate generation and no separate user approval for the exact scope is present
```

## Next Gate

`dp_native_clean_training_log_collection_smoke_user_authorization_pending`

This gate is intentionally pending user approval. Do not run replay, generate
candidates, collect outcome labels, train CAMP, promote selectors/atoms, modify
DP, or make safety/CAMP-over-DP claims unless the user explicitly authorizes the
exact minimal smoke scope.
