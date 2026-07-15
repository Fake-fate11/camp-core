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

## Gate 1: V23 Boundary Review

Status: passed. Official extension source qualification is next.

The read-only boundary review ran at CAMP HEAD
`aad8b1a588e9569a28674a67df5456aa21d7de4d` with fixed DP unchanged. It
rehashes and reads existing v23 source-freeze, adapter, and closeout evidence;
it does not reopen or rerun v23.

V23 froze the TIER IV source at `14 paths / 12 unique blobs`. Its own design
required later map-family, route, and split work, but also listed
`reviewed source-preserving adapter impossibility` as a global stop. After the
single Autoware map failed its source-preserving adapter smoke, the v23 audit
promoted that Branch A result to a study-wide terminal stop. There was no TIER
IV map-family, route, or K=8 support census, yet v23 closed with map families
uncensused, routes `0`, paired support `0`, and holdout unopened.

The review decision is
`v23_global_stop_was_source_scope_control_error`. This corrects control scope;
it does not alter the valid v23 conclusion that the reviewed Autoware map could
not load source-preservingly in that environment, and it does not create a
performance result or claim.

All `16 / 0` checks passed. The review rehashed v23 source-freeze root
`c49f129f092497f6eb30cf887cf3bfbf36fc924244055ada0d0ff221d5ab3265`,
adapter root
`28374ed051e18099448875bb94560cdff0bab6be0082edb660bb6f5f6f994825`,
closeout root
`08276aec1333f26ec02e7f4a05a2c07aeea810ec4b214a37fba062bd0f138752`,
and v24 startup root
`a0c1edac5ae664cb5c4940d41b95569e8e05f102199eb87d47a0e01a4ceb3c67`.
Focused AutoDL py_compile, 4 v24 tests, and diff checks passed.

Immutable artifact/root:
`/root/autodl-tmp/camp_dp_v24_v23_boundary_review_aad8b1a5_20260715T191632CST`
/
`3f127806be14984c7ca08b595bb8947565fa12f74c6a922e0b9fedd9d646c64d`,
with `run.exit=0`. Branch A now proceeds to official extension source
qualification. Branch B remains independently pending raw map census.
No map loader, simulator, corpus, training, calibration, holdout, or paired evaluation ran.

current_v24_status=v24_v23_boundary_review_passed
current_v24_artifact_source_head=aad8b1a588e9569a28674a67df5456aa21d7de4d
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_v23_boundary_review_aad8b1a5_20260715T191632CST
current_v24_artifact_root_sha256=3f127806be14984c7ca08b595bb8947565fa12f74c6a922e0b9fedd9d646c64d
source_a_status=pending_extension_source_qualification
source_a_terminal=false
source_b_status=pending_raw_map_census
source_b_terminal=false
authorized_source_count=2
source_terminal_count=0
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_extension_source_qualification_only

## Gate 2: Official Extension Source Qualification and Freeze

Status: passed. Branch A isolated-build design, TDD, static review, and
preflight are next; no build or map load has started.

The selection rule was frozen before any build or load result: choose the
highest official semantic-version tag in
`autowarefoundation/autoware_lanelet2_extension` dated no later than the frozen
Universe commit. Universe commit
`b8d441c59293e34289cd7bca1ba5e5a33e9189d9` is dated
`2026-07-14T21:08:49+09:00`; the eligible official releases were `1.0.0`,
`1.1.0`, and `1.2.0`. The rule therefore uniquely selected `1.2.0`, not an
experimentally convenient version.

The frozen source URL is
`https://github.com/autowarefoundation/autoware_lanelet2_extension.git` at
commit `4a3420d8cc19906e7739618f8a1686400f79b4ac`, tree
`76ba5b7b3b74bc5539b6ea55dcfb205538ad5362`, with reproducible archive SHA256
`5559112bc301221503dd1316818c853052affa796a852c6c590bf84c75435fa7`.
It is the official Apache-2.0 source. LICENSE SHA256 is
`c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`;
NOTICE is absent at this commit, and DISCLAIMER SHA256 is
`4e3f9eadc58fd538a102666643f567aaf848778d64e55f75c3f46c639bed543d`.
The artifact freezes the dependency graph and key source file/blob hashes.

Static review traced `lib/detection_area.cpp`'s global
`RegisterRegulatoryElement<DetectionArea>` object into the shared
`autoware_lanelet2_extension_lib` target, with a separate official Python
binding for the regulatory type. The AutoDL Lanelet2 Python package is `1.2.2`;
its bundled core shared library exports factory and registrar ABI symbols. The
environment is Python `3.9.25`, SOABI `cpython-39-x86_64-linux-gnu`, GCC
`11.4.0`, CMake `3.22.1`, and glibc `2.35`.

This is source qualification, not a build result. Lanelet2 headers, Lanelet2
CMake package files, ROS, ament, and Autoware build dependencies are absent
from the current environment. The extension dependency manifest also points
to additional unfrozen upstream `main` sources. Binary compatibility and
process-local factory registration remain unproved; the next gate must decide
whether the frozen source can be built wholly inside the authorized prefix
without a system install, a global Lanelet2 change, or an unapproved source.

An initial partial blobless checkout timed out inside the authorized prefix and
was preserved as a failed acquisition attempt; it was never built. A clean,
detached, full official checkout at the selected commit is independently
sealed under `source_full`. No system package, global Python, DP repository,
checkpoint, original OSM, candidate tensor, or trajectory was changed.

All `17 / 0` checks passed. Immutable artifact/root:
`/root/autodl-tmp/camp_dp_v24_extension_source_qualification_78bf6eda_20260715T193857CST`
/
`fea4418715467376102bd8127bdf366ddecbec7dd01f408657b54b84835219e3`,
with `run.exit=0`. Branch B remains independently pending raw map census.
No map loader, simulator, corpus, training, calibration, holdout, or paired evaluation ran.

current_v24_status=v24_extension_source_qualification_passed
current_v24_artifact_source_head=78bf6eda5ec0383d0156e395a170497691ecd714
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_extension_source_qualification_78bf6eda_20260715T193857CST
current_v24_artifact_root_sha256=fea4418715467376102bd8127bdf366ddecbec7dd01f408657b54b84835219e3
source_a_status=official_extension_source_qualified_build_feasibility_pending
source_a_terminal=false
source_b_status=pending_raw_map_census
source_b_terminal=false
authorized_source_count=2
source_terminal_count=0
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_branch_a_isolated_build_design_tdd_static_preflight_only
