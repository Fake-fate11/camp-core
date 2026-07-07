# Diffusion Planner V15 Iteration Audit

This is the authoritative audit for v15 work. V14 is sealed evidence and is
referenced only for its final closeout boundary.

## V15 Broader Non-Formal Evidence Expansion Plan Preflight

The v15 first gate is registered as
`v15_broader_nonformal_evidence_expansion_plan_preflight`.

This preflight is plan-only. It does not run Full36, formal seeds, training,
paired evaluation, candidate generation, Diffusion Planner modification,
candidate tensor mutation, trajectory mutation, reference blending, guidance,
postprocess, or postselection.

Pre-registered scope:

- Larger non-formal route/seed/NPC/traffic-light matrix:
  routes `sample_normal`, `sample_tl`, `nishi_release`,
  `nishi_lane_change`, `left_turn_red_light`, `sharp_turn`, `dense_merge`,
  `npc_interaction`; train seeds `2100-2103`; calibration seeds `2104-2105`;
  holdout seeds `2106-2107`; NPC modes `none`, `single`, `dense`; traffic-light
  modes `off`, `green`, `red`.
- Train/calibration/holdout split must remain zero-overlap by route, seed,
  NPC mode, traffic-light mode, candidate tensor SHA, and record id.
- Fixed DP candidate tensor provenance must be carried from DP head
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`; CAMP may only rerank/select.
- Paired protocol is CAMP-selected fixed DP candidate versus DP Top-1.
- Scenario buckets are `normal`, `traffic_light`, `red_light_turn`,
  `sharp_turn`, `npc_interaction`, `dense_scene`, `lane_change_or_merge`.
- Score remains affine: `score_k(w)=a_k^T w`.
- Weights remain a nonnegative simplex over approved atoms.
- The simplex/CVaR/L2 master remains convex.

Pass/fail criteria:

- Pass requires zero-overlap checks, fixed-DP provenance checks, no Full36 or
  formal seed use, no DP/candidate/trajectory mutation, complete timing
  artifact registration, and later holdout paired SafetyCost_v1 improvement
  with CI95 high below zero.
- Fail on any no-go condition below.

No-go conditions:

- Full36 scope requested.
- Formal seeds `11`, `12`, or `13` used.
- Full36 or formal-seed result used for training, calibration, or online input.
- DP head drift.
- DP code, config, weights, or checkpoint modified.
- CAMP candidate tensor or trajectory mutation.
- Reference blend, guidance, postprocess, or postselection.
- Closed-loop outcome used for training or online selector input.
- Non-affine score, non-simplex weights, or non-convex master.

Timing requirements:

- Offline CAMP training must record wall-clock seconds, start/end timestamps,
  training command, training sample count, and artifact/model/config/log SHA.
- Online selector latency must record count, mean, median, p95, p99, and max.
- Fallback latency must be reported separately with count, mean, median, p95,
  p99, and max.
- Timing JSON, timing MD, and SHA256SUMS must be included in the artifact.
- Timing instrumentation must not change selector behavior.
- GPU model is not required.

Artifact layout:

- `HEADS`
- `COMMAND`
- `stdout.txt`
- `stderr.txt`
- `run.exit`
- `v15_broader_nonformal_evidence_expansion_plan_preflight.json`
- `v15_broader_nonformal_evidence_expansion_plan_preflight.md`
- `timing.json`
- `timing.md`
- `SHA256SUMS`

```text
v15_broader_nonformal_evidence_expansion_plan_preflight_status=v15_broader_nonformal_evidence_expansion_plan_preflight_ready
v15_broader_nonformal_evidence_expansion_plan_preflight_passed=True
v15_broader_nonformal_evidence_expansion_plan_preflight_training_executed=False
v15_broader_nonformal_evidence_expansion_plan_preflight_paired_evaluation_executed=False
v15_broader_nonformal_evidence_expansion_plan_preflight_full36_used=False
v15_broader_nonformal_evidence_expansion_plan_preflight_formal_seed_11_12_13_used=False
v15_broader_nonformal_evidence_expansion_plan_preflight_dp_modified=False
v15_broader_nonformal_evidence_expansion_plan_preflight_candidate_tensor_modified=False
v15_broader_nonformal_evidence_expansion_plan_preflight_trajectory_modified=False
v15_broader_nonformal_evidence_expansion_plan_preflight_camp_action=rerank_or_select_only
v15_broader_nonformal_evidence_expansion_plan_preflight_authorized_next_work=v15_broader_nonformal_evidence_expansion_plan_preflight_static_review_only
current_v15_status=v15_broader_nonformal_evidence_expansion_plan_preflight_ready
current_v15_artifact_scope=v15_broader_nonformal_evidence_expansion_plan_preflight
next_work_target=v15_broader_nonformal_evidence_expansion_plan_preflight_static_review_only
```
