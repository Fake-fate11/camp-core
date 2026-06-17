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

If the original replay directories are not available but an existing
SafetyCost comparison JSON still contains the benchmark configuration fields,
relabel and recompute the comparison without rerunning DP:

```bash
python scripts/integrations/relabel_diffusion_planner_safety_comparison.py \
  --input_json /path/to/safety_score_v1_comparison.json \
  --scenario_bucket_manifest configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json \
  --output_json /path/to/safety_score_v1_bucketed_comparison.json \
  --output_markdown /path/to/safety_score_v1_bucketed_comparison.md \
  --require_strict_pairing
```

This is still a metadata-only recomputation. It does not rerun the DP sampler,
CAMP selector, tracker, simulator, or training.

To start a manifest without inventing labels, generate a skeleton from an
existing SafetyCost comparison JSON:

```bash
python scripts/integrations/build_diffusion_planner_scenario_bucket_manifest.py \
  --comparison_json /path/to/safety_score_v1_comparison.json \
  --output_json /path/to/scenario_buckets.json \
  --include_run_keys
```

The generated file records every route, run key, seed, NPC count, spawn
probability, traffic-light mode, and tracker mode. Route and run-key bucket
lists are empty until an inspected scenario definition justifies explicit
labels. Optional `--route_bucket ROUTE=BUCKET[,BUCKET]` and
`--run_key_bucket RUN_KEY=BUCKET[,BUCKET]` may be used only after that
inspection.

Use the route inspection tool to collect that evidence from fixed DP route
files and Lanelet2 maps:

```bash
python scripts/integrations/inspect_diffusion_planner_routes.py \
  --diffusion_repo /path/to/Diffusion-Planner \
  --comparison_json /path/to/safety_score_v1_comparison.json \
  --route sample59=/path/to/sample_route.pkl \
  --output_json /path/to/route_inspection.json \
  --output_markdown /path/to/route_inspection.md
```

The inspection reports route length, turn geometry, traffic-light regulatory
groups on the route, and run-level traffic/NPC settings. It still does not
apply labels. In mixed `traffic_lights=true/false` matrices, traffic-light
buckets should usually be run-key labels rather than route-level labels.

For mixed matrices, prefer explicit filters over route-wide labels:

```json
{
  "routes": {
    "sample_map_tl_route_59_to_86": ["sharp_turn"]
  },
  "filters": [
    {
      "name": "sample59_tl_on_red_light_turn",
      "match": {
        "route_name": "sample_map_tl_route_59_to_86",
        "traffic_lights": true
      },
      "buckets": ["traffic_light", "red_light_turn"]
    }
  ],
  "run_keys": {},
  "default_buckets": []
}
```

Filters may match only scenario configuration fields: `route`, `route_name`,
`route_stem`, `seed`, `steps`, `max_npcs`, `spawn_probability`,
`traffic_lights`, and `advance_mode`. They must not match closed-loop outcomes
or SafetyCost components.

The current versioned development manifest for the existing redstopfloor05
full36 artifacts is:

```text
configs/integrations/dp_camp_development_scenario_buckets_redstopfloor05_v1.json
```

This file is intentionally development-only. It records the route-inspection
labels already audited for the existing artifacts: `sharp_turn` for
`sample_map_tl_route_59_to_86`, traffic-light labels only when
`traffic_lights=true`, and `normal` only for the traffic-light-off,
zero-NPC `sample_map_route_2_to_104` runs. It also records the known missing
coverage for `npc_interaction`, `dense_scene`, and `lane_change_or_merge`.
Do not use it to claim final coverage or to label new artifacts unless their
route names and run configuration fields match the same inspected scenario
definitions.

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
