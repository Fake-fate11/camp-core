# DP Native Clean Training Log Collection Smoke Result

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_collection_smoke_credential_channel_user_action_required
```

The user authorized using `paramiko` for the already-authorized minimal
nonformal DP-native clean training log smoke. No credential is recorded in this
artifact.

## Local And GitHub State

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git fetch --prune origin
exit=0

git rev-parse HEAD origin/main
f98bc5abd7cf1d6552e49cfa9d3e3228f75999ce
f98bc5abd7cf1d6552e49cfa9d3e3228f75999ce

git ls-remote origin refs/heads/main
f98bc5abd7cf1d6552e49cfa9d3e3228f75999ce refs/heads/main
```

## AutoDL Sync And Fixed DP Check

AutoDL CAMP was first fast-forwarded from
`01b47b96989f0eec82a9536c2cdc1b2594ff94d8` to
`f98bc5abd7cf1d6552e49cfa9d3e3228f75999ce` with:

```text
git -C /root/autodl-tmp/camp_core merge --ff-only origin/main
exit=0
```

Post-sync remote state:

```text
CAMP HEAD:
f98bc5abd7cf1d6552e49cfa9d3e3228f75999ce

CAMP origin/main:
f98bc5abd7cf1d6552e49cfa9d3e3228f75999ce

DP HEAD:
7a1d33da277a1992ec474b5383a0c963c72e04e4

DP status:
## tier4-main...origin/tier4-main
```

Remote CAMP still has unrelated untracked files from prior sessions; they were
not modified or cleaned.

## Smoke Runs

First minimal command attempted `steps=1`, `K=2`, uniform selector, iid noise,
and `--camp_candidate_tensor_provenance_logging` with v10 atom scales. It
failed before writing a selection log because v10 atoms require
`candidate_planned_red_light_cost`:

```text
root=/root/autodl-tmp/camp_dp_native_clean_training_log_smoke_f98bc5a_seed101_steps1_k2
replay_exit=1
validator_exit=99
failure=ValueError: DP v8/v9/v10 CAMP selection requires candidate_planned_red_light_cost.
camp_selection_log_produced=False
```

The successful rerun kept the same nonformal minimum and added only the
pre-existing DP reward atom/mask source required by v10 red-light atoms:

```bash
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path /root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
  --route /root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --output_dir /root/autodl-tmp/camp_dp_native_clean_training_log_smoke_f98bc5a_seed101_steps1_k2_dp_reward \
  --device cuda \
  --advance_mode perfect \
  --steps 1 \
  --seed 101 \
  --max_npcs 0 \
  --spawn_probability 0.3 \
  --traffic_lights on \
  --reward_config /root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json \
  --camp_selector_mode uniform \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --camp_feasibility_source dp_reward \
  --num_candidates 2 \
  --candidate_noise_scale 1.0 \
  --candidate_noise_strategy iid \
  --camp_candidate_tensor_provenance_logging
```

Forbidden options were not used:

```text
--camp_collect_closed_loop_outcomes: not set
--candidate_reference_blend_steps: not set
--candidate_guidance_config: not set
--candidate_guidance_scale: not set
Full36: not run
formal seeds 11/12/13: not run
CAMP retraining: not run
DP modification/config/weight change: not performed
selector/atom promotion: not performed
safety or CAMP-over-DP claim: not made
```

## Successful Artifact

```text
root=/root/autodl-tmp/camp_dp_native_clean_training_log_smoke_f98bc5a_seed101_steps1_k2_dp_reward
replay_exit=0
validator_exit=0
records=1
atom_schema_version=dp_camp_v10_14d
candidate_count=2
selected_index=0
candidate_closed_loop_outcomes=None
```

