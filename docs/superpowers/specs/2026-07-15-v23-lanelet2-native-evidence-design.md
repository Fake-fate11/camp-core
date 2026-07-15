# V23 Lanelet2 Native Evidence Design

## Goal

Create a new v23 study on the unchanged TIER IV Diffusion Planner commit
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Add license-frozen Autoware
Universe bidirectional-traffic and TIER IV `scenario_simulator_v2` Lanelet2
maps, preserve their semantics, enlarge native route and training support, and
run a preregistered paired closed-loop comparison. V22 and earlier studies stay
historical and read-only.

## Decomposition

The objective spans four independently reviewable subprojects. Each has its
own plan, TDD cycle, immutable evidence, commit, and AutoDL verification.

### Subproject 1: Source and license freeze

Fetch only the two exact commits, materialize only allowed OSM files plus
their root LICENSE and NOTICE state, and seal a manifest containing source
URL, commit, Git blob ID, file SHA256, retrieval time, and Apache-2.0
redistribution obligations. No simulator or map loader runs in this subproject.

### Subproject 2: Map compatibility adapter

Load the exact frozen source bytes without deleting or rewriting regulatory
relations. Run TDD, static review, and one Autoware-map smoke before any full
census. A load failure retains an exact receipt and never fabricates a route
or speed source.

### Subproject 3: Map-family, route, and split freeze

Build coordinate-normalized geometry, bbox, topology, speed-source, and
regulatory-source inventories. Deduplicate map copies and routes before
freezing train/calibration/holdout groups and seed namespaces. No outcome is
read before this freeze.

### Subproject 4: Corpus, training, paired evaluation, and closeout

Reuse the existing native runner and fixed K=8 decision path to generate new
train-only material, train the convex selector, calibrate only preregistered
thresholds/scales, open holdout once, independently review evidence, and emit
either a narrow supported claim or an honest no-claim.

## Frozen sources and licensing

Allowed public inputs are:

1. `https://github.com/autowarefoundation/autoware_universe.git` at
   `b8d441c59293e34289cd7bca1ba5e5a33e9189d9`, exact path
   `planning/behavior_path_planner/autoware_behavior_path_bidirectional_traffic_module/test_map/lanelet2_map.osm`.
2. `https://github.com/tier4/scenario_simulator_v2.git` at
   `e22f01093fa6516c0552549ada302270329c59a4`, every repository `*.osm`
   path found by the exact commit tree. These are the frozen Lanelet2
   test/sample-map inventory; path count and unique-byte count are evidence,
   not assumed independence.

INTERACTION, inD, rounD, exiD, CARLA, nuPlan, and nuScenes are forbidden for
v23 acquisition or execution. Existing historical references to those sources
remain untouched.

The source artifact retains the exact upstream LICENSE. It retains upstream
NOTICE when present and records an explicit absent-at-commit receipt when no
root NOTICE exists. Redistribution must provide the Apache-2.0 license, retain
applicable copyright/patent/trademark/attribution notices, preserve readable
NOTICE attribution when upstream supplies NOTICE, and mark any modified file
prominently. Apache-2.0 grants no general trademark permission. V23 source
OSM files are copied byte-for-byte and are never silently modified.

## Compatibility approaches

Recommended approach: official regulatory-element registration. Before the
DP builder imports or loads the map, use an already installed official
Autoware Lanelet2 extension when it registers `detection_area`. This has the
best semantic fidelity and the smallest CAMP change.

Fallback approach: thin process-local registration adapter. If the official
module is absent but the installed Lanelet2 binding exposes a supported
regulatory-element factory hook, register only the missing subtype while
retaining every relation, member, role, and tag from the original map. The
adapter is v23 opt-in and must prove the source file SHA is unchanged before
and after load.

Rejected approach: deleting unsupported regulatory elements is rejected.
`sanitize_lanelet2_map is forbidden for v23`; that older helper remains only
for historical workflows. Removing `detection_area`, removing its lanelet
references, changing subtype tags, or generating a sanitized OSM cannot pass
the v23 gate.

If neither official registration nor the supported thin adapter can load the
map, the reviewed exact failure is a real stop. V23 will not add a parser that
pretends the regulatory relation does not exist.

## Existing architecture reused

- `scripts/integrations/run_diffusion_planner_dp_camp_v21_native.py` remains
  the single native simulator runner/factory.
- `camp_core/camp_core/integrations/diffusion_planner.py` remains the shared
  projection and candidate-materialization boundary.
- V22 source-valid selection, retained failure rows, candidate immutability,
  candidate-0/default identity receipts, speed metrics, and statistics are
  reused where their contracts still apply.
- New v23 code is limited to source freezing, semantic map registration,
  map/route-family census and split materialization, v23 configuration, and
  v23-specific review/orchestration.
- DP code, configuration, weights, checkpoint, request semantics, and fixed
  candidate generation are never modified.

## Map-family and route data flow

For every frozen OSM path:

1. Verify the source SHA against the license manifest.
2. Parse the unmodified OSM and count nodes, ways, lanelets, regulatory
   elements by subtype, explicit speed sources, and missing sources.
3. Project coordinates with the existing no-ROS projection boundary.
4. Build a coordinate-normalized geometry fingerprint that ignores source
   path, ROS/no-ROS naming, and element IDs while retaining quantized geometry
   and direction.
