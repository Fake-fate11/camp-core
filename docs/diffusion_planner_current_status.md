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
- AutoDL Diffusion Planner remains fixed at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Current status is
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_ready`.
- Current next work target is
  `public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only`.

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

## Current Integration Position

CAMP training has started and completed for this v14 fixed-DP candidate source.
The training artifact static contract review, trained default-off shadow
replay/evaluation preflight, and guarded shadow replay/evaluation execution
have passed. The read-only result review, promotion-decision planning gate, and
promotion evidence-package preflight have also passed. The default-off shadow
selector static integration contract plan has passed. The next gate is
default-off shadow selector implementation planning only, and still does not
authorize implementation, promotion, deployment, training, replay, candidate
generation, or safety-benefit claims.

The current boundary does not authorize CAMP generation, DP modification,
postprocessing, guidance, reference blending, closed-loop outcome labels,
formal seeds 11/12/13, promotion, deployment, or safety-benefit claims.

current_v14_status=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_static_integration_contract_plan_ready
next_work_target=public_simulator_fixed_dp_candidate_generation_trained_default_off_shadow_replay_evaluation_default_off_shadow_selector_implementation_plan_only

## Cleanup Policy

Older audit files and append-only audit history are evidence, not current
instructions. Do not delete or rewrite them while current tests or audit
references still depend on them.

Generated session exports, handoff notes, local slide prompts, archives, caches,
and pytest scratch directories are local workspace noise. They are ignored by
`.gitignore` and are not part of the current DP-CAMP integration state.