Artifact SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `camp_selection_log.json` | `2effb6dcd31caa2fae1b4a82f73150ec943e983d8e9c4fa16272bc6d5c51102d` |
| `camp_replay_summary.json` | `e9332b9540fef8feaebbaca2d12b079679e0532d70c9c471aae14a4756905670` |
| `camp_validation_summary.json` | `2fc6d4e039e8f7026684a7f809dd80d637516f5e3b5939daec0a6cb101d8f229` |
| `clean_dp_native_training_data_contract_validation.json` | `8eaff01898c5b2cf6dfdca25e16de27624d940aefa9cc5260354decf569381d7` |
| `clean_dp_native_training_data_contract_validation.md` | `b6f9ca90641dabf70fb36ef91daa0e090eb8fdc592d0c541efd044c330bca564` |
| `replay_stdout.log` | `94203c632e930b8295bb7090331cd1fc484997846dd6852048efbb379878b968` |
| `replay_stderr.log` | `b45b6516d6e65b6029bf1ed3d8a985ef9546be6079f71da16a9db5a5e944b298` |
| `validator_stdout.log` | `8eaff01898c5b2cf6dfdca25e16de27624d940aefa9cc5260354decf569381d7` |
| `validator_stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `command_manifest.txt` | `d343e8bb19e354fe93a3097a8fd352ac6fb62bae866af84cd2f8042986deeb22` |
| `replay_exit.txt` | `41c1bfa88b437d3381f1fbb36a8f017bc5ddccda141821cf2e6de1b64febe929` |
| `validator_exit.txt` | `f5b319bd273bd497761f7a2f6213d5329a4d8d7a751ff08aaaed515d0aa5704d` |

## Clean-Log Validator

```json
{
  "schema_version": "clean_dp_native_training_data_contract_validator_v1",
  "records": 1,
  "failed_records": [],
  "passed": true,
  "future_training_input_contract_satisfied": true
}
```

The validator is read-only; its own report therefore says
`replay_executed=false` and `candidate_generation_executed=false` for the
validator process. The smoke replay itself did execute one minimal DP-native
candidate generation pass, as authorized.

## Provenance And Candidate Generation Contract

Selection-log evidence:

```text
candidate_generation_contract.noise_strategy=iid
candidate_generation_contract.reference_blend_steps=None
candidate_generation_contract.guidance_enabled=False
candidate_generation_contract.changes_diffusion_planner_weights=False

camp_candidate_tensor_provenance.schema_version=dp_native_candidate_tensor_provenance_payload_v1
selection_effect=False
candidate_generation_effect=False
candidate_tensor_mutation_effect=False
candidate_generation_authorized=False
trajectory_rewrite_authorized=False
dp_modification_authorized=False
outcome_label_input=False
closed_loop_outcome_fields_read=False
payload_valid=True
pre_post_tensor_hash_equal=True
selected_index_in_range=True
no_candidate_row_append=True
no_coordinate_heading_speed_rewrite_by_camp=True
reference_blend_stage_hash_separated=True
```

Replay and validation summaries both record:

```text
candidate_reference_blend=None
camp_collect_closed_loop_outcomes=False
camp_candidate_tensor_provenance.enabled=True
camp_candidate_tensor_provenance.all_payloads_present=True
camp_candidate_tensor_provenance.all_payloads_valid=True
camp_candidate_tensor_provenance.all_pre_post_tensor_hash_equal=True
camp_candidate_tensor_provenance.all_candidate_count_unchanged=True
camp_candidate_tensor_provenance.all_no_coordinate_heading_speed_rewrite_by_camp=True
camp_candidate_tensor_provenance.outcome_label_input=False
camp_candidate_tensor_provenance.closed_loop_outcome_fields_read=False
```

## Decision

```text
status=smoke_passed
clean_dp_native_training_log_created=True
clean_log_validator_passed=True
records=1
scope=minimal_nonformal_smoke_only
replay_executed=True
dp_native_candidate_generation_executed=True
new_candidate_generation_family_promoted=False
outcome_label_generation_executed=False
camp_collect_closed_loop_outcomes_enabled=False
reference_blend_enabled=False
guidance_enabled=False
formal_seeds_11_12_13_run=False
Full36_run=False
camp_retraining_authorized=False
training_execution_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This single-record smoke proves that the clean DP-native logging and validator
path can execute on fixed DP with candidate tensor provenance enabled. It does
not provide enough data for CAMP retraining and does not prove safety benefit
or CAMP-over-DP Top-1.

## Next Gate

`dp_native_clean_training_log_collection_broader_nonformal_authorization_only_user_approval_required`

This next gate may only decide whether to authorize a broader nonformal clean
DP-native log collection using the same paper-consistent boundaries. It must
not run Full36, formal seeds 11/12/13, CAMP retraining, DP modification,
selector/atom promotion, reference blend, guidance, closed-loop outcome
collection, or safety/CAMP-over-DP claims.
