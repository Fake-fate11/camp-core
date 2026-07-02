# DP-CAMP Current Status

Last verified: 2026-07-02, Asia/Shanghai.

This file is the short current-state entry point. The authoritative audit for
new writes is `docs/diffusion_planner_v14_iteration_audit.md`. The v13 audit is
historical evidence and the v14 rollover source; do not keep appending current
work to v13.

## Current Authority

- The latest source reclassification audit executed after local, GitHub
  `origin/main`, and AutoDL CAMP were synchronized at
  `88fd3cac6722aedfd4ca13b41f904b4a3331c219`.
- AutoDL Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Current status is
  `public_simulator_fixed_dp_candidate_source_available_preflight_required`.
- Current next work target is
  `public_simulator_fixed_dp_candidate_generation_preflight`.

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

## Distance To Training

Training is no longer blocked on an external DP-native source `.npz` manifest.
The remaining gates are the minimum evidence needed to keep the fixed-DP
selector boundary auditable:

1. Run `public_simulator_fixed_dp_candidate_generation_preflight`.
2. Generate fixed DP candidate tensor data from the public simulator assets.
3. Run zero-overlap validation across `candidate_tensor_hash`,
   `path_signature`, `record_identity`, and `split_manifest_root`.
4. Run data-preparation and training preflight.
5. Start CAMP training only if the preflight authorizes it.

This does not authorize CAMP generation, DP modification, postprocessing,
guidance, reference blending, closed-loop outcome labels, formal seeds 11/12/13,
promotion, deployment, or safety-benefit claims.

## Cleanup Policy

Older audit files and append-only audit history are evidence, not current
instructions. Do not delete or rewrite them while current tests or audit
references still depend on them.

Generated session exports, handoff notes, local slide prompts, archives, caches,
and pytest scratch directories are local workspace noise. They are ignored by
`.gitignore` and are not part of the current DP-CAMP integration state.
