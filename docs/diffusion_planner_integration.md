# CAMP + TIER IV Diffusion Planner Integration

## Verified upstream baseline

The integration was designed against `tier4/Diffusion-Planner` branch
`tier4-main`, commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`
(June 11, 2026).

The relevant upstream path is:

1. `scenario_generation.replay.run_route_replay` builds the Autoware
   Lanelet2 map, route, NPC population, and traffic-light state.
2. Every 0.1 seconds it calls `scenario_generation.simulate._predict_batch`.
3. `_predict_batch` returns one `(80, 4)` ego-centric trajectory per active
   vehicle.
4. `advance_scene_mpc` passes the selected trajectory to the configured
   `mpc` or `perfect` tracker. `teleport` directly executes `pred[0]`.

CAMP therefore belongs between steps 2 and 3. The map, route, NPC, and
traffic-light code does not need to be replaced.

## Implemented bridge

`scripts/integrations/run_diffusion_planner_camp_replay.py` wraps the upstream
replay entrypoint and changes ego planning to:

```text
Diffusion Planner observation
  -> K stochastic ego trajectory candidates in one GPU batch
  -> CAMP 9-atom evaluation and hard feasibility mask
  -> selected trajectory
  -> upstream perfect/MPC tracker
```

NPC planning remains on the original deterministic upstream path. CAMP is
applied only to the executed ego plan.

The selector uses:

- Route centerline and route speed limit from the current `SceneContext`.
- Candidate-specific neighbor futures from the Diffusion Planner output.
- Static objects and static NPC positions from the simulator scene.
- The existing CAMP atom bank and feasibility logic.
- Atom scales from `atom_scales_<RUN_TAG>.json`.
- Static learned CAMP weights from either `offline_weights.npy` or the
  `offline_weights` field in a CAMP-Select checkpoint.

The bridge writes:

- The normal upstream replay artifacts.
- `camp_selection_log.json`, containing selected candidate, feasibility mask,
  CAMP scores, weights, and selection latency per step.
- `camp_replay_summary.json`, containing replay termination and bridge config.
- `camp_validation_summary.json`, containing candidate-use, feasibility,
  fallback, and latency aggregates when using the remote wrapper.

## Why static weights are the first supported mode

The current scene-conditioned CAMP checkpoint has a matrix
`Theta: [num_atoms, trajectron_embedding_dim + 1]`. Its input is the
Trajectron scene embedding used during CAMP training.

Diffusion Planner encoder features are not interchangeable with that
embedding. Passing them directly into `Theta` would be dimensionally or
semantically incorrect. The bridge therefore starts with the learned static
CAMP weights, which provide a valid candidate-ranking policy without
retraining either planner.

`CAMPSelector` also implements linear `Theta` inference, but it rejects
missing or dimensionally incompatible embeddings. Enabling scene-conditioned
CAMP requires a separately trained Diffusion-Planner-to-CAMP embedding adapter
or retraining the CAMP mapping head on Diffusion Planner scene features.

The current bridge logs a fixed-width Diffusion Planner input feature vector
as `dp_scene_features` in every `camp_selection_log.json` record. This is the
first DP-compatible feature path for training a scene-conditioned CAMP
`Theta` without depending on private upstream encoder internals.

## Do we need new CAMP weights?

For integration smoke tests, no: uniform static weights are enough to verify
the simulator wiring. For any reported CAMP + Diffusion Planner result, yes:
the old CAMP weights were trained against the Trajectron candidate/cache
distribution and the current AutoDL workspace does not contain those artifacts
anyway. Diffusion Planner produces a different candidate distribution and
different scene features, so it needs either:

- A DP-specific static CAMP weight vector and atom scales.
- Or a full scene-conditioned `Theta` retrained with a compatible Diffusion
  Planner feature adapter and supervised/preference labels.

The current lightweight simulator has no ground-truth future trajectory, so
it cannot directly produce the `gt_atoms` cache required by the existing
`scripts/train/train_offline_preference.py` and
`scripts/train/train_camp_select.py` pipelines. As a practical first step,
`scripts/integrations/train_diffusion_planner_static_camp.py` calibrates a
DP-specific static warm-start from replay candidate atoms using explicit proxy
preferences. It is useful for reproducible closed-loop experiments, but it is
not GT-supervised CAMP-Select training.

`scripts/integrations/train_diffusion_planner_theta.py` trains a
scene-conditioned `Theta` from the same replay logs, using the logged
`dp_scene_features` as the scene input. This is a DP-compatible mapping head,
but the default labels are still proxy preferences unless separate supervised
labels are supplied in a future pipeline.

## AutoDL command

### Assets and Python environment

Download the official v5.0 model, adjacent parameter JSON, Autoware sample
map, and optional larger Nishishinjuku map with resumable transfers:

```bash
cd /root/autodl-tmp/camp_core
bash scripts/integrations/download_diffusion_planner_assets.sh
```

The script checks all four asset SHA256 values validated on June 11, 2026.
Set `DOWNLOAD_NISHISHINJUKU=0` to skip the larger GitHub release asset.

The verified headless AutoDL environment uses Python 3.12 because the PyPI
`lanelet2==1.2.2` wheel is not available for Python 3.13:

```text
Python 3.12.3
torch 2.8.0
torchvision 0.23.0
lanelet2 1.2.2
numpy 1.26.4
scipy 1.14.1
matplotlib 3.9.4
timm 1.0.22
einops 0.8.1
pandas 2.2.3
tqdm 4.67.1
```

`pandas` is needed because the upstream replay module imports the RLVR
training package at module import time, even though the replay itself does
not train.

### Map and route preparation

Autoware maps contain regulatory-element subtypes that the standalone PyPI
Lanelet2 wheel does not register. Create a separate no-ROS map copy:

```bash
ASSETS=/root/autodl-tmp/camp_dp_assets
DP_PYTHON=/root/autodl-tmp/dp312_venv/bin/python

