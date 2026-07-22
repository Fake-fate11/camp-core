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

## Phase 3: Scene-Conditioned CAMP and Capability Pilot

Phase 3 implemented the frozen causal-context path without changing Diffusion
Planner, any candidate tensor, or any trajectory. Commit
`d052f597254761c59ab55b53d858c1230e22a0dc` adds a strict
`context_simplex` selector alongside the unchanged legacy `static` and
`linear` modes. The online map is exactly `w(x)=Theta*phi(x)`: there is no
bias, softmax, neural adapter, private DP latent, or runtime projection. The
53-dimensional complement lift is nonnegative and sums to one, and every
column of Theta is a nonnegative simplex. Thus every admissible current-tick
context produces weights on the approved active atoms that are nonnegative and
sum to one, while each fixed-candidate score remains `a_k^T*w(x)`.

The raw materializer consumes only the exact fixed-DP causal input schema, the
current fixed K=8 candidate tensor, the current signal-schedule remainder, and
the current source-valid mask. Ego lateral acceleration is the causal
`speed*yaw_rate` value. Route curvature, widths, limits, and signal route
distance come from current route geometry/rules. Neighbor distance, TTC,
closing speed, and lateral gap come from current neighbor history; an empty
neighbor set uses fixed finite 100 m / 30 s sentinels. Candidate consensus,
endpoint dispersion, route-progress dispersion, and source-valid fraction are
computed before selection. Missing signal timing maps to zero but is explicitly
marked source-incomplete; phase-3 controlled requests supplied it, so every
registered source was complete. No identity-like input is accepted.

The paper-consistent finite-candidate master was specialized to the frozen
lift. A deterministic convex Bradley--Terry warmup uses only train-split causal
oracle pair preferences and column-simplex projected-gradient steps with
backtracking; it does not use GT futures, closed-loop outcomes, or holdout.
The authoritative master then optimizes CVaR plus L2 terms with per-column
simplex constraints and exact finite-candidate cuts. It requires strict
CLARABEL `OPTIMAL`, has no solver fallback, and checks the true restricted-
master gap against `1e-6` for at most 20 cut iterations. The warmup is only an
initialization/convex anchor; it is not a neural shortcut and does not replace
the master.

AutoDL used Python 3.12, CVXPY 1.6.7, Torch 2.8.0, and CLARABEL. The focused
suite, including legacy linear-checkpoint compatibility and the phase-2/pointer
contracts, finished `17 passed`. The fixed DP worktree remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The authoritative capability artifact is:

`/root/autodl-tmp/camp_dp_v25_context_capability_pilot_d052f597_20260717T130229CST`

with root SHA256
`d2b88b7f6d91b9b7465a37d8bb00c1b46e8ef1a5fd1bef30e97be712caafbf08`.
A separate manifest recomputation matched. Its 35 outcome-blind
current-request cases passed all 29 registered checks: all 26 raw features
varied, all registered one-at-a-time monotonic checks passed, every source was
complete, raw/phi/weight values were finite, every phi/weight row was a
simplex, context weights varied, affine score mixing held to `1e-12`, and all
candidate tensors were byte-identical before/after materialization.

The artifact's q05/q95 scaler and deterministic Theta are capability probes,
not a trained or calibrated model. This phase does not establish
scene-conditioned utility or safety improvement. It did not read V24 holdout,
open Fresh Benchmark B, train, calibrate, evaluate closed-loop outcomes,
promote, deploy, or activate anything. Phase 4 may now audit the official TIER
IV source, freeze an outcome-blind deterministic scenario grammar/split, and
run its bounded coverage pilot; model training remains closed until that corpus
gate passes.

## Phase 4: Controlled Scenario Corpus and Split Freeze

The official-source audit is pinned to TIER IV `scenario_simulator_v2` commit
`e22f01093fa6516c0552549ada302270329c59a4`. It checked the maintained speed,
lane-change, explicit-route, pedestrian-trajectory, and traffic-signal action
examples. The official implementation does not provide a usable
`RandomRouteAction`/random route strategy for this contract. V25 therefore
uses explicit Lanelet2 routes and a deterministic native-runner materializer
with semantically corresponding current-state actor and signal schedules. It
does not change DP code, configuration, weights, checkpoints, requests, any
candidate tensor, or a selected trajectory.

The frozen grammar has easy, borderline, and high-risk parameter tiers for all
seven preregistered families: lead-vehicle hard brake; cut-in/merge;
pedestrian/cyclist crossing including occlusion; unprotected turn/oncoming
conflict; red-light phase timing; blocked lane/static obstacle; and narrow
encounter. Every case fixes explicit route placement, headway/TTC, speed,
deceleration, trigger time, signal phase where available, and seed namespace
before outcomes. Scripted actors are exogenous and excluded from DP control;
signal schedules may only overwrite rows already mapped as traffic signals.
The adapter consumes no candidate, selected trajectory, future, outcome, or
identity feature.

The preflight artifact
`/root/autodl-tmp/camp_dp_v25_controlled_scenario_preflight_f1bb82a9_20260717T134646CST`
has root SHA256
`9d4fb0216a448e69c09ecd0549db96cb046d00b713c23fb5428d5c976f714cac`
and passed 39 focused remote tests plus all 147 frozen-config validations. The
first pilot artifact is retained for failure accounting: a tick-level record
was initially passed to a run-level validator, so 85 otherwise executed cases
were conservatively recorded as failures. Commit
`e250b19da010117a3416fd3b0f9eb63e55548bf3` corrected only that validation
scope; it did not replace, redraw, or select cases using an outcome.

The authoritative corrected pilot is
`/root/autodl-tmp/camp_dp_v25_controlled_scenario_coverage_pilot_retry_e250b19d_20260717T135338CST`
with root SHA256
`7d5205e9a7efc1276d3f8334d9c80f6f66d7b49bef7ff4482af6f15eadb7ef24`.
All 147 attempts were retained: 85 passed and 62 remained failed. The source-
only review reproduced 61 routes without a complete positive speed-limit
source and one red-light route that produced no executed tracker tick, with
zero mismatch against the runtime failures. Lead hard brake, cut-in/merge, and
pedestrian/cyclist crossing passed 21/21 each; narrow encounter passed 11/21;
red-light timing passed 10/21; unprotected/oncoming passed 1/21; blocked/static
obstacle passed 0/21. Every passing tick preserved the fixed K=8 tensor byte-
for-byte. Registered neighbor-distance monotonic variation was observed for
lead, cut-in, crossing, and narrow cases, and red phase ordering varied as
specified. The other families remain explicitly source/capability limited; no
outcome was used to discard or replace them.

The authoritative formal source/split freeze is
`/root/autodl-tmp/camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_20260717T140842CST`
with independently recomputed root SHA256
`c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531`.
It audited all 401 inventory routes from source. The train inventory contains
375 routes, 222 with complete positive speed limits and 32 with mapped traffic
lights. Calibration contains 2 speed-complete routes and no mapped traffic
light. Fresh B contains 24 speed-complete routes and no mapped traffic light.

The frozen plan contains 1,500 executable controlled-train identities and 153
source-ineligible retained train records. At 64 ticks its controlled capacity
is 96,000 causal snapshots; adding the sealed V24 67,796 snapshots gives a
163,796-snapshot training capacity. Calibration has 36 executable identities
and six retained source-ineligible red-light records. Fresh B remains unopened
at 120 executable identities and five frozen seeds, for exactly 600 three-arm
paired runs. Its real inventory ceiling is only 24 independent routes across
three corridor groups. Scenario identities and repeated seeds increase run
coverage but are not represented as new routes or corridors. Fresh B has no
legal mapped-signal source, so it contains no fabricated red-light cases; the
21 executable red-light training identities and the pilot evidence remain the
bounded signal evidence.

All split rows are outcome-blind and carry their source eligibility and
retention role. No holdout outcome, future, model score, CAMP/DP result, or
closed-loop metric entered route selection, family/tier construction, failure
retention, or split assignment. V24 holdout was not read, Fresh B was not
opened, and fixed DP is clean at the frozen commit. Phase 5 may execute only
the frozen controlled-train identities, append them to the sealed V24 train
corpus, train the four preregistered static/scene-conditioned 9D/14D selectors,
and use calibration only for the allowed scale, threshold, and noninferiority
freeze. Fresh B remains closed until that gate passes.

current_v25_status=v25_controlled_protocol_and_source_split_frozen_phase5_training_calibration_authorized
current_v25_source_head=ff02838780c7b2fa7fc557680e43d85967ee843e
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_20260717T140842CST
current_v25_artifact_root_sha256=c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531
current_v25_atom_schema=dp_camp_v10_14d
current_v25_paper_subset=camp_legacy_v1_9d
current_v25_context_schema=camp_dp_v25_causal_context_raw_v1
current_v25_context_raw_feature_count=26
current_v25_phi_dimension=53
current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection
current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4
current_v25_controlled_pilot_case_count=147
current_v25_controlled_pilot_passed_count=85
current_v25_controlled_pilot_retained_failure_count=62
current_v25_controlled_train_executable_identity_count=1500
current_v25_controlled_train_source_ineligible_retained_count=153
current_v25_combined_train_snapshot_capacity_at_64_ticks=163796
current_v25_fresh_b_identity_count=120
current_v25_fresh_b_paired_run_count=600
current_v25_fresh_b_independent_route_ceiling=24
current_v25_fresh_b_independent_corridor_ceiling=3
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
current_v25_v24_holdout_read=false
current_v25_fresh_benchmark_b_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=48616669184
current_v25_phase=4_controlled_scenario_corpus_and_split
next_work_target=v25_controlled_train_corpus_training_and_calibration

## Phase 5: Ultra Scientific-Contract Correction Gate

The first controlled-train execution was stopped fail-closed with `SIGTERM`
after live source review confirmed that mechanical health did not imply a
scientifically valid corpus. The native selector divided raw atoms by scales
but omitted the canonical `clip(a/s, 0, 10)` operation used by the frozen atom
audit. A read-only diagnostic over 5,828 snapshots found 452 selected-index
disagreements (7.76%); the red-light easy subset disagreed on 13 of 64
snapshots. Because those selections already affected closed-loop state, the
artifact cannot be repaired by offline rescoring or by appending a corrected
suffix.

The same execution passed `phase_remaining_s` from the frozen scenario tier
and future signal schedule into the 26D context as source-complete. That source
is forbidden in the no-V2I main method. The future timing must be zero and
source-masked in context-v2; a separate V2I mode may use only current-time
visible timing with source and freshness receipts. The runner also downgraded
a candidate-heading unit-vector invariant failure and retained four illegal
partial snapshots instead of failing the artifact.

PID `151787` exited after `SIGTERM`; no child or GPU compute process remained,
the exclusive lock was free, and Fresh B was still unopened. The untouched
source artifact ended at 122 attempted identities, 121 complete identities,
one failed identity, and 7,748 snapshots. Its original `progress.json` remains
`running` and no `run.exit` was fabricated. It is superseded and ineligible
for training, calibration, evaluation, V24 merging, or claims.

The separate sealed diagnostic evidence is
`/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST`
with root SHA256
`a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481`.
It byte-indexes the unchanged source and launch trees, retains the invariant
failure and all 1,121 all-K-high-risk snapshots, and records zero candidate
immutability failures. The independent review
`/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST`
passed 9/9 checks with root SHA256
`f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009`.

Fresh Benchmark B v1 is superseded before opening; its frozen manifest remains
unchanged. Fresh B2 is not opened or constructed at this gate. Training,
calibration, scale fitting, model fitting, and any replacement 1,500-identity
execution remain prohibited. Only TDD correction and a bounded sequential-K8
preflight are authorized before an Ultra read-only correction-gate review.

## Phase 5 S0: Correction/Preflight Decision Package

S0 correction is complete at source HEAD
`676e8960338eaf00f8867691c0eb2fa7bff34a8c`; it is not authorization for
Stage A, R, training, calibration, or Fresh. The S0 implementation makes the
following contracts shared and fail-closed:

- native selection, the 14D training loader/master, and the V25 audit use
  finite nonnegative raw atoms, finite positive approved scales, and exactly
  `z=clip(a/s,0,10)` before the affine score `z_k^T w`; NaN/Inf is rejected,
  not silently coerced;
- the registered `>10x` counterexample changes the un-clipped selection from
  candidate 1 to canonical/native candidate 0, proving that clipping is on the
  executed path; equal scores use the lowest eligible candidate index;
- context-v2 never reads the frozen scenario phase schedule in the no-V2I main
  method. `traffic_signal_phase_remaining_s` is zero and unavailable there.
  The separate V2I input requires a mapped current regulatory signal, source
  id, decision/source timestamps, maximum age, validity, and freshness;
- source-valid and physical-feasible masks remain distinct. Candidate 0 is
  bound per tick to the independently generated DP operational default, not a
  native-ranked Top-1;
- candidate shape/dtype/finite state, K=8 SHA, candidate0 SHA, atom/context
  finite state, heading envelope, selected index, exact selected candidate,
  snapshot/context counts, and terminal denominator are hard invariants. A
  complete identity is exactly 64 ticks; an illegal partial identity aborts
  the artifact and cannot enter training;
- the exclusive corpus lock covers execution through terminal progress,
  report, `run.exit`, and seal. Only an explicitly preregistered zero-tick
  scenario-capability failure can be retained; invariant/schema/immutability
  failures cannot be downgraded.

Fixed DP directly regresses the two `(cos,sin)` heading channels; its loss does
not force exact unit magnitude, while its own guidance normalizes internally
and the operational runtime consumes the angle through `atan2`. A first strict
`5e-4` diagnostic therefore rejected 639/640 legitimate identity0 vectors,
whose norms were `0.956490205` to `1.0012432`. S0 freezes the fixed-DP-compatible
near-unit envelope `[0.5,1.5]`: zero/degenerate and grossly invalid vectors fail
closed, but CAMP does not normalize, repair, or otherwise modify the fixed
candidate tensor. Boundary and zero-vector tests are registered.

The no-V2I generation scale file is
`configs/integrations/diffusion_planner_v25_atom_scales_correction_v2.json`.
It replaces only the degenerate planned-red generation scale with a semantic
floor of 1.0; this is not the final training scale. Stage B must fit any final
red continuous/binary scale only from sealed train positive support under its
preregistered rule. `progress_shortfall` is explicitly named a higher-is-worse
candidate-set reference cost; Stage A still must present the source-valid and
physical-feasible adversarial alternatives to Ultra. No fallback is frozen at
S0.

The Stage A path/schema plan exists only at
`configs/integrations/diffusion_planner_v25_atom_ledger_plan_v2.json`. It plans
an exactly-14-row immutable semantics ledger plus a separate validation
receipt, keeps 9D as canonical 14D indices 0:9, and rejects the stopped partial
root. No sealed-corpus statistics or Stage A artifact was created.

AutoDL at the recorded S0 gate passed the focused selector/native/context/
corpus/master/pointer suite (`57 passed`). Four bounded preflight
attempts remain immutable failure accounting:

- device-contract rejection before model execution:
  `/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_2fca607b_20260717T165224CST`,
  root `1c8d2326521a7d565028153dc7b9029bfe932f0a2f70b3c27eb0b9e492d520a2`;
- strict learned-heading mismatch:
  `/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_56872a1b_20260717T165805CST`,
  root `465e45baaf53e054fef2e66c4d930e8a9c41686112548602cd7d3b4f9a747090`;
- the same mismatch with finite norm diagnostics:
  `/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_701fdd5d_20260717T170052CST`,
  root `d926400fd9795e4ce44c3b66245588bdd4a3d314eedb163a1c2b34928d4ee0b3`;
- all three probes executed but strict JSON sealing rejected a `numpy.bool_`:
  `/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_22a06ea0_20260717T170338CST`,
  root `ad20cbaa8d47991bc1aaa72122cf42d49f4339673bbbc916d081d59a8e9d8310`.

None was patched or promoted to passed. The final bounded sequential-K8
preflight is:

`/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_676e8960_20260717T170655CST`

with root SHA256
`d76a772ff15497a13e72538382a99e1027fb9ef53561270523bdc8975afc4fa9`.
It passed all 12 checks over 192 ticks: formal identity0 twice and one
red-light/easy identity. Both identity0 runs have selected-sequence SHA
`53240671aa0a6f66d11298c8e227bb2a269067d103bbc9b82ed49a5cdb3a2dbd`
and full tick-fingerprint root
`c5af99b39635ae6cba77fa11e45a121624aa9047a30420ad73e91e256880a92b`.
The red-light/easy run has selected-sequence SHA
`7d124de90255b68511550187e6c6a78cbca8347b4736fd79edf4469484dc90ec`
and tick-fingerprint root
`21d9480a180b1e17bb02e1d0da4de52b0b1e30073e8b32388d6f492678c503d7`.
Native and canonical normalized atoms, scores, tie-breaks, and selected indices
matched at every tick; candidate tensors were immutable; candidate0 matched
the operational default; all speed sources were complete; all contexts were
context-v2/no-V2I; and Fresh remained unopened. The actual probes included
839, 839, and 1,536 raw atom values above 10 times scale, so the executed clip
path was materially exercised rather than only synthetically tested.

The independent read-only review is:

`/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_review_676e8960_20260717T170900CST`

with root SHA256
`2465fa31b52891ab9130a47bc6f77d1191a83be807eb8b7f2c31c8c8ef1f3138`.
It passed all 18 checks, independently rehashed the preflight seal and per-run
fingerprint/selection roots, reproduced identity0 exact repeat equality, and
confirmed the rejected old partial root, `run.exit=0`, sequential K=8, no
micro-batch/cache/sharding, no full corpus, no outcome consumption, and
Fresh=false.

Existing passive timing shows selector mean about 0.20 ms, candidate inference
about 354--360 ms, and total planning about 459--479 ms in these bounded probes;
these are capability timings, not final evaluation latency claims. The S0
packet records a design-only monotonic-clock breakdown for DP default, extra
fixed-K8 generation, atom, context, scene weight, selector, tracker, and total,
with mean/median/p95/p99/max. No micro-batch, cache, or sharding optimization
was implemented in S0.

If Ultra later releases R after Stage A, the next full artifact is planned as
`/root/autodl-tmp/camp_dp_v25_corrected_controlled_train_sequential_k8_{RELEASED_HEAD}_{CST}`.
It must start from formal identity0 scenario
`fcd9f37128afcd277f02b1bbfb50c7f2609538f5c61968bd539cd52ccf913b89`,
route identity
`888d9b85c647b79a30308a5ff2928b55ef6ec09838b9f0bada390fa3c09afafd`,
and must list the stopped partial root in `rejected_roots`. This is a plan only:
no full worker or replacement monitor exists. The obsolete heartbeat remains
deleted. CAMP local/GitHub/AutoDL and fixed DP were clean and aligned for S0;
free disk was 48,499,146,752 bytes, GPU was idle, and the corpus lock was free.

S0 is now stopped at the required Ultra read-only review boundary. Stage A and
R are both unexecuted; B--F and all later gates are likewise closed. Fresh B v1
remains superseded before opening, Fresh B2 remains unopened, V24 remains
frozen, and no training, calibration, promotion, deployment, or activation is
authorized.

current_v25_status=v25_s0_correction_preflight_passed_ultra_read_only_review_required
current_v25_source_head=676e8960338eaf00f8867691c0eb2fa7bff34a8c
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST
current_v25_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST
current_v25_review_artifact_root_sha256=f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009
current_v25_correction_preflight_artifact=/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_676e8960_20260717T170655CST
current_v25_correction_preflight_artifact_root_sha256=d76a772ff15497a13e72538382a99e1027fb9ef53561270523bdc8975afc4fa9
current_v25_correction_preflight_review_artifact=/root/autodl-tmp/camp_dp_v25_ultra_correction_preflight_review_676e8960_20260717T170900CST
current_v25_correction_preflight_review_artifact_root_sha256=2465fa31b52891ab9130a47bc6f77d1191a83be807eb8b7f2c31c8c8ef1f3138
current_v25_correction_preflight_probe_count=3
current_v25_correction_preflight_tick_count=192
current_v25_correction_preflight_identity0_deterministic=true
current_v25_correction_preflight_native_canonical_equal=true
current_v25_correction_preflight_candidate_immutability=true
current_v25_atom_schema=dp_camp_v10_14d
current_v25_paper_subset=camp_legacy_v1_9d
current_v25_context_schema=camp_dp_v25_causal_context_raw_v2
current_v25_context_raw_feature_count=26
current_v25_phi_dimension=53
current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection
current_v25_normalization_contract=z_clip_raw_atom_over_scale_0_10
current_v25_heading_norm_envelope_min=0.5
current_v25_heading_norm_envelope_max=1.5
current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4
current_v25_controlled_pilot_case_count=147
current_v25_controlled_pilot_passed_count=85
current_v25_controlled_pilot_retained_failure_count=62
current_v25_controlled_train_executable_identity_count=1500
current_v25_controlled_train_source_ineligible_retained_count=153
current_v25_combined_train_snapshot_capacity_at_64_ticks=163796
current_v25_stopped_train_attempted_identity_count=122
current_v25_stopped_train_complete_identity_count=121
current_v25_stopped_train_failed_identity_count=1
current_v25_stopped_train_snapshot_count=7748
current_v25_stopped_train_illegal_partial_snapshot_count=4
current_v25_stopped_train_all_k_high_risk_snapshot_count=1121
current_v25_stopped_train_training_eligible=false
current_v25_stopped_train_calibration_eligible=false
current_v25_stopped_train_evaluation_eligible=false
current_v25_fresh_b_identity_count=120
current_v25_fresh_b_paired_run_count=600
current_v25_fresh_b_independent_route_ceiling=24
current_v25_fresh_b_independent_corridor_ceiling=3
current_v25_fresh_b_v1_status=superseded_before_opening
current_v25_fresh_b2_opened=false
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v2.json
current_v25_stage_a_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_old_monitor_status=deleted
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
current_v25_v24_holdout_read=false
current_v25_fresh_benchmark_b_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=48499146752
current_v25_phase=S0_correction_preflight_decision_package
next_work_target=ultra_read_only_review_required_before_stage_A_or_R

## Phase 5 S0.1: Fail-Closed Authority Correction

Ultra's 2026-07-17 17:30 CST decision released only S0.1 and kept Stage A and
R closed. The correction source is CAMP HEAD
`e6ba79a229ea3cc8e3a69d776ea1913cff8e3279`; fixed DP remains clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. No DP code, config, weights,
checkpoint, request semantics, candidate tensor, trajectory, K=8 cardinality,
or 64-tick protocol changed.

The eight S0.1 findings map to bounded corrections as follows:

1. The all-infeasible learned dedicated fallback no longer references the
   undefined `positive_inf`. Dedicated fallback scales must be finite and
   strictly positive; weights and all 14D atom inputs must be finite and
   nonnegative. The 14D path calls the shared
   `canonical_normalize_atoms`, so normalization is exactly
   `z=clip(a/s,0,10)`. The pre-existing generic 9D fallback test and new 14D,
   zero/negative/NaN/Inf scale, weight, progress, and red-atom variants pass.
2. The bounded reviewer requires exact nonempty report/probe check keys. It
   binds the released CAMP source to the live clean review HEAD, fixed DP,
   formal and template roots, generation scales, static weights, full config
   receipts/root, seed, rejected root, context/schema versions, `HEADS`,
   `COMMAND`, and `run.exit`. Every fingerprint and selection root is
   recomputed over exactly 64 ticks per probe; empty checks cannot pass.
3. The future full-corpus executor preflight now applies the same authority
   contract and independently reconstructs all 1,500 path-independent config
   authority receipts. It additionally requires `corpus_steps=64`, capacity
   96,000, exact unique identities, and explicit no-training/no-calibration/
   no-Fresh flags. An incomplete or different-HEAD preflight is rejected.
4. Scenario capability failure is a typed enum/exception raised only for the
   preregistered mapped-current-signal-source capability. Retention requires a
   structured receipt that exactly matches formal identity, family, and reason;
   the red-light contract is capped at 32 retained identities. Zero complete
   identities, an exceeded cap, a spoofed string/class, a partial identity, or
   any other exception cannot produce a passed corpus.
5. Combined training snapshots and bounded fingerprints retain
   `default_output_sha256`, `candidate0_sha256`, and the full identity receipt.
   Review independently checks them against candidate row 0 and records that
   candidate0 is the operational-default alias from the same forward, not an
   independent second forward or native-ranked Top-1.
6. The main context path remains no-V2I: phase remaining is zero, unavailable,
   and source-masked. S0.1 does not bless the existing generic receipt as a
   production provider. The later V2I hard gate requires a per-tick provider
   bound to TrafficLightRegulatoryElement, physical light, controlled lanelet,
   stop line, route arc, current phase, source/decision timestamps and
   freshness, with wrong-id, phase-mismatch, replay, future, and stale tests.
7. Native selection at this gate is Static14D only. Scene14D runtime remains
   disconnected. Its later C gate must build approved phi before selection,
   load sealed train-only q05/q95 and column-simplex Theta, record Theta/phi/w
   hashes, and use no runtime projection.
8. The versioned Stage A plan now freezes the exact 14-name order, canonical
   9D prefix, 14-row field contract, four-state source enum, ordered
   schema/formula hash, outcome-blind semantic-block hash/dedup contract,
   train-only block-weighted positive-support scale estimator, complete DAG,
   signal/V2I gate, candidate0 semantics, and progress-reference adversarial
   decision. This is still a plan only; no ledger or sealed-corpus statistics
   were executed.

Local validation used Python 3.12: the five focused S0.1 files passed 50 tests
with one local cvxpy-dependent skip, the dedicated fallback selection passed
14 tests, the final pointer/audit suite passed 10 tests, pycompile passed, JSON
parsing passed, and `git diff --check` passed. On AutoDL, the same focused files
passed all 51 tests, the generic/dedicated fallback selection passed all 14
tests, and the final pointer suite passed all 10 tests: 65 focused correctness
tests plus 10 pointer tests.

The first new invocation is immutable failure accounting:

`/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST`

It has root SHA256
`c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a`
and `run.exit=1`. It failed before model execution because the operator supplied
the repository's same-named template whose SHA did not match the frozen
template root. It was not edited or promoted. GPU remained unused.

The corrected bounded sequential-K8 no-V2I preflight is:

`/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST`

with root SHA256
`bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451`
and `run.exit=0`. It passed all 12 checks over the same three probes and 192
ticks. The two identity0 repeats share selected-sequence SHA
`53240671aa0a6f66d11298c8e227bb2a269067d103bbc9b82ed49a5cdb3a2dbd`
and the new, candidate0-complete fingerprint root
`e830f9e6764520d8bc9911a6416caa8a62fbceb5bc07c13d8b683a1b395850b9`.
The red-light/easy selected-sequence SHA remains
`7d124de90255b68511550187e6c6a78cbca8347b4736fd79edf4469484dc90ec`
and its fingerprint root is
`a64f078791ba7014338e232ba7b94142e266896d9049dc98e5500f11b57f8409`.
The probes again materially exercised 839, 839, and 1,536 raw values above ten
times scale. Wall time was 95.12 seconds.

The strengthened independent review is:

`/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST`

with root SHA256
`facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d`
and `run.exit=0`. It passed all 28 checks, including every authority binding,
both config roots, all 192 per-tick fingerprints, selected sequences, and the
operational-default/candidate0 alias evidence.

After review, CAMP source/GitHub/AutoDL were clean and aligned at the released
S0.1 source HEAD, fixed DP was clean, worker count was zero, flock was free,
GPU had no compute process, and free disk was 48,497,549,312 bytes. The stopped
partial corpus remains the current rejected training artifact and is listed in
all new `rejected_roots`. Fresh B v1 remains superseded before opening; Fresh
B2 remains unopened. Stage A=false, R=false, Scene runtime=false, training=false,
calibration=false, and Fresh=false. The next gate is Ultra's read-only S0.1
review; no full worker or replacement monitor may start before a separate
release.

## Stage A: Static 14D Atom Ledger and Independent Validation

Ultra's 2026-07-17 S0.1 decision released only bounded Stage A, with R and all
later stages still closed. The implementation source range is
`f40b615206eaa4aacce10849bc5719110c9a5b91` through
`e07da58f6f589487cf5e41bcf347ec6e18c589c3`; fixed DP remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

### A0 authority hardening

The shared V25 seal verifier now requires a nonempty UTF-8 manifest, lowercase
SHA256 values, safe POSIX relative paths, unique entries, exact recursive file
inventory, regular files/directories, and no symlinks or special nodes. TDD
covers unlisted files, traversal, duplicates, empty manifests, symlinks, and
overflowing finite simplex inputs. Generic `CAMPSelector` static and learned
fallback weights now use one strict finite/nonnegative/finite-positive-total
normalizer; NaN, Inf, negatives, zero mass, and finite-element sum overflow
fail closed instead of `nan_to_num`, truncation, or uniform repair. The native
fixed-R sequential path and fixed candidates were not changed.

The first A0 invocation is immutable diagnostic failure evidence:

`/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_f40b6152_20260717T192912CST`
/
`025dcd686ee44a681b14cc3ad8b5e64e885316b0f334d89096fda19d6cd8b810`.

It stopped with `run.exit=1` because the new exact validator correctly rejected
an incorrectly transcribed historical formal-source CAMP HEAD. No ledger or
model work started. The constant was corrected to the sealed formal receipt
`ff02838780c7b2fa7fc557680e43d85967ee843e` and covered by regression TDD.

The passed A0 supplement is:

`/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_01073398_20260717T193038CST`
/
`b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41`.

It independently rehashed exact inventories for the S0.1 failed preflight,
passed preflight, passed review, and formal source: `2/23/3/10` manifest files,
respectively, with no unsafe, duplicate, missing, extra, symlink, special, or
hash-mismatched entry. It also proved that the two S0.1 configs are precisely
formal identity0 lead-brake/easy and formal red-light/easy, field-equal in
scenario/family/tier/route/seed and sharing the frozen template, generation
scales, and weights. The existing 3x64 model probes were not rerun.

### Immutable ledger and independent math receipt

The 14-row immutable semantics ledger and minimal raw numeric sidecar are:

`/root/autodl-tmp/camp_dp_v25_static_atom_ledger_v2_01073398_20260717T193052CST`
/
`05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2`.

It binds S0.1 source `e6ba79a2...`, final S0.1 release baseline `000d4308...`,
the A0 root, formal/preflight/review roots, fixed DP, and rejected partial-corpus
root `a2f69cdc...`. Every row fixes order, 9D membership, formula/unit/dt,
finite/nonnegative/raw bounds, generation scale provenance and SHA, clip,
four-state source policy, invalid/mask behavior, monotonic domain, K8 and
route/lane/neighbor/signal/candidate0 dependencies, forbidden sources, and
zero/positive/distinguishing fixtures. The paper subset is exactly canonical
14D indices `0:9`; no atom was silently deleted.

The first validator root
`00fdceb44380d5f6aa18af3fdc4a0c122f302f36845db7ea137cd44feb7fe4e8`
is retained but superseded because one JSON check was truthy string-valued
rather than exact boolean. Numeric and scientific results did not change. The
final exact-boolean independent validation is:

`/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_e07da58f_20260717T193156CST`
/
`e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72`.

The validator used explicit scalar `raw/scale`, `[0,10]` clipping, affine sums,
eligible argmin and lowest-index tie-breaking; it did not import producer score
results. It exactly matched all 8x14 normalized values and eight scores, the
selected index, 9D prefix, source/physical masks, and eight distinct candidate
SHAs. Independent algebra also proved `jerk_full=jerk_early+jerk_late` and the
ordered `0/0.5/1.0 m/s` speed-margin increments. Results are 8 PASS, 6 WARN,
0 FAIL:

- PASS: `jerk_early`, `jerk_late`, `jerk_full`, `rms_acceleration`,
  `speed_limit_margin_1_0`, `clearance`,
  `planned_lateral_acceleration_cost`, `dp_prior_jerk_excess_cost`;
- WARN: `speed_limit_margin_0_0`, `speed_limit_margin_0_5`, `lane_deviation`
  because their current generation scales are legacy `1e-6` floors;
  `planned_red_light_cost` and `red_stopping_margin_cost` because continuous
  support is sparse/scale-sensitive; and `progress_shortfall` because Ultra
  must choose its reference policy.

The 192-tick S0 artifact stores atom and normalized-atom hashes, not per-atom
raw values. Therefore Stage A honestly records per-atom zero/positive/saturation
as unavailable rather than inferring them. The only available S0 diagnostic is
the aggregate above-clip count `839 + 839 + 1536 = 3214 / 21504`. The three
`1e-6` generation scales and red-stopping `4.952895923795447e-4` are explicitly
not final training scales. Before R statistics, Stage B's estimator is frozen
to source-valid/applicable, source-independent semantic-block-weighted positive
raw support, q95, at least 20 unique blocks and 128 positive candidate rows;
the red binary alternative is `1(raw>0)` with scale 1.0 and cannot silently
replace the continuous atom.

### Pending progress decision and R coverage gate

The sidecar evaluates both progress references on mixed masks, all-K-high-risk,
and empty-reference fixtures. Both prohibit candidate0/all-K fallback and fail
closed when their reference set is empty. Stage A recommends
`source_valid_candidate_set_reference` because it remains defined on an
all-K-physically-bad but source-valid set; this is a recommendation, not a
freeze, and requires Ultra decision before R.

Formal red inventory is 21 executable identities: easy/borderline/high-risk
`6/10/5`, 21 route families, four source maps, and one corridor group. R's
outcome-blind scientific minimum is frozen to completed mapped-current-signal
coverage `4/7/4` by tier and at least three source maps. All failures remain in
the denominator, but 21/21 retained capability failures now make the artifact
`scientifically_ineligible` and block B/training even though 21 is below the
separate retained-failure cap 32.

AutoDL passed 41 focused Stage-A tests and 40 selector/fallback integration
tests; pycompile, JSON parsing, and diff checks passed. CAMP local/origin/GitHub/
AutoDL source aligned at `e07da58f6f589487cf5e41bcf347ec6e18c589c3` before
this documentation record, fixed DP was clean, worker/GPU counts were zero,
the lock was free, and disk free was 48,495,505,408 bytes. R, a 1500 worker or
monitor, B/C/D, Scene runtime, training, calibration, Fresh B2, promotion, and
activation remain closed. The next gate is Ultra read-only Stage-A review and
the progress-reference decision.

