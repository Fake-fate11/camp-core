# DP-CAMP Current Status

Last verified: 2026-07-02, Asia/Shanghai.

This file is the short current-state entry point. The authoritative audit for
new writes is `docs/diffusion_planner_v14_iteration_audit.md`. The v13 audit is
historical evidence and the v14 rollover source; do not keep appending current
work to v13.

## Current Authority

- The latest source-data availability audit executed after local, GitHub
  `origin/main`, and AutoDL CAMP were synchronized at
  `6f5bf60d5cd0bf5a3237972a97588b9830267e58`.
- AutoDL Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Current status is
  `source_data_unavailable_external_nonfixture_dp_native_npz_required`.
- Current next work target is
  `external_valid_nonfixture_dp_native_npz_source_manifest_required_before_fixed_dp_candidate_generation_execution`.

## Why The Current Gate Exists

The useful gate is not a training-quality milestone. It is a provenance gate:
CAMP may only rerank or select from fixed DP candidate tensors with affine
scores `score_k(w)=a_k^T w`; it must not generate, repair, modify, blend, or
postprocess trajectories.

We can use DP to generate training candidate tensor data, but first the DP run
needs an approved DP-native `.npz` source manifest. Without that manifest, later
training and evaluation cannot prove zero overlap across `candidate_tensor_hash`,
`path_signature`, `record_identity`, and `split_manifest_root`, and cannot prove
Full36 or formal seeds 11/12/13 were excluded.

## Distance To Training

Training is blocked by one real data-provenance problem. The AutoDL validated
scan checked 415 `.npz` files. Only one file had the required DP core keys, and
it was `Diffusion-Planner/scenario_generation/tests/test_data/fixture_scene.npz`,
so it is not a valid source for candidate generation or training. A follow-up
source-data availability audit found no raw rosbag metadata, `.db3`, `.mcap`,
or C++ training binary files that could generate valid nonfixture DP-native
source `.npz` records. The server does have maps and route pickles, but not the
raw source data required by DP's documented rosbag-to-npz path.

1. Produce or locate an approved `fresh_nonformal_fixed_dp_npz` manifest whose
   files are DP-native `.npz` records and satisfy the current boundary.
2. Materialize the fixed DP execution input contract and `valid_set_list`.
3. Run fixed DP candidate generation.
4. Run zero-overlap validation across all four required keys.
5. Run data-preparation and training preflight.
6. Start CAMP training only if the preflight authorizes it.

If step 1 cannot be satisfied from existing AutoDL artifacts, the next action is
source-data remediation, not more planning gates.

## Cleanup Policy

Older audit files and append-only audit history are evidence, not current
instructions. Do not delete or rewrite them while current tests or audit
references still depend on them.

Generated session exports, handoff notes, local slide prompts, archives, caches,
and pytest scratch directories are local workspace noise. They are ignored by
`.gitignore` and are not part of the current DP-CAMP integration state.
