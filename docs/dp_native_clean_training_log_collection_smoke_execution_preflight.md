# DP Native Clean Training Log Collection Smoke Execution Preflight

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_collection_smoke_user_authorization_pending
```

## User Authorization

The user explicitly authorized one minimal nonformal DP-native clean training
log collection smoke:

```text
scope=minimal nonformal replay only
purpose=produce camp_selection_log.json with --camp_candidate_tensor_provenance_logging
must_not_enable=--camp_collect_closed_loop_outcomes
must_not_enable=reference_blend
must_not_enable=guidance
must_not_run=Full36
must_not_run=formal seeds 11/12/13
must_not_train=CAMP
must_not_modify=Diffusion-Planner
must_not_promote=selector/atom
must_not_claim=safety or CAMP-over-DP
post_step=run clean-log validator only if the log is produced
```

## Local And GitHub State

```text
git status --short --branch
## main...origin/main
untracked unrelated session/slide artifacts remain ignored

git fetch --prune origin
exit=0

git rev-parse HEAD origin/main
33e7e84122a0c0e37becd873ad31af76760fb460
33e7e84122a0c0e37becd873ad31af76760fb460

git ls-remote origin refs/heads/main
33e7e84122a0c0e37becd873ad31af76760fb460 refs/heads/main
```

## Execution Preflight

The replay entry point can write `camp_selection_log.json` only when a CAMP
selector is installed. The minimal clean selector that avoids CAMP retraining
and checkpoint dependence is `--camp_selector_mode uniform` with an existing
approved atom-scales file.

The allowed evidence-only logging flag is:

```text
--camp_candidate_tensor_provenance_logging
```

The paper-faithful boundary rejects the disallowed routes:

```text
--candidate_reference_blend_steps
--candidate_guidance_config
--candidate_guidance_scale
--camp_collect_closed_loop_outcomes
postselection / splice / non-atom logging flags
```

Local asset search found no local Diffusion-Planner checkout or replay assets:

```text
Get-ChildItem F:\ -Directory -Filter Diffusion-Planner -Recurse
exit=0
result=no local Diffusion-Planner checkout found

Get-ChildItem F:\ -Directory -Filter camp_dp_assets -Recurse
exit=0
result=no local camp_dp_assets directory found

Get-ChildItem F:\camp_core-main -Recurse -File -Include
diffusion_planner.pth,diffusion_planner.param.json,replay_default.json,*route*.pkl,lanelet2_map_no_ros.osm
exit=0
result=no local replay assets found
```

Noninteractive SSH preflight did not authenticate without a password prompt:

```text
ssh -o BatchMode=yes -o ConnectTimeout=10 -p 39841 root@connect.bjb2.seetacloud.com "hostname"
exit=1
result=Permission denied (publickey,password).
```

No password was written into commands or logs.

Tracked clean-log availability remains empty:

```text
git ls-files | rg "(^|/)camp_selection_log\.json$"
exit=1
result=no tracked camp_selection_log.json files
```

## Minimal Next Execution Command

This command was not executed in this preflight because the required assets are
only expected on AutoDL and noninteractive SSH was unavailable. It is the
minimal next command shape once AutoDL access is available and CAMP/DP heads
have been rechecked:

```bash
cd /root/autodl-tmp/camp_core
OUT=/root/autodl-tmp/camp_dp_native_clean_training_log_smoke_33e7e841
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/run_diffusion_planner_camp_replay.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path /root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
  --route /root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
  --model_path /root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
  --model_args /root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
  --config /root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json \
  --output_dir "$OUT" \
  --device cuda \
  --advance_mode perfect \
  --steps 1 \
  --seed 101 \
  --max_npcs 0 \
  --spawn_probability 0.3 \
  --traffic_lights on \
  --camp_selector_mode uniform \
  --camp_atom_scales /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json \
  --num_candidates 2 \
  --candidate_noise_scale 1.0 \
  --candidate_noise_strategy iid \
  --camp_candidate_tensor_provenance_logging
```

If that command produces `camp_selection_log.json`, the only authorized
post-step is:

```bash
PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core \
/root/autodl-tmp/dp312_venv/bin/python \
  scripts/integrations/validate_dp_native_training_data_contract.py \
  --selection_log "$OUT/camp_selection_log.json" \
  --output_json "$OUT/clean_dp_native_training_data_contract_validation.json" \
  --output_md "$OUT/clean_dp_native_training_data_contract_validation.md"
```

## Decision

```text
status=execution_not_performed
user_authorization_satisfied=True
local_replay_assets_available=False
noninteractive_autodl_ssh_available=False
camp_selection_log_produced=False
clean_log_validator_run=False
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

## Next Gate

`dp_native_clean_training_log_collection_smoke_autodl_noninteractive_execution_required`

This gate may only recheck local/GitHub/AutoDL heads, verify the fixed
Diffusion-Planner commit and required replay assets, run the minimal command
above or a strictly narrower equivalent, run the clean-log validator on the
produced log, and append audit evidence. It must still not enable closed-loop
outcomes, reference blend, guidance, Full36, formal seeds 11/12/13, CAMP
retraining, DP modification, selector/atom promotion, or safety/CAMP-over-DP
claims.