current_v25_status=v25_stage_a_passed_with_warnings_ultra_review_and_progress_decision_required
current_v25_source_head=e07da58f6f589487cf5e41bcf347ec6e18c589c3
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST
current_v25_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST
current_v25_review_artifact_root_sha256=f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009
current_v25_s01_failed_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST
current_v25_s01_failed_preflight_artifact_root_sha256=c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a
current_v25_correction_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST
current_v25_correction_preflight_artifact_root_sha256=bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451
current_v25_correction_preflight_review_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST
current_v25_correction_preflight_review_artifact_root_sha256=facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d
current_v25_correction_preflight_probe_count=3
current_v25_correction_preflight_tick_count=192
current_v25_correction_preflight_check_count=12
current_v25_correction_preflight_review_check_count=28
current_v25_correction_preflight_identity0_deterministic=true
current_v25_correction_preflight_native_canonical_equal=true
current_v25_correction_preflight_candidate_immutability=true
current_v25_correction_preflight_candidate0_operational_default_alias=true
current_v25_s01_remote_focused_test_count=65
current_v25_s01_remote_pointer_test_count=10
current_v25_stage_a0_failed_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_f40b6152_20260717T192912CST
current_v25_stage_a0_failed_artifact_root_sha256=025dcd686ee44a681b14cc3ad8b5e64e885316b0f334d89096fda19d6cd8b810
current_v25_stage_a0_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_01073398_20260717T193038CST
current_v25_stage_a0_artifact_root_sha256=b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41
current_v25_atom_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_v2_01073398_20260717T193052CST
current_v25_atom_ledger_artifact_root_sha256=05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2
current_v25_atom_ledger_superseded_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_01073398_20260717T193052CST
current_v25_atom_ledger_superseded_validation_artifact_root_sha256=00fdceb44380d5f6aa18af3fdc4a0c122f302f36845db7ea137cd44feb7fe4e8
current_v25_atom_ledger_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_e07da58f_20260717T193156CST
current_v25_atom_ledger_validation_artifact_root_sha256=e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72
current_v25_stage_a_atom_pass_count=8
current_v25_stage_a_atom_warn_count=6
current_v25_stage_a_atom_fail_count=0
current_v25_stage_a_progress_reference_recommendation=source_valid_candidate_set_reference
current_v25_stage_a_progress_reference_frozen=false
current_v25_stage_a_s01_per_atom_raw_statistics_available=false
current_v25_stage_a_remote_focused_test_count=41
current_v25_stage_a_remote_selector_test_count=40
current_v25_atom_schema=dp_camp_v10_14d
current_v25_paper_subset=camp_legacy_v1_9d
current_v25_context_schema=camp_dp_v25_causal_context_raw_v2
current_v25_context_raw_feature_count=26
current_v25_phi_dimension=53
current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection
current_v25_normalization_contract=z_clip_raw_atom_over_scale_0_10
current_v25_heading_norm_envelope_min=0.5
current_v25_heading_norm_envelope_max=1.5
current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4
current_v25_controlled_pilot_case_count=147
current_v25_controlled_pilot_passed_count=85
current_v25_controlled_pilot_retained_failure_count=62
current_v25_controlled_train_executable_identity_count=1500
current_v25_controlled_train_source_ineligible_retained_count=153
current_v25_combined_train_snapshot_capacity_at_64_ticks=163796
current_v25_stopped_train_attempted_identity_count=122
current_v25_stopped_train_complete_identity_count=121
current_v25_stopped_train_failed_identity_count=1
current_v25_stopped_train_snapshot_count=7748
current_v25_stopped_train_illegal_partial_snapshot_count=4
current_v25_stopped_train_all_k_high_risk_snapshot_count=1121
current_v25_stopped_train_training_eligible=false
current_v25_stopped_train_calibration_eligible=false
current_v25_stopped_train_evaluation_eligible=false
current_v25_fresh_b_identity_count=120
current_v25_fresh_b_paired_run_count=600
current_v25_fresh_b_independent_route_ceiling=24
current_v25_fresh_b_independent_corridor_ceiling=3
current_v25_fresh_b_v1_status=superseded_before_opening
current_v25_fresh_b2_opened=false
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v2.json
current_v25_stage_a_executed=true
current_v25_corrected_full_corpus_started=false
current_v25_old_monitor_status=deleted
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
current_v25_v24_holdout_read=false
current_v25_fresh_benchmark_b_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=48495505408
current_v25_phase=A_static_atom_ledger_decision_package
next_work_target=ultra_read_only_stage_A_review_and_progress_reference_decision_before_R

## Stage A1/R0: Frozen Semantics, Signal Authority, and Bounded K8 Preflight

Ultra's 2026-07-17 Stage-A decision accepted S0.1/A0 but downgraded the first
ledger and validation roots `05449b7a...` and `e07bfcbd...` to superseded
diagnostic evidence. It released only A1 and R0; full R, a 1,500-identity
worker/monitor, training, calibration, Scene runtime, V2I, and Fresh remained
closed. The implementation source range is `8798f3bfda8f04867e2f70aee7472b74931b1c34`
through `ffd2ec647dabe46734fabe80779027429c59fe04`; fixed DP remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

### A1 corrections and independent ledger validation

The canonical progress contract is now frozen to
`source_valid_candidate_set_reference`: selection eligibility is exactly the
source-valid candidate set, `r=max(progress[j] where source_valid[j])`, and
`progress_shortfall[k]=max(r-progress[k],0)`. Empty source-valid sets fail
closed; candidate0 and all-K fallback are forbidden. Production, generic
selector, training/evaluation helpers, the ledger, and mutation tests share
this contract. Reachable mixed-mask and all-K-physically-bad fixtures enforce
`physical_feasible => source_valid`, independently recompute both reference
options, and prove that a source-valid all-K-physically-bad set remains defined.

The v3 ledger schema uses flat dependency fields and a source-independent
geometry/semantic-clone hash whose canonical JSON excludes source family/path
and map/route/scenario/split/seed identifiers. The validator accepts only the
PASS/WARN/FAIL enum and independently derives each atom's status, warning
rationale, formula, sources, dependencies, monotonicity, policies, and required
fields. Its nontrivial 8x14 sidecar independently recomputes
`clip(raw/scale,0,10) @ w`, an eligible argmin, lowest-index tie, masks, 9D
prefix, and candidate SHAs bound to the candidate tensors used by atom
computation. Generation scales are unchanged and remain generation-only; R
snapshots now retain raw 8x14 atoms, source/applicability masks, scale SHA, and
the canonical semantic hash for later sealed-train-only q95 support/stability
work.

The immutable authority decision, A1 ledger, and independent validation are:

- `/root/autodl-tmp/camp_dp_v25_ultra_stage_a_decision_ffd2ec64_20260717T203912CST`
  / `b75898b2d9263abf157ebd72b8d03e445ceeb23168a06d8065ae0b959aa3340d`;
- `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a1_ffd2ec64_20260717T203912CST`
  / `f8ecaf1a9235753245cad736cef4172e8a553143a0eff45bf179add2b4ecdac5`;
- `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a1_ffd2ec64_20260717T203912CST`
  / `947d4b00fe39222e8be581e3d681959ed153f6410c7c065adb5b992c9de89d58`.

The independent result is 9 PASS, 5 WARN, 0 FAIL. WARN remains limited to
`speed_limit_margin_0_0`, `speed_limit_margin_0_5`, `lane_deviation`,
`planned_red_light_cost`, and `red_stopping_margin_cost`; these are
generation-scale or future sealed-train support warnings, not atom deletion or
safety evidence.

### R0 source qualification and bounded no-V2I preflight

R0 binds the Ultra decision, corrected source, S0.1 passed/review roots, A0,
A1 ledger/validation, the formal root, fixed DP, and rejected old partial root.
Its source-only census independently qualified all 21 formal red identities
over four source maps, with easy/borderline/high-risk counts `6/10/5`. Every
chain binds the TrafficLightRegulatoryElement, physical lights/bulbs, controlled
lanelets, stop line, route-arc relation, map/geometry SHA, unique regulatory
mapping, and same-tick current phase. Wrong/multiple IDs, missing stop line,
route-arc mismatch, phase mismatch, future/replay/stale input, or padded
unmapped route rows fail closed; distance and traffic-row counts cannot
substitute for regulatory authority.

The sealed source and independent review roots are:

- `/root/autodl-tmp/camp_dp_v25_r0_authority_source_ffd2ec64_20260717T203912CST`
  / `69f02664fa96fe9689b60f6432e0c910b9a18bb6ffd1a88f569c10670178d3be`;
- `/root/autodl-tmp/camp_dp_v25_r0_authority_source_review_ffd2ec64_20260717T203912CST`
  / `c8b8b926bd63a0a8185d7ea3f422e7b94bc0c40921560e6576ac9e4b0ca786e9`.

Only after that source review passed, one easy, one borderline, and one
high-risk red identity ran through the unchanged sequential fixed-DP K=8 path,
exactly 64 ticks each. The 192-tick independent review recomputed scalar
clip/affine/eligible argmin and verified candidate0 operational-default alias,
K8/candidate SHAs, raw atoms, masks, context-v2 no-V2I state, selected sequence,
runtime signal receipts, immutability, and failure class:

- `/root/autodl-tmp/camp_dp_v25_r0_red_sequential_k8_ffd2ec64_20260717T204012CST`
  / `209fc00b6aeb90d887f9cc2871fefdcd619d0b1086d6ffb3ee3c0ac39911f11d`;
- `/root/autodl-tmp/camp_dp_v25_r0_red_sequential_k8_review_ffd2ec64_20260717T204012CST`
  / `e948eb17e3561a93c803ec8485d725d47e341b129a794bcf1c2c6e9593cef946`.

The review statuses are `passed_source_only_full_r_closed` and
`passed_independent_3x64_review_full_r_closed`. These are bounded correctness
receipts, not corpus, training, calibration, or safety evidence.

### Preserved failures, verification, and stop boundary

Fail-closed development receipts were not overwritten: the wrong-template R0
attempt is root `c0ee6e94...` with `run.exit=1`; the corrected source retry root
`7d149292...` was followed by a serialization-strict review failure root
`c5a2760e...`; and the first bounded K8 attempt failed before any accepted tick
at root `e15071f0...` because route lanelet IDs did not cover the sliding route
tensor. The final fix derives signal row IDs from the same sliding segment and
requires padded unmapped rows to be zero. All interim 8798/aaf777 artifacts are
superseded diagnostic and cannot authorize R.

Local focused verification passed `104 passed, 1 skipped`, followed after the
route-row fix by `48 passed, 1 skipped`. AutoDL passed 74 focused tests, the
5-test production materializer subset (27 deselected), and 49 final-HEAD tests;
pycompile, JSON parsing, pointer/audit checks, and `git diff --check` passed.
At the final source-head check, CAMP local/origin/GitHub/AutoDL were clean at
`ffd2ec647dabe46734fabe80779027429c59fe04`, fixed DP was clean, worker count
was zero, GPU compute count was zero, the corpus lock was free, and disk free
was 48,487,464,960 bytes. Fresh/outcome remains unopened. Full R remains
unauthorized until a new Ultra read-only decision explicitly releases it.

current_v25_status=v25_a1_r0_bounded_pass_ultra_read_only_review_required
current_v25_source_head=ffd2ec647dabe46734fabe80779027429c59fe04
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST
current_v25_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST
current_v25_review_artifact_root_sha256=f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009
current_v25_s01_failed_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST
current_v25_s01_failed_preflight_artifact_root_sha256=c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a
current_v25_correction_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST
current_v25_correction_preflight_artifact_root_sha256=bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451
current_v25_correction_preflight_review_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST
current_v25_correction_preflight_review_artifact_root_sha256=facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d
current_v25_correction_preflight_probe_count=3
current_v25_correction_preflight_tick_count=192
current_v25_correction_preflight_check_count=12
current_v25_correction_preflight_review_check_count=28
current_v25_correction_preflight_identity0_deterministic=true
current_v25_correction_preflight_native_canonical_equal=true
current_v25_correction_preflight_candidate_immutability=true
current_v25_correction_preflight_candidate0_operational_default_alias=true
current_v25_s01_remote_focused_test_count=65
current_v25_s01_remote_pointer_test_count=10
current_v25_stage_a0_failed_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_f40b6152_20260717T192912CST
current_v25_stage_a0_failed_artifact_root_sha256=025dcd686ee44a681b14cc3ad8b5e64e885316b0f334d89096fda19d6cd8b810
current_v25_stage_a0_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_01073398_20260717T193038CST
current_v25_stage_a0_artifact_root_sha256=b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41
current_v25_stage_a_superseded_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_v2_01073398_20260717T193052CST
current_v25_stage_a_superseded_ledger_artifact_root_sha256=05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2
current_v25_stage_a_superseded_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_e07da58f_20260717T193156CST
current_v25_stage_a_superseded_validation_artifact_root_sha256=e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72
current_v25_ultra_stage_a_decision_artifact=/root/autodl-tmp/camp_dp_v25_ultra_stage_a_decision_ffd2ec64_20260717T203912CST
current_v25_ultra_stage_a_decision_artifact_root_sha256=b75898b2d9263abf157ebd72b8d03e445ceeb23168a06d8065ae0b959aa3340d
current_v25_atom_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a1_ffd2ec64_20260717T203912CST
current_v25_atom_ledger_artifact_root_sha256=f8ecaf1a9235753245cad736cef4172e8a553143a0eff45bf179add2b4ecdac5
current_v25_atom_ledger_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a1_ffd2ec64_20260717T203912CST
current_v25_atom_ledger_validation_artifact_root_sha256=947d4b00fe39222e8be581e3d681959ed153f6410c7c065adb5b992c9de89d58
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_r0_authority_source_ffd2ec64_20260717T203912CST
current_v25_r0_authority_source_artifact_root_sha256=69f02664fa96fe9689b60f6432e0c910b9a18bb6ffd1a88f569c10670178d3be
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_r0_authority_source_review_ffd2ec64_20260717T203912CST
current_v25_r0_authority_source_review_artifact_root_sha256=c8b8b926bd63a0a8185d7ea3f422e7b94bc0c40921560e6576ac9e4b0ca786e9
current_v25_r0_bounded_k8_artifact=/root/autodl-tmp/camp_dp_v25_r0_red_sequential_k8_ffd2ec64_20260717T204012CST
current_v25_r0_bounded_k8_artifact_root_sha256=209fc00b6aeb90d887f9cc2871fefdcd619d0b1086d6ffb3ee3c0ac39911f11d
current_v25_r0_bounded_k8_review_artifact=/root/autodl-tmp/camp_dp_v25_r0_red_sequential_k8_review_ffd2ec64_20260717T204012CST
current_v25_r0_bounded_k8_review_artifact_root_sha256=e948eb17e3561a93c803ec8485d725d47e341b129a794bcf1c2c6e9593cef946
current_v25_stage_a_atom_pass_count=9
current_v25_stage_a_atom_warn_count=5
current_v25_stage_a_atom_fail_count=0
current_v25_stage_a_progress_reference=source_valid_candidate_set_reference
current_v25_stage_a_progress_reference_frozen=true
current_v25_stage_a_s01_per_atom_raw_statistics_available=false
current_v25_a1_r0_local_test_result=104_passed_1_skipped_plus_final_route_subset_48_passed_1_skipped
current_v25_a1_r0_remote_test_result=74_passed_plus_5_passed_27_deselected_plus_final_head_49_passed
current_v25_atom_schema=dp_camp_v10_14d
current_v25_paper_subset=camp_legacy_v1_9d
current_v25_context_schema=camp_dp_v25_causal_context_raw_v2
current_v25_context_raw_feature_count=26
current_v25_phi_dimension=53
current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection
current_v25_normalization_contract=z_clip_raw_atom_over_scale_0_10
current_v25_heading_norm_envelope_min=0.5
current_v25_heading_norm_envelope_max=1.5
current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4
current_v25_controlled_pilot_case_count=147
current_v25_controlled_pilot_passed_count=85
current_v25_controlled_pilot_retained_failure_count=62
current_v25_controlled_train_executable_identity_count=1500
current_v25_controlled_train_source_ineligible_retained_count=153
current_v25_combined_train_snapshot_capacity_at_64_ticks=163796
current_v25_stopped_train_attempted_identity_count=122
current_v25_stopped_train_complete_identity_count=121
current_v25_stopped_train_failed_identity_count=1
current_v25_stopped_train_snapshot_count=7748
current_v25_stopped_train_illegal_partial_snapshot_count=4
current_v25_stopped_train_all_k_high_risk_snapshot_count=1121
current_v25_stopped_train_training_eligible=false
current_v25_stopped_train_calibration_eligible=false
current_v25_stopped_train_evaluation_eligible=false
current_v25_fresh_b_identity_count=120
current_v25_fresh_b_paired_run_count=600
current_v25_fresh_b_independent_route_ceiling=24
current_v25_fresh_b_independent_corridor_ceiling=3
current_v25_fresh_b_v1_status=superseded_before_opening
current_v25_fresh_b2_opened=false
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v3.json
current_v25_stage_a_executed=true
current_v25_stage_a1_executed=true
current_v25_r0_source_executed=true
current_v25_r0_bounded_k8_executed=true
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_probe_identity_count=3
current_v25_r0_probe_tick_count=192
current_v25_corrected_full_corpus_started=false
current_v25_old_monitor_status=deleted
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
current_v25_v24_holdout_read=false
current_v25_fresh_benchmark_b_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=48487464960
current_v25_phase=A1_R0_bounded_decision_package
next_work_target=ultra_read_only_A1_R0_review_before_full_R

## Stage A1.1/R0.1: Stop-Line Authority, Cross-Map Correctness, and Full Bounded Coverage

Ultra's A1/R0 read-only decision blocked full R and released only the bounded
A1.1/R0.1 correction. The released implementation range ends at artifact
source HEAD `de1a21ee2a96a48e3f2e854156538bda5177b477`; fixed DP stayed clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. No DP code, configuration,
checkpoint, weights, K=8 candidate tensors, trajectories, or request semantics
were changed.

### A1.1 semantics and authority

The authorized red-stopping atom now consumes only the uniquely certified
stop-line geometry transformed into the current ego frame. Its causal input is
bound to the TrafficLightRegulatoryElement, physical lights/bulbs, controlled
lanelet, stop-line geometry SHA, route-arc relation, source-chain SHA, same-tick
phase receipt, and semantic-clone SHA. Wrong/multiple/missing stop lines,
wrong chain/phase, stale/replayed/future inputs, and route-arc mismatches fail
closed. Nearby uncertified lines cannot affect the atom.

The ledger and production formulas are exact for asymmetric left/right lane
widths and candidate-specific OBB surface clearance
`dt*sum(max(3m-clearance,0)^2)`. Snapshot schema v3 stores strict `[8,14]`
atom-source-valid and applicability masks separately from the candidate-level
physical-feasible mask. Source-valid eligibility remains frozen, empty
source-valid sets fail closed, and all-K-physically-bad rows remain in the
denominator. Generic 14D selection requires K=8, an explicit strict bool source
mask, and finite nonnegative route-projected progress; legacy behavior is
isolated.

The v4 ledger plan contains the full S0->A->R->B->C/D->E1->T/E2->Q->F/E3 DAG,
including separate C and D entry/exit/Ultra-release contracts. An initial
validator attempt correctly failed closed because the producer emitted the
older compact C/D representation; failed root
`4d51394f8f4f61680fb65bd82062096fbaa72149862c4a6289f7f46927402b20`
was preserved. The final producer and independent validator bind an identical
exact DAG without importing producer status or score summaries.

Final immutable A1.1 roots:

- decision: `/root/autodl-tmp/camp_dp_v25_ultra_stage_a11_r01_decision_de1a21ee_20260717T223757CST`
  / `d98929000c09cbe1f3bcdc7f57290091e0be31e67726f4920d201bc98292897e`;
- 14-row ledger: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a11_de1a21ee_20260717T223757CST`
  / `836d5468fd05cdbd837037352d14cd20fb21a6b653ece41272bb85b30c42ad82`;
- independent validation: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a11_de1a21ee_20260717T223757CST`
  / `a37fd179db35ab51b4ca08c99e669c3b62ecb5804a3679fafd9b35450d618352`.

The atom result remains 9 PASS, 5 WARN, 0 FAIL. WARN denotes generation-scale
or future sealed-train support limits, never silent atom deletion. Static14D
and Scene14D still mean all 14 approved atoms; 9D remains an ablation only.
Generation scales and canonical `[0,10]` clipping are unchanged. The
red-outcome evaluator's legacy 10 m nearest-line heuristic remains an explicit
calibration/Fresh-B2 hard gate. Passive latency instrumentation is planned, but
no micro-batch/cache/sharding optimization was mixed into this correctness run.

The earlier A1/R0 roots `f8ecaf1a...`, `947d4b00...`, `69f02664...`,
`c8b8b926...`, `209fc00b...`, and `e948eb17...`, plus intermediate roots from
the 1bfb/24c/546 correction HEADs, are preserved as superseded diagnostic
evidence. None can authorize full-config preflight or full R.

### R0.1 source census and physical independence

The source-only qualification validated all 21 formal red identities and one
source-qualified non-signal identity. Physical independence is reported as four
source-map files, nine SE(2)-invariant source/ID-independent physical signatures,
five stop-line geometry SHAs, and 21 validated identity-chain receipts; 21 is
not claimed as 21 independent intersections. Each signature is computed from
certified controlled centerline and stop-line geometry in the stop-midpoint
route-tangent/normal frame and excludes source path/family,
map/route/scenario/split/seed IDs, actor order, and outcomes/future fields.

The first R0.1 census incorrectly counted 21 full-route hashes as physical
signatures and failed closed at root
`b491a1fd8c82fd7165bf08763cc1e12f9a1bfe5e89cb7e2b6e8133a2f0958d87`.
That root is diagnostic only. The corrected source artifact and independent
review recompute the nine physical signatures from source maps:

- source: `/root/autodl-tmp/camp_dp_v25_r01_authority_source_de1a21ee_20260717T223757CST`
  / `e099837be509085fd761244ca676d387ee4debfe0214cf22057b631ba4dff1fa`;
- review: `/root/autodl-tmp/camp_dp_v25_r01_authority_source_review_de1a21ee_20260717T223757CST`
  / `e28c5851d15a0d313afe2f577c13ed9207686fa0a724d1738514675aae0fbb1e`.

Both artifacts are sealed with strict exact inventory and `run.exit=0`. The
stopped 122-attempt partial corpus root
`a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481`
remains in rejected roots and is still training/calibration/evaluation
ineligible.

### 21-red plus one non-signal sequential-K8 preflight

The first 21+1 run exposed a CAMP integration correctness defect and failed
closed at root
`652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06`.
A process-local no-ROS Lanelet2 projector retained the previous source-map
origin. For scenario `9b295d94...`, the certified route start
`[40.6621, 24.2647]` was therefore replayed as the prior map's
`[9.57165, -21.68125]`, causing step-0 `goal_passed`. The integration now marks
its fallback projector with the source-map SHA and refreshes it only when that
SHA changes; a real Autoware extension is never evicted. A two-map SE(2)/origin
regression test prevents recurrence. The failed artifact was not spliced,
relabelled, or used by the retry.

The corrected run restarted from identity 0 and completed all 21 red identities
plus one non-signal identity for exactly 64 ticks each: 22 identities and 1,408
ticks. Its independent reviewer consumed saved actual K8 tensors, full context,
strict masks, and signal/stop-line bindings, then independently recomputed
candidate/default/selected/context hashes, canonical clip/affine scores,
source-valid eligible argmin and tie break, candidate0 operational-default
identity, selected trajectory hash, and before/after immutability:

- producer: `/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_de1a21ee_20260717T223934CST`
  / `a520f86c2930fb3c2535efb730bf2e2a1b33db11c77f50535926f1971dbcf07c`;
- independent review: `/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_review_de1a21ee_20260717T225227CST`
  / `81a0c1acf7f5c5b76315659b7c917fb641013db20b5a130c27e2402a6560fb6b`.

All seven final roots passed strict inventory verification with `run.exit=0`.
Focused local verification reached `90 passed, 2 skipped, 126 deselected` plus
the 67-test V25 suite; AutoDL reached 68 focused V25 tests plus 23 targeted
integration tests. Pycompile, JSON, pointer/audit tests, and `git diff --check`
are required again at the release commit.

At the decision-package state, worker and GPU counts are zero, the corpus lock
is free, disk free is 48,252,592,128 bytes, and Fresh outcome files are zero.
Fresh B v1 remains superseded-before-opening; Fresh B2, training, calibration,
Scene runtime, V2I, full-config preflight, and full R are unopened/unstarted.
Two-level release is implemented but unused: Ultra may release only the sealed
1,500-config preflight; after its independent review, a separate Ultra execute
release bound to both roots is mandatory. The present stop target is Ultra's
read-only A1.1/R0.1 review before even the full-config preflight release.

current_v25_status=v25_a11_r01_bounded_pass_ultra_read_only_review_required
current_v25_source_head=de1a21ee2a96a48e3f2e854156538bda5177b477
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_de1a21ee_20260717T223934CST
current_v25_artifact_root_sha256=a520f86c2930fb3c2535efb730bf2e2a1b33db11c77f50535926f1971dbcf07c
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_review_de1a21ee_20260717T225227CST
current_v25_review_artifact_root_sha256=81a0c1acf7f5c5b76315659b7c917fb641013db20b5a130c27e2402a6560fb6b
current_v25_ultra_stage_a_decision_artifact_root_sha256=d98929000c09cbe1f3bcdc7f57290091e0be31e67726f4920d201bc98292897e
current_v25_atom_ledger_artifact_root_sha256=836d5468fd05cdbd837037352d14cd20fb21a6b653ece41272bb85b30c42ad82
current_v25_atom_ledger_validation_artifact_root_sha256=a37fd179db35ab51b4ca08c99e669c3b62ecb5804a3679fafd9b35450d618352
current_v25_r0_authority_source_artifact_root_sha256=e099837be509085fd761244ca676d387ee4debfe0214cf22057b631ba4dff1fa
current_v25_r0_authority_source_review_artifact_root_sha256=e28c5851d15a0d313afe2f577c13ed9207686fa0a724d1738514675aae0fbb1e
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v4.json
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_physical_signature_count=9
current_v25_r0_stop_line_geometry_sha256_count=5
current_v25_r0_probe_identity_count=22
current_v25_r0_probe_tick_count=1408
current_v25_r0_non_signal_identity_count=1
current_v25_full_config_preflight_started=false
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_b2_opened=false
current_v25_fresh_outcome_opened=false
observed_autodl_free_bytes=48252592128
current_v25_phase=A1_1_R0_1_bounded_decision_package
next_work_target=ultra_read_only_A1_1_R0_1_review_before_full_config_preflight_release

## Stage A1.1/R0.1 Semantic-v3 and Full-R Authority Correction

Ultra blocked even the 1,500-config preflight after demonstrating that semantic
payload v2 serialized `initial_heading_local_rad=round(atan2(...),6)`. The
formal `unprotected_turn_oncoming_conflict` family uses an exact opposite
heading, so `+pi` and `-pi` produced different semantic-clone hashes under a
rigid SE(2) transform: 93 of the 201 audited rotations mismatched. That would
have contaminated semantic-block deduplication, block weighting, split-overlap
checks, and later scale support. No full-config preflight, full corpus, training,
calibration, Scene/V2I runtime, or Fresh outcome had started.

The implementation source is
`cc5eb0a7d16d2041b0ee26ad7127a9340dce0c1d`; fixed DP remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. Semantic payload v3 replaces the
branch-cut scalar with the rounded route-local heading unit vector. Exact
opposite-heading, wraparound, a 201-angle sweep, 64 additional random rigid
transforms, actor reordering, source/ID clones, forbidden outcome/future fields,
and the formal unprotected-turn materializer now pass. The source/ID/outcome
independent geometry contract and all 14 approved atoms remain unchanged; no
DP code, K8 candidate, trajectory, generation scale, convex score, or no-V2I
policy changed.

The bounded producer/reviewer contract is now versioned v3. JSON masks must be
native booleans with exact `[8]` and `[8,14]` shapes; candidate source-valid is
recomputed as `atom_source_valid.all(axis=1)`, physical feasibility must be a
subset, non-applicable signal atoms must be exactly zero, and all-K-bad rows
remain in the denominator. The reviewer validates the complete float32
`[8,80,4]` K8 tensor and heading envelope, then independently recomputes raw
atom column 12 from the saved K8 tensor, the certified causal stop-line input,
and `dt=0.1`. Wrong/nearby/missing/multiple stop-line, phase, chain, mask, and
heading mutations fail closed.

The future full-R boundary was hardened but not opened. A preflight/execute
release must bind all seven prerequisite artifacts, their exact inventory,
`run.exit`, HEADS, statuses, and cross-links, plus the rejected partial root.
The immutable implementation HEAD may differ from a later pointer/docs HEAD
only for `diffusion_planner_current_status.md`, this audit, and their pointer
test, while a fixed critical runner/core/config/model-asset SHA manifest must
stay exact. Preflight and execute now share the corpus lock from before output
creation through report, `run.exit`, and seal. Each release has a unique nonce
and exact output directory, and replay fails. The independent full-config
reviewer no longer imports the producer's receipt builder/hash: it reopens the
sealed formal plan, actual maps/routes, source chains, template, scales,
weights, and fixed-DP assets to rebuild the ordered 1,500 executable receipts
and 153 retained-ineligible receipts. The deliberately minimal self-signed
1,500-ID artifact is rejected. None of this constitutes a full-config
preflight release.

The prior semantic-v2 seven-root chain remains immutable and was rehashed at
its original values: `d9892900...`, `836d5468...`, `a37fd179...`, `e099837b...`,
`e28c5851...`, `a520f86c...`, and `81a0c1ac...`. The replacement decision
explicitly lists all seven as superseded diagnostic evidence; they cannot
authorize a later release. S0.1/A0 and the rejected stopped-corpus root remain
unchanged.

### Replacement seven-root bounded package

All replacement artifacts are versioned, sealed, `run.exit=0`, strict-inventory
verified, and bind the same implementation source HEAD:

- decision: `/root/autodl-tmp/camp_dp_v25_ultra_stage_a11_r01_decision_cc5eb0a7_20260717T234441CST`
  / `010f644cc106cb63b479845fa67b59985575df14d9583d7f9164816ac885e73c`;
- 14-row ledger: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a11_cc5eb0a7_20260717T234441CST`
  / `9a7d0b663b5946eb4180f707198e3372d9f20a85dd6eea70ba035ce276a362e5`;
- independent ledger validation: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a11_cc5eb0a7_20260717T234441CST`
  / `85cd4513721e5c8546934aedb34a39fcdb4c99a1318cd2c1fa1fc722acb893bc`;
- 21-red plus one no-signal source authority: `/root/autodl-tmp/camp_dp_v25_r01_authority_source_cc5eb0a7_20260717T234441CST`
  / `ae728cd3781fce5f01afae0bd3411d051e2b657e52b7044de10f3d5b4a8d5b8a`;
- independent source review: `/root/autodl-tmp/camp_dp_v25_r01_authority_source_review_cc5eb0a7_20260717T234441CST`
  / `485e00fcf063f745d415c34e1d762cac62deca84abf027cfa48d8e830cb6ec52`;
- 22x64 sequential-K8 producer: `/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_cc5eb0a7_20260717T234441CST`
  / `b7dc7fe00d21af71caba172eac9edf5500fb967e7379b712024600c62b9e5458`;
- independent bounded review: `/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_review_cc5eb0a7_20260717T234441CST`
  / `6eee9f157d1668ad37120b3a9542f1e5b5661f9077b0fb15cdb5e4a4b43f35d2`.

Their machine-level seven-root binding SHA is
`0c84450c216032686d667209b781cc9b39e68554fd5868eac0aaf0ef725e37ff`.
The bounded run restarted at identity 0 and again completed exactly 22
identities and 1,408 ticks. It did not create a 1,500-config preflight or any
full-R release/worker/monitor. The red census remains four source-map files,
nine physical signatures, five stop-line geometry SHAs, and 21 validated
identity-chain receipts; 21 is not claimed as 21 independent intersections.

Local Python 3.12 passed the 16 targeted learned/static 14D fallback tests (134
deselected) and 63 focused V25 tests with one platform skip; AutoDL Python 3.9
passed the same 16 targeted tests and all 64 focused V25 tests. Pycompile and
`git diff --check` passed. The Windows full integration
file reached 37 passing tests before the local Torch DLL aborted the process;
the authorized targeted fallback subset was then rerun cleanly and this host
limitation is not treated as scientific evidence. At the sealed-package check,
worker count was zero, GPU compute count was zero, the lock was free, disk free
was 48,042,119,168 bytes, and Fresh/outcome remained unopened. The legacy red
outcome evaluator's 10 m line heuristic remains a calibration/Fresh-B2 hard
gate. The next target is Ultra read-only review; full-config preflight remains
blocked until an explicit separate release.

current_v25_status=v25_a11_r01_semantic_v3_bounded_pass_ultra_review_required
current_v25_source_head=cc5eb0a7d16d2041b0ee26ad7127a9340dce0c1d
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_cc5eb0a7_20260717T234441CST
current_v25_artifact_root_sha256=b7dc7fe00d21af71caba172eac9edf5500fb967e7379b712024600c62b9e5458
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_r01_red21_nonsignal1_sequential_k8_review_cc5eb0a7_20260717T234441CST
current_v25_review_artifact_root_sha256=6eee9f157d1668ad37120b3a9542f1e5b5661f9077b0fb15cdb5e4a4b43f35d2
current_v25_ultra_stage_a_decision_artifact_root_sha256=010f644cc106cb63b479845fa67b59985575df14d9583d7f9164816ac885e73c
current_v25_atom_ledger_artifact_root_sha256=9a7d0b663b5946eb4180f707198e3372d9f20a85dd6eea70ba035ce276a362e5
current_v25_atom_ledger_validation_artifact_root_sha256=85cd4513721e5c8546934aedb34a39fcdb4c99a1318cd2c1fa1fc722acb893bc
current_v25_r0_authority_source_artifact_root_sha256=ae728cd3781fce5f01afae0bd3411d051e2b657e52b7044de10f3d5b4a8d5b8a
current_v25_r0_authority_source_review_artifact_root_sha256=485e00fcf063f745d415c34e1d762cac62deca84abf027cfa48d8e830cb6ec52
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_seven_root_bindings_sha256=0c84450c216032686d667209b781cc9b39e68554fd5868eac0aaf0ef725e37ff
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v4.json
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_physical_signature_count=9
current_v25_r0_stop_line_geometry_sha256_count=5
current_v25_r0_probe_identity_count=22
current_v25_r0_probe_tick_count=1408
current_v25_r0_non_signal_identity_count=1
current_v25_full_config_preflight_started=false
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_b2_opened=false
current_v25_fresh_outcome_opened=false
observed_autodl_free_bytes=48042119168
current_v25_phase=A1_1_R0_1_semantic_v3_bounded_decision_package
next_work_target=ultra_read_only_A1_1_R0_1_semantic_v3_review_before_full_config_preflight_release

## Stage A1.2/R0.2 Canonical-Byte, Lock, and Independent-Authority Correction

Ultra did not release the 1,500-config preflight after reviewing the semantic-v3
package. The `cc5eb0a7...` seven-root chain remains immutable but is superseded
diagnostic evidence: producer canonical JSON omitted a final LF while the
reviewer included one; the outer corpus lock would reject its own second-FD
free probe on Linux; and several reviewer paths still accepted self-consistent
but scientifically false route/source or numeric payloads. No 1,500-config
preflight, full-R worker, monitor, training, calibration, Scene/V2I runtime, or
Fresh outcome existed, so no full-corpus or holdout evidence was contaminated.

Implementation source HEAD
`ed7152fd4a0af39949aefc36e21fb003cbcf3ed2` freezes canonical JSON bytes as
UTF-8, sorted keys, preserved Unicode, compact separators, `allow_nan=False`,
and exactly one trailing LF. The golden vector `{"a":1}\n` hashes to
`e346432021b04179518d9614f3560ccd71354a4ee101ddcb893d6959a9d6301c`.
Producer and independent reviewer round trips cover config, semantic,
retained-ineligible, and seven-root namespaces; missing/extra/mutated bytes fail.
The bounded preflight now relies only on the outer lock held before output-dir
creation through report, `run.exit`, and seal. A real AutoDL `flock` test proved
the owning path continues, a second process is rejected, and exception/terminal
exit releases the lock.

