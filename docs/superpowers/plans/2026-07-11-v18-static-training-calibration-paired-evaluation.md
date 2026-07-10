# v18 Static-14D Training, Calibration, and Paired Evaluation Spec/Plan

> **Execution mode:** Inline Execution on the current `main`, already approved.
> Follow TDD, small verified commits, AutoDL ff-only synchronization, immutable
> artifacts, and independent result review. Do not pause for another design or
> execution-choice approval.

**Goal:** Train one static convex CAMP selector from the frozen nuPlan-mini
canonical 14D train split, perform tuning-free calibration diagnostics, freeze
the complete one-shot paired-evaluation protocol, and then compare CAMP against
the proven fixed-DP deterministic/MAP baseline on the 71 materialized holdout
records exactly once.

**Architecture:** Add one thin v18-specific runner. It loads immutable canonical
NPZs and frozen candidate tensors, derives independent expert-future ADE/FDE
labels, and calls the existing `solve_robust_margin_cutting_plane` master. It
does not copy or rewrite the optimizer. `train-calibrate` and `paired-eval` are
mutually exclusive atomic modes. The first mode never reads holdout labels; the
second refuses to run until the model/scales/protocol root and equivalence
evidence are frozen and independently reviewed.

**Files:**

- Create: `scripts/integrations/run_diffusion_planner_dp_camp_v18_training_evaluation.py`
- Create: `camp_core/tests/test_diffusion_planner_v18_training_evaluation.py`
- Modify: `docs/diffusion_planner_v18_iteration_audit.md`
- Modify only `## Current V18 Status` in:
  `docs/diffusion_planner_current_status.md`

## Frozen Contract

### Inputs and exclusions

- Candidate source is immutable root SHA256
  `92b2c989187d58387e3310579cc9d3ea9695b2b369684d807020c98f6885b028`.
- Canonical source is immutable external root SHA256
  `7c89f73e2b26308a42fbd453fff7e0ece4c7d0b49e219a9c56f99bdb2a65d1cc`.
- Fixed DP is tracked-clean at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Candidate 0 equivalence result-review root SHA256 is
  `25f8e3f3763b5af53d70cdba7dddcf85872b42ce459b6b223b1b65cb5b59ea50`.
- Only canonical-materialized records enter any later stage. Source-incomplete
  and all-K-infeasible records retain audit rows/reasons but remain excluded.
  There is no candidate-0 force and no all-K progress or selection fallback.
- Expected materialized counts are train/calibration/holdout `214/65/71`.
  Train and calibration NPZs contain expert labels. Holdout NPZs must not.

### Model and mathematics

- Model family: one static 14-vector; no scene-conditioned `Theta`.
- Runtime score: `score_k = a_scaled_k^T w`, where
  `a_scaled_k = a_canonical_k / train_scales`.
- `w >= 0`, `sum(w) = 1`; no non-affine selector layer and no candidate tensor
  generation, repair, mutation, blending, guidance, or postprocessing.
- Scaling is the per-atom 95th percentile over feasible candidate rows from
  train records only, floored at `1e-6`. There is no clipping. Calibration and
  holdout do not affect scales.
- Primary oracle is minimum expert-future ADE among physically feasible
  candidates. Candidates within `1e-9 m` ADE of the minimum use lower FDE;
  remaining exact ties use the frozen candidate priority generated once by
  `numpy.random.default_rng(3409).permutation(8)`.
- Robust margins are
  `clip(0.1 * max(ADE_k - ADE_oracle, 0), 0, 2.0)`.
- Reuse the existing finite-candidate robust-margin cutting-plane master with:
  static mode, CVaR alpha `0.9`, L2 `1e-4`, CLARABEL, `max_iter=20`, and
  tolerance `1e-6`.
- Training seed is `3408`; tie seed is `3409`; bootstrap seed is `3410`.
  Seeds 11/12/13 are forbidden.
- Save a usable checkpoint only if solver status is exactly `optimal`,
  `converged=true`, `final_master_gap <= 1e-6`, the final history row has
  `new_cuts=0`, weights are finite/nonnegative/simplex, and an independent
  complete-master violation recomputation also satisfies the gap. Otherwise
  fail closed before atomic promotion.

### Calibration and freeze

- Calibration is tuning-free. It computes the frozen selector's ADE/FDE/miss,
  better/tie/worse, selection/oracle gap, baseline-index selection, and
  fail-closed exclusion diagnostics on the 65 calibration records.
- Calibration never changes weights, atom scales, margins, solver settings,
  metric definitions, bootstrap settings, or thresholds.
- Before any holdout label read, atom scales, weights, model/result hashes,
  selector tie priority, miss threshold `FDE > 2.0 m`, better/tie tolerance
  `1e-9 m`, non-regression slack `0.0`, bootstrap replicates `10000`, CI level
  `95%`, seeds, latency protocol, baseline wording, and claim limits are stored
  in an immutable freeze manifest.

### One-shot holdout paired evaluation

- Preflight verifies 71 label-free canonical holdout NPZs, the exact frozen
  holdout identity list, no active job, an absent evaluation output/staging
  root, fixed CAMP/DP/source/freeze/equivalence hashes, and zero split overlap.
- Execution may query each of the 71 expert futures exactly once. Labels are
  used only to derive candidate ADE/FDE arrays; raw expert futures are not
  written to the evaluation artifact. A per-record label SHA receipt is kept.
- CAMP selects the minimum affine score among the frozen physical-feasible
  mask using the frozen tie priority. No feasible candidate is an invariant
  failure, not a fallback. Candidate 0 is always evaluated as the proven
  fixed-DP deterministic/MAP baseline even if the bounded observable mask marks
  it infeasible.
