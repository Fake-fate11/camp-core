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

## Gate 3: Branch A Isolated-Build Design, TDD, Static Review, and Preflight

Status: passed with Branch A fail-closed before build. Branch B raw-map census
is next.

The design and TDD contract authorize a compiler only when the clean frozen
source can configure the unmodified official CMake targets using dependencies
already present in the current environment or isolated prefix. System package
operations, global Python changes, Lanelet2/ROS upgrades, additional source
checkouts, edited upstream CMake, a hand-built registrar, and compiling only
`detection_area.cpp` are prohibited.

The preflight rehashed the qualification artifact, exact extension commit,
tree, archive, key files, official DetectionArea registration chain, bundled
Lanelet2 library, and factory symbols. The Lanelet2 1.2.2 runtime shared
library and factory symbols are present, but the wheel has no development
headers or CMake package. The official targets also lack ROS/ament/Autoware
build dependencies. Upstream `build_depends.repos` points to additional
unfrozen `main` sources, which are not authorized by v24's sole-new-source
contract.

The build authorization predicate is therefore false. Decision:
`branch_a_fail_closed_before_build`. Source A becomes
`source_ineligible_missing_authorized_build_prerequisites`. No compiler, build,
install, extension load, map load, or scientific execution ran. No build or
install directory was created, the official source remains clean, the original
OSM was not opened, and fixed DP remains unchanged.

Two ordinary evidence-harness failures were preserved rather than overwritten:

- `/root/autodl-tmp/camp_dp_v24_branch_a_isolated_build_preflight_4f6ec02e_20260715T195035CST`
  stopped before sealing because the process filter parsed `g++` as an invalid
  regular expression. It ran no compiler or build.
- `/root/autodl-tmp/camp_dp_v24_branch_a_isolated_build_preflight_4f6ec02e_20260715T195207CST`
  sealed root
  `9f5fd7a4862a02911d600ae55d2cf094e692d6947b77c3a1bed9a087af8a7688`
  and passed `27 / 28` checks. Its sole failed check hashed the
  `ROOT_SHA256SUMS` file instead of reading that file's authoritative first
  field. Scientific state and the no-build decision were unaffected.

The corrected receipt verified every file in the sealed source artifact,
applied the established root convention, and rechecked live CAMP/origin/DP,
extension cleanliness, absent build/install outputs, and the disk floor. All
`32 / 0` checks passed with `49,742,798,848` free bytes. Immutable
artifact/root:
`/root/autodl-tmp/camp_dp_v24_branch_a_isolated_build_preflight_4f6ec02e_20260715T195314CST`
/
`9df3f1958408a68841ff1dd074dd7d36774af182b43b8e51ee1f7415a7a4b2b6`,
with `run.exit=0`.

This terminal state is source-local. Branch B raw-map census remains mandatory;
the global stop remains unauthorized. Holdout is unopened and no claim is
authorized.

current_v24_status=v24_branch_a_isolated_build_preflight_passed
current_v24_artifact_source_head=4f6ec02e9c167241920545d2619170bff354a97d
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_branch_a_isolated_build_preflight_4f6ec02e_20260715T195314CST
current_v24_artifact_root_sha256=9df3f1958408a68841ff1dd074dd7d36774af182b43b8e51ee1f7415a7a4b2b6
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=pending_raw_map_census
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_branch_b_raw_map_census_tdd_static_preflight_only

## Gate 4: Branch B Raw Static Map Census, TDD, and Preflight

Status: passed. Fixed-builder smoke is next.

The outcome-blind standard-library census ran against the unchanged v23 source
payload at TIER IV `scenario_simulator_v2` commit
`e22f01093fa6516c0552549ada302270329c59a4`. It reverified the sealed source
root, Apache-2.0 receipt, absent root NOTICE, per-path URL/Git/SHA/byte receipts,
and exact `14 paths / 12 unique blobs`. Source bytes modified: `false`.

For every path, the report records XML validity, regulatory subtypes, bbox,
translation/ID-normalized geometry, ID-independent lanelet topology, explicit
speed sources, traffic-control sources, missing references, and pending builder
and route status. All 14 paths remain in the denominator, including duplicate
byte blobs and failures. The route threshold is frozen outcome-blind at
`>=80m` before any route or simulator result.

