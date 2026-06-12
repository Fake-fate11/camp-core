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

The lightweight simulator has no counterfactual ground-truth future for every
candidate, so it cannot directly produce the `gt_atoms` cache required by the
existing `scripts/train/train_offline_preference.py` and
`scripts/train/train_camp_select.py` pipelines. The integration runner instead
logs the upstream DP reward breakdown for every candidate. By default,
`scripts/integrations/train_diffusion_planner_static_camp.py` uses the
highest `quality_without_progress` feasible candidate as the preference label.
This subtracts `w_progress * progress` from DP total after the safety and
minimum-progress gates have already been applied, so CAMP learns the remaining
safety-margin, lane, centerline, and comfort tradeoffs instead of collapsing to
a progress-only policy.

`scripts/integrations/train_diffusion_planner_theta.py` trains a
scene-conditioned `Theta` from the same replay logs, using the logged
`dp_scene_features` as the scene input and the same candidate-level DP reward
labels. These are model-based preference labels; final claims still require the
matched closed-loop evaluation matrix.

Theta validation is split by complete selection log, not by individual frame,
so one closed-loop scenario cannot leak into both training and validation.

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

Create the second validated sample-map route with separated endpoints:

```bash
"$DP_PYTHON" scripts/integrations/create_diffusion_planner_smoke_route.py \
  --diffusion_repo "$DP_REPO" \
  --map_path "$ASSETS/sample-map-planning/sample-map-planning/lanelet2_map_no_ros.osm" \
  --output "$ASSETS/sample_map_route_2_to_104.pkl" \
  --start_lanelet_id 2 \
  --goal_lanelet_id 104 \
  --min_length_m 300 \
  --min_endpoint_distance_m 250
```

The route generator rejects repeated lanelets and endpoints closer than
`--min_endpoint_distance_m` by default, preventing loop-like smoke routes from
entering formal benchmarks.

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
  --label_source dp_reward \
  --reward_key quality_without_progress \
  --reward_progress_weight 2.0 \
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
added, or without `dp_candidate_rewards`, must be regenerated:

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
LABEL_SOURCE=dp_reward \
REWARD_KEY=quality_without_progress \
REWARD_PROGRESS_WEIGHT=2.0 \
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
  --route sample2_104="$ASSETS/sample_map_route_2_to_104.pkl" \
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
  --camp_feasibility_source dp_reward \
  --camp_fallback_mode uniform \
  --camp_min_progress_ratio 0.8 \
  --resume
```

The script runs `top1`, `uniform`, `static`, and `theta` for every matched
setting and writes `benchmark_comparison.json` plus
`benchmark_comparison.md`.

Set `--camp_fallback_mode learned` to ablate the all-infeasible fallback
branch; `uniform` preserves the legacy behavior.

Omit `--map_path` when routes from multiple maps are supplied; each route
pickle then uses its own verified map. Enabled traffic lights use the same
seed across all four variants, so NPC spawning and initial signal phases are
paired. `--traffic_light_modes on,off` adds an explicit traffic-control
ablation. `--resume` skips any run that already has
`camp_validation_summary.json`.

For formal DP experiments, `--camp_feasibility_source dp_reward` evaluates all
K candidates with the upstream batched reward implementation. Collision,
road-border, lane, stopped-object, kinematic, and red-light gates are applied
before CAMP scoring. `--camp_min_progress_ratio 0.8` then rejects safe
candidates below 80% of the best safe candidate's progress, preventing a
comfort-only score from selecting a near-stationary trajectory. The complete
candidate reward breakdown is stored in each `camp_selection_log.json` record
for later Static/Theta preference training.

Candidate reward gates use the first
`--camp_reward_horizon_steps` trajectory points (default `30`, or 3 seconds at
10 Hz). This matches the receding-horizon simulator better than treating the
current traffic-light phase as fixed across the full 8-second prediction.
Full-horizon selected-plan metrics remain unchanged.

DP reward training uses a backward-compatible tenth atom,
`progress_shortfall = max(candidate_progress) - candidate_progress`. Legacy
nine-atom checkpoints still load unchanged. New collection runs should use
`configs/integrations/dp_camp_atom_scales_10_bootstrap.json`; training then
writes dataset-calibrated ten-atom scales for the final checkpoints.

For reward-labeled data collection without running obsolete checkpoints, use
the matrix runner with `--variants uniform --skip_compare`. The route, seed,
NPC, traffic-light, reward, and candidate-generation paths remain identical to
the formal four-way benchmark.

The legacy `context` feasibility source remains available. Its route-corridor
gate uses `lane_half_width + --camp_lane_corridor_buffer`, whose default remains
`1.0 m`. All feasibility settings are recorded in the replay and validation
summaries.

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

The following values describe the legacy proxy-label checkpoint and are kept
only for provenance. Its training proxy-oracle match rate was 95.7%. A
200-step replay using the
calibrated weights completed with four spawned NPCs, 96.0% nonzero candidate
selection rate, 86.125% candidate feasibility rate, and 11.0% all-infeasible
fallback rate. This confirms the trained files are consumable by the closed
loop, but the fallback rate also makes the limitation explicit: this is a
proxy-calibrated static warm start, not a final CAMP performance result.

The legacy DP-compatible scene-conditioned `Theta` path was trained from 200
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

## Formal four-way benchmark

The first strictly paired formal matrix completed 144/144 runs over three
routes, three unseen seeds, two NPC caps, two traffic-light modes, and four
selectors. Deterministic 10,000-resample bootstrap statistics, the pairing
audit, exact asset provenance, and an honest interpretation are recorded in
[`diffusion_planner_formal_v4_results.md`](diffusion_planner_formal_v4_results.md).

The principal result is mixed rather than a general CAMP win. Uniform and
Theta improve route completion over original DP Top-1, but also worsen comfort
and selected-plan red-light violations. Theta does not significantly
outperform Static across the full matrix. All variants recorded zero OBB
collisions, so no collision-reduction claim is possible from this run.

## V5 closed-loop outcome labels

The v5 label path replaces `dp_reward` preference labels with
`closed_loop_outcome` labels. During replay, pass:

```bash
--camp_collect_closed_loop_outcomes \
--camp_outcome_horizon_steps 30
```

For each simulation tick and each Diffusion Planner candidate, the runner logs
`candidate_closed_loop_outcomes` in `camp_selection_log.json`. The outcome is
a short-horizon branch evaluation: ego follows the candidate with perfect
tracking in the current ego frame, NPCs use the corresponding Diffusion
Planner neighbor futures, and the value is computed from route progress,
OBB collision, near miss, lane violation, red-light violation, jerk, and
lateral acceleration. This is no longer the upstream DP scalar reward.

For batched collection, use the matrix runner with the uniform variant:

```bash
"$DP_PYTHON" scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py \
  --variants uniform \
  --skip_compare \
  --camp_collect_closed_loop_outcomes \
  --camp_outcome_horizon_steps 30 \
  ...  # same route/seed/NPC/traffic-light/model arguments as the formal matrix
