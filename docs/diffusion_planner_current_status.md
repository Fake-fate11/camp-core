# DP-CAMP Current Status

Last verified: 2026-07-03, Asia/Shanghai.

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
- The latest public simulator fixed-DP candidate training preflight ran on
  AutoDL with CAMP synchronized at
  `aff9b0533ff63172f834dfede3836e5553bb05e0`.
- The latest public simulator fixed-DP candidate training execution ran on
  AutoDL with CAMP synchronized at
  `67f8062de6cd36fc9f0480223ad262b1f3f09af5`.
- The latest public simulator fixed-DP candidate training artifact static
  contract review ran on AutoDL with CAMP synchronized at
  `b075ec0854dc7f9d6522fbf6423f8ec1ae00539c`.
- The latest trained default-off shadow replay/evaluation preflight ran on
  AutoDL with CAMP synchronized at
  `adc71422af56711f8baec545259fe47626f955ef`.
- The latest trained default-off shadow replay/evaluation execution ran on
  AutoDL with CAMP synchronized at
  `72fdb3e4c880751948a47d25b0330e3818975162`.
- The latest trained default-off shadow replay/evaluation result review ran on
  AutoDL with CAMP synchronized at
  `2dd27b50b8172fb6f31df9a154e55c329f6ae2f9`.
- The latest trained default-off shadow replay/evaluation promotion-decision
  plan ran on AutoDL with CAMP synchronized at
  `4b17b353024a45b2f89d360f3e63c20ae76eac01`.
- The latest trained default-off shadow replay/evaluation promotion evidence
  package preflight ran on AutoDL with CAMP synchronized at
  `9aea47cc48aad4be26d8221e3c6c40dcf612d9d1`.
- The latest default-off shadow selector static integration contract plan ran
  on AutoDL with CAMP synchronized at
  `8fe12a0fbaa2083613cfaf83f5d0f8693423e6c1`.
- The latest default-off shadow selector implementation plan ran on AutoDL
  with CAMP synchronized at
  `55c360b8047834271a1667a2ebd3353e914358c6`.
- The latest default-off shadow selector implementation static contract review
  ran on AutoDL with CAMP synchronized at
  `5687ee3ee608651da4bab7646d8a45c1eb631b75`.
- The latest default-off shadow selector implementation unit-tests plan ran on
  AutoDL with CAMP synchronized at
  `0152e7bd81dcbbd0962b35a96df5392028b53f47`.
- The latest default-off shadow selector implementation unit-tests-only gate
  ran on AutoDL with CAMP synchronized at
  `1546633d50750358379694243b3629ac08aabe3c`.
- The latest default-off shadow selector implementation-only gate ran on
  AutoDL with CAMP synchronized at
  `98e495749e605304f1094bff62e47ab7c8317775`.
- The latest default-off shadow selector post-implementation static contract
  review ran on AutoDL with CAMP synchronized at
  `2610c4a89f20f86a4ffbe8a8f275ae56a6b85b3a`.
- The latest runtime artifact manifest plan ran on AutoDL with CAMP
  synchronized at `2456037d6f3b214f31ea5991a28732aa52e7bed4`.
- The latest runtime artifact manifest static contract review ran on AutoDL
  with CAMP synchronized at `11f1f7f853e66eec5327184479fb24ab133cb5bc`.
- The latest runtime artifact manifest materialization plan ran on AutoDL with
  CAMP synchronized at `ddce7a172512060ec990f6d01b1269888ca72024`.
- The latest runtime artifact manifest materialization static contract review
  ran on AutoDL with CAMP synchronized at
  `844e46604c460027fc0c8602903b7c365ef91d6b`.
- The latest runtime artifact manifest materialization implementation plan ran
  on AutoDL with CAMP synchronized at
  `3aeb54ec0bdf6e9c24d22ddf102b7ac4d828c790`.
- The latest runtime artifact manifest materialization implementation static
  contract review ran on AutoDL with CAMP synchronized at
  `af4064d7baacb7f073a8aded89a588233e4e80ce`.
- The latest runtime artifact manifest materializer implementation ran locally
  and on AutoDL with CAMP synchronized at
  `9b772d78233cafe508fd2f140188b3f391382d11`.
- The latest runtime artifact manifest materializer post-implementation static
  contract review ran on AutoDL with CAMP synchronized at
  `97754f14ee1f5511ba3e779520a186600a63bfca`.
- The latest runtime artifact manifest materialization ran on AutoDL with CAMP
  synchronized at `bae51947d2ce4e51937da823703181fbf095a333`.
- The latest runtime promotion evidence-package static review attempt failed
  on AutoDL with CAMP synchronized at
  `e870358da583e851b6ef3dd8033242165681c2a9` because the command pointed at
  preflight JSON/MD paths directly under the preflight artifact root while the
  actual files are under the `preflight/` subdirectory.
- AutoDL Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Current status is
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rejected`.
- Current next work target is
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rerun_requires_user_decision`.

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

## Training Execution Result

Verified on AutoDL at 2026-07-02 19:52 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_67f8062de6_20260702T195230CST`
- Source preflight artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_preflight_aff9b0533f_20260702T194544CST`
- Training output dir:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_aff9b0533f_20260702T194544CST_planned`
- CAMP head:
  `67f8062de6cd36fc9f0480223ad262b1f3f09af5`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code: `0`
- Training type:
  `diffusion_planner_static_candidate_preference`
- Label source:
  `dp_reward`
- Records used / dropped all-infeasible:
  `2914 / 286`
- Candidates / atoms:
  `8 / 9`
- Atom schema:
  `camp_legacy_v1_9d`
- Weights sum / min / max:
  `0.9999999999999999 / 0.059347218886831296 / 0.1735927811151367`
- First / final logged loss:
  `2.0419425862497667 / 2.036233432086801`
- Output files:
  `offline_weights_dp_static.npy`, `atom_scales_dp_static.json`,
  `training_summary.json`

This is a training artifact only. It is not a deployable checkpoint claim, not
selector promotion, and not evidence of safety benefit or CAMP superiority over
DP Top-1.

## Training Artifact Static Contract Review

Verified on AutoDL at 2026-07-02 20:02 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_b075ec0854_20260702T200227CST`
- Training execution artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_67f8062de6_20260702T195230CST`
- Current CAMP head:
  `b075ec0854dc7f9d6522fbf6423f8ec1ae00539c`
- Training artifact CAMP head:
  `67f8062de6cd36fc9f0480223ad262b1f3f09af5`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code: `0`
- Status:
  `public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_passed`
- Failed checks:
  `[]`
- Weights sum / min / max:
  `1.0 / 0.059347218886831296 / 0.1735927811151367`
- Weights nonnegative:
  `True`
- Weight file matches summary:
  `True`
- Atom scales positive finite:
  `True`
- Authorized next:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight`

