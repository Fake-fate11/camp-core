# V25 Evaluation v2 Corrected Evidence Index

Status: additive, exploratory, independently reviewed, and not claim-authorizing.

## Immutable source chain

| Evidence | Root/SHA |
|---|---|
| Fixed Diffusion Planner | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Fresh execution | `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881` |
| Independent execution review | `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d` |
| Corrected legacy evaluation | `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f` |
| Corrected legacy review | `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459` |
| Continuation ledger, unchanged | `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392` |

## Preserved superseded v2 diagnostic

| Role | Root |
|---|---|
| Contract | `2a3c39aea959a9e311859f8af2c4ea81e22ac093b4e62ea48cbca6f4808d5795` |
| Independent contract review | `a15edb5cad2279991dec2f091e134cd3a711a1b949eb38523a20125578500fed` |
| Materialization | `0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d` |
| Independent result review | `d1cfb29dbb34e3bb92592f803820a6a0454af89b3b9fc2100b45cbaf8215f91d` |

These seals remain unchanged. They are superseded only for the additive v2
semantics corrected at `6e74016ca97b0677ef0d3221e56206b9642cd65d`.

## Corrected sealed chain

| Role | Exact path | Root |
|---|---|---|
| Outcome-free focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_correction_prefreeze_focused_6e74016c_8680c1b19ce0620b` | `d895e9c5221bb9a1d003e917021ba427ec6c614a695da4a1b00e9fdd36380f3e` |
| Corrected v2 contract | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_contract_6e74016c_8680c1b19ce0620b` | `ab99f6740038136409b9f131c8bd38dd35b1b19c338e85c4df6ba86b25f59306` |
| Independent contract review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_contract_review_6e74016c_8680c1b19ce0620b` | `0962b233a2a0391649433233bd4e7fcbd688ddedc28f2d25fa5cf4eda9354628` |
| Read-only corrected materialization | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_materialization_6e74016c_8680c1b19ce0620b` | `3a4575f346188d87c4c3c18e4cc817540eac09aa38cd0cf886628c3013402588` |
| Independent corrected result review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_corrected_materialization_review_6e74016c_8680c1b19ce0620b` | `372550201df3f62907d7fe247cb9889cecfa2abef91ab7db425613f70c816827` |
| Aggregate-only endpoint vector | `docs/diffusion_planner_v25_evaluation_v2_aggregate_summary.json` | `3c9a88d3570db0529102809e284b1f7d18e7e10f286c85c64ee603f9ddac38af` |

## Corrected acceptance matrix

| Endpoint | Status | Available / missing / required | Inference |
|---|---|---:|---|
| collision | `benchmark_only` | 1500 / 0 / 1500 | 500-pair B/T/W + 100-cluster CI |
| dynamic proximity | `benchmark_only` | 1500 / 0 / 1500 | 500-pair B/T/W + 100-cluster CI |
| road containment | `benchmark_only` | 1500 / 0 / 1500 | outside fraction inferred; signed boundary field explicitly missing |
| certified red crossing | `evidence_missing` | 1063 / 437 / 1500 | cancelled; no complete-case shrinkage |
| speed | `benchmark_only` | 1500 / 0 / 1500 | 500-pair B/T/W + 100-cluster CI |
| route | `evidence_missing` | 929 / 571 / 1500 | cancelled; no complete-case shrinkage |
| goal | `benchmark_only` | 1500 / 0 / 1500 | 500-pair B/T/W + 100-cluster CI |
| vehicle-body planar proxy | `benchmark_only` | 1500 / 0 / 1500 | 500-pair B/T/W + 100-cluster CI |
| latency | `benchmark_only` | 1500 / 0 / 1500 | 500-pair B/T/W + 100-cluster CI |

Every directed scalar uses a contract-frozen `lower`/`higher` direction and
exact-zero tie rule. Directionless scalars are `descriptive_unclassified`.
Between/total/within variance fields are not B/T/W.

## Documentation

| Document | Purpose |
|---|---|
| `docs/diffusion_planner_v25_evaluation_v2_report.md` | Corrected read-only report and interpretation boundary |
| `docs/diffusion_planner_v25_evaluation_v2_migration_matrix.md` | Legacy and superseded-v2 migration |
| `docs/diffusion_planner_v25_evaluation_v2_future_nonholdout_acquisition_plan.md` | Explicit evidence gaps and prospective acquisition |
| `docs/diffusion_planner_v25_evaluation_v2_aggregate_summary.json` | Full aggregate vector without per-run/raw values |

## No-mutation and claim boundary

- Denominator: 500 pairs, 1,500 arms, 96,000 ticks.
- Fresh/arm/DP/K8/corrected-evaluation rerun: false.
- Old materialization/review/artifact/CAS mutation: false.
- Independent corrected reconstruction: 1,500 receipts and 100 clusters.
- Weighted v2 total: none.
- V2 scientific hard gate: `not_prospectively_defined_for_v2`.
- V2 claim authorization: false.
- Legacy decision: `honest_no_claim_under_frozen_preregistered_all_gate`.
- Prohibited claims: Fresh benefit, real-road safety, broad unseen-map,
  native-ranked Top1, industrial comfort/conformity, promotion, deployment,
  online activation, and production readiness.
