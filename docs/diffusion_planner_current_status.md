# DP-CAMP Current Status

Last verified: 2026-07-02, Asia/Shanghai.

This file is the short current-state entry point. The authoritative audit for
new writes is `docs/diffusion_planner_v14_iteration_audit.md`. The v13 audit is
historical evidence and the v14 rollover source; do not keep appending current
work to v13.

## Current Authority

- The latest source reclassification audit executed at
  `88fd3cac6722aedfd4ca13b41f904b4a3331c219`.
- The latest public simulator fixed-DP candidate generation preflight executed
  on AutoDL after local, GitHub `origin/main`, and AutoDL CAMP were
  synchronized at `1ffff597ebdc0cc598daff7db2150df2d5d898ab`.
- The latest public simulator fixed-DP candidate generation execution ran on
  AutoDL with CAMP synchronized at
  `458c66c8aeac8b9eb15ba3f06a7f87e5c9ef0740`.
- The latest public simulator fixed-DP candidate generation zero-overlap
  validation ran on AutoDL with CAMP synchronized at
  `2e17d119941b8134fc4adb7b607204d7ee95899e`.
- The latest public simulator fixed-DP candidate data-preparation preflight
  ran on AutoDL with CAMP synchronized at
  `356ce6301cd02a59dedb971f85aac8481be0a7fd`.
- AutoDL Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Current status is
  `public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_ready`.
- Current next work target is
  `public_simulator_fixed_dp_candidate_generation_training_preflight`.

## What Changed

The previous EOF treated a nonfixture DP-native source `.npz` manifest as a
prerequisite for all fixed-DP candidate generation. That was too strict for the
current CAMP objective.

TIER IV's public answer says the published DP weights were trained on internal
data, and the official training-data converter path is Autoware rosbags plus
maps through `cpp_tools/.../data_converter.cpp` and
`ros_scripts/parse_rosbag_for_directory.py`. That TIER IV rosbag/DP-native
training source is still unavailable in the current AutoDL workspace.

However, CAMP does not need to train or modify DP. The current task is to train
CAMP as a fixed-DP candidate tensor reranker/selector. For that objective, the
usable source is TIER IV's public simulator path: official v5.0 DP weights,
parameter file, public sample/Nishishinjuku maps, and declared routes. DP
generates fixed candidate tensors; CAMP only scores and selects among those
tensors.

## Available Public Simulator Inputs

Verified on AutoDL at 2026-07-02 16:48:03 CST:

- `diffusion_planner.pth`
  SHA256 `4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75`
- `diffusion_planner.param.json`
  SHA256 `ee3145b68fd1e1e44e532933dfe66cfee4384fbd637382c87ab5190c66a8e268`
- `sample-map-planning` no-ROS lanelet map
  SHA256 `a81f937c00158324c83688adc5459e90478f5b3c69a51225ad7f965b80d58036`
- `sample_map_tl_route_59_to_86.pkl`
  SHA256 `dc9b3906bace09ee9e99062ac702df1c5b2d2f4620d0a7fa14022faa9a39e4c4`
- `sample_map_route_2_to_104.pkl`
  SHA256 `489980fd79458695db68b30e91d4fcfc3efb80aca9e82ee9858a94cf2822ae35`
- `nishishinjuku_no_ros.osm`
  SHA256 `bf1ff35bfb7562b6ab15e62b1ac55770bb84352b00af5204c3601bd47f079b81`
- `nishishinjuku_release_auto_route.pkl`
  SHA256 `fef5f2be64fb9d043d4cdf46672d28cf8d3445d67bb6b2c6c1bb7570621e4337`
- `nishishinjuku_lane_change_route_7_via_8_to_1.pkl`
  SHA256 `4d03a3f99f3d39d51e53389064c83f2a942921b7ddea437c9ed3730ae0fd033b`

NuScenes is present and must not be marked missing. AutoDL exposes public
nuScenes archives under `/autodl-pub/data/nuScenes`. They are not currently
extracted or registered in CAMP data paths, and they are not the TIER IV
official rosbag-to-DP `.npz` training source. A nuScenes-to-DP adapter would be
a separate data-adapter project and is not the current gate.

## Preflight Result

Verified on AutoDL at 2026-07-02 17:22:52 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_preflight_1ffff597eb_20260702T172252CST`
- Planned execution output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST`
- Exit code: `0`
- Failed checks: `[]`
- Planned command count: `32`
- Expected records: `3200`
- Candidate output root exists: `False`
- Default-off shadow selector: `True`
- Candidate tensor provenance logging: `True`
- Executed output policy: `dp_top1`

The preflight generated a guarded runbook only. It did not execute fixed-DP
candidate generation, train CAMP, modify DP, change the online selector,
promote, deploy, or make any safety-benefit/CAMP-over-DP claim.

## Execution Result