The full-config reviewer independently reopens the formal case, real route
pickle, source map, lanelets, certified stop line, template, generation scales,
static weights, DP checkpoint/args, and seven prerequisite roots. It rebuilds
route serialization, route-local semantic-v3 payloads, signal/no-signal chains,
and ordered executable/retained roots without the producer canonical helper.
Re-signed v2 payloads, wrong ego speed/actor/route/stop line, numeric strings or
booleans, nonfinite/ragged arrays, HEAD/cross-link/status/schema conflicts,
incomplete self-signed universes, and nonce replay fail closed. The bounded red
reviewer implements its own scalar red-stopping oracle from the saved K8 tensor,
certified stop-line midpoint/tangent, `dt=0.1`, and frozen constants; monkeypatching
the production helper cannot make the reviewer pass. `all_k_high_risk` is exactly
`source_valid.all() and not physical_feasible.any()`; partial-source/no-physical
rows are source-ineligible rather than all-K-high-risk.

The sealed formal plan is authoritative for seed 25001. A control-plane phrase
mentioned 20260716, but the live sealed formal artifact contains 25001 for every
executable case; A1.2 therefore verifies 25001 and treats 20260716 as a mutation
that must fail instead of overriding the sealed input. Fixed DP remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, K=8 sequential candidate semantics,
candidate0 operational-default alias, no-V2I, source-valid progress, all 14 atoms,
and `[0,10]` canonical clipping are unchanged.

### A1.2/R0.2 replacement seven-root bounded package

All seven new roots are immutable, `run.exit=0`, recursively strict-inventory
verified, cross-linked to the same implementation HEAD, and include rejected
partial root `a2f69cd...`. The previous `010f644c...`, `9a7d0b66...`,
`85cd4513...`, `ae728cd3...`, `485e00fc...`, `b7dc7fe0...`, and `6eee9f15...`
roots were not deleted or rewritten and are listed by the new decision as
superseded diagnostic evidence.

- A1.2 decision: `/root/autodl-tmp/camp_dp_v25_ultra_stage_a12_r02_decision_ed7152fd_20260718T022109CST`
  / `9735a52763e7ef61f516c65445d4f02057cf0fb0beda443354b07e6d69cbe54e`;
- 14-row ledger: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a12_ed7152fd_20260718T022109CST`
  / `76b21380fb66ffb2d90f6bd9adbccf887ea34458caf3383226ea8d17f6a1a833`;
- independent ledger validation: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a12_ed7152fd_20260718T022109CST`
  / `6e5847cf600048948e778330dd7aad3d7ea8aeb44f0e7e1070a83782114e87dd`;
- 21-red plus one no-signal source authority: `/root/autodl-tmp/camp_dp_v25_r02_authority_source_ed7152fd_20260718T022109CST`
  / `b705b826324a449eab87af36a1dd9325f3f773ebe6a3b14f8b437dc45478e7c8`;
- independent source review: `/root/autodl-tmp/camp_dp_v25_r02_authority_source_review_ed7152fd_20260718T022109CST`
  / `04d28ed769625f3db23ba2e9646384014817d4bb58196efae358ee2230677682`;
- 22x64 sequential-K8 producer: `/root/autodl-tmp/camp_dp_v25_r02_red21_nonsignal1_sequential_k8_ed7152fd_20260718T022201CST`
  / `1e84bf5bf35fa0dfea601b4e304b863cfabd0a5d3b1b8ee74e2cb7115c1f60cd`;
- independent bounded review: `/root/autodl-tmp/camp_dp_v25_r02_red21_nonsignal1_sequential_k8_review_ed7152fd_20260718T022201CST`
  / `27086204937a9501979bfcdb943be31f7e2be45d60bb7710508633e2af39bcfa`.

The exact seven-root binding hashes to
`5772e347bf82c3a13a1b3399acfafe86c8063abeaf8b6a284802d628e98d758f`.
The new bounded run restarted from identity0 and completed 22 identities and
1,408 ticks. Source authority still reports four source-map files, nine physical
signatures, five stop-line geometry SHAs, and 21 validated identity chains; 21
is not claimed as 21 independent intersections. Atom validation remains 9 PASS,
5 WARN, 0 FAIL, preserving the complete approved 14D schema.

Local focused evidence was 105 passed/2 platform skips, 33 additional fallback
tests passed, and all 14 pointer/audit tests passed. The combined local suite
that imports Torch still aborts at the known Windows Torch DLL boundary and is
not counted as scientific evidence. AutoDL passed all 107 focused tests, all 16
targeted fallback tests, and the dedicated real-flock probe. Pycompile and
`git diff --check` passed. At final sampling CAMP local/origin/GitHub/AutoDL
shared implementation HEAD `ed7152fd...`; DP was fixed/clean, worker and GPU
counts were zero, the lock was free, free disk was 47,831,265,280 bytes, and
Fresh/outcome remained unopened. This bounded PASS is not a full-config
preflight release. The next gate is Ultra read-only A1.2/R0.2 review.

current_v25_status=v25_a12_r02_bounded_pass_ultra_review_required
current_v25_source_head=ed7152fd4a0af39949aefc36e21fb003cbcf3ed2
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_r02_red21_nonsignal1_sequential_k8_ed7152fd_20260718T022201CST
current_v25_artifact_root_sha256=1e84bf5bf35fa0dfea601b4e304b863cfabd0a5d3b1b8ee74e2cb7115c1f60cd
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_r02_red21_nonsignal1_sequential_k8_review_ed7152fd_20260718T022201CST
current_v25_review_artifact_root_sha256=27086204937a9501979bfcdb943be31f7e2be45d60bb7710508633e2af39bcfa
current_v25_ultra_stage_a_decision_artifact_root_sha256=9735a52763e7ef61f516c65445d4f02057cf0fb0beda443354b07e6d69cbe54e
current_v25_atom_ledger_artifact_root_sha256=76b21380fb66ffb2d90f6bd9adbccf887ea34458caf3383226ea8d17f6a1a833
current_v25_atom_ledger_validation_artifact_root_sha256=6e5847cf600048948e778330dd7aad3d7ea8aeb44f0e7e1070a83782114e87dd
current_v25_r0_authority_source_artifact_root_sha256=b705b826324a449eab87af36a1dd9325f3f773ebe6a3b14f8b437dc45478e7c8
current_v25_r0_authority_source_review_artifact_root_sha256=04d28ed769625f3db23ba2e9646384014817d4bb58196efae358ee2230677682
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_seven_root_bindings_sha256=5772e347bf82c3a13a1b3399acfafe86c8063abeaf8b6a284802d628e98d758f
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1
current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v4
current_v25_snapshot_schema=camp_dp_v25_controlled_training_snapshot_v4
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v4.json
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_physical_signature_count=9
current_v25_r0_stop_line_geometry_sha256_count=5
current_v25_r0_probe_identity_count=22
current_v25_r0_probe_tick_count=1408
current_v25_r0_non_signal_identity_count=1
current_v25_full_config_preflight_started=false
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_b2_opened=false
current_v25_fresh_outcome_opened=false
observed_autodl_free_bytes=47831265280
current_v25_phase=A1_2_R0_2_bounded_decision_package
next_work_target=ultra_read_only_A1_2_R0_2_review_before_full_config_preflight_release

## Stage A1.3/R0.3 Canonical Snapshot and Exact Authority Correction

Ultra kept full-config preflight closed after A1.2/R0.2 because the real
snapshot writer appended a second LF, the seven-root verifier checked several
field names without freezing their values, and the future full-config reviewer
did not independently anchor the unique formal/template universe. The A1.2/R0.2
seven roots remain immutable superseded diagnostic evidence. No preflight
release or nonce, 1,500-config preflight, full-R worker, monitor, training,
calibration, Scene/V2I runtime, or Fresh outcome was created.

Implementation commits `907fa90cb613babbfa205c54ac9a26691c4f3864` and
`6efa44ed576363b842396b94587ab800493e276f` form the A1.3/R0.3 correction;
the latter is the immutable implementation source HEAD for the bounded package.
The real snapshot writer now delegates to one V25 serializer and writes exactly
one trailing LF. The golden `{"a":1}\n` byte vector remains
`e346432021b04179518d9614f3560ccd71354a4ee101ddcb893d6959a9d6301c`.
A real one-identity, 64-tick write/read/index/seal regression checks raw bytes,
the content-addressed filename, and `_canonical_sha256(payload)`. The corpus
reviewer uses a local canonical oracle and rejects double-LF, noncanonical, or
misnamed snapshot bytes rather than accepting a successful JSON parse alone.

The seven-root authority verifier now derives per-role exact values and exact
cross-root bindings. Mutation coverage includes the four live counterexamples:
`training_executed=true` in the source root, `calibration_executed=true` in the
bounded-review root, a null fixed-DP HEAD, and conflicting decision/source
formal roots. It also mutates every frozen flag, nested authority, HEAD,
fixed-DP/formal/A0/S0.1/rejected root, path/root cross-link, and denominator.
The independent full-config reviewer freezes the official formal artifact and
root, probe template SHA, generation scales/static weights, DP repository,
checkpoint, arguments, native-source hashes, and fixed DP HEAD. It independently
checks the formal schema and exact 1,653 train rows: 1,500 executable plus 153
retained-ineligible, all with train role/split and seed 25001. A complete,
internally self-consistent, re-signed alternate formal/template/map/route/release
universe is rejected.

### A1.3/R0.3 replacement seven-root bounded package

All seven roots were produced from identity0 under implementation source HEAD
`6efa44ed576363b842396b94587ab800493e276f`, have `run.exit=0`, pass recursive
strict-inventory verification, and bind the fixed DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. The prior A1.2/R0.2 roots are
preserved and listed as superseded diagnostic evidence.

- decision: `/root/autodl-tmp/camp_dp_v25_ultra_stage_a13_r03_decision_6efa44ed_20260718T032112CST`
  / `1b2dd591e342fdfa0d88f05a2d2537bc8f51292d71502a22e701147cee15488c`;
- 14-row ledger: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a13_6efa44ed_20260718T032112CST`
  / `02529652c60e5843c2bb5568222291e5e3b5884fc218ab2e3cd0884810620ae4`;
- independent ledger validation: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a13_6efa44ed_20260718T032112CST`
  / `e2f7f484bdbb18d9eac7963cc7737cc6f39fc6427deb39e07a62060a9ecdc2a0`;
- source authority: `/root/autodl-tmp/camp_dp_v25_r03_authority_source_6efa44ed_20260718T032112CST`
  / `c7375c3539727abf7b5a726b437bcb643de96fcbf2911b966bfa5e13f20881f8`;
- independent source review: `/root/autodl-tmp/camp_dp_v25_r03_authority_source_review_6efa44ed_20260718T032112CST`
  / `7d6308d5f3b36a3ec3925ffe1a3ef929f5e45940429e117b8fe52837a4e2f332`;
- 22x64 sequential-K8 producer: `/root/autodl-tmp/camp_dp_v25_r03_red21_nonsignal1_sequential_k8_6efa44ed_20260718T032112CST`
  / `50ae46bb76f76e07bac6a91405e30cade7bdfd715cf417a6e7d5931cdaaa3878`;
- independent bounded review: `/root/autodl-tmp/camp_dp_v25_r03_red21_nonsignal1_sequential_k8_review_6efa44ed_20260718T032112CST`
  / `c07e1c4cd63db8aaa21118925e7a78bbb2b6c1687ecbaf4939047057863979b1`.

The exact seven-root binding hash is
`4c9a4a666506195aef0ff556858a1fda942cf094c9824abdde827e47e83cc9f5`.
The bounded artifact completed 22 identities and 1,408 ticks. Source authority
still records four map files, nine physical signatures, five stop-line geometry
SHAs, and 21 validated identity-chain receipts; it does not call these 21
independent intersections. Atom validation remains 9 PASS, 5 WARN, 0 FAIL.

Local evidence is 108 passed with two platform skips plus two fixed-K8 fixture
tests. AutoDL passed 115 V25 tests, all 150 integration tests, 16 targeted
fallback tests, and the real Linux flock test. Pycompile, JSON validation, exact
seven-root verification, and `git diff --check` passed. At the bounded evidence
sample, worker/GPU counts were zero, the lock was free, disk free was
47,620,890,624 bytes, and Fresh/outcome remained unopened. This is not a
full-config preflight release: full-config preflight remains blocked until an
explicit separate Ultra release. The next gate is Ultra read-only A1.3/R0.3
review.

current_v25_status=v25_a13_r03_bounded_pass_ultra_review_required
current_v25_source_head=6efa44ed576363b842396b94587ab800493e276f
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_r03_red21_nonsignal1_sequential_k8_6efa44ed_20260718T032112CST
current_v25_artifact_root_sha256=50ae46bb76f76e07bac6a91405e30cade7bdfd715cf417a6e7d5931cdaaa3878
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_r03_red21_nonsignal1_sequential_k8_review_6efa44ed_20260718T032112CST
current_v25_review_artifact_root_sha256=c07e1c4cd63db8aaa21118925e7a78bbb2b6c1687ecbaf4939047057863979b1
current_v25_ultra_stage_a_decision_artifact_root_sha256=1b2dd591e342fdfa0d88f05a2d2537bc8f51292d71502a22e701147cee15488c
current_v25_atom_ledger_artifact_root_sha256=02529652c60e5843c2bb5568222291e5e3b5884fc218ab2e3cd0884810620ae4
current_v25_atom_ledger_validation_artifact_root_sha256=e2f7f484bdbb18d9eac7963cc7737cc6f39fc6427deb39e07a62060a9ecdc2a0
current_v25_r0_authority_source_artifact_root_sha256=c7375c3539727abf7b5a726b437bcb643de96fcbf2911b966bfa5e13f20881f8
current_v25_r0_authority_source_review_artifact_root_sha256=7d6308d5f3b36a3ec3925ffe1a3ef929f5e45940429e117b8fe52837a4e2f332
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_seven_root_bindings_sha256=4c9a4a666506195aef0ff556858a1fda942cf094c9824abdde827e47e83cc9f5
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1
current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v4
current_v25_snapshot_schema=camp_dp_v25_controlled_training_snapshot_v4
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v4.json
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_physical_signature_count=9
current_v25_r0_stop_line_geometry_sha256_count=5
current_v25_r0_probe_identity_count=22
current_v25_r0_probe_tick_count=1408
current_v25_r0_non_signal_identity_count=1
current_v25_full_config_preflight_started=false
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_b2_opened=false
current_v25_fresh_outcome_opened=false
observed_autodl_free_bytes=47620890624
current_v25_phase=A1_3_R0_3_bounded_decision_package
next_work_target=ultra_read_only_A1_3_R0_3_review_before_full_config_preflight_release

## Stage A1.4/R0.4 Type-Exact Authority and Snapshot Schema Correction

Ultra kept full-config preflight closed after A1.3/R0.3 because Python equality
accepted `false == 0`, `true == 1`, and equal-valued integers/floats; nested
ledger control maps and two future reviewers also admitted re-signed type or
unknown-field drift. Commits `10943e86c1ca340b6325f9902e86fbaaa19fa2d7`,
`7ca89e1e17b6b7efe71e4cb274677f3e52ca98af`, and
`70c04b45e5c9416a14f099e1cc87f70c0d3f6936` form the bounded correction. The
last is the immutable implementation source HEAD for the replacement package.
No full-config preflight release, nonce, 1,500-config preflight, full-R worker,
monitor, training, calibration, Scene/V2I runtime, or Fresh outcome was created.

The seven-root verifier now uses recursive JSON-native type equality: booleans,
integers, and floats are distinct; dictionaries require exact keys; lists
require exact length, order, and element types. `a11_ledger.authority` and
`stage_boundaries` have frozen nested key sets, and unregistered nested gate,
Fresh, outcome, future, holdout, label, or ID-proxy fields fail closed. The
mutation matrix includes all five live type-smuggling examples, a nested
`full_r_authorized` insertion, and a nested boolean-to-integer drift.

The future full-config reviewer independently requires native integer counts,
seed 25001 as an exact `list[int]`, and native boolean gates. Source/report,
formal summary, retained-ineligible receipts, and all 1,500 config receipts use
type-exact comparison. It enforces `reported root == hash(actual receipts) ==
hash(independently rebuilt receipts)` and independently removes then recomputes
every row's `config_authority_sha256`. Resigned float seeds/counts, false-to-zero
gates, forged row SHAs, an actual/expected root mismatch, and `[25001.0]` are
rejected.

The final corrected-corpus reviewer is now part of the critical implementation
manifest. It freezes exact four-field snapshot-index rows plus versioned
top-level, `feature_payload`, `sidecar`, and candidate0-identity schemas; all
discrete types are native JSON types. Unknown
future/outcome/label/holdout/ID-proxy fields at any nesting level, deleted or
misnamed hash fields, and
bool/int/float drift fail closed. Its local canonical-byte oracle and the
single-LF writer contract remain independent and unchanged. The atom-ledger
plan is versioned as
`configs/integrations/diffusion_planner_v25_atom_ledger_plan_v5.json` so its DAG
names A1.4/R0.4 without rewriting the immutable v4 plan.

The first A1.4/R0.4 seven-root chain under `7ca89e1e...` was fully sealed and
type-clean, but the final machine-chain call rejected it because the legitimate
pre-existing `a11_validation.contract_checks.r_and_fresh_closed` path was not
in the new explicit allowlist. The seven roots below remain immutable
superseded diagnostic evidence and were added to the replacement decision's
`superseded_diagnostic_roots`; none was joined to the final chain:

- `b92026ff87523e6d2be1fb583d99052eec628e1b8a39a18d4167d580be0f739f`;
- `a692d57ee7d08b6cf563472e6cc98ec16a1f06babecd5da47bed715e3eba6cb9`;
- `cd67c79c543dd9baad64e8042d103a91cd00ffd6b6877a42e9c718b6021e75a2`;
- `bd460b74bf8b7040c719caf4b1d8226bc7d8f79b54c185c1a7efa6330d05871d`;
- `4ec520d710a329a0ed728067d0251b744f03a24aa71c1d6e0d4ac7dfab2c0350`;
- `de278472be78e6f6ebec087e36cdf87115047cfab0850213891054499165c105`;
- `71a2be88ab93a8cc6406e20dac8f7eee90717456240fc4e44befb9965343c2a6`.

Only that exact legitimate path was registered. Tests additionally prove an
unknown validation `full_r_authorized` key is still rejected. Because the
implementation HEAD changed, all seven artifacts and all 22x64 sequential-K8
records were rebuilt again from identity0; no prefix/suffix reuse occurred.

### A1.4/R0.4 replacement seven-root bounded package

All seven roots bind implementation source HEAD
`70c04b45e5c9416a14f099e1cc87f70c0d3f6936`, fixed DP HEAD
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, S0.1/A0/formal authorities,
and rejected partial root
`a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481`.
Each has `run.exit=0` and passed recursive exact-inventory verification.

- decision: `/root/autodl-tmp/camp_dp_v25_ultra_stage_a14_r04_decision_70c04b45_20260718T042453CST`
  / `baaf879f1eac5579a1029c2eb046dc125d8c82e7677f904b2b41dd8bfcd00947`;
- 14-row ledger: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a14_70c04b45_20260718T042453CST`
  / `5d7ff800eb79a9d8cd1b6b91af0d9fb239d654c9661a65e3bdda83d69046d214`;
- independent ledger validation: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a14_70c04b45_20260718T042453CST`
  / `ac557c902d9aa5069059e20072e3853f85a9c9f6a69f3b3d350d936bd0e1ab93`;
- source authority: `/root/autodl-tmp/camp_dp_v25_r04_authority_source_70c04b45_20260718T042453CST`
  / `1f2b042887bb9499f4af4b2c8cfff1000d0229988cde98cea91a8e7be54c9414`;
- independent source review: `/root/autodl-tmp/camp_dp_v25_r04_authority_source_review_70c04b45_20260718T042453CST`
  / `9055042f5503e7b1e23067691d516e1933557dac7c3b5baf99bce893ea393069`;
- 22x64 sequential-K8 producer: `/root/autodl-tmp/camp_dp_v25_r04_red21_nonsignal1_sequential_k8_70c04b45_20260718T042453CST`
  / `1afd6ccfe1dda380be1b3d912515cb112e8c315e1cf9a9a1e45bbbe069666106`;
- independent bounded review: `/root/autodl-tmp/camp_dp_v25_r04_red21_nonsignal1_sequential_k8_review_70c04b45_20260718T042453CST`
  / `55ff4688dc4926348e26b8e9e161f4203c816eb8829dea974396f4f0aaa32b88`.

The type-exact machine verifier accepted all seven roles and their cross-links;
the binding root is
`6fc039adb7aa21bed58a8ca6aa97dae944332566b37b471be015a4a7a933e066`.
Ledger validation remains 9 PASS, 5 WARN, 0 FAIL over the complete approved
14D schema. Source authority remains 21 red identity chains, four source-map
files, nine physical signatures, five stop-line geometry SHAs, and one
non-signal identity. The bounded artifact completed 22 identities and 1,408
ticks. Independent review recomputed K8/default/context hashes, red source
bindings, scalar clip/affine/argmin, candidate0 alias, and immutability.

Local non-Torch V25 tests passed `127` with two platform skips; 20 focused
selector/fallback tests passed. The Windows all-V25 and full integration runs
again stopped at the known Torch DLL boundary and are not counted. AutoDL/Linux
passed all `134` V25 tests, all `150` integration tests, three fallback-ablation
tests, and the dedicated real-flock test. Pycompile, JSON validation, and
`git diff --check` passed. Final live sampling found local/origin/GitHub/AutoDL
at implementation source HEAD `70c04b45...`, CAMP and fixed DP tracked-clean,
worker/GPU counts zero, the corpus lock free, 47,200,604,160 bytes free, and
Fresh/outcome unopened. Full-config preflight remains blocked pending a separate
Ultra read-only release decision.

current_v25_status=v25_a14_r04_bounded_pass_ultra_review_required
current_v25_source_head=70c04b45e5c9416a14f099e1cc87f70c0d3f6936
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_r04_red21_nonsignal1_sequential_k8_70c04b45_20260718T042453CST
current_v25_artifact_root_sha256=1afd6ccfe1dda380be1b3d912515cb112e8c315e1cf9a9a1e45bbbe069666106
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_r04_red21_nonsignal1_sequential_k8_review_70c04b45_20260718T042453CST
current_v25_review_artifact_root_sha256=55ff4688dc4926348e26b8e9e161f4203c816eb8829dea974396f4f0aaa32b88
current_v25_ultra_stage_a_decision_artifact_root_sha256=baaf879f1eac5579a1029c2eb046dc125d8c82e7677f904b2b41dd8bfcd00947
current_v25_atom_ledger_artifact_root_sha256=5d7ff800eb79a9d8cd1b6b91af0d9fb239d654c9661a65e3bdda83d69046d214
current_v25_atom_ledger_validation_artifact_root_sha256=ac557c902d9aa5069059e20072e3853f85a9c9f6a69f3b3d350d936bd0e1ab93
current_v25_r0_authority_source_artifact_root_sha256=1f2b042887bb9499f4af4b2c8cfff1000d0229988cde98cea91a8e7be54c9414
current_v25_r0_authority_source_review_artifact_root_sha256=9055042f5503e7b1e23067691d516e1933557dac7c3b5baf99bce893ea393069
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_seven_root_bindings_sha256=6fc039adb7aa21bed58a8ca6aa97dae944332566b37b471be015a4a7a933e066
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1
current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v4
current_v25_snapshot_schema=camp_dp_v25_controlled_training_snapshot_v4
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v5.json
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_physical_signature_count=9
current_v25_r0_stop_line_geometry_sha256_count=5
current_v25_r0_probe_identity_count=22
current_v25_r0_probe_tick_count=1408
current_v25_r0_non_signal_identity_count=1
current_v25_full_config_preflight_started=false
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_b2_opened=false
current_v25_fresh_outcome_opened=false
observed_autodl_free_bytes=47200604160
current_v25_phase=A1_4_R0_4_bounded_decision_package
next_work_target=ultra_read_only_A1_4_R0_4_review_before_full_config_preflight_release

## Stage A1.5/R0.5 Nested-Control, Corpus-Schema, and Release-Authority Correction

Ultra kept full-config preflight closed after A1.4/R0.4 because several
allowlisted nested controls were only permitted, not required with exact values;
future full-config/final-corpus schemas still admitted some native-type,
receipt, context, candidate0/mask/all-K, nonce/output-path, and critical-manifest
alias drift. Commit `1e1c32c71be4a0672652f8574f7cd62002a3c2b4` is the immutable
A1.5/R0.5 implementation source HEAD. Fixed DP remains
`7a1d33da277a1992ec474b5383a0c963c72e04e4`; no DP code, K8 candidate,
trajectory, atom, progress, or mathematical contract changed.

The seven A1.4/R0.4 roots remain immutable superseded diagnostic evidence and
were not joined to the A1.5/R0.5 chain:

- `baaf879f1eac5579a1029c2eb046dc125d8c82e7677f904b2b41dd8bfcd00947`;
- `5d7ff800eb79a9d8cd1b6b91af0d9fb239d654c9661a65e3bdda83d69046d214`;
- `ac557c902d9aa5069059e20072e3853f85a9c9f6a69f3b3d350d936bd0e1ab93`;
- `1f2b042887bb9499f4af4b2c8cfff1000d0229988cde98cea91a8e7be54c9414`;
- `9055042f5503e7b1e23067691d516e1933557dac7c3b5baf99bce893ea393069`;
- `1afd6ccfe1dda380be1b3d912515cb112e8c315e1cf9a9a1e45bbbe069666106`;
- `55ff4688dc4926348e26b8e9e161f4203c816eb8829dea974396f4f0aaa32b88`.

The exact seven-root verifier now requires all five
`a11_validation.contract_checks` keys as native booleans equal to true. It also
requires the frozen passive-latency microbatch flag and both frozen DAG strings
plus the red outcome-heuristic string. Unknown controls are normalized across
snake_case, camelCase, and hyphenated spellings before rejection, so an alias
cannot evade the closed-gate scan. The mutation suite rejects
`r_and_fresh_closed` as false, zero, or text; value/type mutations of every other
required nested control; and camel/hyphen control extras.

Future full-config authority now requires every identity/count/seed/tick/
capacity field to be a native non-boolean integer and every gate to be a native
boolean. Actual receipts, independently rebuilt receipts, and the reported root
must have identical canonical hashes; every row authority SHA is recomputed.
The future final-corpus reviewer freezes report/progress/results/index/snapshot/
feature/sidecar schemas, exact 26-feature raw-context/source-completeness keys,
and exact context/signal receipt schemas. It rejects IDs, nested schedule/
outcome/label leakage, booleans/strings in numeric tensors, candidate0 or mask/
all-K contradictions, and unknown or mistyped fields. Release nonces are native
64-hex strings; authorized output paths are native canonical absolute strings
equal to the requested path. Critical-manifest raw keys must exactly match the
frozen forward-slash implementation paths, so backslash aliases, duplicates,
and extras fail closed. The plan is versioned as
`configs/integrations/diffusion_planner_v25_atom_ledger_plan_v6.json`.

Local non-Torch V25 tests passed 132 with two platform skips. AutoDL/Linux
passed all 139 V25 tests, all 150 integration tests, three fallback-ablation
tests, and the real Linux flock test. Pycompile, JSON validation, focused
mutation tests, and `git diff --check` passed. The Windows all-V25 collection
still stops at the known Torch DLL boundary and is not counted.

### A1.5/R0.5 replacement seven-root bounded package

All seven roots bind implementation source HEAD `1e1c32c7...`, fixed DP, S0.1,
A0, formal authority, and rejected partial root
`a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481`.
Each has `run.exit=0`, strict recursive exact inventory, exact role schema, and
machine-verified cross-links:

- decision: `/root/autodl-tmp/camp_dp_v25_ultra_stage_a15_r05_decision_1e1c32c7_20260718T051807CST`
  / `0f48f22861721258be945ae42fb10d3fec7f90992addb386c535a1b8001b3e5a`;
