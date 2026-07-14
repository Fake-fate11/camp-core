# V22 Native Route-family Safety Design

## Status, scope, and assumptions

This design implements the user-authorized v22 protocol in TiER IV Diffusion
Planner's native `scenario_generation` simulator. It reuses the v21 CAMP-side
hook and shared atom/selector/master code. V21 remains historical, read-only,
and an honest no-claim.

The two fixed logical maps may be reused across train, calibration, and
holdout. Independence is instead enforced at the outcome-blind
route-family/corridor group. Route identity, route family, and seed namespace
are strictly disjoint across splits. The claim scope is only paired
closed-loop safety improvement within the two fixed logical maps on unseen
route-family/corridor and seed. There is no unseen-map generalization claim.
A third independent map is a future external-validation extension and does
not block v22 training, the 30 routes x 3 pilot, or the 100 routes x 5 main
evaluation.

The source baseline for this design is the Gate 1 final synced CAMP HEAD
`a94ad0a50640a86583e9dcc74b33bd68a00c1382`. Fixed DP remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4` and tracked-clean. DP
modification is a hard stop.

## Fixed candidate and selector boundary

Every planning tick uses the fixed K=8 candidate tensor already constructed
by the v21 native hook. CAMP may only select an exact indexed candidate. It
may not generate, repair, rewrite, blend, smooth, or postprocess a trajectory.
Candidate 0 remains byte-identical to the separately computed DP operational
default. Each receipt stores `candidate_tensor_sha256_before` and
`candidate_tensor_sha256_after`; they must match, and the selected bytes must
hash to the selected candidate row.

The selector remains `score_k(w)=a_k^T w` on approved finite affine atoms,
with `w` on the nonnegative simplex. The existing convex robust-margin master
is reused. DP, checkpoint, request semantics, candidate construction, and the
native tracker are unchanged.

Map ID, route ID, and split identity are forbidden from CAMP atoms, features,
online input, DP input, and learned labels. They may appear only in offline
manifests, receipts, grouping, failure accounting, and clustered statistics.
An approved atom must have a real causal native source and preserve the
affine/convex boundary; a missing source is hard invalid and is never
synthesized.

## Outcome-blind route-family/corridor split

The split manifest is constructed and hashed before any CAMP or DP outcome.
It uses only fixed map bytes, Lanelet2 topology and geometry, authored or
deterministically enumerated route bytes, and frozen non-formal seed lists.
Record-level random split is forbidden.

For every route, the manifest records a route identity SHA over logical-map
SHA, ordered lanelet IDs, source geometry, and route serialization. Before
allocation, it builds an undirected leakage graph over route identities. Two
routes receive an edge when any source-only rule holds:

1. their route identity is equal;
2. they contain a shared lanelet or share a Lanelet2 boundary-line ID;
3. their source centerlines describe an overlapping corridor: after 1 m
   arc-length sampling, at least 20 m in each route is within 3 m with parallel
   or antiparallel heading difference at most 15 degrees;
4. they traverse the same topology family, defined as the same map-local
   connected intersection/traffic-light complex and ordered entry/exit arm
   pair. A complex contains branch lanelets or regulatory traffic-light
   lanelets plus their immediate predecessor and successor lanelets.

Connected components of this leakage graph are indivisible
route-family/corridor groups. Thus a shared lanelet, overlapping corridor, or
highly correlated topology family cannot cross splits, including through a
transitive chain. The implementation must emit the route pair and exact rule
for every graph edge, plus group membership and group SHA.

Groups are ordered by SHA256 and allocated whole, outcome-blind, while
balancing source-only map and stress descriptors. Stress descriptors are
limited to topology facts available before simulation: traffic-light
regulation, branch/intersection traversal, tight source corridor width, and
route length/progress opportunity. No model inference, candidate score,
SafetyCost, completion, or observed failure may influence allocation.

The manifest freezes disjoint `train`, `calibration`, and `holdout` group
sets. Pilot routes are a frozen calibration-only subset; main routes are a
frozen holdout-only subset. V21's two observed routes may be train,
calibration, or diagnostic records only and are forbidden from holdout. Seed
namespaces are disjoint by split and arm-paired within a route. Formal seeds
11/12/13 and Full36 are forbidden.

Before any simulator run, static validation must prove:

- no route identity, route-family/corridor group, or seed namespace appears
  in more than one split;
- no cross-split route pair has a leakage-graph edge;
- every pilot route belongs only to calibration and every main route only to
  holdout;
- no forbidden ID field enters an atom/feature schema;
- every preregistered route/seed pair has an expected DP arm, CAMP arm, and
  receipt key.

The deterministic source inventory currently has 915 route starts across the
two maps. The pilot target is at least 30 routes x 3 non-formal seeds = 90
paired runs; main is at least 100 routes x 5 non-formal seeds = 500 paired
runs. The route-family census may establish a lower leakage-safe ceiling. If
so, that true ceiling and every excluded pre-preregistration source route with
its source-only reason are frozen before execution; routes are not repeated,
redrawn, or outcome-selected to fabricate scale.

## Hard validity versus soft risk

The shared causal materializer exposes a `source_valid_mask`. Hard invalidity
is limited to:

- NaN/Inf, candidate shape, dtype, or 80-step time-grid error;
- missing real causal atom or metric source;
- incomplete candidate bytes, row hash, or tensor hash;
- objective inability of the tracker or simulator to execute.

Lane corridor overrun, predicted collision or low clearance, red-light
exposure, speed excess, low progress/stuck risk, and comfort risk are finite,
auditable atoms or severities. They never remove an otherwise source-valid
candidate. Canonical 14D atoms are reused where their native causal sources
exist. The old signal/lane/OBB physical screen remains a diagnostic risk mask,
not an eligibility mask.

When all K candidates are source-valid, CAMP scores all K and selects the
finite argmin even if every candidate fails that legacy risk screen. Such a
tick and its route are marked `all-K-high-risk/stress`. CAMP must not force
candidate 0, fail closed, or use fallback. If fewer than K are source-valid,
only source-valid candidates may be scored; the missing candidates and exact
hard-invalid reasons remain in the receipt. A post-selection tracker or
simulator execution failure is retained as an arm failure, never converted to
a different candidate.

Every preregistered route/seed pair remains in the evaluation set. There is no
deletion, replacement, redraw, or skip because of low progress, high cost,
all-K risk, lane overrun, speed, collision risk, or any observed outcome. A
hard-invalid route remains in the denominator with failure stage and reason.
Reports separately state route coverage, hard-invalid rate,
paired-complete rate, execution-failure rate, and all-K-high-risk rate. An arm
failure never deletes its pair.

## Native training and calibration

Train-route native causal decision snapshots are sampled every 0.5 s rather
than treating every 0.1 s tick as independent. Each snapshot includes the
immutable K tensor receipt, causal source receipt, complete finite atom
matrix, source-valid mask, offline supervision provenance, and group/split
receipt outside the feature payload.

The preregistered learning curve uses 5k/10k/20k/50k snapshots. If fewer are
available, all reachable levels are run and the ceiling is recorded. The v22
primary model is trained only from the v22 train split with the existing
convex solver. V18 frozen weights are an ablation baseline only. Reports use
solver status, iterations, gap, cuts, and offline wall-clock; they do not
invent epochs.

Train/calibration closed-loop outcomes may supply offline supervision,
pairwise ranking labels, or calibration targets. They never become selector
features, online input, or DP input. Calibration chooses atom scales, model
checkpoint among preregistered learning-curve levels, and diagnostics before
holdout. Holdout outcomes are never used for atom selection, training,
threshold selection, retries, or replacement; main holdout is opened once
after freeze.

The frozen train corpus has no K-way actual counterfactual closed-loop outcome:
one behavior-selected arm cannot label the seven unexecuted candidates. V22
therefore uses `v22_causal_soft_risk_surrogate_v1`, not an actual-outcome
label. For train snapshot `n` and candidate `k`, it freezes
`cost_nk = 100 * physical_risk_nk + sum_r(q_r * clip(a_nkr / s_r, 0, 10))`.
The physical-risk term is a finite additive cost and never an eligibility veto;
when all K are high risk its common penalty cancels and the relative minimum
continuous severity wins. `source_valid_mask` is the only oracle eligibility
mask. Scales `s_r` are train-only 95th percentiles with a `1e-6` floor. The
fixed `q` vector is recorded in the training config and maps existing native
SafetyCost/secondary priorities onto the canonical 14D atoms without adding a
new source. Identity and future/outcome fields are forbidden. Atoms without
positive cross-candidate train support remain in the 14D schema but are marked
unsupported and receive zero learned weight. This surrogate is only offline
supervision; final evidence still comes from paired native closed-loop
SafetyCost.

Speed calibration reports raw strict overspeed, operational events at
0/0.05/0.1/0.2 m/s tolerances, and continuous excess magnitude-duration.
The primary operational tolerance is frozen at 0.1 m/s regardless of holdout;
strict remains a transparent sensitivity result.

## Paired evaluation and metrics

Each pair uses one preregistered route and scenario seed. DP and CAMP arms use
fresh native runs with identical fixed map/route bytes, initial state,
SpawnConfig, NPC/traffic-light seed schedule, fixed DP/checkpoint/request, and
native MPC tracker. CAMP's local candidate RNG remains isolated. Natural
closed-loop divergence after a different selected action is expected.

Primary `SafetyCost Native v22` is lower-is-better:

```text
100 * collision_any
+ 10 * near_miss_noncollision_rate
+ 20 * offroad_rate
+ 20 * wrong_way_rate
+ 30 * red_light_violation_any
+ 10 * operational_speed_violation_rate_at_0.1_mps
```

Raw strict speed violations and continuous speed-excess magnitude-duration
are reported beside the primary cost. Collision, near miss/diagnostic TTC,
offroad/drivable-area, wrong-way, red-light, and speed components retain raw
counts, denominators, severities, and event ticks. Results are reported
overall and for normal, stress, and all-K-high-risk strata.

Secondary metrics include route progress/completion/stuck, distance traveled,
comfort, candidate-0 and non-candidate-0 selection rates, termination reason,
and DP default/K8 inference, atom, affine selector, tracker, and total latency.
ADE/FDE/miss are omitted unless a symmetric, real, future-leakage-free target
is defined before holdout.

Statistics include every planned pair row, better/tie/worse at tolerance
`1e-12`, mean and median CAMP-minus-DP delta, and a frozen bootstrap seed for
95% cluster intervals over logical map, route-family/corridor group, route,
and scenario seed. Receipts and failure rows remain addressable by every
cluster key.

## Claim and no-go contract

A narrow within-two-fixed-maps claim is allowed only when all conditions pass:

- overall mean CAMP-minus-DP SafetyCost is strictly below zero;
- the cluster-bootstrap CI95 upper bound is strictly below zero;
- better pairs outnumber worse pairs;
- CAMP causes zero additional collision or red-light event pairs;
- offroad-rate and wrong-way-rate mean deltas are nonpositive and their CI95
  upper bounds are no greater than `0.005` absolute rate;
- planned holdout coverage and all failure accounting are complete;
- independent review, HEAD/SHA chain, candidate-0 identity, candidate
  immutability, split zero-overlap, and forbidden-feature checks all pass.

If any condition fails, v22 closes with an honest no-claim. Thresholds,
tolerance, routes, seeds, groups, and failure policy may not change after
holdout results. Even a passing result supports only unseen
route-family/corridor and seed performance within the two fixed logical maps,
not deployment, real-road safety, broad CAMP>DP superiority, or unseen-map
generalization.

## Gate order and evidence

Implementation follows the existing runner and these gates: shared-boundary
TDD; single-tick and tiny multi-route capability; source-only census/split and
preregistration; native train/calibration corpus; 5k/10k/20k/50k convex
learning curve and freeze; 90-pair calibration pilot; independent pilot
review; one-shot 500-pair main holdout; independent result review and
claim/no-claim closeout.

Every gate preserves HEADS, COMMAND, stdout, stderr, summary JSON/Markdown,
`SHA256SUMS`, and `ROOT_SHA256SUMS`. Candidate and receipt hashes are retained
per tick and route/seed. A failed sealed gate is not overwritten, and a
successful audited gate is not repeated.

## Self-review

The design changes only the user-authorized split interpretation: logical map
reuse is allowed, while route identity, route-family/corridor group, and seed
namespace stay disjoint. The grouping rules use source map/route geometry and
topology only, group correlated routes transitively, and run before outcomes.
The selected implementation remains the v21 native hook plus the existing
shared materializer, selector, and convex master; there is no parallel runner.
The all-K-high-risk case changes eligibility, not trajectory bytes or the
affine score. Every preregistered failure remains visible. The claim is
explicitly narrower than unseen-map generalization.