Source-valid / XML-valid / static-eligible path counts are `14 / 14 / 13`.
The sole static exclusion is
`simulation/traffic_simulator/test/map/empty/lanelet2_map.osm`, preserved with
one `no_lanelets` receipt. It is not replaced. Regulatory subtype totals are
`crosswalk: 4`, `right_of_way: 10`, `road_marking: 2`, `traffic_light: 24`,
and `traffic_sign: 10`. Static census does not pre-exclude the maps containing
`road_marking`; their stock-builder result remains pending per-map evidence.

Geometry and geometry-plus-topology cluster candidate counts are `11 / 11`.
Map-family count remains unset: byte duplicates, filenames, and static
fingerprints are inputs to the later reviewed family adjudication, not an
automatic independent-map claim.

All `26 / 0` checks passed. Local and AutoDL py_compile, 12 focused v24 tests,
and diff checks passed. Builder, route census, outcomes, and holdout remained
unopened; no DP code/configuration/weights/checkpoint/request changed.
Immutable artifact/root:
`/root/autodl-tmp/camp_dp_v24_branch_b_static_map_census_88e646f4_20260715T200301CST`
/
`2dbe704a7f244b7ac09648de006a67cdc03fa283079ff2a3bb213c894635fb8c`,
with `run.exit=0`.

Source A remains terminal only locally. Source B proceeds to one isolated
stock fixed-builder smoke per unique blob, with all 14 path receipts retained.
The global stop remains unauthorized.

current_v24_status=v24_branch_b_static_map_census_passed
current_v24_artifact_source_head=88e646f46568ed46670aab36636a873399948f41
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_branch_b_static_map_census_88e646f4_20260715T200301CST
current_v24_artifact_root_sha256=2dbe704a7f244b7ac09648de006a67cdc03fa283079ff2a3bb213c894635fb8c
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=static_census_passed_builder_smoke_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_branch_b_fixed_builder_smoke_execution_only

## Gate 5: Branch B Isolated Fixed-Builder Smoke Execution

Status: passed. Independent result review is next.

The controller executed one isolated process per unique frozen byte blob and
mapped each result back to every source path. Accounting is
`14 paths / 12 unique blobs / 12 executed blobs`. Byte-identical standard-map
and road-shoulder copies inherited their representative receipts and were not
executed twice.

Loaded / failed / execution-invalid blob counts are `10 / 2 / 0`, producing
`12` loadable path receipts. Every loaded worker used `stock_lanelet2`,
installed only the existing process-local no-ROS projection fallback, and
constructed the unchanged fixed-DP `LaneletSceneBuilder`. Layer and cached
lanelet counts are retained per worker.

The two failures remain map-local:

- `simulation/traffic_simulator/test/map/empty/lanelet2_map.osm` has a
  `projection_failure` because it contains no georeferenced node. This matches
  its frozen static `no_lanelets` receipt.
- `simulation/traffic_simulator/test/map/intersection/lanelet2_map.osm` has an
  `unsupported_autoware_regulatory_element` receipt. Its original map requires
  `road_marking`; the official source-preserving extension is unavailable, so
  the regulatory gate rejected it before projection or builder construction.

No map was sanitized or rewritten. Source bytes modified: `false`. All 12
worker return codes were zero, there were 12 distinct worker PIDs, and every
worker stdout/stderr pair is sealed. Map incompatibility is represented inside
a successful worker receipt rather than as controller failure.

The local observation wrapper initially used a 10-second outer timeout and
lost its SSH channel while the remote controller continued. A read-only
follow-up found no live controller/worker, found the completed artifact with
`run.exit=0`, and therefore did not restart it. This observation failure did
not alter the remote artifact or scientific state.

All `27 / 0` checks passed. Route, model, candidate generation, outcomes, and
holdout remained unopened. CAMP and fixed DP were tracked-clean, and disk
remained above the 10 GiB floor. Immutable artifact/root:
`/root/autodl-tmp/camp_dp_v24_branch_b_fixed_builder_smoke_fdde35ab_20260715T201012CST`
/
`26b4b58bf19559cafc3c2f0c3681cf3e52cd5f5f4873d1f5317e8cdc17587733`.

Source B has substantial loadable support, so neither a source-local terminal
state nor a global stop is authorized. Review must rehash every receipt and
recompute accounting before map-family adjudication.

