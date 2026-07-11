# V18 Bounded Offline Safety Score Design

## Scope

Add one independent, read-only safety evaluation for CAMP selection versus the
fixed-DP deterministic/MAP baseline. The evaluator consumes only the frozen
v18 canonical candidate records and the immutable paired-evaluation selected
indices. It does not query expert labels, call either model, mutate candidate
tensors, retrain CAMP, or modify Diffusion Planner.

The metric is named `camp_dp_bounded_offline_safety_score_v1`. It is not the
official nuPlan closed-loop scenario score. Its collision evidence is limited
to the frozen 32 dynamic plus 5 static observable objects, and its lane check
is the existing route-corridor check rather than full drivable-area coverage.

## Alternatives

1. **Bounded offline score (selected):** reuse frozen causal geometry and
   candidate trajectories. This is available now and preserves the fixed-DP
   boundary.
2. **Official nuPlan closed-loop score:** defer until a nuPlan simulator,
   reactive-agent policy, full scene state, and official metric engine are in
   scope.
3. **CAMP weighted atom score:** rejected because using learned selector
   weights for evaluation would be circular.

## Candidate-Level Score

All constants are fixed before the mini result is calculated.

Hard multipliers:

- `collision_free`: frozen `obb_collision_free_mask`.
- `lane_compliant`: frozen `lane_feasible_mask`.
- `red_light_compliant`: `planned_red_light_cost <= 1e-12`.
- `making_progress`: `progress_ratio >= 0.2`.

Soft components, each in `[0, 1]`:

- `clearance_score = clip(minimum_obb_clearance_m / 3.0, 0, 1)`.
  This is a predicted-horizon OBB-clearance proxy, not TTC.
- `speed_score = clip(1 - rms_overspeed_mps / 2.23, 0, 1)`, where
  `rms_overspeed_mps = sqrt(speed_limit_margin_0_0 / 7.9)` from the frozen
  14D atom. The squared-integral source makes this an RMS proxy rather than
  the official linear overspeed integral.
- `progress_score = clip(max(route_progress, 0.1) /
  max(progress_reference, 0.1), 0, 1)`.
- `comfort_score` is one only when the candidate trajectory satisfies every
  available official nuPlan comfort bound: longitudinal acceleration in
  `[-4.05, 2.40] m/s^2`, absolute lateral acceleration at most `4.89 m/s^2`,
  absolute yaw acceleration at most `1.93 rad/s^2`, absolute yaw rate at most
  `0.95 rad/s`, absolute longitudinal jerk at most `4.13 m/s^3`, and jerk
  magnitude at most `8.37 m/s^3`.

The aggregate uses the supported nuPlan soft-metric weights and renormalizes
after omitting unavailable driving-direction and true TTC metrics:

```text
soft = (5*clearance + 4*speed + 5*progress + 2*comfort) / 16
score = 100 * collision_free * lane_compliant * red_light_compliant
            * making_progress * soft
```

The official structure and thresholds are documented at:

- https://github.com/motional/nuplan-devkit/blob/master/docs/metrics_description.md
- https://nuplan-devkit.readthedocs.io/_/downloads/en/latest/pdf/

## Outputs

For both CAMP and baseline, persist:

- mean bounded offline safety score;
- collision-free, lane-compliant, red-compliant, progress-pass, comfort-pass,
  and physical-feasibility rates;
- mean minimum OBB clearance, speed score, progress ratio, and frozen
  red-stopping-margin cost;
- paired score better/tie/worse counts and mean CAMP-minus-baseline delta;
- log- and scene-cluster 95% bootstrap intervals for the score delta;
- immutable source roots, method indices, metric constants, and all exclusions.

Per-record output contains only identities, selected/baseline indices, derived
components, and scores. It contains no expert labels or learned-weight-derived
evaluation value.

## Mini Interpretation

The completed 71-row mini holdout may be scored once from the immutable paired
output without reopening labels. Because this metric was added after the mini
paired evaluation, the result is descriptive smoke evidence only. It cannot
support a performance, safety, promotion, deployment, or CAMP-over-DP claim.

## Causal 10k Preregistration

The same schema, constants, formula, tie tolerance, bootstrap seed, and
exclusion policy must be frozen before causal-10k training or holdout access.
No metric tuning is allowed after calibration or holdout results are visible.

A future bounded-offline improvement statement requires all of:

- log- and scene-cluster CI95 lower bounds for CAMP-minus-baseline score are
  greater than zero;
- paired `better > worse`;
- CAMP has no higher collision, lane, red-light, or progress-failure count;
- candidate tensors, fixed DP, splits, and the affine/simplex/convex CAMP
  contracts remain unchanged.

Even if these pass, wording remains limited to improvement in
`camp_dp_bounded_offline_safety_score_v1`; closed-loop or real-world safety is
not established.

## Failure Handling

Missing masks, component arrays, source hashes, selected indices, or finite
candidate values fail closed. Existing output or staging directories block a
rerun. The evaluator never substitutes constants for unavailable evidence and
never forces baseline candidate 0 to be feasible.

## Verification

- Unit tests cover formula constants, comfort thresholds, hard-zero behavior,
  learned-weight independence, hash checks, no-label execution, and paired
  aggregation.
- Local and AutoDL run `py_compile`, targeted pytest, v18 audit/status tests,
  artifact SHA verification, and `git diff --check`.
- The mini result receives a separate read-only result review before docs EOF
  advances to the causal-10k decision boundary.
