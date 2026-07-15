# V24 Independent Lanelet2 Source Control Design

## Goal

Run a new v24 study on unchanged TIER IV Diffusion Planner commit
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Correct v23's control error by
qualifying and advancing the Autoware and TIER IV Lanelet2 sources
independently. Prefer an official source-preserving Autoware extension chain,
but complete the TIER IV map census, route generation, training, and paired
closed-loop evaluation regardless of Branch A's result.

V23 and earlier audits, evidence, routes, outcomes, models, and decisions stay
historical and read-only. V23's honest no-claim is a dependency-capability
diagnosis, not evidence that CAMP or the fixed DP failed a performance test.

## Root cause and alternatives

The v23 runtime adapter gate correctly treated stock maps and maps with
Autoware-only regulatory subtypes differently. The global control contract was
wrong: its stop rules promoted one reviewed Autoware adapter failure to a
study-wide stop before the 14 TIER IV paths were censused. The v23 audit then
claimed that every remaining route required a semantic change despite having
performed no map-family, route, or K=8 source-support census.

Three designs were considered:

1. Add a generic runtime state machine. This would be testable but would add a
   new controller entry point that the repository does not currently use.
2. Use independent source receipts plus a machine-checked audit EOF contract.
   This matches the existing evidence-driven workflow and changes the minimum
   surface.
3. Copy the native runner into one runner per source. This isolates imports but
   duplicates the fixed candidate path and increases drift risk.

V24 chooses option 2. No new runtime controller abstraction is introduced;
gate-specific scripts may be added only when a gate needs new deterministic
materialization or review logic. Existing fixed-DP native runner, selector,
training, and reviewer paths remain the default.

## Source-independent control contract

Every v24 EOF carries machine-readable fields for both sources:

- `source_a_status` and `source_b_status`;
- `source_a_terminal` and `source_b_terminal`;
- `authorized_source_count` and `source_terminal_count`;
- `global_stop_authorized` and `global_stop_reason`;
- the current artifact, root SHA256, CAMP source HEAD, fixed DP HEAD, and exact
  `next_work_target`.

Source-local terminal states never imply a global stop. Branch A failure cannot close Branch B.
A source can become ineligible after a sealed source, license,
semantic, build, or source-support receipt; the other source continues from its
own last passed gate.

The zero-support stop is legal only after all authorized sources finish per-source map, route, and K=8 paired-support accounting
and every source has zero legal support. Other global stops are restricted to unsafe three-endpoint
alignment, fixed-DP drift, an already running unique long task, inability to
preserve the 10 GiB disk floor, a required change to DP/map semantics/candidate
tensor/convexity, a post-open holdout protocol defect, or a next step requiring
promotion, deployment, or online activation.

Ordinary import, path, harness, artifact-layout, and single-map failures are
attributed, minimally fixed, or sealed as source-local exclusions. They are not
global stops. Failed artifacts remain immutable and a corrected artifact gets
a new path and root.

## Frozen sources

### Branch A: Autoware source-preserving extension

- Map repository: `https://github.com/autowarefoundation/autoware_universe.git`.
- Map commit: `b8d441c59293e34289cd7bca1ba5e5a33e9189d9`.
- Map path:
  `planning/behavior_path_planner/autoware_behavior_path_bidirectional_traffic_module/test_map/lanelet2_map.osm`.
- Frozen map SHA256:
  `cda848e3d440aaf48e532f8ab33afdff0bf8b8f1a45abd3d7724637a287ed660`.
- Dependency repository only:
  `https://github.com/autowarefoundation/autoware_lanelet2_extension`.

The dependency must be official Apache-2.0 source. Its commit is selected
before build results from Autoware Universe dependency metadata, publication
date, and Lanelet2 1.2.2 ABI compatibility. The freeze records repository URL,
commit, tree/file SHA values, LICENSE/NOTICE state, dependency graph, compiler,
and ABI. Forks, gists, handwritten `detection_area` substitutes, relation
deletion, subtype rewriting, and map sanitization are forbidden.

