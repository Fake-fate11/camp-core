# Diffusion Planner V25 Iteration Audit

Last verified: 2026-07-17, Asia/Shanghai.

This append-forward audit is the sole current-gate authority for V25. The V24
audit, paired-evaluation config, sealed training corpus, training artifacts,
and 120-pair holdout are frozen read-only evidence. They must not be rewritten,
regenerated, or reopened.

## Terminal Objective and Fixed Scientific Boundary

V25 tests whether the CAMP method transfers as a planner-agnostic selector over
the fixed Diffusion Planner at commit
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. CAMP may only rerank the fixed
per-tick K=8 candidate set using affine scores `score_k = a_k^T w(x)`, with
nonnegative-simplex weights over approved active atoms. It may not generate,
repair, blend, postprocess, or otherwise mutate a trajectory; modify Diffusion
Planner code, config, weights, checkpoint, or request semantics; consume future,
closed-loop outcome, holdout, or identity/proxy features; or weaken the frozen
convex CVaR/L2 master contract. Trajectron++ is the original paper validation
object, while the V25 contribution is transfer to fixed DP rather than a
reproduction of Trajectron++ K=50 or its original data scale.

V25 has exactly six phases:

1. startup and V24 reconciliation;
2. atom/context audit and freeze;
3. scene-conditioned implementation and focused capability pilot;
4. controlled scenario corpus and split;
5. training and calibration;
6. Fresh Benchmark B paired evaluation, one independent review, evidence, and
   honest closeout.

Promotion, deployment, and online activation are outside V25.

## Phase 1: Startup and V24 Reconciliation

Status: complete.

Live reconciliation established all of the following before V25 writes:

- local `main`, `origin/main`, and GitHub `main` are aligned at
  `3f25b697eb99b55e79388c90147b1fc3d18423ef`;
- AutoDL CAMP `/root/autodl-tmp/camp_core` is on `main`, tracked-clean, and at
  the same HEAD and origin/main;
- AutoDL DP `/root/autodl-tmp/Diffusion-Planner` is tracked-clean at the fixed
  commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- no pre-existing V24/V25 training, evaluation, or scenario-generation long
  task was active; the process query matched only its own inspection shell;
- AutoDL free space was `48,674,500,608` bytes, above the 10 GiB floor;
- unrelated local untracked files were left untouched.

The frozen V24 audit and paired-evaluation config SHA256 values are respectively
`cd9a33655e1919182f33256dd07d3bd7a6bdbe7fd8aab1107199859ccf39f228`
and
`9dc0ab9415239211f16e65495362d83c2a11ffe04a96f4ddd2881b12fc193c0f`.
V25 regression coverage pins both byte identities.

## Legacy Benchmark A: Read-Only Scientific Diagnosis

V24 is now named Legacy Benchmark A. It remains useful for regression,
mechanistic diagnosis, and a separate side-by-side table, but it is not fresh
confirmation and its outcome must not tune V25 atoms, weights, thresholds,
margins, or sample composition.

The sealed train corpus contains 375 routes across five seeds, 1,875 retained
route-seed rows, 1,054 complete and 821 retained failures, and 67,796 causal K=8
snapshots. The 14 approved `dp_camp_v10_14d` atoms were all source-available and
train-nonconstant. That proves computability, not utility. The frozen full model
had effective support concentrated on lane_deviation, clearance, and
dp_prior_jerk_excess_cost, with weights
`0.4178605234516141 / 0.5784894895043772 / 0.0036499870440052018`.

The 120-pair holdout result is frozen as `honest_no_claim`: SafetyCost mean
delta was `-0.014322916666666666`, clustered CI95 was
`[-0.06380208333333333, 0.01953125]`, and better/tie/worse was `4 / 113 / 3`.
Among the preregistered primary components, only near_miss_noncollision_rate had
a nonzero primary-component delta; collision, offroad, red-light, speed-limit,
and wrong-way components were exactly tied for all 120 pairs. The comparison
baseline was candidate 0: candidate 0 is the DP operational default and is not
native-ranked Top-1.

Frozen evidence anchors include:

- V24 training independent-review root
  `0b2539ef6c8fa195dfefac6f330775cdc8cb6c0ec7a7ca3aec96d19d0e0b5e6c`;
- V24 paired-holdout independent-review root
  `43e165aad29a614835430d90f53d0c906079ba01826f1f49d73dbe5de4f3e5bf`;
- V24 evidence/claim root
  `044defd7e6a0fb03893b7c676182d79587d0bfe8ed9f5638687cc1093fed6808`;
- final V24 independent-review root
  `6203712edf374433ab948781da72c30a399e1cb77e332b15beb7e4f97e883895`;
- holdout state SHA256
  `f40ae944de12078e5d8f169f7c3b6b451cd0c48a1d0819a165e2cdc1260c1633`,
  with open count `1` and rerun authorization `false`.

V24 also exposes a material comfort warning: the selector's mean/max jerk and
mean lateral-acceleration deltas are not evidence of noninferiority. V25 must
freeze performance and comfort margins before Fresh Benchmark B, report those
gates independently, and retain an honest no-claim if any required safety,
coverage, immutability, zero-overlap, or noninferiority gate fails.

## Phase 2 Entry Contract

The next gate is a train-only, outcome-blind scientific audit of every approved
14D atom and the legal causal-context sources. It must establish engineering
meaning, units, formula, real causal source, finite/nonnegative behavior,
candidate discrimination, zero/saturation/tail/scale behavior, redundancy,
train-only label alignment, route/event stability, monotonicity, and
context-conditioned utility. The paper 9D subset and 14D extension must be
explicit. Exclusion is permitted only through a recorded 9D/14D ablation; no
new atom is admitted without evidence.

The context freeze may use ego kinematics, route curvature/lane width/speed
limit, current traffic-light state/distance, neighbor relative position/
velocity/TTC, and K=8 dispersion/consensus/source-valid count. Future state,
closed-loop outcome, ground-truth holdout, and map/route/scenario/split identity
or proxies remain forbidden.

current_v25_status=v25_startup_v24_reconciliation_complete
current_v25_startup_base_head=3f25b697eb99b55e79388c90147b1fc3d18423ef
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
local_origin_github_aligned=true
autodl_camp_aligned=true
autodl_dp_clean=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=48674500608
current_v25_phase=1_startup_v24_reconciliation
next_work_target=v25_atom_context_audit_and_freeze

## Phase 2: Atom and Causal-Context Audit/Freeze

Status: passed with a required phase 3 raw-context capability gate.

The authoritative train-only audit ran at CAMP source HEAD
`fe356ef7a441dd75c1d524105117e01fb6665223` against clean fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. It complete-sealed the frozen
V24 merged corpus, atom freeze, causal labels, and their independent reviews;
then it rehashed and read all 67,796 snapshots and 542,368 candidate rows. The
222 route identities with at least one snapshot were used only for grouped
stability diagnostics, never as features. V24 holdout, closed-loop outcomes,
future fields, calibration, and Fresh Benchmark B remained unopened.

The first successful numeric artifact at source HEAD `927b033f...` exposed a
precision-only wording defect in the canonical `dp_prior_jerk_excess_cost`
contract: it called candidate 0 a DP Top-1 semantic. That artifact remains
immutable but is superseded. The formula and all numeric results were unchanged;
the canonical source now says candidate 0 DP operational-default reference and
that native ranking is not claimed. The corrected authoritative artifact/root
are:

`/root/autodl-tmp/camp_dp_v25_atom_context_audit_20260717T114320CST`
/
`5135bebe8a78942fb91ec72957db5e0386b15f99bcf4e8bca35be2a98d00241c`.

Independent manifest rehash, root recomputation, and the candidate-0 wording
check passed. Runtime was `16.10695989476517` seconds and free disk was
`48,673,611,776` bytes.

### 14D Engineering Contract and 9D Correspondence

The paper-consistent `camp_legacy_v1_9d` subset is exactly indices 0 through 8.
The DP extension is indices 9 through 13. All per-candidate coefficients are
fixed before scoring, finite, nonnegative, and independent of `w`, selection,
closed-loop outcomes, and GT future.

