# Diffusion Planner V24 Iteration Audit

This file is the sole mutable audit for v24. V23 and earlier audits are historical and read-only.
V24 corrects the v23 single-source global-stop control error and advances the
Autoware and TIER IV Lanelet2 sources independently on the unchanged fixed DP.

## Frozen Scope

- CAMP repositories are `F:\camp_core-main` and
  `/root/autodl-tmp/camp_core`, branch `main`.
- Fixed DP is `/root/autodl-tmp/Diffusion-Planner` at
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Branch A is the frozen Autoware map plus only the official Apache-2.0
  `autoware_lanelet2_extension` dependency source.
- Branch B is the 14-path/12-blob TIER IV `scenario_simulator_v2` inventory at
  `e22f01093fa6516c0552549ada302270329c59a4`.
- Branch-local and single-map failures cannot stop the other source.
- CAMP may only rerank/select the fixed DP K=8 tensor. DP, source-map semantics,
  candidate tensors, and the convex master remain unchanged.

Persistent goal thread `019f656a-1a4a-7550-8d42-8a385fd2712e` was created
without a token budget. The goal tool limits objective text to 4,000
characters, so its stored compression binds source task
`019f26f1-36ec-7f91-932d-3f365940e8f8` and this full authorized contract.

## Gate 0: Startup Reconciliation

Status: passed. V23 boundary review is next.

Local `main`, local `origin/main`, live GitHub `main`, AutoDL CAMP HEAD, and
AutoDL `origin/main` were identical and tracked-clean at
`245ce029b91f73e6a7fca7c4ecf6a40679770ad7`. AutoDL DP was tracked-clean at
the fixed commit `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The startup check found zero related tasks. Free space was `49,752,203,264`
bytes, above the 10 GiB floor. V23 closeout root
`08276aec1333f26ec02e7f4a05a2c07aeea810ec4b214a37fba062bd0f138752`
and v22 closeout root
`d82dacf580a1d135c902a27b1cc5ade9af64604b7c7a72ce3c76b437744269ff`
were rehashed successfully.

Two pre-artifact AutoDL public-GitHub probes received transient HTTP 503
errors; bounded retries passed. The sealed startup artifact/root is
`/root/autodl-tmp/camp_dp_v24_startup_reconciliation_245ce029_20260715T190348CST`
/
`a0c1edac5ae664cb5c4940d41b95569e8e05f102199eb87d47a0e01a4ceb3c67`,
with `run.exit=0`.

V23 remains a dependency-capability diagnosis, not a CAMP/DP performance failure.
Branch A and Branch B remain independently eligible.
No map loader, simulator, corpus, training, calibration, holdout, or paired evaluation ran.
`claim_authorized=false` and `holdout_opened=false`.

current_v24_status=v24_startup_reconciliation_passed
current_v24_artifact_source_head=245ce029b91f73e6a7fca7c4ecf6a40679770ad7
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_startup_reconciliation_245ce029_20260715T190348CST
current_v24_artifact_root_sha256=a0c1edac5ae664cb5c4940d41b95569e8e05f102199eb87d47a0e01a4ceb3c67
source_a_status=pending_v23_boundary_review
source_a_terminal=false
source_b_status=pending_v23_boundary_review
source_b_terminal=false
authorized_source_count=2
source_terminal_count=0
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_v23_boundary_review_only
