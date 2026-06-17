# DP-CAMP SafetyCost v1

This note defines the first deployable comparison score for deciding whether a
DP-CAMP variant is better than Diffusion Planner Top-1 in the fixed Tier4
Diffusion Planner simulator.

This is an evaluation contract, not a new selector, not a new CAMP atom schema,
and not a Benders subproblem. The Diffusion Planner neural sampler,
postprocessing, PerfectTracker, and closed-loop simulator remain outside the
CAMP finite-candidate master.

## Relationship to Trajectron++ CAMP

The Trajectron++ CAMP evaluation reported a weighted-and-clipped safety metric:
normalized safety atoms were clipped before aggregation so rare outliers could
not dominate the reported Safety CVaR. The important rule was:

```text
compare fixed candidate selectors using a predeclared weighted safety cost,
then report mean and tail risk.
```

DP-CAMP SafetyCost v1 follows that reporting logic, but uses DP closed-loop
summary outcomes instead of Trajectron++ map atoms. It is computed at replay
run level from matched `camp_validation_summary.json` rows.

## Components

SafetyCost v1 is lower-is-better:

```text
SafetyCost_v1 =
  100 * collision_rate
+  10 * near_miss_rate
+  20 * lane_violation_rate
+  30 * realized_red_light_rate
+  15 * planned_red_light_rate
+   1 * clip(mean_jerk_mps3 / 10.0, 0, 10)
+   2 * clip(mean_lateral_acceleration_mps2 / 2.0, 0, 10)
+   2 * clip(1.0 - route_completion_rate, 0, 1)
```

Component mapping:

| SafetyCost component | Replay summary field | Normalization |
| --- | --- | --- |
| `collision_rate` | `obb_collision_rate` | clipped to `[0, 1]` |
| `near_miss_rate` | `near_miss_rate` | clipped to `[0, 1]` |
| `lane_violation_rate` | `lane_violation_rate` | clipped to `[0, 1]` |
| `realized_red_light_rate` | `red_light_violation_rate` | clipped to `[0, 1]` |
| `planned_red_light_rate` | `planned_red_light_violation_rate` | clipped to `[0, 1]` |
| `mean_jerk_mps3` | `mean_jerk_magnitude_mps3` | divide by `10.0`, clip to `[0, 10]` |
| `mean_lateral_acceleration_mps2` | `mean_lateral_acceleration_mps2` | divide by `2.0`, clip to `[0, 10]` |
| `route_shortfall` | `1 - route_completion_rate` | clipped to `[0, 1]` |

The weights intentionally mirror the existing DP-CAMP closed-loop outcome
weights where possible: collision `100`, near miss `10`, lane `20`, red light
`30`, jerk `1`, lateral acceleration `2`, and progress/route completion `2`.
Planned red-light exposure is kept separate from realized red-light violation
and receives weight `15`, half of the realized-red penalty. This makes planned
red visible without allowing it to override actual collisions or realized red
violations.

## Paired Comparison

Every claim must be paired against DP Top-1 on identical run keys:

```text
DeltaSafetyCost_v1 = SafetyCost_v1(CAMP) - SafetyCost_v1(Top1)
```

Lower is better. A CAMP variant may claim lower composite safety cost only when
the deterministic paired bootstrap interval satisfies:

```text
ci95_high(DeltaSafetyCost_v1) < 0
```

The comparison script uses deterministic percentile bootstrap with 10,000
resamples, matching the existing DP-CAMP replay comparison convention.

## Tail Risk

SafetyCost v1 also reports upper-tail CVaR:

```text
SafetyCost_v1_CVaR90 = mean of the worst ceil(0.10 * N) run costs
```

For paired comparisons, the report includes the CVaR90 difference between the
variant and Top-1 over the common run keys. This is a tail-risk diagnostic. It
does not replace the paired mean SafetyCost claim rule above.

## Hard Safety Gate

The score cannot mask hard safety regressions. A CAMP variant is not accepted as
better than DP Top-1 unless all hard-gate checks pass:

| Gate | Rule |
| --- | --- |
| Collision | paired `obb_collision_rate` mean delta <= 0 and CI high <= 0 |
| Near miss | paired `near_miss_rate` mean delta <= 0 and CI high <= 0 |
| Lane violation | paired `lane_violation_rate` mean delta <= 0 and CI high <= 0 |
| Realized red light | paired `red_light_violation_rate` mean delta <= 0 and CI high <= 0 |
| Completion | paired `route_completion_rate` CI low >= `-0.001` |
| Latency | variant `p95_selection_latency_ms` CI high <= `95 ms` |
| Contract | every paired CAMP run carries `dp_camp_finite_candidate_contract_v1` |
| Formal seeds | no paired run uses seeds `11`, `12`, or `13` |

The latency rule uses a `95 ms` threshold to leave a `5 ms` margin under the
nominal `100 ms` budget. If a future comparison records total planning-path
latency separately from selector latency, the total planning-path latency must
be used for the industrial gate.

The final claim rule is:

```text
CAMP is better than DP Top-1 only if:
  hard_gate_passed == true
  and ci95_high(DeltaSafetyCost_v1) < 0
```

## Scenario Buckets

The comparison tool supports explicit scenario buckets. Buckets are not
inferred from route names or metrics, because that would silently mislabel
critical scenes.

Supported bucket names:

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

Optional manifest format:

```json
{
  "routes": {
    "sample59_86": ["traffic_light", "red_light_turn"]
  },
  "run_keys": {
    "sample59_86|1|200|4|0.3|on|perfect": ["dense_scene"]
  },
  "default_buckets": []
}
```

Every run is always included in `overall`. Additional buckets come only from
the manifest. If a route or run key is not in the manifest, it remains
`overall` only.

## Current Interpretation

The existing `redstopfloor05` checkpoint is mathematically certified under the
finite-candidate DP-CAMP contract, but prior paired evidence shows it should not
be claimed as better than DP Top-1: comfort and red-light metrics still regress
relative to Top-1, and latency margin is limited. SafetyCost v1 formalizes that
judgement as an explicit gate instead of relying on narrative inspection.