This review did not train, replay, generate candidates, modify DP, promote,
deploy, or make safety-benefit/CAMP-over-DP claims.

## Trained Shadow Replay/Evaluation Preflight

Verified on AutoDL at 2026-07-02 20:30 CST:

- Passing artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_adc71422af_20260702T203050CST`
- First failed import-path artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_bedc10752b_20260702T202857CST`
- Failure class:
  `script_import_path_missing`, fixed by
  `adc71422af56711f8baec545259fe47626f955ef`
- Training execution artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_execution_67f8062de6_20260702T195230CST`
- Training artifact static contract review:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_fixed_dp_candidate_generation_training_artifact_static_contract_review_b075ec0854_20260702T200227CST`
- Runtime manifest:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_adc71422af_20260702T203050CST/runtime/dp_camp_v14_trained_default_off_shadow_runtime_manifest.json`
- Planned replay output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_adc71422af_20260702T203050CST`
- Exit code: `0`
- Status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_preflight_ready`
- Failed checks: `[]`
- Planned command count / expected records:
  `32 / 3200`
- Runtime manifest default-off / fail-closed:
  `True / True`
- Executed output policy:
  `dp_top1`
- Weights sum / min / max:
  `1.0 / 0.059347218886831296 / 0.1735927811151367`
- Weights SHA256:
  `5bfe692465c0e0cdbf2fb937737674e53b3f41a31ea932a65f65a6321f4c0dde`
- Atom scales SHA256:
  `2239fb09e2231405dbc58b1a79486ff3f3c111a9bab96c24d88e6832f2325b8b`
- Closed-loop outcome command flag present:
  `False`

This preflight wrote only a guarded runbook and runtime manifest for a future
trained default-off shadow replay/evaluation execution. It did not run replay,
generate candidates, train CAMP, modify DP, change executed trajectory
selection, promote, deploy, or make safety-benefit/CAMP-over-DP claims.

## Trained Shadow Replay/Evaluation Execution

Verified on AutoDL at 2026-07-02 21:54 CST:

- Execution artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact_72fdb3e4c8_20260702T204752CST`
- Refreshed current-head preflight:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_preflight_refresh_72fdb3e4c8_20260702T204702CST`
- Stale runbook failure artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact_5b23ae8f25_20260702T204229CST`
- Stale runbook failure class / exit:
  `stale_runbook_camp_head_mismatch / 41`
- CAMP head:
  `72fdb3e4c880751948a47d25b0330e3818975162`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code: `0`
- Status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_execution_passed`
- Selection logs / records:
  `32 / 3200`
- Validation summaries / replay summaries:
  `32 / 32`
- Records per log:
  `100`
- Shadow selected non-Top-1 records:
  `2832`
- Executed DP Top-1 records:
  `3200`
- `selected_index` matches executed index records:
  `3200`
- Selection-effect / online-selector-change counts:
  `0 / 0`
- Reference-blend steps, closed-loop outcome weights, and postselection active
  counts:
  `0 / 0 / 0`
- Formal seed path count:
  `0`
- CAMP candidate tensor provenance schema:
  `dp_native_candidate_tensor_provenance_payload_v1`
- Forbidden CAMP provenance effects:
  `[]`
- Execution SHA256SUMS SHA256:
  `5bb414a4a0cc8d3013ade90be55efa9608ced26c7a0ca6c9056d722a137bfeca`

This execution ran the guarded default-off shadow replay/evaluation. CAMP
computed shadow scores and shadow selected indices over fixed DP candidate
tensors, but the online/executed trajectory remained DP Top-1 for every record.
This is not selector promotion, deployment, a deployable checkpoint claim,
safety-benefit evidence, or a CAMP-over-DP claim.

## Trained Shadow Replay/Evaluation Result Review

Verified on AutoDL at 2026-07-02 22:24 CST:

- Passing artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_2dd27b50b8_20260702T222425CST`
- First rejected artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_result_review_3642c74a10_20260702T222136CST`
- First rejected failure class:
  `head_or_fixed_dp_contract_failure`
- First rejected failed checks:
  `artifact_camp_head_matches_current`,
  `artifact_camp_origin_matches_current`
- Remediation commit:
  `2dd27b50b8172fb6f31df9a154e55c329f6ae2f9`
- Source execution artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_artifact_72fdb3e4c8_20260702T204752CST`
- Source evaluation output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_execution_72fdb3e4c8_20260702T204702CST`
- Exit code: `0`
- Failed checks: `[]`
- Selection logs / records:
  `32 / 3200`
- Records per log:
  `100`
- Validation summaries / replay summaries:
  `32 / 32`
- Routes / seeds:
  `16 / 4`
- Shadow selected non-Top-1 records:
  `2832`
- Executed DP Top-1 records:
  `3200`
- `selected_index` matches executed index records:
  `3200`
- Selection-effect / online-selector-change counts:
  `0 / 0`
- Reference-blend steps, closed-loop outcome weights, postselection active,
  and formal seed path counts:
  `0 / 0 / 0 / 0`
- Atom schema / candidate count / weights sum:
  `camp_legacy_v1_9d / 8 / 1.0`
- CAMP candidate tensor provenance schema:
  `dp_native_candidate_tensor_provenance_payload_v1`
- Forbidden CAMP provenance effects:
  `0`
- Result review JSON SHA256:
  `41484dde58c3e89b4f2a9a644f3c8f1700e3f198f76e6f20fae8a7c254a17e78`
- Artifact SHA256SUMS SHA256:
  `9ba54de606c2aff79a2a85cb5015af3ef59468b963492dc3f2e763bbe930f3fe`

The result review is read-only. It did not run replay, generate candidates,
train CAMP, modify DP, change executed trajectory selection, promote, deploy,
or make safety-benefit/CAMP-over-DP claims. It authorizes only a future
promotion-decision plan gate, not promotion itself.

## Trained Shadow Replay/Evaluation Promotion-Decision Plan

Verified on AutoDL at 2026-07-02 23:14 CST:

- Passing artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_4b17b35302_20260702T231416CST`
- First rejected artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_4b17b35302_20260702T231157CST`
- First rejected failure class:
  `python_alias_missing_in_runbook`
- Source result-review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_result_review_passed`
- Source result-review authorized work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_user_authorization`
- CAMP head:
  `4b17b353024a45b2f89d360f3e63c20ae76eac01`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Plan status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_decision_plan_ready`
- Failed checks:
  `[]`
- Recommendation:
  `do_not_promote_from_current_evidence_alone`
