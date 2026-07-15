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

## Gate 1: License and Source Freeze

Status: passed. Adapter design, TDD, and static review are next. No map loader
or simulator has run.

The standard-library freezer ran at CAMP HEAD
`51c97eb24a2076247e892d2e4dfab82852e30914` with fixed DP unchanged. It
materialized only the allowed exact commits and OSM paths. Retrieval time was
`2026-07-15T09:28:32Z`. The source manifest contains
`15 OSM paths / 13 unique file SHA256 values`: Autoware contributes one path
and `scenario_simulator_v2` contributes `14 paths / 12 unique files`.
Map-family count remains intentionally unknown until the later geometry and
topology census; path/blob counts are not treated as independent maps.

The exact Autoware bidirectional map is 3,441,081 bytes. Its file SHA256 is
`cda848e3d440aaf48e532f8ab33afdff0bf8b8f1a45abd3d7724637a287ed660`,
Git blob OID is `028ef16a80b515cfdc65d13d7ada190dd578cf2d`, and Git blob-object
SHA256 is
`5ea83543ae9a4447c385c26b918f24e0af8ab18967943eeaeffd9a784b1a5662`.
The manifest preserves the exact raw URL, relative path, commit, acquisition
time, and corresponding receipts for all other OSM files.

Both exact commits carry the same root Apache-2.0 LICENSE SHA256
`c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`.
Autoware root NOTICE is present with SHA256
`9082255fb4bbb2bdf6e83e0d40ac749f49942953c123d7453e6ea67ce12e7119`;
the scenario repository has no root NOTICE at the frozen commit and records
`absent_at_commit`. The manifest freezes license-copy, modified-file notice,
applicable attribution retention, upstream NOTICE reproduction, and trademark
limits. Its SHA256 is
`8a44cb16207e1c8bb4cfa9c7b250a40d4d9f7d16c71949da79357b817eb77d72`.

The first source artifact is preserved at
`/root/autodl-tmp/camp_dp_v23_source_license_freeze_be97d7a4_20260715T172054CST`
with root SHA256
`361cec4cb2dba84d0560a3476104696a8973d8b2d3331ac0410dc156c047adc4`
and `run.exit=1`. Both exact commit fetches passed, but one scenario partial-
clone lazy blob read encountered a transient Git transport failure. The exact
blob later read successfully. TDD added a bounded three-attempt blob read with
the final Git stderr retained.

The second artifact is preserved at
`/root/autodl-tmp/camp_dp_v23_source_license_freeze_retry_51c97eb2_20260715T172639CST`
with root SHA256
`7ad99da785c33c0d2f15448d27064737de08fa97b412e9877601ed2f137066e9`
and `run.exit=1`. CAMP fetch and fast-forward completed, but a redundant live
GitHub probe then received HTTP 503 before materialization. Read-only state
proved CAMP HEAD/origin already matched and tracked state was clean, so the
corrected harness used one bounded fetch followed by local `merge --ff-only`.

The corrected immutable artifact/root is
`/root/autodl-tmp/camp_dp_v23_source_license_freeze_retry2_51c97eb2_20260715T172832CST`
/
`c49f129f092497f6eb30cf887cf3bfbf36fc924244055ada0d0ff221d5ab3265`,
with `run.exit=0`. AutoDL passed 30 focused regression tests and 18 independent
payload file/hash checks. Free space before/after was
`49,759,244,288 / 49,753,133,056` bytes. `source bytes modified: false`.
No map loader, simulator, model, training, calibration, or holdout ran.
`claim_authorized=false`.

current_v23_status=v23_license_source_freeze_passed
current_v23_artifact_source_head=51c97eb24a2076247e892d2e4dfab82852e30914
current_v23_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v23_artifact=/root/autodl-tmp/camp_dp_v23_source_license_freeze_retry2_51c97eb2_20260715T172832CST
current_v23_artifact_root_sha256=c49f129f092497f6eb30cf887cf3bfbf36fc924244055ada0d0ff221d5ab3265
next_work_target=v23_adapter_design_tdd_static_review_only
