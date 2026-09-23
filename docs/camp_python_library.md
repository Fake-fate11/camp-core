# CAMP Python library

The current method is demonstration calibration followed by fixed within-pool
target sets and the original target-set hinge / CVaR .9 / lambda 1 Benders
trainer. The solver has not been rewritten. Python owns training and independent
evaluation; deployment loads only weights, atom scales and transition scales.

## Install and select

```bash
python -m pip install -e ./camp_core
# Only in the training environment, not the planning node:
python -m pip install -e './camp_core[training]'
```

Use the existing DP environment for generator inference and the official
`planner_metrics` source for TIER IV evaluation. Native lanelet geometry needs
the existing Shapely dependency (`camp_core[nuplan]`).

```python
from camp_core import dp
from camp_core.integrations.diffusion_planner_tier4_npz import native_camp_tick

selector = dp.load('artifacts/camp_v26_k8_50k')
tick = native_camp_tick(
    observation, prediction, identity={'scene': scene, 'frame': frame},
    encoder_tokens=encoder_tokens, token_masks=token_masks,
    origin_seconds=timestamp, ego_x=x, ego_y=y, ego_yaw=yaw,
)
decision = selector.select(tick, mode='scene')  # or 'fixed'
trajectory = decision.selected_trajectory      # unchanged original candidate
selector.reset()                              # a new route/episode
```

`prediction` is `[K,1+N,80,4]`, `N>=32`, with original ordered ego and actor
slots. All K candidates share endpoint availability. There is no chunk-of-eight
selection, candidate-specific missing mask, score-time simplex projection or
unavailable-value imputation. Existing checkpoints retain their 24 status heads
and frozen scales. A small API-training example may contain only the patterns
present in that subset; the loader uses its saved heads instead of requiring 24
populated patterns. Unsupported status heads remain errors, without a fallback.

The selector normally retains its last selected plan. An offline common-stream
experiment must instead use the common **actually executed** previous plan; an
unexecuted CAMP choice must not be described as executed behavior.

## Training with fixed demonstration-calibrated labels

Use a Python 3.12 training environment with the `training` extra for the
JAX/JAXopt trainer. The online DP environment does not need these solver packages.

```python
# Offline comparison order: 7 Safety, 6 Comfort, 3 Other; H is row 0.
names = dp.PREFERENCE_EVIDENCE_NAMES  # exact existing calibration order
calibration = dp.fit(evidence_H_and_candidates, shared_mask, existing_evidence_scales)
costs, target_set = dp.point_targets(
    candidate_evidence, shared_mask, existing_evidence_scales, calibration['beta_hat'],
)
```

These call the SLSQP likelihood/gradient/Hessian functions in
`camp_core.training.preference`. The input
evidence must already have the final source definitions/directions. Existing
scale normalization and clipping to [0,10] are retained; unavailable values
remain unavailable, and omitted terms are not renormalized by beta mass.
`fit` does not run bootstrap. When comparing candidate pools under one calibrated
preference rule, pass the same beta to `point_targets` for both pools instead of
refitting it for each condition.

```python
result = dp.train(
    complete_pool_jsonl=['train/complete_pools.jsonl'],
    embedding_npz=['train/context_free_static_embeddings.npz'],
    atom_scales_json='train/atom_scales.json',
    preference_target_npz='train/point_preference_labels.npz',
    expected_scenes=number_of_training_scenes,
    output_dir='training/fixed', device='cuda:0',
)
```

This calls the trainer in `camp_core.training.diffusion_planner`. Fixed uses
constant-zero context arrays; Scene uses
frozen `masked_mean256` arrays and its established embedded-Fixed initialization:

```python
initial = dp.initialize_scene(
    fixed_checkpoint='training/fixed/best_primal_feasible_checkpoint.npz',
    embedding_dimension=256, output='training/scene_initial.npz',
)
# Pass [initial] as resume_theta_checkpoint to dp.train, with Scene embeddings.
```

Both arms use the same fixed preference labels.
The original native convergence / 500-update work blocks / 100-block 0.1%
patience rule and exact full-K legal separation are unchanged. A work-block or
zero-new-cuts result is not by itself a claim of globally optimal training.

The training pools contain the same 16 deployment atom definitions and endpoint
states. Target NPZ has `anchor_ids`, `target_set_mask [N,K]`, and `beta_hat [16]`.
The numerical optimizer consumes the supplied targets, not an old hand-written
teacher. This call starts training; it is not run by loading the deployment API.

## Independent evaluation and export