- Immediate action:
  `build_promotion_evidence_package_preflight_only`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_only`
- Evidence-package preflight authorized:
  `True`
- Source selection logs / records:
  `32 / 3200`
- Source training records / dropped all-infeasible:
  `2914 / 286`
- Shadow selected non-Top-1 / executed DP Top-1 records:
  `2832 / 3200`
- Selection-effect / online-selector-change counts:
  `0 / 0`
- Reference-blend, closed-loop outcome, formal seed, and forbidden CAMP
  provenance counts:
  `0 / 0 / 0 / 0`
- First loss / last loss:
  `2.0419425862497667 / 2.036233432086801`
- Oracle match rate / feasible candidate rate:
  `0.22786547700754975 / 0.9781228551818806`
- Plan JSON SHA256:
  `c33a5c47b532fb22d73d82e47a6c80094a308e07837a5e96f560dd85b7bcdd77`
- Artifact SHA256SUMS SHA256:
  `18a3059edc457835635e51f4fc21228fdf19b2bce5db607d8fe832df7ab79bb1`

This gate is planning-only. It does not promote atoms or selectors, deploy a
checkpoint, train CAMP, run replay, generate candidates, modify DP, change
online selection, or authorize safety/CAMP-over-DP claims. The conservative
decision is that the current evidence is sufficient to plan the evidence
package preflight, but not sufficient for promotion.

## Trained Shadow Replay/Evaluation Promotion Evidence-Package Preflight

Verified on AutoDL at 2026-07-02 23:47 CST:

- Passing artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_9aea47cc48_20260702T234739CST`
- First rejected artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_2aa96d0f16_20260702T234535CST`
- First rejected failure class:
  `source_training_contract_failure`
- First rejected failed check:
  `training_summary_contract`
- CAMP head:
  `9aea47cc48aad4be26d8221e3c6c40dcf612d9d1`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Preflight status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_promotion_evidence_package_preflight_ready`
- Failed checks:
  `[]`
- Artifact manifest entries:
  `7`
- Source selection logs / records:
  `32 / 3200`
- Source training records / dropped all-infeasible:
  `2914 / 286`
- Shadow selected non-Top-1 / executed DP Top-1 records:
  `2832 / 3200`
- Static integration contract status:
  `preflight_ready_contract_pinned`
- Future default-off shadow selector wiring status:
  `future_static_contract_plan_required_before_implementation`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_only`
- Evidence preflight JSON SHA256:
  `dc4e5bcd3ef41380c91a1911510821ea8fecbdc37a4ac2f9f319c5ee73b2053f`
- Artifact SHA256SUMS SHA256:
  `0c874c1b4b5c7814fc67933dcb1af72504e30ceacd3e3168afbfd96457fbf10d`

This preflight is read-only. It only packages and checks existing promotion
plan, result review, training review, training summary, weights, atom scales,
and shadow execution hashes. It does not promote, deploy, train CAMP, run
replay, generate candidates, modify DP, change online selection, or authorize
safety/CAMP-over-DP claims.

## Default-Off Shadow Selector Static Integration Contract Plan

Verified on AutoDL at 2026-07-02 23:59 CST:

- Passing artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_8fe12a0fba_20260702T235910CST`
- CAMP head:
  `8fe12a0fbaa2083613cfaf83f5d0f8693423e6c1`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Plan status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_ready`
- Failed checks:
  `[]`
- Runtime effect:
  `must_log_shadow_selected_index_without_changing_dp_top1_output`
- Candidate source:
  `fixed current-tick DP candidate tensor before CAMP scoring`
- Selection rule:
  `argmin_k score_k(w) over finite feasible candidate rows`
- Implementation plan authorized:
  `True`
- Implementation authorized:
  `False`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only`
- Static contract plan JSON SHA256:
  `2389f0bf1d2a08e2453e1944c940108fa8997a123fa65e2981397f34d5775951`
- Artifact SHA256SUMS SHA256:
  `f5e52d9645cf3b8e1505c3ab63fdda0f5da47c86361a4de504e53007d0d13697`

This gate is plan-only. It inspected the evidence-package preflight and source
surfaces for CAMP selection, replay runner fail-closed behavior, and Benders
affine atom tests. It did not implement selector wiring, train CAMP, replay,
generate candidates, modify DP, promote, deploy, or authorize safety/CAMP-over-DP
claims.

## Default-Off Shadow Selector Implementation Plan

Verified on AutoDL at 2026-07-03 00:15 CST:

- Passing artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_plan_55c360b804_20260703T001526CST`
- First rejected artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_plan_55c360b804_20260703T001423CST`
- First rejected failure class:
  `source_static_contract_plan_failure`
- Source static contract plan:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_static_integration_contract_plan_8fe12a0fba_20260702T235910CST/report/default_off_shadow_selector_static_integration_contract_plan.json`
- CAMP head:
  `55c360b8047834271a1667a2ebd3353e914358c6`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Plan status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_ready`
- Failed checks:
  `[]`
- Runtime effect:
  `log shadow_selected_index while executed output remains DP Top-1`
- Candidate source:
  `fixed current-tick DP candidate tensor before CAMP scoring`
- Selection rule:
  `shadow_selected_index = argmin_k score_k(w)`
- Implementation static contract review authorized:
  `True`
- Implementation authorized:
  `False`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_only`
- Implementation plan JSON SHA256:
  `553c09c55ae87cb65dcfce6e0497a0b1773b1b68e4c574b34f93ff03e15df398`
- Artifact SHA256SUMS SHA256:
  `08fdb3c7eae8d89708ae229151248c24724eb1b283fe7cef2a4c3b12360ae88e`

This gate is plan-only. It did not implement selector wiring, train CAMP, run
replay, generate candidates, modify DP, promote, deploy, or authorize
safety/CAMP-over-DP claims. The next gate is static contract review only.

## Default-Off Shadow Selector Implementation Static Contract Review

Verified on AutoDL at 2026-07-03 00:29 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_5687ee3ee6_20260703T002900CST`
- Source implementation plan:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_plan_55c360b804_20260703T001526CST/default_off_shadow_selector_implementation_plan.json`
- CAMP head:
  `5687ee3ee608651da4bab7646d8a45c1eb631b75`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_static_contract_review_passed`
- Failed checks:
  `[]`
- Runtime effect:
  `executed output remains DP Top-1 during shadow phase`
- Candidate operation:
  `fixed DP candidate reranking only`
- Selection rule:
  `shadow_selected_index = argmin_k score_k(w)`
- Unit-tests plan authorized:
  `True`
- Implementation authorized:
  `False`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_only`
- Static contract review JSON SHA256:
  `8eceaef8bf837e9450acda594c37b8e2021e6a92f02d338336c5887c2f2342ef`
- Artifact SHA256SUMS SHA256:
  `d0078e0a716fb1a66425837ec5885d1482ba9504f37ced24477f413c662b1b24`

This gate is review-only. It did not implement selector wiring, train CAMP, run
replay, generate candidates, modify DP, promote, deploy, or authorize
safety/CAMP-over-DP claims. The next gate is unit-test planning only.

## Default-Off Shadow Selector Implementation Unit-Tests Plan

Verified on AutoDL at 2026-07-03 00:39 CST:

- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_plan_0152e7bd81_20260703T003918CST`
- Source static contract review:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_static_contract_review_5687ee3ee6_20260703T002900CST/default_off_shadow_selector_implementation_static_contract_review.json`
- CAMP head:
  `0152e7bd81dcbbd0962b35a96df5392028b53f47`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Plan status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_plan_ready`