"$DP_PYTHON" scripts/integrations/prepare_diffusion_planner_map.py \
  --input "$ASSETS/sample-map-planning/sample-map-planning/lanelet2_map.osm" \
  --output "$ASSETS/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm"
```

The tool removes only `detection_area`, `no_stopping_area`, `road_marking`,
and `virtual_traffic_light` relations and their references. It preserves
standard traffic-light regulatory elements.

Create the fixed sample-map validation route. Lanelets `59 -> 86` resolve to
a 501.9 m route with four traffic-light groups and about 192.8 m Euclidean
start-to-goal separation:

```bash
"$DP_PYTHON" scripts/integrations/create_diffusion_planner_smoke_route.py \
  --diffusion_repo /root/autodl-tmp/Diffusion-Planner \
  --map_path "$ASSETS/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm" \
  --output "$ASSETS/sample_map_tl_route_59_to_86.pkl" \
  --start_lanelet_id 59 \
  --goal_lanelet_id 86 \
  --min_length_m 450
```

Omit the explicit lanelet IDs to let the script find a deterministic smoke
route, or pass ordered `--via_lanelet_id` values to force a scenario through
specific lanelets.

The official Nishishinjuku release map is extracted to:

```text
/root/autodl-tmp/camp_dp_assets/nishishinjuku_autoware_map/
  nishishinjuku_autoware_map/lanelet2_map.osm
```

Apply the same map-preparation command to that OSM. With seed 42 and
`--min_length_m 500`, the route generator resolves lanelet `569 -> 249`, a
747.2 m route with five traffic-light groups.

### Replay

Set the remote asset paths and run the checked wrapper:

```bash
cd /root/autodl-tmp/camp_core