```python
outcomes = dp.evaluate(prediction[:, 0], offline_source)
bundle = dp.export(
    fixed_checkpoint='training/fixed/scene_conditioned_parameters.npz',
    scene_checkpoint='training/scene/scene_conditioned_parameters.npz',
    atom_scales='train/atom_scales.json',
    transition_scales='train/transition_scales.json', directory='deployment',
)
dp.export_cpp(
    checkpoint=bundle/'scene_conditioned_camp.npz',
    atom_scales=bundle/'atom_scales.json', transition_scales=bundle/'transition_scales.json',
    path='deployment/scene_cpp.json', candidate_count=8,
)
```

`evaluate` calls the existing official metric adapter, returning per-candidate
outcomes, units, directions and missingness separately. Realized future records
are allowed only here, never in `select`. Training-label alignment is not an
independent driving outcome. Paired aggregation remains experiment-specific.

## C++ online library

The library in [`cpp/camp_online`](../cpp/camp_online/README.md) provides
`camp::Selector`, which loads and
scores both Fixed and Scene with `select/reset`. `dp.export_cpp` exports either
model's exact affine heads; `export_fixed_cpp` remains solely for the existing
Fixed-only Autoware prototype format. The C++ implementation uses status lookup,
atom scaling and original-row argmin. The training solver remains in Python.

The C++ scorer accepts the whole pool of materialized atoms. The host's existing
DP atom materializer remains a separate responsibility; Python's tensor-to-atom
selector is the reference. Scoring the same supplied atoms and phi in both
languages checks the scorer, not parity of independently implemented atom
materializers or complete ROS deployment.

## Official map input

Online: DP receives `LaneletMapBin` and `LaneletRoute`; call the compiled
`camp::lanelet_context(route_handler, lanelet_route)` bridge using its already loaded map.
TrafficLightGroupArray remains a separate timestamped dynamic input.

Offline: `camp_export_map` reads the source map's explicit
`map_projector_info.yaml`, uses the installed official Autoware projector and
centerline helpers, and roundtrips LaneletMapBin with the official conversion.
`camp_core.integrations.autoware_map.AutowareMap` consumes the resulting projected
coordinates directly. Pass its `context(ego_x,ego_y,ego_yaw)` into
`native_camp_tick(..., map_context=context)`. Ego/route/map must share the original
map frame. No inferred origin, guessed MGRS grid, lane-subtype rewriting, or
cropped-NPZ full-road proxy is used. The single OSM example needs no tiled-map
metadata. Missing dynamic phases stay missing despite mapped signal geometry.

Current examples intentionally retain the frozen DP tensor/model version. They
do not upgrade the model to the newest online architecture. A different DP major
tensor layout needs an explicit adapter, not a silent reshape or new checkpoint.

## Runnable examples

The examples below run from the repository root after installing CAMP. They do
not download data, train a model, modify a bundle, or require a particular
machine's research directories.

```bash
# Self-contained API demonstration using synthetic atoms and the bundled weights.
python examples/camp_library/score_demo.py

# One independent saved planning tick, with the original full candidate pool.
python examples/camp_library/select_npz.py \
  --bundle artifacts/camp_v26_k8_50k \
  --observation /path/to/observation.npz \
  --pool /path/to/candidate_pool.npz --mode fixed

# Add a projected full-map snapshot in the same frame as the supplied ego pose.
python examples/camp_library/select_npz.py \
  --bundle artifacts/camp_v26_k8_50k \
  --observation /path/to/observation.npz \
  --pool /path/to/candidate_pool.npz --mode scene \
  --map /path/to/projected_map.json --ego-pose 10.0 20.0 0.5
```

`score_demo.py` exercises only scoring and unchanged-row selection. Its synthetic
atoms are an API fixture, not a physical scenario or a performance result.
`select_npz.py` accepts the decision-time observation fields listed by
`load_native_observation` and a pool NPZ containing `prediction`. Scene mode also
requires `encoder_tokens` and one `mask_<token_type>` array for each token type
in `V26_DP_MASKED_TOKEN_TYPES`; masks use the planner's padding-mask convention.
The script keeps every candidate in the supplied pool and prints the selected
row, scores and endpoint states. Each invocation starts a new selector, so it
does not claim cross-frame continuity. Use the stateful API directly for a
sequence, with actual decision-time timestamps and world poses.

The source data and frozen DP model are supplied by the caller. A projected-map
snapshot must contain `frame_id`, `lanelets`, `route_lanelet_ids`, and `polygons`
as produced by the C++ bridge; `--ego-pose` is required with `--map`. Neither the
NPZ adapter nor map geometry invents missing signal phases or full-road data.
The `evaluate` API additionally requires the upstream `planner_metrics` package
and its offline source records; it is not invoked by these deployment examples.