| Atom | Set | Unit | Engineering meaning / formula | Real causal source |
|---|---|---|---|---|
| jerk_early | 9D | m^2/s^5 | `dt * sum(||third_difference(xy)/dt^3||^2)` over first third | current fixed-DP K=8 candidate tensor |
| jerk_late | 9D | m^2/s^5 | same squared-jerk integral after first third | current fixed-DP K=8 candidate tensor |
| jerk_full | 9D | m^2/s^5 | same squared-jerk integral over full horizon | current fixed-DP K=8 candidate tensor |
| rms_acceleration | 9D | m/s^2 | RMS norm of second differences | current fixed-DP K=8 candidate tensor |
| speed_limit_margin_0_0 | 9D | m^2/s | squared speed excess above current route limit | candidate tensor + current route speed rules |
| speed_limit_margin_0_5 | 9D | m^2/s | squared speed excess above `limit - 0.5 m/s` | candidate tensor + current route speed rules |
| speed_limit_margin_1_0 | 9D | m^2/s | squared speed excess above `limit - 1.0 m/s` | candidate tensor + current route speed rules |
| lane_deviation | 9D | m^2*s | squared excess outside measured left/right lane width | candidate tensor + current route centerline/boundaries |
| clearance | 9D | m^2*s | squared shortfall from obstacle safety distance | candidate-specific same-call DP neighbor predictions + current static obstacles |
| progress_shortfall | 14D extension | m | shortfall from best current feasible K=8 route progress | current K=8 set + current route + current feasibility mask |
| planned_red_light_cost | 14D extension | DP reward cost | hinge of fixed-DP planned red-light reward | current candidate set + current route-aligned signal phase |
| planned_lateral_acceleration_cost | 14D extension | m/s^2 | mean absolute candidate lateral acceleration | current fixed-DP K=8 candidate tensor |
| red_stopping_margin_cost | 14D extension | m^2/s | speed excess over current red-signal stopping envelope | candidate tensor + current red route points/directions |
| dp_prior_jerk_excess_cost | 14D extension | m/s^3 | jerk excess over candidate 0 | candidate tensor + candidate 0 operational-default identity; no native-rank claim |

### Train-Only Empirical Audit

`variable` is the fraction of snapshots with K=8 cross-candidate range above
`1e-12`; saturation is the fraction clipped at the frozen normalized value 10;
`rho` is deterministic-sample Spearman correlation with the frozen causal
train-only label cost. Scale remains the frozen V24 train p95/floor value.

| Atom | zero rate | variable | p95 / scale | p99 | saturation | label rho | route corr median |
|---|---:|---:|---:|---:|---:|---:|---:|
| jerk_early | 0.000000 | 1.000000 | 2481.76 / 2481.76 | 10508.64 | 0.000011 | 0.119445 | 0.028745 |
| jerk_late | 0.000000 | 1.000000 | 12392.16 / 12392.16 | 74859.11 | 0.002207 | 0.051001 | 0.004015 |
| jerk_full | 0.000000 | 1.000000 | 14971.37 / 14971.37 | 85458.72 | 0.001261 | 0.050884 | 0.006550 |
| rms_acceleration | 0.000000 | 1.000000 | 2.64498 / 2.64498 | 6.00707 | 0.000000 | 0.028518 | 0.037339 |
| speed_limit_margin_0_0 | 0.081389 | 0.939524 | 112.103 / 112.103 | 170.296 | 0.000000 | 0.549459 | 0.153544 |
| speed_limit_margin_0_5 | 0.026390 | 0.987123 | 143.208 / 143.208 | 208.604 | 0.000000 | 0.549611 | 0.166803 |
| speed_limit_margin_1_0 | 0.008503 | 0.997581 | 178.296 / 178.296 | 250.773 | 0.000000 | 0.546941 | 0.160368 |
| lane_deviation | 0.845413 | 0.169656 | 226.100 / 226.100 | 4375.79 | 0.019367 | 0.456745 | 0.520106 |
| clearance | 0.914991 | 0.106083 | 4.44735 / 4.44735 | 13.4079 | 0.000127 | 0.314403 | 0.734704 |
| progress_shortfall | 0.175462 | 0.950381 | 5.27309 / 5.27309 | 13.0541 | 0.000472 | -0.021836 | 0.064010 |
| planned_red_light_cost | 0.995145 | 0.005546 | 0 / 1e-6 | 0 | 0.004855 | 0.118172 | 0.962447 |
| planned_lateral_acceleration_cost | 0.000000 | 1.000000 | 1.49486 / 1.49486 | 3.66244 | 0.000000 | -0.084497 | -0.028914 |
| red_stopping_margin_cost | 0.995735 | 0.005635 | 0 / 1e-6 | 0 | 0.004265 | 0.112280 | 0.962184 |
| dp_prior_jerk_excess_cost | 0.505277 | 0.995457 | 1.80487 / 1.80487 | 8.34853 | 0.002932 | 0.085073 | 0.066846 |