- Failed checks:
  `[]`
- Target test file:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py`
- Test groups:
  `default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract`
- Unit-tests-only authorized:
  `True`
- Implementation authorized:
  `False`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_only`
- Unit-tests plan JSON SHA256:
  `499c4da63d66818ac7ab3a16bcd5bea8af2086cc64df10dab759c2c0d451ee44`
- Artifact SHA256SUMS SHA256:
  `cebaea57596b233271e857e35a4908de07c80b734b06111c8460b0a9ad897194`

This gate is plan-only. It did not write unit tests, implement selector wiring,
train CAMP, run replay, generate candidates, modify DP, promote, deploy, or
authorize safety/CAMP-over-DP claims. The next gate is unit-tests-only.

## Default-Off Shadow Selector Implementation Unit Tests

Verified on AutoDL at 2026-07-03 00:59 CST:

- Test file:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py`
- CAMP head:
  `1546633d50750358379694243b3629ac08aabe3c`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Successful artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_rerun_dp312_1546633d50_20260703T005948CST`
- Successful exit code:
  `0`
- Local pytest:
  `20 passed`
- AutoDL pytest:
  `20 passed`
- Unit-tests status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_unit_tests_passed`
- Test groups:
  `default_off_disabled_contract,immutable_artifact_hash_contract,fixed_candidate_affine_score_contract,dp_top1_shadow_runtime_contract,no_candidate_mutation_contract,benders_and_seed_boundary_contract`
- First failed artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_1546633d50_20260703T005637CST`
- First failure class:
  `python312_alias_missing`
- Second failed artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests_rerun_1546633d50_20260703T005806CST`
- Second failure class:
  `base_python_pytest_missing`
- Successful artifact SHA256SUMS SHA256:
  `1ebe8b8e528e3fc8861f94cda963465f4a95bd365ad72d4bab57a488654eed47`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_only_after_explicit_user_authorization`

This gate is unit-tests-only. It added focused tests for the default-off shadow
selector contract and verified them locally and on AutoDL. It did not implement
selector wiring, train CAMP, run replay, generate candidates, modify DP,
promote, deploy, or authorize safety/CAMP-over-DP claims. The next gate is
implementation-only and requires explicit authorization.

## Default-Off Shadow Selector Implementation

Verified on AutoDL at 2026-07-03 01:19 CST:

- Implementation commit:
  `98e495749e605304f1094bff62e47ab7c8317775`
- Source file:
  `scripts/integrations/run_diffusion_planner_camp_replay.py`
- Test file:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_implementation_unit_tests.py`
- Runtime schema:
  `dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1`
- Source scope:
  `public_simulator_fixed_dp_candidate_tensor`
- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_98e495749e_20260703T011920CST`
- CAMP head:
  `98e495749e605304f1094bff62e47ab7c8317775`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `42 passed`
- AutoDL pytest:
  `42 passed`
- Artifact SHA256SUMS SHA256:
  `d0be444a9e3454545ce0cacbf0828007d33ae4dfaff8b8d0aab5cae77e9ae3ea`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_only`

This gate implemented only the default-off shadow selector runtime schema/source
scope pinning already covered by the unit tests. It keeps the selector
default-off and fail-closed: executed output remains `dp_top1`, CAMP only logs
`shadow_selected_index`, and scoring remains affine as `score_k(w)=a_k^T w`.
It did not train CAMP, run replay, generate candidates, modify DP, promote,
deploy, or authorize safety/CAMP-over-DP claims.

## Default-Off Shadow Selector Post-Implementation Static Review

Verified on AutoDL at 2026-07-03 01:35 CST:

- Review commit:
  `2610c4a89f20f86a4ffbe8a8f275ae56a6b85b3a`
- Review script:
  `scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_post_implementation_static_contract.py`
- Review test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_post_implementation_static_contract.py`
- Source implementation artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_implementation_98e495749e_20260703T011920CST/result.json`
- Review artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_post_implementation_static_contract_review_2610c4a89f_20260703T013539CST`
- CAMP head:
  `2610c4a89f20f86a4ffbe8a8f275ae56a6b85b3a`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `44 passed`
- AutoDL pytest:
  `44 passed`
- Review decision:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_post_implementation_static_contract_review_passed`
- Artifact SHA256SUMS SHA256:
  `706ce66d9f9bfa5a9dc75c2053d3dd0689e304e508b64240346d9f13b87da705`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_only`

This gate is static-review-only. It verified the v14 runtime schema/source
scope, default-off fail-closed behavior, immutable artifact hash boundary,
fixed-candidate reranking contract, affine score contract, DP Top-1 runtime
output contract, and no-promotion/no-claims boundary. It did not train CAMP,
run replay, generate candidates, modify DP, promote, deploy, or authorize
safety/CAMP-over-DP claims.

## Default-Off Shadow Selector Runtime Artifact Manifest Plan

Verified on AutoDL at 2026-07-03 01:58 CST:

- Plan commit:
  `2456037d6f3b214f31ea5991a28732aa52e7bed4`
- Plan script:
  `scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.py`
- Plan test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan.py`
- Artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST`
- CAMP head:
  `2456037d6f3b214f31ea5991a28732aa52e7bed4`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `8 passed`
- AutoDL pytest:
  `8 passed`
- Plan status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_plan_ready`
- Plan checks:
  `121`
- Failed checks:
  `[]`
- Runtime schema:
  `dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1`
- Source scope:
  `public_simulator_fixed_dp_candidate_tensor`
- Required runtime entries:
  `atom_scales,static_weights`
- Required evidence entries:
  `training_summary,post_static_review,implementation_result,replay_runner`
- Training summary SHA256:
  `783684d1fd7038587efc43a47e4ca4f88eb392267187eb4e0042ed346b9fc6a0`
- Atom scales SHA256:
  `2239fb09e2231405dbc58b1a79486ff3f3c111a9bab96c24d88e6832f2325b8b`
- Static weights SHA256:
  `5bfe692465c0e0cdbf2fb937737674e53b3f41a31ea932a65f65a6321f4c0dde`
- Report JSON SHA256:
  `be3734e2d897c85c797ad6cb03ccf3f7af6c88202a0db26954dc9e4e1f984b74`
- Artifact SHA256SUMS SHA256:
  `321998d25ec45bfee32890636a4acae76a0b7ce342cae17ca7efd55f7d1e995b`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_only`

