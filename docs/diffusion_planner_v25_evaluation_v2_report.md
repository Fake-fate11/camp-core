# V25 Evaluation v2 — Additive Read-Only B4 Report

## 1. Decision

Evaluation v2 is an additive, post-hoc, read-only endpoint-vector analysis of
the already sealed Fresh B4 denominator. It is
`exploratory_posthoc_not_claim_authorizing`.

It does not alter the legacy benchmark v1 values, preregistration,
multiplicity, NI gates, corrected evaluation/review, scientific ledger,
continuation ledger, or final decision. The final legacy scientific decision
remains:

`honest_no_claim_under_frozen_preregistered_all_gate`

No weighted v2 total is generated. No v2 scientific hard gate was
prospectively defined. A future confirmatory claim would require a separate
prospective preregistration on new nonholdout evidence.

## 2. Immutable source chain

| Evidence | Immutable binding |
|---|---|
| Fixed Diffusion Planner | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Fresh identity | `5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a` |
| Protocol | `aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f` |
| Plan | `41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0` |
| Nonce | `8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42` |
| Execution root | `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881` |
| Execution-review root | `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d` |
| Corrected-evaluation root | `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f` |
| Corrected-evaluation-review root | `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459` |
| Continuation-ledger SHA | `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392` |

The denominator is exactly 500 paired units, 1,500 complete arms, 64 ticks per
arm, and 96,000 ticks. Fresh, arms, DP/K8, corrected evaluation, and corrected
review were not rerun. The old sealed artifacts and both scientific/CAS
histories were not written.

## 3. Prospective v2 contract and independent reviews

The versioned `camp_dp_v25_evaluation_v2_contract_v1` was implemented and
tested without reading B4 outcome values, then sealed before B4
materialization. A separate contract-review role validated the literal
contract, grids, formulas, roots, denominator, source-capability policy, and
claim boundary.

After contract PASS, the producer verified the full existing seal chain and
materialized one read-only v2 artifact. A separate result-review role did not
import the producer metric module or its threshold tables. It independently
reconstructed all 1,500 receipts, full-polygon geometry, route logic,
64→63→62→52→51 sample accounting, legacy equality, per-run values,
500-pair/100-cluster aggregates, denominators, and claim invariance.

### Preserved pre-artifact mechanical diagnostic

The first implementation contract at `ab67b801…` sealed successfully, but its
first materialization control stopped before atomic artifact formation. The
aggregate path serializer split a contract-known decimal threshold key on
`.` and raised `KeyError: '5'`; neither a v2 materialization artifact nor a
v2 review directory was created. No outcome value was used to choose the
repair. The producer and reviewer-local oracle were changed to escaped JSON
Pointer scalar paths, a synthetic decimal/reserved-key regression test was
added, and the outcome-free contract/review were resealed at `de173a20…`
before the repaired materialization. The failed control and superseded
contract seals remain preserved as engineering diagnostics.

The first independent result-review control then passed literal equality for
every endpoint but failed before atomic review formation at the run-inventory
hash. Static inspection found that the producer correctly treated candidate0
supplementary equivalence as not applicable when a run had no dynamic actors,
whereas the reviewer had computed it for all candidate0 runs. The
reviewer-local applicability rule and synthetic test were corrected at
`7c3e67c6…`; the already sealed materialization was not rerun. The repaired
review additionally accounts for equivalent, evidence-missing, and
not-applicable candidate0 runs.

## 4. Endpoint contract

Every endpoint carries its own formula, units, source root/SHA, evidence
class, opportunity/denominator, per-run values, aggregate, and status. Status
is one of `computed`, `benchmark_only`, `evidence_missing`, or
`requires_future_nonholdout_acquisition`; an ambiguous route/red substatus
maps to `evidence_missing`.

| Endpoint | Frozen v2 definition | Industrial/claim boundary |
|---|---|---|
| Collision | Full ego/actor OBB intersection; any, false→true episodes, duration. | Geometric benchmark only; severity is missing. |
| Dynamic proximity | Full-polygon clearance, relative closing, continuous-SAT TTC, DRAC. | Descriptive project grids only; PET is missing; no `near_miss` label. |
| Road containment | Full footprint area outside root-bound drivable polygon union. | Five-point coverage is not substituted. |
| Certified red crossing | Same-tick certified red phase and exact route stop-line; swept full front edge; unthresholded crossing. | No future phase; ambiguity is missing; not a regulatory violation rate. |
| Speed | Same-tick `max(0,v-limit)`, duration and magnitude-duration at 0/0.05/0.1/0.2 m/s. | Project benchmark; 0.1 m/s is not a legal threshold. |
| Route | Stateful ordered-route projection with same/adjacent transitions and tick travel bound. | Ambiguous path is missing; completion is benchmark-only. |
| Vehicle-body planar kinematic proxy | 64 positions→63 velocities→62 accelerations→52 filtered samples→51 filtered-jerk samples. | Not seat/occupant comfort; ISO 2631/SAE J2834 not assessed. |
| Latency | Per-run/per-stage mean, median, p95, p99, max; total deadline grid 50/100/200/500/1000 ms. | Controlled AutoDL measurement, not production real-time certification. |

