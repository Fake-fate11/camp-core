# Diffusion Planner V23 Iteration Audit

This file is the sole mutable audit for v23. V22 and earlier audits are historical and read-only.
V23 is a new fixed-DP native-simulator study; it does
not rewrite or rerun the v22 honest-no-claim closeout.

## Frozen Scope

- CAMP repository: `F:\camp_core-main` and
  `/root/autodl-tmp/camp_core`, branch `main`.
- Fixed DP repository: `/root/autodl-tmp/Diffusion-Planner`, commit
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Allowed new public sources only: Autoware Universe commit
  `b8d441c59293e34289cd7bca1ba5e5a33e9189d9` bidirectional-traffic map and
  TIER IV `scenario_simulator_v2` commit
  `e22f01093fa6516c0552549ada302270329c59a4` Lanelet2 test/sample maps.
- INTERACTION, inD, rounD, exiD, CARLA, nuPlan, and nuScenes are excluded.
- CAMP may only rerank/select the fixed DP K=8 candidate tensor. It may not
  generate, repair, rewrite, blend, or postprocess trajectories or modify DP
  code, configuration, weights, checkpoint, or request semantics.
- Claim scope remains preregistered and narrow. Any failed gate produces an
  honest no-claim; no promotion, deployment, or online activation occurs.

Persistent goal thread `019f64fa-fefc-7db2-a736-b194e2ef58bd` was created
without a token budget. The tool limits objective text to 4,000 characters,
so the stored objective is an equivalent 3,983-character compression that
explicitly binds this full user-authorized v23 contract.

## Gate 0: Startup Reconciliation

Status: passed. License/source freeze is next.

Local `main`, local `origin/main`, live GitHub `main`, AutoDL CAMP HEAD, and
AutoDL `origin/main` are identical at
`f895b71f65c5971412a8d0be0c3ce492b25bbbe0`. Local and AutoDL CAMP tracked
state is clean. AutoDL DP is tracked-clean at the fixed commit
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The startup check found zero related v23, v22 native-runner, or scenario
generation tasks. JupyterLab and TensorBoard were unrelated and left alone.
Free space under `/root/autodl-tmp` was `49,761,910,784` bytes, above the
10 GiB floor. Unrelated untracked files were neither listed nor changed.

The verifier rehashed the sealed v22 main execution, independent review,
corrected evidence package, and closeout roots. V22 remains frozen at
`honest_no_claim`; no v22 outcome, route, threshold, model, or artifact was
changed or rerun.

AutoDL access used Windows Credential Manager, Paramiko, the existing
known-host key, and `RejectPolicy`. No password entered a prompt, command,
log, artifact, commit, audit, or response. Remote git/network commands sourced
`/etc/network_turbo` and used ff-only synchronization.

The first evidence attempt is preserved at
`/root/autodl-tmp/camp_dp_v23_startup_reconciliation_f895b71f_20260715T170342CST`
with root SHA256
`436afe23998b18b578b06bf901f9b0b45f6119612342a230d9777a5e72da786d`
and `run.exit=1`. Its sole failure was a transient GitHub HTTP 503 during the
live `git ls-remote`; it made no repository or scientific-state change.

The retry added bounded live-remote retry handling and passed. Immutable
artifact/root:
`/root/autodl-tmp/camp_dp_v23_startup_reconciliation_retry_f895b71f_20260715T170517CST`
/
`637eb928b5210bfc8096c4a6b533d5600dc795c76407e1105dd3829fd80f2cc9`,
with `run.exit=0`. No simulator, model, training, calibration, or holdout execution occurred.
`claim_authorized=false`.

current_v23_status=v23_startup_reconciliation_passed
current_v23_artifact_source_head=f895b71f65c5971412a8d0be0c3ce492b25bbbe0
current_v23_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v23_artifact=/root/autodl-tmp/camp_dp_v23_startup_reconciliation_retry_f895b71f_20260715T170517CST
current_v23_artifact_root_sha256=637eb928b5210bfc8096c4a6b533d5600dc795c76407e1105dd3829fd80f2cc9
next_work_target=v23_license_source_freeze_only
