# V25 CAMP over Fixed Diffusion Planner K=8

## Final Corrected-Evaluation Auditable Report

Date: 2026-07-25 (Asia/Shanghai)

Scientific disposition: `honest_no_claim_under_frozen_preregistered_all_gate`

Fresh execution reused: `true`

Fresh execution rerun: `false`

## 1. Executive decision

The unique Fresh B4 execution over the unchanged Diffusion Planner K=8
candidate set completed 500/500 paired units, 1,500/1,500 complete and terminal
arms, and 96,000 planned ticks. Its execution and independent execution review
remain immutable and accepted.

The first frozen evaluation control failed because it incorrectly required the
release pointer HEAD to equal the execution implementation-source HEAD. The
2026-07-25 prospective user decision authorized an outcome-blind evaluator
policy correction that recognizes the already-sealed dual-HEAD contract. It
did not authorize a new Fresh execution, a new nonce, changed data, changed
models, or changed scientific rules. The old fatal control, closeout, review,
and `terminal_failure` scientific ledger remain intact as a superseded
engineering diagnostic.

A separate, exclusively keyed continuation authority and CAS then permitted
one deterministic evaluation of the preserved denominator. The corrected
evaluation and its literal-oracle independent review passed and sealed:

- corrected evaluation root:
  `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f`;
- corrected evaluation-review root:
  `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459`;
- continuation terminal state: `independently_reviewed_terminal`.

Both Static14D and no-V2I Scene14D reduced mean total SafetyCost relative to
candidate0, with paired clustered CI95 bounds below zero. Neither method passes
the frozen scientific claim rule: component guardrails and the complete
performance/comfort noninferiority gate do not both pass. Therefore:

- `Static14D safety_improvement_claim_passed=false`;
- `Scene14D safety_improvement_claim_passed=false`;
- `red_light_improvement_claim_passed=false` for both;
- no real-world, broad unseen-map, native-ranked Top-1, promotion, deployment,
  online-activation, or production-readiness claim is authorized.

CAMP remained a selector/reranker only. It did not generate, repair, blend,
mask, mutate, or replace fixed-DP candidates or trajectories.

## 2. Immutable authority and provenance

| Role | Frozen value |
|---|---|
| Execution implementation source | `7be93df20deee03587b9898e8560909662df972c` |
| Release pointer HEAD | `06d3a1f3a37061f93f5c9788312ae59d1356d126` |
| Correction-authority implementation HEAD | `dddca1c64f9e03ca515ffb4e06724b0842e33135` |
| Corrected-evaluation role HEAD | `62079a71920f218f7a5269c6c01e6e3700db3723` |
| Independent-review role HEAD | `6e43a625ca0a74dea569926d18fd26f0f7b552c3` |
| Fixed Diffusion Planner HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Execution critical manifest | `f3b707d480b30e1d37d2c10355d8a824df4cff8230af7d78d803dd4504ef6c2b` |
| 24-role authority contract | `3254191ef3ff10e8ab0dda5985acb3589bb44df8534f51a8a033bca26e01c653` |
| Holdout identity | `5f2f8e2c2eb90927ec485a8d0baa3935b155e82d90b04fa3d456fc845cd8464a` |
| Experiment protocol | `aa79576f8ac487e2ce197c481d57f9c5d350a41d9522096975786207ef76785f` |
| Execution plan | `41442dd7d71552972d737d9a9e3d56e9827f864e0c06e11c57487f651206dee0` |
| Unique B4 nonce | `8680c1b19ce0620b7dc2ec9453ffde0da024d3443e6d6307fc41e87f3dad3b42` |

The source-to-pointer difference is restricted to the frozen three-file
pointer-only allowlist. Evaluation-role provenance is separate from execution
provenance; no new evaluator manifest is substituted for the historical
execution manifest.

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
rows: 14 PASS, 0 WARN, 0 FAIL. Numerical atom-delta rank was 14 and effective
rank was 3.1832077907871783. Relative to the 14D causal-label reference, the 9D
prefix changed 32,204 selected indices, weighted rate 0.34094138781638783.
These are computability and association findings within controlled support,
not isolated causal safety effects.

Atom audit/review roots:
`4dc98d9a812403148f30e2041358fbd79c967e3c8581a9d8569dc362f71d8e7e`
and
`149995eacbcdf21201934bbf428ca5d8871f6c3085b4ab5e90db1d8ef78753bc`.

## 4. Twenty-six-dimensional context and leakage audit

The ordered raw context is:

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

