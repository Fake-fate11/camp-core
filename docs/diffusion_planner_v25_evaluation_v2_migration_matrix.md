# V25 Evaluation v2 Corrected Migration Matrix

The legacy benchmark v1 values and frozen claim remain immutable. The earlier
v2 roots `2a3c39...`, `a15edb...`, `0cd17b...`, and `d1cfb2...` are preserved
as superseded diagnostics; this correction is additive and read-only.

| Legacy or superseded field | Corrected v2 treatment | Boundary |
|---|---|---|
| Legacy SafetyCost and preregistered NI | Preserved verbatim as immutable benchmark v1 | Not a v2 or industrial score |
| B/T/W mislabeled as variance decomposition | 500-pair `better_tie_worse`, frozen direction, exact-zero ties; variance retained separately | Directionless scalars are `descriptive_unclassified` |
| OBB overlap/clearance aliases | Full OBB collision plus polygon clearance, closing, DRAC, and continuous SAT TTC | Severity and PET remain missing |
| Infinite-horizon/unqualified SAT | Requires centroid approach and entry within frozen 5.0 s descriptive horizon | Ego velocity is speed-times-heading kinematic reconstruction |
| Five-point road proxy | Full footprint outside root-bound drivable polygon union | Signed union-boundary clearance/penetration explicitly missing |
| Red zero-area sweep treated as missing | Disjoint stationary edge is computed false; coincident/tangent/multiple crossing is ambiguous | Stop-line encounter deduplicated across phase interruption |
| Speed tolerance proxy | Same-tick excess and duration/magnitude-duration grid | Project benchmark only |
| Forward-only route state | Same/forward/backward adjacent transitions with sealed displacement/trapezoidal bound | Non-adjacent jumps rejected; ambiguous path remains missing |
| Absolute route completion | `clip((max(s)-s0)/route_length,0,1)` | No stateless-nearest fallback |
| Goal coupled to route availability | Independent same-tick goal distance/reached/passed endpoint | No historical-minimum/later-heading combination |
| Raw scalar-speed comfort diagnostics | Planar body kinematic proxy: 64->63->62->52 acceleration, 51 jerk | Not seat/occupant/ISO/SAE evidence |
| Stage timing | Per-run stage distribution and project deadline grid | Not production real-time certification |

Inference always summarizes each run before forming 500 method-candidate0
pairs. One hundred equal-mass corridor/intersection clusters then support
Student-t CI. Missing arms cancel paired inference; complete-case denominator
shrinkage is prohibited.

The corrected v2 materialization is
`exploratory_posthoc_not_claim_authorizing`. It cannot reuse the legacy
multiplicity or NI gate and cannot change
`honest_no_claim_under_frozen_preregistered_all_gate`.