- 14-row ledger: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a15_1e1c32c7_20260718T051807CST`
  / `5e762a14b53c6c81f6bb3bfa67c6aeeb7fa5fe603bb95fa0776d75035cb8311c`;
- independent ledger validation: `/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a15_1e1c32c7_20260718T051807CST`
  / `641fadb24926cb7e6fc49c98d66f6a0a9528f41856b0417aae9e6fb9a80fa469`;
- source authority: `/root/autodl-tmp/camp_dp_v25_r05_authority_source_1e1c32c7_20260718T051807CST`
  / `372dd7a9d248e9a70b00c188b87053c33e2333533639d618461b17e21aa06632`;
- independent source review: `/root/autodl-tmp/camp_dp_v25_r05_authority_source_review_1e1c32c7_20260718T051807CST`
  / `6d74c0739a042c16af2eb4bc3a50888ddbc3291a659572096dcbe9bc1c42bcb5`;
- 22x64 sequential-K8 producer: `/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_1e1c32c7_20260718T051807CST`
  / `694ddcde9bd5972c4fb95eeb45da7f46663bb3a6acb87ca5b4cc18abbf97b79c`;
- independent bounded review: `/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053800CST`
  / `7dc54a3d9baa3d818284ffdcb3ed1192c0805d93ea7019c6975c86cba20fe47f`.

The exact seven-root binding hash is
`4c3410f5c4f123e08e63a18cef10c366911fef7f454f74dbc2532d20db3dd396`.
Ledger validation remains 9 PASS, 5 WARN, 0 FAIL over all approved 14 atoms.
Source authority remains 21 red identity chains, four source-map files, nine
physical signatures, five stop-line geometry SHAs, and one non-signal identity.
The bounded artifact was rebuilt from identity0 and completed 22 identities and
1,408 ticks. Independent review recomputed K8/default/context hashes, red source
bindings, scalar clip/affine/argmin, candidate0 operational-default alias,
masks/all-K state, and immutability.

The first reviewer invocation supplied a source-review root string with one
missing character. It failed closed before reviewing producer ticks and sealed
the failure at
`/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053400CST`
with root
`d3cf28b2f62814b89e9b6debace6e3f87a14d5a3b9c38eabd92a50e059b1cab5`.
It remains diagnostic evidence and is not a prerequisite root.

Final live sampling found local/origin/GitHub/AutoDL at implementation source
HEAD `1e1c32c7...`, CAMP and fixed DP tracked-clean, worker/GPU counts zero, the
corpus lock free, and 46,990,168,064 bytes free. No full-config release nonce or
output, full-config preflight, full R, monitor, training, calibration,
Scene/V2I, Fresh B2, or outcome exists. The next gate is Ultra read-only
A1.5/R0.5 review; no subsequent stage is authorized.

## Stage A1.6/R0.6 Route-Level Signal-Authority Source-Only Correction

Ultra released one preflight-only nonce after A1.5/R0.5. The corresponding
release artifact is sealed at
`/root/autodl-tmp/camp_dp_v25_ultra_full_config_preflight_release_1e1c32c7_5f919a54290957e2`
with root
`cb8733b4c81a2071a82c37caf74fa06586f51d7d9c1b7c3c0722f824029b33b1`.
The exact nonce
`5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e`
was consumed once. Full-config preflight then correctly failed closed before
model or simulator construction and before candidate generation, training,
calibration, Fresh, or outcome access. The sealed failed artifact is
`/root/autodl-tmp/camp_dp_v25_full_config_preflight_1e1c32c7_5f919a54290957e2`
with root
`b2022b6eb363023ce4ad842aefebb95c7d575a5101d822c0bdf874890758b62d`;
its error is `non-red identity lacks a qualified same-tick mapped signal
source`. Independent full-config review was not run. The release, failure, and
consumed marker are immutable diagnostic evidence; the nonce is permanently
invalid and no output may be retried or spliced.

Ultra's outcome-blind read-only census found exact actual route classification
of 146 mapped-signal and 1,354 no-signal identities across the sealed 1,500
executable train universe, with no mismatch against the formal mapped flag.
The mapped set is 21 controlled red-family identities plus 125 non-red
identities. All 125 have exactly one TrafficLightRegulatoryElement, physical
light/bulbs, a certified stop line, and a legal controlled-lanelet route
projection. Their formal `phase=none` means no scenario phase override; it does
not prove a no-signal route. Therefore Ultra selected route-level option A and
rejected blanket source-ineligible reclassification.

This gate authorizes only a versioned family-independent mapped-signal static
authority, same-tick controlled-override versus observed-request phase modes,
strict current-phase/timestamp receipts, and a no-model/no-simulator/
no-candidate/no-DP-forward full-universe source census with an independent
reviewer. The original 1,500 executable plus 153 retained denominator remains
unchanged. A1.5's seven roots remain immutable history but their binding is not
sufficient for the full universe; source/source-review/bounded/bounded-review
must be rebuilt under a later Ultra gate. This gate does not run any K8 root.
Full-config release/nonce, full R, monitor, training, calibration, Scene/V2I,
Fresh, outcome, and V24 holdout reads remain closed.

After the original AutoDL endpoint recovered, a read-only recovery preflight
reverified the instance identity, clean CAMP and fixed-DP worktrees, the sealed
formal plan, consumed release and nonce marker, failed preflight, all seven A1.5
parent roots, worker/GPU/lock state, disk floor, and unopened Fresh/outcome
state. The remote CAMP checkout was then synchronized ff-only to source HEAD
`53b07e309c03d8d0a491121b4b135f80fccbbc3d`. The first complete V25 test run
found one stale historical A1.5 pointer assertion; commit `53b07e309...` corrected
only that assertion to the historical prose still present in this audit. AutoDL
py_compile and all 165 V25 tests then passed.

The source-only census is sealed at
`/root/autodl-tmp/camp_dp_v25_a16_r06_route_signal_source_census_53b07e30_20260718T104858CST`
with root
`c93af9687c0c4c50e62d396311d3d10e0b8e953453186b0dde6b1aa21ecf51db`.
It preserved all 1,653 formal train identities: 1,500 executable and 153
retained. The executable universe is exactly 146 mapped-signal routes and 1,354
no-signal routes. The mapped set is exactly 21 controlled-same-tick overrides
plus 125 observed-same-tick request phases. Source failures are zero.

The independent review is sealed at
`/root/autodl-tmp/camp_dp_v25_a16_r06_route_signal_source_review_53b07e30_20260718T104923CST`
with root
`0797f4dfbbe947eed7296249e0b904ed91cfde323f1e775f2e189100e3e2c73e`.
It independently rebuilt map/route classification, regulatory element to
physical-light/bulb/controlled-lanelet/stop-line/route-arc chains, same-tick
route/map tensors, controlled override readback, observed phase receipts, and
receipt/supplement roots. Producer and reviewer both exited zero and their
strict seal inventories were reverified. Neither loaded a model, started a
simulator, generated a candidate, executed a DP forward, trained, calibrated,
read Fresh/outcome, or authorized a claim. Terminal sampling found worker=0,
GPU=0, lock free, both repos tracked-clean, fixed DP unchanged, and
46,981,681,152 bytes free. Bounded K8 and all later gates remain closed pending
Ultra read-only A1.6/R0.6 review. Its historical next target was
`ultra_read_only_A1_6_R0_6_source_package_review_before_bounded_coverage_gate`.

## Stage A1.6.1 Machine-Authority and Production-Integration Correction

Ultra accepted the A1.6 scientific census while withholding machine authority.
The prior source and review roots remain immutable scientific diagnostic
evidence, but they are ineligible to authorize a later bounded K8 run. Source
HEAD `4d0cfe6e2e1f46bd6a8d6a73ace724121660f415` now freezes the exact six-file
source and four-file review inventories, the canonical one-shot consumed
marker, fixed-DP imported-module provenance against commit `7a1d33da...`, the
source/pointer dual-HEAD critical manifest, and route-level production signal
semantics independent of scenario family. Observe mode leaves the request
tensor immutable; controlled override is same-tick only and requires readback.

The same implementation also produces an outcome-blind bounded coverage design
that includes all 146 mapped identities and covers no-signal semantic/source
cells, corridor, tensor-layout signature, identity0, and a separate 64-tick
repeat, with a hard ceiling of 320 unique identities. This is design evidence
only: no K8, model, simulator, candidate generation, DP forward, training,
calibration, Fresh, or outcome was run. Local non-Torch V25 tests passed
185 with 2 skipped; the targeted set passed 117 with 1 skipped. The next action
is AutoDL ff-only verification followed only by a fresh 1,653-identity
source-only census and independent review under a later pointer HEAD.

The first producer run under `4d0cfe6e...` sealed the complete source-only
census at
`/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_4d0cfe6e_20260718T115300CST`
with root
`1b8b2dfebaccd9e7071ff04f8e3b1f30c2f2af3677abac6bd02183a94c28064e`.
Its counts were 1,653/1,500/153, 146/1,354, and 21/125 with zero source
failures. The independent reviewer immediately failed closed before sealing:
its exact report schema omitted the two new bounded-design check keys. No K8 or
later stage ran. The source root remains immutable diagnostic evidence only.
Commit `df55b700b4e0e323f2d69d4bac3ec3c1ccd16322` freezes the complete literal
check set and adds a 43-test regression result; a fresh source/review pair is
required from identity0.

The corrected fresh pair under source HEAD `df55b700...` and pointer HEAD
`9f942daa...` passed. The source census is sealed at
`/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_df55b700_20260718T120200CST`
with root
`44c9b094b84c4de5afc3b37439beecc333314042d0d0dee605d2e5c015e7a56a`;
the independent review is sealed at
`/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_review_df55b700_20260718T120200CST`
with root
`1259883e38f628bf62f7595b19b98045e9990cda508af8d6fd334ffe35000728`.
Strict independent revalidation confirmed exact six/four payload inventories,
exit zero, the unchanged 1,653/1,500/153 denominator, 146/1,354 route source
classes, 21/125 phase modes, zero failures, 14 producer checks, and 10
independent checks. The deterministic outcome-blind coverage design selects
243 identities (146 mapped plus 97 no-signal), below the cap. The production
attachment path independently accepted all 1,500 executable cases with the
same counts. Worker/GPU are zero, lock is free, disk free is 46,960,885,760
bytes, both repos are clean, fixed DP is unchanged, and Fresh/outcome is still
unopened. Bounded K8 remains unexecuted pending Ultra review.

current_v25_status=v25_a161_source_only_census_review_passed_ultra_read_only_review_required
current_v25_source_head=df55b700b4e0e323f2d69d4bac3ec3c1ccd16322
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_df55b700_20260718T120200CST
current_v25_artifact_root_sha256=44c9b094b84c4de5afc3b37439beecc333314042d0d0dee605d2e5c015e7a56a
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_review_df55b700_20260718T120200CST
current_v25_review_artifact_root_sha256=1259883e38f628bf62f7595b19b98045e9990cda508af8d6fd334ffe35000728
current_v25_a16_old_source_machine_authority_eligible=false
current_v25_a16_old_source_scientific_diagnostic=true
current_v25_a16_old_source_artifact_root_sha256=c93af9687c0c4c50e62d396311d3d10e0b8e953453186b0dde6b1aa21ecf51db
current_v25_a16_old_source_review_artifact_root_sha256=0797f4dfbbe947eed7296249e0b904ed91cfde323f1e775f2e189100e3e2c73e
current_v25_a161_failed_census_artifact=/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_4d0cfe6e_20260718T115300CST
current_v25_a161_failed_census_root_sha256=1b8b2dfebaccd9e7071ff04f8e3b1f30c2f2af3677abac6bd02183a94c28064e
current_v25_a161_failed_census_machine_authority_eligible=false
current_v25_a161_failed_review_reason=source_census_report_exact_check_key_contract_drift
current_v25_full_config_preflight_release_artifact=/root/autodl-tmp/camp_dp_v25_ultra_full_config_preflight_release_1e1c32c7_5f919a54290957e2
current_v25_full_config_preflight_release_artifact_root_sha256=cb8733b4c81a2071a82c37caf74fa06586f51d7d9c1b7c3c0722f824029b33b1
current_v25_full_config_preflight_consumed_nonce=5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e
current_v25_full_config_preflight_consumed_marker_sha256=0b62753b0b07ea987d78e309fde4ed9d9aeda5e2cf0b25d1107f7c446a1b864d
current_v25_full_config_preflight_failure=non_red_identity_lacks_qualified_same_tick_mapped_signal_source
current_v25_r05_failed_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053400CST
current_v25_r05_failed_review_artifact_root_sha256=d3cf28b2f62814b89e9b6debace6e3f87a14d5a3b9c38eabd92a50e059b1cab5
current_v25_ultra_stage_a_decision_artifact_root_sha256=0f48f22861721258be945ae42fb10d3fec7f90992addb386c535a1b8001b3e5a
current_v25_atom_ledger_artifact_root_sha256=5e762a14b53c6c81f6bb3bfa67c6aeeb7fa5fe603bb95fa0776d75035cb8311c
current_v25_atom_ledger_validation_artifact_root_sha256=641fadb24926cb7e6fc49c98d66f6a0a9528f41856b0417aae9e6fb9a80fa469
current_v25_r0_authority_source_artifact_root_sha256=44c9b094b84c4de5afc3b37439beecc333314042d0d0dee605d2e5c015e7a56a
current_v25_r0_authority_source_review_artifact_root_sha256=1259883e38f628bf62f7595b19b98045e9990cda508af8d6fd334ffe35000728
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_seven_root_bindings_sha256=4c3410f5c4f123e08e63a18cef10c366911fef7f454f74dbc2532d20db3dd396
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1
current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v6
current_v25_snapshot_schema=camp_dp_v25_controlled_train_snapshot_v6
current_v25_route_source_receipts_schema=camp_dp_v25_a161_route_signal_source_receipts_v2
current_v25_bounded_coverage_design_schema=camp_dp_v25_bounded_coverage_design_v1
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v6.json
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a16_source_only_no_model_simulator_candidate_dp_forward=true
current_v25_a16_independent_review_passed=true
current_v25_a161_local_non_torch_test_result=185_passed_2_skipped
current_v25_a161_targeted_test_result=117_passed_1_skipped
current_v25_a161_schema_regression_test_result=43_passed
current_v25_a161_autodl_v25_test_result=193_passed
current_v25_a161_pointer_test_result=18_passed
current_v25_a161_windows_full_collection=torch_dll_abort_not_counted
current_v25_a161_source_census_started=true
current_v25_a161_source_census_completed=true
current_v25_a161_source_review_started=true
current_v25_a161_source_review_completed=true
current_v25_a161_source_census_review_passed=true
current_v25_a161_bounded_coverage_design_identity_count=243
current_v25_a161_bounded_k8_executed=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_b2_opened=false
current_v25_fresh_outcome_opened=false
local_origin_github_autodl_aligned=true
observed_autodl_free_bytes=46960885760
current_v25_phase=A1_6_1_source_only_census_and_independent_review_passed
next_work_target=ultra_read_only_A1_6_1_source_package_review_before_any_bounded_k8

## A1.6.2 Bounded-Integration Correction and Execution-Plan Preflight

Ultra accepted the A1.6.1 static source census and authorized only a bounded
integration correction and a sealed execution-plan preflight. K8 execution,
full-config release, full R, worker/monitor creation, training, calibration,
Scene/V2I, Fresh, and all outcome access remained closed throughout this gate.

Implementation source HEAD
`daa8407e922080b84a4955371e86b8d8b6e51c72` closes the bounded integration
findings without changing the fixed DP repository, commit, K=8 candidate
semantics, trajectory tensors, atom formulas, normalization, or source-valid
progress contract:

- controlled same-tick signal override now synchronizes the already-built
  fixed-DP `MapTensorCache` after the scenario adapter and before tensor
  conversion or any forward; scene lanes, route lanes, and model-consumed cache
  state must agree;
- observe mode performs no request/cache mutation, while override mode records
  same-tick readback and both modes bind deterministic input hashes;
- snapshot schema v7 binds each source receipt and model-cache receipt to the
  exact sealed A1.6.2 source row, source-chain, regulatory/stop-line/route
  geometry, and rejects cross-identity swaps, duplicate lanelets, non-exact
  one-hot values, or receipt/tensor mismatches;
- bounded terminal acceptance requires every selected run to complete exactly
  64 ticks with no retained capability failure; mapped runtime source failure
  is fail-closed rather than a retained denominator allowance.

Two plan attempts were preserved as diagnostic failures before the final plan.
The `eafe96e4...` attempt failed before a complete seal because it looked for a
source HEAD at the wrong report level. The `7e1d5be3...` retry correctly sealed
fail-closed at root
`d1cdc934d385da3b53884a89b4e4d819740dac7f046f3dd167d495890872690a`.
Read-only diagnosis showed four terminal cells were being expanded solely by
`parameters.variant` and `source_chain_sha256`; the former is an identity-only
generator ordinal and the latter signs `scenario_id`. Neither is a fixed-DP
physical input. The versioned v2 tie payload now freezes the eight physical
tier parameters and the complete source-chain physical contract with only the
scenario-ID/signature wrappers removed. Tests separately prove that changes to
actor dynamics or route/source geometry remain non-equivalent.

The final implementation reproduces the preregistered outcome-blind design on
the live formal/source universe: all 146 mapped identities and 97 no-signal
coverage identities, 243 unique identities total. Execution order is identity0
first, the remaining 242 unique identities, and identity0 final repeat: 244
runs and a prospective 15,616 ticks. All four scenario-ID terminal ties have
identical route, semantic physical payload, seed, and K8-relevant input. The
plan contains no score, selected-index, outcome, Fresh, holdout, or private-DP
latent selection source.

Fresh source evidence was rebuilt under the same implementation HEAD:

- source census:
  `/root/autodl-tmp/camp_dp_v25_a162_route_signal_source_census_daa8407e_20260718T131723CST`,
  root `1540fcaeda72fc1e3ab23ba400ad050e3144d8d82fcd100ca5b3aa4293b3c5ac`;
- independent source review:
  `/root/autodl-tmp/camp_dp_v25_a162_route_signal_source_review_daa8407e_20260718T131723CST`,
  root `290bdd8001d6eb4938bd534a46347c6bf56d2a6b74c0167979c090acbdc88fcc`;
- bounded execution plan:
  `/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_daa8407e_20260718T131815CST`,
  root `26563110b20f3d6f12488baad84629871a5eb4f6f2c8e82c15ebaa3f4258bbdb`;
- independent plan review:
  `/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_review_daa8407e_20260718T131815CST`,
  root `56c3a173abc1f620f1244f72d5e40d5a631c959d18d3d136c3212917273daa3e`.

The source artifacts retain the complete 1,653-row denominator: 1,500
executable plus 153 retained, 146 mapped plus 1,354 no-signal, 21 controlled
same-tick override plus 125 observe-same-tick, and zero source failures.
Producer and independent reviewer both exited zero with exact inventories.
The plan and independent reconstruction both record 243/244/15,616, four
equivalent ties, identity0 repeat positions `[0, 243]`, `k8_executed=false`,
`candidate_generation_started=false`, `model_loaded=false`,
`simulator_started=false`, `fresh_b2_opened=false`, and no outcome fields.

Focused evidence is 110 local tests passed and the same 110 AutoDL tests
passed, plus the real sealed source and plan producer/reviewer runs. At the
decision-package stop, local/origin/GitHub/AutoDL are aligned through the
implementation/pointer chain, fixed DP remains clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, worker and GPU compute counts are
zero, the corpus lock is free, disk is above the 10 GiB floor, and Fresh/outcome
remains unopened. The next gate is Ultra read-only A1.6.2 review; this record
does not authorize bounded K8 execution.

current_v25_status=v25_a162_bounded_plan_review_passed_ultra_k8_execute_review_required
current_v25_source_head=daa8407e922080b84a4955371e86b8d8b6e51c72
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_daa8407e_20260718T131815CST
current_v25_artifact_root_sha256=26563110b20f3d6f12488baad84629871a5eb4f6f2c8e82c15ebaa3f4258bbdb
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_review_daa8407e_20260718T131815CST
current_v25_review_artifact_root_sha256=56c3a173abc1f620f1244f72d5e40d5a631c959d18d3d136c3212917273daa3e
current_v25_a16_old_source_machine_authority_eligible=false
current_v25_a16_old_source_scientific_diagnostic=true
current_v25_a16_old_source_artifact_root_sha256=c93af9687c0c4c50e62d396311d3d10e0b8e953453186b0dde6b1aa21ecf51db
current_v25_a16_old_source_review_artifact_root_sha256=0797f4dfbbe947eed7296249e0b904ed91cfde323f1e775f2e189100e3e2c73e
current_v25_a161_failed_census_artifact=/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_4d0cfe6e_20260718T115300CST
current_v25_a161_failed_census_root_sha256=1b8b2dfebaccd9e7071ff04f8e3b1f30c2f2af3677abac6bd02183a94c28064e
current_v25_a161_failed_census_machine_authority_eligible=false
current_v25_a161_failed_review_reason=source_census_report_exact_check_key_contract_drift
current_v25_full_config_preflight_release_artifact=/root/autodl-tmp/camp_dp_v25_ultra_full_config_preflight_release_1e1c32c7_5f919a54290957e2
current_v25_full_config_preflight_release_artifact_root_sha256=cb8733b4c81a2071a82c37caf74fa06586f51d7d9c1b7c3c0722f824029b33b1
current_v25_full_config_preflight_consumed_nonce=5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e
current_v25_full_config_preflight_consumed_marker_sha256=0b62753b0b07ea987d78e309fde4ed9d9aeda5e2cf0b25d1107f7c446a1b864d
current_v25_full_config_preflight_failure=non_red_identity_lacks_qualified_same_tick_mapped_signal_source
current_v25_r05_failed_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053400CST
current_v25_r05_failed_review_artifact_root_sha256=d3cf28b2f62814b89e9b6debace6e3f87a14d5a3b9c38eabd92a50e059b1cab5
current_v25_ultra_stage_a_decision_artifact_root_sha256=0f48f22861721258be945ae42fb10d3fec7f90992addb386c535a1b8001b3e5a
current_v25_atom_ledger_artifact_root_sha256=5e762a14b53c6c81f6bb3bfa67c6aeeb7fa5fe603bb95fa0776d75035cb8311c
current_v25_atom_ledger_validation_artifact_root_sha256=641fadb24926cb7e6fc49c98d66f6a0a9528f41856b0417aae9e6fb9a80fa469
current_v25_r0_authority_source_artifact_root_sha256=1540fcaeda72fc1e3ab23ba400ad050e3144d8d82fcd100ca5b3aa4293b3c5ac
current_v25_r0_authority_source_review_artifact_root_sha256=290bdd8001d6eb4938bd534a46347c6bf56d2a6b74c0167979c090acbdc88fcc
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_seven_root_bindings_sha256=4c3410f5c4f123e08e63a18cef10c366911fef7f454f74dbc2532d20db3dd396
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1
current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v7
current_v25_snapshot_schema=camp_dp_v25_controlled_train_snapshot_v7
current_v25_route_source_receipts_schema=camp_dp_v25_a161_route_signal_source_receipts_v2
current_v25_bounded_coverage_design_schema=camp_dp_v25_bounded_coverage_design_v1
current_v25_bounded_execution_plan_schema=camp_dp_v25_a162_route_level_bounded_execution_plan_v2
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v6.json
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a16_source_only_no_model_simulator_candidate_dp_forward=true
current_v25_a16_independent_review_passed=true
current_v25_a161_local_non_torch_test_result=185_passed_2_skipped
current_v25_a161_targeted_test_result=117_passed_1_skipped
current_v25_a161_schema_regression_test_result=43_passed
current_v25_a161_autodl_v25_test_result=193_passed
current_v25_a161_pointer_test_result=18_passed
current_v25_a161_windows_full_collection=torch_dll_abort_not_counted
current_v25_a161_source_census_started=true
current_v25_a161_source_census_completed=true
current_v25_a161_source_review_started=true
current_v25_a161_source_review_completed=true
current_v25_a161_source_census_review_passed=true
current_v25_a161_bounded_coverage_design_identity_count=243
current_v25_a161_bounded_k8_executed=false
current_v25_a162_source_artifact_root_sha256=1540fcaeda72fc1e3ab23ba400ad050e3144d8d82fcd100ca5b3aa4293b3c5ac
current_v25_a162_source_review_artifact_root_sha256=290bdd8001d6eb4938bd534a46347c6bf56d2a6b74c0167979c090acbdc88fcc
current_v25_a162_failed_sealed_plan_artifact_root_sha256=d1cdc934d385da3b53884a89b4e4d819740dac7f046f3dd167d495890872690a
current_v25_a162_bounded_plan_artifact_root_sha256=26563110b20f3d6f12488baad84629871a5eb4f6f2c8e82c15ebaa3f4258bbdb
current_v25_a162_bounded_plan_review_artifact_root_sha256=56c3a173abc1f620f1244f72d5e40d5a631c959d18d3d136c3212917273daa3e
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_tie_proof_count=4
current_v25_a162_all_tie_proofs_equivalent=true
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a162_local_targeted_test_result=110_passed
current_v25_a162_autodl_targeted_test_result=110_passed
current_v25_a162_pointer_test_result=18_passed
current_v25_a162_bounded_k8_executed=false
current_v25_a162_candidate_generation_started=false
current_v25_a162_model_loaded=false
current_v25_a162_simulator_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_b2_opened=false
current_v25_fresh_outcome_opened=false
local_origin_github_autodl_aligned=true
observed_autodl_free_bytes=46936682496
current_v25_phase=A1_6_2_bounded_integration_plan_and_independent_review_passed_k8_closed
next_work_target=ultra_read_only_A1_6_2_review_before_any_bounded_k8_execute
## A1.6.3 Bounded-Only Machine Authority and Execution Preflight

Ultra accepted the A1.6.2 source/design package but blocked bounded K8 because
the existing full-corpus path could not consume the 244-run plan, represent
identity0 at both ordinals 0 and 243, or derive the required repeat checks from
sealed raw evidence. This gate changed only CAMP execution authority and audit
code; fixed DP, K=8 candidate semantics, trajectories, 14D atoms, canonical
normalization, source-valid progress, no-V2I, and the formal denominator did not
change.

Implementation source HEAD
`49faaae4aaa69089aaa1b37d2e7ea5ca9caf0a3e` adds:

- a bounded-only release schema and one-shot `a162_bounded_execute` nonce
  namespace bound to the four source/plan roots, implementation/pointer HEADs,
  fixed DP, critical manifest, seed 25001, exact output directory, and
  243/244/15,616 denominator;
- a dedicated plan-ordered runner whose native directories, results, snapshot
  index, and snapshot sidecars include `run_ordinal` and `occurrence`, allowing
  identity0 only as the frozen first/final repeat;
- terminal acceptance wired to 244 exact 64-tick completions and zero retained
  or mapped-source failures; callers can no longer provide eight pass booleans;
- an independent post-run reviewer that reopens raw K8 tensors, candidate0,
  canonical affine scores, atoms, context, selected indices, native safety
  trajectory, and speed to rebuild all eight repeat comparisons;
- the same exclusive corpus lock from before output creation through terminal
  report, `run.exit`, and seal, plus fail-closed sealed failure evidence.

No real release artifact, nonce, nonce marker, bounded output, model, simulator,
candidate, K8, full-config/full-R action, worker, or monitor was created.

After local TDD and AutoDL ff-only synchronization, focused evidence was 123
passed with three Windows platform skips locally and 126 passed on AutoDL,
including the real Linux second-process flock rejection/release test. GitHub
HTTPS fetch from AutoDL failed twice with GnuTLS termination before changing
remote state; a local-main incremental git bundle was then SHA256-verified and
used to update AutoDL `origin/main` and `main` by `--ff-only` semantics to the
same GitHub-pushed commit.

All four source/design roots were rebuilt from identity0 under that source HEAD
without K8:

- source census:
  `/root/autodl-tmp/camp_dp_v25_a163_route_signal_source_census_49faaae4_20260718T140504CST`,
  root `e71ca03450e8a6b55bc11d2b319ea17ff7392b053ad0f0afa27835cd7739265b`;
- independent source review:
  `/root/autodl-tmp/camp_dp_v25_a163_route_signal_source_review_49faaae4_20260718T140504CST`,
  root `cb5bd1c643fff70206597e2265502cc563524a3645a142cf85da94d8d1aa9d81`;
- bounded plan:
  `/root/autodl-tmp/camp_dp_v25_a163_bounded_execution_plan_49faaae4_20260718T140504CST`,
  root `1f67303ffc0c6ba1d2b97b91077a2e5610b82ca423a57df63ebf6e1cf38be0a2`;
- independent plan review:
  `/root/autodl-tmp/camp_dp_v25_a163_bounded_execution_plan_review_49faaae4_20260718T140504CST`,
  root `0c953c0654af34fbda65118240e2836c954fd39648da68f4c02def05a707952c`.

The source roots preserve 1,653 total, 1,500 executable, 153 retained,
146 mapped-signal, 1,354 no-signal, 21 controlled overrides, 125 same-tick
observed phases, and zero source failures. The plan/review preserve 243 unique
identities, 244 ordered runs, 15,616 prospective ticks, four equivalent ties,
and identity0 positions `[0, 243]`. The new machine verifier independently
reopened all four seals, exact inventories, HEADS, status/cross-links, types,
counts, order, and closed execution flags. `k8_executed`, candidate generation,
model/simulator, training, calibration, Scene/V2I, Fresh, and outcome access
remain false.

The A1.6.3 four roots remain immutable design evidence but are machine-authority
ineligible under the subsequent Ultra review. They were not overwritten or
used to create a release, nonce, output, or K8 execution.

## A1.6.4 Canonical Execution Assets and Independent Tick Review

Ultra found that A1.6.3 did not freeze the canonical probe template/static
weights/checkpoint/args and that its independent post-run reviewer could select
index zero from an empty source-valid set or omit native-to-snapshot evidence
cross-binding. Implementation source HEAD
`ac70c354fc9dcd8bfaadb97abc79392627f72cd9` corrects only that bounded
authority/reviewer surface:

- release build and consumption now require the exact canonical probe template
  path/SHA, generation scales, float64 14D static weight path/SHA/values,
  fixed-DP checkpoint/args, and five fixed-DP native git-object source SHAs;
- the independent reviewer requires a nonempty native `bool[8]` source-valid
  set, `physical_feasible` as a subset, exact feature/sidecar atom masks, and
  candidate heading unit vectors;
- it independently binds the sealed route-source row and root, mapped/no-signal
  regulatory chain, same-tick phase/timestamps/tensors, certified stop line,
  route arc, no-V2I context, cache receipt, and red-stopping column 12;
- every tick cross-binds native and snapshot K8/candidate0/default, raw and
  normalized atom hashes, scores, masks, selected index and exact selected
  trajectory before the identity0 repeat evidence is rebuilt.

Local focused testing passed 136 tests with the Windows-only flock test skipped.
AutoDL ff-only synchronization then passed all 137 focused tests including the
real Linux flock test. The live canonical execution-assets receipt SHA is
`c59222c920dcb25e8ec18219f7eb683c0e9867f36c026e329e01a16c6cfb9c47`.

No bounded release, nonce ledger, output, model, simulator, candidate, K8,
worker, monitor, training, calibration, Scene/V2I, Fresh, or outcome access was
created. Source-only static evidence was rebuilt from identity0 under the same
implementation HEAD:

- source census:
  `/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_census_ac70c354_20260718T150655CST`,
  root `0541fbc52373e0851160e36da6d202153df26fa4dde26b9c8d3461554a9d72f3`;
- independent source review:
  `/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_review_ac70c354_20260718T150655CST`,
  root `81c59e1babf8a82d4edbad64d22f8dcd6654425ea8f2d7d8dc975b2ee8866db3`;
- bounded plan:
  `/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_ac70c354_20260718T150655CST`,
  root `273a60489abc1c065ef4fe6112f07fd4c0309f1ee0f0e24a01f09efe061a9583`;
- independent plan review:
  `/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_review_ac70c354_20260718T150655CST`,
  root `f8debcc856a869f6f776e2a5ec88d8a3b3c41216f0338895fa1623c8cd36e6c6`.

The source pair preserves 1,653/1,500/153, 146/1,354, 21/125, and zero
source failures. The plan pair preserves 243 unique identities, 244 runs,
15,616 prospective ticks, four equivalent ties, and identity0 at `[0,243]`.
The new verifier reopened all four exact seals and cross-links; their binding
SHA is `365b18fcb914ce55d2dd934fffb7a173679f653c4e871ed95d00a75dd0c1c0ef`.
The next gate is Ultra read-only A1.6.4 review. This record does not authorize
creation of a bounded release/nonce/output or any K8 execution.

current_v25_status=v25_a164_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=ac70c354fc9dcd8bfaadb97abc79392627f72cd9
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_ac70c354_20260718T150655CST
current_v25_artifact_root_sha256=273a60489abc1c065ef4fe6112f07fd4c0309f1ee0f0e24a01f09efe061a9583
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_review_ac70c354_20260718T150655CST
current_v25_review_artifact_root_sha256=f8debcc856a869f6f776e2a5ec88d8a3b3c41216f0338895fa1623c8cd36e6c6
current_v25_a16_old_source_machine_authority_eligible=false
current_v25_a16_old_source_scientific_diagnostic=true
current_v25_a16_old_source_artifact_root_sha256=c93af9687c0c4c50e62d396311d3d10e0b8e953453186b0dde6b1aa21ecf51db
current_v25_a16_old_source_review_artifact_root_sha256=0797f4dfbbe947eed7296249e0b904ed91cfde323f1e775f2e189100e3e2c73e
current_v25_a161_failed_census_artifact=/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_4d0cfe6e_20260718T115300CST
current_v25_a161_failed_census_root_sha256=1b8b2dfebaccd9e7071ff04f8e3b1f30c2f2af3677abac6bd02183a94c28064e
current_v25_a161_failed_census_machine_authority_eligible=false
current_v25_a161_failed_review_reason=source_census_report_exact_check_key_contract_drift
current_v25_full_config_preflight_release_artifact=/root/autodl-tmp/camp_dp_v25_ultra_full_config_preflight_release_1e1c32c7_5f919a54290957e2
current_v25_full_config_preflight_release_artifact_root_sha256=cb8733b4c81a2071a82c37caf74fa06586f51d7d9c1b7c3c0722f824029b33b1
current_v25_full_config_preflight_consumed_nonce=5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e
current_v25_full_config_preflight_consumed_marker_sha256=0b62753b0b07ea987d78e309fde4ed9d9aeda5e2cf0b25d1107f7c446a1b864d
current_v25_full_config_preflight_failure=non_red_identity_lacks_qualified_same_tick_mapped_signal_source
current_v25_r05_failed_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053400CST
current_v25_r05_failed_review_artifact_root_sha256=d3cf28b2f62814b89e9b6debace6e3f87a14d5a3b9c38eabd92a50e059b1cab5
current_v25_s01_failed_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST
current_v25_s01_failed_preflight_artifact_root_sha256=c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a
current_v25_correction_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST
current_v25_correction_preflight_artifact_root_sha256=bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451
current_v25_correction_preflight_review_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST
current_v25_correction_preflight_review_artifact_root_sha256=facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d
current_v25_correction_preflight_probe_count=3
current_v25_correction_preflight_tick_count=192
current_v25_correction_preflight_check_count=12
current_v25_correction_preflight_review_check_count=28
current_v25_correction_preflight_identity0_deterministic=true
current_v25_correction_preflight_native_canonical_equal=true
current_v25_correction_preflight_candidate_immutability=true
current_v25_correction_preflight_candidate0_operational_default_alias=true
current_v25_s01_remote_focused_test_count=65
current_v25_s01_remote_pointer_test_count=10
current_v25_stage_a0_failed_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_f40b6152_20260717T192912CST
current_v25_stage_a0_failed_artifact_root_sha256=025dcd686ee44a681b14cc3ad8b5e64e885316b0f334d89096fda19d6cd8b810
current_v25_stage_a0_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_01073398_20260717T193038CST
current_v25_stage_a0_artifact_root_sha256=b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41
current_v25_stage_a_superseded_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_v2_01073398_20260717T193052CST
current_v25_stage_a_superseded_ledger_artifact_root_sha256=05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2
current_v25_stage_a_superseded_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_e07da58f_20260717T193156CST
current_v25_stage_a_superseded_validation_artifact_root_sha256=e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72
current_v25_ultra_stage_a_decision_artifact=/root/autodl-tmp/camp_dp_v25_ultra_stage_a15_r05_decision_1e1c32c7_20260718T051807CST
current_v25_ultra_stage_a_decision_artifact_root_sha256=0f48f22861721258be945ae42fb10d3fec7f90992addb386c535a1b8001b3e5a
current_v25_atom_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a15_1e1c32c7_20260718T051807CST
current_v25_atom_ledger_artifact_root_sha256=5e762a14b53c6c81f6bb3bfa67c6aeeb7fa5fe603bb95fa0776d75035cb8311c
current_v25_atom_ledger_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a15_1e1c32c7_20260718T051807CST
current_v25_atom_ledger_validation_artifact_root_sha256=641fadb24926cb7e6fc49c98d66f6a0a9528f41856b0417aae9e6fb9a80fa469
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a163_route_signal_source_census_49faaae4_20260718T140504CST
current_v25_r0_authority_source_artifact_root_sha256=e71ca03450e8a6b55bc11d2b319ea17ff7392b053ad0f0afa27835cd7739265b
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a163_route_signal_source_review_49faaae4_20260718T140504CST
current_v25_r0_authority_source_review_artifact_root_sha256=cb5bd1c643fff70206597e2265502cc563524a3645a142cf85da94d8d1aa9d81
current_v25_r0_bounded_k8_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_1e1c32c7_20260718T051807CST
current_v25_r0_bounded_k8_artifact_root_sha256=694ddcde9bd5972c4fb95eeb45da7f46663bb3a6acb87ca5b4cc18abbf97b79c
current_v25_r0_bounded_k8_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053800CST
current_v25_r0_bounded_k8_review_artifact_root_sha256=7dc54a3d9baa3d818284ffdcb3ed1192c0805d93ea7019c6975c86cba20fe47f
current_v25_seven_root_bindings_sha256=4c3410f5c4f123e08e63a18cef10c366911fef7f454f74dbc2532d20db3dd396
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1
current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v7
current_v25_snapshot_schema=camp_dp_v25_controlled_train_snapshot_v7
current_v25_route_source_receipts_schema=camp_dp_v25_a161_route_signal_source_receipts_v2
current_v25_bounded_coverage_design_schema=camp_dp_v25_bounded_coverage_design_v1
current_v25_bounded_execution_plan_schema=camp_dp_v25_a162_route_level_bounded_execution_plan_v2
current_v25_a11_failed_validation_artifact_root_sha256=4d51394f8f4f61680fb65bd82062096fbaa72149862c4a6289f7f46927402b20
current_v25_r01_failed_signature_artifact_root_sha256=b491a1fd8c82fd7165bf08763cc1e12f9a1bfe5e89cb7e2b6e8133a2f0958d87
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_rejected_partial_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_rejected_partial_review_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST
current_v25_rejected_partial_review_artifact_root_sha256=f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009
current_v25_stage_a_atom_pass_count=9
current_v25_stage_a_atom_warn_count=5
current_v25_stage_a_atom_fail_count=0
current_v25_stage_a_progress_reference=source_valid_candidate_set_reference
current_v25_stage_a_progress_reference_frozen=true
current_v25_stage_a_s01_per_atom_raw_statistics_available=false
current_v25_a1_r0_local_test_result=132_v25_non_torch_passed_2_skipped
current_v25_a1_r0_remote_test_result=165_v25_passed_after_A1_6_source_authority_sync
current_v25_real_flock_test_result=1_passed
current_v25_atom_schema=dp_camp_v10_14d
current_v25_paper_subset=camp_legacy_v1_9d
current_v25_context_schema=camp_dp_v25_causal_context_raw_v2
current_v25_context_raw_feature_count=26
current_v25_phi_dimension=53
current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection
current_v25_normalization_contract=z_clip_raw_atom_over_scale_0_10
current_v25_heading_norm_envelope_min=0.5
current_v25_heading_norm_envelope_max=1.5
current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4
current_v25_controlled_pilot_case_count=147
current_v25_controlled_pilot_passed_count=85
current_v25_controlled_pilot_retained_failure_count=62
current_v25_controlled_train_executable_identity_count=1500
current_v25_controlled_train_source_ineligible_retained_count=153
current_v25_combined_train_snapshot_capacity_at_64_ticks=163796
current_v25_stopped_train_attempted_identity_count=122
current_v25_stopped_train_complete_identity_count=121
current_v25_stopped_train_failed_identity_count=1
current_v25_stopped_train_snapshot_count=7748
current_v25_stopped_train_illegal_partial_snapshot_count=4
current_v25_stopped_train_all_k_high_risk_snapshot_count=1121
current_v25_stopped_train_training_eligible=false
current_v25_stopped_train_calibration_eligible=false
current_v25_stopped_train_evaluation_eligible=false
current_v25_fresh_b_identity_count=120
current_v25_fresh_b_paired_run_count=600
current_v25_fresh_b_independent_route_ceiling=24
current_v25_fresh_b_independent_corridor_ceiling=3
current_v25_fresh_b_v1_status=superseded_before_opening
current_v25_fresh_b2_opened=false
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v6.json
current_v25_stage_a_executed=true
current_v25_stage_a1_executed=true
current_v25_r0_source_executed=true
current_v25_r0_bounded_k8_executed=true
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_probe_identity_count=22
current_v25_r0_probe_tick_count=1408
current_v25_r0_non_signal_identity_count=1
current_v25_r0_physical_signature_count=9
current_v25_r0_stop_line_geometry_sha256_count=5
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a16_source_only_no_model_simulator_candidate_dp_forward=true
current_v25_a16_independent_review_passed=true
current_v25_a161_local_non_torch_test_result=185_passed_2_skipped
current_v25_a161_targeted_test_result=117_passed_1_skipped
current_v25_a161_schema_regression_test_result=43_passed
current_v25_a161_autodl_v25_test_result=193_passed
current_v25_a161_pointer_test_result=18_passed
current_v25_a161_windows_full_collection=torch_dll_abort_not_counted
current_v25_a161_source_census_started=true
current_v25_a161_source_census_completed=true
current_v25_a161_source_review_started=true
current_v25_a161_source_review_completed=true
current_v25_a161_source_census_review_passed=true
current_v25_a161_bounded_coverage_design_identity_count=243
current_v25_a161_bounded_k8_executed=false
current_v25_a162_source_artifact=/root/autodl-tmp/camp_dp_v25_a163_route_signal_source_census_49faaae4_20260718T140504CST
current_v25_a162_source_artifact_root_sha256=e71ca03450e8a6b55bc11d2b319ea17ff7392b053ad0f0afa27835cd7739265b
current_v25_a162_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a163_route_signal_source_review_49faaae4_20260718T140504CST
current_v25_a162_source_review_artifact_root_sha256=cb5bd1c643fff70206597e2265502cc563524a3645a142cf85da94d8d1aa9d81
current_v25_a162_failed_unsealed_plan_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_eafe96e4_20260718T130620CST
current_v25_a162_failed_sealed_plan_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_7e1d5be3_20260718T131240CST
current_v25_a162_failed_sealed_plan_artifact_root_sha256=d1cdc934d385da3b53884a89b4e4d819740dac7f046f3dd167d495890872690a
current_v25_a162_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a163_bounded_execution_plan_49faaae4_20260718T140504CST
current_v25_a162_bounded_plan_artifact_root_sha256=1f67303ffc0c6ba1d2b97b91077a2e5610b82ca423a57df63ebf6e1cf38be0a2
current_v25_a162_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a163_bounded_execution_plan_review_49faaae4_20260718T140504CST
current_v25_a162_bounded_plan_review_artifact_root_sha256=0c953c0654af34fbda65118240e2836c954fd39648da68f4c02def05a707952c
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_tie_proof_count=4
current_v25_a162_all_tie_proofs_equivalent=true
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a162_local_targeted_test_result=123_passed_3_skipped
current_v25_a162_autodl_targeted_test_result=126_passed
current_v25_a162_pointer_test_result=18_passed
current_v25_a162_bounded_k8_executed=false
current_v25_a162_candidate_generation_started=false
current_v25_a162_model_loaded=false
current_v25_a162_simulator_started=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_old_monitor_status=deleted
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
current_v25_v24_holdout_read=false
current_v25_fresh_benchmark_b_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46936682496
current_v25_phase=A1_6_3_bounded_machine_authority_and_plan_preflight_passed_k8_closed
next_work_target=ultra_read_only_A1_6_3_review_before_any_bounded_execute_release

current_v25_status=v25_a164_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=ac70c354fc9dcd8bfaadb97abc79392627f72cd9
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_ac70c354_20260718T150655CST
current_v25_artifact_root_sha256=273a60489abc1c065ef4fe6112f07fd4c0309f1ee0f0e24a01f09efe061a9583
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_review_ac70c354_20260718T150655CST
current_v25_review_artifact_root_sha256=f8debcc856a869f6f776e2a5ec88d8a3b3c41216f0338895fa1623c8cd36e6c6
current_v25_a16_old_source_machine_authority_eligible=false
current_v25_a16_old_source_scientific_diagnostic=true
current_v25_a16_old_source_artifact_root_sha256=c93af9687c0c4c50e62d396311d3d10e0b8e953453186b0dde6b1aa21ecf51db
current_v25_a16_old_source_review_artifact_root_sha256=0797f4dfbbe947eed7296249e0b904ed91cfde323f1e775f2e189100e3e2c73e
current_v25_a161_failed_census_artifact=/root/autodl-tmp/camp_dp_v25_a161_route_signal_source_census_4d0cfe6e_20260718T115300CST
current_v25_a161_failed_census_root_sha256=1b8b2dfebaccd9e7071ff04f8e3b1f30c2f2af3677abac6bd02183a94c28064e
current_v25_a161_failed_census_machine_authority_eligible=false
current_v25_a161_failed_review_reason=source_census_report_exact_check_key_contract_drift
current_v25_full_config_preflight_release_artifact=/root/autodl-tmp/camp_dp_v25_ultra_full_config_preflight_release_1e1c32c7_5f919a54290957e2
current_v25_full_config_preflight_release_artifact_root_sha256=cb8733b4c81a2071a82c37caf74fa06586f51d7d9c1b7c3c0722f824029b33b1
current_v25_full_config_preflight_consumed_nonce=5f919a54290957e2decfc662804db6ff320ca9582b62ea2869b67a13926fe37e
current_v25_full_config_preflight_consumed_marker_sha256=0b62753b0b07ea987d78e309fde4ed9d9aeda5e2cf0b25d1107f7c446a1b864d
current_v25_full_config_preflight_failure=non_red_identity_lacks_qualified_same_tick_mapped_signal_source
current_v25_r05_failed_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053400CST
current_v25_r05_failed_review_artifact_root_sha256=d3cf28b2f62814b89e9b6debace6e3f87a14d5a3b9c38eabd92a50e059b1cab5
current_v25_s01_failed_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST
current_v25_s01_failed_preflight_artifact_root_sha256=c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a
current_v25_correction_preflight_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST
current_v25_correction_preflight_artifact_root_sha256=bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451
current_v25_correction_preflight_review_artifact=/root/autodl-tmp/camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST
current_v25_correction_preflight_review_artifact_root_sha256=facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d
current_v25_correction_preflight_probe_count=3
current_v25_correction_preflight_tick_count=192
current_v25_correction_preflight_check_count=12
current_v25_correction_preflight_review_check_count=28
current_v25_correction_preflight_identity0_deterministic=true
current_v25_correction_preflight_native_canonical_equal=true
current_v25_correction_preflight_candidate_immutability=true
current_v25_correction_preflight_candidate0_operational_default_alias=true
current_v25_s01_remote_focused_test_count=65
current_v25_s01_remote_pointer_test_count=10
current_v25_stage_a0_failed_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_f40b6152_20260717T192912CST
current_v25_stage_a0_failed_artifact_root_sha256=025dcd686ee44a681b14cc3ad8b5e64e885316b0f334d89096fda19d6cd8b810
current_v25_stage_a0_artifact=/root/autodl-tmp/camp_dp_v25_stage_a0_authority_supplement_01073398_20260717T193038CST
current_v25_stage_a0_artifact_root_sha256=b8664cd074bf48ded82017950616c851a3f3ca6afdd6fbe0ba0e705359e8ff41
current_v25_stage_a_superseded_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_v2_01073398_20260717T193052CST
current_v25_stage_a_superseded_ledger_artifact_root_sha256=05449b7a8913559575347763aa95f25b4a9e5e9f58b5dc6106251a9e1b4c7fa2
current_v25_stage_a_superseded_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_v2_e07da58f_20260717T193156CST
current_v25_stage_a_superseded_validation_artifact_root_sha256=e07bfcbd879d992b1a9ad61d467a7970bcc19b120303e457e244899bb0316a72
current_v25_ultra_stage_a_decision_artifact=/root/autodl-tmp/camp_dp_v25_ultra_stage_a15_r05_decision_1e1c32c7_20260718T051807CST
current_v25_ultra_stage_a_decision_artifact_root_sha256=0f48f22861721258be945ae42fb10d3fec7f90992addb386c535a1b8001b3e5a
current_v25_atom_ledger_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_a15_1e1c32c7_20260718T051807CST
current_v25_atom_ledger_artifact_root_sha256=5e762a14b53c6c81f6bb3bfa67c6aeeb7fa5fe603bb95fa0776d75035cb8311c
current_v25_atom_ledger_validation_artifact=/root/autodl-tmp/camp_dp_v25_static_atom_ledger_validation_a15_1e1c32c7_20260718T051807CST
current_v25_atom_ledger_validation_artifact_root_sha256=641fadb24926cb7e6fc49c98d66f6a0a9528f41856b0417aae9e6fb9a80fa469
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_census_ac70c354_20260718T150655CST
current_v25_r0_authority_source_artifact_root_sha256=0541fbc52373e0851160e36da6d202153df26fa4dde26b9c8d3461554a9d72f3
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_review_ac70c354_20260718T150655CST
current_v25_r0_authority_source_review_artifact_root_sha256=81c59e1babf8a82d4edbad64d22f8dcd6654425ea8f2d7d8dc975b2ee8866db3
current_v25_r0_bounded_k8_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_1e1c32c7_20260718T051807CST
current_v25_r0_bounded_k8_artifact_root_sha256=694ddcde9bd5972c4fb95eeb45da7f46663bb3a6acb87ca5b4cc18abbf97b79c
current_v25_r0_bounded_k8_review_artifact=/root/autodl-tmp/camp_dp_v25_r05_red21_nonsignal1_sequential_k8_review_1e1c32c7_20260718T053800CST
current_v25_r0_bounded_k8_review_artifact_root_sha256=7dc54a3d9baa3d818284ffdcb3ed1192c0805d93ea7019c6975c86cba20fe47f
current_v25_seven_root_bindings_sha256=4c3410f5c4f123e08e63a18cef10c366911fef7f454f74dbc2532d20db3dd396
current_v25_semantic_clone_schema=camp_dp_v25_semantic_clone_payload_v3
current_v25_canonical_json_byte_spec=camp_dp_v25_canonical_json_utf8_lf_v1
current_v25_execution_schema=camp_dp_v25_controlled_training_corpus_execution_v7
current_v25_snapshot_schema=camp_dp_v25_controlled_train_snapshot_v7
current_v25_route_source_receipts_schema=camp_dp_v25_a161_route_signal_source_receipts_v2
current_v25_bounded_coverage_design_schema=camp_dp_v25_bounded_coverage_design_v1
current_v25_bounded_execution_plan_schema=camp_dp_v25_a162_route_level_bounded_execution_plan_v2
current_v25_a11_failed_validation_artifact_root_sha256=4d51394f8f4f61680fb65bd82062096fbaa72149862c4a6289f7f46927402b20
current_v25_r01_failed_signature_artifact_root_sha256=b491a1fd8c82fd7165bf08763cc1e12f9a1bfe5e89cb7e2b6e8133a2f0958d87
current_v25_r01_failed_projection_artifact_root_sha256=652975e9464988d10971c4fe633f145f78c18edbe1ddc56a448f2d74b7cb0c06
current_v25_rejected_partial_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_491716fc_20260717T154959CST
current_v25_rejected_partial_artifact_root_sha256=a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481
current_v25_rejected_partial_review_artifact=/root/autodl-tmp/camp_dp_v25_controlled_train_corpus_superseded_ineligible_review_491716fc_20260717T154959CST
current_v25_rejected_partial_review_artifact_root_sha256=f73004a10c48d65bfb410dcddf4f618f303c5c6bea4b61cee26e6e450cda9009
current_v25_stage_a_atom_pass_count=9
current_v25_stage_a_atom_warn_count=5
current_v25_stage_a_atom_fail_count=0
current_v25_stage_a_progress_reference=source_valid_candidate_set_reference
current_v25_stage_a_progress_reference_frozen=true
current_v25_stage_a_s01_per_atom_raw_statistics_available=false
current_v25_a1_r0_local_test_result=132_v25_non_torch_passed_2_skipped
current_v25_a1_r0_remote_test_result=165_v25_passed_after_A1_6_source_authority_sync
current_v25_real_flock_test_result=1_passed
current_v25_atom_schema=dp_camp_v10_14d
current_v25_paper_subset=camp_legacy_v1_9d
current_v25_context_schema=camp_dp_v25_causal_context_raw_v2
current_v25_context_raw_feature_count=26
current_v25_phi_dimension=53
current_v25_scene_conditioned_mode=context_simplex_column_simplex_no_softmax_no_runtime_projection
current_v25_normalization_contract=z_clip_raw_atom_over_scale_0_10
current_v25_heading_norm_envelope_min=0.5
current_v25_heading_norm_envelope_max=1.5
current_v25_official_scenario_source_head=e22f01093fa6516c0552549ada302270329c59a4
current_v25_controlled_pilot_case_count=147
current_v25_controlled_pilot_passed_count=85
current_v25_controlled_pilot_retained_failure_count=62
current_v25_controlled_train_executable_identity_count=1500
current_v25_controlled_train_source_ineligible_retained_count=153
current_v25_combined_train_snapshot_capacity_at_64_ticks=163796
current_v25_stopped_train_attempted_identity_count=122
current_v25_stopped_train_complete_identity_count=121
current_v25_stopped_train_failed_identity_count=1
current_v25_stopped_train_snapshot_count=7748
current_v25_stopped_train_illegal_partial_snapshot_count=4
current_v25_stopped_train_all_k_high_risk_snapshot_count=1121
current_v25_stopped_train_training_eligible=false
current_v25_stopped_train_calibration_eligible=false
current_v25_stopped_train_evaluation_eligible=false
current_v25_fresh_b_identity_count=120
current_v25_fresh_b_paired_run_count=600
current_v25_fresh_b_independent_route_ceiling=24
current_v25_fresh_b_independent_corridor_ceiling=3
current_v25_fresh_b_v1_status=superseded_before_opening
current_v25_fresh_b2_opened=false
current_v25_atom_ledger_plan=configs/integrations/diffusion_planner_v25_atom_ledger_plan_v6.json
current_v25_stage_a_executed=true
current_v25_stage_a1_executed=true
current_v25_r0_source_executed=true
current_v25_r0_bounded_k8_executed=true
current_v25_r0_source_identity_count=21
current_v25_r0_source_map_count=4
current_v25_r0_probe_identity_count=22
current_v25_r0_probe_tick_count=1408
current_v25_r0_non_signal_identity_count=1
current_v25_r0_physical_signature_count=9
current_v25_r0_stop_line_geometry_sha256_count=5
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a16_source_only_no_model_simulator_candidate_dp_forward=true
current_v25_a16_independent_review_passed=true
current_v25_a161_local_non_torch_test_result=185_passed_2_skipped
current_v25_a161_targeted_test_result=117_passed_1_skipped
current_v25_a161_schema_regression_test_result=43_passed
current_v25_a161_autodl_v25_test_result=193_passed
current_v25_a161_pointer_test_result=18_passed
current_v25_a161_windows_full_collection=torch_dll_abort_not_counted
current_v25_a161_source_census_started=true
current_v25_a161_source_census_completed=true
current_v25_a161_source_review_started=true
current_v25_a161_source_review_completed=true
current_v25_a161_source_census_review_passed=true
current_v25_a161_bounded_coverage_design_identity_count=243
current_v25_a161_bounded_k8_executed=false
current_v25_a162_source_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_census_ac70c354_20260718T150655CST
current_v25_a162_source_artifact_root_sha256=0541fbc52373e0851160e36da6d202153df26fa4dde26b9c8d3461554a9d72f3
current_v25_a162_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_route_signal_source_review_ac70c354_20260718T150655CST
current_v25_a162_source_review_artifact_root_sha256=81c59e1babf8a82d4edbad64d22f8dcd6654425ea8f2d7d8dc975b2ee8866db3
current_v25_a162_failed_unsealed_plan_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_eafe96e4_20260718T130620CST
current_v25_a162_failed_sealed_plan_artifact=/root/autodl-tmp/camp_dp_v25_a162_bounded_execution_plan_7e1d5be3_20260718T131240CST
current_v25_a162_failed_sealed_plan_artifact_root_sha256=d1cdc934d385da3b53884a89b4e4d819740dac7f046f3dd167d495890872690a
current_v25_a162_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_ac70c354_20260718T150655CST
current_v25_a162_bounded_plan_artifact_root_sha256=273a60489abc1c065ef4fe6112f07fd4c0309f1ee0f0e24a01f09efe061a9583
current_v25_a162_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a164_bounded_execution_plan_review_ac70c354_20260718T150655CST
current_v25_a162_bounded_plan_review_artifact_root_sha256=f8debcc856a869f6f776e2a5ec88d8a3b3c41216f0338895fa1623c8cd36e6c6
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_tie_proof_count=4
current_v25_a162_all_tie_proofs_equivalent=true
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a162_local_targeted_test_result=123_passed_3_skipped
current_v25_a162_autodl_targeted_test_result=126_passed
current_v25_a162_pointer_test_result=18_passed
current_v25_a162_bounded_k8_executed=false
current_v25_a162_candidate_generation_started=false
current_v25_a162_model_loaded=false
current_v25_a162_simulator_started=false
current_v25_a163_four_roots_machine_authority_eligible=false
current_v25_a164_execution_assets_sha256=c59222c920dcb25e8ec18219f7eb683c0e9867f36c026e329e01a16c6cfb9c47
current_v25_a164_four_root_bindings_sha256=365b18fcb914ce55d2dd934fffb7a173679f653c4e871ed95d00a75dd0c1c0ef
current_v25_a164_local_targeted_test_result=136_passed_1_skipped
current_v25_a164_autodl_targeted_test_result=137_passed
current_v25_a164_bounded_release_created=false
current_v25_a164_bounded_nonce_created=false
current_v25_a164_bounded_k8_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_old_monitor_status=deleted
v24_legacy_benchmark_status=frozen_read_only_honest_no_claim
v24_holdout_open_count=1
v24_holdout_rerun_authorized=false
current_v25_v24_holdout_read=false
current_v25_fresh_benchmark_b_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46918983680
current_v25_phase=A1_6_4_bounded_authority_and_independent_reviewer_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_4_review_before_any_bounded_execute_release

## A1.6.5 bounded evidence-authority correction and static four-root package (2026-07-18 CST)

Ultra kept bounded K8 closed after reproducing five A1.6.4 authority gaps. The
reviewer did not independently bind controlled ticks to the frozen expected
phase; native controlled-scene/context/failure evidence could contradict the
snapshot; atom source/applicability masks were not independently reconstructed;
the release did not freeze CUDA; and textually aliased output paths could reach
nonce consumption. The A1.6.4 four roots remain sealed diagnostic evidence and
are explicitly machine-authority-ineligible.

Implementation source HEAD
`82dffe39869bc0af7d0535d6fcf0ee2ae9f0d04f` implements only the authorized
A1.6.5 correction. Controlled mode now requires a frozen green/yellow/red phase,
matching formal phase, required authority, and exact per-tick phase. Observe
mode requires absent expected phase, formal `none`, and no override. Native
controlled-scene source/tensor/cache evidence and native 26D context evidence
must exactly match the snapshot; forbidden future/outcome fields and unknown
failure schemas fail closed, and failure class is evidence-derived. The
independent reviewer reconstructs the speed-source and red-applicability masks,
source-valid/physical/all-K relations, and native-to-snapshot bindings. Release
schema `camp_dp_v25_ultra_a165_bounded_execute_release_v3` freezes native string
`device=cuda`; noncanonical, relative, `..`, symlink, alternate, or type-smuggled
output paths fail before nonce creation.

Focused verification passed locally with 159 tests and two Windows platform
skips. AutoDL passed the same integration scope with 161 tests, including Linux
flock/symlink behavior. A broader legacy v21 runner fixture still has four
pre-existing failures because it does not supply the already-required
`normalized_atom_matrix_sha256`; the new real public-tick regression passes and
that unrelated legacy fixture was not weakened.

Under the same implementation HEAD, the full source-only universe and bounded
design were rebuilt from identity0 without loading a model or simulator and
without candidate/K8/outcome access:

- source: `/root/autodl-tmp/camp_dp_v25_a165_route_signal_source_census_82dffe39_20260718T161700CST`, root `d9e1a391cab32ddefdc9e418b8347642929354ad6b1318e3031001416639c933`;
- source review: `/root/autodl-tmp/camp_dp_v25_a165_route_signal_source_review_82dffe39_20260718T161700CST`, root `f5ebf66697797555ed1ba3f1e9ab2ce73393c04a63fb0d25827be0f58e57b028`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a165_bounded_execution_plan_82dffe39_20260718T161700CST`, root `4b1d3869d8d7f4792e7cf4533cdc31f3ccd6c059af01050125c05943b4179adc`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a165_bounded_execution_plan_review_82dffe39_20260718T161700CST`, root `b0f76d563b86bc1e6d21fbfb563dc518fcdb71872a48552c8cbef0088b047d10`.

The implementation's strict verifier reopened the exact inventories, exit
codes, HEADS, source rows, reports, plan, and cross-links. The four-root binding
SHA is `484c819072810345097dab16321ff0d37a6c2f87692441efe37c5944e16104cd`.
Counts remain 1,653 formal, 1,500 executable, 153 retained, 146 mapped, 1,354
no-signal, 21 controlled, 125 observe, zero source failures, 243 unique bounded
identities, 244 ordered runs, and 15,616 prospective ticks. identity0 remains at
positions 0 and 243.

Final control-plane recheck before the documentation pointer commit found CAMP
and fixed DP tracked clean at the stated source HEADs, worker/GPU counts zero,
the corpus lock free, 46,910,328,832 free bytes, no A1.6.5 nonce ledger, no
release or bounded K8 output, and no Fresh B2 outcome artifact. This package
does not authorize release, nonce, K8, full-config/full-R, monitor, training,
calibration, Scene/V2I, Fresh, or outcome access. The only next action is Ultra
read-only review.

current_v25_status=v25_a165_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=82dffe39869bc0af7d0535d6fcf0ee2ae9f0d04f
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a165_bounded_execution_plan_82dffe39_20260718T161700CST
current_v25_artifact_root_sha256=4b1d3869d8d7f4792e7cf4533cdc31f3ccd6c059af01050125c05943b4179adc
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a165_bounded_execution_plan_review_82dffe39_20260718T161700CST
current_v25_review_artifact_root_sha256=b0f76d563b86bc1e6d21fbfb563dc518fcdb71872a48552c8cbef0088b047d10
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a165_route_signal_source_census_82dffe39_20260718T161700CST
current_v25_r0_authority_source_artifact_root_sha256=d9e1a391cab32ddefdc9e418b8347642929354ad6b1318e3031001416639c933
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a165_route_signal_source_review_82dffe39_20260718T161700CST
current_v25_r0_authority_source_review_artifact_root_sha256=f5ebf66697797555ed1ba3f1e9ab2ce73393c04a63fb0d25827be0f58e57b028
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a164_four_roots_machine_authority_eligible=false
current_v25_a165_release_schema=camp_dp_v25_ultra_a165_bounded_execute_release_v3
current_v25_a165_device=cuda
current_v25_a165_four_root_bindings_sha256=484c819072810345097dab16321ff0d37a6c2f87692441efe37c5944e16104cd
current_v25_a165_local_targeted_test_result=159_passed_2_skipped
current_v25_a165_autodl_targeted_test_result=161_passed
current_v25_a165_bounded_release_created=false
current_v25_a165_bounded_nonce_created=false
current_v25_a165_bounded_k8_executed=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46910328832
current_v25_phase=A1_6_5_phase_native_mask_device_output_authority_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_5_review_before_any_bounded_execute_release

## A1.6.6 independent causal-evidence and raw-output authority correction (2026-07-18 CST)

Ultra kept bounded execution closed after reproducing circular trust in the
A1.6.5 source-valid mask, non-exact failure schemas, output-path normalization
before authority, self-reported physical/all-K status, context values not
anchored to native causal evidence, an unchecked planned-red atom, and missing
end-to-end release/source bindings. The A1.6.5 roots remain immutable
diagnostic evidence and are not machine execution authority:

- source `d9e1a391cab32ddefdc9e418b8347642929354ad6b1318e3031001416639c933`;
- source review `f5ebf66697797555ed1ba3f1e9ab2ce73393c04a63fb0d25827be0f58e57b028`;
- plan `4b1d3869d8d7f4792e7cf4533cdc31f3ccd6c059af01050125c05943b4179adc`;
- plan review `b0f76d563b86bc1e6d21fbfb563dc518fcdb71872a48552c8cbef0088b047d10`.

Implementation source HEAD
`e9e2a0ba3ed30bd3adad2df72bad604225bfabde` makes only the authorized
A1.6.6 bounded correction. Per-tick evidence now persists canonical raw causal
inputs and hashes for route lanes, route speed limits and availability,
candidate-specific neighbor predictions, neighbor validity/history, static
objects, ego shape/state, signal mask, and the fixed-DP planned-red cost. The
native public receipt adds an exact pre-decision speed source, independently
binding the context ego speed to the same decision tick.

The post-run reviewer locally reconstructs route projection and speed-source
eligibility, candidate OBB/lane/signal physical feasibility and reasons,
source-valid/applicability masks, all-K-high-risk, the complete 26D no-V2I raw
context and source-complete mask, fixed-DP planned-red column 10, certified
red-stopping column 12, canonical `[0,10]` normalized affine scores, and the
lowest eligible argmin. It cross-binds those values to the native candidate0,
K8 rows, atoms, masks, selected index/trajectory, controlled signal receipts,
source row/root, release artifact/root/nonce, formal root, critical manifest,
and CUDA device. Candidate0 remains the operational-default alias from the
same forward, not a second forward or native-ranked Top-1.

Native receipt, public tick, safety, tracker, latency, final snapshot,
feature, and sidecar schemas use exact field/type/value checks. Unknown
`fault`, `success`, `aborted`, `crash`, exit/status code, future, outcome, or
failure fields fail closed at any nesting. The A1.6.6 release schema is
`camp_dp_v25_ultra_a166_bounded_execute_release_v4`; raw `--output-dir` text is
retained until authority succeeds, and relative, `..`, duplicate-separator,
trailing-separator, or symlink aliases fail before a nonce ledger or requested
output can be created. Post-authority failure alone may seal the exact
authorized directory.

Focused local verification passed 176 tests with two Windows-only Linux
flock/symlink skips. AutoDL passed all 178 tests, including real Linux locking
and symlink behavior. The same scope passed `py_compile`; local and staged
`git diff --check` were clean. Mutation coverage includes candidate0
source-mask/selection rewrite, all-false/all-true physical masks, native
pre-decision speed versus context contradiction, unknown/nested failure fields,
planned-red column 10 rewrite, raw `./`, `//`, trailing slash and symlink
aliases, pre-authority no-output/no-nonce, and release/formal/manifest/device
bindings.

