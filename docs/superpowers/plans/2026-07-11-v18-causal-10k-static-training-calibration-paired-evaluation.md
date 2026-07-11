# v18 Causal-10k Static Training, Calibration, Paired Evaluation, and Bounded Safety Spec/Plan

> **Execution mode:** Inline Execution on the current `main`, already approved.
> Follow TDD, small verified commits, AutoDL ff-only synchronization, immutable
> artifacts, and independent result review. Do not pause for another design or
> execution-choice approval while this frozen contract remains unchanged.

**Goal:** Train the primary static convex canonical-14D CAMP selector from the
frozen causal nuPlan-10k train split, freeze the required offline comparison
family before any holdout access, perform tuning-free calibration diagnostics,
open the 1,931 materialized holdout labels exactly once for paired evaluation,
and apply the preregistered bounded-offline safety protocol without learned
CAMP evaluation weights.

**Architecture:** Reuse the existing thin v18 training/evaluation runner and
`solve_robust_margin_cutting_plane`; do not add another runner or optimizer.
Generalize only the frozen corpus contract, counts, comparison-family loop, and
causal-10k evidence wording. Training/calibration, holdout preflight, one-shot
paired evaluation, and bounded safety remain separate atomic gates. Holdout
labels stay sealed until every model, scale, threshold, metric, bootstrap,
comparison, claim criterion, and safety-protocol hash has passed independent
freeze review.

**Files:**

- Modify: `scripts/integrations/run_diffusion_planner_dp_camp_v18_training_evaluation.py`
- Modify: `camp_core/tests/test_diffusion_planner_v18_training_evaluation.py`
- Reuse unchanged: `scripts/integrations/run_diffusion_planner_dp_camp_v18_bounded_safety.py`
- Reuse unchanged: `camp_core/camp_core/optim/robust_margin_master.py`
- Modify: `docs/diffusion_planner_v18_iteration_audit.md`
- Modify only `## Current V18 Status` in
  `docs/diffusion_planner_current_status.md`

## Frozen Corpus and Evidence Contract

- Fixed DP is tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Candidate source root/SHA256 is
  `/root/autodl-tmp/camp_dp_v18_nuplan_causal_10k_candidates_703a47bec14d`
  / `3febcd4de182598e69d3420900c996eb37dc3f54d0a8a4a1f221d6ab3c648515`.
- Canonical source root/SHA256 is
  `/root/autodl-tmp/camp_dp_v18_nuplan_causal_10k_canonical_14d_3febcd4de182`
  / `79c9570bf04088ff05aea30a1e251738742e3648742044be724b662ff5329a3c`.
- Candidate-0 equivalence review root/SHA256 is
  `/root/autodl-tmp/camp_dp_v18_nuplan_causal_10k_fixed_dp_deterministic_map_equivalence_result_review_a5f38464_20260711T193330CST`
  / `aacbab7f5b64bdec369435309a3530b4cec6d704c031be6c8d8322b2a4ff6446`.
- The source manifest has exactly `6000/2000/2000` train/calibration/holdout
  rows with zero log/scene overlap. Canonical materialization retains all
  10,000 audit rows and exactly `5631/1896/1931` materialized NPZs.
- The 243 source-incomplete and 299 all-K-infeasible rows keep reasons/masks but
  have no canonical NPZ or label and remain excluded from scaling, training,
  calibration, evaluation, and bounded safety. Never force candidate 0 and
  never compute all-K `progress_shortfall` fallback.
- Train and calibration NPZs contain expert-derived ADE/FDE labels. Holdout NPZs
  contain no expert label. All 1,931 materialized holdout labels remain sealed
  until the one-shot gate.
- Candidate tensors, DP, canonical atoms, identities, split, and all upstream
  roots are immutable. Any drift fails closed.

## Frozen Model and Training Mathematics

- The primary model is one static canonical 14-vector; no scene-conditioned
  `Theta` and no online feature-conditioned weights.
- Runtime score is `score_k = a_scaled_k^T w`, where
  `a_scaled_k = a_canonical_k / train_scales`, `w >= 0`, and `sum(w) = 1`.
- Scaling is the per-atom 95th percentile over feasible candidate rows from the
  applicable train subset only, floored at `1e-6`, with no clipping.
  Calibration and holdout never affect scales.
- Primary oracle/label is minimum independent expert-future ADE among feasible
  candidates. Candidates within `1e-9 m` ADE use lower FDE; remaining exact
  ties use `numpy.random.default_rng(3409).permutation(8)`.
- Robust margins are
  `clip(0.1 * max(ADE_k - ADE_oracle, 0), 0, 2.0)`.
- Reuse the existing finite-candidate robust-margin cutting-plane master in
  static mode with CVaR alpha `0.9`, L2 `1e-4`, CLARABEL, `max_iter=20`, and
  tolerance `1e-6`. Do not use the v16 epoch trainer or random restarts.