The audit found 4 high-redundancy pairs at absolute Spearman at least 0.98:
`jerk_late/jerk_full` and all three pairings among the speed-limit-margin
atoms. This is disclosed evidence for the required 9D/14D ablations, not
authority to silently remove an atom. Lane deviation and clearance are sparse
but show material route-level positive alignment. Planned red-light and red
stopping-margin atoms are active in only about 0.56% of train snapshots; they
remain explicit because V25 controlled signal-phase scenarios are intended to
test their coverage. Weak or negative marginal label correlation is not treated
as a formula failure because the causal label is multicomponent and includes a
finite physical-risk penalty.

### Frozen Causal Context Schema

The schema contains 26 raw features, grouped as:

- ego: speed, longitudinal/lateral acceleration, and yaw rate;
- route/rules: mean/max absolute curvature, minimum/median lane width, minimum
  and current speed limit;
- current signal: red/yellow/green/unknown one-hot, route distance, and phase
  time remaining;
- current neighbors: count, minimum distance/TTC/lateral gap, and closing speed;
- fixed K=8 set: consensus RMS median/MAD, endpoint dispersion, progress
  dispersion, and source-valid fraction.

Every source is an existing current request/state, current static route/rule,
current traffic-light state, current neighbor history, or the fixed DP K=8
tensor. Future, closed-loop outcome, GT holdout, private DP latent, and
map/route/scenario/split/seed identity or proxies are forbidden.

Train-only q05/q95 scaling clips each raw feature to `[0,1]`. The frozen
53-dimensional complement-lift is one constant plus `[u_j, 1-u_j]` for each of
26 raw features, divided by its constant sum. Every column of `Theta` is
constrained to the nonnegative simplex, so `w(x)=Theta*phi(x)` is a
nonnegative simplex for every bounded `phi` without softmax or a neural head.
For fixed `phi_i` and atoms, scores remain affine and the CVaR/L2 master remains
convex.

The V24 sealed snapshots contain no raw context. The only directly available
context field candidate_source_valid_fraction was exactly 1.0 for every
snapshot and therefore has zero utility variation. Context-conditioned utility
was not estimated from IDs, source-stratum labels, or V24 holdout. A focused
phase 3 outcome-blind capability pilot must prove source completeness,
variation, finite behavior, monotonicity, and request-only construction before
scene-conditioned training is authorized.

current_v25_status=v25_atom_context_audit_freeze_passed_phase3_context_capability_required
current_v25_source_head=fe356ef7a441dd75c1d524105117e01fb6665223
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_atom_context_audit_20260717T114320CST
current_v25_artifact_root_sha256=5135bebe8a78942fb91ec72957db5e0386b15f99bcf4e8bca35be2a98d00241c
current_v25_atom_schema=dp_camp_v10_14d
current_v25_paper_subset=camp_legacy_v1_9d
current_v25_context_schema=camp_dp_v25_causal_context_raw_v1
current_v25_context_raw_feature_count=26
current_v25_phi_dimension=53
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
current_v25_v24_holdout_read=false
current_v25_fresh_benchmark_b_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=48673611776
current_v25_phase=2_atom_context_audit_and_freeze
next_work_target=v25_scene_conditioned_implementation_and_context_capability_pilot