Under the same implementation HEAD and with no model/simulator/candidate/DP
forward, the full 1,653-row route-source census/review and outcome-blind bounded
plan/review were rebuilt from identity0:

- source: `/root/autodl-tmp/camp_dp_v25_a166_route_signal_source_census_e9e2a0ba_20260718T173720CST`, root `dc91ed4f397dad00ec16a7c5933a786d3440f8f725c5749fb0aa7213a6d8397c`;
- source review: `/root/autodl-tmp/camp_dp_v25_a166_route_signal_source_review_e9e2a0ba_20260718T173720CST`, root `d89311d34525c0b8a77a26caf4fe408cd27eeed2d8c542b33993106324ef665a`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a166_bounded_execution_plan_e9e2a0ba_20260718T173720CST`, root `ff7882302b147c01bc6d935b5299304d00780747d6997c0e49a8f0febd3e27cd`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a166_bounded_execution_plan_review_e9e2a0ba_20260718T173720CST`, root `6185fcda37ef0b11ebf54dd37584f62ce0a6d1368241bbec140da40b82ac6095`.

The strict current verifier reopened all exact inventories, `run.exit=0`,
HEADS, reports, source rows, plan order, and cross-links. Four-root binding SHA
is `125e1026758890a75c8bb789e4121ca7f579858a97e3637beac160c1a9b16477`.
Counts remain 1,653 total, 1,500 executable, 153 retained, 146 mapped, 1,354
no-signal, 21 controlled overrides, 125 observe-mode routes, zero source
failures, 243 unique bounded identities, 244 ordered runs, identity0 at 0 and
243, and 15,616 prospective ticks. The plan records `k8_executed=false` and
`fresh_b2_opened=false`.

The final control-plane check found local/origin/GitHub/AutoDL aligned at the
implementation HEAD before this docs-only pointer commit, fixed DP clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, worker/GPU counts zero, corpus
lock free, free disk above the 10 GiB floor, and no A1.6.6 nonce ledger,
release, execution output, Fresh, or outcome access. Full-config/full-R,
monitor, training, calibration, Scene/V2I, and Fresh remain closed. The only
next gate is Ultra read-only A1.6.6 review; no bounded release may be created
without a new Ultra decision.

current_v25_status=v25_a166_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=e9e2a0ba3ed30bd3adad2df72bad604225bfabde
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a166_bounded_execution_plan_e9e2a0ba_20260718T173720CST
current_v25_artifact_root_sha256=ff7882302b147c01bc6d935b5299304d00780747d6997c0e49a8f0febd3e27cd
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a166_bounded_execution_plan_review_e9e2a0ba_20260718T173720CST
current_v25_review_artifact_root_sha256=6185fcda37ef0b11ebf54dd37584f62ce0a6d1368241bbec140da40b82ac6095
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a166_route_signal_source_census_e9e2a0ba_20260718T173720CST
current_v25_r0_authority_source_artifact_root_sha256=dc91ed4f397dad00ec16a7c5933a786d3440f8f725c5749fb0aa7213a6d8397c
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a166_route_signal_source_review_e9e2a0ba_20260718T173720CST
current_v25_r0_authority_source_review_artifact_root_sha256=d89311d34525c0b8a77a26caf4fe408cd27eeed2d8c542b33993106324ef665a
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_snapshot_schema=camp_dp_v25_controlled_train_snapshot_v8
current_v25_a165_four_roots_machine_authority_eligible=false
current_v25_a166_release_schema=camp_dp_v25_ultra_a166_bounded_execute_release_v4
current_v25_a166_device=cuda
current_v25_a166_four_root_bindings_sha256=125e1026758890a75c8bb789e4121ca7f579858a97e3637beac160c1a9b16477
current_v25_a166_local_targeted_test_result=176_passed_2_skipped
current_v25_a166_autodl_targeted_test_result=178_passed
current_v25_a166_bounded_release_created=false
current_v25_a166_bounded_nonce_created=false
current_v25_a166_bounded_k8_executed=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46901469184
current_v25_phase=A1_6_6_independent_source_physical_context_failure_output_authority_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_6_review_before_any_bounded_execute_release

## A1.6.7 exact receipt, native-header, and terminal authority correction (2026-07-18 CST)

Ultra accepted the A1.6.6 static source/plan science and control plane but kept
bounded execution closed after independently reproducing two machine-authority
bypasses. First, the execution source receipt and report checked exact field
sets without freezing every leaf's native type and value, so gate, count,
schema, outcome, terminal, and nested nonce-marker mutations could survive a
self-consistent reseal. Second, the native receipt did not independently bind
route/map/fixed-DP assets, seed/spawn/initial state, terminal result, or the
top-level derived summaries to the sealed plan and raw 64-tick evidence. The
A1.6.6 roots remain immutable diagnostic evidence and machine authority false:

- source `dc91ed4f397dad00ec16a7c5933a786d3440f8f725c5749fb0aa7213a6d8397c`;
- source review `d89311d34525c0b8a77a26caf4fe408cd27eeed2d8c542b33993106324ef665a`;
- plan `ff7882302b147c01bc6d935b5299304d00780747d6997c0e49a8f0febd3e27cd`;
- plan review `6185fcda37ef0b11ebf54dd37584f62ce0a6d1368241bbec140da40b82ac6095`.

Implementation source HEAD
`c6246642e26e792415e4f6b3ba82aaf02b75a1f3` makes only the authorized
A1.6.7 authority/schema correction. Release schema
`camp_dp_v25_ultra_a167_bounded_execute_release_v5` uses a new one-shot nonce
namespace, but no release or nonce was created. The independent post-run
reviewer now constructs complete expected source-receipt and execution-report
objects and requires recursive JSON-native strict equality. It independently
rebuilds the terminal receipt from the sealed plan, exact results, and raw run
evidence. `wall_seconds` is the sole variable leaf and accepts only a finite
nonnegative native integer/float.

For every run, the reviewer reopens the exact formal plan and canonical probe
template, verifies the fixed-DP `Route` source against git object
`7a1d33da...`, independently serializes the formal route to bind the route
pickle SHA, verifies the source map bytes, rebuilds the frozen spawn config,
and derives the initial input/state hashes. The bounded contract freezes 64
ticks with `final_step=63`, `goal_reached=false`, `reason=max_steps`, and zero
random NPC spawns. Exact trajectory and clearance log paths and all 64 log rows
are rebound to the native raw-tick positions, headings, and speeds. Fixed DP
checkpoint/args, seed 25001, the 14D scale receipt, and Python 3.12 annotation
compatibility token are exact. Top-level derived safety/secondary/latency
summaries are deliberately excluded from the authoritative bounded native
receipt and rejected if present; raw per-tick safety and latency evidence is
still retained and reviewed.

Parameterized mutation coverage walks every leaf of the source receipt,
execution report/terminal, nonce marker, and native header/result/scale/runtime
receipt. Deletion, nested extra fields, wrong values, and bool/int/float/string/
null smuggling all fail closed; a meta-contract requires the field sets used by
the reviewer to match the authoritative schemas. Local focused tests passed
191 with two Windows-only Linux flock/symlink skips. AutoDL Python 3.12.3
passed all 193 tests. Focused `py_compile`, local/staged/remote diff checks, and
tracked-clean checks passed.

Under the same implementation HEAD and without loading a model, simulator,
candidate generator, or executing a DP forward, the full source universe and
the outcome-blind bounded plan were rebuilt from identity0 and independently
reviewed:

- source: `/root/autodl-tmp/camp_dp_v25_a167_route_signal_source_census_c6246642_20260718T182116CST`, root `039b706a32a0f9aaefabf3e5e5f5d745d5127ecfc7ebe2091afdb94017a6a74d`;
- source review: `/root/autodl-tmp/camp_dp_v25_a167_route_signal_source_review_c6246642_20260718T182116CST`, root `8992f880956f421964be13dd5857b6ae714ed06e44acb07501ce6fef29b2581c`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a167_bounded_execution_plan_c6246642_20260718T182116CST`, root `88c2c60706ffb01e27152987719dee91597903a1929e1f4351daf097eb18855e`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a167_bounded_execution_plan_review_c6246642_20260718T182116CST`, root `4badcc8bf775f2b1c33edbb7788fb14d37fe17316d015bb487a63a0e19a915be`.

The current strict verifier reopened exact inventories, `run.exit=0`, HEADS,
reports, source rows, cross-links, plan order, and all four tie proofs.
Four-root binding SHA is
`266648422720feaceae06f6b42b032c76629acbce8bff87d03fab544da7d70ff`.
Counts remain 1,653 formal train identities, 1,500 executable, 153 retained,
146 mapped, 1,354 no-signal, 21 controlled overrides, 125 observe mode, zero
source failures, 243 unique bounded identities, 244 ordered runs, identity0 at
positions 0 and 243, and 15,616 prospective ticks. The plan records
`k8_executed=false` and `fresh_b2_opened=false`.

Final control-plane review before this pointer commit found local/origin/GitHub/
AutoDL aligned at the implementation HEAD, fixed DP clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, no A1.6.7 nonce ledger,
release, or execution output, worker/GPU counts zero, the corpus lock free, and
46,892,675,072 free bytes. Full-config/full-R, 1500x64, monitor, training,
calibration, Scene/V2I, Fresh B2 and outcome access remain closed. The only
next action is Ultra read-only A1.6.7 review; this package does not authorize a
bounded release or K8 execution.

current_v25_status=v25_a167_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=c6246642e26e792415e4f6b3ba82aaf02b75a1f3
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a167_bounded_execution_plan_c6246642_20260718T182116CST
current_v25_artifact_root_sha256=88c2c60706ffb01e27152987719dee91597903a1929e1f4351daf097eb18855e
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a167_bounded_execution_plan_review_c6246642_20260718T182116CST
current_v25_review_artifact_root_sha256=4badcc8bf775f2b1c33edbb7788fb14d37fe17316d015bb487a63a0e19a915be
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a167_route_signal_source_census_c6246642_20260718T182116CST
current_v25_r0_authority_source_artifact_root_sha256=039b706a32a0f9aaefabf3e5e5f5d745d5127ecfc7ebe2091afdb94017a6a74d
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a167_route_signal_source_review_c6246642_20260718T182116CST
current_v25_r0_authority_source_review_artifact_root_sha256=8992f880956f421964be13dd5857b6ae714ed06e44acb07501ce6fef29b2581c
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a166_four_roots_machine_authority_eligible=false
current_v25_a167_release_schema=camp_dp_v25_ultra_a167_bounded_execute_release_v5
current_v25_a167_device=cuda
current_v25_a167_four_root_bindings_sha256=266648422720feaceae06f6b42b032c76629acbce8bff87d03fab544da7d70ff
current_v25_a167_local_targeted_test_result=191_passed_2_skipped
current_v25_a167_autodl_targeted_test_result=193_passed
current_v25_a167_bounded_release_created=false
current_v25_a167_bounded_nonce_created=false
current_v25_a167_bounded_k8_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46892675072
current_v25_phase=A1_6_7_exact_receipt_native_header_terminal_authority_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_7_review_before_any_bounded_execute_release

