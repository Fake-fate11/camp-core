# V25 Evaluation v2 Migration Matrix

Status: additive exploratory migration. The sealed legacy benchmark v1 values,
preregistration, denominator, evaluator artifacts, independent reviews,
continuation ledger, and final claim are immutable.

Evaluation v2 does not produce a weighted total. It exposes a vector of
separately denominated endpoints. Every v2 value is
`exploratory_posthoc_not_claim_authorizing`; no v2 endpoint inherits the
legacy multiplicity or NI gates.

| Legacy benchmark v1 field | Evaluation v2 endpoint | Migration rule | v2 evidence boundary |
|---|---|---|---|
| `collision_any` from legacy clearance overlap | `collision` | Reconstruct full ego and actor OBB polygons at every tick; count any, false-to-true episodes, and duration. | Physical severity, delta-v, and qualified contact dynamics remain `evidence_missing`. |
| `noncollision_obb_clearance_le_2m_tick_rate` (legacy near-miss alias) | `dynamic_proximity` | Report full-polygon clearance, relative closing speed, continuous-SAT TTC, and DRAC as separate descriptive fields. | PET requires conflict-zone identity and both passage times. A stationary 1.9 m exposure is not automatically dynamic risk. |
| `five_point_drivable_coverage_failure_tick_rate` | `road_containment` | Use full footprint area outside the union of root-bound drivable lanelet polygons. | Five points are never substituted for polygon containment. Missing root-bound polygons cancel the endpoint. |
| `certified_red_phase_stopline_crossing_gt_0_5mps_any` | `certified_red_crossing` | Preserve same-tick certified phase and exact route stop-line, then use the swept full front edge and report unthresholded crossing separately from the legacy `>0.5 m/s` field. | Ambiguous within-tick geometry maps to `evidence_missing`; future phase is never consumed. |
| `onroad_speed_excess_gt_0_1mps_tick_rate` | `speed` | Retain the 0.1 m/s project tolerance and add strict plus 0/0.05/0.1/0.2 m/s duration and magnitude-duration sensitivity from same-tick map limits. | These are controlled-benchmark measures, not legal or type-approval thresholds. |
| Final global-nearest route projection and clipped fraction | `route` | Use an ordered, stateful route projection with same/adjacent transitions and a frozen trapezoidal tick travel bound; report final, net, max-forward, backtracking, traveled distance, and completion. | No unique feasible path yields `ambiguous_evidence_missing`; no stateless nearest fallback is allowed. |
| Raw scalar-speed second-difference, speed-times-heading-rate, and same-tick speed-drop diagnostics | `vehicle_body_planar_kinematic_proxy` | Derive planar body-frame acceleration from positions and headings: 64 positions -> 63 velocities -> 62 accelerations -> 52 valid filtered samples; derive 51 filtered-jerk samples. | This is not seat/occupant response and does not assess ISO 2631 or SAE J2834 conformity. |
| Controlled stage timing summaries | `latency` | Preserve per-run/per-stage empirical mean, median, p95, p99, max and report total-latency exceedance rates for 50/100/200/500/1000 ms. | Warm-up, concurrent load, deadline scheduling, and production certification remain missing. |
| Legacy SafetyCost weighted composite | none | Preserve byte-for-byte under `immutable_legacy_benchmark_v1`; do not translate or recompute it as a v2 endpoint. | SafetyCost decrease is not a v2 pass or an industrial safety claim. |
| Legacy component and performance/comfort NI gates | none | Preserve their historical decision only. | `v2_scientific_hard_gate=not_prospectively_defined_for_v2`; future confirmatory use requires a new prospective protocol. |

## Denominator and inference migration

- Each endpoint is summarized per complete 64-tick run before pairing.
- The paired unit is one of the frozen 500 candidate0/Static14D/Scene14D
  triplets.
- Inference uses 100 independent equal-mass corridor/intersection clusters,
  each containing five paired units, with Student-t CI and B/T/W accounting.
- Ticks, seeds, and arms are not treated as independent observations.
- If an endpoint is missing for any required arm, v2 reports the full missing
  denominator and cancels paired inference. Complete-case shrinkage is
  forbidden.

## Claim migration

The legacy decision remains
`honest_no_claim_under_frozen_preregistered_all_gate`. Evaluation v2 cannot
retroactively authorize Fresh benefit, real-road safety, broad unseen-map,
native-ranked Top1, industrial comfort/conformity, promotion, deployment,
online activation, or production-readiness claims.