```

Train Static CAMP from the collected logs with:

```bash
"$DP_PYTHON" scripts/integrations/train_diffusion_planner_static_camp.py \
  --selection_log /path/to/camp_selection_log.json \
  --output_dir /root/autodl-tmp/camp_dp_assets/camp_dp_outcome_static_v5 \
  --label_source closed_loop_outcome \
  --outcome_key value
```

Train scene-conditioned `Theta` with:

```bash
LABEL_SOURCE=closed_loop_outcome \
OUTCOME_KEY=value \
THETA_OUTPUT_DIR=/root/autodl-tmp/camp_dp_assets/camp_dp_outcome_theta_v5 \
SELECTION_LOGS=/path/a/camp_selection_log.json:/path/b/camp_selection_log.json \
bash scripts/integrations/run_diffusion_planner_theta_remote.sh
```

After training, rerun the same 144-run strict matrix with the v5 Static and
Theta assets and regenerate paired bootstrap statistics.

### V5 formal matrix result

The v5 closed-loop outcome experiment completed the same strict 144-run
matrix as v4: three routes, unseen seeds 11-13, two NPC caps, two
traffic-light modes, and four selectors. The comparison audit reports
36/36/36/36 runs for Top-1, Uniform, Static, and Theta, with
`strictly_paired=true`. The local artifacts are stored under
`results/diffusion_planner/v5_2082ad5/`.

The result is still mixed, not a general CAMP win. Against DP Top-1, Static
improves route completion by +0.0223 with 95% bootstrap CI [0.0129, 0.0333],
and Theta improves it by +0.0221 with CI [0.0126, 0.0333]. All variants have
zero OBB collision rate, so this run cannot support a collision-reduction
claim. The tradeoff is that Static and Theta both worsen planned red-light
violation rate by +0.0433, with CIs excluding zero, and worsen comfort:
mean jerk magnitude increases by about +0.96 m/s^3 and mean lateral
acceleration by about +0.048-0.049 m/s^2.

Relative to Uniform, Static and Theta still improve route completion by about
+0.0086 to +0.0089, but also increase planned red-light violation rate by
+0.0201. Theta does not improve over Static: Theta-Static route completion
delta is -0.00024 with CI [-0.00048, -0.00005], while the safety and comfort
deltas are effectively tied.

### V6 red/comfort label reweighting

Because v5 was still mixed, v6 tunes only the closed-loop outcome label
weights, not the CAMP selector. The training scripts can now pass
`--outcome_weights configs/integrations/dp_camp_outcome_weights_v6_red_comfort.json`
to recompute candidate labels from the already-collected outcome components.
The v6 weights increase near-miss, lane, red-light, jerk, and lateral
acceleration penalties while keeping the same progress and collision terms.

The v6 strict matrix also completed 144/144 runs with `strictly_paired=true`;
artifacts are stored under `results/diffusion_planner/v6_red_comfort_726f7f1/`.
It does not change the overall conclusion. Static route completion is still
+0.0223 over Top-1 with CI [0.0128, 0.0333], and Theta is +0.0218 with CI
[0.0123, 0.0332]. Planned red-light violation still regresses versus Top-1:
Static is +0.0433 and Theta is +0.0408, both with CIs excluding zero. Comfort
also remains worse: mean jerk magnitude is about +0.96 m/s^3 and mean lateral
acceleration is about +0.046-0.049 m/s^2 versus Top-1.

The reweighting did make Theta slightly less aggressive than Static:
Theta-Static planned red-light delta is -0.0025 with CI [-0.0054, -0.0004],
and mean lateral acceleration delta is -0.0033 with CI [-0.0063, -0.0003].
That small improvement comes with a small route-completion loss
(-0.00048, CI [-0.00081, -0.00019]). This is a label-design result, not a
selector tuning result.

## V7 robust outcome-margin training

The v7 training path keeps the v5 candidate branch outcomes and v6 outcome
weights, but replaces supervised oracle imitation with a CAMP-style robust
margin objective. For record `i`, the best finite feasible outcome defines
the oracle candidate `k*`. Each feasible candidate receives the clipped
outcome margin

```text
m_i,k = clip(beta * (V_i,k* - V_i,k), 0, margin_max)
```

and the scene loss is the largest nonnegative ranking violation:

```text
L_i = max_k max(0, m_i,k + w_i^T(A_i,k* - A_i,k))
```

Infeasible candidates participate in neither the oracle nor the maximum.
Static training optimizes one simplex-constrained `w`. Theta training uses
`w_i = Theta [phi_i; 1]`, with nonnegative unit-sum weights on every training
scene. Both modes minimize either the empirical mean or CVaR of `L_i` plus
L2 regularization. The master problem is solved by adding the current
worst-candidate cut for each scene until no violated cut remains.

Train Static and Theta from the existing v5 logs with:

```bash
COMMON_ARGS=(
  --objective robust_margin_cvar
  --risk_type cvar
  --alpha 0.9
  --margin_scale 0.1
  --margin_clip 2.0
  --l2_reg 1e-4
  --outcome_weights \
    configs/integrations/dp_camp_outcome_weights_v6_red_comfort.json
)

