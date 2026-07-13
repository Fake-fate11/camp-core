# V19 Zero-Support Source-Contract Redesign

## Goal

Determine why the immutable fixed-DP K=8 CARLA probe produced zero legal
paired support, correct any implementation defect without using candidate
coverage to choose a threshold, and permit a new source-only probe only if one
unique route/lifting contract is independently justified.

## Fixed Boundaries

- Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`; do not modify its code,
  configuration, weights, checkpoint, environment, or outputs.
- The immutable `float32 [8,80,4]` candidate tensor SHA256 remains
  `8ca8c2e35de6363d40a154033ebee08e326114da0d7ae6790013329988f6a42c`.
  Do not regenerate, edit, smooth, project back, or rehash candidate XY or
  heading.
- Keep route-constrained matching. Global nearest-road/lane,
  `project_to_road=True`, z=0, ego-z fallback, identity inheritance, and
  unknown-lane interpolation remain forbidden.
- Keep candidate 0 and DP operational Top-1 equivalence as a hard source
  completeness gate; `native_ranked_top1=false` remains explicit.
- No SafetyCost, ADE/FDE, latency, selection result, eligible-count target,
  outcome, holdout, or formal seed may select this redesign.
- Preserve all prior failed/no-claim artifacts. This redesign does not replace
  or reinterpret the sealed zero-support receipt.

## Authoritative Evidence

The sealed complete breakdown is
`/root/autodl-tmp/camp_dp_v19_zero_support_source_only_breakdown_a27e292f_20260713T213103CST`
with root
`e2601162e8bbeb1c6ddc781e99246097dda95f4ff5ae7f30b4004d2d512efb4a`.
Its independent review root is
`d540bf6b195db9a33cf31c6b6769d52d1d82d01cda5a19135ac6934c805e5b34`.

The full candidate x 80 decomposition is:

| Failure class | Count | Attribution |
|---|---:|---|
| XODR float32 station round-trip | 405 | implementation/census precision defect |
| continuity propagated after an earlier source failure | 81 | fail-closed consequence, not an intrinsic branch/backtrack |
| before the first frozen route chord | 127 | route-window semantic boundary |
| between directed-edge identity samples | 24 | route discretization/identity representation gap |
| true lateral/non-route | 3 | fixed candidate 7 points 77-79 |

There are zero intrinsic backtracks, non-edge branch hops, identity/station
ambiguities, missing XODR waypoints, or missing elevations in the sealed
record.

## Independent Semantic Sources

- The official [CARLA Python API](https://carla.readthedocs.io/en/latest/python_api/)
  defines `Map.get_waypoint_xodr(road_id, lane_id, s)` with `s` in metres and
  `Waypoint.next(distance)` as approximate-distance topology traversal.
- Official CARLA 0.9.16
  [`client::Map::GetWaypointXODR`](https://raw.githubusercontent.com/carla-simulator/carla/0.9.16/LibCarla/source/carla/client/Map.cpp)
  accepts `float s` and forwards it to the road map.
- Official CARLA 0.9.16
  [`road::Map::GetWaypoint`](https://raw.githubusercontent.com/carla-simulator/carla/0.9.16/LibCarla/source/carla/road/Map.cpp)
  stores that float station, derives the lane section from the station, and
  returns no waypoint for an invalid road/lane/station.
- The official [ASAM OpenDRIVE lane-section
  specification](https://publications.pages.asam.net/standards/ASAM_OpenDRIVE/ASAM_OpenDRIVE_Specification/v1.8.1/specification/11_lanes/11_03_lane_sections.html)
  orders lane sections by road-reference-line `s`; lane identity is unique only
  within its section.

These sources define station and identity semantics. They do not specify
whether a downstream mission-route surface must include a predecessor halo or
how an application must assign identity inside a coarse sample gap at a road
transition.

## Proven Implementation Defect and Selected Correction

The previous map-only census called `get_waypoint_xodr` only with `waypoint.s`
values returned by CARLA. Those values had already crossed the C++ float API
boundary, so their apparent station round-trip error was approximately zero.
The production lifting path instead passes an arbitrary double station from a
route-chord interpolation through the same float boundary. The census therefore
did not exercise the production numeric path.

For each official XODR road length `L`, the outcome-free bound is:

```text
float32_station_error_bound(L) = 0.5 * spacing(float32(L))
map_set_bound = max(bound(L) for every road in the eight frozen XODRs)
station_epsilon = map_set_bound + max(1e-9, 64 * ulp(coordinate_scale_m))
```

The eight-map maximum is `3.0517578125e-05 m`; the existing deterministic
floating allowance remains `1e-9 m`. The corrected frozen station and
continuity epsilons are therefore `3.0518578125e-05 m`. Geometry remains
`1.5273609989704584 m`, and z remains `1e-9 m`.

This correction is selected because it follows directly from the official API
type and all-map XODR road-length census. It does not use any candidate point,
eligible count, selection, or outcome to choose the value. The minimal code
change is to name the frozen tolerances in the existing source-probe harness and
replace only the two obsolete station/continuity literals. No matching rule,
route sample, candidate, DP behavior, or eligibility gate changes.

## Route-Surface Decision: No Unique Correction

The precision correction cannot make the current record legally complete. The
remaining 151 route-coverage points expose a separate semantic choice:

1. retain the current strict future-only route window and exclude points before
   its first chord;
2. add a preregistered predecessor halo and exact OpenDRIVE boundary samples;
3. change finite-chord endpoint/transition representation, with an explicit
   identity rule at route-graph edges.

All three can be implemented without outcomes, but they encode different
scientific support sets. CARLA/OpenDRIVE specifies the map topology and station
identities, not which of these application-level route-window policies is the
correct evaluation contract. The current candidates may diagnose where the
policies differ but may not select the policy that admits them. No independent
mission-route source, scenario route, or pre-existing contract resolves the
choice.

Consequently, this redesign does not select a predecessor halo, endpoint cap,
boundary interpolation, new route source, new sampling step, or new geometry
tolerance. Global nearest-road and all fallbacks remain forbidden.

## Gate Decision

Implement and independently review only the proven float32 station precision
fix. Do not run a new source-only K=8 probe: under the unchanged route contract,
candidate 0 still has route-window failures, while changing that route contract
has multiple scientifically indistinguishable options. Per the user-authorized
stop rule, v19 then closes with honest no-claim and preserves zero legal paired
support.

No matched closed-loop arm, SafetyCost, official metric, latency comparison,
promotion, deployment, activation, closed-loop safety claim, or broad
CAMP-over-DP operational Top-1 claim is authorized by this redesign.