current_v24_status=v24_branch_b_fixed_builder_smoke_execution_passed
current_v24_artifact_source_head=fdde35ab667eb4c6c765cb3453cf3064a6544f4b
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_branch_b_fixed_builder_smoke_fdde35ab_20260715T201012CST
current_v24_artifact_root_sha256=26b4b58bf19559cafc3c2f0c3681cf3e52cd5f5f4873d1f5317e8cdc17587733
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=builder_smoke_executed_review_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_branch_b_fixed_builder_smoke_review_only

## Gate 6: Branch B Fixed-Builder Smoke Independent Review

Status: passed. Merged map-family census and adjudication are next.

The reviewer independently reconstructed all `12` blob groups and `14` path
receipts from the static census. It rehashed every file in the execution and
static artifacts, then rehashed every live frozen source map. The execution
artifact root
`26b4b58bf19559cafc3c2f0c3681cf3e52cd5f5f4873d1f5317e8cdc17587733`
and static root
`2dbe704a7f244b7ac09648de006a67cdc03fa283079ff2a3bb213c894635fb8c`
both verified exactly.

Independent counts reproduce `10 / 2 / 0` loaded / failed /
execution-invalid blobs and `12` loadable paths. All loaded layer counts are
internally consistent, all 12 PIDs are distinct, all worker return codes are
zero, and live source hashes still equal their frozen receipts. The exact
empty-map projection failure and intersection-map `road_marking` failure were
recomputed without reclassification.

The review did not reexecute the builder. It did not start route census, load a
model, generate candidates, access outcomes, or open holdout. Map-family count
remains unset. Source B therefore has source-preserving fixed-builder support
and decision `builder_smoke_review_passed_loadable_support`; the two excluded
maps remain in failure accounting.

All `34 / 0` checks passed. Local and AutoDL v24 py_compile, 17 focused tests,
diff checks, CAMP/origin alignment, fixed DP cleanliness, and the 10 GiB disk
floor passed. Immutable review artifact/root:
`/root/autodl-tmp/camp_dp_v24_branch_b_fixed_builder_smoke_review_5a109127_20260715T201434CST`
/
`6f8ee2ec104530d143c65d40f4f11007f853b43ecd3929439db5f19b4483fd08`,
with `run.exit=0`.

Source B continues; neither a source-local terminal state nor global stop is
authorized. The next review must adjudicate map families from geography,
geometry, topology, duplicate, and configuration evidence before route census.

current_v24_status=v24_branch_b_fixed_builder_smoke_review_passed
current_v24_artifact_source_head=5a1091273f76a9ce63b2391b6afae9f18b7d61a9
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_branch_b_fixed_builder_smoke_review_5a109127_20260715T201434CST
current_v24_artifact_root_sha256=6f8ee2ec104530d143c65d40f4f11007f853b43ecd3929439db5f19b4483fd08
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=builder_smoke_review_passed_loadable_support
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_merged_map_family_census_tdd_review_only

## Gate 7: Outcome-Blind Merged Map-Family Census

Status: passed. Outcome-blind route-census TDD and preflight are next.

The adjudicator retained all `14 paths / 12 unique blobs`. Exact byte copies
remain one graph node while every source path keeps its own denominator
receipt. A graph edge requires both bbox containment `>=0.98` and absolute
segment containment `>=0.80` at the frozen 1e-8 degree coordinate grid. The
`connected components` are the map families. Filenames and builder outcomes
cannot create or tune an edge; builder status only labels family loadability.

This produced `5` map families, of which `4` loadable families cover 12 paths:

- `map_family_d7f16a17d3eb` contains the nine Kashi/standard-map path receipts
  across seven distinct byte blobs. Its configuration and ROS/no-ROS copies
  are one geography, not nine independent maps.
- The simple-cross, four-track-highway, and slope maps are three separate
  loadable singleton families.
- The intersection family remains nonloadable because its unchanged official
  `road_marking` semantics failed the fixed builder.
- The empty map remains an unassigned source receipt with
  `no_geometry_or_bbox`; it is neither dropped nor promoted into a family.

Because four independent loadable families remain, the frozen split regime is
the map-family-level train/calibration/holdout split regime. Exact allocation
waits for the outcome-blind `>=80m` route census and route/corridor grouping.
Route census, candidate generation, outcomes, and holdout remained unopened.
Source A remains terminal only locally; Source B continues, so the global stop
remains unauthorized.

