# v18 nuPlan Physical Feasibility, Canonical 14D, and Expert Label Materialization Design

Date: 2026-07-11
Status: design approved; written spec awaiting user review

## Goal

Implement the live v18 implementation-only gate that turns the frozen nuPlan
mini K=8 candidate corpus into auditable bounded-feasibility evidence,
canonical `dp_camp_v10_14d` atom matrices, and train/calibration expert labels.
The implementation must remain causal, leave fixed DP and the candidate root
unchanged, and keep all 71 source-complete holdout labels sealed.

The current input has 367 records: 354 have complete signal sources and 13 are
already fail-closed. The 354 records split into 217 train, 66 calibration, and
71 holdout scenes. The implementation may read expert future for at most the
283 source-complete train/calibration records, and only after each record passes
the canonical eligibility checks below.

## Chosen approach

Extend the existing path; add no runner, dependency, or abstraction layer.

- `diffusion_planner_causal_atoms.py` owns exact source validation, route
  projection, OBB construction, component feasibility masks, and canonical
  atom materialization. It reuses the existing canonical availability/matrix
  validators and CAMP's existing OBB, lateral-comfort, DP-prior, and
  red-stopping primitives.
- `nuplan_causal_adapter.py` gains one read-only expert ego-future loader. This
  loader is separate from causal-input materialization and is never called for
  holdout or excluded records.
- `run_diffusion_planner_dp_camp_v18.py` gains one mutually exclusive
  materialization mode. It reads the frozen v2 manifest and candidate root,
  invokes no model, and writes a new immutable materialization root.
- The two existing v18 test modules cover the new behavior. No per-gate runner
  or duplicated pipeline is introduced.

The old `build_context_from_scene`, `compute_atom_bank_vector`, and
`compute_candidate_obstacle_clearance_diagnostics` paths are not valid for
this gate: they collapse real route values to scalars, use point or
bounding-circle clearance, and allow a zero-feasible progress fallback.

## Status-reading contract

The actual EOF of `docs/diffusion_planner_current_status.md` intentionally
contains historical v14 status. A v18 controller must never take the file's
last generic `next_work_target`. It may read only the `## Current V18 Status`
section, while `docs/diffusion_planner_v18_iteration_audit.md` EOF is the sole
authority for the current gate.

A regression test extracts the latest v18 pointer tuple from that named status
section and the pointer tuple at the v18 audit EOF, and requires exact equality
for `current_v18_status`, `current_v18_artifact_scope`,
`current_v18_artifact`, `current_v18_artifact_root_sha256`, and
`next_work_target`. Historical sections after `Current V18 Status` are ignored.

## Fixed-DP baseline semantics

Candidate 0 is the `draw(noise_scale=0)` deterministic fixed-DP output. The
historical `dp_top1_index=0` field records its array position only; it does not
prove that fixed DP produced or ranked a native K=8 list. Materializer metadata
and all subsequent v18 documents call index 0 the **fixed-DP deterministic/MAP
baseline**, never a native ranked Top-1.

Before the first paired evaluation, a separate EOF-authorized evidence gate
must run an independent fixed-DP deterministic/MAP inference on the same causal
input and prove elementwise equality or an identical tensor SHA256 against
candidate 0. Until that evidence passes, no evaluation or claim gate may infer
baseline equivalence merely from `dp_top1_index=0`. Even after equivalence is
proved, native K=8 ranking must not be claimed without separate native-ranking
evidence.

## Eligibility and fail-closed policy

Every source record remains represented in the audit `records.jsonl`, including
all masks and exclusion reasons. A record receives a canonical NPZ only when:

1. all eight saved signal-source availability values are true; and
2. at least one of the eight candidates is physically feasible.

For every candidate, the bounded observable-source feasibility mask is exactly:

`saved signal-source availability AND variable-boundary lane-corridor feasibility AND exact OBB collision-free within the frozen 32-dynamic + 5-static observable source`.

The audit output freezes the saved signal mask, lane-corridor mask,
OBB-collision-free mask, final physical mask, and per-candidate reason set.
Reason names are stable and source-specific, including at least
`signal_source_unavailable`, `lane_corridor`, and `obb_collision`.

If all eight final physical values are false, the record and complete failure
evidence remain in `records.jsonl`, but no canonical NPZ or expert label is
written. Downstream materialization, training, calibration, and evaluation
must therefore exclude it by construction. Candidate 0 is never forced true,
and progress is never computed over all K as a fallback.