The schema is `camp_dp_v25_causal_context_raw_v2`, lifted through an
availability-masked complement construction. Same-tick current signal phase is
permitted; future schedules are forbidden. In no-V2I mode,
`phase_remaining_s` is unavailable and masked, with independently reviewed
available count zero. Identity, split, route/scenario proxies, closed-loop
outcomes, Fresh values, and future fields are excluded from model features.
Scalers and training are train-only. Redundant lifted context prevents isolated
causal interpretation of individual Theta columns.

## 5. Corpus, split, coverage, and failure retention

The corrected training corpus retained the complete planned denominator:
1,500 terminal identities, 1,494 complete identities, six typed
`fixed_dp_candidate_generation_capability_failure` identities, 95,616 complete
snapshots, and zero partial snapshots. Failures contribute zero training rows
but remain in coverage accounting.

Corpus/review roots:
`97a361b2bbb3544e842c9b6d12b3c17b8f63982db3217e9e360643b0cd7b0ffd`
and
`548a5468e585bd39bfbb58ecfd4780e6c78ff88cddb7fef985532639d8dd2c4a`.

Clone-aware train/calibration/B2/B3/B4 overlap checks passed. Fresh B4 used 25
maps, 100 intersections/corridors/routes/semantic blocks, five seeds, 500
paired units, 1,500 arms, and 96,000 ticks. The frozen plan guarantees arm
balance overall and within each independent inference cluster; it does not
claim exact balance within every scenario family. The pre-artifact arm-order
repair enforced this static contract without changing any execution row. The
sealed evaluation retained the identical 500-pair set and all failed rows,
used no SafetyCost imputation, and accepted 500 complete arms for each of
candidate0, Static14D, and Scene14D. There were zero fixed-DP capability
failures and zero source-ineligible B4 arms.

## 6. Static/Scene 9D/14D training and convergence

Static14D and no-V2I Scene14D are primary methods. Static9D and Scene9D are
separately trained paper-subset ablations, not additional Fresh arms. All four
used the same 95,616 rows, causal-policy-distillation labels, 14D train scales,
source-valid eligibility, hierarchical weights, and convex-solver contract.

| Model | Role | Iterations | Final master gap | Offline wall time (s) |
|---|---|---:|---:|---:|
| CAMP-Static14D | primary | 4 | 0 | 208.129 |
| CAMP-Scene14D | primary | 4 | 8.045300603498617e-7 | 2760.453 |
| CAMP-Static9D | ablation | 2 | 0 | 129.172 |
| CAMP-Scene9D | ablation | 3 | 8.934973414476133e-7 | 1346.148 |

All four ended with CLARABEL `optimal`, zero new cuts, and final master gap at
or below the frozen `1e-6` tolerance. Training/review roots:
`8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9`
and
`ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9`.

## 7. Frozen calibration and claim rule

The calibration freeze compared candidate0, Static14D, and no-V2I Scene14D
over 100 paired units, 300 complete arms, and 19,200 ticks. It was tuning-free,
candidate0-anchored, and did not consume Fresh results. Static14D calibration
SafetyCost delta was -1.5290645589 with corridor-cluster CI95
[-2.8613315699, -0.1967975478]; Scene14D delta was -0.7356063381 with CI95
[-2.3272034503, 0.8559907741]. Both failed the all-NI gate and component
guardrails. Calibration authorized neither claim nor promotion.

Freeze/review roots:
`295e22adcb6c4840c678f0e1d6ea7725a9786519bf7a856285a008ee0ce4fa80`
and
`8d11c6794925fa99cb24183e0291c4e46f324f5a5ae8460f1bfd8aa8821eb5eb`.

The frozen Fresh claim rule requires denominator and immutability gates, total
SafetyCost improvement, all component guardrails, and all performance/comfort
NI gates. It was not modified after exposure.

## 8. Benchmark A and Fresh Benchmark B4

### Legacy Benchmark A

The frozen V24 120-pair holdout remains read-only diagnostic evidence. Mean
SafetyCost delta was -0.014322916666666666, clustered CI95
[-0.06380208333333333, 0.01953125], and Better/Tie/Worse 4/113/3. Its decision
remains `honest_no_claim`. Candidate0 was the fixed-DP operational default, not
native-ranked Top-1.

Evidence/claim root:
`044defd7e6a0fb03893b7c676182d79587d0bfe8ed9f5638687cc1093fed6808`;
final review:
`6203712edf374433ab948781da72c30a399e1cb77e332b15beb7e4f97e883895`.

