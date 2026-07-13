# V20 CARLA Pre-Generation Route Corridor Design

## Goal

Reopen the CARLA evidence chain after the honest v19 no-claim closeout by
constructing a candidate-independent route corridor before fixed-DP inference.
The corridor must provide auditable OpenDRIVE source coverage near the current
pose and at route-identity boundaries without changing DP inputs, DP outputs,
candidate tensors, or trajectories.

Success for the first execution gate is deliberately narrow: candidate 0 must
remain elementwise equivalent to the DP operational Top-1, candidate 0 must be
source-complete, and at least two unchanged K=8 candidates must be eligible for
a meaningful paired selector comparison. The gate does not require all eight
candidates to be eligible.

## Starting Evidence

The sealed v19 source-only probe generated a real immutable
`float32 [8,80,4]` tensor with SHA256
`8ca8c2e35de6363d40a154033ebee08e326114da0d7ae6790013329988f6a42c`.
Candidate 0 is independently equal to the fixed-DP operational Top-1. The
complete 640-point breakdown is:

| Failure class | Count | Interpretation |
|---|---:|---|
| XODR float32 station round-trip | 405 | Proven implementation precision defect; fixed in v19 |
| Continuity propagated after an earlier failure | 81 | Consequence, not an independent source defect |
| Before the first frozen route chord | 127 | Missing pre-generation predecessor support |
| Between route-identity samples | 24 | Coarse 5 m boundary representation |
| True lateral/non-route | 3 | Correct fail-closed rejection for candidate 7 |

The first frozen route sample is road `0`, section `0`, lane `-2`, station
approximately zero. The 127 pre-start projections are only `0.000112` to
`0.013257` of one 5 m route step behind that endpoint. The route also contains
positive lane IDs whose stations decrease in travel order, while the v19
continuity implementation assumes stations always increase. V20 fixes this
source-contract defect before attempting closed-loop execution.

V19 and all of its artifacts remain immutable historical evidence. V20 does
not reinterpret the sealed v19 zero-support result.

## Fixed Boundaries

- Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`. Its repository, configuration,
  weights, checkpoint, environment, decoder, and output schema are immutable.
- CAMP may only score and select unchanged fixed-DP candidates. It may not
  generate, repair, smooth, blend, project back, or otherwise rewrite a
  trajectory.
- Candidate generation keeps guidance and postprocessing disabled and records
  before/after tensor SHA256 values.
- Candidate 0 remains the DP operational Top-1 baseline with
  `native_ranked_top1=false`; no native K-ranking claim is introduced.
- The approved 14D atom schema, affine `score_k(w)=a_k^T w`, approved atoms,
  nonnegative simplex weights, and convex master remain unchanged.
- Closed-loop outcomes, SafetyCost, trajectory metrics, and later selections
  may not influence corridor construction, tolerances, route choice, source
  eligibility, or exact-speed rung selection.
- Global nearest-road/lane search, `project_to_road=True`, z=0 fallback,
  current-speed fallback, legal-default speed, identity inheritance, unknown
  lane interpolation, and result-driven retries remain forbidden.
- Full36, formal seeds `11/12/13`, promotion, deployment, online activation,
  model replacement, and broad performance or safety claims remain outside
  this design.

## Minimal Architecture

Reuse the existing v19 adapter, lifting module, worker, and source-probe runner.
Do not create another orchestrator or dependency.

The capture schema separates two objects:

1. **DP route**: the existing future route lanes, mission goal, and causal
   history passed unchanged to fixed DP.
2. **Lifting corridor**: an audit-only sidecar built before DP inference from
   the same live CARLA map, OpenDRIVE text, current route, and unique topology.

The lifting corridor is never encoded into the fixed-DP tensor. Its canonical
JSON, map SHA, ordered samples, identity directions, directed edges,
predecessor receipt, boundary receipt, and tolerances are hashed into a new
source-contract SHA.

## Corridor Construction

### Future route

Keep the existing deterministic 5 m future-route generation and route lanes
used by DP. Preserve route order and reject repeated non-contiguous identities,
branches, missing driving lanes, nonfinite geometry, and inconsistent map
hashes.

### Predecessor halo

Before candidate generation, request exactly one existing route step (`5 m`)
behind the current route start using the official CARLA topology API. Exactly
one predecessor must exist. Zero or multiple predecessors fail closed; no
candidate or outcome may choose a branch.

The predecessor sample is added only to the lifting corridor. If its identity
differs from the current route identity, add the official directed predecessor
edge. It is not added to DP route lanes or the mission goal.

The 5 m distance is the already frozen route-sampling constant, not a value
chosen from the observed 6.7 cm candidate excursion. Candidates that leave
this support remain ineligible.

### OpenDRIVE boundaries

Parse road lengths and lane-section starts from the frozen OpenDRIVE text. For
every contiguous route identity, derive its travel direction from the ordered
CARLA waypoints and record the exact section entry and exit station. Add
boundary-adjacent samples one frozen float32 station allowance inside each
identity, then verify each sample with official `get_waypoint_xodr` for exact
road, section, lane, finite station, finite z, lane width, and junction state.

The exact OpenDRIVE boundary station and the inward station used for stable
float32 lookup are both recorded. Adjacent directed identities must have
boundary coordinates within a map-only contact tolerance frozen before any
candidate probe. A missing, ambiguous, or geometrically inconsistent contact
fails closed.

Only consecutive samples of one identity form ordinary surface chords. Exact
boundary samples remove the coarse 5 m unrepresented interval. V20 does not
invent a global cross-lane chord or use proximity to break an identity tie. A
point that still matches zero or multiple identities remains source-ineligible.

### Direction-aware continuity

Each route identity stores travel direction `+1` or `-1` from ordered source
samples. Consecutive points on one identity must satisfy:

```text
direction = +1: current_s + epsilon >= previous_s
direction = -1: current_s <= previous_s + epsilon
```

Identity changes must follow one frozen directed edge, and a departed identity
cannot be re-entered. This replaces the v19 unconditional nondecreasing-station
assumption while retaining fail-closed branch and backtrack behavior.

## Matching and Eligibility

The existing ego-to-world transform, unique lane-surface projection,
`get_waypoint_xodr` identity/z verification, and full 80-point receipts remain.
The matcher consumes ordered corridor chords and direction metadata; it does
not mutate candidate arrays.

Eligibility order is:

1. verify fixed DP, checkpoint, config, request, candidate, and operational
   Top-1 hashes;
2. lift all 80 points for every candidate and the independent operational
   Top-1;
3. require candidate 0 and operational Top-1 lifting equivalence;
4. apply the existing exact-speed A/B/C ladder only to lifting-complete
   candidates;
5. intersect source eligibility with the existing physical feasibility mask;
6. require candidate 0 plus at least one additional eligible candidate before
   paired CAMP selection;
7. score only the eligible fixed candidates with the unchanged affine/simplex
   selector.

Every excluded candidate retains all point receipts and reasons. The known
three true lateral/non-route points are not grandfathered into the corridor.

## Gate Sequence

1. Write and review this contract and its TDD implementation plan.
2. Add RED tests for schema separation, unique predecessor handling,
   OpenDRIVE boundary samples, decreasing-station lanes, immutable tensors,
   ambiguity rejection, and minimum paired support.
3. Implement only the minimum adapter/lifting changes required by those tests.
4. Run a map-only corridor census and independent static review. It freezes
   boundary/contact tolerances without loading candidates or outcomes.
5. Run one new source-only fixed-DP K=8 probe. Do not retry with altered route,
   halo, tolerance, or source rules based on its coverage.
6. If candidate 0 and at least one additional candidate are source-complete,
   independently review and freeze the corridor, route, seed, DP hashes,
   candidate SHA, eligible mask, and exclusion reasons.
7. Continue to a tiny matched CARLA closed-loop smoke with identical paired
   initial state and simulator settings. SafetyCost v1 is primary; official
   trajectory/safety components and six-segment latency are secondary.
8. Independently review execution before any claim decision or expansion.

## Tests and Verification

Focused unit tests use fake map/waypoint objects and must prove:

- a unique predecessor is included only in the lifting corridor;
- zero or multiple predecessors fail closed;
- exact boundary metadata is candidate-independent and hash-stable;
- positive and negative station directions are both accepted only in travel
  order;
- backtracks, non-edge transitions, repeated identities, ambiguous matches,
  and unsupported boundary contacts remain rejected;
- candidate 0 equivalence and all candidate tensor hashes are unchanged;
- fewer than two eligible candidates cannot enter paired CAMP selection; and
- forbidden outcome, metric, future-label, fallback, and mutation fields are
  rejected.

Each code gate runs focused `py_compile`, targeted pytest, v19/v20 pointer and
audit tests, and `git diff --check` locally and on AutoDL. Artifacts retain
`HEADS`, `COMMAND`, stdout/stderr, JSON/MD summaries, `SHA256SUMS`, and root SHA.

## Continuous Authorization and Stop Rules

The user's approval of this design authorizes continuous execution of the
spec, plan, TDD, map-only census, static reviews, one source-only K=8 probe,
its independent review, tiny matched closed-loop smoke, SafetyCost/secondary
metrics, latency review, and evidence packaging. These ordinary gates do not
require repeated user approval.

Stop and request a new decision only if work would require:

- modifying fixed DP, its checkpoint, configuration, or candidate tensor;
- changing the frozen corridor constants or source contract after seeing
  candidate or outcome results;
- a new download, destructive cleanup, license acceptance, or unrelated data
  access;
- promotion, deployment, online activation, model replacement, formal seeds,
  Full36, holdout reopening, or a broad performance/safety claim;
- overriding a fail-closed source, ambiguity, or mathematical-convexity gate;
  or
- a repeated genuine failure showing that this architecture cannot provide
  legal paired support.

Passing the smoke supports only the exact preregistered CARLA scope. It cannot
by itself establish general closed-loop safety or broad CAMP-over-DP claims.