The industrial-semantics classifications and current ISO/SAE scope references
remain in
`docs/diffusion_planner_v25_metric_semantics_amendment_report.md`. Evaluation
v2 adds better-defined exploratory geometry/kinematics; it does not upgrade
the evidence class to industrial conformity.

## 5. Materialized endpoint availability

| Endpoint | Status | Available / required arms | Missing | Aggregate |
|---|---:|---:|---:|---|
| `collision` | `benchmark_only` | 1500 / 1500 | 0 | `benchmark_only` |
| `dynamic_proximity` | `benchmark_only` | 1500 / 1500 | 0 | `benchmark_only` |
| `road_containment` | `benchmark_only` | 1500 / 1500 | 0 | `benchmark_only` |
| `certified_red_crossing` | `evidence_missing` | 1063 / 1500 | 437 | `evidence_missing` |
| `speed` | `benchmark_only` | 1500 / 1500 | 0 | `benchmark_only` |
| `route` | `evidence_missing` | 0 / 1500 | 1500 | `evidence_missing` |
| `vehicle_body_planar_kinematic_proxy` | `benchmark_only` | 1500 / 1500 | 0 | `benchmark_only` |
| `latency` | `benchmark_only` | 1500 / 1500 | 0 | `benchmark_only` |

Missing arms are always shown against the required 1,500-arm denominator.
No complete-case subset is promoted into paired inference.
An endpoint may be `benchmark_only` while a separately named capability
inside its scope remains missing—for example collision severity, PET,
occupant/seat response, or production deadline certification. Those gaps are
not converted into zeroes or proxy passes.

The red endpoint has 846 total certified-stop-line opportunities, but 437
runs contain at least one within-tick swept-geometry ambiguity. Those runs are
`ambiguous_evidence_missing`, so the full paired red inference is cancelled.
The route endpoint is `ambiguous_evidence_missing` for all 1,500 arms because
the frozen sampled evidence does not yield a unique path satisfying the
ordered adjacency and trapezoidal tick travel bound
(`no_unique_kinematically_feasible_route_path`). V2 does not fall back to the
legacy stateless nearest projection.

All 320 candidate0 runs with dynamic actors passed exact
supplementary↔primary equivalence. The remaining 180 candidate0 runs contain
no dynamic actors, so equivalence is correctly `not_applicable`; none is
evidence-missing.

## 6. Descriptive B4 v2 results

Representative complete-denominator descriptive summaries are below. Values
are arm means of per-run endpoint summaries; deltas are method minus
candidate0 over 100 equal-mass cluster means.

| Endpoint scalar path | Candidate0 | Static14D | Scene14D | Static14D delta [CI95] | Scene14D delta [CI95] |
|---|---:|---:|---:|---:|---:|
| `collision/collision_any` | 0.336 | 0.312 | 0.322 | -0.024 [-0.0460485, -0.00195154] | -0.014 [-0.0320628, 0.00406277] |
| `collision/duration_s` | 0.3256 | 0.3080 | 0.3106 | -0.0176 [-0.0458997, 0.0106997] | -0.0150 [-0.0348492, 0.00484918] |
| `dynamic_proximity/max_closing_mps` | 4.61771 | 4.45006 | 4.52298 | -0.167647 [-0.264142, -0.0711524] | -0.0947279 [-0.133836, -0.0556198] |
| `dynamic_proximity/max_drac_mps2` | 166.565 | 94.0329 | 81.1370 | -72.5325 [-237.953, 92.8879] | -85.4285 [-245.079, 74.2216] |
| `road_containment/max_outside_fraction` | 0.245950 | 0.229714 | 0.239550 | -0.0162363 [-0.0245723, -0.00790036] | -0.00640012 [-0.0130530, 0.000252736] |
| `road_containment/duration_s` | 1.8042 | 1.7868 | 1.7772 | -0.0174 [-0.0950928, 0.0602928] | -0.0270 [-0.0882152, 0.0342152] |
| `speed/max_excess_mps` | 0.166054 | 0.125024 | 0.160236 | -0.0410297 [-0.0605025, -0.0215570] | -0.00581840 [-0.0134303, 0.00179353] |
| `speed/0.1mps_duration_s` | 0.3430 | 0.2590 | 0.3156 | -0.0840 [-0.131881, -0.0361189] | -0.0274 [-0.0474111, -0.00738895] |
| `speed/0.1mps_magnitude_duration_m` | 0.214760 | 0.125383 | 0.176825 | -0.0893777 [-0.134816, -0.0439396] | -0.0379352 [-0.0614168, -0.0144536] |
| `body_proxy/longitudinal_acceleration_rms_mps2` | 1.13384 | 1.08679 | 1.08500 | -0.0470491 [-0.0584729, -0.0356253] | -0.0488422 [-0.0575187, -0.0401657] |
| `body_proxy/lateral_acceleration_rms_mps2` | 0.362311 | 0.330556 | 0.341628 | -0.0317541 [-0.0422262, -0.0212820] | -0.0206831 [-0.0286087, -0.0127574] |
| `body_proxy/longitudinal_jerk_rms_mps3` | 2.48444 | 2.49481 | 2.45208 | 0.0103764 [-0.0177714, 0.0385242] | -0.0323561 [-0.0550232, -0.00968907] |
| `body_proxy/lateral_jerk_rms_mps3` | 0.493217 | 0.517307 | 0.511958 | 0.0240901 [0.00911801, 0.0390622] | 0.0187410 [0.00587678, 0.0316053] |
| `latency/total_p95_ms` | 70.2469 | 566.872 | 571.615 | 496.625 [487.874, 505.377] | 501.368 [492.566, 510.169] |
| `latency/100ms_exceedance_rate` | 0.00278125 | 1.0 | 1.0 | 0.997219 [0.996655, 0.997782] | 0.997219 [0.996655, 0.997782] |
| `latency/500ms_exceedance_rate` | 0.00003125 | 0.9665 | 0.990313 | 0.966469 [0.953518, 0.979419] | 0.990281 [0.984675, 0.995887] |

