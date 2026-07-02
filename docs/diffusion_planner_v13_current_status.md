# DP-CAMP V13 Current Status

Last verified: 2026-07-02, Asia/Shanghai.

This file is the short current-state entry point. The authoritative audit source
is still `docs/diffusion_planner_v13_iteration_audit.md`; always re-read its EOF
`current_v13_status` and `next_work_target` before executing another gate.

## Current Authority

- CAMP local, GitHub `origin/main`, and AutoDL CAMP are synchronized at
  `d1ba483c370aa2b0e888c54c6841ffbdb63f4121`.
- AutoDL Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Current EOF status is
  `fixed_dp_candidate_generation_execution_input_contract_materialization_rejected_missing_approved_source_manifest`.
- Current EOF next work target is
  `fixed_dp_candidate_generation_execution_approved_source_manifest_remediation_only`.

## What The Gates Are For

The gates are meant to prevent CAMP from silently becoming a generator,
trajectory editor, postprocessor, or closed-loop learner. For this integration,
CAMP is only allowed to rerank or select from fixed DP candidate tensors with
affine scores `score_k(w)=a_k^T w` and approved nonnegative simplex weights.

The current blocking gates are not training-quality milestones. They are data
legality and provenance checks:

- the fixed DP runner must receive an explicit input contract;
- that contract must point to approved DP-native `.npz` source files;
- later zero-overlap checks must prove the generated candidate tensors do not
  overlap training/evaluation identities by `candidate_tensor_hash`,
  `path_signature`, `record_identity`, or `split_manifest_root`.

## Why We Cannot Just Train From DP Output Yet

We can and should use DP to generate candidate tensor data, but only after the
source list is approved. Running DP directly on an unapproved or ambiguous
source list would make it impossible to prove whether later training/evaluation
records overlap, whether Full36 or formal seeds 11/12/13 leaked in, or whether
the artifact is DP-native rather than a CAMP replay/log derivative.

The current materializer found no exact approved source manifest of kind
`fresh_nonformal_fixed_dp_npz`. Therefore fixed-DP candidate generation,
data preparation, training preflight, and training execution are not currently
authorized.

## Distance To Training

Training is blocked by one real data-provenance problem, not by a useful pile of
extra planning work:

1. Produce or locate an approved `fresh_nonformal_fixed_dp_npz` manifest whose
   files are DP-native `.npz` records and satisfy the current boundary.
2. Materialize the fixed DP execution input contract and `valid_set_list`.
3. Run fixed DP candidate generation.
4. Run zero-overlap validation across all four required keys.
5. Run data-preparation and training preflight.
6. Start CAMP training only if the preflight authorizes it.

If step 1 cannot be satisfied from existing AutoDL artifacts, the next action is
not another synthetic training gate. It is an explicit source-data remediation:
provide or generate a valid DP-native nonformal source manifest within the fixed
DP and no-closed-loop boundaries.

## Cleanup Policy

Older audit files and append-only audit history are evidence, not current
instructions. Do not delete or rewrite them while current tests or EOF references
still depend on them.

Generated session exports, handoff notes, local slide prompts, archives, caches,
and pytest scratch directories are local workspace noise. They are ignored by
`.gitignore` and are not part of the current DP-CAMP integration state.