Verified on AutoDL at 2026-07-02 18:48 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_458c66c8ae_20260702T173540CST_artifact`
- Candidate output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST`
- Exit code: `0`
- Commands started/succeeded: `32/32`
- Validation summaries: `32`
- Replay summaries: `32`
- Default-off shadow selector summaries: `32`
- Candidate tensor provenance summaries: `32`
- Seeds: `1,2,3,4`; formal seed intersection: `[]`
- Steps per command: `100`
- Routes: `4`
- Traffic-light values: `False,True`
- Closed-loop outcome collection count: `0`

This generated fixed DP candidate replay artifacts for later CAMP reranking
and validation. It did not train CAMP, generate trajectories with CAMP, modify
DP, change executed trajectory selection online, promote, deploy, or make any
safety-benefit/CAMP-over-DP claim.

## Zero-Overlap Validation Result

Verified on AutoDL at 2026-07-02 19:05 CST:

- Passing artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_2e17d11994_20260702T190542CST_complete_reference`
- Candidate output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST`
- Complete reference registry root:
  `/root/autodl-tmp/camp_dp_v13_default_off_member_source_generation_implementation_7ca9b6848b_20260702T061630CST/generated_outputs`
- Exit code: `0`
- Status:
  `public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_passed`
- Selection logs: `32`
- Records: `3200`
- Unique candidate tensor hashes: `3080`
- Unique path signatures: `32`
- Unique record identities: `3200`
- Unique split manifest roots: `4`
- Formal seed intersection: `[]`
- Tensor hash mismatches: `0`
- Executed non-Top-1 count: `0`
- Closed-loop outcome collection count: `0`
- Forbidden runtime flag count: `0`
- Overlap counts:
  `candidate_tensor_hash=0`, `path_signature=0`,
  `record_identity=0`, `split_manifest_root=0`

A prior attempt against
`/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_2e17d11994_20260702T190418CST`
correctly rejected with
`reference_training_registry_missing_or_empty` because the reference registry
root had only one candidate tensor hash and empty path, record, and split-root
registries. That rejected artifact is recorded as reference-root evidence, not
as a passing holdout claim.

## Data-Preparation Preflight Result

Verified on AutoDL at 2026-07-02 19:25 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_356ce6301c_20260702T192546CST`
- Candidate output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_execution_1ffff597eb_20260702T172252CST`
- Zero-overlap artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_zero_overlap_validation_2e17d11994_20260702T190542CST_complete_reference`
- Exit code: `0`
- Status:
  `public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_ready`
- Selection logs: `32`
- Records: `3200`
- Failed records: `0`
- Future training input contract satisfied: `True`
- Zero-overlap counts remain:
  `candidate_tensor_hash=0`, `path_signature=0`,
  `record_identity=0`, `split_manifest_root=0`
- Training input manifest:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_356ce6301c_20260702T192546CST/training_input_manifest.json`

This preflight wrote only data-preparation/training-input evidence. It did not
materialize training arrays, train CAMP, generate trajectories with CAMP,
modify DP, promote, deploy, or make any safety-benefit/CAMP-over-DP claim.

## Training Preflight Result

Verified on AutoDL at 2026-07-02 19:45 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_preflight_aff9b0533f_20260702T194544CST`
- Data-preparation artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_data_preparation_preflight_356ce6301c_20260702T192546CST`
- Planned training output dir:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_aff9b0533f_20260702T194544CST_planned`
- CAMP head:
  `aff9b0533ff63172f834dfede3836e5553bb05e0`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code: `0`
- Status:
  `public_simulator_fixed_dp_candidate_generation_training_preflight_ready`
- Selection logs: `32`
- Records: `3200`
- Clean contract failed records: `0`
- Future training input contract satisfied: `True`
- Usable feasible records: `2914`
- Dropped all-infeasible records: `286`
- Atom schema versions: `{'camp_legacy_v1_9d': 3200}`
- Selected/executed index counts: `{'0': 3200}` / `{'0': 3200}`
- Training execution authorized next: `True`
- CAMP training executed: `False`

This preflight wrote the fixed selection-log manifest and guarded training
command plan only. It did not train CAMP, run replay, generate trajectories
with CAMP, modify DP, promote, deploy, or make any safety-benefit/CAMP-over-DP
claim.

## Distance To Training

Training preflight is complete. The next gate may start CAMP training execution
from the fixed-DP selection logs and the guarded command plan produced above.

The current boundary authorizes only that training execution gate. It does not
authorize CAMP generation, DP modification, postprocessing, guidance, reference
blending, closed-loop outcome labels, formal seeds 11/12/13, promotion,
deployment, or safety-benefit claims.

current_v14_status=public_simulator_fixed_dp_candidate_generation_training_preflight_ready
next_work_target=public_simulator_fixed_dp_candidate_generation_training_execution

## Cleanup Policy

Older audit files and append-only audit history are evidence, not current
instructions. Do not delete or rewrite them while current tests or audit
references still depend on them.

Generated session exports, handoff notes, local slide prompts, archives, caches,
and pytest scratch directories are local workspace noise. They are ignored by
`.gitignore` and are not part of the current DP-CAMP integration state.