LOG_ARGS=()
while IFS= read -r log; do
  LOG_ARGS+=(--selection_log "$log")
done < <(
  find /root/autodl-tmp/camp_dp_outcome_collect_v5_2082ad5 \
    -path '*/uniform/camp_selection_log.json' -print | sort
)

"$DP_PYTHON" scripts/integrations/train_diffusion_planner_robust_camp.py \
  "${LOG_ARGS[@]}" "${COMMON_ARGS[@]}" \
  --mode static \
  --output_dir /root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v7

"$DP_PYTHON" scripts/integrations/train_diffusion_planner_robust_camp.py \
  "${LOG_ARGS[@]}" "${COMMON_ARGS[@]}" \
  --mode theta \
  --output_dir /root/autodl-tmp/camp_dp_assets/camp_dp_robust_theta_v7
```

The generated Static and Theta artifacts use the existing selector filenames
and checkpoint schema. They must still be evaluated with the unchanged
strictly paired 144-run matrix before making performance claims.

### V7 formal matrix result

The v7 robust outcome-margin matrix completed 144/144 runs with
`strictly_paired=true`. Robust Static significantly reduces planned
red-light violations and mean jerk relative to v6 Static without a
significant route-completion loss. It also improves route completion and jerk
relative to Uniform in the same v7 matrix.

The full target is not met. Static still significantly regresses planned
red-light, jerk, and lateral acceleration relative to DP Top-1. Theta does
not improve over Static and has significantly worse mean jerk. Exact training
metrics, paired bootstrap intervals, cross-version comparisons, and the
artifact inventory are recorded in
[`diffusion_planner_v7_robust_results.md`](diffusion_planner_v7_robust_results.md).

## Current limitations

- Dynamic-vehicle hard collision feasibility now uses oriented bounding-box
  overlap when Diffusion Planner neighbor predictions provide shape metadata.
  Map static objects still fall back to point-distance checks because their
  stable length/width/heading fields are not exposed by the current wrapper.
- The current DP-compatible `Theta` uses a stable 96-dimensional summary of
  Diffusion Planner input tensors, not a learned adapter over private DP
  encoder features.
- Static and Theta v5 now use short-horizon candidate-branch closed-loop
  outcome labels. They are still simulator-derived labels, not human
  preferences or full recursive re-planning rollouts.
- The v5 formal matrix is complete, but selection p95 averages about 105 ms
  for CAMP variants, with bootstrap upper bounds around 114 ms, slightly above
  the simulator's 100 ms tick.
- V5 and the v6 red/comfort label reweighting are complete. The evidence
  supports a route-completion gain, but not a general quality gain, because
  red-light planning and comfort metrics still regress.
- V7 validates robust Static as an improvement over v5/v6 imitation, but not
  as a general win over DP Top-1. The current robust Theta formulation has no
  verified closed-loop benefit over Static.