- Report paired CAMP/baseline ADE, FDE, miss rate, better/tie/worse, feasible
  oracle and selection/oracle gaps, baseline-index selection count, excluded
  source rows, fallback count/policy, and selector latency p50/p95/p99/max.
- Compute percentile CI95 for paired ADE/FDE/miss deltas with both log-cluster
  resampling and scene-cluster resampling. Use 10,000 replicates from distinct
  child streams of seed `3410`.
- FDE and miss non-regression mean delta checks use slack `0.0`. They are
  diagnostics, not promotion gates. Regardless of direction, nuPlan mini is
  smoke/directional evidence only and cannot support a performance, safety, or
  CAMP-over-DP claim.
- `native_ranked_top1=false` remains frozen. All writing calls candidate 0 the
  fixed-DP deterministic/MAP baseline, never native ranked Top-1.
- OBB feasibility/exactness remains exact only within the frozen 32 dynamic +
  5 static observable source. No complete-scene, closed-loop, or safety claim.

## Task 1: Test pure data, oracle, selector, and bootstrap contracts

**Test:** `camp_core/tests/test_diffusion_planner_v18_training_evaluation.py`

1. Write failing tests for:
   - exact 14D schema and materialized-only loading;
   - holdout label absence in train/calibrate mode;
   - train-only feasible-row scaling;
   - ADE-primary/FDE-secondary/seeded-priority oracle;
   - affine masked selector and all-K fail-closed behavior;
   - deterministic log/scene bootstrap and metric aggregation.
2. Run:

   ```powershell
   $env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
   C:\Users\lenovo\anaconda3\python.exe -m pytest camp_core/tests/test_diffusion_planner_v18_training_evaluation.py -q
   ```

   Expected: RED because the runner does not exist.
3. Add only the pure helpers/constants needed to turn these tests GREEN.
4. Commit: `feat: add v18 static selector data contracts`.

## Task 2: TDD atomic train-calibrate mode

1. Add failing tests that monkeypatch the existing master and assert:
   - only 214 train rows fit scales/master;
   - 65 calibration rows are diagnostics only;
   - configuration is static/CVaR/0.9/L2 1e-4/20/1e-6/CLARABEL;
   - exact `optimal` plus convergence/gap/no-new-cut acceptance;
   - `optimal_inaccurate`, nonzero final cut, gap failure, or bad simplex leaves
     no promoted checkpoint;
   - the freeze manifest contains every preregistered threshold/hash and
     `holdout_label_reads=0`.
2. Implement immutable-source verification, train/cal loaders, ADE/FDE oracle
   derivation, call into the existing master, independent final audit, atomic
   checkpoint/freeze writing, and calibration metrics.
3. Run the focused tests and `py_compile`.
4. Commit: `feat: train and freeze v18 static 14d selector`.

## Task 3: TDD one-shot paired-evaluation mode

1. Add failing tests that assert:
   - the mode refuses an unreviewed or changed freeze/equivalence root;
   - preflight never queries holdout labels;
   - execution queries each materialized holdout identity once;
   - raw labels are not persisted;
   - records contain candidate metrics and label SHA receipts;
   - paired summaries, cluster CIs, latency, fallback/exclusion reporting, and
     no-claim/native-ranking/32+5 boundaries are present;
   - an existing output/staging root prevents a second execution.
2. Implement the smallest atomic evaluator and no-label-read preflight seam.
3. Run focused tests and `py_compile`.
4. Commit: `feat: add v18 one-shot paired evaluation`.

## Task 4: Full local verification and implementation checkpoint

Run:

```powershell
$env:PYTHONPATH='F:\camp_core-main;F:\camp_core-main\camp_core'
C:\Users\lenovo\anaconda3\python.exe -m py_compile scripts/integrations/run_diffusion_planner_dp_camp_v18_training_evaluation.py
C:\Users\lenovo\anaconda3\python.exe -m pytest camp_core/tests/test_diffusion_planner_v18_training_evaluation.py camp_core/tests/test_diffusion_planner_v18_orchestrator.py camp_core/tests/test_diffusion_planner_v18_nuplan_causal_adapter.py camp_core/tests/test_diffusion_planner_v17_causal_atom_availability.py camp_core/tests/test_diffusion_planner_v17_causal_materializer.py -q
git diff --check
```

Record the exact counts and implementation SHA in the v18 audit/current-status
pointer. Commit/push only task files, preserve unrelated work, then AutoDL
ff-only and rerun the same checks with the preserved Shapely path.

## Task 5: AutoDL train/calibration preflight, execution, and review

1. Verify source/freeze/equivalence hashes, live EOF, split counts, exact
   train/cal label presence, holdout label absence, disk, solver/version,
   no active job, and absent new output/staging roots.
2. Execute train-calibrate once into a new immutable root.
3. Independently rederive train-only scales, oracle/margins, complete-master
   convergence, checkpoint simplex, calibration aggregates, and all hashes
   without accessing holdout labels.
4. Freeze and document the exact model/scales/protocol root. Commit/push/sync.

## Task 6: AutoDL one-shot holdout evaluation and result review

1. Run the final no-label-read preflight against the frozen Task-5 root.
2. Execute the 71-label paired evaluation once. Never rerun it to tune or
   choose settings.
3. Independently recompute all reported aggregates/CIs from persisted derived
   per-record metrics without requerying expert labels.
4. Record artifacts, roots, one-shot receipt, directional results, invariant
   status, and no-claim boundary in audit/current status.
5. Commit/push/AutoDL ff-only, verify three-surface HEAD equality, and stop at
   `mini paired-evaluation result review completed` as authorized.

