# V25 Evaluation v2 Evidence Index

Status: additive exploratory evidence package; not claim-authorizing.

## Immutable input chain

| Role | Root/SHA |
|---|---|
| Fixed Diffusion Planner HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Fresh execution | `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881` |
| Independent execution review | `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d` |
| Corrected evaluation | `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f` |
| Corrected evaluation review | `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459` |
| Continuation ledger | `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392` |

## Evaluation v2 sealed chain

| Role | Exact path | Root/SHA |
|---|---|---|
| Final producer implementation | Git HEAD `de173a204efddbb8494d8bfe4c90f07f60d5d1d8` | Outcome-free contract implementation |
| Outcome-free prefreeze focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_prefreeze_focused_de173a20_8680c1b19ce0620b` | `9fd8152d5187accb3f493da28e8d636216f3025b4b92bc9ae36470aae467c331` |
| V2 contract | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_contract_de173a20_8680c1b19ce0620b` | `2a3c39aea959a9e311859f8af2c4ea81e22ac093b4e62ea48cbca6f4808d5795` |
| Independent contract review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_contract_review_de173a20_8680c1b19ce0620b` | `a15edb5cad2279991dec2f091e134cd3a711a1b949eb38523a20125578500fed` |
| Read-only v2 materialization | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_materialization_de173a20_8680c1b19ce0620b` | `0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d` |
| Reviewer repair implementation | Git HEAD `7c3e67c64faf1dbc838f9dcd10da82fa1a8fbdb2` | Materialization unchanged |
| Reviewer repair focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_reviewer_repair_focused_7c3e67c6_8680c1b19ce0620b` | `e218de63613459a35a3339080aa296935dcf0c582f284bbcbb6c0d1dea3a9214` |
| Independent v2 result review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_materialization_review_7c3e67c6_8680c1b19ce0620b` | `d1cfb29dbb34e3bb92592f803820a6a0454af89b3b9fc2100b45cbaf8215f91d` |
| Aggregate-only endpoint vector | `docs/diffusion_planner_v25_evaluation_v2_aggregate_summary.json` | `2698b7d65f9d791ea048b0c3c3d79dcec788bd8df45aed12a5d87d10f7c467d0` |

## Preserved pre-artifact diagnostic

| Evidence | Path/root |
|---|---|
| Initial outcome-free focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_prefreeze_focused_ab67b801_8680c1b19ce0620b`; `9b86dd3b0cfcb1aacf4fcbb9a26da682d6e004b037e76450e0865068fdb1d8d1` |
| Initial contract | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_contract_ab67b801_8680c1b19ce0620b`; `767d3befd1c071008d053e70da542405c5167e82f9e187a1ee4e89ed424bb702` |
| Initial independent contract review | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_contract_review_ab67b801_8680c1b19ce0620b`; `32e61f64ed9922776cd8152fe2cd0682e734a0dd81ae125c0d193a53e775c8c3` |
| Failed control | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_materialization_control_ab67b801_8680c1b19ce0620b`; `run.exit=1`; no materialization/review artifact |

Classification:
`pre_artifact_mechanical_scalar_path_serialization_failure`. The fix used
escaped JSON Pointer paths and did not read an outcome value, alter an
endpoint, or change any legacy/scientific artifact.

| Review-only repair evidence | Path/root |
|---|---|
| Successful materialization | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_materialization_de173a20_8680c1b19ce0620b`; `0cd17b28553b1ae8b1f23eb8796974e6c06f1d5e1c020998d302526f3b07c72d` |
| First review control | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_materialization_control_de173a20_8680c1b19ce0620b`; `run.exit=1`; no review artifact |
| Reviewer repair focused | `/root/autodl-tmp/camp_dp_v25_evaluation_v2_reviewer_repair_focused_7c3e67c6_8680c1b19ce0620b`; `e218de63613459a35a3339080aa296935dcf0c582f284bbcbb6c0d1dea3a9214` |

The review-only failure was
`candidate0_no_dynamic_actor_equivalence_applicability_drift`. All endpoint
literal comparisons had passed before the inventory hash check. The
materialization root was preserved and only the independent reviewer was
rerun.

## Versioned implementation

| File | Purpose |
|---|---|
| `camp_core/camp_core/integrations/diffusion_planner_v25_evaluation_v2.py` | Exact contract, pure computation kernel, endpoint vector, denominator and cluster summaries. |
| `scripts/integrations/freeze_diffusion_planner_v25_evaluation_v2_contract.py` | Outcome-free contract producer. |
| `scripts/integrations/review_diffusion_planner_v25_evaluation_v2_contract.py` | Independent literal contract review. |
| `scripts/integrations/materialize_diffusion_planner_v25_evaluation_v2.py` | Single read-only materialization over the sealed denominator. |
| `scripts/integrations/review_diffusion_planner_v25_evaluation_v2.py` | Separate-role independent result reconstruction without producer metric imports/tables. |
| `camp_core/tests/test_diffusion_planner_v25_evaluation_v2.py` | Synthetic/adversarial contract, geometry, route, red, body proxy, denominator, and fail-closed tests. |

## Documentation

| Document | Purpose | SHA256 |
|---|---|---|
| `docs/diffusion_planner_v25_evaluation_v2_report.md` | Main additive v2 report. | `9c7312c550164b65f9f68e6d1c1a649154bc7fd8b2f53c2d3ac2894c7f0fc37a` |
| `docs/diffusion_planner_v25_evaluation_v2_migration_matrix.md` | Immutable legacy v1 to exploratory v2 mapping. | `6286680de3cb7b920f4e45c14b8f627cd26ea25f3e82e0647d94f82d1ed3c693` |
| `docs/diffusion_planner_v25_evaluation_v2_future_nonholdout_acquisition_plan.md` | Evidence gaps and minimum prospective acquisition. | `057f0f033825602efd3ddb710fd058778d20773fcf1587e97f1486be5f924c6b` |
| `docs/diffusion_planner_v25_evaluation_v2_aggregate_summary.json` | Complete aggregate endpoint vector without per-run or legacy payloads. | `2698b7d65f9d791ea048b0c3c3d79dcec788bd8df45aed12a5d87d10f7c467d0` |

## Acceptance boundary

- Denominator: 500 pairs, 1,500 complete arms, 96,000 ticks.
- Independent result reconstruction: 1,500 receipts and 100 clusters.
- Candidate0 actor-source accounting: 320 equivalent, 0
  evidence-missing, 180 not-applicable because no dynamic actor.
- Endpoint availability: six complete `benchmark_only`; red has 437
  ambiguous runs and route has 1,500 ambiguous runs, with paired inference
  cancelled rather than denominator shrinkage.
- Evaluation v2 weighted total: none.
- V2 prospective scientific hard gate:
  `not_prospectively_defined_for_v2`.
- V2 claim authorization: false.
- Legacy values/preregistration/claim mutation: false.
- Scientific or continuation CAS write: false.
- Final legacy decision:
  `honest_no_claim_under_frozen_preregistered_all_gate`.
- Prohibited claims: Fresh benefit, real-road safety, broad unseen-map,
  native-ranked Top1, industrial comfort/conformity, promotion, deployment,
  online activation, and production readiness.