Source, build, and install are isolated under
`/root/autodl-tmp/camp_v24_autoware_lanelet2_extension`. No system Python,
global Lanelet2, DP repository, checkpoint, or source OSM changes are allowed.
If success requires a system-level install or Lanelet2/ROS upgrade, Branch A
fails closed without changing the machine globally.

Branch A success requires evidence that the loaded shared library/module is
from the frozen official source, matches the existing Lanelet2 1.2.2 ABI,
registers `detection_area` process-locally, preserves all 15 regulatory
relations and all 9 lanelet references, leaves the original OSM SHA unchanged,
leaves a stock TIER IV builder result unchanged before/after extension load,
and leaves DP code/configuration/weights/checkpoint/request unchanged.

### Branch B: TIER IV scenario_simulator_v2

- Repository: `https://github.com/tier4/scenario_simulator_v2.git`.
- Commit: `e22f01093fa6516c0552549ada302270329c59a4`.
- Frozen inventory: 14 paths and 12 unique OSM byte blobs before map-family
  deduplication.

Branch B does not depend on Branch A qualification, build, or smoke success.
Every path receives a license/source SHA receipt, XML validity result,
regulatory subtype census, bbox, coordinate-normalized geometry fingerprint,
lanelet topology, speed source, traffic-control source, and stock fixed-builder
smoke. An unsupported element, projection defect, or missing source excludes
only that map and keeps its failure receipt. No relation is removed, no subtype
is changed, and filename/configuration copies do not count as independent maps.

## Map families, routes, and split

Path count and unique byte count are not map-family count. Equal geography,
normalized geometry, topology copies, ROS/no-ROS copies, and configuration
variants belong to one family.

For every loadable map, generate an outcome-blind deduplicated route census at
the frozen `>=80m` threshold. Freeze the threshold before any outcome. Then run
single-record and K=8 source-valid probes with candidate tensors produced by
the fixed DP. All preregistered routes remain in denominator, receipts, and
failure accounting. Poor routes, poor outcomes, or all-K-high-risk routes are
never redrawn, replaced, or dropped.

Map-family, route-family, overlapping corridor, route, and seed namespace never
cross splits. Split whole map families when at least three exist. With two
families, reserve one as unseen-map holdout and split the other by indivisible
route-family/corridor groups for train and calibration. With one family, split
by those groups across train/calibration/holdout and prohibit an unseen-map
claim. Approximate 70/10/20 by indivisible cluster count, preferring train over
record-level leakage.

## Seeds and corpus

All seeds for one route stay in one split. DP and CAMP arms share route, seed,
initial state, environment random stream, request, configuration, checkpoint,
and exact fixed K=8 tensor. The seed namespace is frozen before outcomes.

Primary size is five seeds per route. Ten may be frozen only before first
holdout when an outcome-independent benchmark proves full execution within 24
hours while always retaining more than 10 GiB free. Pilot uses only the first
seed per route and cannot tune weights or support a claim.

Training corpus contains causal per-tick K=8 snapshots for every train route
and frozen seed. Any storage thinning uses one preregistered fixed time grid for
all routes before labels or outcomes are read.

## CAMP and fixed-DP boundary

CAMP may only rerank/select one row from the fixed DP K=8 candidate tensor each
tick. It may not generate, repair, rewrite, blend, or postprocess trajectories.
DP code, configuration, weights, checkpoint, and request semantics are frozen.

Candidate 0 is the operational DP default/Top-1 only after per-tick byte/hash
identity. No native K-ranking provenance is inferred. Selector score remains
`score_k(w)=a_k^T w`; weights are finite, nonnegative, and on the approved
simplex; the simplex/CVaR/L2 master stays convex. Future labels, closed-loop
outcomes, map/route/split IDs, and holdout information cannot enter training or
online selection.

## Atoms and training