### Fresh Benchmark B4

The unique three-arm execution completed candidate0, Static14D, and no-V2I
Scene14D for all 500 pairs and 1,500 arms. Execution/review roots:
`e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881`
and
`f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d`.

The corrected evaluation reused that exact sealed denominator. No Fresh arm,
candidate, trajectory, identity, protocol, plan, nonce, split, denominator, or
claim rule was regenerated or altered.

## 9. Fresh SafetyCost, components, CI95, and B-T-W

Negative deltas favor CAMP. Confidence intervals are paired and clustered over
100 corridor clusters with 500 observations.

| Method | Mean total delta vs candidate0 | CI95 | Better/Tie/Worse | Total gate |
|---|---:|---|---:|---|
| Static14D | -2.5299346354001058 | [-3.551884242964027, -1.5079850278361844] | 280/81/139 | pass |
| Scene14D | -1.2135901546149832 | [-2.132750489352197, -0.29442981987776917] | 227/111/162 | pass |

Mean total SafetyCost was 24.034851910817732 for candidate0,
21.504917275417625 for Static14D, and 22.821261756202745 for Scene14D.

### Six-component guardrails

| Method | Component | Mean delta | CI95 | Better/Tie/Worse | Guardrail |
|---|---|---:|---|---:|---|
| Static14D | collision | -0.002 | [-0.005968433903017364, 0.001968433903017364] | 1/499/0 | fail |
| Static14D | near_miss | -0.009 | [-0.01564292998, -0.00235707002] | 135/329/36 | pass |
| Static14D | offroad | -0.0005625 | [-0.00843021909, 0.00730521909] | 194/141/165 | fail |
| Static14D | red_light | -0.07 | [-0.10258571006, -0.03741428994] | 36/463/1 | pass |
| Static14D | speed | -0.01286846354 | [-0.01990528962, -0.00583163746] | 76/410/14 | pass |
| Static14D | wrong_way | 0 | [0, 0] | 0/500/0 | pass |
| Scene14D | collision | -0.002 | [-0.005968433903017364, 0.001968433903017364] | 1/499/0 | fail |
| Scene14D | near_miss | -0.0021875 | [-0.0055613789, 0.0011863789] | 82/372/46 | fail |
| Scene14D | offroad | -0.0031875 | [-0.0088547619, 0.0024797619] | 182/171/147 | fail |
| Scene14D | red_light | -0.03 | [-0.0578476700, -0.00215232999] | 22/471/7 | pass |
| Scene14D | speed | -0.00279651546 | [-0.00498177697, -0.00061125395] | 52/417/31 | pass |
| Scene14D | wrong_way | 0 | [0, 0] | 0/500/0 | pass |

Candidate0/Static14D/Scene14D component means respectively were:

- collision: 0.002 / 0 / 0;
- near miss: 0.122625 / 0.113625 / 0.1204375;
- offroad: 0.41509375 / 0.41453125 / 0.41190625;
- red light: 0.456 / 0.386 / 0.426;
- speed: 0.06267269 / 0.04980423 / 0.05987618;
- wrong way: 0 / 0 / 0.

Because not every component guardrail passed, the all-component gate failed for
both methods.

### Event-family stratification

| Family | Scene14D delta (CI95), B/T/W | Static14D delta (CI95), B/T/W |
|---|---|---|
| blocked | -2.89385 ([-9.13294, 3.34524]), 24/4/22 | -5.81910 ([-10.87116, -0.76704]), 30/3/17 |
| cut-in | 0.66793 ([-1.10392, 2.43978]), 25/14/16 | -5.16447 ([-8.83492, -1.49401]), 37/8/10 |
| lead | -3.84644 ([-8.54074, 0.84786]), 32/6/17 | -7.67575 ([-12.70848, -2.64302]), 39/4/12 |
| narrow | -3.26959 ([-8.46393, 1.92476]), 26/13/11 | -2.54691 ([-7.49970, 2.40588]), 30/4/16 |
| naturalistic | 0.037704 ([-0.050877, 0.126286]), 43/46/36 | 0.188527 ([-0.112328, 0.489381]), 35/41/49 |
| pedestrian | 0.143555 ([-0.413207, 0.700317]), 20/9/26 | -0.306279 ([-0.676867, 0.064308]), 33/8/14 |
| redlight | -0.520077 ([-0.852210, -0.187943]), 30/12/13 | -0.685920 ([-1.201197, -0.170644]), 37/6/12 |
| unprotected | -1.96017 ([-4.47858, 0.558244]), 27/7/21 | -1.989993 ([-4.206856, 0.226871]), 39/7/9 |

