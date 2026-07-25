# V25 CAMP over Fixed Diffusion Planner K=8

## Final Auditable Honest-No-Claim Report

Date: 2026-07-25 (Asia/Shanghai)
Final scientific disposition: `honest_no_claim`
Terminal cause:
`unavailable_due_to_post_exposure_evaluation_fatal`

## 1. Executive decision

V25 completed the unique Fresh B4 closed-loop execution over the unchanged
Diffusion Planner K=8 candidate set: 500/500 paired units, 1,500/1,500 complete
and terminal arms, and the full 96,000-tick planned denominator. The independent
execution review passed. The subsequently frozen evaluator failed before
creating an evaluation artifact with:

`ValueError: holdout execution/evaluation role HEAD drifted`

The failure occurred after scientific exposure and after the full denominator
was formed. It is therefore a permanent one-time terminal failure. The
evaluation was not rerun, repaired, redirected, or recomputed; no evaluation
review was started; raw Fresh outcome values were not inspected. Fresh B4
SafetyCost, six-component, CI95, Better/Tie/Worse, stratum, NI, mechanism, and
latency result tables are unavailable. No V25 scientific claim is authorized.

CAMP remained a selector/reranker only. It did not generate, repair, blend,
mask, mutate, or replace fixed-DP candidates or trajectories. Promotion,
deployment, online activation, real-road safety, broad unseen-map
generalization, and native-ranked Top-1 statements are not authorized.

## 2. Immutable authority and provenance

| Item | Frozen value |
|---|---|
| Execution implementation source | `7be93df20deee03587b9898e8560909662df972c` |
| Execution pointer HEAD | `06d3a1f3a37061f93f5c9788312ae59d1356d126` |
| Terminal reporting machinery HEAD | `77b735dcb24ed17e5a897f98f430ca1c536d787c` |
| Fixed Diffusion Planner HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Critical implementation manifest | `f3b707d480b30e1d37d2c10355d8a824df4cff8230af7d78d803dd4504ef6c2b` |
| 24-role authority contract | `3254191ef3ff10e8ab0dda5985acb3589bb44df8534f51a8a033bca26e01c653` |
| Holdout identity | `5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a` |
| Experiment protocol | `aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f` |
| Execution plan | `41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0` |
| Unique B4 nonce | `8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42` |

The later reporting HEAD adds only post-exposure closeout machinery. It is not
the execution/evaluation authority and does not alter the frozen source,
pointer, fixed DP, identity, protocol, plan, models, atoms, scales, weights,
Theta, margins, multiplicity, denominator, or claim rule.

## 3. Fourteen-dimensional atom contract

| Index | Atom | Set |
|---:|---|---|
| 0 | `jerk_early` | 9D |
| 1 | `jerk_late` | 9D |
| 2 | `jerk_full` | 9D |
| 3 | `rms_acceleration` | 9D |
| 4 | `speed_limit_margin_0_0` | 9D |
| 5 | `speed_limit_margin_0_5` | 9D |
| 6 | `speed_limit_margin_1_0` | 9D |
| 7 | `lane_deviation` | 9D |
| 8 | `clearance` | 9D |
| 9 | `progress_shortfall` | 14D extension |
| 10 | `planned_red_light_cost` | 14D extension |
| 11 | `planned_lateral_acceleration_cost` | 14D extension |
| 12 | `red_stopping_margin_cost` | 14D extension |
| 13 | `dp_prior_jerk_excess_cost` | 14D extension |

The train-only audit covered 95,616 snapshots and 764,928 fixed-DP candidate
rows and reported 14 PASS, 0 WARN, 0 FAIL. Numerical atom-delta rank was 14 and
effective rank was 3.1832077907871783. The 9D prefix changed 32,204 selected
indices, weighted rate 0.34094138781638783, relative to the 14D causal-label
reference. This establishes computability and association inside the
controlled training support, not causal safety benefit.

Atom audit/review roots:
`4dc98d9a812403148f30e2041358fbd79c967e3c8581a9d8569dc362f71d8e7e`
/
`149995eacbcdf21201934bbf428ca5d8871f6c3085b4ab5e90db1d8ef78753bc`.

## 4. Twenty-six-dimensional causal context and leakage audit

The ordered context is:

1. `ego_speed_mps`
2. `ego_longitudinal_acceleration_mps2`
3. `ego_lateral_acceleration_mps2`
4. `ego_yaw_rate_radps`
5. `route_curvature_mean_abs_radpm`
6. `route_curvature_max_abs_radpm`
7. `route_lane_width_min_m`
8. `route_lane_width_p50_m`
9. `route_speed_limit_min_mps`
10. `route_speed_limit_current_mps`
11. `traffic_phase_red`
12. `traffic_phase_yellow`
13. `traffic_phase_green`
14. `traffic_phase_unknown`
15. `traffic_signal_distance_m`
16. `traffic_signal_phase_remaining_s`
17. `neighbor_count`
18. `neighbor_min_distance_m`
19. `neighbor_min_ttc_s`
20. `neighbor_closing_speed_mps`
21. `neighbor_lateral_gap_min_m`
22. `candidate_consensus_rms_median_m`
23. `candidate_consensus_rms_mad_m`
24. `candidate_endpoint_xy_std_m`
25. `candidate_progress_std_m`
26. `candidate_source_valid_fraction`

The schema is `camp_dp_v25_causal_context_raw_v2`. Context is lifted through
the availability-masked complement construction. Same-tick current signal
phase is permitted; future signal schedules are forbidden. In no-V2I mode,
`phase_remaining_s` is unavailable and masked; its independently reviewed
available count is zero. Identity, split, route/scenario proxies, closed-loop
outcomes, Fresh values, and future fields are excluded from model features.
Scalers and training are train-only. Redundant lifted context means individual
Theta columns do not support isolated causal interpretation.

## 5. Corpus, split, coverage, and retained failures

The corrected training corpus retained its complete planned denominator:
1,500 terminal identities, 1,494 complete identities, six typed
`fixed_dp_candidate_generation_capability_failure` identities, 95,616 complete
snapshots, and zero partial snapshots. Failures contribute zero training rows
but remain in coverage accounting.

Corpus/review roots:
`97a361b2bbb3544e842c9b6d12b3c17b8f63982db3217e9e360643b0cd7b0ffd`
/
`548a5468e585bd39bfbb58ecfd4780e6c78ff88cddb7fef985532639d8dd2c4a`.

Clone-aware train/calibration/B2/B3/B4 overlap checks passed. Fresh B4 used 25
maps, 100 intersections/corridors/routes/semantic blocks, five seeds, 500
paired units, 1,500 balanced arms, and 96,000 planned ticks. Execution and its
independent review accept 500/500 pairs and 1,500/1,500 complete and terminal
arms with full denominator and coverage PASS. Invalid K8 runs, source
ineligibility, typed failures, zero-overlap rows, all-K-high-risk cases, and
failed arms remain governed by the frozen full-denominator policy.

## 6. Static/Scene 9D/14D training and convergence

Static14D and no-V2I Scene14D are primary methods. Static9D and Scene9D are
separately trained paper-subset ablations. All four used the same 95,616 rows,
causal-policy-distillation labels, 14D train scales, source-valid eligibility,
hierarchical weights, and convex solver contract.

| Model | Role | Iterations | Final master gap | Offline wall time (s) |
|---|---|---:|---:|---:|
| CAMP-Static14D | primary | 4 | 0 | 208.129 |
| CAMP-Scene14D | primary | 4 | 8.045300603498617e-7 | 2760.453 |
| CAMP-Static9D | ablation | 2 | 0 | 129.172 |
| CAMP-Scene9D | ablation | 3 | 8.934973414476133e-7 | 1346.148 |

All models ended with CLARABEL `optimal`, zero new cuts, and final master gap at
or below the frozen `1e-6` tolerance. Training/review roots:
`8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9`
/
`ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9`.

## 7. Frozen calibration, guardrails, and NI contract

The frozen calibration compared candidate0, Static14D, and no-V2I Scene14D
over 100 paired units, 300 complete arms, and 19,200 ticks. It is tuning-free,
candidate0-anchored, and not Fresh confirmation. Static14D had calibration
SafetyCost delta -1.5290645589 with corridor-cluster CI95
[-2.8613315699, -0.1967975478]; Scene14D delta was -0.7356063381 with CI95
[-2.3272034503, 0.8559907741]. Both primary methods failed the all-NI gate,
and component guardrails also failed. Therefore calibration itself authorizes
no claim or promotion.

Calibration freeze/review roots:
`295e22adcb6c4840c678f0e1d6ea7725a9786519bf7a856285a008ee0ce4fa80`
/
`8d11c6794925fa99cb24183e0291c4e46f324f5a5ae8460f1bfd8aa8821eb5eb`.

Fresh B4 guardrail and NI decisions are:
`unavailable_due_to_post_exposure_evaluation_fatal`.