DIFFUSION_REPO=/root/autodl-tmp/Diffusion-Planner \
DP_PYTHON=/root/autodl-tmp/dp312_venv/bin/python \
DP_MODEL=/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth \
DP_MODEL_ARGS=/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json \
MAP_PATH=/root/autodl-tmp/camp_dp_assets/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm \
ROUTE=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl \
CAMP_CHECKPOINT=/root/autodl-tmp/camp_core/models/camp_select_linear_it100_mapaware_clearance_v2.pt \
CAMP_ATOM_SCALES=/root/autodl-tmp/camp_core/models/production/atom_scales_mapaware_clearance_v2.json \
OUTPUT_DIR=/root/autodl-tmp/camp_dp_replay_smoke_20 \
STEPS=20 \
NUM_CANDIDATES=8 \
bash scripts/integrations/run_diffusion_planner_camp_remote.sh
```

The wrapper validates all assets and the upstream replay API, checks CUDA,
creates a run-local spawn config with `"advance_mode": "perfect"`, runs the
bridge in either the Diffusion Planner `uv` environment or an explicit
`DP_PYTHON` environment, and writes the aggregate validation summary. It does
not modify the Diffusion Planner checkout or install the historical CAMP root
requirements.

The upstream map builder imports Autoware's Python `MGRSProjector`. When that
module is unavailable, the bridge installs a process-local fallback backed by
the standard Lanelet2 UTM projector.

Use a short 20-50 step run first. After it passes, choose a new `OUTPUT_DIR`
and run with `STEPS=200` before long route experiments. Existing replay output
is never deleted or silently reused.

### DP-specific static calibration

After collecting replay logs, train static weights from the candidate atoms:

```bash
cd /root/autodl-tmp/camp_core

DP_CAL=/root/autodl-tmp/camp_dp_assets/camp_dp_static_calibration_v2

DP_PYTHON=/root/autodl-tmp/dp312_venv/bin/python
"$DP_PYTHON" scripts/integrations/train_diffusion_planner_static_camp.py \
  --selection_log /root/autodl-tmp/camp_dp_replay_tl_59_86_k8_steps200_npc/camp_selection_log.json \
  --selection_log /root/autodl-tmp/camp_dp_replay_nishishinjuku_release_k8_steps10/camp_selection_log.json \
  --output_dir "$DP_CAL" \
  --epochs 1000 \
  --lr 0.2 \
  --l2_reg 0.01
```

Use the resulting files in the replay wrapper:

```bash
CAMP_STATIC_WEIGHTS="$DP_CAL/offline_weights_dp_static.npy" \
CAMP_ATOM_SCALES="$DP_CAL/atom_scales_dp_static.json" \
bash scripts/integrations/run_diffusion_planner_camp_remote.sh
```

### DP scene-conditioned Theta training

First collect selection logs with a current checkout. The current replay
wrapper records `dp_scene_features`; older logs produced before this field was
added must be regenerated:

```bash
cd /root/autodl-tmp/camp_core