All `16 / 0` adjudication checks passed. AutoDL also passed Python compilation,
all nine focused map-census tests, and `git diff --check`; CAMP/origin were
aligned and tracked-clean at
`24882c5218199e0fb9d73b513be0a5feba1f1b08`, and fixed DP remained clean at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

The first sealing command ran the adjudicator and verification successfully,
then resolved its relative SHA paths from the repo directory and exited 123.
The controller did not rerun adjudication. It entered the same artifact root,
confirmed `run.exit=0` and zero failed checks, rebuilt the SHA lists there, and
sealed immutable artifact/root:
`/root/autodl-tmp/camp_dp_v24_merged_map_family_census_24882c52_20260715T202223CST`
/
`33626198d8945e7f102946005bfa6b9db4762d93b1146896c9ebfd99ad633717`.

current_v24_status=v24_merged_map_family_census_passed
current_v24_artifact_source_head=24882c5218199e0fb9d73b513be0a5feba1f1b08
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_merged_map_family_census_24882c52_20260715T202223CST
current_v24_artifact_root_sha256=33626198d8945e7f102946005bfa6b9db4762d93b1146896c9ebfd99ad633717
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=map_family_census_passed_route_census_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_outcome_blind_route_census_tdd_preflight_only

## Gate 8: Outcome-Blind Route-Census TDD and Preflight

Status: passed. Route-census execution is next.

The route contract makes one attempt per fixed-builder drivable start lanelet.
It sorts starts, follows the smallest numeric unvisited successor, prevents a
lanelet repeat, and keeps the first source-arc prefix reaching `>=80m`. A dead
end, cycle, or the frozen 100-hop ceiling ends that attempt without redrawing
it. Every qualifying and nonqualifying start remains in the denominator.

Exact directed geometry identities are sampled at 1m, quantized at 1mm, and
deduplicated only inside the adjudicated map family. All duplicate source
records retain receipts. The existing source-only corridor thresholds are
frozen at `3m / 20 samples / 15 degrees`; connected components remain
indivisible for split construction instead of being counted as independent
support. No result was used to select any threshold or route.

The preflight reverified the static-census, fixed-builder, and map-family roots
and built the full execution plan without running a worker. The plan contains
`10 blobs / 12 paths / 4 map families`; the empty and intersection maps keep
their earlier map-local failure receipts. Lanelet2 1.2.2, the fixed-DP builder,
and both source-preserving adapter functions import in the isolated runtime.
The worker call order is regulatory adapter, projection fallback, then builder.

All `30 / 0` checks passed. AutoDL had `49,740,017,664` free bytes, zero active
route-census processes, aligned clean CAMP/origin at
`78a276f9bd7323b681cd8a440ba8d36262335292`, and clean fixed DP at
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. AutoDL also passed all 27 v24
tests, four-script compilation, and diff checks.

Route census execution did not start. The model, candidate generation,
outcome, and holdout remained unopened. No source map, DP file, route asset,
split, seed, corpus, selector, or claim changed. Immutable preflight
artifact/root:
`/root/autodl-tmp/camp_dp_v24_outcome_blind_route_census_preflight_78a276f9_20260715T203134CST`
/
`2550ecef112c79be18c1ec4a11e5425db543e7f58e7a167f1c854ee84eb9475a`.

Source B continues, and no global stop is authorized. The next gate may run
the frozen route census once, preserving each map and start-lanelet receipt.

current_v24_status=v24_outcome_blind_route_census_preflight_passed
current_v24_artifact_source_head=78a276f9bd7323b681cd8a440ba8d36262335292
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_outcome_blind_route_census_preflight_78a276f9_20260715T203134CST
current_v24_artifact_root_sha256=2550ecef112c79be18c1ec4a11e5425db543e7f58e7a167f1c854ee84eb9475a
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=route_census_preflight_passed_execution_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_outcome_blind_route_census_execution_only

## Gate 9: Outcome-Blind Route-Census Execution

Status: passed. Independent route-census review is next.

The controller executed the frozen plan once. Worker accounting is `10 / 0 /
0` completed / failed / execution-invalid blobs. Every loaded source blob ran
in its own process; the two byte-copy paths reused their representative blob
receipt. Source bytes modified: `false`.

The complete result is `603 / 552 / 51` start attempts / qualifying /
below-threshold. Every start receipt remains present. The qualifying records
produce `552 / 401 / 151 / 5` raw / exact-deduplicated / duplicate /
corridor-group counts. Exact duplicates point to their deterministic retained
record; corridor groups remain indivisible and are not discarded.

