# V25 Evaluation v2 Corrected Read-Only Report

Status: independently reviewed exploratory post-hoc evidence; not claim-authorizing.

## 1. Decision

Evaluation v2 was corrected and materialized once, read-only, from the existing
sealed Fresh B4 denominator: 500 paired units, 1,500 complete arms, 64 ticks per
arm, and 96,000 ticks. No Fresh arm, DP/K8, corrected evaluation, or legacy
review was rerun. No scientific or continuation CAS was written.

The corrected v2 package remains
`exploratory_posthoc_not_claim_authorizing`. It has no weighted total and no
prospectively defined scientific hard gate. The immutable legacy decision is
still `honest_no_claim_under_frozen_preregistered_all_gate`.

## 2. Immutable inputs and additive correction

| Evidence | Root/SHA |
|---|---|
| Fixed Diffusion Planner | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Fresh execution | `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881` |
| Independent execution review | `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d` |
| Corrected legacy evaluation | `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f` |
| Corrected legacy evaluation review | `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459` |
| Continuation ledger, unchanged | `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392` |

The first v2 package is preserved as a superseded diagnostic, not rewritten:
contract `2a3c39aea959a9e311859f8af2c4ea81e22ac093b4e62ea48cbca6f4808d5795`,
contract review
`a15edb5cad2279991dec2f091e134cd3a711a1b949eb38523a20125578500fed`,
materialization
`0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d`,
and review
`d1cfb29dbb34e3bb92592f803820a6a0454af89b3b9fc2100b45cbaf8215f91d`.
Its B/T/W label, red encounter handling, route/goal coupling, omitted road
boundary field, and unbounded TTC policy are superseded only for this additive
v2 evaluation.

The first corrected package is also preserved as a superseded engineering
diagnostic: contract
`ab99f6740038136409b9f131c8bd38dd35b1b19c338e85c4df6ba86b25f59306`,
contract review
`0962b233a2a0391649433233bd4e7fcbd688ddedc28f2d25fa5cf4eda9354628`,
materialization
`3a4575f346188d87c4c3c18e4cc817540eac09aa38cd0cf886628c3013402588`,
and review
`372550201df3f62907d7fe247cb9889cecfa2abef91ab7db425613f70c816827`.
It incorrectly classified union-boundary extraction as new-evidence missing
and used a coarse scalar-direction heuristic.

The current corrected implementation is Git HEAD
`ee04c1ee3226684ba85f66f6e75566b82e871c77`. Its outcome-independent contract
and independent contract review were sealed before the current B4
materialization:

| Role | Exact path | Root |
|---|---|---|
| Outcome-free focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_second_correction_prefreeze_focused_ee04c1ee_8680c1b19ce0620b` | `d87d54009088ad5b60fd299c962950c884bae9ea928d0ba86f0972021936cbd7` |
| Corrected contract | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_contract_ee04c1ee_8680c1b19ce0620b` | `99501763a4a88c9d80fff738054b37593717df0b6d33e3749ad451d9e52a15e0` |
| Independent contract review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_contract_review_ee04c1ee_8680c1b19ce0620b` | `a7ba686647ccfe64f45a3304a00a392c1a362534833023fe26e0343a374bfac0` |
| Read-only corrected materialization | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_materialization_ee04c1ee_8680c1b19ce0620b` | `4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941` |
| Independent corrected review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_materialization_review_ee04c1ee_8680c1b19ce0620b` | `e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b` |

The result reviewer uses reviewer-local formulas, direction tables, thresholds,
root checks, sample accounting, and cluster aggregation; it does not import
the producer v2 metric oracle.

## 3. Corrected contract semantics

### Better / tie / worse and clustered inference

For every scalar with an outcome-independent natural direction, v2 reports
Better/Tie/Worse over all 500 paired units. `lower` or `higher` is frozen in
the contract and a tie is exactly zero method-minus-candidate0 delta. The three
counts must sum to 500. Signed means, opportunity counts, sample-accounting
fields, and other directionless scalars are
`descriptive_unclassified`; no B/T/W is manufactured.
The producer records an exhaustive direction mapping for all 180 actual
descriptive scalar paths, and the independent reviewer reconstructs that
mapping using a reviewer-local literal table. Unknown paths fail closed.

Confidence intervals remain Student-t intervals over 100 equal-mass
corridor/intersection cluster means. The retained between/total/within
variance fields are auxiliary variance decomposition and explicitly are not
Better/Tie/Worse.

### Geometry and source corrections

- Dynamic TTC is finite only when centroid `r dot v_rel < 0` and continuous
  SAT entry occurs within the frozen 5.0 s project-descriptive horizon.
  Candidate ego velocity is accurately named as the same-tick
  scalar-speed-times-heading kinematic reconstruction.
- A stationary front edge disjoint from a certified stop line is a computed
  non-crossing. Coincident/tangent/multiple-crossing geometry remains
  ambiguous. Certified stop-line encounter identity is deduplicated across
  red-phase interruptions; red-phase interval count remains separate.
- Ordered route state can stay on the same segment or move through frozen
  forward or backward adjacency, while rejecting non-adjacent jumps. The
  travel bound is the larger of sealed position displacement and trapezoidal
  speed distance plus the frozen numeric epsilon. Completion is
  `clip((max(s)-s0)/route_length,0,1)`.
- Goal distance/reached/passed is independent of route-path availability.
  Passed uses same-tick distance and heading geometry, never an historical
  minimum combined with a later heading.
- Full-polygon outside fraction and signed boundary distance are computed from
  the same root-bound finite lanelet-polygon inventory. Polygon edges are
  split at intersections; segments with union on both sides are discarded as
  internal overlap/adjacency seams. A contained footprint reports positive
  minimum full-footprint-boundary clearance; an outside footprint reports
  negative maximum boundary penetration and its positive magnitude.

Synthetic/adversarial tests cover stationary-far and coincident red geometry,
phase interruption and multiple stop lines, 0.4 m/s unthresholded crossing,
backward adjacency and non-adjacent route jumps, nonzero start arc,
route-missing-but-goal-computable, near-then-turn-away goal geometry,
non-approaching SAT and TTC beyond 5 s, five-points-inside/full-polygon-outside,
adjacent and overlapping lanelet seams, fully inside/touching/partially outside
footprints, exhaustive scalar-direction coverage, and every
schema/root/formula/grid drift required to fail closed.

## 4. Endpoint availability

| Endpoint | Status | Available / required | Missing | Opportunity or missing reason |
|---|---:|---:|---:|---|
| Collision | `benchmark_only` | 1500 / 1500 | 0 | 1,500 complete runs; severity missing |
| Dynamic proximity | `benchmark_only` | 1500 / 1500 | 0 | 68,160 actor-ticks; PET missing |
| Road containment | `benchmark_only` | 1500 / 1500 | 0 | outside fraction and signed external-union-boundary metrics computed |
| Certified red crossing | `evidence_missing` | 1063 / 1500 | 437 | 846 deduplicated certified encounters; ambiguous swept geometry |
| Speed | `benchmark_only` | 1500 / 1500 | 0 | same-tick map limit |
| Route | `evidence_missing` | 929 / 1500 | 571 | 565 no unique feasible path; 6 equal-cost paths |
| Goal | `benchmark_only` | 1500 / 1500 | 0 | independently computed from sealed goal inputs |
| Vehicle-body planar proxy | `benchmark_only` | 1500 / 1500 | 0 | 64->63->62->52 acceleration and 51 jerk samples |
| Latency | `benchmark_only` | 1500 / 1500 | 0 | controlled AutoDL stage timing |

Red and route paired inference are cancelled because the full 1,500-arm
denominator is unavailable. No complete-case denominator is substituted.
Candidate0 dynamic-source equivalence is 320 equivalent, zero missing, and 180
not applicable because those runs contain no dynamic actor.

## 5. Representative descriptive results with real B/T/W

All deltas are method minus candidate0. CI95 is over 100 independent equal-mass
clusters; B/T/W is over the 500 frozen paired units.

| Scalar (direction) | Method | Mean delta [CI95] | Better / tie / worse |
|---|---|---:|---:|
| collision any (`lower`) | Static14D | -0.0240 [-0.0460485, -0.00195154] | 14 / 484 / 2 |
| collision any (`lower`) | Scene14D | -0.0140 [-0.0320628, 0.00406277] | 10 / 487 / 3 |
| collision duration (`lower`) | Static14D | -0.0176 [-0.0458997, 0.0106997] | 58 / 420 / 22 |
| collision duration (`lower`) | Scene14D | -0.0150 [-0.0348492, 0.00484918] | 47 / 432 / 21 |
| maximum closing (`lower`) | Static14D | -0.167647 [-0.264142, -0.0711524] | 199 / 192 / 109 |
| maximum closing (`lower`) | Scene14D | -0.0947279 [-0.133836, -0.0556198] | 220 / 198 / 82 |
| road max outside fraction (`lower`) | Static14D | -0.0162363 [-0.0245723, -0.00790036] | 269 / 44 / 187 |
| road max outside fraction (`lower`) | Scene14D | -0.00640012 [-0.0130530, 0.000252736] | 211 / 88 / 201 |
| road minimum signed boundary clearance (`higher`) | Static14D | 0.0281822 [0.0122791, 0.0440854] | 257 / 20 / 223 |
| road minimum signed boundary clearance (`higher`) | Scene14D | 0.00704554 [-0.00774476, 0.0218358] | 243 / 67 / 190 |
| road maximum penetration (`lower`) | Static14D | -0.0281822 [-0.0440854, -0.0122791] | 257 / 20 / 223 |
| road maximum penetration (`lower`) | Scene14D | -0.00704554 [-0.0218358, 0.00774476] | 243 / 67 / 190 |
| speed max excess (`lower`) | Static14D | -0.0410297 [-0.0605025, -0.0215570] | 86 / 402 / 12 |
| speed max excess (`lower`) | Scene14D | -0.00581840 [-0.0134303, 0.00179353] | 51 / 402 / 47 |
| goal minimum distance (`lower`) | Static14D | 1.016269 [0.644221, 1.388318] | 144 / 0 / 356 |
| goal minimum distance (`lower`) | Scene14D | 0.358971 [0.137536, 0.580406] | 197 / 0 / 303 |
| longitudinal acceleration RMS (`lower`) | Static14D | -0.0470491 [-0.0584729, -0.0356253] | 383 / 0 / 117 |
| longitudinal acceleration RMS (`lower`) | Scene14D | -0.0488422 [-0.0575187, -0.0401657] | 396 / 0 / 104 |
| longitudinal jerk RMS (`lower`) | Static14D | 0.0103764 [-0.0177714, 0.0385242] | 250 / 0 / 250 |
| longitudinal jerk RMS (`lower`) | Scene14D | -0.0323561 [-0.0550232, -0.00968907] | 277 / 0 / 223 |
| 100 ms latency exceedance (`lower`) | Static14D | 0.997219 [0.996655, 0.997782] | 0 / 0 / 500 |
| 100 ms latency exceedance (`lower`) | Scene14D | 0.997219 [0.996655, 0.997782] | 0 / 0 / 500 |

The complete aggregate-only endpoint vector, including every scalar, arm mean,
direction or unclassified status, B/T/W, 100-cluster CI, denominator, and
missing reason, is
`docs/diffusion_planner_v25_evaluation_v2_aggregate_summary.json`
(SHA256 `ca6a911d9d1f98ad5b73eaec43fc23c36ed81edc4003b436e6ca7765401d3680`).
It contains no per-run values and no embedded legacy evaluation payload.

## 6. Interpretation boundary

All threshold grids, signed road-boundary summaries, and the 5 s TTC horizon are
`project_descriptive_not_industrial_gate`. Collision severity, PET,
occupant/seat/vertical response, ISO 2631 or SAE J2834 conformity, and
production scheduler/deadline evidence
remain missing or not assessed.

Nothing in v2 authorizes Fresh scientific benefit, real-road safety, broad
unseen-map generalization, native-ranked Top1, industrial comfort or
conformity, promotion, deployment, online activation, or production
readiness. The immutable legacy SafetyCost values remain controlled-benchmark
project composites, not v2 or industrial claims.