5. Build a topology fingerprint from lanelet adjacency, connectivity,
   boundary sharing, direction, and regulatory attachment.
6. Group equal geometry/topology copies and configuration variants into the
   same map family. Fourteen paths or twelve unique OSM blobs never imply
   twelve independent map families.
7. Generate outcome-blind routes at the frozen `>=80m` threshold, deduplicate
   exact and corridor-overlapping routes, and then measure source-valid K=8
   capacity. The earlier 551 count is only a pre-deduplication upper bound.

Map-family identity, route-family identity, overlapping corridor, and seed
namespace are indivisible split boundaries. The same route and all of its
seeds stay in one split. No record-level random split is allowed.

If at least three independent map families exist, assign whole families
without leakage. Otherwise, do not invent map-level 60/20/20: group
train/calibration by indivisible route-family/corridor on training maps and
reserve the compatible, source-complete Autoware bidirectional map as the
independent unseen-map holdout. Claim wording reports the achieved support.

All outcome-blind preregistered routes remain in denominator, failure
accounting, and receipts. No route or seed is redrawn, replaced, retried, or
dropped because its outcome is poor.

## Candidate and selector contract

Each DP/CAMP arm uses the same route, seed, initial state, environment random
stream, request, configuration, checkpoint, and fixed K=8 candidate tensor.
CAMP only computes `score_k(w)=a_k^T w` and selects a source-valid row. It does
not generate, repair, rewrite, blend, or postprocess a trajectory.

Candidate 0 is called the operational DP default/Top-1 only after per-tick
byte/hash identity. Native K-ranking provenance remains false unless an
upstream receipt proves it. Weights are finite, nonnegative, and on the
approved simplex; the master remains convex.

## Atoms and training

The target schema is `dp_camp_v10_14d`. Before reading any label or outcome,
freeze the active atom mask from causal source availability, finiteness,
nonnegativity, and train-only nonzero variance. Record engineering meaning,
source, coverage, missing reason, scale, and train variance. Unavailable atoms
fail or receive an explicit frozen inactive receipt; they are never silently
zeroed.

Generate training material from the new maps and new native per-tick K=8
decision distribution. V18 and v22 weights are read-only named baselines, not
the final model. Optimize on train only. Calibration performs only the
preregistered threshold/scale choice. Holdout opens once.

Use the existing CLARABEL/simplex/CVaR/L2 convex master. Convergence means
exact/optimal solver status, the preregistered gap, and either no new cuts or
the frozen cut cap; solver iterations are not epochs. Run the 25/50/75/100%
train learning curve and freeze the final model at 100%. Record wall-clock,
cuts, iterations, gap, weights, and stability.

## Seeds and runtime preflight

Pre-register a source-only seed namespace. Primary size is five seeds per
route. Freeze ten only if an outcome-blind wall-clock/disk preflight proves the
full evaluation completes within 24 hours while maintaining at least 10 GiB
free. Otherwise freeze five. Performance cannot influence this choice. Pilot
may use only the first seed per route and cannot support a claim.

## Paired evaluation and statistics

Primary metrics are paired closed-loop SafetyCost and collision, near-miss,
offroad, red-light, speed violation, and wrong-way components. Speed uses
0.1 m/s as primary tolerance and reports 0/0.05/0.2 sensitivity. Secondary
metrics are route progress/completion, jerk, lateral acceleration,
candidate-0/non-0 selection, and all-K-high-risk strata.

Latency reports DP and CAMP total planning; DP default; and CAMP K8 candidate,
atom, selector, and tracker stages with mean, median, p95, p99, and max.
Statistics report better/tie/worse, mean/median paired delta, map/route-family
clustered CI95, and the full failure denominator. Repeated seeds are not
independent maps.

Only passed preregistered gates plus supporting CI permit a narrowly scoped
claim. Otherwise close as an honest no-claim. Real-world safety, broad
deployment, and broad CAMP-over-native-ranked-DP claims are prohibited.
Promotion, deployment, and online activation are out of scope.

## Error handling and stop rules

Every ordinary import, path, harness, or contract failure is attributed,
preserved, minimally fixed, and reverified. A new artifact never overwrites a
failed artifact. Stop only for unsafe three-endpoint/DP alignment, an existing
unique long task, license/source conflict, reviewed source-preserving adapter
impossibility, zero legal routes or paired support, failure to preserve the
10 GiB floor, a post-open holdout protocol defect, or a next step requiring
promotion/deployment/activation.

## Verification

Each gate runs the narrow pytest target, relevant regression tests,
`py_compile`, and `git diff --check` locally and on AutoDL. Evidence contains
HEADS, COMMAND, stdout, stderr, JSON, MD, SHA256SUMS, and ROOT_SHA256SUMS.
After each checkpoint commit/push and AutoDL ff-only sync, reread the v23 audit
EOF and current-status v23 tuple before continuing.

## Design self-review

- Placeholder scan: no TBD, TODO, or deferred contract remains.
- Consistency: exact source commits, fixed DP, source preservation, split
  boundaries, seeds, atoms, evaluation, evidence, and stop rules match the
  authorized v23 objective.
- Scope: four subprojects avoid one unreviewable all-in-one implementation.
- Reuse: existing native runner and shared v22 contracts remain the default;
  no second simulator path or speculative abstraction is introduced.