The target schema is `dp_camp_v10_14d`. Before outcomes or holdout, audit each
atom's causal source, engineering meaning, units, coverage, finiteness,
nonnegativity, scale, and train-only variance. Freeze active atoms only from
source availability and train-only non-constant variance. Unavailable atoms
get explicit inactive receipts; calibration and holdout cannot select atoms.

V18 and v22 weights are read-only baselines. V24 retrains on the new native
per-tick K=8 distribution. Optimization uses train only. Calibration performs
only preregistered scale/threshold calibration. Holdout opens once.

CLARABEL/master convergence requires exact/optimal status, the preregistered
gap, and no new cuts or the frozen fail-closed cap. Iterations are not epochs.
Run 25/50/75/100 percent train learning curves and freeze the full-train model
before holdout. Record corpus time, training wall-clock, iterations, cuts, gap,
weights, and atom stability.

## Paired closed-loop evaluation

Primary metrics are paired SafetyCost total delta, collision, near-miss,
offroad, red-light, speed violation, and wrong-way. Primary speed tolerance is
0.1 m/s with 0, 0.05, and 0.2 m/s sensitivities. Secondary metrics include
route progress/completion, jerk, lateral acceleration, better/tie/worse,
candidate-0/non-0 selection, all-K-high-risk stratum, coverage, and source and
execution failures.

Latency reports DP default/tracker/total and CAMP default/K8 candidate/atom/
selector/tracker/total with mean, median, p95, p99, and max. Statistics report
paired mean/median delta and map-family/route-family clustered CI95. Seeds are
not treated as independent maps. An independent reviewer rehashes sources and
recomputes every metric.

A narrow safety-improvement claim requires all preregistered coverage and
execution gates, negative mean SafetyCost delta, clustered CI95 upper below
zero, better greater than worse, no unacceptable collision/offroad/red-light/
wrong-way regression, and passed candidate immutability, candidate-0 identity,
zero-overlap, and holdout-once checks. Otherwise v24 closes with an honest
no-claim. Real-world safety, deployment, broad unseen-map, and broad
CAMP-over-native-ranked-DP claims are forbidden.

## Gate decomposition

1. Startup reconciliation and v23 boundary review.
2. Official extension source qualification/freeze.
3. Branch A design, TDD, static review, isolated build, preflight, smoke, and
   independent review.
4. Branch B raw census and builder smoke, independent of Branch A status.
5. Merged map-family census, route census, K=8 source probe, and split freeze.
6. Corpus planning/materialization and atom availability freeze.
7. Training planning/execution/review and learning curve.
8. Paired-evaluation planning, static preflight, pilot/review, one-shot main,
   and independent review.
9. Evidence package, claim decision, and closeout.

Each subproject gets a focused plan before implementation. Successful gates
are not rerun. A running unique long task is observed, not duplicated.

## Evidence and verification

Every gate artifact contains HEADS, COMMAND, stdout, stderr, JSON, markdown,
`SHA256SUMS`, and `ROOT_SHA256SUMS`. Each gate runs local `py_compile`, focused
pytest, v24 audit tests, and `git diff --check`; repeats the relevant check on
AutoDL; updates the v24 audit and current-status pointer; commits and pushes a
small checkpoint; ff-only synchronizes AutoDL; and rereads live v24 EOF before
continuing.

AutoDL access uses credentials only from local secure storage, Paramiko with
the existing known-host key and `RejectPolicy`, and never emits a password.
Remote git/network commands source `/etc/network_turbo` first.

## Design self-review

- Placeholder scan: no placeholder marker or deferred contract remains.
- Root cause: the design distinguishes the correct source-local adapter failure
  from the incorrect v23 global stop.
- Scope: existing native fixed-DP execution paths are reused; only source and
  gate-specific evidence logic is added when needed.
- Consistency: sources, fixed DP, preservation, split, seeds, atoms, training,
  evaluation, claim gates, and stop rules match the authorized v24 objective.
- Safety: no source sanitization, DP mutation, trajectory mutation, holdout
  reopening, promotion, deployment, or online activation is authorized.