All grids are `project_descriptive_not_industrial_gate`. Paired summaries are
descriptive Student-t summaries over 100 equal-mass independent
corridor/intersection cluster means. Ticks, seeds, and arms are not treated as
independent samples. The complete aggregate endpoint vector, including every
descriptive scalar path, arm mean, paired mean delta, CI95, and B/T/W
variance component, is published in
`docs/diffusion_planner_v25_evaluation_v2_aggregate_summary.json`. That
aggregate-only file contains no per-run values and no embedded legacy
evaluation payload.

## 7. Evidence gaps

The following are not inferred or backfilled:

- collision severity/delta-v/contact qualification;
- PET without conflict-zone identity and both passage times;
- any candidate0 dynamic-pair endpoint lacking exact supplementary↔primary
  equivalence;
- any road/route endpoint lacking execution-time root-bound geometry;
- seat, occupant, vertical, roll, pitch, suspension, or human-transfer
  response;
- ISO 2631 or SAE J2834 conformity;
- production deadline behavior without controlled warm-up, concurrent load,
  and scheduler evidence.

The minimum prospective acquisition package is specified in
`docs/diffusion_planner_v25_evaluation_v2_future_nonholdout_acquisition_plan.md`.

## 8. Migration and interpretation

The field-by-field legacy→v2 mapping is in
`docs/diffusion_planner_v25_evaluation_v2_migration_matrix.md`. Legacy
SafetyCost remains an immutable project-defined controlled-benchmark
composite. Its historical decrease is not a v2 pass, Fresh benefit claim, or
industrial safety claim.

Evaluation v2 does not authorize claims of Fresh scientific benefit, real-road
safety, broad unseen-map generalization, native-ranked Top1 performance,
industrial comfort/conformity, promotion, deployment, online activation, or
production readiness.

## 9. Reproducibility and no-mutation accounting

| Role | HEAD/path | Root/SHA |
|---|---|---|
| Frozen v2 producer implementation | `de173a204efddbb8494d8bfe4c90f07f60d5d1d8` | JSON Pointer repair included before final contract |
| Outcome-free prefreeze focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_prefreeze_focused_de173a20_8680c1b19ce0620b` | `9fd8152d5187accb3f493da28e8d636216f3025b4b92bc9ae36470aae467c331` |
| V2 contract | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_contract_de173a20_8680c1b19ce0620b` | `2a3c39aea959a9e311859f8af2c4ea81e22ac093b4e62ea48cbca6f4808d5795` |
| Independent contract review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_contract_review_de173a20_8680c1b19ce0620b` | `a15edb5cad2279991dec2f091e134cd3a711a1b949eb38523a20125578500fed` |
| Read-only materialization | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_materialization_de173a20_8680c1b19ce0620b` | `0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d` |
| Reviewer repair implementation | `7c3e67c64faf1dbc838f9dcd10da82fa1a8fbdb2` | Materialization unchanged |
| Reviewer repair focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_reviewer_repair_focused_7c3e67c6_8680c1b19ce0620b` | `e218de63613459a35a3339080aa296935dcf0c582f284bbcbb6c0d1dea3a9214` |
| Independent v2 review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_materialization_review_7c3e67c6_8680c1b19ce0620b` | `d1cfb29dbb34e3bb92592f803820a6a0454af89b3b9fc2100b45cbaf8215f91d` |
| Aggregate-only summary | `docs/diffusion_planner_v25_evaluation_v2_aggregate_summary.json` | `2698b7d65f9d791ea048b0c3c3d79dcec788bd8df45aed12a5d87d10f7c467d0` |

The authoritative focused suite uses synthetic/adversarial and existing
nonFresh fixtures only. The sealed execution and corrected-evaluation chains
are read-only inputs. Evaluation v2 does not write scientific or continuation
CAS state.
