# v18 nuPlan Causal Source Remediation Design

Date: 2026-07-10  
Status: approved approach; implementation pending

## Goal

Make the existing thin v18 CAMP path expose every real decision-time source
needed by the later canonical 14D materializer, without modifying fixed DP,
mutating the verified candidate corpus, accessing expert future, or creating a
second runner.

This gate repairs sources only. It does not materialize atoms or labels, train
CAMP, access holdout labels, or make a performance claim.

## Chosen approach

Modify only the existing nuPlan causal adapter and v18 orchestrator, plus their
existing tests.

1. Materialize fixed-DP's real current static-object input.
2. Return ego candidates and the matching neighbor predictions from each same
   fixed-DP call.
3. Freeze a new causal-input manifest before regeneration because static input
   changes every affected input hash.
4. Regenerate into a new immutable root and record whether each candidate can
   reach a `WHITE/unknown` controlled route segment.
5. Keep 14D fail-closed until the next atom-materialization gate derives and
   freezes the physical feasibility mask from these repaired sources.

The previous 367-record candidate root remains unchanged as historical
generation evidence and is never used as the final 14D corpus.

## Data flow

### 1. Static objects

`nuplan_causal_adapter.py` reads only boxes at the decision lidar tick. It
keeps `czone_sign`, `barrier`, `traffic_cone`, and `generic_object`, transforms
them into the ego frame, sorts deterministically by distance and token, and
encodes the nearest five as:

`[x, y, cos_yaw, sin_yaw, width, length, czone_sign, barrier, traffic_cone, generic_object]`.

This is the exact fixed-DP historical schema. Unused rows remain zero only
when fewer than five real objects exist. Dynamic categories are already
represented by neighbor history and are not duplicated as static objects.
Non-finite poses or non-positive dimensions fail closed.

### 2. Same-call predictions

The v18 orchestrator replaces the ego-only native wrapper with one CAMP-local
sampling helper that follows the same fixed-DP latent construction and decoder
guidance restoration. It still performs exactly one deterministic call and
seven stochastic calls. Each call returns the full `[1, 321, 80, 4]` decoder
prediction.

The exporter writes:

- `candidate_tensor`: `[8, 80, 4]`, ego slot 0;
- `neighbor_prediction_tensor`: `[8, 32, 80, 4]`, slots 1 through 32 from the
  same eight calls;
- `neighbor_valid_mask`: `[32]`, derived from the unpadded causal neighbor
  history;
- `candidate_signal_source_available_mask`: `[8]`, false only when that
  candidate reaches a `WHITE/unknown` controlled route segment using the
  fixed-DP red-light distance, heading, and moving thresholds.

Padded neighbor slots are never presented as real obstacles. Shape, finiteness,
K=8, DP Top-1 index 0, and guidance restoration are hard validation failures.

### 3. New manifest and immutable output

The existing orchestrator gains `--refresh_manifest_output`; no new runner is
added. It rematerializes the same frozen scene identities and split
assignments, replaces `causal_input_sha256`, and adds
`causal_source_schema_version`, `parent_manifest_sha256`,
`static_object_count`, and `neighbor_valid_count`. It writes a new manifest
atomically and refuses to overwrite any path.

Candidate regeneration accepts only that new manifest and its expected SHA.
Every NPZ and JSONL record freezes the candidate, neighbor prediction, masks,
causal input, fixed DP commit, and file hashes. The old manifest and candidate
root are read-only inputs for identity/split provenance, not overwrite targets.

### 4. Unknown signal and feasibility boundary

All 367 scenarios are regenerated. A record with any false
`candidate_signal_source_available_mask` remains preserved for audit but is
ineligible for canonical 14D training/evaluation. Unknown is never converted
to green, no-red, or zero cost.

The exporter does not invent a physical `feasible_mask`. The following
atom-materialization gate combines the saved signal-source mask with the
existing CAMP lane/collision feasibility path using the repaired same-call
neighbors and real static objects, then freezes the resulting mask before
computing `progress_shortfall`. Until that artifact exists,
`materialization_ready=false` remains authoritative.

## Error handling

- Missing or malformed real static rows: fail the record; do not substitute a
  default object.
- Full decoder prediction not exactly `[1, 321, 80, 4]` and finite: fail.
- Neighbor mask not exactly 32 booleans or a padded slot marked real: fail.
- Existing manifest/output path, DP commit drift, input-hash mismatch, or
  future field: fail before writing candidates.
- Reachable `WHITE/unknown`: write auditable evidence and mark the affected
  candidate unavailable; do not fail or silently drop the generation record.
- Any partial output remains outside the committed manifest and cannot be
  promoted by the result reviewer.

## Tests

Tests are added before production changes.

1. Adapter fixture proves exact static type encoding, nearest-five deterministic
   ordering, dynamic-category exclusion, zero padding only for true absence,
   invalid-dimension failure, and global SE(2) invariance.
2. Real mini contract proves a known decision produces nonzero real static
   input while preserving the existing future sentinel and causal hash rules.
3. Fake fixed-DP context proves eight model calls produce paired ego and
   first-32 neighbor tensors from the same outputs, preserve candidate 0 as
   deterministic Top-1, restore guidance state, and reject bad shapes/NaNs.
4. Signal-source tests cover reachable and unreachable white segments and
   verify that unknown never becomes a zero red cost.
5. Manifest tests prove scene/split identity preservation, changed causal
   hashes, atomic new output, old-root immutability, and future-field rejection.
6. Local and AutoDL run py_compile, the focused adapter/orchestrator tests, the
   v17/v18 causal suites, and `git diff --check`. A later execution gate performs
   a one-record real-model smoke before any full regeneration.

## Non-goals

- No DP source, config, weight, or checkpoint change.
- No new dependency, runner, abstraction layer, or per-gate script.
- No atom/label materialization, training, calibration, holdout access,
  evaluation, claim, promotion, deployment, or raw-data redistribution.
- No reuse or mutation of the old nuScenes 10k or current nuPlan candidate
  tensors.