## A1.6.8 full causal-input, goal-terminal, and serialization evidence correction (2026-07-18 CST)

Ultra accepted the A1.6.7 static source/design counts but kept bounded execution
closed because three scientific-evidence contracts were incomplete. The
initial-input digest was still circularly anchored to producer receipts rather
than an independently readable preimage; `goal_d` and final reason were not
derived from the formal goal plus the full trajectory; and authoritative
JSON/JSONL and nested native evidence could be re-encoded or extended without
one complete byte/schema policy. The A1.6.7 roots remain unchanged, immutable
diagnostic evidence and machine-authority false:

- source `039b706a32a0f9aaefabf3e5e5f5d745d5127ecfc7ebe2091afdb94017a6a74d`;
- source review `8992f880956f421964be13dd5857b6ae714ed06e44acb07501ce6fef29b2581c`;
- plan `88c2c60706ffb01e27152987719dee91597903a1929e1f4351daf097eb18855e`;
- plan review `4badcc8bf775f2b1c33edbb7788fb14d37fe17316d015bb487a63a0e19a915be`.

Implementation source HEAD
`b7dd2932e4e3667ae3204e0a3698340f5bd5b2e5` changes only the bounded
scientific-evidence path. The native hook copies all 16 fixed-DP causal arrays
before tensor conversion/forward. The prospective runner stores all 64 ticks
in a content-addressed compressed NPZ shard with exact array name, dtype,
shape, and raw-byte digests. The independent reviewer contains its own
deterministic array-mapping digest implementation and reconstructs each tick's
input digest and initial state from the saved preimage. Coordinated changes to
receipt, sidecar, initial state, index, or seal therefore cannot replace the
independent data source; missing/extra arrays, dtype/shape/byte mutations, and
cross-run shard swaps fail closed.

The reviewer also implements the fixed-DP goal oracle independently from the
pinned git-object contract: each of the 64 trajectory positions/headings is
compared with the formal goal using the 2 m arrival tolerance and 25 m pass
window, and `goal_d`, minimum goal distance, `goal_reached`, `goal_passed`, and
the final reason are derived rather than assumed. Trajectory and clearance log
schemas are exact; red stop-line geometry is finite and source-bound; unknown
nested evidence is rejected.

Every retained CAMP-authored authority JSON now uses canonical UTF-8, sorted
compact keys, finite values, and exactly one trailing LF. Authority JSONL uses
the same per-row contract. The reviewer uses a local strict parser that rejects
duplicate keys and non-finite values, compares original bytes to the canonical
oracle, and registers exactly one byte/schema policy for every sealed execution
path. Noncanonical spacing, double LF, duplicate-key first/last variants,
nested evidence additions, goal-distance coordination, and NPZ byte mutations
are covered by focused tests.

Local verification passed the focused 144-test suite with two platform skips
and the expanded V25 regression suite with 247 passed and two Windows-only
skips. AutoDL Python 3.12.3 passed all 249 expanded tests. All six modified
files passed `py_compile`; local/staged/remote diff checks passed. CAMP local,
origin/GitHub, and AutoDL were aligned at the implementation HEAD before the
pointer-only commit; fixed DP remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Without loading a model, starting a simulator, generating candidates, or
executing any DP forward, the source universe and bounded design were rebuilt
from identity0 and independently reviewed under the same implementation HEAD:

- source: `/root/autodl-tmp/camp_dp_v25_a168_route_signal_source_census_b7dd2932_20260718T213107CST`, root `48bdbf77a2df14a1002f371f32fab47604f3daaa4b09646f434b0c843aa3f272`;
- source review: `/root/autodl-tmp/camp_dp_v25_a168_route_signal_source_review_b7dd2932_20260718T213107CST`, root `c80424c1b217afe7d603e939233d0c9c8dd3461d2dde0f28988181974dd09c90`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a168_bounded_execution_plan_b7dd2932_20260718T213107CST`, root `b9660ad7ee5ecda719a463e0cbb593c915bb967ad6d139ab6e63ff7a275331be`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a168_bounded_execution_plan_review_b7dd2932_20260718T213107CST`, root `fbc312aa00730595adf185157f683fb60cfbaa5ea048234b1b7185adbc756a21`.

The current strict verifier reopened exact inventories, `run.exit=0`, HEADS,
reports, source rows, cross-links, plan order, and all tie proofs. Four-root
binding SHA is
`7cc450281423580aca4485a36cdfc05b63ae9e199e000428b736234543eb7978`.
Counts remain 1,653 formal train identities, 1,500 executable, 153 retained,
146 mapped, 1,354 no-signal, 21 controlled overrides, 125 observe mode, zero
source failures, 243 unique bounded identities, 244 ordered runs, identity0 at
positions 0 and 243, and 15,616 prospective ticks.

Final control-plane evidence before the pointer-only commit found worker/GPU
counts zero, the shared corpus lock free, and 46,892,244,992 free bytes. No
A1.6.8 bounded release, nonce, execution output, K8, full-config/full-R,
1500x64, monitor, training, calibration, Scene/V2I, Fresh B2, or outcome access
occurred. The new four roots are not machine-execution authority until Ultra
reviews them. The only next action is Ultra read-only A1.6.8 review.

current_v25_status=v25_a168_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=b7dd2932e4e3667ae3204e0a3698340f5bd5b2e5
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a168_bounded_execution_plan_b7dd2932_20260718T213107CST
current_v25_artifact_root_sha256=b9660ad7ee5ecda719a463e0cbb593c915bb967ad6d139ab6e63ff7a275331be
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a168_bounded_execution_plan_review_b7dd2932_20260718T213107CST
current_v25_review_artifact_root_sha256=fbc312aa00730595adf185157f683fb60cfbaa5ea048234b1b7185adbc756a21
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a168_route_signal_source_census_b7dd2932_20260718T213107CST
current_v25_r0_authority_source_artifact_root_sha256=48bdbf77a2df14a1002f371f32fab47604f3daaa4b09646f434b0c843aa3f272
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a168_route_signal_source_review_b7dd2932_20260718T213107CST
current_v25_r0_authority_source_review_artifact_root_sha256=c80424c1b217afe7d603e939233d0c9c8dd3461d2dde0f28988181974dd09c90
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a167_four_roots_machine_authority_eligible=false
current_v25_a168_release_schema=camp_dp_v25_ultra_a168_bounded_execute_release_v6
current_v25_a168_device=cuda
current_v25_a168_four_root_bindings_sha256=7cc450281423580aca4485a36cdfc05b63ae9e199e000428b736234543eb7978
current_v25_a168_four_roots_machine_authority_eligible=false
current_v25_a168_local_targeted_test_result=247_passed_2_skipped
current_v25_a168_autodl_targeted_test_result=249_passed
current_v25_a168_bounded_release_created=false
current_v25_a168_bounded_nonce_created=false
current_v25_a168_bounded_k8_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46892244992
current_v25_phase=A1_6_8_full_causal_input_goal_terminal_and_serialization_evidence_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_8_review_before_any_bounded_execute_release

## A1.6.9 terminal timing, scene-materialization, and byte-policy correction (2026-07-18 CST)

Ultra accepted the A1.6.8 static root integrity and the independent digest of
the saved 16-array materialization, but kept bounded execution closed for three
scientific-evidence inconsistencies. Fixed-DP trajectory and clearance rows are
written before tracker advance while wrapper safety rows are post-advance, so
the prior reviewer joined different physical times at the same tick index. The
16-array training-NPZ representation was causal scene materialization rather
than the normalized/batched input actually passed to the fixed-DP forward. The
byte/schema policy registry also described every authoritative file without
executing every policy at the real four-root, release and post-run review
entrypoints. The A1.6.8 roots remain unchanged, immutable diagnostic evidence
and machine-authority false:

- source `48bdbf77a2df14a1002f371f32fab47604f3daaa4b09646f434b0c843aa3f272`;
- source review `c80424c1b217afe7d603e939233d0c9c8dd3461d2dde0f28988181974dd09c90`;
- plan `b9660ad7ee5ecda719a463e0cbb593c915bb967ad6d139ab6e63ff7a275331be`;
- plan review `fbc312aa00730595adf185157f683fb60cfbaa5ea048234b1b7185adbc756a21`.

Implementation source HEAD
`1779fb8993ef66151c8d641732a7861d1135dd6a` changes only this bounded
scientific-evidence path. The independent terminal oracle now derives the
2 m goal tolerance and 25 m pass-window result exclusively from the formal goal
and the 64 pre-advance trajectory rows. Trajectory row zero is bound to the
independently reconstructed snapped initial world state. For indices zero
through 62, post-advance safety row `i` must equal trajectory row `i+1` in
position, heading and speed; clearance row `i` binds trajectory row `i`.
Post-advance safety row 63 is retained as the state after the 64th advance but
is not treated as a goal-check trajectory row. Focused tests use distinct
pre-state and post-state fixtures and cover the last-row exclusion.

The 16-array content-addressed NPZ shard and all corresponding receipt fields
are renamed to causal scene-materialization evidence. They no longer claim to
be the actual fixed-DP forward input. The reviewer still independently rebuilds
the deterministic materialization digest from exact names, dtypes, shapes and
bytes, while initial-world-state authority comes from the formal route/spawn,
the pinned fixed-DP snapping contract and trajectory row zero. Any later fixed-
DP execution remains evidenced by the sealed candidate0/K8 candidate tensor and
output SHAs, not by the scene-materialization digest.

All CAMP-authored four-root, release and prospective execution authority JSON
uses strict canonical UTF-8, sorted compact keys, finite values and exactly one
trailing LF; authority JSONL applies the same contract per row. HEADS and
run.exit have exact byte contracts. COMMAND is explicitly non-authoritative
diagnostic text with strict framing. Fixed-DP native trajectory/clearance logs
are not rewritten, but duplicate fields, nonfinite values and schema/value
drift fail closed. The manifest policy dispatcher now actually opens and
validates every registered path. End-to-end tests rewrite and reseal artifacts,
then call the real `verify_four_root_chain`, bounded-release verification and
post-run review entrypoints; noncanonical and duplicate-key variants fail.

The six implementation/test files passed focused `py_compile`. A single local
consolidated batch passed 222 tests with two Windows-only skips. On AutoDL, the
existing Python 3.12 environment passed the corresponding 224 tests. No local
or remote tests overlapped, no polling monitor or unconditional process cleanup
was created, and all commands ended naturally before this review gate.

Without loading a model, starting a simulator, generating candidates, or
executing any DP forward, the full source universe and outcome-blind bounded
plan were rebuilt from identity0 under the same implementation HEAD and
independently reviewed:

- source: `/root/autodl-tmp/camp_dp_v25_a169_route_signal_source_census_1779fb89_20260718T222955CST`, root `92c8c5b878d86f7a9ce043b543ee40f78add54f63fbdfe52425f48d34ba43330`;
- source review: `/root/autodl-tmp/camp_dp_v25_a169_route_signal_source_review_1779fb89_20260718T222955CST`, root `88c028e1534edd6cd3458dc964d34fbb1ccf0c45adbf5d9cf160cba5967d1daa`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a169_bounded_execution_plan_1779fb89_20260718T222955CST`, root `357f34ed39467f6c16fe64e41118cc48a8a922c3ee51d9ba657b98954930110b`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a169_bounded_execution_plan_review_1779fb89_20260718T222955CST`, root `9d05e1617e65a61a95f2543821b32dddb830c0d083d88017a14e01633e41b15e`.

The A1.6.9 strict verifier reopened exact inventories, `run.exit=0`, HEADS,
reports, source rows, cross-links, plan order and all tie proofs. Four-root
binding SHA is
`a7d0249af3ba2b8fdccddec820d6eb17a47b59582769970661a364e8e0bb6980`.
Counts remain 1,653 formal train identities, 1,500 executable, 153 retained,
146 mapped, 1,354 no-signal, 21 controlled overrides, 125 observe mode, zero
source failures, 243 unique bounded identities, 244 ordered runs, identity0 at
positions 0 and 243, and 15,616 prospective ticks. The plan records
`k8_executed=false` and `fresh_b2_opened=false`.

Control-plane evidence before the pointer-only commit found worker/GPU counts
zero, the shared corpus lock free, and 46,883,004,416 free bytes. No A1.6.9
release, nonce, execution output, K8, full-config/full-R, 1500x64, monitor,
training, calibration, Scene/V2I, Fresh B2 or outcome access occurred. The
four roots are not machine-execution authority until Ultra reviews them. The
only next action is Ultra read-only A1.6.9 review.

current_v25_status=v25_a169_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=1779fb8993ef66151c8d641732a7861d1135dd6a
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a169_bounded_execution_plan_1779fb89_20260718T222955CST
current_v25_artifact_root_sha256=357f34ed39467f6c16fe64e41118cc48a8a922c3ee51d9ba657b98954930110b
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a169_bounded_execution_plan_review_1779fb89_20260718T222955CST
current_v25_review_artifact_root_sha256=9d05e1617e65a61a95f2543821b32dddb830c0d083d88017a14e01633e41b15e
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a169_route_signal_source_census_1779fb89_20260718T222955CST
current_v25_r0_authority_source_artifact_root_sha256=92c8c5b878d86f7a9ce043b543ee40f78add54f63fbdfe52425f48d34ba43330
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a169_route_signal_source_review_1779fb89_20260718T222955CST
current_v25_r0_authority_source_review_artifact_root_sha256=88c028e1534edd6cd3458dc964d34fbb1ccf0c45adbf5d9cf160cba5967d1daa
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a168_four_roots_machine_authority_eligible=false
current_v25_a169_release_schema=camp_dp_v25_ultra_a169_bounded_execute_release_v7
current_v25_a169_device=cuda
current_v25_a169_four_root_bindings_sha256=a7d0249af3ba2b8fdccddec820d6eb17a47b59582769970661a364e8e0bb6980
current_v25_a169_four_roots_machine_authority_eligible=false
current_v25_a169_local_targeted_test_result=222_passed_2_skipped
current_v25_a169_autodl_targeted_test_result=224_passed
current_v25_a169_bounded_release_created=false
current_v25_a169_bounded_nonce_created=false
current_v25_a169_bounded_k8_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46883004416
current_v25_phase=A1_6_9_terminal_timing_scene_materialization_and_byte_policy_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_9_review_before_any_bounded_execute_release

## A1.6.10 terminal reachability, seeded-history, float32, and full-manifest JSON correction (2026-07-18 CST)

Ultra accepted the A1.6.9 source/design roots, causal scene-materialization
boundary, max-steps temporal direction, and canonical execution-policy wiring,
but kept bounded execution closed for four exact evidence gaps. A 64-post-
safety receipt could still claim a pre-advance row-63 goal termination that the
fixed DP cannot produce; initial speed was equated to configured spawn speed
instead of the seeded noisy-history velocity; initial/terminal arithmetic mixed
formal float64 values with Route float32 values; and two source JSON payloads
were inventoried without being opened by the four-root strict loader. The four
A1.6.9 roots remain unchanged, immutable diagnostic evidence and machine-
authority false:

- source `92c8c5b878d86f7a9ce043b543ee40f78add54f63fbdfe52425f48d34ba43330`;
- source review `88c028e1534edd6cd3458dc964d34fbb1ccf0c45adbf5d9cf160cba5967d1daa`;
- plan `357f34ed39467f6c16fe64e41118cc48a8a922c3ee51d9ba657b98954930110b`;
- plan review `9d05e1617e65a61a95f2543821b32dddb830c0d083d88017a14e01633e41b15e`.

Implementation source HEAD
`ee457bd845f0caa83c4891b1c4dacfe28d07bbbe` changes only the prospective
bounded evidence path. The 244-run, 64-decision denominator remains frozen.
Both producer and independent reviewer now require a run with exactly 64
post-safety ticks to end at `final_step=63`, `goal_reached=false`, and
`reason=max_steps`. If the formal-goal oracle reaches or passes the goal at any
pre-advance trajectory row, including row 63, the coexistence of 64 post-safety
ticks is impossible and fails closed. Max-steps with the retained post-safety
row 63 remains valid. No fixed-DP code or behavior was changed.

The independent initial-world oracle validates the pinned fixed-DP builder
source and locally reproduces its `generate_history` and velocity chain:
31 float32 history rows, seed 25001 through legacy NumPy MT19937, the same
backward-polyline interpolation and lateral Gaussian draw order, the explicit
heading override, and `(history[-1]-history[-2])/0.1` stored as float32 before
the speed norm. It handles the fixed-DP fallback when configured ego speed is
absent. A real AutoDL fixed-source/formal-route fixture compares the independent
result with the actual pinned `LaneletSceneBuilder.generate_history`; the noisy
row-zero speed is not silently replaced by configured spawn speed.

The initial and terminal oracles independently rebuild Route start and goal as
float32. Snapping uses that float32 start; distance uses float32 position minus
float32 goal followed by the same NumPy norm; the ego forward vector and pass-
window dot product are float32. Logged `goal_d` must equal the value produced by
that exact chain. Decimal coordinates not exactly representable in float32 and
large-coordinate fixtures cover both ordinary and amplified rounding cases.

The four-root verifier now executes strict canonical JSON parsing for every
`.json` file in each verified manifest before reading role-specific fields.
This includes `formal_route_source_contract_supplement.json` and
`route_signal_source_receipts.json`, in addition to reports and the bounded
plan. UTF-8 errors, duplicate keys, nonfinite values, noncompact/sorted bytes,
or a missing single trailing LF fail closed even after resealing. Both omitted
source payloads have mutation tests through the real `verify_four_root_chain`;
representative execution policies continue to be tested through the real
post-run review entrypoint. COMMAND remains non-authoritative diagnostic text.

The four modified code/test files passed `py_compile`. The single consolidated
local regression batch passed 226 tests with three platform/source-fixture
skips. The single AutoDL Python 3.12 batch passed all 229 tests, including the
real fixed-source history fixture. No test batch overlapped another, no
polling monitor or unconditional process cleanup was created, and all commands
ended naturally before this review gate.

Without loading a model, starting a simulator, generating candidates, or
executing a DP forward, the full source universe and outcome-blind bounded plan
were rebuilt from identity0 under the same implementation HEAD and independently
reviewed:

- source: `/root/autodl-tmp/camp_dp_v25_a1610_route_signal_source_census_ee457bd8_20260718T225856CST`, root `6e78cf3b2178572163d5642c2b3dbcae142b09156e19869cc51205eab3960270`;
- source review: `/root/autodl-tmp/camp_dp_v25_a1610_route_signal_source_review_ee457bd8_20260718T225856CST`, root `86d4c4f2e38a385cb998db1d73cecfe152094dfa987d61e78c0555be5d30b26d`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a1610_bounded_execution_plan_ee457bd8_20260718T225856CST`, root `290798d1040abd64e29959f2076c795e6372ee14046b6c42038eb0ff7633db3b`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a1610_bounded_execution_plan_review_ee457bd8_20260718T225856CST`, root `090a952ea77d8edeb0ccf9b8dd5fa084b79bad3b90c24c986497aeedb8380dd9`.

The A1.6.10 strict verifier reopened every JSON payload, exact inventories,
`run.exit=0`, HEADS, reports, source rows, cross-links, plan order and all tie
proofs. Four-root binding SHA is
`4773fa3f290cf997305235f101a97467da890c0981166e4ced5ef3788a040497`.
Counts remain 1,653 formal train identities, 1,500 executable, 153 retained,
146 mapped, 1,354 no-signal, 21 controlled overrides, 125 observe mode, zero
source failures, 243 unique bounded identities, 244 ordered runs, identity0 at
positions 0 and 243, and 15,616 prospective ticks. The plan records
`k8_executed=false` and `fresh_b2_opened=false`.

Control-plane evidence before the pointer-only commit found worker/GPU counts
zero, the shared corpus lock free, the A1.6.10 nonce ledger absent, and
46,874,378,240 free bytes. No A1.6.10 release, nonce, execution output, K8,
full-config/full-R, 1500x64, monitor, training, calibration, Scene/V2I, Fresh B2
or outcome access occurred. The four roots are not machine-execution authority
until Ultra reviews them. The only next action is Ultra read-only A1.6.10
review.

current_v25_status=v25_a1610_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=ee457bd845f0caa83c4891b1c4dacfe28d07bbbe
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a1610_bounded_execution_plan_ee457bd8_20260718T225856CST
current_v25_artifact_root_sha256=290798d1040abd64e29959f2076c795e6372ee14046b6c42038eb0ff7633db3b
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a1610_bounded_execution_plan_review_ee457bd8_20260718T225856CST
current_v25_review_artifact_root_sha256=090a952ea77d8edeb0ccf9b8dd5fa084b79bad3b90c24c986497aeedb8380dd9
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a1610_route_signal_source_census_ee457bd8_20260718T225856CST
current_v25_r0_authority_source_artifact_root_sha256=6e78cf3b2178572163d5642c2b3dbcae142b09156e19869cc51205eab3960270
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a1610_route_signal_source_review_ee457bd8_20260718T225856CST
current_v25_r0_authority_source_review_artifact_root_sha256=86d4c4f2e38a385cb998db1d73cecfe152094dfa987d61e78c0555be5d30b26d
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a169_four_roots_machine_authority_eligible=false
current_v25_a1610_release_schema=camp_dp_v25_ultra_a1610_bounded_execute_release_v8
current_v25_a1610_device=cuda
current_v25_a1610_four_root_bindings_sha256=4773fa3f290cf997305235f101a97467da890c0981166e4ced5ef3788a040497
current_v25_a1610_four_roots_machine_authority_eligible=false
current_v25_a1610_local_targeted_test_result=226_passed_3_skipped
current_v25_a1610_autodl_targeted_test_result=229_passed
current_v25_a1610_bounded_release_created=false
current_v25_a1610_bounded_nonce_created=false
current_v25_a1610_bounded_k8_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46874378240
current_v25_phase=A1_6_10_terminal_reachability_seeded_history_float32_and_full_manifest_json_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_10_review_before_any_bounded_execute_release

## A1.6.11 Python-Random History and Real GitHub Authority Correction (2026-07-18 CST)

Ultra accepted the A1.6.10 terminal-reachability, Route float32, and complete
four-root JSON corrections, and froze A1.6.11 as the final bounded-execute
correction gate. This gate changed only two verified items. First, the
independent fixed-DP history oracle now reproduces the Python `random` stream
used by `LaneletSceneBuilder._build_backward_polyline` when the snapped start
lanelet has multiple predecessors. It verifies that the formal route has a
nonempty explicit lanelet sequence, saves the process Python RNG state, seeds
with 25001 only around the backward-polyline call, and restores the original
state in `finally`. The existing isolated NumPy `RandomState(25001)` remains
unchanged. Second, the repository chain was repaired through a normal GitHub
push rather than a local tracking-ref update or AutoDL bundle.

The new formal-corpus branching-predecessor regression deliberately perturbs
global Python RNG state, invokes the independent oracle repeatedly, verifies
that the caller's RNG state is unchanged, and compares the result to the real
pinned builder with both NumPy and Python RNGs seeded to 25001. The existing
real fixed-source history comparison now also saves, seeds, and restores both
RNGs. The formal route IDs are explicitly nonempty, so fixed replay does not
call `find_route` or consume an earlier Python-random draw before history
generation. No schema/version name, receipt, atom, source, terminal, float32,
fixed-DP, K8, trajectory, denominator, or claim contract changed.

Implementation source commit is
`bcbb27ec5babccacdf009787d886aabfd9f4babe`. A normal `git push origin main`
advanced the real GitHub branch from `ee457bd845f0caa83c4891b1c4dacfe28d07bbbe`,
and a fresh independent `git ls-remote origin refs/heads/main` returned the
implementation commit exactly. AutoDL then performed a normal GitHub fetch and
ff-only merge to the same commit; fixed DP remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The frozen focused regression scope passed 226 local tests with four platform/
source-fixture skips. AutoDL Python 3.12 passed all 230 tests, including the
real fixed-source history fixture and the new branching-predecessor comparison.
Native-hook and pointer subsets ran serially after their authority inputs existed.
The relevant implementation/test files passed `py_compile`; local and remote
`git diff --check` and tracked-clean checks passed. Tests ran serially, all
commands ended naturally before this gate, and no polling monitor, taskkill, or
concurrent local shell batch was used.

Without loading a model, starting a simulator, generating candidates, executing
a DP forward, or reading any outcome, the static source and bounded-plan package
was rebuilt from identity0 under the same implementation commit:

- source: `/root/autodl-tmp/camp_dp_v25_a1611_route_signal_source_census_bcbb27ec_20260718T233203CST`, root `8015ace9fa00a84ed5524b0dd9bfa31a29937e6aad37fe6a46ea505000613a72`;
- source review: `/root/autodl-tmp/camp_dp_v25_a1611_route_signal_source_review_bcbb27ec_20260718T233203CST`, root `87b7bbf319665bc3023d6495f0cd5f59d101e12a01b4cdd353c002ab3bc03f91`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a1611_bounded_execution_plan_bcbb27ec_20260718T233203CST`, root `4c72abbb9435a88805a65e0dc9b41030f371130a8896b3a11766265eb359106e`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a1611_bounded_execution_plan_review_bcbb27ec_20260718T233203CST`, root `5047b3947d0b703b7b5eed6468ced519b29e5e6096104aa52c456f06695adf88`.

The strict four-root verifier reopened the exact inventories, every registered
JSON payload, `run.exit=0`, HEADS, reports, source rows, cross-links, ordered
plan, and four tie proofs. Four-root binding SHA is
`a9979c8e90a06f48cc58c2b12359b2f9e1c70506da5a900cdffd20119fef229b`.
Counts remain 1,653 formal train identities, 1,500 executable, 153 retained,
146 mapped signal, 1,354 no signal, 21 controlled override, 125 observe mode,
zero source failures, 243 unique bounded identities, 244 ordered runs,
identity0 at positions 0 and 243, and 15,616 prospective ticks.

The final control-plane check found worker/GPU counts zero, the shared corpus
lock free, 46,857,494,528 free bytes, and no A1.6.11 release, nonce, execution
output, K8, full-config/full-R, 1500x64, monitor, training, calibration,
Scene/V2I, Fresh B2, or outcome access. The A1.6.10 roots remain immutable
diagnostic evidence with machine authority false. The A1.6.11 roots are also
machine-authority false until the single frozen Ultra read-only review; no
further preventive A1.6.x gate is authorized.

current_v25_status=v25_a1611_static_source_plan_package_passed_ultra_bounded_execute_release_review_required
current_v25_source_head=bcbb27ec5babccacdf009787d886aabfd9f4babe
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a1611_bounded_execution_plan_bcbb27ec_20260718T233203CST
current_v25_artifact_root_sha256=4c72abbb9435a88805a65e0dc9b41030f371130a8896b3a11766265eb359106e
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611_bounded_execution_plan_review_bcbb27ec_20260718T233203CST
current_v25_review_artifact_root_sha256=5047b3947d0b703b7b5eed6468ced519b29e5e6096104aa52c456f06695adf88
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a1611_route_signal_source_census_bcbb27ec_20260718T233203CST
current_v25_r0_authority_source_artifact_root_sha256=8015ace9fa00a84ed5524b0dd9bfa31a29937e6aad37fe6a46ea505000613a72
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611_route_signal_source_review_bcbb27ec_20260718T233203CST
current_v25_r0_authority_source_review_artifact_root_sha256=87b7bbf319665bc3023d6495f0cd5f59d101e12a01b4cdd353c002ab3bc03f91
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a169_four_roots_machine_authority_eligible=false
current_v25_a1611_release_schema=camp_dp_v25_ultra_a1610_bounded_execute_release_v8
current_v25_a1611_device=cuda
current_v25_a1611_four_root_bindings_sha256=a9979c8e90a06f48cc58c2b12359b2f9e1c70506da5a900cdffd20119fef229b
current_v25_a1611_four_roots_machine_authority_eligible=false
current_v25_a1611_local_targeted_test_result=226_passed_4_skipped
current_v25_a1611_autodl_targeted_test_result=230_passed
current_v25_a1611_bounded_release_created=false
current_v25_a1611_bounded_nonce_created=false
current_v25_a1611_bounded_k8_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46857494528
current_v25_phase=A1_6_11_python_random_history_and_real_github_alignment_corrected_static_four_root_review_required_k8_closed
next_work_target=ultra_read_only_A1_6_11_final_correction_review_before_bounded_execute_release

## A1.6.11-R2 closeout and R3 interpreter qualification/static-root rebuild (2026-07-19 CST)

Ultra formally closed A1.6.11-R2 as
`fail_closed_stopped_before_test_execution`. Implementation source HEAD
`0a07183913844dd9ab0c1e7c619c42be81c579ab` classifies the exact frozen probe
template and fixed-DP args as external legacy JSON objects: both retain exact
path/SHA/schema/value binding plus strict UTF-8, duplicate-key, nonfinite, and
top-level-object checks, while CAMP-authored authority JSON remains canonical
compact/sorted/single-LF. Local py_compile, diff-check, and the frozen focused
scope passed 238 tests with five platform/source skips. The first R2 AutoDL
invocation nevertheless used an unavailable bare `python` command and stopped
before py_compile, pytest, the actual release-create entry, or any authority
directory. R2 was never a PASS; its nonce
`4c8cc2086d77cf5969fa0ce1bfc8d22305269f74b11fd8074869977a5d3a5d26`
is permanently revoked unconsumed, and its exact release/execution/review
directories remain absent.

Ultra separately authorized the R3 environment-interpreter gate without a repo
or schema change. The exact launcher
`/root/autodl-tmp/dp312_venv/bin/python` exists and is executable, resolves to
`/root/miniconda3/bin/python3.12`, and reported `sys.executable` as the launcher,
`sys.prefix` as `/root/autodl-tmp/dp312_venv`, Python 3.12.3, and pytest 8.3.5.
The same interpreter imported pytest, NumPy, Torch, and SciPy. The exact R3
qualification then passed, followed serially by py_compile and the unchanged
frozen AutoDL scope: 243 tests passed, including the actual temporary
`create_diffusion_planner_v25_a163_bounded_release.py` entry through both
external legacy assets, the four-root chain, execution assets, critical
manifest, and decision construction. No package install, PATH change, new venv,
interpreter search, nonce, model, simulator, candidate generation, K8, training,
calibration, Scene/V2I, Fresh, or outcome access occurred.

With CAMP source/pointer both still at `0a071839...` and fixed DP clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, the static package was rebuilt
from identity0 and independently reviewed:

- source census: `/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_census_0a071839_20260719T001726CST`, root `944f07399616f8870385827204ac2dcfef29637828e0a40112cb266a908aa3aa`;
- source review: `/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_review_0a071839_20260719T001726CST`, root `4bef57a9bcea8b911cbbf3880f2c29d575b5fc1c9696e222a587eae675c1a989`;
- bounded plan: `/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_0a071839_20260719T001726CST`, root `27bc6cd53da17535ab573016102d26d6d21d26b951bb16739d56bc5c8720b7b8`;
- bounded plan review: `/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_review_0a071839_20260719T001726CST`, root `44453e0ad2220b29bbd9bb473d41f927429a6ed899cecb6c1e990f8c8bcf96f4`.

The exact four-root verifier reopened the inventories, canonical JSON payloads,
`run.exit=0`, HEADS, source rows, cross-links, ordered runs, and four tie proofs.
Four-root binding SHA is
`163c4fd7c67d924a27c7cf9b47ec986e915d3db1fe0f54ff10a7077fe344b5eb`.
Counts remain 1,653 formal train identities, 1,500 executable, 153 retained,
146 mapped signal, 1,354 no signal, 21 controlled override, 125 observe mode,
zero source failures, 243 unique bounded identities, 244 ordered runs,
identity0 at positions 0 and 243, and 15,616 prospective ticks. Worker/GPU
counts remained zero, the shared lock was free, and free space was
46,856,781,824 bytes. These new four roots remain machine-authority-ineligible
until Ultra's final R3 release decision; bounded K8 remains closed.

current_v25_status=v25_a1611_r3_static_source_plan_package_passed_ultra_final_release_review_required
current_v25_source_head=0a07183913844dd9ab0c1e7c619c42be81c579ab
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_0a071839_20260719T001726CST
current_v25_artifact_root_sha256=27bc6cd53da17535ab573016102d26d6d21d26b951bb16739d56bc5c8720b7b8
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_review_0a071839_20260719T001726CST
current_v25_review_artifact_root_sha256=44453e0ad2220b29bbd9bb473d41f927429a6ed899cecb6c1e990f8c8bcf96f4
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_census_0a071839_20260719T001726CST
current_v25_r0_authority_source_artifact_root_sha256=944f07399616f8870385827204ac2dcfef29637828e0a40112cb266a908aa3aa
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_review_0a071839_20260719T001726CST
current_v25_r0_authority_source_review_artifact_root_sha256=4bef57a9bcea8b911cbbf3880f2c29d575b5fc1c9696e222a587eae675c1a989
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a169_four_roots_machine_authority_eligible=false
current_v25_a1611_release_schema=camp_dp_v25_ultra_a1610_bounded_execute_release_v8
current_v25_a1611_device=cuda
current_v25_a1611_four_root_bindings_sha256=163c4fd7c67d924a27c7cf9b47ec986e915d3db1fe0f54ff10a7077fe344b5eb
current_v25_a1611_four_roots_machine_authority_eligible=false
current_v25_a1611_local_targeted_test_result=238_passed_5_skipped
current_v25_a1611_autodl_targeted_test_result=243_passed
current_v25_a1611_r2_status=fail_closed_stopped_before_test_execution
current_v25_a1611_r2_nonce_status=permanently_revoked_unconsumed
current_v25_a1611_r3_interpreter=/root/autodl-tmp/dp312_venv/bin/python
current_v25_a1611_r3_interpreter_realpath=/root/miniconda3/bin/python3.12
current_v25_a1611_r3_python_version=3.12.3
current_v25_a1611_r3_pytest_version=8.3.5
current_v25_a1611_bounded_release_created=false
current_v25_a1611_bounded_nonce_created=false
current_v25_a1611_bounded_k8_executed=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46856781824
current_v25_phase=A1_6_11_R3_interpreter_qualification_and_static_four_root_review_passed_k8_closed
next_work_target=ultra_read_only_A1_6_11_R3_final_release_decision_before_bounded_execute

## A1.6.11-R3 bounded-only release and fail-closed execution result (2026-07-19 CST)