This gate is plan-only. It writes only the plan artifact and future static
review requirements for a default-off runtime artifact manifest. It did not
write the future runtime manifest, run replay, train CAMP, generate candidates,
modify DP, promote atoms or selectors, deploy, or authorize safety/CAMP-over-DP
claims.

## Default-Off Shadow Selector Runtime Artifact Manifest Static Review

Verified on AutoDL at 2026-07-03 02:15 CST:

- Static review commit:
  `11f1f7f853e66eec5327184479fb24ab133cb5bc`
- Static review script:
  `scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract.py`
- Static review test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract.py`
- Source plan artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/report/default_off_shadow_selector_runtime_artifact_manifest_plan.json`
- Successful artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_11f1f7f853_20260703T021546CST`
- CAMP head:
  `11f1f7f853e66eec5327184479fb24ab133cb5bc`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `9 passed`
- AutoDL pytest:
  `9 passed`
- Review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_passed`
- Review checks:
  `110`
- Failed checks:
  `[]`
- First failed artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_e8fd20270e_20260703T021331CST`
- First failure class:
  `runtime_artifact_manifest_static_contract_failure`
- First failed checks:
  `script_v14_plan_schema,script_authorizes_static_review_only`
- Successful report JSON SHA256:
  `e9bbd2f62de4bbc06f740bef784c3fec5f7cf768c9878ddb5da3ad12b3e4d7cb`
- Successful artifact SHA256SUMS SHA256:
  `554384a654840f5bfcc5ea4d9b4d6e6ba550a0b314e5daccd64cd7238bc05fb6`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_only`

This review is static only. It verified the source plan is not a runtime
manifest, the planned manifest path remains unmaterialized, the future runtime
entries are `atom_scales` and `static_weights`, the v14 runtime schema/source
scope are pinned, and the default-off shadow selector remains fail-closed with
executed output fixed to DP Top-1. It did not materialize the runtime manifest,
run replay, train CAMP, generate candidates, modify DP, promote, deploy, or
authorize safety/CAMP-over-DP claims.

## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Plan

Verified on AutoDL at 2026-07-03 02:32 CST:

- Plan support commit:
  `ddce7a172512060ec990f6d01b1269888ca72024`
- Plan script:
  `scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization.py`
- Plan test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan.py`
- Source static-review artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_static_contract_review_11f1f7f853_20260703T021546CST/report/runtime_artifact_manifest_static_contract_review.json`
- Source runtime-manifest plan artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/report/default_off_shadow_selector_runtime_artifact_manifest_plan.json`
- Successful artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ddce7a1725_20260703T023207CST`
- CAMP head:
  `ddce7a172512060ec990f6d01b1269888ca72024`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `7 passed`
- AutoDL pytest:
  `7 passed`
- Plan status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ready`
- Plan checks:
  `109`
- Failed checks:
  `[]`
- Planned runtime manifest exists after this gate:
  `False`
- Successful report JSON SHA256:
  `bac353cb142af137a03e3fa96c21892f57ef3cfe3a3f280d311b1e80a504693d`
- Successful artifact SHA256SUMS SHA256:
  `23179ca81f45cfd997af9953b8a1d129b458e324c38d6ac23fe720395576aa2e`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_only`

This gate is plan-only. It planned the future runtime manifest content and
static-review requirements, but did not write the runtime manifest, run replay,
train CAMP, generate candidates, modify DP, promote, deploy, or authorize
safety/CAMP-over-DP claims. The planned runtime manifest remains unmaterialized.

## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Static Review

Verified on AutoDL at 2026-07-03 02:43 CST:

- Static review support commit:
  `844e46604c460027fc0c8602903b7c365ef91d6b`
- Static review script:
  `scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract.py`
- Static review test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract.py`
- Source materialization plan artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ddce7a1725_20260703T023207CST/report/runtime_artifact_manifest_materialization_plan.json`
- Successful artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_844e46604c_20260703T024304CST`
- CAMP head:
  `844e46604c460027fc0c8602903b7c365ef91d6b`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `8 passed`
- AutoDL pytest:
  `8 passed`
- Review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_passed`
- Review checks:
  `114`
- Failed checks:
  `[]`
- Planned runtime manifest exists after this gate:
  `False`
- Successful report JSON SHA256:
  `aa3b096059d671cd42d888f7929114800fecd8c50b65af319dbb6e28b52b7134`
- Successful artifact SHA256SUMS SHA256:
  `b3a34cfbaaedd8493c3a91f550d358e52a8190ff67065217bfe2ff757ee6f746`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_only`

This review is static only. It verified the materialization plan is not a
runtime manifest, no runtime manifest was written, future entries are
`atom_scales` and `static_weights`, the v14 runtime schema/source scope remain
pinned, and default-off fail-closed execution remains DP Top-1. It did not
materialize the runtime manifest, run replay, train CAMP, generate candidates,
modify DP, promote, deploy, or authorize safety/CAMP-over-DP claims.

## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Implementation Plan

Verified on AutoDL at 2026-07-03 03:01 CST:

- Implementation-plan support commit:
  `3aeb54ec0bdf6e9c24d22ddf102b7ac4d828c790`
- Implementation-plan script:
  `scripts/integrations/plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation.py`
- Implementation-plan test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan.py`
- Source materialization static-review artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_static_contract_review_844e46604c_20260703T024304CST/report/runtime_artifact_manifest_materialization_static_contract_review.json`
- Source materialization plan artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_plan_ddce7a1725_20260703T023207CST/report/runtime_artifact_manifest_materialization_plan.json`
- Successful artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_3aeb54ec0b_20260703T030149CST`
- CAMP head:
  `3aeb54ec0bdf6e9c24d22ddf102b7ac4d828c790`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `8 passed`
- AutoDL pytest:
  `8 passed`
- Plan status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_ready`
- Plan checks:
  `119`
- Failed checks:
  `[]`
- Planned runtime manifest exists after this gate:
  `False`
- Successful report JSON SHA256:
  `8b15be1ccd3be99f0924e71d5ed3befdd57a3416e6ebaa00a1f8986aee68ff59`
- Successful artifact SHA256SUMS SHA256:
  `391438fb49d63de0139d85bbb9d7cff1ffbeb62fad52dd735ff60e59dd4e51b0`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_only`

This gate is plan-only. It planned a future materializer contract that writes
exactly one runtime manifest at the planned path using a same-directory temp
file plus atomic replace, after verifying the fixed DP head and the
`atom_scales`/`static_weights` file hashes. It did not write the runtime
manifest, run replay, train CAMP, generate candidates, modify DP, promote,
deploy, or authorize safety/CAMP-over-DP claims.

## Default-Off Shadow Selector Runtime Artifact Manifest Materialization Implementation Static Review

Verified on AutoDL at 2026-07-03 03:20 CST:

- Static review support commit:
  `af4064d7baacb7f073a8aded89a588233e4e80ce`
- First failed artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_1fcbfe3680_20260703T031832CST`
- First failed checks:
  `script_implementation_plan_schema`, `script_authorizes_static_review_only`