When at least one candidate is feasible, the canonical NPZ keeps the full K=8
atom matrix and all masks. Later selector/training/evaluation paths may compare
only candidates allowed by the frozen physical mask; infeasible candidates are
not silently promoted or removed from the auditable fixed candidate set.

## Causal geometry and physical masks

### Route projection and lane corridor

Replay `materialize_nuplan_decision` for each identity and require its causal
input SHA256 to match the frozen manifest. Use only valid route rows in their
stored connected order. Each candidate timestep is projected onto the nearest
valid ordered route segment. The projection carries the segment arclength,
signed lateral offset, interpolated left/right boundary offsets, and the real
speed limit for that route segment.

Lane feasibility follows the existing CAMP corridor semantics, but replaces
the forbidden median half-width with the projected, side-specific boundary at
every timestep. Missing, non-finite, disconnected, or non-positive boundary or
speed sources fail the record; there is no nearby-lane route, 100 m/s limit,
current-speed desired-speed, or scalar fallback.

### Dynamic and static OBBs

For each of the eight same-call neighbor bundles, use only slots enabled by
the frozen 32-value neighbor-valid mask. Neighbor x/y and heading come from
`neighbor_prediction_tensor`; width and length come from the matching causal
`neighbor_agents_past` columns 6 and 7. Invalid headings or dimensions fail
closed instead of being clamped into a real obstacle.

Each nonzero static row uses its stored x/y, cos/sin heading, width, and length,
and is repeated over the 80-step horizon. Dynamic and static rows form one
candidate-specific `[M,80,5]` OBB tensor. Ego length, width, and wheelbase come
from the causal `ego_shape`, not hardcoded substitutes.

Collision feasibility reuses CAMP's exact OBB separating-axis branch with the
point-static path disabled. Exactness is limited to the frozen observable source
of at most 32 valid same-call dynamic slots and five current static boxes. The
clearance atom uses the existing exact OBB corner-distance primitive at every
valid ego/obstacle pair in that 32+5 source; the existing bounding-circle value
may prune obviously distant pairs but may not supply the atom value or change
collision truth.

This mask is not complete-scene physical feasibility. It cannot be interpreted
as coverage of unobserved actors/objects, realized closed-loop safety, or a
safety claim. Materialized metadata freezes
`feasibility_scope=frozen_observable_32_dynamic_plus_5_static_only` and
`closed_loop_safety_claim=false`; later evaluation and claim gates must retain
those qualifiers.

## Canonical 14D materialization

Materialize all 14 nonnegative atoms in the registered order and validate the
result with `canonical_atom_availability` and
`validate_canonical_atom_matrix`:

1. `jerk_early`, `jerk_late`, `jerk_full`, and `rms_acceleration` use the
   frozen candidate tensor and causal `dt=0.1` contract.
2. The three speed-limit atoms use the projected per-segment speed limits for
   every timestep.
3. `lane_deviation` uses projected signed offset and the matching real
   left/right boundary without the physical-corridor allowance.
4. `clearance` integrates the registered hinge over exact OBB surface distance
   within the frozen 32+5 observable source only.
5. Candidate route progress is the maximum monotone arclength reached on the
   ordered route. `progress_shortfall` uses only
   `max(progress[physical_feasible_mask])` as its reference. An empty feasible
   set excludes the record before atom construction.
6. `planned_red_light_cost` is `max(-fixed_dp_red_reward, 0)` from the frozen
   DP `compute_red_light_score_batch` formula and current route-light channels.
   The saved signal mask remains an independent eligibility gate.
7. `planned_lateral_acceleration_cost`, `red_stopping_margin_cost`, and
   `dp_prior_jerk_excess_cost` reuse the existing CAMP helpers; candidate 0 is
   only the verified fixed-DP prior reference, never a feasibility fallback.

The final matrix must be exactly `[8,14]`, finite, nonnegative, and independent
of expert future. Any missing true source rejects that record rather than
writing a zero-valued unavailable atom.

## Expert-label boundary

