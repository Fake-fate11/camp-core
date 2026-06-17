# DP-CAMP Scenario Suite v1

This note defines the development entry point for scenario bucket coverage in
DP-CAMP SafetyCost comparisons. It is an evaluation and dataset-audit contract,
not a selector change, CAMP retraining step, or Diffusion Planner modification.

## Rule

Scenario labels are explicit only. A run may enter a critical bucket only when
the route or exact run key has been inspected and labeled in a manifest. The
comparison and audit tools must not infer critical scenes from route names,
red-light outcomes, jerk, collisions, or other metrics.

Supported buckets:

```text
overall
normal
traffic_light
red_light_turn
sharp_turn
npc_interaction
dense_scene
lane_change_or_merge
```

Every run is always in `overall`. Additional labels come from a manifest such
as `configs/integrations/dp_camp_scenario_buckets_v1.template.json`, copied to
an experiment-specific file and filled after route inspection.

## Workflow

1. Build or update an explicit scenario bucket manifest.
2. Run `scripts/integrations/compare_diffusion_planner_camp_replays.py` with
   `--scenario_bucket_manifest`.
3. Run `scripts/integrations/audit_diffusion_planner_scenario_buckets.py` on
   the comparison JSON.
4. Treat missing required buckets as a coverage gap, not as evidence that CAMP
   is safe in those scenes.
5. Only after bucket coverage and SafetyCost hard gates are both clean should a
   larger non-formal matrix be considered.

## Development Gate

Before claiming DP-CAMP improves over DP Top-1, the comparison must satisfy the
SafetyCost v1 hard gate and the scenario audit must show nonzero coverage for:

```text
normal
traffic_light
red_light_turn
sharp_turn
npc_interaction
dense_scene
lane_change_or_merge
```

This gate is deliberately stricter than the current `redstopfloor05` evidence.
Existing full36 results without a bucket manifest remain `overall` only and
cannot support critical-bucket claims.

## Mathematical Boundary

Bucket labels are evaluation metadata. They do not change the finite candidate
set, CAMP atoms, feasibility mask, affine score, simplex/CVaR/L2 master, or
the generalized Benders-style cutting-plane contract. They also do not make
the DP sampler, tracker, postprocessor, closed-loop simulator, or trajectory
coordinates part of a Benders subproblem.