OUTPUT_DIR=/root/autodl-tmp/camp_dp_replay_theta_collect_59_86_k8_steps200 \
CAMP_STATIC_WEIGHTS=/root/autodl-tmp/camp_dp_assets/camp_dp_static_calibration_v2/offline_weights_dp_static.npy \
CAMP_ATOM_SCALES=/root/autodl-tmp/camp_dp_assets/camp_dp_static_calibration_v2/atom_scales_dp_static.json \
bash scripts/integrations/run_diffusion_planner_camp_remote.sh
```

Then train the DP-compatible scene-conditioned mapping head:

```bash
THETA_OUTPUT_DIR=/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1 \
SELECTION_LOGS=/root/autodl-tmp/camp_dp_replay_theta_collect_59_86_k8_steps200/camp_selection_log.json \
BACKGROUND=1 \
bash scripts/integrations/run_diffusion_planner_theta_remote.sh
```

Monitor the run:

```bash
THETA_OUTPUT_DIR=/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1 \
bash scripts/integrations/monitor_diffusion_planner_theta.sh
```

The training output is:

```text
camp_dp_scene_theta.npz
atom_scales_dp_scene_theta.json
feature_normalization_dp_scene_theta.json
training_summary.json
train_dp_scene_theta.log
```

Use the trained `Theta` in closed-loop replay with:

```bash
OUTPUT_DIR=/root/autodl-tmp/camp_dp_replay_theta_59_86_k8_steps200 \
CAMP_SELECTOR_MODE=linear \
CAMP_CHECKPOINT=/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1/camp_dp_scene_theta.npz \
CAMP_ATOM_SCALES=/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1/atom_scales_dp_scene_theta.json \
bash scripts/integrations/run_diffusion_planner_camp_remote.sh
```

For comparable results, run at least these variants with the same map, route,
seed, NPC settings, steps, candidate count, and DP checkpoint:

- original Diffusion Planner replay without CAMP;
- DP + CAMP uniform/static smoke weights;
- DP + CAMP calibrated static weights;
- DP + CAMP scene-conditioned `Theta`.

The single-run replay wrapper now accepts all four comparable modes via
`--camp_selector_mode top1|uniform|static|linear`. `top1` runs upstream
Diffusion Planner unchanged and does not require CAMP weights; `uniform`,
`static`, and `linear` all use the same K-candidate generation path.

For a full matched matrix over routes, seeds, NPC caps, and spawn
probabilities, use:

```bash
"$DP_PYTHON" scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py \
  --diffusion_repo "$DP_REPO" \
  --route sample59_86="$ROUTE" \
  --route sample58_55="$ASSETS/sample_map_tl_route_58_to_55.pkl" \
  --route nishishinjuku="$ASSETS/nishishinjuku_release_auto_route.pkl" \
  --model_path "$DP_MODEL" \
  --model_args "$DP_PARAM" \
  --config "$CONFIG" \
  --reward_config configs/integrations/dp_camp_reward_eval.json \
  --output_root /root/autodl-tmp/camp_dp_benchmark_v1 \
  --steps 200 \
  --seeds 1,2,3 \
  --max_npcs 4,8 \
  --spawn_probabilities 0.2,0.4 \
  --traffic_light_modes on,off \
  --camp_atom_scales "$THETA_ASSET_DIR/atom_scales_dp_scene_theta.json" \
  --camp_static_weights "$STATIC_ASSET_DIR/offline_weights_dp_static.npy" \
  --camp_theta_checkpoint "$THETA_ASSET_DIR/camp_dp_scene_theta.npz" \
  --num_candidates 8 \
  --camp_lane_corridor_buffer 1.25 \
  --resume
```

The script runs `top1`, `uniform`, `static`, and `theta` for every matched
setting and writes `benchmark_comparison.json` plus
`benchmark_comparison.md`.

Omit `--map_path` when routes from multiple maps are supplied; each route
pickle then uses its own verified map. Enabled traffic lights use the same
seed across all four variants, so NPC spawning and initial signal phases are
paired. `--traffic_light_modes on,off` adds an explicit traffic-control
ablation. `--resume` skips any run that already has
`camp_validation_summary.json`.

The hard route-corridor gate uses
`lane_half_width + --camp_lane_corridor_buffer`. Its default remains `1.0 m`;
benchmark calibration should pass an explicit value, which is recorded in
`camp_replay_summary.json` and `camp_validation_summary.json`.

The versioned reward configuration is:

```text
configs/integrations/dp_camp_reward_eval.json
```

It fixes lane, road-border, static-collision, kinematic, and red-light reward
semantics. The runner calls upstream Diffusion Planner `_score_step` in memory,
so these diagnostics do not require writing the large per-step NPZ tensors.
Realized red-light violations are measured separately from consecutive
closed-loop ego poses against the red route-lane state recorded at each tick.
The output distinguishes realized and selected-plan red-light rates.

For existing replay outputs, create a matched comparison table with:

```bash
"$DP_PYTHON" scripts/integrations/compare_diffusion_planner_camp_replays.py \
  --baseline top1 \
  --variant top1=/root/autodl-tmp/camp_dp_benchmark_v1/sample59_86/seed_1/npc_4/spawn_0p2/top1 \
  --variant uniform=/root/autodl-tmp/camp_dp_benchmark_v1/sample59_86/seed_1/npc_4/spawn_0p2/uniform \
  --variant static=/root/autodl-tmp/camp_dp_replay_static_59_86_k8_steps200 \
  --variant theta=/root/autodl-tmp/camp_dp_replay_theta_59_86_k8_steps200 \
  --output_json /root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1/comparison.json \
  --output_markdown /root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1/comparison.md