Strata are descriptive diagnostics under the frozen multiplicity policy, not
independent promotion claims.

### No-V2I signal diagnostics

No V2I arm was authorized or run; `phase_remaining_s` was not consumed.
Static14D red-light violation delta was -0.00198143116, CI95
[-0.00289781676, -0.00106504556], B/T/W 36/245/1. Scene14D was
-0.00084918478, CI95 [-0.00163706453, -0.0000613050], B/T/W 22/253/7.
Crossing-speed deltas were -0.97385284 for Static14D and -0.46333794 for
Scene14D. False-stop-on-green delta was zero for both. Stop-margin harm deltas
were -1.27928712 and -0.3782713 respectively. Despite favorable red-light
diagnostics, the preregistered red-light claim requires the total claim, which
failed; both red-light claims are false.

## 10. Fresh performance/comfort noninferiority

The table reports method-minus-candidate0 delta, one-sided upper bound, frozen
margin, and decision.

| Method | Metric | Delta | Upper bound | Margin | NI |
|---|---|---:|---:|---:|---|
| Static14D | completion | 0.0080503 | 0.0104983 | 0.02 | pass |
| Static14D | max jerk | -0.373166 | 0.202832 | 1.0 | pass |
| Static14D | max lateral acceleration | 0.155932 | 0.203232 | 0.3 | pass |
| Static14D | max deceleration | approximately 0 | 0.0002986 | 0.5 | pass |
| Static14D | mean jerk | 3.067968 | 3.231892 | 0.2 | fail |
| Static14D | mean lateral acceleration | 0.0002501 | 0.0070538 | 0.1 | pass |
| Static14D | progress | 1.02038 | 1.331338 | 1.0 | fail |
| Scene14D | completion | 0.00285112 | 0.00429947 | 0.02 | pass |
| Scene14D | max jerk | -0.254293 | 0.269061 | 1.0 | pass |
| Scene14D | max lateral acceleration | 0.13913 | 0.18754 | 0.3 | pass |
| Scene14D | max deceleration | -0.0001264 | 0.0000834 | 0.5 | pass |
| Scene14D | mean jerk | 2.688594 | 2.836671 | 0.2 | fail |
| Scene14D | mean lateral acceleration | 0.005396 | 0.009971 | 0.1 | pass |
| Scene14D | progress | 0.35908 | 0.543477 | 1.0 | pass |

Mean jerk fails NI for both methods; progress additionally fails for
Static14D. Thus the all-NI gate is false for both.

## 11. Ablation and atom-mechanism evidence

The 9D models are separately trained ablations. Single-atom/group removal is
diagnostic score subtraction rather than retraining and does not establish a
closed-loop causal effect. In accepted calibration analysis, 9D versus 14D
changed 720 Static and 3,836 Scene selections. Leave-group flip counts were:
DP-prior 2,901; jerk3 1,577; lane/clearance 505; lateral 306; progress 2,713;
signal2 810; speed3 336.

Mechanism/review roots:
`79c733159594ce31e204127802971e47f9461187f420c1bf90f29467ce931c07`
and
`214550b755fe520d601ed97138202eb1ba772a8bd851062bb14eb54a2bd87073`.
All mechanism language is associative.

## 12. Controlled benchmark latency

Values are mean/p95/p99/max milliseconds. Each arm has 500 runs and 32,000
ticks.

| Arm | Total planning | Additional K8 generation | Atom | Context | Scene weight | Selector |
|---|---|---|---|---|---|---|
| candidate0 | 68.8009/72.2326/75.8978/518.258 | n/a | n/a | n/a | n/a | 0 |
| Static14D | 531.7828/607.2238/755.5456/993.905 | mean 358.9905 | mean 35.3676 | n/a | n/a | mean 0.199182 |
| Scene14D | 536.4562/613.8304/755.1553/1072.831 | mean 359.5578 | mean 35.9324 | mean 3.16974 | mean 0.284847 | mean 0.190547 |

Candidate0 default-DP mean latency was 51.9854 ms. These are controlled
benchmark timings, not deployment, online-activation, or real-time production
claims.

## 13. Failure accounting and continuation state

Fresh B2 is permanently tombstoned with one candidate0 raw run and zero
complete pairs. Closeout/review roots:
`b2c545ff3afa77a3d2c5a7cb91735f9859f1a70286ca3404f2d680b5b6f12363`
and
`6d1d785cd452335cbce135eb4f1ecbf53edcf651a0191a07fe4d67b698d28367`;
tombstone identity
`d07fa8b17bdf00fecd70ccc02584920e38657a8502c74be46f3081ffdd95b606`.

