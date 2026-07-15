# v24 Native Corpus Plan

## Scope

Materialize causal fixed-DP K=8 snapshots for the corrected v24 **train split
only**. The gate may create source-derived route assets and validate run
configs. It may not read calibration/holdout outcomes, tune atoms, train a
model, or make a claim.

## Frozen input

- Corrected split plan SHA256:
  `52ea1a5c498c73be64ed9a2f4ec6093574eb534f25e7dd0f82081b683a376539`
- Corrected split manifest SHA256:
  `ba814ee3da89fc6d9b3ae1ce9a9929e38bebc6349f3871f8d105f285207bf5fa`
- Train/calibration/holdout routes: `375 / 2 / 24`
- Train seeds: `24001..24005`
- Fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Candidate count: `K=8`

## Capture contract

- Run every train route with every frozen train seed: `375 * 5 = 1875` runs.
- Run at most 64 native ticks per route-seed.
- Capture every available tick; `sample_every_ticks=1`; no thinning.
- The theoretical maximum is `120000` causal snapshots.
- Feature payload is only the existing 14D atom matrix, source-valid mask,
  and candidate-row hashes. Map/route/split/seed identity stays in receipts.
- Preserve candidate tensor immutability and candidate-0/default byte/hash
  identity before accepting a snapshot.
- Retain every attempted route-seed and failure in the denominator.

## Execution phases

1. Capability pilot: all 375 train routes with seed `24001`. This tests
   execution breadth and disk/runtime only. It cannot tune weights, atoms,
   thresholds, route choice, or failure handling.
2. Main completion: the same 375 routes with seeds `24002..24005`.
3. Independent corpus review: rehash assets/snapshots/receipts; recompute
   counts and boundary checks without generating candidates.

The phases are one frozen corpus protocol. Pilot results cannot remove,
replace, or reorder routes or seeds. Stop before duplicate launch if a unique
phase is already running. Maintain more than 10 GiB free throughout.

## Next gates

After independent corpus review: atom availability/freeze review, then
train-only learning-curve and final optimization. Calibration and holdout stay
closed during corpus generation and training.
