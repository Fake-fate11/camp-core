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

## Gate 2: Source-Preserving Adapter Design, TDD, Static Review, and Smoke

Status: terminal stop condition passed fail-closed. Honest-no-claim closeout
record is the only remaining v23 work.

The adapter plan is
`docs/superpowers/plans/2026-07-15-v23-source-preserving-adapter.md`.
TDD added a read-only regulatory-element census and a native-runner gate at
CAMP HEAD `e52da52fbea27844e2545dcac5ac504664ef10ef`. The gate runs before the
existing no-ROS projection fallback and fixed DP builder. It accepts stock
Lanelet2 maps, but requires a real official Autoware extension for maps with
Autoware-only regulatory elements. A process-local projection module cannot
masquerade as regulatory registration. No v23 path calls
`sanitize_lanelet2_map`, removes a relation/reference, rewrites a subtype, or
modifies fixed DP.

Local and AutoDL focused verification both passed: `15` v23 tests and `2`
Lanelet2 integration tests (`134` deselected), plus targeted `py_compile` and
`git diff --check`. An attempted broader local integration run reached 51
tests before the local Anaconda Torch binary aborted during import; it was not
counted as a pass. The equivalent adapter tests and compilation passed in the
authoritative AutoDL DP environment.

Read-only capability review found Lanelet2 `1.2.2`. The Python binding exposes
`RegulatoryElement`, `RegulatoryElementLayer`, and generic `registerId`, but no
regulatory factory/register hook. None of
`autoware_lanelet2_extension_python`, its projection module,
`lanelet2_extension_python`, or `autoware_lanelet2_extension` is installed,
and no matching official shared library exists under the reviewed runtime
roots.

The frozen original Autoware OSM remained exactly 3,441,081 bytes with SHA256
`cda848e3d440aaf48e532f8ab33afdff0bf8b8f1a45abd3d7724637a287ed660`.
Static census found `15` regulatory relations: `9 detection_area`,
`1 right_of_way`, and `5 traffic_sign`. All nine `detection_area` relations
are referenced by lanelets. The fail-closed adapter rejected the absent
official implementation before builder construction. One separate diagnostic
load of the same original map through the fixed DP builder returned `1` and
reported all nine failures as `No regulatory element found that implements
rule detection_area`, followed by the nine corresponding missing relation
references. Source SHA256 before and after both attempts was identical.

Immutable artifact/root:
`/root/autodl-tmp/camp_dp_v23_source_preserving_adapter_e52da52f_20260715T174325CST`
/
`28374ed051e18099448875bb94560cdff0bab6be0082edb660bb6f5f6f994825`,
with outer `run.exit=0`, nested raw-builder return code `1`, and decision
`stop_source_preserving_adapter_unavailable`. Fresh verification of both
`SHA256SUMS` and `ROOT_SHA256SUMS` passed.

This is an explicit user-defined real stop condition. Continuing would require
deleting or retagging attached map semantics, treating the projection fallback
as a registration implementation, adding an unapproved public source, or
changing the fixed-DP scientific contract. All are forbidden.

Consequently, map-family and route census, split freeze, corpus generation,
training, calibration, holdout, paired evaluation, evidence statistics, and
latency evaluation did not run. Counts are therefore: map paths/unique blobs
frozen `15/13`; reviewed Autoware map `1`; independent map families `not
censused`; routes `0`; train/calibration/holdout routes `0/0/0`; seeds `0`;
paired support `0`; corpus records `0`. No atom mask, new v23 weights, solver
iterations/cuts/gap, learning curve, paired metrics/CI, or latency statistics
exist. Holdout was never opened. V18/v22 weights remained read-only. V23 makes
no safety, deployment, native-ranking, or CAMP-over-DP claim.

current_v23_status=v23_adapter_terminal_stop_honest_no_claim_pending_closeout
current_v23_artifact_source_head=e52da52fbea27844e2545dcac5ac504664ef10ef
current_v23_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v23_artifact=/root/autodl-tmp/camp_dp_v23_source_preserving_adapter_e52da52f_20260715T174325CST
current_v23_artifact_root_sha256=28374ed051e18099448875bb94560cdff0bab6be0082edb660bb6f5f6f994825
next_work_target=v23_honest_no_claim_closeout_record_only

## Gate 3: Honest-No-Claim Record-Only Closeout

Status: passed. V23 is closed with no further action recommended.

The closeout was record-only. It did not load a map, run the simulator, open
holdout, generate a corpus, train a model, execute paired evaluation, or rerun
v22 or earlier work. It verified the sealed adapter evidence, exact source-map
SHA256, v23-scoped live pointers, local/GitHub/AutoDL CAMP alignment, fixed DP
HEAD and tracked state, the 10 GiB disk floor, zero related tasks, and focused
tests.

The first closeout artifact is preserved at
`/root/autodl-tmp/camp_dp_v23_honest_no_claim_closeout_0e1c0ac4_20260715T174704CST`
with root SHA256
`5949c3d7e90054c9eb05c5d36f21bff44e4d442ef56189e0d6c9fc4560bbf89e`
and `run.exit=1`. All 16 tests passed, but one harness check incorrectly
counted pointer occurrences across the entire historical current-status file;
the fixed-DP line legitimately appears in older version sections. No
scientific or repository state changed.

The retry scoped pointer uniqueness to the named `Current V23 Status` section,
matching the audited reader contract. Immutable corrected artifact/root:
`/root/autodl-tmp/camp_dp_v23_honest_no_claim_closeout_retry_0e1c0ac4_20260715T174756CST`
/
`08276aec1333f26ec02e7f4a05a2c07aeea810ec4b214a37fba062bd0f138752`,
with `run.exit=0`, `14 / 0` checks, and 16 focused tests passed. Fresh
verification of both `SHA256SUMS` and `ROOT_SHA256SUMS` passed. Free space was
`49,752,567,808` bytes, and no related process was running.

Final v23 accounting is unchanged: frozen map paths/unique files `15/13`;
independent map families censused `0`; routes `0`; split routes `0/0/0`;
seeds `0`; paired support `0`; corpus records `0`. No v23 atom mask, weights,
solver convergence, learning curve, paired metric/clustered CI95, or latency
result exists. The holdout was never opened. Claim decision is
`honest_no_claim` because the source-preserving adapter is unavailable for the
lanelet-attached `detection_area` semantics. Promotion, deployment, and online
activation remain out of scope and did not occur.

current_v23_status=v23_closed_honest_no_claim_source_preserving_adapter_unavailable
current_v23_artifact_source_head=0e1c0ac485b33e64cb6a7a15cf0039eb34b38e72
current_v23_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v23_artifact=/root/autodl-tmp/camp_dp_v23_honest_no_claim_closeout_retry_0e1c0ac4_20260715T174756CST
current_v23_artifact_root_sha256=08276aec1333f26ec02e7f4a05a2c07aeea810ec4b214a37fba062bd0f138752
next_work_target=no_further_action_v23_closed_honest_no_claim_source_preserving_adapter_unavailable