Fresh B3 is permanently closed after a first-arm execution-artifact fatal:
one attempted candidate0 arm, zero complete pairs, 1,499 unattempted arms, no
evaluation, and no claim. Closeout/review roots:
`b57f3d23d4d0537b315161c5c5eb1dbd2b1c095c0c0f6ac327b54ba3910b5e83`
and
`b0d87070278ee2f32cbc98420f1b11701db25982a8334c2b0130e679651b3171`.

Fresh B4 first completed its full denominator. The original evaluation control
then failed with
`ValueError: holdout execution/evaluation role HEAD drifted`. Its immutable
closeout/review roots remain
`a97af4901ac0627ece1203eaac130f8bf2f10caf6b8bee523555582b2ff3d398`
and
`86aa7ca12ae8cfa4a655fc55022761a78ac54a3a22ef32a750df9c7eb75d0062`.
The old scientific ledger SHA is
`c3db4fb56f28efda7e3feb762ab0f01954f09983813b442f0a31e7730fbe72e4`;
it remains `terminal_failure` with history
`exposure_started -> full_denominator_formed -> terminal_failure`, reason
`post_exposure_evaluation_control_fatal`. It was never rewritten.

The prospective correction authority is additive:

- authority/review roots:
  `b468b5ec04379327db6ca8f736bc2ef249d7b65594891cda1e135bffbbd806f1`
  and
  `c47ae78fdb7b5df9f050b775c3691b3abe562b7508fad42960c1ea5c9c8afc55`;
- pre-artifact repair/review roots:
  `f3696e993abd1d28fb2d194234d1b48c3a9b2fef851b7fae6460e2e62b05c027`
  and
  `e622220157c46ae2a95173ad63699fd0afad03d24a6514edae92c28f746f3583`;
- continuation ledger:
  `/root/autodl-tmp/.camp_dp_v25_fresh_b4_evaluation_continuation_cas/625fee32ec6600d7d17345ffa5c096f3585ff91537a93f67a66dcda4335f6144.json`;
- final continuation ledger SHA256:
  `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392`;
- continuation history:
  `authorized_from_preserved_denominator -> evaluation_started -> evaluation_artifact_formed -> independently_reviewed_terminal`.

Before correction authority, `raw_outcome_inspected_before_authority=false`.
After authority, only the corrected evaluator consumed the sealed rows to
produce the frozen artifact. Fresh execution was not rerun.

## 14. Final claim boundary

Final V25 decision:
`honest_no_claim_under_frozen_preregistered_all_gate`.

Supported engineering/method statements:

- CAMP reranks/selects only the unchanged fixed-DP K=8 candidates;
- the unique Fresh B4 execution completed 500 pairs, 1,500 arms, and 96,000
  ticks with full denominator and coverage PASS;
- corrected evaluation deterministically reused the preserved denominator and
  passed independent review;
- both primary methods reduced mean total SafetyCost in this controlled
  benchmark, but neither passed all frozen component and NI gates.

Explicitly unsupported:

- a Fresh scientific benefit claim for Static14D or Scene14D;
- a red-light improvement claim;
- real-road safety or broad unseen-map generalization;
- candidate0 as native-ranked Top-1 or CAMP beating native-ranked Top-1;
- causal interpretation of atom-mechanism associations;
- promotion, deployment, online activation, or production readiness.

## 15. Reproducibility

The complete path/root register and 11-item acceptance checklist are in
`docs/diffusion_planner_v25_final_corrected_evidence_index.md`. The
authoritative status tuple is in the named top Current V25 section of
`docs/diffusion_planner_current_status.md` and, field for field, at the EOF of
`docs/diffusion_planner_v25_iteration_audit.md`. The earlier
`docs/diffusion_planner_v25_final_honest_no_claim_report.md` remains preserved
as the superseded engineering-diagnostic closeout; it is not silently rewritten
as though the original fatal never occurred.

Focused evidence is explicitly layered: the evaluator/reviewer implementation
suite passed 101/101 at root
`7c01cd9ea5176da889186d3beffec38d6e9ab5d04e40d3fa2b4a47eea8713437`;
the post-publication final-package suite passed 102/102 at root
`58c241ec562a570c72f3d96bc2b85e32079f367e9d9d2e30e2835b20e49f8205`.
