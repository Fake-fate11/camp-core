# DP Native Training Sufficiency Development Profile Plan

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_profile_plan_only
```

This plan-only gate defines the smallest paper-consistent development
sufficiency profile that should exist before any future CAMP training request
is considered. It does not run collection, replay, candidate generation,
training, Diffusion Planner modification, selector/atom promotion, or any
safety/CAMP-over-DP claim.

## Heads

```text
local_HEAD=e01722bd974db827bdd806a1fbf6bdb077ebd333
origin_main=e01722bd974db827bdd806a1fbf6bdb077ebd333
github_refs_heads_main=e01722bd974db827bdd806a1fbf6bdb077ebd333
```

Tracked worktree files were clean before this gate. Existing unrelated
untracked handoff/session files were intentionally left untouched.

## Authority

```text
docs/dp_camp_mathematical_contract.md=d52cec8159b0ff46f0abde2c6c492806fbc3db25a2f3b89e1886c0828b1cafd2
docs/dp_camp_benders_formalization.md=5fe5e6830af84ac9dd1477c44a4db8be317c6f807b226be4af851de24dbbdf12
docs/dp_camp_benders_compatible_atom_audit.md=2b42e35f2199603589f7df074c40e627858051bd23190ff0c42002df817a5f0b
docs/dp_native_training_sufficiency_preflight_artifact_audit.md=d9ac2c1cc6850e5f19ce4a596af29bebcf912e6afeef48f26400c30dc363f88f
```

The main iteration audit tail is authoritative for gate order. The atom audit
still records `dp_native_candidate_tensor_provenance_payload_implementation_authorization_only`
as its local next gate, but the main audit has already advanced through
candidate tensor provenance, clean log collection, static smoke, and
training-sufficiency preflight. This gate therefore follows the main audit
tail: `dp_native_training_sufficiency_development_profile_plan_only`.

## Current Fixed Evidence

```text
source_artifact=/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
selection_log_count=12
raw_records=36
usable_static_smoke_records=31
routes={"sample_normal": 18, "sample_tl": 18}
seeds={"101": 12, "102": 12, "103": 12}
traffic_lights={"off": 18, "on": 18}
candidate_count_values={"4": 36}
formal_seed_records=0
clean_contract_passed=True
label_source_records_present=True
candidate_tensor_provenance_clean=True
```

The fixed artifact is clean enough to prove the data path and static trainer
smoke. It is not sufficient to authorize CAMP retraining because it is too
small and too narrow for a development split.

## Proposed Development Profile

Profile name:

```text
dp_native_feasible_ranking_development_minimal_v1
```

Scope:

```text
mode=static
training_scope=feasible_ranking
label_source=dp_reward
reward_key=quality_without_progress
reward_progress_weight=2.0
profile_default_off=True
nonformal_development_only=True
```

The profile is a preflight profile, not a training authorization. Passing it
would only mean that a later explicit training request has enough clean
development evidence to be evaluated. It would not authorize replay,
candidate generation, training, deployment, promotion, or claims by itself.

Required data contract:

```text
require_dp_native_training_data_contract=True
require_candidate_tensor_provenance=True
require_pre_camp_scoring_tensor_hash=True
require_post_selector_tensor_hash=True
require_pre_post_tensor_hash_equal=True
require_selected_index_in_range=True
require_candidate_count_unchanged=True
require_no_candidate_row_append=True
require_no_coordinate_heading_speed_rewrite_by_camp=True
require_no_online_outcome_label_input=True
require_atom_schema=True
allowed_atom_schemas=[
  "camp_legacy_v1_9d",
  "dp_camp_v7_10d",
  "dp_camp_v8_12d",
  "dp_camp_v9_13d",
  "dp_camp_v10_14d"
]
```

Minimum coverage:

```text
min_raw_records=100
min_usable_feasible_records=100
min_routes=3
min_seeds=4
required_traffic_light_states=["off", "on"]
min_candidate_count=4
allow_formal_seeds=False
allow_full36=False
```

Split boundary:

```text
require_heldout_split=True
heldout_split_axis=route_or_seed
train_only_atom_scale_fit=True
validation_groups_must_not_fit_scales=True
formal_eval_groups_forbidden=True
```

Forbidden in this profile:

```text
reference_blend=False
guidance=False
postprocess_mainline=False
postselection_mainline=False
splice_or_materialized_generator=False
new_candidate_generation=False
closed_loop_outcome_online_input=False
dp_code_config_or_weight_change=False
selector_promotion=False
atom_promotion=False
safety_benefit_claim=False
camp_over_dp_top1_claim=False
```

## Current Gap To Profile

```text
raw_record_gap=64
usable_feasible_record_gap=69
route_gap=1
seed_gap=1
traffic_light_state_gap=0
candidate_count_gap=0
formal_seed_gap=0
clean_contract_gap=False
dp_reward_label_gap=False
candidate_tensor_provenance_gap=False
heldout_split_profile_not_yet_implemented=True
```

The smallest admissible evidence gap is therefore not a retraining step. It is
a validator/profile implementation gap followed by a later, separately
authorized clean DP-native development collection proposal. Until that later
authorization exists, collection/replay remains forbidden.

## Decision

```text
status=development_profile_plan_ready
profile_name=dp_native_feasible_ranking_development_minimal_v1
current_artifact_passes_profile=False
failure_class=coverage_and_split_profile_gap
direct_camp_retraining_blocked=True
training_execution_authorized=False
camp_retraining_authorized=False
collection_replay_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
authorized_next_work=dp_native_training_sufficiency_development_profile_default_off_implementation
```

## Next Gate

`dp_native_training_sufficiency_development_profile_default_off_implementation`

The next gate may only implement this named default-off preflight profile and
static tests proving that the current fixed 36-record artifact still fails
closed. It must not run collection, replay, candidate generation, training,
promotion, DP changes, or claims.