- Training seed is `3408`, tie seed `3409`, bootstrap seed `3410`; seeds
  11/12/13 are forbidden.
- A model is evaluable only if solver status is exactly `optimal`,
  `converged=true`, `final_master_gap <= 1e-6`, final `new_cuts=0`, weights are
  finite/nonnegative/simplex, and an independent complete-master recomputation
  passes. Otherwise no checkpoint is promoted.

## Frozen Offline Comparison Family

All selectors below must be frozen before holdout access and use the same fixed
candidate tensors, feasibility masks, labels, tie priority, and metric code.

- fixed-DP deterministic/MAP baseline: candidate 0, with
  `native_ranked_top1=false`;
- uniform14D: fixed `w_i = 1/14` after train-only 14D scaling;
- corrected 9D/10D/12D/13D/14D: the existing canonical schema prefixes
  `camp_legacy_v1_9d`, `dp_camp_v7_10d`, `dp_camp_v8_12d`,
  `dp_camp_v9_13d`, and `dp_camp_v10_14d`, each trained with the same approved
  convex master and its own train-only prefix scales;
- mini-trained14D: immutable mini selector freeze
  `b09a81f94776a59ad6ac8fe93ec27f610d4b74859efa1b10f7f4d0160596a058`,
  independently reviewed at
  `de5a90b7ac5e4295b58f11f48ddbb519646130129644c7cbc8d7b559051b29ea`;
- external-metric feasible best-of-K oracle, reported only as headroom;
- same-data retrained `legacy9D` is allowed only if a distinct, causal,
  previously approved legacy schema and training contract can be proven. The
  v16 epoch trainer, noncausal source semantics, constants, proxies, or future
  leakage are forbidden. If no distinct compliant contract exists, record
  `legacy9D=unavailable` with the complete reason and fail the formal comparison
  claim closed rather than aliasing corrected9D.

For the primary corrected14D learning curve, use nested prefixes of the frozen
train order at 10/25/50/100 percent: `564/1408/2816/5631` records. Each point
fits its own train-only scales and convex model under the same settings. These
are diagnostics; the 100-percent model is the primary 10k-trained14D selector.

## Calibration, Freeze, and One-Shot Holdout Contract

- Calibration is tuning-free. It computes each frozen selector's ADE/FDE/miss,
  better/tie/worse, feasible-oracle gap, selection/oracle gap, candidate-0
  selection count, exclusions, and latency without changing any model, scale,
  threshold, margin, solver setting, or metric.
- Before holdout access, freeze every model/scales hash, unavailable-comparator
  reason, miss threshold `FDE > 2.0 m`, better/tie tolerance `1e-9 m`,
  non-regression slack `0.0`, bootstrap replicates `10000`, CI level `95%`,
  seeds, comparison family, claim criteria, latency protocol, baseline wording,
  and OBB/claim limits. Independent review is mandatory.
- Holdout preflight verifies exactly 1,931 label-free canonical holdout NPZs,
  the 69 excluded source-holdout audit rows, exact identity list, zero overlap,
  fixed roots, reviewed freeze, no active job, and absent output/staging roots.
- One execution may query each materialized holdout expert future exactly once.
  It derives candidate ADE/FDE arrays once and applies all frozen selectors.
  Raw expert futures are never persisted; each record retains a label SHA
  receipt and derived candidate metrics.
- CAMP selection is the minimum affine score among feasible candidates under
  frozen tie priority. No feasible candidate is an invariant failure, never a
  fallback. Candidate 0 is always evaluated as the proven fixed-DP
  deterministic/MAP baseline even if the bounded mask marks it infeasible.
- Report per-selector ADE/FDE/miss, paired deltas, better/tie/worse,
  log-cluster and scene-cluster percentile CI95, feasible-oracle and
  selection/oracle gaps, non-Top1 rate, exclusions, fallback policy/count, and
  selector latency mean/p50/p95/p99/max. Use 10,000 bootstrap replicates from
  distinct child streams of seed `3410`.
- Formal performance language requires all original preregistered conditions:
  corrected14D-minus-baseline ADE mean `< 0` and scene-cluster CI95 high `< 0`;
  FDE, bounded collision, and available road/lane diagnostics non-regression;
  corrected14D primary non-inferiority to corrected9D plus at least one
  14D-sensitive improvement; selector latency p99 `<= 1 ms`; and complete
  paired/hash evidence. Missing or unavailable evidence means no-claim.

## Frozen Bounded-Offline Safety Contract

- Reuse `camp_dp_bounded_offline_safety_score_v1` byte-for-byte at protocol
  SHA256 `54022f480b53d1a036af82f81b4d9124b333bda1971a07122523e9e692a6f94b`.
  Formula, thresholds, supported soft weights, seed, CI, and pass criteria may
  not change after calibration or holdout results are visible.