Ultra released one and only one bounded-execute nonce against implementation
source `0a07183913844dd9ab0c1e7c619c42be81c579ab`, pointer
`09ca988b4db6e27c74bfa2331f3e6d4247a51252`, fixed DP
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, and the R3 four-root package.
The exact release artifact is
`/root/autodl-tmp/camp_dp_v25_ultra_a1611r3_bounded_execute_release_036bee497270ef5c`,
root `1b9e8b7d6587c816359c97a821324c6e411ab9d5b5e79064a824240ef990965e`.
Strict reopening before consumption verified schema
`camp_dp_v25_ultra_a1610_bounded_execute_release_v8`, gate
`a1610_bounded_execute`, status `bounded_execute_released`, CUDA, seed 25001,
243 unique identities, 244 ordered runs, 15,616 prospective ticks, four-root
binding SHA `163c4fd7c67d924a27c7cf9b47ec986e915d3db1fe0f54ff10a7077fe344b5eb`,
and critical implementation manifest SHA
`86a6c60c14d69047baad9e598e35f26bcdb4839003417d8eb96bd5c798a6717d`.
All nonbounded gates and Fresh/outcome fields were false/empty.

The consumer atomically consumed nonce
`036bee497270ef5c9899ed60c4b6f48d8cd8341cf505482ceb2b036263967bf0`;
the immutable marker SHA is
`49f8558e444114d5ba65db3c22f0afb745090b8d44169ec586a9f7360726a1f5`.
Execution then failed closed during the first run before it could accept an
authoritative projected result. The exact error was
`ValueError: bounded scene materialization digest drifted before projection`.
The failure artifact is
`/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_036bee497270ef5c`,
root `872982b9de4404ae1340235b9117dbcee2ef811563a89c699506972413e774fb`.
It has `run.exit=1`, schema `camp_dp_v25_a163_bounded_failure_v1`, status
`failed_closed_bounded_execution`, canonical `failure.json`, a sealed causal
scene materialization, route inputs, and empty `results.jsonl`,
`run_evidence.jsonl`, and `snapshot_index.jsonl`; therefore the accepted
denominator is zero runs and zero ticks. K8-capable execution started, but no
K8 result is accepted as scientific evidence.

The independent post-run review directory was never created because execution
did not complete. The nonce is consumed permanently; no retry, alternative
nonce/directory, suffix splice, correction, full-config/full-R/1500x64,
monitor, training, calibration, Scene/V2I, Fresh, or outcome access followed.
After failure, worker/GPU counts were zero, the shared lock was free, fixed DP
and CAMP remained at their released heads, and free space was 46,844,665,856
bytes. The only next action is Ultra read-only review of this sealed failure
and a new upper-level decision; XHigh is not authorized to diagnose or fix it.

current_v25_status=v25_a1611_r3_bounded_execution_failed_closed_ultra_result_review_required
current_v25_source_head=0a07183913844dd9ab0c1e7c619c42be81c579ab
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_036bee497270ef5c
current_v25_artifact_root_sha256=872982b9de4404ae1340235b9117dbcee2ef811563a89c699506972413e774fb
current_v25_review_artifact=none_execution_failed_before_independent_review
current_v25_review_artifact_root_sha256=none
current_v25_a1611_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_0a071839_20260719T001726CST
current_v25_a1611_bounded_plan_artifact_root_sha256=27bc6cd53da17535ab573016102d26d6d21d26b951bb16739d56bc5c8720b7b8
current_v25_a1611_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_bounded_execution_plan_review_0a071839_20260719T001726CST
current_v25_a1611_bounded_plan_review_artifact_root_sha256=44453e0ad2220b29bbd9bb473d41f927429a6ed899cecb6c1e990f8c8bcf96f4
current_v25_r0_authority_source_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_census_0a071839_20260719T001726CST
current_v25_r0_authority_source_artifact_root_sha256=944f07399616f8870385827204ac2dcfef29637828e0a40112cb266a908aa3aa
current_v25_r0_authority_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a1611r3_route_signal_source_review_0a071839_20260719T001726CST
current_v25_r0_authority_source_review_artifact_root_sha256=4bef57a9bcea8b911cbbf3880f2c29d575b5fc1c9696e222a587eae675c1a989
current_v25_a16_formal_train_identity_count=1653
current_v25_a16_executable_identity_count=1500
current_v25_a16_retained_identity_count=153
current_v25_a16_mapped_signal_identity_count=146
current_v25_a16_no_signal_identity_count=1354
current_v25_a16_controlled_same_tick_override_count=21
current_v25_a16_observe_same_tick_request_count=125
current_v25_a16_source_failure_count=0
current_v25_a162_unique_identity_count=243
current_v25_a162_run_count=244
current_v25_a162_snapshot_capacity=15616
current_v25_a162_identity0_repeat_positions=0,243
current_v25_a169_four_roots_machine_authority_eligible=false
current_v25_a1611_release_schema=camp_dp_v25_ultra_a1610_bounded_execute_release_v8
current_v25_a1611_device=cuda
current_v25_a1611_four_root_bindings_sha256=163c4fd7c67d924a27c7cf9b47ec986e915d3db1fe0f54ff10a7077fe344b5eb
current_v25_a1611_four_roots_machine_authority_eligible=true_for_consumed_release_only
current_v25_a1611_local_targeted_test_result=238_passed_5_skipped
current_v25_a1611_autodl_targeted_test_result=243_passed
current_v25_a1611_r2_status=fail_closed_stopped_before_test_execution
current_v25_a1611_r2_nonce_status=permanently_revoked_unconsumed
current_v25_a1611_r3_interpreter=/root/autodl-tmp/dp312_venv/bin/python
current_v25_a1611_r3_interpreter_realpath=/root/miniconda3/bin/python3.12
current_v25_a1611_r3_python_version=3.12.3
current_v25_a1611_r3_pytest_version=8.3.5
current_v25_a1611_bounded_release_created=true
current_v25_a1611_bounded_release_artifact=/root/autodl-tmp/camp_dp_v25_ultra_a1611r3_bounded_execute_release_036bee497270ef5c
current_v25_a1611_bounded_release_artifact_root_sha256=1b9e8b7d6587c816359c97a821324c6e411ab9d5b5e79064a824240ef990965e
current_v25_a1611_bounded_nonce_created=true_consumed_once
current_v25_a1611_bounded_nonce_marker_sha256=49f8558e444114d5ba65db3c22f0afb745090b8d44169ec586a9f7360726a1f5
current_v25_a1611_bounded_k8_executed=started_not_accepted
current_v25_a1611_bounded_execution_completed=false
current_v25_a1611_bounded_execution_run_exit=1
current_v25_a1611_bounded_execution_failure_type=ValueError
current_v25_a1611_bounded_execution_failure_reason=bounded_scene_materialization_digest_drifted_before_projection
current_v25_a1611_bounded_execution_accepted_run_count=0
current_v25_a1611_bounded_execution_accepted_tick_count=0
current_v25_a1611_bounded_independent_review_started=false
current_v25_corrected_full_corpus_started=false
current_v25_full_config_preflight_release_created=true_diagnostic_consumed
current_v25_full_config_preflight_started=true_failed_closed_before_receipts
current_v25_full_r_authorized=false
current_v25_monitor_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=46844665856
current_v25_phase=A1_6_11_R3_bounded_execution_failed_closed_after_nonce_consumption_before_independent_review
next_work_target=ultra_read_only_A1_6_11_R3_failed_bounded_execution_result_review_and_decision

## A1.7 exact failing-run candidate preimage localization (2026-07-19 CST)

A1.7 first added a diagnostic-only K8 boundary sink. It copies the exact
`float32[8,80,4]` fixed-DP candidate tensor and same-forward candidate0/row
hashes after candidate construction but before atom materialization. The
normal bounded path does not enable the sink. Diagnostic authority now binds
one native-integer run ordinal to the exact sealed plan; the default remains
ordinal zero, while this investigation bound ordinal 155. The change does not
modify fixed DP, K8 generation, trajectories, atom formulas, scales, weights,
normalization, simplex/affine scoring, eligibility, or tie-breaking.

Local py_compile and full affected regression passed 191 tests with five
platform skips. Commit `fb2eb97c2abadaf91c1cc6d8e27dac4970499f35` was pushed
normally to GitHub and synchronized AutoDL ff-only; AutoDL py_compile and the
same full affected regression passed 196 tests. The fixed DP remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Because the critical implementation manifest changed, all four static roots
were regenerated at that HEAD and independently reopened:

- source census `/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_census_fb2eb97c_20260719T133516CST`, root `3b5f41117a2de6a7e0b8ae5b95690abb4b253b7a383d090dd4d7a825d5096b3b`;
- source review `/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_review_fb2eb97c_20260719T133516CST`, root `4f5cd4a7475a980d24f93362da7d455e2f2ad8f05de0f7d3abcbe47e45da29ad`;
- bounded plan `/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_fb2eb97c_20260719T133516CST`, root `5abfe89d0831ceaa8eb7b9d44cbec940965033cf6d60260916078aa4d6db8845`;
- bounded plan review `/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_fb2eb97c_20260719T133516CST`, root `dcbd677b1e48d9bec22735b1962b8cbe147d6d2d84904ab888727aa245681ce8`.

Counts remained 1,653 formal train identities, 1,500 executable, 153 retained,
146 mapped signal, 1,354 no signal, 21 controlled override, 125 observe mode,
zero source failures, 243 unique bounded identities, 244 ordered runs, and
15,616 prospective ticks.

The prior corrected bounded attempt remains immutable and ineligible at
`/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_dfb06e5e_4440c5cd6843f7ca`,
root `0c36e621aef55446422f938d67fa9ab40b174cc50be19297c4c9a3f4a69f4bc1`.
It accepted 155 complete runs and 9,920 ticks, then failed closed on run ordinal
155 with `candidate headings must be valid cos/sin vectors`. No independent
review ran and no suffix/retry was attempted.

The exact-run diagnostic release is
`/root/autodl-tmp/camp_dp_v25_a17_run155_diagnostic_release_fb2eb97c_0094bfb8a41b86ec`,
root `74ccc44b56551dc09f25132c1cc5d743ded66aa9679094e0da5dead9193f4b94`.
Its one-shot nonce was consumed once. The diagnostic execution sealed
fail-closed at
`/root/autodl-tmp/camp_dp_v25_a17_run155_diagnostic_execution_fb2eb97c_0094bfb8a41b86ec`,
root `2a519f1deacd6d3917b1f1945141ee378368fc8a34585f4eb6ad157ccc108672`,
with 33 candidate records for ticks zero through 32 and no accepted scientific
result.

The saved tick-32 tensor SHA is
`32cb0d033f20d0f51087b81ecaae297220c89757db31bc2456d555449ae9360d`.
Candidate 5 has six vectors below the frozen norm floor at steps 10 through 15;
the minimum norm is 0.06830171230455423. The candidate rows themselves are
finite and content-addressed. Earlier ticks have no sub-0.5 heading vectors.
This reproduces the failure from the raw fixed-DP K8 output and rules out the
earlier digest/tick-pairing/evidence-order hypotheses.

The frozen contract requires every candidate heading to satisfy the invariant
and makes any such violation fail the run. Normalizing/repairing the trajectory,
masking candidate 5, or relaxing the 0.5 floor would change the scientific
contract and is not authorized. Therefore 244-run bounded execution, the
1,500x64 corpus, training, calibration, Scene/V2I, Fresh, and outcome work are
stopped pending Ultra direction. Worker/GPU counts are zero, the shared lock is
free, disk remains above the 10 GiB floor, and Fresh/outcome is unopened.

current_v25_status=v25_a17_fixed_dp_heading_invariant_confirmed_scientific_contract_decision_required
current_v25_source_head=fb2eb97c2abadaf91c1cc6d8e27dac4970499f35
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a17_run155_diagnostic_execution_fb2eb97c_0094bfb8a41b86ec
current_v25_artifact_root_sha256=2a519f1deacd6d3917b1f1945141ee378368fc8a34585f4eb6ad157ccc108672
current_v25_review_artifact=none_diagnostic_failed_closed_before_scientific_acceptance
current_v25_review_artifact_root_sha256=none
current_v25_a17_diagnostic_release_artifact=/root/autodl-tmp/camp_dp_v25_a17_run155_diagnostic_release_fb2eb97c_0094bfb8a41b86ec
current_v25_a17_diagnostic_release_root_sha256=74ccc44b56551dc09f25132c1cc5d743ded66aa9679094e0da5dead9193f4b94
current_v25_a17_source_artifact=/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_census_fb2eb97c_20260719T133516CST
current_v25_a17_source_root_sha256=3b5f41117a2de6a7e0b8ae5b95690abb4b253b7a383d090dd4d7a825d5096b3b
current_v25_a17_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_review_fb2eb97c_20260719T133516CST
current_v25_a17_source_review_root_sha256=4f5cd4a7475a980d24f93362da7d455e2f2ad8f05de0f7d3abcbe47e45da29ad
current_v25_a17_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_fb2eb97c_20260719T133516CST
current_v25_a17_bounded_plan_root_sha256=5abfe89d0831ceaa8eb7b9d44cbec940965033cf6d60260916078aa4d6db8845
current_v25_a17_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_fb2eb97c_20260719T133516CST
current_v25_a17_bounded_plan_review_root_sha256=dcbd677b1e48d9bec22735b1962b8cbe147d6d2d84904ab888727aa245681ce8
current_v25_a17_failed_bounded_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_dfb06e5e_4440c5cd6843f7ca
current_v25_a17_failed_bounded_root_sha256=0c36e621aef55446422f938d67fa9ab40b174cc50be19297c4c9a3f4a69f4bc1
current_v25_a17_failed_bounded_accepted_run_count=155
current_v25_a17_failed_bounded_accepted_tick_count=9920
current_v25_a17_diagnostic_run_ordinal=155
current_v25_a17_diagnostic_failure_tick=32
current_v25_a17_diagnostic_failure_candidate=5
current_v25_a17_diagnostic_failure_steps=10,11,12,13,14,15
current_v25_a17_diagnostic_min_heading_norm=0.06830171230455423
current_v25_a17_diagnostic_candidate_tensor_sha256=32cb0d033f20d0f51087b81ecaae297220c89757db31bc2456d555449ae9360d
current_v25_a17_diagnostic_training_eligible=false
current_v25_corrected_full_corpus_started=false
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=33869266944
current_v25_phase=A1_7_preprojection_evidence_localization_confirmed_fixed_dp_candidate_heading_invariant_block
next_work_target=ultra_read_only_A1_7_fixed_dp_heading_invariant_scientific_contract_decision

## A1.7 typed fixed-DP candidate-generation capability contract (2026-07-19 CST)

Ultra accepted the run155 evidence as a real unchanged fixed-DP same-forward
K8 support limitation and selected the prospective, outcome-blind typed
capability-failure policy. Implementation source HEAD
`87c3dc9e1851a0458dbb27bbd3e7565110fe533f` preserves the exact finite
`float32[8,80,4]` tensor and `[0.5,1.5]` heading-norm invariant. It does not
normalize or repair trajectories, mask a candidate, reduce K, fall back to
candidate0, modify fixed DP/checkpoint/args/request semantics, or change atoms,
clip, scales, weights, simplex/affine scoring, eligibility, or tie-breaking.

The canonical K8 validator now raises only the exact typed class
`fixed_dp_candidate_generation_capability_failure` with reason
`invalid_k8_heading_norm_envelope` after same-forward K8 generation and before
atom materialization, scoring, or selection. The runner catches only that
class. It drops every partial trainable row from the identity, writes zero
snapshot/context/index/label/scale rows, and persists a content-addressed raw
K8 preimage plus a diagnostic-only receipt binding scenario/route, family,
tier, source mode, fixed-DP HEAD, tick, sorted invalid indices, min/max norm,
the frozen envelope, raw tensor SHA, and same-forward candidate0 identity.
Every other exception remains artifact-fatal.

The bounded and full-corpus terminal contracts now retain this class separately
from preregistered scenario-source capability failures. Bounded acceptance
requires all 244 terminal rows, complete and eight-way equivalent identity0
first/final runs, at least 231 of 243 unique identities complete, greater than
90% completion by family and source/mode, greater than 80% by family×tier, and
the frozen red 4/7/4 tier plus three-map minimum. Full-corpus acceptance keeps
all 1,500 terminal rows and 153 formal source-ineligible ledger rows, requires
at least 1,425 complete identities, the same grouped thresholds, no planned
zero-complete stratum, and unchanged red minima. Typed fixed-DP failures remain
excluded from every train-only scale, label, context scaler, Static/Scene model,
and ablation input.

Local py_compile plus the affected regression passed 234 tests with six
platform skips. Commit `87c3dc9e...` was pushed normally to GitHub and AutoDL
was fast-forwarded from GitHub. AutoDL py_compile and the same scope passed all
240 tests. CAMP local/origin/GitHub/AutoDL were then aligned at the source HEAD;
fixed DP remained clean at `7a1d33da...`, worker/GPU counts were zero, the
shared lock was free, disk stayed above 10 GiB, and Fresh/outcome remained
unopened.

The critical-manifest change invalidated the prior four roots for future
execution authority. A single fresh static chain was regenerated at the source
HEAD:

- source census `/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_census_87c3dc9e_20260719T142523CST`, root `ead219b2575d4b8f7e40fbba93735a363bd124595497cfd96bc707361d0b0544`;
- source review `/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_review_87c3dc9e_20260719T142523CST`, root `09b5661538528c3ca83cdfb40f90f228affac5e33f5eabe15e7080b6874954f8`;
- bounded plan `/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_87c3dc9e_20260719T142523CST`, root `ff633a969bdf032da543f70aa0b0b17ae3174a1a17160b4095e511715c28fae9`;
- bounded plan review `/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_87c3dc9e_20260719T142523CST`, root `64867da260ad8b32e26db2999efe58d08d992381b4873a3c8eb893fe27750347`.

The source-only producer completed successfully; the surrounding shell then
stopped while parsing its deliberately noisy multi-line stdout. The sealed
source root was not repeated. The independent source review and both plan roots
subsequently completed once. Counts remain 1,653/1,500/153, 146/1,354,
21/125, zero source failures, 243 unique identities, 244 ordered runs, and
15,616 prospective ticks. No K8, training, calibration, Scene/V2I, Fresh, or
outcome was opened while constructing these roots.

current_v25_status=v25_a17_fixed_dp_heading_capability_contract_static_authority_passed_bounded_execution_next
current_v25_source_head=87c3dc9e1851a0458dbb27bbd3e7565110fe533f
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_87c3dc9e_20260719T142523CST
current_v25_artifact_root_sha256=ff633a969bdf032da543f70aa0b0b17ae3174a1a17160b4095e511715c28fae9
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_87c3dc9e_20260719T142523CST
current_v25_review_artifact_root_sha256=64867da260ad8b32e26db2999efe58d08d992381b4873a3c8eb893fe27750347
current_v25_a17_source_artifact=/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_census_87c3dc9e_20260719T142523CST
current_v25_a17_source_root_sha256=ead219b2575d4b8f7e40fbba93735a363bd124595497cfd96bc707361d0b0544
current_v25_a17_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_review_87c3dc9e_20260719T142523CST
current_v25_a17_source_review_root_sha256=09b5661538528c3ca83cdfb40f90f228affac5e33f5eabe15e7080b6874954f8
current_v25_a17_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_87c3dc9e_20260719T142523CST
current_v25_a17_bounded_plan_root_sha256=ff633a969bdf032da543f70aa0b0b17ae3174a1a17160b4095e511715c28fae9
current_v25_a17_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_87c3dc9e_20260719T142523CST
current_v25_a17_bounded_plan_review_root_sha256=64867da260ad8b32e26db2999efe58d08d992381b4873a3c8eb893fe27750347
current_v25_a17_failed_bounded_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_dfb06e5e_4440c5cd6843f7ca
current_v25_a17_failed_bounded_root_sha256=0c36e621aef55446422f938d67fa9ab40b174cc50be19297c4c9a3f4a69f4bc1
current_v25_a17_failed_bounded_accepted_run_count=155
current_v25_a17_failed_bounded_accepted_tick_count=9920
current_v25_a17_diagnostic_run_ordinal=155
current_v25_a17_diagnostic_failure_tick=32
current_v25_a17_diagnostic_failure_candidate=5
current_v25_a17_diagnostic_failure_steps=10,11,12,13,14,15
current_v25_a17_diagnostic_min_heading_norm=0.06830171230455423
current_v25_a17_diagnostic_candidate_tensor_sha256=32cb0d033f20d0f51087b81ecaae297220c89757db31bc2456d555449ae9360d
current_v25_a17_diagnostic_training_eligible=false
current_v25_fixed_dp_capability_failure_class=fixed_dp_candidate_generation_capability_failure
current_v25_fixed_dp_capability_failure_reason=invalid_k8_heading_norm_envelope
current_v25_bounded_execution_plan_schema=camp_dp_v25_a17_route_level_bounded_execution_plan_v3
current_v25_bounded_min_complete_unique_identity_count=231
current_v25_full_corpus_min_complete_identity_count=1425
current_v25_local_focused_test_result=234_passed_6_skipped
current_v25_autodl_focused_test_result=240_passed
current_v25_corrected_full_corpus_started=false
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=33868288000
current_v25_phase=A1_7_fixed_dp_candidate_generation_capability_contract_static_authority_passed
next_work_target=A1_7_new_244x64_sequential_fixed_k8_bounded_execution_and_independent_review

## A1.7 bounded terminal evidence-wiring correction and static authority rebuild (2026-07-19 CST)

The first execution under the typed fixed-DP capability contract completed all
244 prospective runs and sealed fail-closed at
`/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_87c3dc9e_8fdd1d562d63d00d`,
root `f78e79939579339a629c5035c83c19aaea4ec7ce6fb8346384521f298c4cdd14`.
It produced 242 complete runs and retained two exact typed
`fixed_dp_candidate_generation_capability_failure` identities, each with zero
training snapshots; complete runs produced 15,488 snapshots. The second typed
failure was run 212/tick 37 and remained inside the same prospective,
outcome-blind support-ceiling contract as run 155.

Terminal acceptance rejected the artifact because `build_run_evidence` called
the already strict native failure-class derivation without the route, config,
native-directory, and scene-materialization hash context. Results correctly
recorded the 242 complete rows as `none`, while evidence rows recorded
`native_evidence_schema_invalid`. This was an ordinary evidence-wiring failure;
the artifact remains immutable and training/calibration/evaluation-ineligible.
A read-only in-memory correction passed 244/244 terminal accounting, 241/243
unique completion, all eight identity0 repeat checks, every family/source-mode
and family×tier coverage threshold, the red 6/10/5 tier counts over four maps,
and zero mapped runtime-source failures. That projection diagnoses the defect
but is not artifact authority.

Commit `11023da56125d1c660fb70ab659aab5aa843762f` passes the exact context
into evidence derivation and adds a regression for the complete-row path. Local
focused tests passed 179 with five platform skips; AutoDL passed all 184 tests.
CAMP local/origin/GitHub/AutoDL were aligned at the source HEAD before the
static rebuild, fixed DP stayed clean at `7a1d33da...`, GPU/worker counts were
zero, the lock was free, Fresh/outcome remained unopened, and free disk was
29,114,728,448 bytes after sealing the four roots.

The critical-manifest change invalidated the prior four roots for new execution
authority. A single new static chain was built from identity0 at the source
HEAD:

- source census `/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_census_11023da5_20260719T185301CST`, root `52efa827fc6bb6e5c0646ac775f83db0856a69fc635076c05d27a63a460b0848`;
- source review `/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_review_11023da5_20260719T185301CST`, root `5eb497f0b9372ace305ea03c2b720629613e766c906efb07fd7abffa39665b8c`;
- bounded plan `/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_11023da5_20260719T185301CST`, root `c15d3e71ecfb108ec7103b857ec5a20c9ba813437eaf8dc89b710570ee488e04`;
- bounded plan review `/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_11023da5_20260719T185301CST`, root `fd6e596a527bf62dfba8a8ce011c8f121d0bc917859fcbab566f547a69ddbb98`.

The chain preserves 1,653/1,500/153 identities, 146 mapped/1,354 no-signal,
21 controlled override/125 observe, zero source failures, and the unchanged
243-identity/244-run/15,616-tick sequential-K8 plan. No new K8, full corpus,
training, calibration, Scene/V2I, Fresh, or outcome was opened while rebuilding
the chain. The next action is a new bounded execution from identity0 with a new
nonce and fresh artifact paths; no failed artifact is reused or appended.

current_v25_status=v25_a17_bounded_terminal_evidence_wiring_corrected_static_authority_passed_bounded_rerun_next
current_v25_source_head=11023da56125d1c660fb70ab659aab5aa843762f
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_11023da5_20260719T185301CST
current_v25_artifact_root_sha256=c15d3e71ecfb108ec7103b857ec5a20c9ba813437eaf8dc89b710570ee488e04
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_11023da5_20260719T185301CST
current_v25_review_artifact_root_sha256=fd6e596a527bf62dfba8a8ce011c8f121d0bc917859fcbab566f547a69ddbb98
current_v25_a17_source_artifact=/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_census_11023da5_20260719T185301CST
current_v25_a17_source_root_sha256=52efa827fc6bb6e5c0646ac775f83db0856a69fc635076c05d27a63a460b0848
current_v25_a17_source_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_route_signal_source_review_11023da5_20260719T185301CST
current_v25_a17_source_review_root_sha256=5eb497f0b9372ace305ea03c2b720629613e766c906efb07fd7abffa39665b8c
current_v25_a17_bounded_plan_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_11023da5_20260719T185301CST
current_v25_a17_bounded_plan_root_sha256=c15d3e71ecfb108ec7103b857ec5a20c9ba813437eaf8dc89b710570ee488e04
current_v25_a17_bounded_plan_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_plan_review_11023da5_20260719T185301CST
current_v25_a17_bounded_plan_review_root_sha256=fd6e596a527bf62dfba8a8ce011c8f121d0bc917859fcbab566f547a69ddbb98
current_v25_a17_heading_diagnostic_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_dfb06e5e_4440c5cd6843f7ca
current_v25_a17_heading_diagnostic_root_sha256=0c36e621aef55446422f938d67fa9ab40b174cc50be19297c4c9a3f4a69f4bc1
current_v25_a17_failed_bounded_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_87c3dc9e_8fdd1d562d63d00d
current_v25_a17_failed_bounded_root_sha256=f78e79939579339a629c5035c83c19aaea4ec7ce6fb8346384521f298c4cdd14
current_v25_a17_failed_bounded_complete_run_count=242
current_v25_a17_failed_bounded_retained_fixed_dp_capability_failure_count=2
current_v25_a17_failed_bounded_snapshot_count=15488
current_v25_a17_failed_bounded_training_eligible=false
current_v25_a17_failed_bounded_failure_reason=bounded_run_evidence_schema_content_drifted
current_v25_a17_failed_bounded_coverage_projection=passed_read_only_not_artifact_authority
current_v25_a17_diagnostic_run_ordinal=155
current_v25_a17_diagnostic_failure_tick=32
current_v25_a17_diagnostic_failure_candidate=5
current_v25_a17_diagnostic_failure_steps=10,11,12,13,14,15
current_v25_a17_diagnostic_min_heading_norm=0.06830171230455423
current_v25_a17_diagnostic_candidate_tensor_sha256=32cb0d033f20d0f51087b81ecaae297220c89757db31bc2456d555449ae9360d
current_v25_a17_diagnostic_training_eligible=false
current_v25_fixed_dp_capability_failure_class=fixed_dp_candidate_generation_capability_failure
current_v25_fixed_dp_capability_failure_reason=invalid_k8_heading_norm_envelope
current_v25_bounded_execution_plan_schema=camp_dp_v25_a17_route_level_bounded_execution_plan_v3
current_v25_bounded_min_complete_unique_identity_count=231
current_v25_full_corpus_min_complete_identity_count=1425
current_v25_local_focused_test_result=179_passed_5_skipped
current_v25_autodl_focused_test_result=184_passed
current_v25_corrected_full_corpus_started=false
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=29114728448
current_v25_phase=A1_7_bounded_terminal_evidence_wiring_corrected_static_authority_passed
next_work_target=A1_7_new_244x64_sequential_fixed_k8_bounded_rerun_and_independent_review

## A1.7 corrected bounded execution and independent review PASS

The fresh sequential fixed-K8 bounded artifact completed all 244 ordered runs
and sealed with `run.exit=0`. It retained the two prospective typed
`fixed_dp_candidate_generation_capability_failure` identities, emitted zero
training rows for those identities, and preserved 15,488 complete snapshots
for 241 of 243 unique identities. All preregistered support ceilings passed:
overall unique completion was above 95%, every family and source mode was above
90%, every family-by-tier cell was above 80%, red coverage was 6/10/5 across
easy/borderline/high-risk with four distinct source maps, and identity0's first
and final runs matched on all eight frozen repeat checks.

The first post-run review invocation correctly failed closed because the
archived-release validator required a nonempty review-only code delta even
when release source, pointer, and review HEAD were identical. That failed
review remains sealed at root `bdba1e24...`. Commit `3feee605...` makes the
minimal harness correction: an empty delta is valid, while every changed path
must still lie in the two-file reviewer/test allowlist. AutoDL then passed all
188 focused post-run-review tests. A fresh independent review reopened 80,863
execution file policies, the release and four upstream roots, all route-level
signal receipts, K8/candidate0/atom/context/selection/trajectory evidence, both
typed failures, coverage, and the identity0 repeat. It passed with
`run.exit=0` and root `44001045...`.

No Fresh/outcome, training, calibration, Scene runtime, V2I, full-config, or
full corpus was opened. The bounded artifact and review are training-input
authority only after the forthcoming full-corpus denominator independently
passes. A read-only storage census found `/autodl-pub` has more than 11 TB free,
so the full corpus will use a fresh canonical path on that filesystem and keep
the 10 GiB floor without deleting or compressing prior evidence.

current_v25_status=v25_a17_bounded_execution_and_independent_review_passed_full_corpus_authority_next
current_v25_source_head=3feee6059ec28393bbbd530ff359485fb75c1ede
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_c7b1cdba_605f8d227d0e83cb
current_v25_artifact_root_sha256=8ee2c25ab993ad23e5c3d29ecf1940c296f4cead9a4c839be7723959f4e66f3f
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_bounded_execution_review_3feee605_20260720T173132CST
current_v25_review_artifact_root_sha256=4400104508f898b5ef0ad877036bb9f14bd0a0b0012d7ab2b57a4cfe4728fe7b
current_v25_a17_bounded_release_root_sha256=2d1b82bca3f9d32aaf9069fbc6b017c5cc01ff8aa16e3fcb048b50af1cc97df9
current_v25_a17_failed_same_head_review_root_sha256=bdba1e2448925b2417a26b4e6c5594d63635c7fe8a4b68507e6b28cb0ad86023
current_v25_a17_bounded_run_count=244
current_v25_a17_bounded_unique_identity_count=243
current_v25_a17_bounded_complete_unique_identity_count=241
current_v25_a17_bounded_snapshot_count=15488
current_v25_a17_bounded_retained_fixed_dp_capability_failure_count=2
current_v25_a17_bounded_identity0_repeat_deterministic=true
current_v25_a17_bounded_coverage_passed=true
current_v25_autodl_focused_test_result=188_passed
current_v25_corrected_full_corpus_started=false
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=25322827776
current_v25_full_corpus_storage_root=/autodl-pub
current_v25_full_corpus_storage_free_bytes=11021925453824
current_v25_phase=A1_7_bounded_execution_and_independent_review_passed
next_work_target=A1_7_full_1500x64_corrected_corpus_authority_preflight_execute_and_independent_review

## A1.7 one-time failure-regression control matrix and production-entry hold

The resource cleanup is complete and no full-corpus worker is active. The
canonical writable corpus parent is `/root/autodl-tmp`: `findmnt` reports the
project XFS mount as `rw,prjquota`, whereas `/autodl-pub` and
`/autodl-pub/data` are read-only despite reporting TB-scale parent/AutoFS
capacity. Removing only confirmed-unused artifacts raised writable free space
from 37,128,237,056 to 41,851,711,488 bytes; the bounded linear peak estimate
is 27,909,527,113 bytes, leaving 13,942,184,375 bytes, above the 10 GiB floor.
The local complete and interrupted tar payloads were deleted after their exact
paths and roots were recorded, releasing 23,275,442,176 bytes on `F:`; small
verification/deletion receipts remain.

The first `/root/autodl-tmp` execute attempt after cleanup sealed fail-closed at
root `ba79db8dd0ae87c9b4614aca09ef75077f316a40bbbc15cc614626d624bdafab`
with zero accepted runs/snapshots. It exposed a single ordinary harness defect:
the execute path reconstructed the historical controlled-train preflight nonce
path instead of consuming the exact sealed A1.7 preflight marker binding.
Commit `19bcebe67f1026f8087505190d11d159d7aa2f1a` fixes only that binding and
adds the direct regression. AutoDL passed the focused test and all four A1.7
full-corpus authority tests. A fresh real-entry full-config preflight and its
independent review then passed with roots `e578642e...` and `96bd1626...`;
they executed zero model/candidate/snapshot work. No full-corpus execute nonce
has been generated after this control hold.

| Failure signature | Current forbidden behavior | Unique machine check | Regression test or command |
|---|---|---|---|
| `stale_heartbeat_exited_worker` | Keep or create a monitor before a live worker has valid progress | app automation inventory must report the obsolete monitor absent; creation requires live PID, held lock, first valid `progress.json`, and GPU/model-loaded evidence | `automation_update(view/delete)` plus worker-start receipt check |
| `readonly_parent_misread_as_capacity` | Select a parent from `df` capacity without proving the exact target mount writable | `findmnt -T <literal-parent>` + `df -B1` + exact create/fsync/remove probe on the resolved parent | A1.7 production-entry storage batch |
| `logical_vs_allocated_or_hardlink_confusion` | Treat `du -sb`, projected logical bytes, or hard-linked content as actual freed blocks | record both `du -sb` and `du -sB1`, then re-read writable-volume free bytes after exact deletion | `20260721_v25_confirmed_unused_deletion_receipt.json` |
| `external_legacy_json_forced_canonical` | Apply CAMP compact/sorted/single-LF policy to frozen external JSON | exact path+SHA selects the strict legacy loader; CAMP-authored authority still uses canonical loader | `test_diffusion_planner_v25_a163_bounded_authority.py` legacy-asset cases |
| `operator_short_sha_or_interpreter_realpath_assertion` | Compare 8-char with 40-char HEAD or require venv launcher realpath/prefix equality | exact 40-hex HEAD equality; record interpreter metadata but require only Python 3.12 and frozen imports | production-entry interpreter/HEAD batch |
| `formal_nonce_consumed_before_real_entry_pass` | Generate/consume an execute nonce before the real create/run zero-data entry passes | no execute marker exists before/after production-entry preflight; nonce is generated only afterward | real `create_diffusion_planner_v25_a17_full_corpus_release.py` + real corpus `--preflight` |
| `docs_pointer_vs_live_implementation_drift` | Treat a docs-only pointer HEAD as implementation source or skip the dual-HEAD allowlist | exact implementation manifest at source HEAD plus only current-status/audit/pointer-test delta to pointer HEAD | `test_diffusion_planner_v25_iteration_audit.py` pointer tests |
| `scenario_family_drives_signal_source` | Infer signal applicability/phase from scenario family | route-level regulatory chain plus same-tick `controlled_same_tick_override` or `observe_same_tick_request` receipt | A1.6 source census/review and full-config review |
| `confirmed_unused_artifact_archived_locally` | Tar confirmed-unused failed/superseded artifacts by default | authority non-membership + exact deletion receipt; retain only small receipts | exact-path deletion receipt validation |
| `unchanged_status_visible_polling` | Emit repeated unchanged status or run concurrent/high-frequency polling | one low-frequency read-only monitor only after worker admission; user-visible output only on milestone/error/material progress | heartbeat admission policy in Current V25 status |