Three independent map families retain `>=80m` route support. Deduplicated
counts for Kashi/standard, four-track-highway, and simple-cross are respectively
`375 / 24 / 2`. The loadable slope family has zero `>=80m` support and remains
in map/start failure accounting; it does not stop the other families. Thus the
later split can still operate at map-family level after review.

All `20 / 0` execution checks passed. Free space was
`49,739,603,968` before and `49,711,423,488` after, above the frozen 10 GiB
floor. All 28 v24 tests, script compilation, and diff checks passed on AutoDL.
The model, candidate generation, outcomes, and holdout remained unopened. No
route asset, split, seed, corpus, selector, claim, deployment, or activation
was created.

One launch attempt used an incorrect guessed full expansion of the already
known short source HEAD. It stopped immediately after remote fast-forward at
the exact-HEAD assertion and did not create an execution artifact or worker.
The controller read the live full SHA, confirmed zero processes and zero
execution artifacts, then started the sole scientific execution above. This
is a controller-observation correction, not a repeated route census.

Immutable execution artifact/root:
`/root/autodl-tmp/camp_dp_v24_outcome_blind_route_census_execution_88c57e55_20260715T203449CST`
/
`e933cc37f8635867d3f34c4efeb3a54858a0f1c20c0db387dc73df20dd81bf5d`.

Source B has substantial source-valid route support, so neither a source-local
nor global stop is authorized. Independent review must rehash the artifact,
recompute all attempt/dedup/family/corridor counts, and must not reexecute a
route worker or open K=8.

current_v24_status=v24_outcome_blind_route_census_execution_passed
current_v24_artifact_source_head=88c57e5597ffdbcc60c26a1c6232b3796b9e9a18
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_outcome_blind_route_census_execution_88c57e55_20260715T203449CST
current_v24_artifact_root_sha256=e933cc37f8635867d3f34c4efeb3a54858a0f1c20c0db387dc73df20dd81bf5d
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=route_census_execution_passed_review_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_outcome_blind_route_census_independent_review_only

## Gate 10: Outcome-Blind Route-Census Independent Review

Status: passed. Single-record fixed-DP source-probe design/TDD/preflight are
next.

The reviewer rehashed the sealed execution and static-census roots, then
recomputed the route census directly from the stored JSON and live frozen map
bytes. It reproduced 10 completed workers with 10 distinct worker PIDs and all
return codes zero; 603 attempts; 552 qualifying and 51 nonqualifying routes;
552 raw records; 401 retained identities; 151 exact duplicate receipts; and
five corridor groups. The 51 nonqualifying attempts are exactly
`dead_end_before_80m`.

Every raw record key is unique. Retained `(map_family_id, identity_sha256)`
pairs are unique. The 552 deduplication receipts cover every raw record, and
the five corridor groups cover all 401 retained records exactly once. The
review independently reproduced family support `375 / 24 / 2` for
Kashi/standard, four-track-highway, and simple-cross, with zero slope routes.
It also confirmed all 14 live source SHA values still equal the frozen
receipts.

All `31 / 0` independent checks passed. The review did not execute a route
worker and did not call the route-census controller. The model, candidates,
outcomes, holdout, split, seeds, corpus, and claims remained unopened. Its
decision is
`route_census_review_passed_three_family_source_valid_support`.

Immutable review artifact/root:
`/root/autodl-tmp/camp_dp_v24_outcome_blind_route_census_independent_review_4d92f6b5_20260715T203745CST`
/
`210cec6201e098169b2c606e265c6e95efc40f6593489d41802ddd1b1010795f`.

Three independent source-valid route families remain, so the global stop is
unauthorized. The next gate freezes a single-record fixed-DP source probe and
its candidate-tensor receipt contract before any K=8 execution. It may not
select a favorable route from results; route choice must be source-only and
deterministic from the sealed census.

current_v24_status=v24_outcome_blind_route_census_review_passed
current_v24_artifact_source_head=4d92f6b5ffe9351a374c8c3bf4e9092f5225cc9f
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_outcome_blind_route_census_independent_review_4d92f6b5_20260715T203745CST
current_v24_artifact_root_sha256=210cec6201e098169b2c606e265c6e95efc40f6593489d41802ddd1b1010795f
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=route_census_review_passed_single_record_probe_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_fixed_dp_single_record_source_probe_tdd_static_preflight_only
