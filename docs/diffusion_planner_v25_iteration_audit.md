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