This is one control package, not a new scientific gate or A1.7 sub-version.
The next action is the single same-implementation production-entry preflight;
until it passes, worker, execute nonce, monitor, training, calibration, Scene,
V2I, Fresh, and outcome access remain closed.

current_v25_status=v25_a17_failure_regression_matrix_frozen_production_entry_preflight_pending
current_v25_source_head=19bcebe67f1026f8087505190d11d159d7aa2f1a
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a17_full_config_preflight_19bcebe6_b2de06d662cf9764
current_v25_artifact_root_sha256=e578642e9478f9021fdcbfb3b683a37db9ff3cf4ac9323bb98d801644181a5cb
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_full_config_preflight_review_19bcebe6_b2de06d662cf9764
current_v25_review_artifact_root_sha256=96bd1626eba2be1143eb4ad439ad7b38de90d56d9bbafee76e63d0402f53386e
current_v25_full_config_preflight_release_root_sha256=323a7326c744d54b410f6b0ace7e1ac648e4c60045569bab77640942398a2687
current_v25_failed_execute_root_sha256=ba79db8dd0ae87c9b4614aca09ef75077f316a40bbbc15cc614626d624bdafab
current_v25_failure_regression_matrix_row_count=10
current_v25_production_entry_preflight_passed=false
current_v25_official_execute_nonce_generated=false
current_v25_corrected_full_corpus_started=false
current_v25_monitor_started=false
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=41851711488
current_v25_full_corpus_storage_root=/root/autodl-tmp
current_v25_projected_full_corpus_peak_bytes=27909527113
current_v25_projected_post_corpus_free_bytes=13942184375
current_v25_phase=A1_7_failure_regression_control_before_full_corpus_execute
next_work_target=A1_7_same_implementation_production_entry_preflight_before_execute_nonce

## A1.7 production-entry preflight PASS

The single consolidated production-entry preflight passed on the unchanged
implementation source `19bcebe67f1026f8087505190d11d159d7aa2f1a`. It used
`/root/autodl-tmp/dp312_venv/bin/python` (Python 3.12.3) and imported the
frozen pytest/numpy/torch/scipy scope; verified fixed DP `7a1d33da...`; proved
the exact `/root/autodl-tmp` mount is XFS `rw,prjquota`; performed an exact
create/fsync/read/delete probe below that literal/resolved parent; opened the
real frozen probe, weights, checkpoint, arguments, native sources, sealed
create-entry release, zero-snapshot run-entry preflight, and independent
review; and passed all three pointer/matrix regressions plus the focused marker
binding and four full-corpus authority tests. The real create/run artifacts
remain roots `323a7326...`, `e578642e...`, and `96bd1626...`.

No full-corpus execute release exists for source `19bcebe6...`; therefore no
official execute nonce has been generated or consumed. Worker/GPU counts are
zero, the corpus lock is free, the obsolete monitor count is zero, and
Fresh/outcome remains unopened. Writable free space is 41,835,847,680 bytes;
after the 27,909,527,113-byte bounded projection, the remaining estimate is
13,926,320,567 bytes, above 10 GiB. Per the user's stop point, this record does
not create the execute release or start the full corpus.

current_v25_status=v25_a17_failure_regression_matrix_and_production_entry_preflight_passed_execute_nonce_not_generated
current_v25_source_head=19bcebe67f1026f8087505190d11d159d7aa2f1a
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a17_full_config_preflight_19bcebe6_b2de06d662cf9764
current_v25_artifact_root_sha256=e578642e9478f9021fdcbfb3b683a37db9ff3cf4ac9323bb98d801644181a5cb
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_full_config_preflight_review_19bcebe6_b2de06d662cf9764
current_v25_review_artifact_root_sha256=96bd1626eba2be1143eb4ad439ad7b38de90d56d9bbafee76e63d0402f53386e
current_v25_full_config_preflight_release_root_sha256=323a7326c744d54b410f6b0ace7e1ac648e4c60045569bab77640942398a2687
current_v25_failed_execute_root_sha256=ba79db8dd0ae87c9b4614aca09ef75077f316a40bbbc15cc614626d624bdafab
current_v25_failure_regression_matrix_row_count=10
current_v25_production_entry_preflight_passed=true
current_v25_production_entry_regression_test_result=8_passed
current_v25_official_execute_nonce_generated=false
current_v25_corrected_full_corpus_started=false
current_v25_monitor_started=false
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=41835847680
current_v25_full_corpus_storage_root=/root/autodl-tmp
current_v25_projected_full_corpus_peak_bytes=27909527113
current_v25_projected_post_corpus_free_bytes=13926320567
current_v25_phase=A1_7_production_entry_preflight_passed_before_full_corpus_execute
next_work_target=A1_7_full_corpus_execute_release_and_unique_worker_after_control_report

## A1.7 corrected 1,500-identity corpus and independent review PASS

The fresh corrected controlled-training corpus completed and sealed without
changing the fixed DP, K=8 candidate tensors, trajectory contract, atom
formulas, canonical `[0,10]` normalization, source-valid eligibility, or
candidate0 same-forward alias. The full planned denominator is retained:
1,500 terminal identities, 1,494 complete identities with exactly 64 ticks,
six typed `fixed_dp_candidate_generation_capability_failure` identities with
zero training rows, 95,616 complete snapshots, and zero partial snapshots.
The six failures remain in coverage accounting and are ineligible for labels,
scales, context fitting, training, calibration, or evaluation.

The independent reviewer ran once over the sealed corpus and passed with
`run.exit=0`. It reopened the corpus, route-level signal source artifacts,
snapshot shards, native receipts, fixed K8/candidate0 evidence, raw 14D atoms,
26D causal context, source/applicability/physical masks, selection evidence,
typed failures, terminal denominator, and exact inventories. The strict review
seal has four payloads and root
`548a5468e585bd39bfbb58ecfd4780e6c78ff88cddb7fef985532639d8dd2c4a`.
The review consumed no Fresh or outcome fields. Its posthoc correction scope is
limited to the three frozen reviewer/test paths and binds producer source HEAD
`19bcebe6...`, producer pointer HEAD `0b689591...`, and review HEAD
`709a76c2...`.

At the terminal check, CAMP and fixed DP were tracked clean, no worker or GPU
compute process remained, the corpus lock was free, and writable free space
was 19,667,914,752 bytes, above the 10 GiB floor. The obsolete review heartbeat
was deleted after terminal evidence appeared. Training, calibration, Scene
runtime, V2I, Fresh B2, and outcome evaluation remain unopened. The sole next
stage is a sealed train-only empirical audit of all approved 14 atoms with the
canonical 9D prefix and preregistered group ablations; it may consume only this
sealed corpus and its passed review.

current_v25_status=v25_a17_corrected_full_corpus_and_independent_review_passed_train_only_atom_audit_next
current_v25_source_head=709a76c297fc00c87d5852574bc6851fdeffb4bd
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_a17_corrected_full_corpus_19bcebe6_e591ab98ae575ed6
current_v25_artifact_root_sha256=97a361b2bbb3544e842c9b6d12b3c17b8f63982db3217e9e360643b0cd7b0ffd
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_a17_corrected_full_corpus_review_shards_709a76c2
current_v25_review_artifact_root_sha256=548a5468e585bd39bfbb58ecfd4780e6c78ff88cddb7fef985532639d8dd2c4a
current_v25_corpus_producer_source_head=19bcebe67f1026f8087505190d11d159d7aa2f1a
current_v25_corpus_producer_pointer_head=0b689591dd109ed883e26205dbb289676341716b
current_v25_corpus_identity_denominator=1500
current_v25_corpus_complete_identity_count=1494
current_v25_corpus_typed_retained_failure_count=6
current_v25_corpus_snapshot_count=95616
current_v25_corpus_partial_snapshot_count=0
current_v25_corpus_review_passed=true
current_v25_failure_regression_matrix_row_count=10
current_v25_corrected_full_corpus_started=true
current_v25_corrected_full_corpus_completed=true
current_v25_monitor_started=false
current_v25_train_only_atom_audit_started=false
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=19667914752
current_v25_full_corpus_storage_root=/root/autodl-tmp
current_v25_phase=A1_7_corrected_full_corpus_independent_review_passed
next_work_target=sealed_train_only_14d_atom_empirical_audit_and_independent_review

## Train-only 14D atom empirical audit and independent review PASS

The audit consumed only the sealed corrected corpus and its passed independent
review. It used 95,616 complete snapshots and 764,928 fixed-DP candidates;
the six typed fixed-DP capability failures contributed zero rows. Route,
semantic-block, seed, and tick identifiers were used only for hierarchical
offline weighting, never as model/context features. The 26D no-V2I context has
zero available `phase_remaining_s` entries. No closed-loop outcome, Fresh,
calibration, or future field was consumed.

The producer and independent reviewer both report 14 PASS, zero WARN, and zero
FAIL under the explicitly narrow train-support/candidate-distinction scope.
This does not erase the earlier static formula/source ledger, and it is not a
safety or cross-map claim. Numerical rank is 14 but effective atom-delta rank
is only 3.1832. The canonical 9D subset changes 32,204 selected indices with
weighted flip rate 0.34094 relative to the 14D causal-label reference, so the
extension is empirically consequential and remains the primary representation.

| # | Atom | Status | positive rows / blocks | K8 distinguishing weight | clip saturation | label-minus-atom Spearman | train scale |
|---:|---|---|---:|---:|---:|---:|---:|
| 0 | jerk_early | PASS | 764928 / 1387 | 1.0000 | 0.000059 | 0.2234 | 1315.8699 |
| 1 | jerk_late | PASS | 764928 / 1387 | 1.0000 | 0.000318 | 0.1076 | 5202.7992 |
| 2 | jerk_full | PASS | 764928 / 1387 | 1.0000 | 0.000282 | 0.1076 | 6271.8155 |
| 3 | rms_acceleration | PASS | 764928 / 1387 | 1.0000 | 0 | 0.0897 | 1.8198 |
| 4 | speed_limit_margin_0_0 | PASS | 691749 / 1387 | 0.9302 | 0 | -0.1884 | 93.9869 |
| 5 | speed_limit_margin_0_5 | PASS | 736206 / 1387 | 0.9785 | 0 | 0.4742 | 118.1000 |
| 6 | speed_limit_margin_1_0 | PASS | 755421 / 1387 | 0.9963 | 0 | 0.4639 | 147.7588 |
| 7 | lane_deviation | PASS | 67730 / 659 | 0.1074 | 0 | 0.1744 | 2902.5946 |
| 8 | clearance | PASS | 299745 / 1107 | 0.4326 | 0 | 0.5340 | 56.4167 |
| 9 | progress_shortfall | PASS | 664569 / 1387 | 0.9937 | 0 | 0.0707 | 8.7528 |
| 10 | planned_red_light_cost | PASS | 27453 / 119 | 0.4761 | 0 | 0.3707 | 40.5000 |
| 11 | planned_lateral_acceleration_cost | PASS | 764928 / 1387 | 1.0000 | 0 | -0.0784 | 1.0534 |
| 12 | red_stopping_margin_cost | PASS | 6259 / 74 | 0.1923 | 0 | 0.2336 | 28.2274 |
| 13 | dp_prior_jerk_excess_cost | PASS | 379186 / 1387 | 0.9935 | 0.000176 | 0.0655 | 2.6082 |

The low effective rank, sparse lane/red distinction, and weak or negative
label-minus-atom associations are retained as redundancy/trade-off evidence;
no atom is silently removed. The sealed train inventory contains 222 route
hashes and 1,387 semantic blocks but only one map family and one corridor.
Consequently, training may continue for the fixed controlled support domain,
but final claims cannot imply broad unseen-map generalization. Fresh B2 must
establish its own independent map/intersection/corridor ceiling and power.

The atom audit sealed at root
`4dc98d9a812403148f30e2041358fbd79c967e3c8581a9d8569dc362f71d8e7e`;
its independent review sealed at root
`149995eacbcdf21201934bbf428ca5d8871f6c3085b4ab5e90db1d8ef78753bc`.
Strict re-open verified eight producer payloads and four review payloads.
Training, calibration, Scene runtime, V2I, Fresh B2, and outcome evaluation
remain closed. The next stage is the fair four-model training suite using the
same reviewed rows, train-only labels/scales, and block weights.

current_v25_status=v25_train_only_atom_audit_and_independent_review_passed_training_next
current_v25_source_head=2e6432456efd5f542d174977e4212aab51d4b82a
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_train_only_atom_audit_2e643245_20260722T094825CST
current_v25_artifact_root_sha256=4dc98d9a812403148f30e2041358fbd79c967e3c8581a9d8569dc362f71d8e7e
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_train_only_atom_audit_review_2e643245_20260722T100733CST
current_v25_review_artifact_root_sha256=149995eacbcdf21201934bbf428ca5d8871f6c3085b4ab5e90db1d8ef78753bc
current_v25_atom_audit_snapshot_count=95616
current_v25_atom_audit_candidate_count=764928
current_v25_atom_audit_pass_warn_fail=14,0,0
current_v25_training_scale_pass_warn_fail=14,0,0
current_v25_atom_delta_numerical_rank=14
current_v25_atom_delta_effective_rank=3.1832077907871783
current_v25_paper_9d_selected_index_flip_count=32204
current_v25_paper_9d_selected_index_flip_weight=0.34094138781638783
current_v25_train_unique_route_count=222
current_v25_train_unique_semantic_block_count=1387
current_v25_train_unique_corridor_count=1
current_v25_train_unique_map_family_count=1
current_v25_phase_remaining_available_count=0
current_v25_failure_regression_matrix_row_count=10
current_v25_corrected_full_corpus_started=true
current_v25_corrected_full_corpus_completed=true
current_v25_monitor_started=false
current_v25_train_only_atom_audit_started=true
current_v25_train_only_atom_audit_completed=true
current_v25_training_started=false
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=19532099584
current_v25_full_corpus_storage_root=/root/autodl-tmp
current_v25_phase=train_only_atom_audit_and_independent_review_passed
next_work_target=fair_static14d_scene14d_training_with_9d_subset_ablations

## Fair Static/Scene 14D Training and Independent Review PASS

The fair training suite consumed only the sealed train-only atom-audit rows and
the reviewed no-V2I causal context. Static14D and Scene14D are the two primary
methods; Static9D and Scene9D are paper-subset ablations. All four used the same
95,616 rows, causal-policy-distillation labels, 14D training scales, source-valid
eligibility, hierarchical record weights, and solver contract. V24 rows without
raw context were excluded from the primary 2x2 comparison.

The training artifact sealed successfully at root
`8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9`.
The first independent review failed at the context-scaler gate and remains
immutable diagnostic root
`298f223626f54317f538a122b00af3dd7c6716afd8e9f16eaf7db4aa037c39d7`.
Read-only localization proved all 14 scales were bit-exact and isolated one
reviewer-only empirical-CDF boundary mismatch at
`context_q05[19]=neighbor_closing_speed_mps`: stored/frozen-producer
`-10.138996566652708` versus reviewer `-10.139556013866958`. The producer used
`q*cumulative[-1]`; the reviewer had used `q*np.sum(mass)`. No tolerance or
stored value changed.

After that reviewer fix, the second full review failed at the Static14D
score/cut/selection gate and remains immutable diagnostic root
`a79d090a4acf38fc355963ddc8172c076ffcdf4dd272001c957bf9081d5668e2`.
The authorized merged dry-run continued through all four models and every
later gate. It found two reviewer-only contract mismatches:

- the producer forms active atoms with advanced indexing, while the reviewer
  used a numerically equal contiguous slice; different `einsum` accumulation
  order at machine-precision ties caused 34 Static14D, 16 Scene14D, 40
  Static9D, and one Scene9D selected-index differences;
- the reviewer compared the maximum full-versus-active-cut envelope gap to the
  frozen solver tolerance, although the training contract's reported gap is
  `exact_losses - optimized_master_losses`. CVaR master-loss slack can exceed
  the active-cut envelope without changing the optimized objective, so these
  are distinct quantities. The active-cut envelope gap is not the frozen
  optimized-master-loss gap. The envelope remains visible as a non-gating
  diagnostic rather than being mislabeled as the solver master gap.

With the producer's frozen active-index layout, all stored selected indices,
selection margins, train violations, Theta/runtime weights, q05/q95 arrays,
14D scales, summaries, and leave-corridor diagnostics reproduced bit-exact for
all four models. Every active-cut mask had at least one cut per row; cut hashes,
counts and min/median/max summaries matched. The sealed histories matched their
iteration counts, final cut totals and solver statuses, ended with zero new
cuts, and reported final gaps within the frozen `1e-6` tolerance:

| Model | Iterations | Reported final master gap | Active-cut envelope diagnostic |
|---|---:|---:|---:|
| CAMP-Static14D | 4 | 0 | 0.38570803769146317 |
| CAMP-Scene14D | 4 | 8.045300603498617e-7 | 0.3301689654054084 |
| CAMP-Static9D | 2 | 0 | 0.36978180193253846 |
| CAMP-Scene9D | 3 | 8.934973414476133e-7 | 0.36696802551998947 |

Commit `8fecda47e93412ff9659168088c84feb8dc93ab1` contains only the merged
reviewer consistency fix and its dedicated regressions. AutoDL passed all 38
focused scene/training tests. The final independent review then ran from the
beginning, passed every gate over 95,616 snapshots, reported zero available
no-V2I `phase_remaining_s` rows, and sealed at root
`ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9`.

No producer, model parameter, scale, Theta, runtime weight, training row,
fixed-DP/K8 candidate, trajectory, atom formula, clip, simplex, affine score,
or convex objective changed. No closed-loop outcome or Fresh field was read.
Training is accepted only inside this fixed controlled support domain; it is
not safety evidence and does not establish broad unseen-map generalization.
Calibration, Scene runtime, V2I, Fresh B2, and outcome evaluation remain
closed. The next stage is the preregistered calibration freeze and independent
review before any Fresh B2 pre-open action.

current_v25_status=v25_training_and_independent_review_passed_calibration_freeze_next
current_v25_source_head=8fecda47e93412ff9659168088c84feb8dc93ab1
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_camp_training_863e28da_20260722T103219CST
current_v25_artifact_root_sha256=8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_camp_training_review_8fecda47_20260722T122701CST
current_v25_review_artifact_root_sha256=ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9
current_v25_training_snapshot_count=95616
current_v25_training_model_count=4
current_v25_training_primary_models=CAMP-Static14D,CAMP-Scene14D
current_v25_training_ablation_models=CAMP-Static9D,CAMP-Scene9D
current_v25_training_solver=CLARABEL
current_v25_training_review_passed=true
current_v25_training_context_q05_q95_exact=true
current_v25_training_scales_14d_exact=true
current_v25_training_phase_remaining_available_count=0
current_v25_training_failed_review_root_1=298f223626f54317f538a122b00af3dd7c6716afd8e9f16eaf7db4aa037c39d7
current_v25_training_failed_review_root_2=a79d090a4acf38fc355963ddc8172c076ffcdf4dd272001c957bf9081d5668e2
current_v25_monitor_started=false
current_v25_training_started=true
current_v25_training_completed=true
current_v25_calibration_started=false
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=19524542464
current_v25_full_corpus_storage_root=/root/autodl-tmp
current_v25_phase=fair_four_model_training_and_independent_review_passed
next_work_target=calibration_freeze_and_independent_review_before_fresh_b2_preopen

## Paired Calibration Recovery and Independent Review PASS

The Fresh-closed calibration contract compared the DP operational default
(candidate0 from the same fixed-DP forward), CAMP-Static14D, and no-V2I
CAMP-Scene14D. Static9D and Scene9D remain subset ablations and are not promoted
to primary methods. All arms used the unchanged fixed DP at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`, sequential K=8 candidate
semantics, the frozen 14D atom/scale/clip contract, the accepted trained
parameters, source-valid eligibility, and lowest-index tie break.

### Immutable raw evidence and analyzer-only recovery

The original execution completed all 300/300 arms before its terminal analyzer
failed closed. It remains immutable with `run.exit=1` at:

`/root/autodl-tmp/camp_dp_v25_paired_calibration_execution_325cd486_20260722Tcalibration325cd486CST`

root
`5cd071b6ac9dd805422d7fe572f3db273abe9fce5cd4f910a0cf6fa9296e8249`.
The failure was a registry omission for the already-recorded latency field
`input_materialization`; it occurred after 100 pairs, 300 terminal arms, and
19,200 ticks were written and sealed. No arm was rerun.

The detached read-only localization receipt
`/root/autodl-tmp/camp_dp_v25_calibration_localization_receipt_5cd071b6.json`
(SHA256
`bb63ac5bf02d84d8d4a2fc256325b8efd2cbb673f43845774ab986be5780d8a7`)
independently revalidated all configs, terminal rows, native receipts, paired
resets, corpus rows, atom evidence, and latency records. All 19,200
`input_materialization` values are finite nonnegative milliseconds measured by
`time.perf_counter_ns`. Static source inspection and receipt reconstruction
confirmed that the field never enters DP/K8 generation, atoms, context,
weights, scores, selection, trajectory, SafetyCost, thresholds, NI margins, or
sample retention. It is supplementary runtime timing, not a post-outcome
protocol change.

Commit `7d924b6491a8ebe4f8e2f858989659c71b3def60` added only the missing
analyzer latency classification and the recovery producer/reviewer. The
corrected detached focused suite passed 54 tests. Commit
`f4a4110b234d1204ef0b46d6db753896995a3bb8` made the independent reviewer
compare the same canonicalized exact values while retaining adjacent-value
drift rejection; its affected suite passed four tests. No producer, raw
artifact, model, threshold, margin, DP/K8, trajectory, atom, score, selection,
or outcome changed.

The analyzer-only recovery sealed with `run.exit=0` at:

`/root/autodl-tmp/camp_dp_v25_paired_calibration_recovery_analysis_7d924b64_20260722T145211CST`

root
`9d67e57bfa4a96ff3bf318c5aafd17f024207645344f076963fc5f756caa6551`.
The final from-scratch independent recovery review re-opened the original seal,
rebuilt all 300 configs and terminal rows, revalidated all native receipts and
initial paired resets, rederived the analysis, scores, selections and atom
tables, and confirmed that the original raw bytes were unchanged. It sealed
with `run.exit=0` at:

`/root/autodl-tmp/camp_dp_v25_paired_calibration_recovery_review_f4a4110b_20260722T153812CST`

root
`650e6749bda63f23b073a5491c0f57dd9f97136a644be8ab7c918a48a3f609f7`.
The chain receipt SHA256 is
`b4439eea4ff4f3891d39458c4125fa55ba7169d81346407576ae11793812c41c`.

### Split, denominator, and source coverage

The reviewed denominator is 100 paired units and 300/300 complete arms, with
zero retained failures and 19,200 ticks. It contains 5 maps, 50 intersections,
50 corridors, 50 routes, 50 semantic blocks, and 2 seeds. Every planned arm,
family, family-by-tier, and mapped-signal source-mode completion rate is 1.0;
all seven scenario families are represented. Ticks and seeds remain repeated
measurements, while corridor is the 50-unit cluster level used below.

The entire calibration set is controlled mapped-signal stress evidence. It is
not mixed with natural-road strata and is not reported as a real-world event
frequency. Signal receipts use the certified regulatory element -> physical
light/bulbs -> controlled lanelet -> stop line -> route arc -> same-tick phase
chain. The legacy nearest-line heuristic is not used, future schedules are not
read, and no-V2I `phase_remaining_s` availability is exactly zero. All bad
routes, both-arm failures, source-ineligible rows, retained fixed-DP capability
failures, and all-K-high-risk cases would remain in the denominator; none
occurred in these 300 arms.

The frozen paired preregistration and its independent review roots are
`e6f8cf6cb37c3acd964502f04c12a6e15af1fb3d946048ea4abc18c8741f5d55`
and `235a99323be75476b7d8d31d9458ddd6f583d6a5d6593901e492addfe40c69e6`.
The paired plan/review roots are `efaf7f2eeef4cb3d74e74879c81f4ce47bbad4fe30cb87bb8d135158ff64fa8d`
and `4b8ce3b10b6eefcd342f252981479e193022b2b00f15b7e4d4d36991b0475b8f`.
The signal map, route/review, and runtime/review roots are respectively
`f4ab3e93a43bef1486cdc4e8bcd74abe445bd4fb73d4ad770ebeb3ae046d6b15`,
`62c149f164c617f74a73871c08a56680019725b8e879f674511d2d142cb83259` /
`3fd602f054c0e8703651306681868e95fb0a4f367b9ce42a1c629508b6a42832`,
and `0d5b804fe868a7cb3a3f5f6da0178b8c4b0cf6753ec8c09c7d8b46135e8a482c` /
`61c7c0ba0beee85e806a163fb5fd55be2f962a8911f80feace08a3d4f4890f87`.

### Primary SafetyCost benchmark

| Method | Mean SafetyCost | Delta vs candidate0 | Corridor-cluster CI95 | Better / tie / worse |
|---|---:|---:|---:|---:|
| DP operational default / candidate0 | 19.2212599512 | 0 | reference | reference |
| CAMP-Static14D | 17.6921953923 | -1.5290645589 | [-2.8613315699, -0.1967975478] | 52 / 10 / 38 |
| CAMP-Scene14D no-V2I | 18.4856536131 | -0.7356063381 | [-2.3272034503, 0.8559907741] | 48 / 17 / 35 |

The Static14D one-sided SafetyCost upper bound is `-0.4175792035`; the
Scene14D one-sided upper bound is `0.5922332520`. These are calibration results,
not Fresh confirmatory evidence.

Component deltas below are CAMP minus candidate0:

| Component | Static14D delta / CI95 / B-T-W | Scene14D delta / CI95 / B-T-W |
|---|---|---|
| collision | 0 / [0, 0] / 0-100-0 | 0 / [0, 0] / 0-100-0 |
| near-miss | -0.015 / [-0.025009, -0.004991] / 42-52-6 | -0.005781 / [-0.010395, -0.001167] / 26-65-9 |
| offroad | +0.009688 / [-0.002185, 0.021560] / 37-20-43 | +0.013281 / [0.003461, 0.023101] / 32-33-35 |
| red-light | -0.05 / [-0.093062, -0.006938] / 5-95-0 | -0.03 / [-0.083013, 0.023013] / 5-93-2 |
| speed | -0.007281 / [-0.021526, 0.006963] / 9-84-7 | -0.004342 / [-0.010736, 0.002052] / 10-84-6 |
| wrong-way | 0 / [0, 0] / 0-100-0 | 0 / [0, 0] / 0-100-0 |

Static14D passes collision, near-miss, red-light and wrong-way component
guardrails but not offroad or speed. Scene14D does not pass the offroad,
red-light, or speed guardrails; its offroad CI is entirely above zero.

Certified-stop-line red-light counts/rates were `31 / 0.01030585` for
candidate0, `26 / 0.00864362` for Static14D, and `28 / 0.00930851` for
Scene14D. False-stop-on-green was zero in all three arms.

### Performance and comfort noninferiority

| Metric | candidate0 mean | Static14D mean | Scene14D mean |
|---|---:|---:|---:|
| completion | 0.278433 | 0.273877 | 0.278366 |
| progress | 35.232873 | 34.659026 | 35.219464 |
| mean jerk | 6.586002 | 9.418703 | 9.437160 |
| max jerk | 56.222370 | 55.706420 | 56.326970 |
| mean lateral acceleration | 0.287976 | 0.294197 | 0.301885 |
| max lateral acceleration | 1.164940 | 1.250779 | 1.273734 |
| max deceleration | 4.247885 | 4.247885 | 4.247885 |

The preregistered one-sided NI results were:

| Metric (margin) | Static upper / pass | Scene upper / pass |
|---|---:|---:|
| completion (0.02) | 0.008536 / PASS | PASS |
| progress (1.0) | 1.081425 / FAIL | PASS |
| mean jerk (0.2) | 3.078369 / FAIL | 3.136 / FAIL |
| max jerk (1.0) | 0.871316 / PASS | 1.145 / FAIL |
| mean lateral acceleration (0.1) | 0.016438 / PASS | PASS |
| max lateral acceleration (0.3) | 0.202414 / PASS | PASS |
| max deceleration (0.5) | 5.62e-7 / PASS | PASS |

Accordingly, the all-NI gate is false for both primary CAMP methods. The frozen
0.1 m/s operational overspeed tolerance remains an evaluation tolerance and is
not substituted for the 0/0.5/1.0 speed-margin atom definitions.

### Atom, selection, and numerical-layout audit

All 14 approved atoms are PASS with zero WARN and zero FAIL. Source coverage is
1.0 for every atom; signal atom applicability is 0.47 and all other atoms are
1.0. Only `dp_prior_jerk_excess_cost` shows nonzero clip saturation
(`1.953125e-05`). No weak or redundant atom was silently removed.

Across 12,800 official selection ticks there was one lowest-index tie. The
frozen producer accumulation layout versus the diagnostic mathematically
equivalent layout produced zero selected-index flips. Score-margin q05/q50/q95
was `3.3308421603e-17 / 0.0007283336 / 0.0339509477`. The 9D subset changed 720
Static selections and 3,836 Scene selections relative to 14D. Leave-group flip
counts were: dp-prior 2,901; jerk3 1,577; lane+clearance 505; lateral 306;
progress 2,713; signal2 810; speed3 336. These are mechanism/ablation evidence,
not independent safety claims.

### Online latency and prospective power

Each latency cell is mean / median / p95 / p99 / max milliseconds:

| Stage | candidate0 | Static14D | Scene14D |
|---|---|---|---|
| input materialization (supplementary) | 6.518 / 6.465 / 7.075 / 8.226 / 112.002 | 6.522 / 6.481 / 7.095 / 7.886 / 16.616 | 6.503 / 6.459 / 7.078 / 8.217 / 25.917 |
| DP default | 52.893 / 52.473 / 55.174 / 57.215 / 427.844 | 52.922 / 52.545 / 55.224 / 57.884 / 106.477 | 52.975 / 52.546 / 55.522 / 57.856 / 117.504 |
| additional K8 candidate inference | 364.513 / 363.612 / 371.279 / 390.143 / 714.781 | 364.738 / 363.980 / 371.533 / 391.557 / 503.197 | 364.748 / 363.902 / 372.275 / 387.185 / 616.889 |
| atom | 39.626 / 26.181 / 109.307 / 163.696 / 232.962 | 39.151 / 26.111 / 107.211 / 162.297 / 234.801 | 39.674 / 26.151 / 109.120 / 161.207 / 240.939 |
| context | n/a | n/a | 3.167 / 3.147 / 3.318 / 3.736 / 7.831 |
| Scene weight | n/a | n/a | 0.275 / 0.273 / 0.289 / 0.339 / 1.566 |
| selector | n/a | 0.194 / 0.192 / 0.205 / 0.231 / 1.687 | 0.186 / 0.185 / 0.196 / 0.224 / 1.020 |
| tracker | 5.768 / 5.953 / 6.477 / 7.569 / 17.249 | 5.793 / 5.987 / 6.511 / 7.461 / 19.077 | 5.828 / 6.004 / 6.522 / 8.072 / 15.787 |
| total planning | 535.842 / 521.737 / 615.220 / 702.048 / 1411.673 | 550.964 / 522.500 / 637.378 / 1312.534 / 1916.648 | 552.661 / 526.704 / 638.132 / 1254.223 / 1806.725 |

This separates the small selector cost from the much larger system cost of
obtaining the additional fixed-DP candidates. No microbatch/cache/sharding
optimization was mixed into the scientific run.

At 50 corridor clusters, the prospective SafetyCost CI half-width / MDE is
`1.332267 / 1.857338` for Static14D and `1.591597 / 2.218874` for Scene14D.
The red-light component half-width / MDE is `0.043062 / 0.060034` for
Static14D and `0.053013 / 0.073907` for Scene14D. Seeds and ticks are not counted
as independent maps or corridors.

### Honest calibration boundary and next gate

Calibration is accepted as complete, immutable, and independently reviewed.
It does not authorize a V25 safety claim. Static14D has a negative clustered
SafetyCost CI but fails progress and mean-jerk NI and two component guardrails.
Scene14D's SafetyCost CI crosses zero, its offroad component significantly
regresses, and max/mean jerk NI fails. Neither result supports promotion,
deployment, native-ranked-Top1 language, real-road safety, broad-map
generalization, or model/threshold changes.

Fresh B v1 remains superseded-before-opening. Fresh B2 and all Fresh outcomes
remain unopened. The next gate is Ultra's one-time Fresh B2 pre-open review;
no evaluation may start before that explicit release.

current_v25_status=v25_calibration_recovery_and_independent_review_passed_fresh_b2_preopen_review_required
current_v25_source_head=f4a4110b234d1204ef0b46d6db753896995a3bb8
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v25_artifact=/root/autodl-tmp/camp_dp_v25_paired_calibration_recovery_analysis_7d924b64_20260722T145211CST
current_v25_artifact_root_sha256=9d67e57bfa4a96ff3bf318c5aafd17f024207645344f076963fc5f756caa6551
current_v25_review_artifact=/root/autodl-tmp/camp_dp_v25_paired_calibration_recovery_review_f4a4110b_20260722T153812CST
current_v25_review_artifact_root_sha256=650e6749bda63f23b073a5491c0f57dd9f97136a644be8ab7c918a48a3f609f7
current_v25_calibration_preregistration_root_sha256=e6f8cf6cb37c3acd964502f04c12a6e15af1fb3d946048ea4abc18c8741f5d55
current_v25_calibration_preregistration_review_root_sha256=235a99323be75476b7d8d31d9458ddd6f583d6a5d6593901e492addfe40c69e6
current_v25_original_calibration_artifact=/root/autodl-tmp/camp_dp_v25_paired_calibration_execution_325cd486_20260722Tcalibration325cd486CST
current_v25_original_calibration_root_sha256=5cd071b6ac9dd805422d7fe572f3db273abe9fce5cd4f910a0cf6fa9296e8249
current_v25_original_calibration_run_exit=1
current_v25_calibration_recovery_review_passed=true
current_v25_calibration_pair_count=100
current_v25_calibration_arm_count=300
current_v25_calibration_complete_arm_count=300
current_v25_calibration_retained_failure_count=0
current_v25_calibration_tick_count=19200
current_v25_calibration_independent_corridor_count=50
current_v25_static14d_safetycost_delta=-1.5290645588752225
current_v25_static14d_safetycost_ci95_upper=-0.19679754782883419
current_v25_static14d_all_noninferiority_passed=false
current_v25_scene14d_safetycost_delta=-0.7356063380674055
current_v25_scene14d_safetycost_ci95_upper=0.8559907741462941
current_v25_scene14d_all_noninferiority_passed=false
current_v25_calibration_claim_authorized=false
current_v25_atom_calibration_pass_warn_fail=14,0,0
current_v25_phase_remaining_available_count=0
current_v25_monitor_started=false
current_v25_training_completed=true
current_v25_calibration_started=true
current_v25_calibration_completed=true
current_v25_worker_count=0
current_v25_gpu_compute_count=0
current_v25_lock_state=free
current_v25_fresh_outcome_opened=false
current_v25_fresh_b2_opened=false
local_origin_github_autodl_aligned=true
minimum_free_disk_gib=10
observed_autodl_free_bytes=24659705856
current_v25_full_corpus_storage_root=/root/autodl-tmp
current_v25_phase=paired_calibration_recovery_and_independent_review_passed
next_work_target=ultra_fresh_b2_preopen_review_required_before_one_time_opening
