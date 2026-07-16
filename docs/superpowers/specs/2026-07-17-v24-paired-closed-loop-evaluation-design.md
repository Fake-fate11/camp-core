# V24 Paired Closed-Loop Evaluation Design

Status: outcome-blind protocol freeze and static-preflight design. No simulator,
candidate generation, calibration outcome, holdout outcome, or claim is opened
by this document.

## Frozen population

The corrected source-only v24 split and route census are the only route
authorities. The calibration population contains two routes and five frozen
seeds in `map_family_f62e06cd1303`; the holdout population contains 24 routes
and five frozen seeds in `map_family_828a913c2f9a`. Capability is one
calibration route at seed `24101` for one tick. Consistent with the frozen
pilot rule, pilot is both calibration routes at their first seed `24101` for
64 ticks, exactly two pairs; the other eight calibration route-seeds are not
opened. Main is every holdout route at seeds `24201` through `24205` for 64
ticks, exactly 120 pairs. A route/seed is never replaced or resampled because
of execution status or outcome.

The pilot is an execution-capability gate only. It cannot tune weights, choose
atoms, recompute scales, select thresholds, select routes, select seeds, or
authorize a performance claim. The full-train 14-atom model is the only model.
Main opens the frozen holdout exactly once after pilot review; no main receipt
may be retried or substituted based on its result.

## Arm symmetry and candidate boundary

Both arms use the same route asset, initial-state construction, scenario seed,
external random schedule, fixed DP request/config/checkpoint, and maximum
steps. Each arm is independently reset to that same initial state. The DP arm
generates fixed-DP K=8 on its own realized state and selects candidate 0 as the
operational default; this is not called native-ranked Top-1. The CAMP arm
generates fixed-DP K=8 on its own realized state and may only select an exact
row using the frozen 14D affine/simplex weights. Every tick in both arms must
prove before/after tensor hash equality, candidate-0/default byte identity,
and exact selected-row identity. CAMP additionally proves unchanged NPC
outputs and no global RNG mutation during candidate work.

At `t=0`, identical causal inputs and candidate seeds require cross-arm input,
candidate-tensor, and candidate-row hashes to match. Once the policies select
different trajectories, their closed-loop states may diverge. Later K=8 tensors
are correctly state-conditioned fixed-DP outputs and are expected to be
non-comparable across arms. They must not be made equal by wrong-state replay or
trajectory transformation, and their expected non-comparability does not close
a policy-level closed-loop claim.

Arm execution order is not fixed to DP-then-CAMP. Within each mode, pair keys
are ranked by SHA256 with domain `camp-v24-paired-arm-order-v1`; the lower half
uses AB (`dp`, `camp`) and the upper half BA (`camp`, `dp`). Pilot is exactly
`1/1` and main exactly `60/60`. Both arms still start from independent resets.
Latency remains descriptive and is not a claim gate because K=8 audit
instrumentation and device cache state are not identical operational workloads.

## Outcomes and statistics

Primary SafetyCost is the frozen affine sum: collision `100`, near miss `10`,
offroad `20`, wrong-way `20`, red-light `30`, and speed violation `10`.
Operational speed tolerance is `0.1 m/s`; `0`, `0.05`, `0.1`, and `0.2 m/s`
are all reported. Secondary outcomes are route progress/completion, jerk,
lateral acceleration, better/tie/worse, candidate-0/nonzero selection,
all-K-high-risk stratum, source/execution failures, and retained coverage.

Every paired mean and median delta is reported. The 120-pair holdout contains
one map family and three corridor groups, so map-family bootstrap is forbidden
(`n=1`). Primary CI95 uses a frozen hierarchical bootstrap over indivisible
corridor/route-family group, route identity, then seed, with 5,000 resamples
and seed `24047`; seeds are never counted as independent maps.
Latency reports count, mean, median, p95, p99, and maximum for DP
default/tracker/total and CAMP default/K8-candidate/atom/selector/tracker/total.

A limited claim would require all 120 planned rows retained and paired-complete,
zero source-invalid and execution-invalid pairs, SafetyCost mean delta below
zero, clustered CI95 upper below zero, better more frequent than worse, zero
additional collision/offroad/red-light/wrong-way pairs, per-arm candidate
immutability, per-arm candidate-0/default identity, t=0 cross-arm identity,
zero split overlap, holdout-once, and independent SHA review. Any failed arm
retains the pair and both arm receipts; no imputation, replacement, or redraw is
allowed. Claim scope is at most the frozen held-out map family and its three
corridor groups. Reality-safety, deployment, broad unseen-map, map-family-level
generalization, and CAMP-over-native-ranking claims are forbidden.

The training source-coverage risk is disclosed before outcomes: 1,875 frozen
train route-seeds yielded 1,054 complete and 821 failed receipts, a failure rate
of `0.4378666666666667`. This does not remove routes from any denominator.

## Learning-curve stability and concentration risk

At 25/50/75/100% train data, weight L1 distance to the full model is
`0.3998769536 / 0.1897176421 / 0.2061194201 / 0`. Effective support above
`1e-6` is `3 / 3 / 3 / 3`. Candidate-0 selection rates are
`0.2021909418 / 0.2786534179 / 0.2586302018 / 0.2702224320`; normalized
selected-index histogram L1 distance to full is
`0.1360629805 / 0.0197657608 / 0.0231844605 / 0`, and candidate 0 is the most
frequent selected index at every level. The full model places effective weight
`0.4178605235 / 0.5784894895 / 0.0036499870` on lane deviation, clearance, and
DP-prior jerk excess. This concentration is not an automatic failure, but is a
required distribution-risk disclosure and cannot be repaired from calibration
or holdout outcomes.

## Static preflight

Static preflight verifies every upstream artifact root and source file SHA,
fixed DP HEAD and tracked cleanliness, the exact 401-route split join, the
2/24 calibration/holdout route counts, frozen seed namespaces, source map bytes,
and the 14-atom model bytes plus all four learning-curve stability receipts. It
creates only source-preserving Route assets and
runtime serialization adapters: the exact f64le weights become a `.npy` array,
and the exact model scales become a schema-tagged JSON file. Numeric equality
and both source/output SHAs are sealed. It assigns the frozen AB/BA order and
validates 123 disabled run configs
but does not build the runner, load the DP model, execute a simulator, generate
candidates, read outcomes, open holdout, or authorize pilot/main execution.