```

The comparison output includes per-run rows, per-variant means with 95% CI,
and paired deltas against the requested baseline when runs share the same
route/seed/NPC/spawn key.

## AutoDL validation result

The official v5.0 checkpoint loaded strictly as a 14,545,305-parameter model
on an RTX 5090. A 200-step run on the fixed `59 -> 86` route with eight
candidates, perfect tracking, random NPC spawning, and live traffic lights
completed on June 11, 2026:

- 200 CAMP selection steps and four spawned NPCs.
- All eight candidate indices were selected; nonzero selection rate was 98.5%.
- 99.625% candidate feasibility rate and no all-infeasible fallback.
- Candidate generation plus CAMP selection p95: 111.6 ms.

That run used explicitly untrained uniform weights and unit atom scales only
to validate integration mechanics. It is not a CAMP quality result. Meaningful
evaluation requires the matching trained `offline_weights` and atom-scale
files from the CAMP experiment.

The official Nishishinjuku release map was also validated for 10 steps with
eight candidates. The sanitized map loaded 979 lanelets, including 887
drivable lanelets; all candidates were feasible and no fallback occurred.

DP-specific static calibration was run on 210 replay records, producing:

```text
/root/autodl-tmp/camp_dp_assets/camp_dp_static_calibration_v2/
  offline_weights_dp_static.npy
  atom_scales_dp_static.json
  training_summary.json
```

The training proxy-oracle match rate was 95.7%. A 200-step replay using the
calibrated weights completed with four spawned NPCs, 96.0% nonzero candidate
selection rate, 86.125% candidate feasibility rate, and 11.0% all-infeasible
fallback rate. This confirms the trained files are consumable by the closed
loop, but the fallback rate also makes the limitation explicit: this is a
proxy-calibrated static warm start, not a final CAMP performance result.

The DP-compatible scene-conditioned `Theta` path was then trained from 200
logged replay records with 96-dimensional DP input features. At epoch 1000,
the proxy-label masked match rate was 66.25% on the training split and 77.5%
on the validation split. The checkpoint was consumed successfully by the
linear CAMP selector in a matched 200-step closed-loop replay.

Under the same fixed `59 -> 86` route, seed, candidate count, NPC settings,
and DP checkpoint, the recorded static-vs-Theta comparison was:

| Selector | Fallback rate | Candidate feasibility | p95 selection latency |
| --- | ---: | ---: | ---: |
| DP-specific static CAMP | 9.5% | 83.4375% | 115.69 ms |
| DP scene-conditioned `Theta` | 7.5% | 85.6875% | 113.35 ms |

Both variants completed 200 selection steps, spawned six NPCs, and selected a
nonzero candidate on 97.5% of steps. This is evidence that the full training,
checkpoint-loading, and closed-loop comparison path works. It is not yet a
statistically sufficient claim that scene-conditioned CAMP is generally
better, because the comparison covers one route and one seed and uses proxy
preference labels.

## Current limitations

- Dynamic-vehicle hard collision feasibility now uses oriented bounding-box
  overlap when Diffusion Planner neighbor predictions provide shape metadata.
  Map static objects still fall back to point-distance checks because their
  stable length/width/heading fields are not exposed by the current wrapper.
- The current DP-compatible `Theta` uses a stable 96-dimensional summary of
  Diffusion Planner input tensors, not a learned adapter over private DP
  encoder features.
- Both the static and scene-conditioned DP weights are trained from explicit
  proxy preferences rather than ground-truth closed-loop safety labels.
- Formal evaluation still needs matched original-DP, uniform-CAMP,
  static-CAMP, and scene-conditioned-CAMP runs over multiple routes, seeds,
  traffic-light phases, and NPC densities.