## 8. Benchmark A and Fresh Benchmark B

### Legacy Benchmark A

The frozen V24 120-pair holdout remains read-only diagnostic evidence. Mean
SafetyCost delta was -0.014322916666666666, clustered CI95
[-0.06380208333333333, 0.01953125], and Better/Tie/Worse 4/113/3. The original
decision remains `honest_no_claim`. The baseline was candidate0, the fixed-DP
operational default, not native-ranked Top-1.

Evidence anchors:

- training independent review:
  `0b2539ef6c8fa195dfefac6f330775cdc8cb6c0ec7a7ca3aec96d19d0e0b5e6c`;
- paired holdout independent review:
  `43e165aad29a614835430d90f53d0c906079ba01826f1f49d73dbe5de4f3e5bf`;
- evidence/claim root:
  `044defd7e6a0fb03893b7c676182d79587d0bfe8ed9f5638687cc1093fed6808`;
- final review:
  `6203712edf374433ab948781da72c30a399e1cb77e332b15beb7e4f97e883895`.

### Fresh Benchmark B4

The unique three-arm execution completed candidate0, Static14D, and no-V2I
Scene14D for all 500 pairs and 1,500 arms. Execution root:
`e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881`.
Independent execution-review root:
`f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d`.

No frozen evaluation artifact or root exists. All Fresh B4 numerical method
comparisons are:
`unavailable_due_to_post_exposure_evaluation_fatal`.

## 9. Fresh SafetyCost, CI95, B-T-W, and stratification

| Required Fresh B4 output | Status |
|---|---|
| Total SafetyCost, candidate0/Static14D/Scene14D | `unavailable_due_to_post_exposure_evaluation_fatal` |
| collision component and CI95/B-T-W | `unavailable_due_to_post_exposure_evaluation_fatal` |
| near-miss component and CI95/B-T-W | `unavailable_due_to_post_exposure_evaluation_fatal` |
| offroad component and CI95/B-T-W | `unavailable_due_to_post_exposure_evaluation_fatal` |
| red-light component and CI95/B-T-W | `unavailable_due_to_post_exposure_evaluation_fatal` |
| speed component and CI95/B-T-W | `unavailable_due_to_post_exposure_evaluation_fatal` |
| wrong-way component and CI95/B-T-W | `unavailable_due_to_post_exposure_evaluation_fatal` |
| family/tier/map/corridor/signal-source strata | `unavailable_due_to_post_exposure_evaluation_fatal` |
| no-V2I signal-safety result | `unavailable_due_to_post_exposure_evaluation_fatal` |

No value was reconstructed from the execution artifact. The 500/1,500/full
denominator and coverage facts are engineering facts, not estimands or claims.

## 10. Fresh performance/comfort noninferiority

Fresh point estimates, clustered confidence bounds, individual performance
and comfort gates, and the all-NI decision are all:
`unavailable_due_to_post_exposure_evaluation_fatal`.

Safety improvement and noninferiority remain separate frozen gates. Missing
evaluation evidence fails the claim rule closed.

## 11. Ablation and atom-mechanism evidence

The 9D models are separately trained ablations, not extra Fresh arms.
Single-atom/group removal uses diagnostic score subtraction and does not
retrain or establish a closed-loop causal effect.

On the accepted calibration analysis, 9D versus 14D changed 720 Static and
3,836 Scene selections. Leave-group flip counts were: DP-prior 2,901; jerk3
1,577; lane/clearance 505; lateral 306; progress 2,713; signal2 810; speed3
336. These are associations and selection-sensitivity diagnostics only.

Mechanism/review roots:
`79c733159594ce31e204127802971e47f9461187f420c1bf90f29467ce931c07`
/
`214550b755fe520d601ed97138202eb1ba772a8bd851062bb14eb54a2bd87073`.
Post-Fresh B4 mechanism analysis is
`unavailable_due_to_post_exposure_evaluation_fatal`.

## 12. Latency

Accepted calibration latency is descriptive only. Each cell is
mean/median/p95/p99/max milliseconds:

