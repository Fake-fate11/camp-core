# V25 Metric-Semantics Amendment Evidence Index

Date: 2026-07-25 (Asia/Shanghai)

Schema: `camp_dp_v25_metric_semantics_amendment_v1`

Status: `independently_reviewed`

Final claim (unchanged):
`honest_no_claim_under_frozen_preregistered_all_gate`.

## Authoritative additive artifacts

| Layer | Path | Root SHA-256 | Status |
|---|---|---|---|
| Outcome-independent contract | `/root/autodl-tmp/camp_dp_v25_metric_semantics_contract_b729ebe4_8680c1b19ce0620b` | `318e85f9656a5dd79c9fb0ad6c1dfcd94678b35c4aba455f3909cf3475cca758` | sealed |
| Contract independent review | `/root/autodl-tmp/camp_dp_v25_metric_semantics_contract_review_b729ebe4_8680c1b19ce0620b` | `fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95` | PASS |
| Read-only metric amendment | `/root/autodl-tmp/camp_dp_v25_metric_semantics_amendment_b729ebe4_8680c1b19ce0620b` | `99fd5e571160a3ac3d5bb2b6d6f3391c3da5965bf592707ff85c88080ac2dbcf` | sealed |
| Amendment independent review | `/root/autodl-tmp/camp_dp_v25_metric_semantics_amendment_review_b729ebe4_8680c1b19ce0620b` | `88b35ab8ef51807c848200675ceeebe6b26e15a4f4b34da51f131e9303f37898` | PASS |
| Implementation-focused AutoDL suite | `/root/autodl-tmp/camp_dp_v25_metric_semantics_focused_b729ebe4_8680c1b19ce0620b` | `896fa3858a427462ecd4d3b206208605864fb34f3a4a5dd43ca723ec30445e95` | 31 passed |

Implementation HEAD:
`b729ebe4ca34615453a8f7252585bdb5f30d3ac9`.

Fixed DP HEAD:
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

## Preserved sealed source chain

| Evidence | Root / SHA-256 |
|---|---|
| Fresh B4 execution | `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881` |
| Independent execution review | `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d` |
| Corrected evaluation | `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f` |
| Corrected evaluation review | `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459` |
| Continuation ledger | `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392` |
| Old scientific ledger, preserved diagnostic | `c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4` |
| Old closeout | `a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398` |
| Old closeout review | `86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062` |

Denominator: 500 paired units, 1,500 complete and terminal arms, 96,000
ticks, full denominator formed. Fresh rerun=false; corrected-evaluation
rerun=false; DP/K8 rerun=false; sealed source artifacts written=false;
scientific or continuation CAS written=false.

## Per-metric acceptance index

| # | Metric | Exact class | Amendment evidence |
|---:|---|---|---|
| 1 | SafetyCost | benchmark-only | Legacy formula/value/source preserved; industrial interpretation deprecated |
| 2 | Collision | benchmark-only | Simulation OBB overlap-any only |
| 3 | Near miss | FAIL-industrial | Exact alias `noncollision_obb_clearance_le_2m_tick_rate`; clearance duration/episode grid added |
| 4 | Offroad | FAIL-industrial | Exact five-point proxy alias; full-polygon evidence missing |
| 5 | Wrong-way | FAIL-industrial | Exact nearest-route-segment heading-opposition alias |
| 6 | Red-light source / aggregate | PASS / benchmark-only | Same-tick certified source plus separate unthresholded and >0.5 m/s counts/denominators |
| 7 | Speed | benchmark-only | Strict and 0/0.05/0.1/0.2 sensitivity plus continuous excess measures |
| 8 | Progress/completion | benchmark-only | Final/net/max/backtracking/distance-traveled extension |
| 9 | Jerk | FAIL-industrial | Raw scalar-speed second-difference chatter diagnostic only |
| 10 | Lateral acceleration | FAIL-industrial | Raw speed-times-heading-rate kinematic diagnostic only |
| 11 | Maximum deceleration | FAIL-industrial | Raw same-tick scalar-speed-drop peak diagnostic only |
| 12 | Latency / online readiness | benchmark-only / FAIL-industrial | Sealed stage timing retained; Static/Scene p95 exceed a hypothetical 100 ms cycle |
| 13 | Clustered statistics | PASS | Per-run first, then 100 independent cluster means; no pooled-tick inference |
| 14 | Vehicle-body planar proxy | post-hoc descriptive | 64->63->62->52 accounting, signed summaries and project duration grid |
| 15 | Occupant/seat/vertical comfort | evidence-missing | ISO 2631 / SAE J2834 conformity not assessed |

## Verification coverage

The focused suite covers:

- exact aliases, formulas, and no mutation of legacy values;
- 64 positions -> 63 interval velocities -> 62 accelerations -> 52
  valid-only filtered samples;
- signed body-frame rotation and the 11-point equal-weight zero-phase filter;
- duration grids and per-run-before-pair-and-cluster aggregation;
- fail-closed missing full-polygon, seat, and vertical evidence;
- exact red, speed, route, and clearance fixtures;
- no raw artifact write and no CAS write;
- rejection of unknown fields, source/root drift, legacy-value drift,
  formula drift, sample-accounting drift, claim drift, and pooled-tick
  inference.

The independent reviewer reconstructs producer outputs from sealed native
receipts and frozen formulas. It verifies 500 pairs, 1,500 arms, 96,000 ticks,
52 filtered samples per run, legacy equality, paired cluster summaries, roots,
HEADs, and claim invariance.

## Documentation

- Additive report:
  `docs/diffusion_planner_v25_metric_semantics_amendment_report.md`
- Additive evidence index:
  `docs/diffusion_planner_v25_metric_semantics_amendment_evidence_index.md`
- Preserved corrected report:
  `docs/diffusion_planner_v25_final_corrected_evaluation_report.md`
- Preserved corrected evidence index:
  `docs/diffusion_planner_v25_final_corrected_evidence_index.md`

## Claim boundary

The legacy total deltas are only controlled-benchmark composite decreases.
The frozen component and NI all-gates remain false. The new proxy is
descriptive and not a comfort gate. Industrial occupant comfort is
`evidence_missing_not_assessed`.

No Fresh benefit, real-road safety, broad unseen-map/ODD, native-ranked Top1,
industrial comfort, ISO/SAE conformity, promotion, deployment, online
activation, or production-readiness claim is authorized.