- The evaluator consumes only immutable selected indices and canonical
  candidate records. It never uses learned CAMP weights as evaluation weights,
  queries labels/models, retrains, or mutates candidates.
- Report CAMP versus candidate-0 score/components and frozen log/scene CI95.
  Exactness is only within the frozen 32 dynamic + 5 static observable source.
  Route-corridor lane compliance is not full drivable-area off-road evidence.
- Mini safety remains post-hoc descriptive no-claim. Causal-10k bounded safety
  is still an offline proxy and cannot establish complete-scene, closed-loop,
  real-world, or deployment safety.

## Task 1: TDD the causal-10k corpus and comparison-family contract

**Files:** modify the existing v18 runner and its focused test only.

1. Write failing tests for exact causal-10k roots/counts, dynamic equivalence
   review count `10000`, materialized-only loading, holdout label absence,
   schema-prefix selectors, nested learning-curve counts, distinct legacy9D
   fail-closed handling, and causal-10k/no-claim wording.
2. Run the focused test and confirm RED for the current mini-only constants and
   hardcoded 367-review contract.
3. Make the smallest change: replace the mini corpus constants/wording with the
   frozen causal-10k contract and reuse existing schema tables/helpers.
4. Run focused tests and `py_compile`.
5. Commit: `feat(v18): bind static selector to causal 10k corpus`.

## Task 2: TDD multi-schema convex training and learning curves

1. Add failing tests that monkeypatch the existing master and prove every
   corrected schema uses only its approved prefix, train-only scales, the same
   frozen solver settings, and exact acceptance gates.
2. Add tests for the corrected14D `564/1408/2816/5631` nested curve and for
   atomic fail-closed behavior when any required primary model is not accepted.
3. Reuse the existing single-model train path in a short loop; do not copy the
   optimizer or add a trainer abstraction.
4. Persist all model/scales/history hashes plus uniform14D, mini-trained14D,
   oracle, and legacy9D availability evidence in one immutable freeze root.
5. Commit: `feat(v18): freeze causal 10k selector comparisons`.

## Task 3: TDD calibration and one-shot multi-selector evaluation

1. Add failing tests for tuning-free 1,896-record calibration, reviewed-freeze
   gating, 1,931 label-free holdout preflight, one query per holdout identity,
   no raw-label persistence, all frozen selector outputs, cluster CI metrics,
   latency, exclusions, and no second execution.
2. Extend the existing evaluator to derive holdout candidate metrics once and
   apply all frozen selectors; do not add another evaluator.
3. Preserve candidate-0 deterministic/MAP wording, `native_ranked_top1=false`,
   all-K fail-closed behavior, and the 32+5 boundary.
4. Commit: `feat(v18): evaluate frozen causal 10k selectors once`.

## Task 4: Full local implementation checkpoint

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m py_compile scripts/integrations/run_diffusion_planner_dp_camp_v18_training_evaluation.py
C:\Users\lenovo\anaconda3\python.exe -m pytest camp_core/tests/test_diffusion_planner_v18_training_evaluation.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py camp_core/tests/test_diffusion_planner_v17_causal_materializer.py -q
git diff --check
```

Record exact counts and implementation SHA, commit/push only task files, then
AutoDL ff-only and rerun the same checks with the preserved Shapely path.

## Task 5: AutoDL train/calibration preflight, execution, and review

1. Reverify all roots, live EOF, exact split/label presence, zero overlap,
   solver/version, disk, no active job, and absent output/staging roots.
2. Execute training/calibration once. Holdout label reads must remain zero.
3. Independently recompute every train-only scale, oracle/margin, complete-
   master gap, model acceptance, learning-curve point, calibration aggregate,
   comparator hash, and unavailable-comparator reason.
4. Freeze model/scales/comparison/evaluation/safety protocol, then
   commit/push/sync and reread EOF.

## Task 6: AutoDL one-shot paired evaluation and independent review

1. Run the final no-label-read preflight against the reviewed freeze.
2. Execute the 1,931-label paired evaluation once and never rerun it for tuning
   or model selection.
3. Independently recompute every persisted per-record selector choice,
   aggregate, CI, claim criterion, latency summary, and label receipt without
   requerying labels.
4. Record claim or no-claim exactly from the frozen criteria, then
   commit/push/sync and reread EOF.

## Task 7: Frozen bounded-offline safety execution and review

1. Preflight the byte-identical protocol SHA and immutable paired-evaluation
   selected indices without labels or learned evaluation weights.
2. Execute once, independently recompute every component/aggregate/CI, and
   preserve the frozen 32+5 and no-closed-loop-safety boundaries.
3. Record the bounded offline result and final claim/no-claim boundary. Stop
   before promotion, deployment, activation, or any broader safety claim.