| Stage | candidate0 | Static14D | Scene14D |
|---|---|---|---|
| input materialization | 6.518/6.465/7.075/8.226/112.002 | 6.522/6.481/7.095/7.886/16.616 | 6.503/6.459/7.078/8.217/25.917 |
| DP default | 52.893/52.473/55.174/57.215/427.844 | 52.922/52.545/55.224/57.884/106.477 | 52.975/52.546/55.522/57.856/117.504 |
| additional K8 inference | 364.513/363.612/371.279/390.143/714.781 | 364.738/363.980/371.533/391.557/503.197 | 364.748/363.902/372.275/387.185/616.889 |
| atom | 39.626/26.181/109.307/163.696/232.962 | 39.151/26.111/107.211/162.297/234.801 | 39.674/26.151/109.120/161.207/240.939 |
| context | n/a | n/a | 3.167/3.147/3.318/3.736/7.831 |
| Scene weight | n/a | n/a | 0.275/0.273/0.289/0.339/1.566 |
| selector | n/a | 0.194/0.192/0.205/0.231/1.687 | 0.186/0.185/0.196/0.224/1.020 |
| tracker | 5.768/5.953/6.477/7.569/17.249 | 5.793/5.987/6.511/7.461/19.077 | 5.828/6.004/6.522/8.072/15.787 |
| total planning | 535.842/521.737/615.220/702.048/1411.673 | 550.964/522.500/637.378/1312.534/1916.648 | 552.661/526.704/638.132/1254.223/1806.725 |

Fresh B4 latency summaries were not read from execution and are
`unavailable_due_to_post_exposure_evaluation_fatal`.

## 13. Failure accounting and one-time state

Fresh B2 is permanently closed with one candidate0 raw run and zero complete
pairs. Its closeout/review roots are
`b2c545ff3afa77a3d2c5a7cb91735f9859f1a70286ca3404f2d680b5b6f12363`
/
`6d1d785cd452335cbce135eb4f1ecbf53edcf651a0191a07fe4d67b698d28367`.
Its tombstone identity is
`d07fa8b17bdf00fecd70ccc02584920e38657a8502c74be46f3081ffdd95b606`.

Fresh B3 is permanently closed after a first-arm execution artifact fatal:
one attempted candidate0 arm, zero complete pairs, 1,499 unattempted arms, no
evaluation, and no claim. Closeout/review roots are
`b57f3d23d4d0537b315161c5c5eb1dbd2b1c095c0c0f6ac327b54ba3910b5e83`
/
`b0d87070278ee2f32cbc98420f1b11701db25982a8334c2b0130e679651b3171`.

Fresh B4 completed the execution denominator and then terminated at the
evaluation control gate. Its terminal closeout/review roots are
`a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398`
/
`86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062`.
The evaluation command, run.exit, and stderr evidence SHA256 values are:

- command: `5c2134847ef9a1686d3653d48d0147912ee5abc713cf15f574dc5ec02cc0e304`;
- run.exit: `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865`;
- stderr: `23ffd85aa1c6abf6c04a4bef15469fdd83a1e05a01f53aadbc6d5a4a3a1d8a60`.

The scientific ledger SHA256 is
`c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4`.
Its history is
`exposure_started → full_denominator_formed → terminal_failure`; reason is
`post_exposure_evaluation_control_fatal`; terminal artifact root is the B4
closeout root. Rerun, replacement, new nonce, alternate directory, suffix,
manual outcome recovery, and claim authorization are false.

The terminal machine-readable boundary is:
`evaluation_artifact_created=false`, `evaluation_root=null`,
`evaluation_review_started=false`, `raw_outcome_values_inspected=false`,
`rerun_allowed=false`, and `claim_authorized=false`.

## 14. Final claim boundary

Final V25 decision: `honest_no_claim`.

The following are explicitly unsupported:

- CAMP improves real-world road safety;
- CAMP generalizes broadly to unseen maps or unrestricted traffic;
- candidate0 is native-ranked Top-1;
- CAMP beats native-ranked Diffusion Planner Top-1;
- Static14D or Scene14D passes Fresh SafetyCost, component, CI95, B-T-W,
  stratified, red-light, or NI gates;
- Fresh B4 latency or mechanism conclusions;
- promotion, deployment, online activation, or production readiness.

The only affirmative B4 statements are engineering facts: fixed-DP K=8
immutability, exact one-time execution, 500 complete pairs, 1,500 complete and
terminal arms, 96,000 planned ticks, full denominator, coverage PASS, accepted
execution/review roots, outcome-blind terminal closeout, and permanent CAS
terminal failure.

## 15. Reproducibility and evidence index

The complete path/root register and the 11-item acceptance checklist are in
`docs/diffusion_planner_v25_final_evidence_index.md`. The authoritative live
pointer is the Current V25 section of
`docs/diffusion_planner_current_status.md`; the append-forward terminal tuple is
the EOF of `docs/diffusion_planner_v25_iteration_audit.md`.