- First failed failure class:
  `source_surface_contract_failure`
- Successful artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_af4064d7ba_20260703T032021CST`
- CAMP head:
  `af4064d7baacb7f073a8aded89a588233e4e80ce`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `10 passed`
- AutoDL pytest:
  `10 passed`
- Review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_static_contract_review_passed`
- Review checks:
  `109`
- Failed checks:
  `[]`
- Successful report JSON SHA256:
  `30ba6e44ec75dacf5fb1fea5ee096bc5f333c1f6087d01cfd0a48e58e273c775`
- Successful artifact SHA256SUMS SHA256:
  `6077c3aa952e4b2a15f01d89330fd018eb2058b19e52aeb29bd4478977129798`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_only`

The first static review failed because source-surface checks expected full
long constants in contiguous source text while the implementation-plan script
used adjacent string literals. The remediation narrowed those checks to the
contract suffixes, then reran the gate successfully. This review did not write
or materialize the runtime manifest, run replay, train CAMP, generate
candidates, modify DP, promote, deploy, or authorize safety/CAMP-over-DP
claims.

## Default-Off Shadow Selector Runtime Artifact Manifest Materializer Implementation

Verified locally and on AutoDL at 2026-07-03 CST:

- Implementation commit:
  `9b772d78233cafe508fd2f140188b3f391382d11`
- Implementation status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_implementation_complete`
- Materializer script:
  `scripts/integrations/build_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.py`
- Materializer script SHA256:
  `9219b03efe692b00eb92ed7d9af9ceaa372937ead1afbe957a9edc48e855ae89`
- Materializer test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer.py`
- Materializer test SHA256:
  `95b7e1dc6ceffc9c4093facc4f73f807b635c37d1e07e0599383334802e22af7`
- Local py_compile:
  `0`
- Local pytest:
  `12 passed`
- AutoDL py312 py_compile:
  `0`
- AutoDL camp-env pytest:
  `12 passed`
- AutoDL CAMP head and origin/main:
  `9b772d78233cafe508fd2f140188b3f391382d11`
- AutoDL DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`

The materializer is default-off before reading missing inputs, fail-closed
without output, verifies the implementation-plan SHA256, verifies the fixed DP
head, verifies that the output path equals the plan, verifies the
`atom_scales` and `static_weights` file hashes, writes exactly one runtime
manifest only when explicitly enabled, and uses a same-directory temp file plus
atomic replace. The implementation and tests do not run replay, train CAMP,
generate candidates, touch DP source files, change online selector behavior, or
materialize the real planned runtime manifest.

## Default-Off Shadow Selector Runtime Artifact Manifest Materializer Post-Implementation Static Review

Verified on AutoDL at 2026-07-03 03:58 CST:

- Static review initial support commit:
  `169e5d10c41f50882c3990b336c79a566739a875`
- Static review remediation commit:
  `97754f14ee1f5511ba3e779520a186600a63bfca`
- Static review script:
  `scripts/integrations/review_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract.py`
- Static review script SHA256:
  `018a5545ee01c64cf025e5f94976b25558b362c428cef07975f0598dffb6bf3b`
- Static review test:
  `camp_core/tests/test_diffusion_planner_dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract.py`
- Static review test SHA256:
  `7d30a023ee0d3f2fed83557a8f1539046bf99a5fe20b89ec9464472e3bb0c35b`
- First failed artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_169e5d10c4_20260703T035722CST`
- First failed checks:
  `materializer_schema_constant`, `materializer_source_plan_schema`
- First failed report JSON SHA256:
  `556f1f1dbed1f8ba45f049a5f53b030ce2bf061d7e297dbee024693273d90ca4`
- Successful artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_97754f14ee_20260703T035849CST`
- CAMP head and origin/main:
  `97754f14ee1f5511ba3e779520a186600a63bfca`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Exit code:
  `0`
- Local pytest:
  `10 passed`
- AutoDL pytest:
  `10 passed`
- Review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_passed`
- Authorized current work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materializer_post_implementation_static_contract_review_only`
- Review checks:
  `121`
- Failed checks:
  `[]`
- Planned runtime manifest exists:
  `False`
- Successful report JSON SHA256:
  `5c6056f4f25574ec44de05eac017022f4dcc3827daee6cd69695f14956835886`
- Successful report MD SHA256:
  `1e19b1043b2c14e1e9a42ce199f66922494da71fcb6fc6f3fba167998b9f7625`
- Successful artifact SHA256SUMS SHA256:
  `72d87c7b27d160a2ffbb03b02c4089fab4ec39783c5e60f3221f122f4e66a68f`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialization_only`

The first static review failed because two source-surface checks expected full
long schema constants in contiguous source text, while the materializer uses
adjacent string literals. The remediation changed those checks to contract
suffix checks and reran the same gate successfully.

This review was static only. It did not materialize the real runtime manifest,
run replay, train CAMP, generate candidates, modify DP, promote, deploy, or
authorize runtime execution or safety/CAMP-over-DP claims. It authorizes only
the next runtime artifact manifest materialization gate.

## Default-Off Shadow Selector Runtime Artifact Manifest Materialization

Verified on AutoDL at 2026-07-03 04:05 CST:

- Materialization artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_bae51947d2_20260703T040546CST`
- CAMP head and origin/main:
  `bae51947d2ce4e51937da823703181fbf095a333`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Source implementation plan:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_materialization_implementation_plan_3aeb54ec0b_20260703T030149CST/report/runtime_artifact_manifest_materialization_implementation_plan.json`
- Source implementation plan SHA256:
  `8b15be1ccd3be99f0924e71d5ed3befdd57a3416e6ebaa00a1f8986aee68ff59`
- Output existed before:
  `False`
- Output runtime manifest:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest_plan_2456037d6f_20260703T015846CST/report/planned_runtime/dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_artifact_manifest.json`
- Output runtime manifest SHA256:
  `92e82fbf2e7bb26847b6f24b8ccc9d78242addb451bc7301aa77997592569bd2`
- Runtime manifest summary SHA256:
  `6e5cdae55b3fccdefd9bd2081e47d4f5a3e88cd7c0b08356117ec47a519945d2`
- Artifact SHA256SUMS SHA256:
  `c33f265c9c278a3e03a6c15f601ea31e97810116b536ee6e4d0d40ed8818cfd4`
- Exit code:
  `0`
