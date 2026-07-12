# V19 nuPlan Closed-loop Safety Component and Latency Design

## Status and authority

This design closes only the execution-readiness gaps identified by the v19
closed-loop smoke preflight. It does not change SafetyCost v1 weights,
normalizations, hard gates, bootstrap rules, seeds, scenario selection, fixed
DP, candidate tensors, CAMP weights, or baseline provenance.

The baseline remains `DP-default deterministic/MAP baseline` with
`native_ranked_top1=false`. The two-scenario smoke remains non-formal,
nonreactive-traffic evidence and cannot establish a native-Top-1, reactive
closed-loop, complete-scene, or real-world safety claim.

## Alternatives considered

1. **Use only official nuPlan aggregate metrics.** Rejected. Official nuPlan
   v1.2 has collision, TTC, drivable-area, direction, progress, speed, and
   comfort metrics, but no realized-red metric or matched selected-trajectory
   planned-red receipt. Its boolean/score outputs also do not directly equal
   the frozen run-rate fields consumed by SafetyCost v1.
2. **Replace SafetyCost v1 with an official aggregate score.** Rejected. This
   would change the preregistered primary metric after seeing existing evidence.
3. **Add a CAMP-side matched evidence adapter while retaining official metrics
   as secondary.** Selected. The adapter materializes the existing SafetyCost
   v1 fields from official simulation history, map/traffic-light observations,
   and immutable per-tick bridge receipts. No outcome enters training,
   calibration, selection, or online input.

## Architecture

The official Python 3.9 process owns scenario construction, simulation history,
map queries, traffic-light observations, run-level evidence materialization,
official metric computation, and result serialization. The unchanged fixed-DP
Python 3.12 process owns model inference, fixed candidate generation, planned
red calculation already used by the causal 14D materializer, and CAMP atom/
selector work. Atomic NPZ/JSON files remain the only process boundary.

For each scenario, DP-default and CAMP use fresh scenario, simulation, planner,
metric-engine, bridge, and output objects. They share only the frozen scenario,
seed, model/config/checkpoint, simulator configuration, and initial state.
Natural state and candidate divergence after the first selection is expected.

## Time contract and causal history

The selected mini scenarios have an official database interval of `0.05 s`.
The fixed DP causal contract remains exactly 31 history samples at `0.1 s`,
covering the current state and the preceding 3.0 seconds.

At planner iteration `i`, the adapter must use only history ending at `i`. It
requires a uniform 61-sample `0.05 s` window and selects indices
`0, 2, ..., 60` to produce the 31-sample `0.1 s` input. Ego states and
observations are downsampled with the identical indices. The current traffic
light observation, route, mission goal, and map sources remain current-tick
only. Any missing timestamp, nonuniform interval, insufficient window, or
ego/observation misalignment fails the arm and matched pair. No interpolation,
future sample, label, expert future, or current-speed substitute is allowed.

The simulation itself remains at its native `0.05 s` step. Physical closed-loop
jerk and lateral acceleration use the observed time deltas, not a hardcoded
`0.1 s` derivative.

## SafetyCost v1 run-level component materialization

Every component is computed over the completed arm history before any paired
comparison. A missing or non-finite source fails the arm. Denominators and raw
counts are retained beside each rate.

### Collision and near miss

At every finite simulation sample, compute exact 2D polygon distance between
the official ego footprint and every official tracked-object box in that
sample. Use all objects exposed by the official `DetectionsTracks` observation;
this is posterior evaluation and is separate from the online frozen 32 dynamic
+ 5 static candidate-feasibility source.

- `obb_collision_rate = collision_steps / evaluated_clearance_steps`, where a
  collision step has minimum polygon distance `<= 1e-6 m`.
- `near_miss_rate = near_miss_steps / evaluated_clearance_steps`, where a near
  miss step has minimum polygon distance `<= 2.0 m`. Collision steps are also
  near-miss steps, matching the existing replay summary convention.

Official at-fault collision and TTC metrics are reported independently as
secondary metrics; they do not replace these frozen SafetyCost fields.

### Lane violation

For each finite sample, obtain the ego footprint and the union of the true
route lane/lane-connector polygons from the official map API. A lane violation
step is one where the footprint is not covered by that route-corridor union.

`lane_violation_rate = lane_violation_steps / evaluated_lane_steps`.

Missing route polygons, disconnected route geometry, or geometry errors fail
closed. Official drivable-area and driving-direction metrics remain separately
reported secondary results and cannot silently replace this route-lane field.

### Realized red light

Reuse the established `closed_loop_state_transition` convention in
`camp_core.integrations.diffusion_planner._summarize_realized_red_lights`.
For every transition, materialize current red lane-connector baseline points
and aligned directions from the official current-tick traffic-light state and
map. A violation requires finite consecutive ego poses, speed `> 0.5 m/s`, and
an aligned red point within `3.0 m` of the current ego position.

