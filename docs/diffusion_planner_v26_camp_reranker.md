# CAMP reranking for Diffusion Planner

`DiffusionPlannerCAMPSelector` attaches to the candidate-selection stage of a
frozen Diffusion Planner and returns one unchanged K=8 candidate. It supports
both paper models:

- `fixed`: Fixed-weight CAMP, with one learned weight vector per endpoint-status pattern.
- `scene`: Scene-conditioned CAMP, with weights affine in the frozen DP encoder's
  256-dimensional masked-token mean.

Inference never computes the training Teacher and never reads logged or
simulated future actors. The online path is:

1. Diffusion Planner generates its ordered eight-candidate pool.
2. The selector consumes the same-tick DP actor predictions, planner inputs,
   map/signal context, and its retained previous selected plan.
3. The selector computes the 16 deployment atoms and endpoint states, and pools
   the valid DP encoder tokens for scene-conditioned CAMP.
4. CAMP normalizes each observed atom as `clip(raw / train_scale, 0, 10)`.
5. The selected row is `argmin_k x_k^T w`; ties keep the lowest original row.

## Deployment bundle

The checked-in 50k bundle is under `artifacts/camp_v26_k8_50k/`:

```text
atom_scales.json
transition_scales.json
fixed_weight_camp.npz
scene_conditioned_camp.npz
fixed_weight_camp.json
scene_conditioned_camp.json
metadata.json
```

The two NPZ files are below 1 MiB in total. The frozen Diffusion Planner model
weights are not duplicated in this bundle; the scene mode reuses the DP model
already loaded by the planner.

## DP selector use

```python
from camp_core.integrations.diffusion_planner_v26_selector import (
    DiffusionPlannerCAMPSelector,
    DiffusionPlannerCAMPTick,
)

selector = DiffusionPlannerCAMPSelector.from_directory(
    "artifacts/camp_v26_k8_50k"
)

tick = DiffusionPlannerCAMPTick(
    identity=planning_tick_identity,
    prediction=out["prediction"],
    encoder_tokens=encoding,
    token_masks=encoder_token_masks,
    neighbor_history=raw_inputs["neighbor_agents_past"][0],
    static_objects=raw_inputs["static_objects"][0],
    ego_shape=raw_inputs["ego_shape"][0],
    route_lanes=raw_inputs["route_lanes"][0],
    route_speed_limits=raw_inputs["route_lanes_speed_limit"][0],
    route_has_speed_limits=raw_inputs["route_lanes_has_speed_limit"][0],
    route_atom_context=map_context.route_atom_context,
    signal_authority=map_context.signal_authority,
    drivable_area_geometry=map_context.drivable_area_geometry,
    drivable_area_source_authority=map_context.drivable_area_source_authority,
    origin_seconds=planning_time_seconds,
    ego_x=ego_state.x,
    ego_y=ego_state.y,
    ego_yaw=ego_state.yaw,
    current_speed_mps=ego_state.speed,
)
decision = selector.select(tick, mode="scene")
selected_trajectory = decision.selected_trajectory
```

Use `mode="fixed"` when the encoder output is unavailable. The selector stores
the previously selected world plan for the continuity atom and exposes
`reset()` for route or episode boundaries. `DiffusionPlannerCAMPDecision`
contains the selected row, candidate scores, active weights, atom names,
endpoint-status pattern, normalized atom matrix, and an unchanged copy of the
selected trajectory.

`CAMPDPRerankingPipeline` remains available as the lower-level scorer for tests
or integrations that already own an equivalent atom materializer.