- Materializer status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_artifact_manifest_materialized`
- Failed checks:
  `[]`

The materialized manifest has schema
`dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_v1`, source
scope `public_simulator_fixed_dp_candidate_tensor`, `default_off=True`,
`fail_closed=True`, `selection_effect=False`, `online_selector_change=False`,
selector mode `static`, executed output policy `dp_top1`, candidate count `8`,
atom count `9`, atom schema `camp_legacy_v1_9d`, and affine score expression
`score_k(w)=a_k^T w`. It contains only `atom_scales` and `static_weights`
artifact entries. Its authorizations keep runtime execution, replay, candidate
generation, DP modification, online selector change, promotion, deployment,
training, and safety/CAMP-over-DP claims disabled.

## Default-Off Selector Runtime Shadow Replay Preflight

Verified on AutoDL at 2026-07-03 04:29 CST:

- Preflight artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_preflight_b4f312801c_20260703T042928CST`
- Planned runtime shadow replay output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_preflight_b4f312801c_20260703T042928CST_planned_runtime_shadow_replay_execution`
- CAMP head and origin/main:
  `b4f312801c5256f73ae6b4f97a6638ce47441bb0`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Runtime manifest SHA256:
  `92e82fbf2e7bb26847b6f24b8ccc9d78242addb451bc7301aa77997592569bd2`
- Planned command count / expected records:
  `32 / 3200`
- Check count:
  `470`
- Exit code:
  `0`
- Failed checks:
  `[]`

This preflight only generated a guarded runbook for the next gate. It did not
run replay, generate candidates, train CAMP, modify DP, promote, deploy, or
authorize safety/CAMP-over-DP claims. The planned commands keep CAMP as a
default-off shadow reranker over fixed DP candidate tensors and keep the
executed trajectory policy at DP Top-1.

## Default-Off Selector Runtime Shadow Replay Execution

Verified on AutoDL at 2026-07-03 09:36 CST:

- Fresh execution artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_artifact_dbd5b539a0_20260703T090930CST`
- Fresh execution output root:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_dbd5b539a0_20260703T090512CST`
- Fresh preflight refresh artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_preflight_refresh_dbd5b539a0_20260703T090512CST`
- Interrupted prior execution artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_artifact_dbd5b539a0_20260703T044233CST`
- Interrupted prior progress:
  `14/32`, no `runbook.exit`, PID not alive
- CAMP head and origin/main:
  `dbd5b539a0117c47ea0809e923940619ec41214a`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Runtime manifest SHA256:
  `92e82fbf2e7bb26847b6f24b8ccc9d78242addb451bc7301aa77997592569bd2`
- Runbook exit / audit exit:
  `0 / 0`
- Selection/validation/replay summaries:
  `32 / 32 / 32`
- Records:
  `3200`
- Executed DP Top-1 records:
  `3200`
- Default-off selector records:
  `3200`
- Shadow selected non-Top-1 records:
  `2832`
- Feasible / fail-closed fallback records:
  `2914 / 286`
- Max affine score error:
  `4.440892098500626e-16`
- Audit failed checks:
  `[]`
- Execution audit JSON SHA256:
  `1277624d6ff07b4a02f73c18af10f68a84a6e999b1483a5d654adafebc9cba7c`
- Artifact SHA256SUMS SHA256:
  `55be6fa553f180dd2be565e2206c69285e4cd8850eab1832b8db10224e4c72ac`

The prior execution was interrupted by the AutoDL terminal closure and is
retained only as interruption evidence. The fresh execution completed the
guarded runbook and the read-only audit passed. CAMP remained a default-off
shadow reranker over the fixed DP candidate tensor; the executed trajectory
remained DP Top-1 for every record.

## Default-Off Selector Runtime Shadow Replay Result Review

Verified on AutoDL at 2026-07-03 09:58 CST:

- Result review artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST`
- Source execution artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_execution_artifact_dbd5b539a0_20260703T090930CST`
- CAMP head and origin/main:
  `9e86ec1fb2bb9f22df578712b8003414694131f1`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Result review exit:
  `0`
- Failed checks:
  `[]`
- Result review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_result_review_passed`
- Selection/validation/replay summaries:
  `32 / 32 / 32`
- Records:
  `3200`
- Executed DP Top-1 records:
  `3200`
- Default-off selector records:
  `3200`
- Shadow selected non-Top-1 records:
  `2832`
- Feasible / fail-closed fallback records:
  `2914 / 286`
- Max affine score error:
  `4.440892098500626e-16`
- Result review report JSON SHA256:
  `627fe492c69bbc422a798f025e2cb632008b61dd193b3fa59e1c5c84fbb603ab`
- Artifact SHA256SUMS SHA256:
  `27bc90bf3f55add804ab6535f44cf02b879cabd7262a27da9df4547552ded6d0`

The result review only inspected the passed execution audit. It did not run
replay, generate candidates, train CAMP, modify DP, promote, deploy, or make
safety/CAMP-over-DP claims. It authorizes only a future promotion-decision
planning gate after explicit user authorization, not promotion itself.

## Default-Off Selector Runtime Shadow-vs-Top1 Delta Review

Verified on AutoDL at 2026-07-03 10:34 CST:

- Delta review artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST`
- Source result review JSON:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST/review/result_review_report.json`
- CAMP head and origin/main:
  `04f4b6842178204717051209e0b106c67332d420`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Delta review exit:
  `0`
- Failed checks:
  `[]`
- Delta review status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed`
- Static objective delta supported:
  `True`
- Selection logs / records:
  `32 / 3200`
- Executed DP Top-1 records:
  `3200`
- Shadow selected non-Top-1 records:
  `2832`
- Masked selection score, lower is better:
  `better=2832`, `tie=368`, `worse=0`, `uncomparable=0`
- Masked selection score on the shadow-different subset:
  `better=2832`, `tie=0`, `worse=0`, `uncomparable=0`
- Raw affine score before feasibility masking:
  `better=2804`, `tie=368`, `worse=28`, `uncomparable=0`
- Delta review report JSON SHA256:
  `2bdfbce1e89db54465d895148f3dc3ecae2a511b3db889a29f693cb4cdfebc62`
- Artifact SHA256SUMS SHA256:
  `24b24b26ad644076ec2952b575b840068e44e13ee12abcf78416655f799722bd`

The delta review only compared logged scores and atoms from the existing
selection logs. It did not replay, train, generate candidates, modify DP,
promote, deploy, or make safety/CAMP-over-DP claims. The supported positive
claim is limited to static masked objective delta: the shadow-selected
candidate was no worse than DP Top-1 on the logged masked CAMP selection
score, and strictly better on all 2832 records where the shadow index differed
from the executed DP Top-1 index.

## Default-Off Selector Runtime Promotion-Decision Plan

Verified on AutoDL at 2026-07-03 11:02 CST:

- Promotion-decision plan artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_decision_plan_192d2928b2_20260703T110247CST`
- Source runtime result review JSON:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_9e86ec1fb2_20260703T095832CST/review/result_review_report.json`
- Source shadow-vs-Top1 delta review JSON:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_shadow_vs_top1_delta_review_04f4b68421_20260703T103434CST/review/shadow_vs_top1_delta_review_report.json`
- CAMP head and origin/main:
  `192d2928b2c9bbe22275f02c3c1532e713b1542f`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Plan exit:
  `0`