`red_light_violation_rate = realized_red_light_violation_steps /
evaluated_transition_steps`.

No future traffic-light state or official metric substitute is allowed.

### Planned red light

The fixed-DP worker must compute the existing `_fixed_dp_red_cost` on the
selected trajectory for both arms using the same causal request. It writes the
selected scalar cost, its source contract, and the selected trajectory SHA into
the immutable response metadata. For CAMP, the scalar must equal the selected
entry of the already materialized planned-red vector; for DP-default it is
computed on the direct default trajectory without creating or ranking K
candidates.

A tick is a planned-red violation when the selected cost is greater than
`1e-12`, matching the frozen canonical feasibility tolerance.

`planned_red_light_violation_rate = violating_tick_receipts /
validated_tick_receipts`.

Missing receipts, selected-SHA mismatch, cross-arm receipts, or a CAMP scalar
that differs from its selected vector entry fail the matched pair.

### Dynamics and route completion

Materialize global ego `x`, `y`, heading, speed, and timestamps from official
history. Use finite differences with the observed uniform `0.05 s` interval:

- velocity is the global two-vector derived from speed and heading;
- acceleration is the first velocity difference divided by `dt`;
- jerk magnitude is the norm of the next acceleration difference divided by
  `dt`;
- lateral acceleration magnitude is `abs(speed[t] * yaw_rate[t])`, with wrapped
  heading differences.

The reported fields are arithmetic means over all valid derived samples:
`mean_jerk_magnitude_mps3` and `mean_lateral_acceleration_mps2`.

Build one ordered centerline from the frozen mission-route roadblocks and reuse
the monotone projection contract in `_project_route_progress`. Report route
length, projected progress, and
`route_completion_rate = min(max_progress / route_length, 1.0)`. Missing,
disconnected, or zero-length route geometry fails closed.

## Latency receipts

Use `time.perf_counter_ns()` and serialize milliseconds as finite nonnegative
floats. Every tick must carry these six fields:

- `causal_conversion`: live official input through validated 31-sample causal
  materialization;
- `bridge_write`: atomic request NPZ/JSON write and validation;
- `dp_inference`: fixed-model inference calls inside the worker (one default
  call for baseline, eight fixed-candidate calls for CAMP);
- `atom_selector`: CAMP planned-red, canonical 14D materialization, affine
  scoring, and feasible-only selection; exactly `0.0` for DP-default;
- `bridge_read`: response read, hash/identity validation, and selected-array
  extraction;
- `total_planning_path`: planner method entry through construction of the
  returned official `InterpolatedTrajectory` and durable tick receipt.

The fields are not required to sum exactly because process startup, scheduling,
trajectory conversion, and receipt persistence remain inside total path.
`total_planning_path` must be at least every individual segment. The result
reports selector (`atom_selector`) and total planning-path distributions
separately; any later industrial latency gate uses total planning path.

Each tick receipt includes pair/run key, arm, iteration, simulation timestamp,
request/response/selected trajectory SHA values, worker exit code, all six
latencies, and `native_ranked_top1=false`. A partial or duplicate receipt fails
closed and is never overwritten.

## Official secondary metrics

The exact official v1.2 `closed_loop_nonreactive_agents` metric constructors and
thresholds captured by the execution preflight remain frozen. Report collision,
TTC, drivable area, driving direction, expert-route progress, speed limit, and
comfort alongside SafetyCost components. ADE/FDE/miss remain secondary
trajectory-quality diagnostics. Official metrics never fill a missing primary
component by renaming.

## Failure behavior and evidence

Any causal resampling error, source absence, geometry failure, bridge hash
mismatch, candidate mutation, all-K infeasible CAMP response, worker failure,
missing SafetyCost component, missing latency receipt, runner failure, or metric
failure terminates the current arm and matched pair. Preserve all completed
requests/responses, candidates, masks, reasons, histories, raw counts,
official metrics, failure JSON, stdout/stderr, and manifests. Never force
candidate 0, reuse the other arm's result, or delete a failed arm.

## TDD and acceptance

Implementation proceeds test-first in four bounded slices:

1. causal `0.05 -> 0.1 s` history downsampling and rejection tests;
2. pure history/map/traffic-light SafetyCost component materializers using
   synthetic official-shaped objects and exact denominator/count tests;
3. worker/bridge planned-red and latency receipt tests, including SHA and
   cross-arm failures;
4. harness integration with fake runner/metric engine, then official-runtime
   construction-only tests.

Before any real smoke execution, py_compile, target pytest, v18/v19 pointer
tests, causal suites, diff check, AutoDL isolated-runtime tests, fixed head/hash
checks, zero related jobs, and the 10 GiB disk floor must pass. Preflight must
prove all eight SafetyCost fields and all six latency fields can be produced for
both arms without running a simulator. Only a later EOF gate may execute the
two-scenario smoke.