Only after a train or calibration record passes canonical eligibility may the
orchestrator call the expert loader. The loader opens the nuPlan DB read-only,
queries ego poses from the same scene bracketing target times 0.1 through 8.0
seconds after the decision tick, unwraps heading, linearly interpolates x/y/yaw,
and transforms the 80 poses into the decision SE(2) frame. Every target must be
bracketed; duplicate or unordered timestamps, a scene boundary, missing pose,
or required extrapolation fails closed.

The split check occurs before the label-loader call. Holdout records may receive
causal atom matrices and masks, but their output contains no expert-label field
and performs no future-pose query. Source-complete train/calibration label count
is therefore at most 283 and decreases for any all-K-infeasible record.

## Output and immutability

Materialization writes to a new output root and refuses an existing target.
The frozen candidate root, manifest, NPZ files, and hashes are checked before
and after the run and are never modified.

- `records.jsonl` has one row for every one of the 367 source records, including
  source hashes, component/final masks, reasons, split, canonical eligibility,
  label-read status, and either the canonical NPZ path/SHA256 or an explicit
  null output plus exclusion reason.
- Eligible canonical NPZ files contain the `[8,14]` atom matrix, all masks,
  schema version, source hashes, deterministic/MAP baseline metadata, bounded
  32+5 feasibility scope, and a train/calibration expert label only when
  permitted. Excluded records have no canonical NPZ.
- `summary.json` records source-complete, component-failure, all-K-infeasible,
  materialized, labelled, and holdout-sealed counts by split/log.

Writes use temporary files followed by atomic replacement. A failed partial
root remains unpromotable and cannot be mistaken for a complete artifact.

## Error handling

- DP HEAD drift, candidate/manifest/hash mutation, K other than 8, bad shape or
  dtype, non-finite values, future fields in causal input, or split mismatch:
  stop before producing a promotable output.
- Missing route speed/boundary/light data, malformed OBB source, or missing
  canonical atom input: preserve the record failure and fail closed; never
  synthesize a replacement.
- All K physically infeasible: preserve full masks/reasons, write no canonical
  NPZ or label, and continue auditing other records.
- Holdout label-loader invocation: hard failure.
- Any native-ranked-Top-1 or complete-scene/closed-loop/safety interpretation
  without its required evidence: hard contract failure.
- Existing output path: hard failure; never overwrite evidence.

## Tests and verification

Tests are written before production changes and cover:

1. section-bounded `current_status` parsing and exact latest-v18-pointer
   equality with the v18 audit EOF despite the historical v14 file tail;
2. deterministic/MAP baseline metadata, legacy `dp_top1_index` position-only
   semantics, and rejection of native-ranked-Top-1 wording/evidence inference;
3. component-mask truth tables, stable per-candidate reasons, and the all-false
   case with candidate 0 still false and no progress fallback;
4. variable speed/boundary projection, side-specific lane truth, route progress,
   and global SE(2) invariance;
5. valid-slot neighbor OBBs, repeated static OBBs, exact-within-32+5 collision
   and clearance, required scope/non-safety metadata, plus rejection of
   malformed headings/dimensions;
6. exact `[8,14]` ordering, formula fixtures, nonnegativity, feasible-only
   progress reference, candidate-0 DP-prior semantics, and future perturbation
   invariance;
7. expert interpolation on the 0.1-to-8.0-second grid, heading unwrap, no
   extrapolation, no cross-scene query, and a trap proving the loader is never
   called for holdout or excluded records;
8. all-367 audit accounting, absent NPZs for excluded records, no holdout label
   fields, atomic/no-overwrite behavior, and candidate-root hash immutability.

The implementation-only gate runs `py_compile`, focused v18 pytest modules,
the full v17/v18 causal suites, and `git diff --check` locally and on AutoDL.
It invokes the model zero times, generates no candidates, reads no holdout
labels, and performs no real corpus materialization, training, evaluation,
claim, promotion, deployment, or DP modification. A later EOF-authorized gate
will preflight and execute the immutable mini materialization.

## Non-goals

- No fixed-DP source/config/weight/checkpoint change or candidate regeneration.
- No new runner, dependency, generalized geometry framework, or scalar fallback.
- No native K=8 ranking, complete-scene feasibility, closed-loop safety, or
  safety claim from candidate index or the bounded 32+5 OBB source.
- No training, calibration search, holdout opening, evaluation, claim,
  promotion, deployment, activation, or raw-data redistribution in this gate.
- No reuse of the deleted nuScenes 10k or mutation of unrelated untracked files.