- Failed checks:
  `[]`
- Check count / failed check count:
  `80 / 0`
- Recommendation:
  `do_not_promote_from_current_evidence_alone`
- Immediate action:
  `build_runtime_promotion_evidence_package_preflight_only`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_only`
- Evidence package preflight authorized:
  `True`
- Selector promotion / deployment / safety / CAMP-over-DP-Top1 claim authorized:
  `False / False / False / False`
- Plan JSON SHA256:
  `16394aebd9cf92025fc36613f196d6f0728c1a60ec12768474e459d48e88eb44`
- Artifact SHA256SUMS SHA256:
  `c025186948924debf7e43b26c2d2d3025e649e167cf37c7301e8c5cfe312a811`

This gate is planning-only. It does not promote from the current evidence
alone. It authorizes only a read-only runtime promotion evidence-package
preflight, where immutable hashes and boundary evidence must be packaged before
any future promotion discussion. Promotion, deployment, selector changes, DP
changes, replay, candidate generation, training, safety claims, and
CAMP-over-DP-Top1 claims remain unauthorized.

## Default-Off Selector Runtime Promotion Evidence-Package Preflight

Verified on AutoDL at 2026-07-03 11:33 CST:

- Runtime promotion evidence-package preflight artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST`
- CAMP head and origin/main:
  `1758ea83eaf61ada32f60b7bbd15e97479b2e1e5`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Preflight exit:
  `0`
- Failed checks:
  `[]`
- Check count / failed check count:
  `229 / 0`
- Artifact manifest entries:
  `runtime_promotion_decision_plan,runtime_result_review,shadow_vs_top1_delta_review,runtime_manifest,training_artifact_static_review,training_summary,offline_weights_npy,atom_scales_json,runtime_shadow_execution_sha256s`
- Preflight status:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_preflight_ready`
- Authorized next work:
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_only`
- Evidence-package static review authorized:
  `True`
- Selector promotion / deployment / safety / CAMP-over-DP-Top1 claim authorized:
  `False / False / False / False`
- Training / replay / candidate generation / DP modification authorized:
  `False / False / False / False`
- Runtime records / executed DP Top-1 / shadow non-Top-1:
  `3200 / 3200 / 2832`
- Static masked objective better/tie/worse/uncomparable:
  `2832 / 368 / 0 / 0`
- Training records / dropped all-infeasible:
  `2914 / 286`
- Preflight report JSON SHA256:
  `0cda58e1e95b36c867d9208ed51e4e23f24d1106f4460e5d932515eff976b6be`
- Artifact SHA256SUMS SHA256:
  `5e277729fe2c0690c599c006a02f221d94d553acdc164f2000e29dbc16283149`

This preflight is read-only evidence packaging. It does not train, replay,
generate candidates, modify DP, change the online selector, promote atoms or
selectors, deploy, or authorize safety/CAMP-over-DP claims. It only authorizes
the next evidence-package static review gate.

## Default-Off Selector Runtime Promotion Evidence-Package Static Review Failed Attempt

Verified on AutoDL at 2026-07-03 16:02 CST:

- Failed static review artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_static_review_e870358da5_20260703T160217CST`
- Source preflight artifact:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST`
- CAMP head and origin/main:
  `e870358da583e851b6ef3dd8033242165681c2a9`
- DP head:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Static review exit:
  `1`
- Failure class:
  `source_preflight_sha256s_mismatch`
- Failure attribution:
  `preflight_artifact_path_mismatch_json_md_under_preflight_subdir`
- Actual preflight JSON:
  `/root/autodl-tmp/camp_dp_v14_public_simulator_default_off_runtime_promotion_evidence_package_preflight_1758ea83ea_20260703T113342CST/preflight/runtime_promotion_evidence_package_preflight.json`
- Failed report JSON SHA256:
  `4c19c3162cb9488169e9b555a8095617ab6f4f4530f0e160066d1c77ef809458`
- Artifact SHA256SUMS SHA256:
  `0f3db6b1cf249e1537d60b49b365397903561d67f92ed3508a038ed9bd93a0b6`

This failed attempt did not train, replay, generate candidates, modify DP,
change the online selector, promote atoms or selectors, deploy, or authorize
safety/CAMP-over-DP claims. The next action requires a user decision before
any path fix or rerun.

## Current Integration Position

CAMP training has started and completed for this v14 fixed-DP candidate source.
The training artifact static contract review, trained default-off shadow
replay/evaluation preflight, and guarded shadow replay/evaluation execution
have passed. The read-only result review, promotion-decision planning gate, and
trained promotion evidence-package preflight have also passed. The default-off
shadow selector static integration contract plan, implementation plan, and
implementation static contract review have passed. The implementation unit-test
plan, implementation unit-tests-only gate, and implementation-only gate have
also passed. The post-implementation static contract review and runtime
artifact manifest plan-only/static-review/materialization-plan-only/static-review
and materialization implementation-plan/static-review gates have passed. The
runtime artifact manifest materializer implementation and post-implementation
static contract review are complete, the runtime artifact manifest has been
materialized, and the default-off selector runtime shadow replay preflight and
fresh execution audit/result review have passed. The read-only shadow-vs-Top1
delta review has also passed, supporting only a static masked-objective delta
claim and not a safety or CAMP-over-DP claim. The runtime promotion-decision
plan is ready and recommends not promoting from current evidence alone. The
runtime promotion evidence-package preflight has now passed. The first runtime
promotion evidence-package static review attempt failed because the command
used the wrong preflight artifact input paths. That failure is not a promotion
or safety claim failure; it is a rerun decision boundary. The next action
requires user direction before any path fix or rerun.

The current boundary does not authorize CAMP generation, DP modification,
postprocessing, guidance, reference blending, closed-loop outcome labels,
formal seeds 11/12/13, promotion, deployment, or safety-benefit claims.

current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rejected
next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_runtime_shadow_replay_promotion_evidence_package_static_review_rerun_requires_user_decision

## Cleanup Policy

Older audit files and append-only audit history are evidence, not current
instructions. Do not delete or rewrite them while current tests or audit
references still depend on them.

Generated session exports, handoff notes, local slide prompts, archives, caches,
and pytest scratch directories are local workspace noise. They are ignored by
`.gitignore` and are not part of the current DP-CAMP integration state.
