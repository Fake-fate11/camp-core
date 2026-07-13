# V19 CARLA Route-Constrained 2D-to-3D Lifting Design

## Goal

Lift immutable fixed-DP ego-frame `float32 [8,80,4]` candidate points onto
official CARLA/OpenDRIVE lane surfaces without changing candidate XY or heading.
The lifting receipt makes exact-speed eligibility auditable before CAMP scoring,
scenario freeze, simulator advancement, or metric computation.

The paired comparison is named **CAMP-selected candidate vs DP operational
Top-1**. DP operational Top-1 is the unmodified DP's actual single output,
already proven elementwise and SHA-equivalent to K=8 candidate 0. Metadata must
retain `native_ranked_top1=false`; this wording does not claim native K-ranking.

## Fixed Boundaries

- Fixed DP remains
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`; its code, configuration,
  weights, checkpoint, environment, and output schema are immutable.
- CAMP may only score and select unchanged K=8 candidates. Lifting is a
  simulator/source receipt and never rewrites, resamples, smooths, projects
  back into, or rehashes candidate XY or heading.
- The 3+8 causal contract, approved 14D atoms, affine score, nonnegative
  simplex weights, convex master, seed `3411`, two-scenario smoke size, and
  A-to-B-to-C speed ladder remain unchanged.
- Closed-loop outcomes, labels, SafetyCost, trajectory metrics, latency
  results, old holdout data, Full36, and formal seeds `11/12/13` are forbidden
  during lifting, census, tolerance freeze, and scenario selection.
- Scheme 2 flat-only filtering is not enabled. Scheme 3 DP modification is
  permanently forbidden.

## Minimal Architecture

Reuse the existing modules and runner boundaries:

1. `carla_causal_adapter.py` supplies the same-tick finite planar
   `agents_from_world_tf` and a source-only sidecar describing the pre-registered
   current route/lane graph. The sidecar is not added to the fixed-DP tensor
   schema.
2. `carla_exact_speed_source.py` gains pure route-surface matching and receipt
   types. It continues to avoid importing CARLA; an injected map API is used
   only for `get_waypoint_xodr` identity/z verification.
3. The existing v19 bridge/worker supplies immutable K=8 tensors and before/
   after SHA receipts. No second DP worker or general controller is created.
4. `audit_diffusion_planner_dp_camp_v19_carla_exact_speed_sources.py` validates
   lifting receipts, combines them with A/B/C speed eligibility, and emits the
   source-only coverage/exclusion census.

No new dependency is required. Canonical JSON and SHA256 use the standard
library; candidate tensor hashing reuses `array_sha256`.

## Route-Constrained Lifting Contract

### Frozen route surface

Before DP generation for a tick, build a route-lane sidecar only from the
decision-time mission route and its pre-registered lane graph. Each official
sample records `(road_id, section_id, lane_id, s, x, y, z, lane_width,
is_junction)`. Consecutive samples form a surface segment only when they share
one OpenDRIVE identity and are connected in the frozen route graph. The
ordered samples, directed identity edges, map/OpenDRIVE SHA, and exact numeric
tolerances are hashed into `lifting_contract_sha256`.

Global map search, global nearest-road/lane, `project_to_road=True`, nearby-lane
inheritance, and route expansion after candidate generation are forbidden.

### Candidate XY to world XY

For each unchanged candidate point `(x_ego, y_ego)`, compute world XY using the
strict inverse of the same-tick `agents_from_world_tf`. The transform must be a
finite orientation-preserving planar homogeneous matrix. The receipt records
both coordinate pairs and the transform SHA. Candidate arrays are read-only;
the derived world coordinates live only in the lifting receipt.

### Unique lane-surface match

Project world XY onto consecutive centerline chords only inside the frozen
route sidecar. A chord is a possible lane-surface match when:

- the clamped projection lies on that chord;
- lateral residual is no greater than half the interpolated official lane
  width plus the frozen geometry epsilon; and
- the projected `s` lies within the chord's official endpoint interval.

Group possible chords by `(road_id, section_id, lane_id)`. Exactly one identity
must remain. Multiple identities are `lane_identity_ambiguous`. Multiple
non-equivalent `s` values within one identity are `lane_station_ambiguous`.
No tie is broken by proximity, candidate score, speed availability, outcome,
or later metric.

For the unique identity/station, call official
`Map.get_waypoint_xodr(road_id, lane_id, s)`. The returned waypoint must match
road, section, lane, and station within the frozen station epsilon and expose a
finite z. Its transform z is the only allowed z source. Missing or mismatched
OpenDRIVE lookup is source-ineligible. z=0, constant ego z, sample-z
interpolation, unknown-lane interpolation, and one-sided inheritance are
forbidden.

### Candidate continuity

All 80 points must lift. Consecutive receipts must either remain on the same
identity with nondecreasing `s` within the frozen station epsilon, or traverse
one directed edge in the frozen route graph. A non-edge transition, backward
jump beyond epsilon, non-unique branch, or return to a departed branch is
`route_topology_discontinuous`. No post-hoc repair is allowed.

## Receipt Schema

Each tick receipt records:

- schema and `lifting_contract_sha256`;
- scenario/run/tick identity and seed;
- CAMP/DP/map/OpenDRIVE/source/route-graph/transform SHAs;
- immutable K=8 tensor SHA and independent DP operational Top-1 SHA;
- all access counters, which must remain zero for outcomes and metrics;
- one record for every `(candidate_index, point_index)` containing ego XY,
  world XY, road/section/lane/s/z, lateral residual, identity/station/
  continuity checks, and a failure reason when ineligible;
- per-candidate eligibility, point receipt SHA, and exclusion reason; and
- full receipt SHA from canonical JSON (`sort_keys=True`, compact separators,
  `allow_nan=False`).

Candidate 0 is lifted independently from the DP operational Top-1 output. The
canonical per-trajectory payload intentionally omits the origin label, so its
`trajectory_lifting_sha256` is directly comparable. The two lifts must match
in XY, all segment identities, s/z, per-point receipt SHA, and
`trajectory_lifting_sha256`. Their outer tick wrappers may differ because the
K=8 wrapper also records all candidate receipts. Equality failure excludes the
record.

## Eligibility and Speed Ladder

Lifting eligibility is computed before CAMP atoms or scores. Candidate 0 must
be lifting-complete. Then apply exact-speed rung A, followed only when needed by
B and C. A candidate is source-complete only when every lifted segment has an
eligible speed under the current rung. An all-K-ineligible record, incomplete
operational Top-1, or operational/candidate-0 receipt mismatch is retained with
all masks/reasons but excluded from materialization, scoring, training,
calibration, simulation, and evaluation.

Both paired arms use the identical frozen scenario/run keys, map and route
SHAs, lifting contract, source rung, DP model/config/checkpoint, seed, and
simulator settings. The arms may diverge naturally only after their first
selection during closed-loop rollouts.

## Tolerance Freeze

No tolerance is chosen from SafetyCost, trajectory metrics, CAMP selections,
or favourable coverage. Before any source-only K=8 census:

1. freeze the official route sampling step;
2. measure coordinate, chord, station, and `get_waypoint_xodr` round-trip error
   using official map geometry only;
3. derive geometry/station/z/continuity epsilons from the maximum observed
   source-only numerical error plus a deterministic floating-point allowance;
4. seal the exact values, formulas, source rows, and SHAs in an independently
   reviewed artifact.

The later candidate census may measure coverage but cannot change these
values. Any tolerance change restarts the pre-outcome source qualification and
invalidates later freeze artifacts.

## Gate Order and Stop Rules

1. Static-review the written contract and TDD plan.
2. Implement route-sidecar, lifting, canonical receipt, operational Top-1
   equivalence, and fail-closed masks test-first.
3. Run map-only numeric tolerance preflight and independent review.
4. Generate one source-only fixed-DP K=8 probe, verify tensor immutability, and
   validate independent operational Top-1 lifting.
5. Run the full source-only census, report coverage/exclusions, independently
   review, and permanently freeze contract, scenarios, route graph, seed,
   A/B/C rung, and thresholds before any outcome.
6. Only with nonzero legal paired support may the existing frozen CARLA
   closed-loop smoke proceed.

Stop for user direction if legal paired support is zero, DP/3+8/14D/weights
would need modification, the same genuine failure repeats three times, disk or
license gates fail, or the next action is holdout/formal-seed use, promotion,
deployment, activation, model replacement, or a broad claim.

Claim taxonomy remains unchanged until a separate claim decision:
`performance_claim=no_claim`, bounded offline proxy improvement supported,
closed-loop safety not yet supported, and broad CAMP-over-native-DP-Top1 not
supported.
