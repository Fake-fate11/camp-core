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

## Gate 11: Fixed-DP Single-Record Source-Probe TDD and Preflight

Status: passed. Single-record source-probe execution is next.

The source-only selector chose the lexicographically minimum
`(map_family_id, identity_sha256, record_key)` from all 401 retained routes.
The frozen record is family `map_family_828a913c2f9a`, identity
`1962e44a5dd0ace089aeb9011d5b70e05dfa6ae5adeec4450a6c20e3e09776b2`,
and record key
`map_family_828a913c2f9a/c13a9234727186c7/3002178/1962e44a5dd0ace0`.
It belongs to the unchanged four-track-highway source map. No metric, outcome,
candidate, or prior probe chose this record.

The preflight freezes `24001 / 8 / 1` seed / candidates / ticks. It uses the
existing fixed-DP native runner, v22 source-valid selection policy, and the
read-only v18/v22 14D baseline solely for call-path capability. Training,
calibration, holdout, claims, and parameter tuning remain forbidden.

All `29 / 0` preflight checks passed. The deterministic Route asset SHA is
`63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd`;
probe config SHA is
`1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc`;
and the nested existing-runner preflight root is
`58c9b506dee7ebd27095d223ce4ff52aafcdbbf8bef306b898f5d6f9f0497441`.
Every checkpoint, args, map, route, scale, and weight SHA verified. CUDA was
available and free space was `49,709,850,624` bytes. The native runner reported
zero arms and zero routes executed; the checkpoint was hashed but not loaded.
Model, candidate generation, outcomes, and holdout remained unopened.

The first preflight exposed a Python 3.9 evidence-sealer compatibility defect:
`Path.write_text(newline=...)` is unsupported. Preparation and asset checks had
completed, but no model or replay ran. The failed attempt was preserved and
externally sealed at
`/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_preflight_c96cf276_20260715T204500CST`
/
`b1886120e0b39d29ae9f7926ba59921851d248b9f769128eecd74459f47f3323`.
The minimal compatibility fix uses `Path.open(..., newline="\n")`; local native
regressions passed before push.

The retry's production preflight passed once. Its first outer verification
scope included an existing Python-3.10-only annotated test and failed during
Python 3.9 collection. That output remains sealed; preparation/native preflight
were not repeated. The corrected outer scope passed all `35` remote v24 tests,
script compilation, and diff checks.

Immutable successful artifact/root:
`/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_a53d6ee3_20260715T204719CST`
/
`cedcc6fe8ca00fff7bbab4eeb92faa2f4cd5d172ec8b1d9d1cb9168ead955394`.

Source B continues. The next gate may execute this exact config once. Failure
cannot authorize a result-selected replacement route; normal code defects may
be minimally fixed and the same frozen record retried with explicit evidence.

current_v24_status=v24_fixed_dp_single_record_source_probe_preflight_passed
current_v24_artifact_source_head=a53d6ee3471c4051a18d1cbe8d408b378dd6197f
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_preflight_retry_a53d6ee3_20260715T204719CST
current_v24_artifact_root_sha256=cedcc6fe8ca00fff7bbab4eeb92faa2f4cd5d172ec8b1d9d1cb9168ead955394
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=single_record_probe_preflight_passed_execution_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_fixed_dp_single_record_source_probe_execution_only

## Gate 12: Fixed-DP Python 3.9 Runtime-Compatibility Remediation Preflight

Status: passed. Retry the same frozen single-record source probe next.

The first exact-config execution stopped during module import with
`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`. The
fixed Diffusion Planner source uses a Python 3.10 union annotation, while the
existing complete CAMP runtime is Python 3.9.25. The failure occurred before
checkpoint load, candidate generation, replay, outcomes, or holdout access.
It is preserved at
`/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_execution_f345642c_20260715T205047CST`
with root
`0eb8cae8aa9611ad3cc51866313704f71c9e48c074f453a326f7851caf2de58c`.

The minimal remediation is a process-local import loader that compiles only
Python source under `/root/autodl-tmp/Diffusion-Planner` with postponed
annotation evaluation. It modifies no fixed-DP file, config, weight,
checkpoint, request, candidate tensor, trajectory, system package, or global
Python installation. TDD exposed that an existing `.pyc` could bypass the
source compiler; a second test required the loader to read the immutable source
bytes directly. Local results are 39 v24 tests passed, script compilation
passed, and diff check passed.

The first remote compatibility preflight reproduced the cached-bytecode bypass
without loading the model. It is sealed at
`/root/autodl-tmp/camp_dp_v24_fixed_dp_python39_annotation_compatibility_preflight_d3a387b9_20260715T205724CST`
with root
`acfff0854b551f14ff0264569ebb572dfe6929a76c39db89956c909749313938`.
This was a normal import defect and did not authorize source or global
closeout.

After the `.pyc` bypass fix, the fresh Python 3.9 preflight imported the frozen
`scenario_generation.replay` and `scenario_generation.tensor_converter`
modules from the fixed-DP root. The process-local finder was installed for that
exact root, and all five registered native-source SHA values matched. Remote
script compilation and all 39 v24 tests passed. The only stderr was an existing
nonfatal `wandb`/`pkg_resources` deprecation warning. CAMP and DP tracked state
were clean at
`03d1b02a047ca2c216821835a16e345c4046d749` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`; free space was 46.30 GiB.

Immutable successful artifact/root:
`/root/autodl-tmp/camp_dp_v24_fixed_dp_python39_annotation_compatibility_preflight_retry_03d1b02a_20260715T205856CST`
/
`1ab93bb525cee1481f7b9ab307fd13a431160e144b3145df3ccd01f340e936ef`.

The source-only route, identity, seed 24001, fixed K=8, and one-tick scope are
unchanged. Branch B therefore continues. The next gate may retry only that
same exact-config execution; it may not select a replacement route from
results.

current_v24_status=v24_fixed_dp_single_record_source_probe_runtime_compatibility_preflight_passed
current_v24_artifact_source_head=03d1b02a047ca2c216821835a16e345c4046d749
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_fixed_dp_python39_annotation_compatibility_preflight_retry_03d1b02a_20260715T205856CST
current_v24_artifact_root_sha256=1ab93bb525cee1481f7b9ab307fd13a431160e144b3145df3ccd01f340e936ef
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=single_record_probe_runtime_compatibility_passed_execution_retry_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_fixed_dp_single_record_source_probe_execution_only

## Gate 13: Fixed-DP Single-Record Source-Probe Execution

Status: passed. Independent evidence review is next.

The controller executed the exact source-only record frozen in Gate 11: family
`map_family_828a913c2f9a`, identity
`1962e44a5dd0ace089aeb9011d5b70e05dfa6ae5adeec4450a6c20e3e09776b2`,
seed `24001`, fixed `K=8`, and one tick. The route/config SHA values remained
`63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd`
and
`1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc`.
No result-selected route or seed replacement occurred.

One detached-controller launch was interrupted after its SSH monitor failed.
After confirming zero related processes, zero nested evidence, and no run exit,
the controller sealed it as execution-invalid at
`/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_execution_retry_ab8d9735_20260715T210212CST`
with root
`19cdfb2a893602d13077c9c87f0f3880c55a46ad4e25c3981122f375ae517081`.
It is not a scientific result. The successful detached controller then ran the
same immutable config once; no alternative route was authorized.

The native runner produced one CAMP observation arm with one tracker tick. All
eight candidate rows were source-complete, source-valid, and physically
feasible. Candidate-tensor SHA before and after selection was identically
`147379fe4ac82828f879c78f17ffc47b432019f1f74723a557980a776c680fb5`.
Candidate 0 and the operational default output were elementwise identical with
SHA
`64b71a3496577d6b3a2dd1c4bd3d08fbb229d4ca92c9196b42b8e1a5db31e5ee`
and zero maximum absolute difference. Native K-ranking provenance remains
false. The affine source-valid baseline selected existing candidate index 3;
its row/trajectory SHA is
`318b6829b64d623d8e39fa9175e33fb37426fea8395611436fe65dd0f9761e59`.
The candidate tensor was not generated, repaired, blended, or postprocessed by
CAMP.

The tick's atom matrix SHA is
`79c07ef0b5d20cf7d6d1b2fad44d00743054aab0f75776511092716671804314`;
the score contract is `score_k(w)=a_k^T w`; and the effective read-only schema
is `dp_camp_v10_14d`. This is capability evidence only. It does not authorize
the inherited weights, atom mask, training, outcome use, holdout opening, or a
safety/CAMP-over-DP claim.

Execution exit was zero in 7.461 seconds. Remote script compilation, all 39
v24 tests, and diff check passed. Free space after the gate was 46.29 GiB.
CAMP/DP tracked state stayed clean at
`ab8d973598ae5dfa68e707caaabf9147b69cd49c` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. The only stderr was the existing
nonfatal `wandb`/`pkg_resources` deprecation warning.

Immutable successful artifact/root:
`/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_execution_retry2_ab8d9735_20260715T210344CST`
/
`3b3d759620ee0fe98d7b56f4305920fac015372ddaa3ef9126416ac2cc5ace16`.

Branch B has now demonstrated real source-valid K=8 support on one source-only
route. Global stop remains unauthorized. The next gate is a read-only
independent recomputation of the sealed receipt and SHA chain; it must not load
the model or rerun the probe.

current_v24_status=v24_fixed_dp_single_record_source_probe_execution_passed
current_v24_artifact_source_head=ab8d973598ae5dfa68e707caaabf9147b69cd49c
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_execution_retry2_ab8d9735_20260715T210344CST
current_v24_artifact_root_sha256=3b3d759620ee0fe98d7b56f4305920fac015372ddaa3ef9126416ac2cc5ace16
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=single_record_probe_execution_passed_independent_review_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_fixed_dp_single_record_source_probe_independent_review_only

## Gate 14: Fixed-DP Single-Record Source-Probe Independent Review

Status: passed. Map-family split plan/TDD/static preflight are next.

The pure-stdlib reviewer read only the sealed Gate 13 artifact. It did not
import fixed-DP or CAMP model modules, load the checkpoint, generate a
candidate, rerun the probe, access outcomes, or open holdout. It independently
rehashed every outer and nested manifest entry, then recomputed the frozen
config, route, seed, K, candidate, mask, affine-score, and claim boundaries.

All `127 / 0` checks passed. The reviewer reproduced eight distinct candidate
row SHA values, candidate-tensor SHA
`147379fe4ac82828f879c78f17ffc47b432019f1f74723a557980a776c680fb5`
before and after selection, candidate-0/default SHA
`64b71a3496577d6b3a2dd1c4bd3d08fbb229d4ca92c9196b42b8e1a5db31e5ee`,
selected index 3, and selected row SHA
`318b6829b64d623d8e39fa9175e33fb37426fea8395611436fe65dd0f9761e59`.
All eight source-complete, source-valid, and physical-feasibility flags were
true. Global RNG and candidate tensor receipts were unchanged.

The review also found two native-result path strings that retain the runner's
staging `native_execution.tmp` prefix after atomic directory rename. Replacing
only that prefix with the sealed `native_execution` directory resolves both
files, and their bytes are already covered by the outer SHA manifest. Thus this
is an artifact-layout defect, not missing K=8 evidence. It must be corrected
before formal corpus generation; the successful source probe will not be
rerun.

Remote script compilation, all 40 v24 tests, and diff check passed. CAMP/DP
tracked state remained clean at
`3a70498f6a9722742525598d69cf77a8a2c8bc6c` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Immutable review artifact/root:
`/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_independent_review_3a70498f_20260715T210836CST`
/
`a232b1bf0ac8da388fcd081404f9a0f3c4810dab2047e58afda89ed124d4912a`.

Branch B therefore has independently reviewed source-valid K=8 support and
continues. With three independent route-supporting map families, the frozen
split regime is map-family-level train/calibration/holdout. The next gate may
plan and statically preflight that split from the sealed 401-route census. It
must remain outcome-blind and may not open holdout records.

current_v24_status=v24_fixed_dp_single_record_source_probe_independent_review_passed
current_v24_artifact_source_head=3a70498f6a9722742525598d69cf77a8a2c8bc6c
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_fixed_dp_single_record_source_probe_independent_review_3a70498f_20260715T210836CST
current_v24_artifact_root_sha256=a232b1bf0ac8da388fcd081404f9a0f3c4810dab2047e58afda89ed124d4912a
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=single_record_probe_review_passed_split_plan_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_map_family_split_plan_tdd_static_preflight_only

## Gate 15: Map-Family Split Plan, TDD, and Static Preflight

Status: passed. Split-manifest execution is next.

The outcome-blind plan consumes only the sealed 401-route census and makes
each map family indivisible. It enumerates all nonempty family assignments and
minimizes absolute route-count deviation from 70/10/20; ties prefer holdout
closest to 20%, then the larger train set, then lexicographic order. No K=8
score, outcome, label, metric, holdout result, or prior route performance is an
input.

The source-only assignment is:

- `map_family_d7f16a17d3eb`, Kashi/standard, 375 routes: train;
- `map_family_f62e06cd1303`, simple-cross, 2 routes: calibration;
- `map_family_828a913c2f9a`, four-track-highway, 24 routes: holdout.

This yields `375 / 2 / 24` routes and `1875 / 10 / 120` route-seed records.
Primary seeds are frozen as `24001, 24002, 24003, 24004, 24005`; seed 24001
is the sole pilot seed. All five corridor groups, each route, and all seeds for
that route remain within one family-level split. The skewed ratio is an honest
consequence of whole-family isolation; no route can cross a family boundary to
improve it.

All `41 / 0` preflight checks passed. Every source-manifest file rehashed, the
route denominator and five corridor groups were fully covered, and three
supporting families were reproduced. Plan SHA is
`55fc3f0aeca1daff1177d533394162b44e0684f7a9e0756d1981042baa265ff3`.
The preflight did not materialize a formal split manifest or load a model,
generate candidates, access outcomes, or open holdout.

Remote script compilation, all 42 v24 tests, and diff check passed. Free space
was 46.29 GiB. CAMP/DP tracked state remained clean at
`c4287db16490f9e39fb6ce87f908c07da4156410` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Immutable preflight artifact/root:
`/root/autodl-tmp/camp_dp_v24_map_family_split_static_preflight_c4287db1_20260715T211347CST`
/
`3e3254858ed5daacd1d97f3967bd598e54fdf707f67c66ac3908ba7d46a7eff7`.

Branch B continues. The next gate may only materialize all 401 route identities,
their family/corridor membership, assigned split, and five frozen seeds from
this exact plan. It may not run a simulator or access holdout outcomes.

current_v24_status=v24_map_family_split_static_preflight_passed
current_v24_artifact_source_head=c4287db16490f9e39fb6ce87f908c07da4156410
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_map_family_split_static_preflight_c4287db1_20260715T211347CST
current_v24_artifact_root_sha256=3e3254858ed5daacd1d97f3967bd598e54fdf707f67c66ac3908ba7d46a7eff7
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=split_static_preflight_passed_execution_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_map_family_split_execution_only

## Gate 16: Map-Family Split Execution

Status: passed. Independent split review is next.

The execution consumed the sealed route-census root and exact preflight plan
SHA
`55fc3f0aeca1daff1177d533394162b44e0684f7a9e0756d1981042baa265ff3`.
It materialized one formal manifest containing every retained route identity,
map family, corridor group, assigned split, and the frozen five-seed namespace.
No assignment was recomputed from outcomes and no route or seed was dropped.

The manifest contains 401 route records and 2005 route-seed assignments.
Train/calibration/holdout counts remain `375 / 2 / 24` routes and
`1875 / 10 / 120` route-seeds. Manifest SHA is
`c57382fe500cd80c9bf37f402a567720756bdb0b25bb56d80bcf1b5ada699b1b`.
Plan SHA matched the static preflight exactly. The gate did not run a simulator,
load a model, generate candidates, access outcomes, or open holdout.

All `41 / 0` execution checks passed. Remote script compilation, all 43 v24
tests, and diff check passed. Free space remained 46.29 GiB. CAMP/DP tracked
state was clean at
`096747e2e83af29cb4f4aa7c175e1f56793b50a6` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Immutable execution artifact/root:
`/root/autodl-tmp/camp_dp_v24_map_family_split_execution_096747e2_20260715T211547CST`
/
`b923895a594c00a01c244a2342816539baa1c8400a0aeefb49946bcac37519af`.

Branch B continues. The next gate must independently rehash the execution and
source census, recompute full route/corridor/family/seed coverage and zero
overlap, and confirm the skewed whole-family split without rewriting the
manifest or opening holdout.

current_v24_status=v24_map_family_split_execution_passed
current_v24_artifact_source_head=096747e2e83af29cb4f4aa7c175e1f56793b50a6
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_map_family_split_execution_096747e2_20260715T211547CST
current_v24_artifact_root_sha256=b923895a594c00a01c244a2342816539baa1c8400a0aeefb49946bcac37519af
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=split_execution_passed_independent_review_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_map_family_split_independent_review_only

## Gate 17: Map-Family Split Independent Review

Status: passed. Corpus plan/TDD/artifact-layout remediation/static preflight are
next.

The pure-stdlib reviewer independently rehashed the sealed split execution and
route-census artifacts, recomputed the split manifest's canonical SHA, and
rebuilt route-to-family, route-to-corridor, route-to-split, and route-to-seed
mappings from both sources. It did not call the split builder, rewrite the
manifest, load a model, generate candidates, access outcomes, or open holdout.

All `116 / 0` checks passed. The full 401-route denominator and all 2005
route-seed pairs are present exactly once. Train/calibration/holdout contain
`375 / 2 / 24` routes, `1875 / 10 / 120` route-seed pairs, one map family each,
and `1 / 1 / 3` corridor groups. Family, corridor, route key, route identity,
and route-seed overlap are all zero. Every route retains exactly seeds
`24001-24005`. Plan and manifest SHA values remain
`55fc3f0aeca1daff1177d533394162b44e0684f7a9e0756d1981042baa265ff3`
and
`c57382fe500cd80c9bf37f402a567720756bdb0b25bb56d80bcf1b5ada699b1b`.

Remote script compilation, all 44 v24 tests, and diff check passed. CAMP/DP
tracked state remained clean at
`90f73ab2c2c473be48eb6cc3c4bcea07747fce50` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Immutable review artifact/root:
`/root/autodl-tmp/camp_dp_v24_map_family_split_independent_review_90f73ab2_20260715T211904CST`
/
`637b1920421639c949814bd0448379f9677089026a90b0bc0e010661670845df`.

Branch B continues. The next gate plans causal per-tick K=8 corpus generation
using train routes only. Before generation, TDD must correct the runner's two
staging-path receipts so future formal artifacts point at their final sealed
location. The gate may preflight route/seed/capacity/runtime contracts but may
not generate the corpus, access calibration/holdout outcomes, or tune atoms.

current_v24_status=v24_map_family_split_independent_review_passed
current_v24_artifact_source_head=90f73ab2c2c473be48eb6cc3c4bcea07747fce50
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_map_family_split_independent_review_90f73ab2_20260715T211904CST
current_v24_artifact_root_sha256=637b1920421639c949814bd0448379f9677089026a90b0bc0e010661670845df
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=split_review_passed_corpus_plan_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_corpus_plan_tdd_artifact_layout_remediation_static_preflight_only

## Gate 18: Split Seed-Namespace and Artifact-Path Remediation Preflight

Status: passed. Corrected split-manifest execution is next.

While adapting the reviewed split to the existing native corpus contract, the
controller found that the first manifest reused numeric seeds `24001-24005` in
train, calibration, and holdout. Route-seed pairs were distinct because routes
were disjoint, but the explicit v24 contract also requires the numeric seed
namespace itself not to cross a split. No corpus, outcome, calibration, or
holdout execution had begun, so a source-only remediation remains legal.

The sealed Gate 17 review is preserved; it is superseded only as a future
corpus/evaluation input. The corrected namespaces are:

- train: `24001-24005`;
- calibration: `24101-24105`;
- holdout: `24201-24205`.

Every route still has exactly five primary seeds, and the first seed in each
namespace is its split's pilot seed. Route and route-seed counts remain
`375 / 2 / 24` and `1875 / 10 / 120`. The new plan SHA is
`52ea1a5c498c73be64ed9a2f4ec6093574eb534f25e7dd0f82081b683a376539`.

The same TDD checkpoint also fixes future atomic evidence receipts: absolute
paths rooted under a staging `.tmp` directory are rewritten to the final
artifact root before sealing. It changes no scientific tensor or old sealed
artifact, and the successful single-record source probe is not rerun.

All `41 / 0` remediation preflight checks passed. Remote script compilation,
all 45 v24 tests, and diff check passed. CAMP/DP tracked state remained clean at
`0cc08b26fa1a12ea9160f95e59bc1ae59ff52324` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Immutable remediation preflight artifact/root:
`/root/autodl-tmp/camp_dp_v24_split_seed_namespace_remediation_preflight_0cc08b26_20260715T212416CST`
/
`7e08bcb6a4598398eeb427bc9f3a7267572090ec448c5b3a7e66b4367c46e9a1`.

The next gate may only materialize the corrected split manifest from this plan.
It may not generate a corpus, model candidate, label, outcome, or holdout
result.

current_v24_status=v24_split_seed_namespace_remediation_preflight_passed
current_v24_artifact_source_head=0cc08b26fa1a12ea9160f95e59bc1ae59ff52324
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_split_seed_namespace_remediation_preflight_0cc08b26_20260715T212416CST
current_v24_artifact_root_sha256=7e08bcb6a4598398eeb427bc9f3a7267572090ec448c5b3a7e66b4367c46e9a1
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=split_seed_remediation_preflight_passed_execution_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_split_seed_namespace_remediation_execution_only

## Gate 19: Corrected Split Seed-Namespace Execution

Status: passed. Independent review of the corrected manifest is next.

The execution consumed remediation plan SHA
`52ea1a5c498c73be64ed9a2f4ec6093574eb534f25e7dd0f82081b683a376539`
and materialized all 401 route records with 2005 route-seed assignments. Map
family, corridor group, route identity, and split assignments are unchanged
from the first split. Only the preregistered numeric seed namespaces differ:
train `24001-24005`, calibration `24101-24105`, and holdout `24201-24205`.
Their union has 15 members and every cross-split intersection is empty.

The corrected manifest SHA is
`ba814ee3da89fc6d9b3ae1ce9a9929e38bebc6349f3871f8d105f285207bf5fa`.
Route and route-seed counts remain `375 / 2 / 24` and `1875 / 10 / 120`.
No route was dropped, replaced, or reassigned. No corpus, simulator, model,
candidate, label, outcome, calibration, or holdout execution occurred.

All `41 / 0` execution checks passed. Remote script compilation, all 45 v24
tests, and diff check passed. CAMP/DP tracked state remained clean at
`6f3e923f6fe3a1ff3c15d05a0cd8bfc45cb3d337` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Immutable corrected execution artifact/root:
`/root/autodl-tmp/camp_dp_v24_split_seed_namespace_remediation_execution_6f3e923f_20260715T212602CST`
/
`3f51241b575c00f091d5aa283aaf78f1a10816f2a11cf4bbc50346675f79cd42`.

The next gate independently rehashes and recomputes the corrected manifest,
including numeric seed-namespace zero overlap. It may not call split execution
or begin corpus generation.

current_v24_status=v24_split_seed_namespace_remediation_execution_passed
current_v24_artifact_source_head=6f3e923f6fe3a1ff3c15d05a0cd8bfc45cb3d337
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_split_seed_namespace_remediation_execution_6f3e923f_20260715T212602CST
current_v24_artifact_root_sha256=3f51241b575c00f091d5aa283aaf78f1a10816f2a11cf4bbc50346675f79cd42
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=split_seed_remediation_execution_passed_review_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_split_seed_namespace_remediation_independent_review_only

## Gate 20: Corrected Split Seed-Namespace Independent Review

Status: passed. Corpus plan/TDD/static preflight are next.

The reviewer independently rehashed the corrected execution and source census,
recomputed canonical plan/manifest identities, and rebuilt every mapping without
calling split execution. All `115 / 0` checks passed. Plan and manifest SHA are
`52ea1a5c498c73be64ed9a2f4ec6093574eb534f25e7dd0f82081b683a376539`
and
`ba814ee3da89fc6d9b3ae1ce9a9929e38bebc6349f3871f8d105f285207bf5fa`.

The reviewer reproduced 401 routes and 2005 route-seed pairs, with
train/calibration/holdout counts `375 / 2 / 24` and `1875 / 10 / 120`.
Families, corridors, route keys, route identities, and route-seed pairs are
pairwise disjoint. The 15 numeric seeds are also pairwise disjoint across
splits. Every route has exactly the five seeds assigned to its split.

The review did not rewrite the manifest, run a simulator, load a model,
generate candidates, access outcomes, or open holdout. Remote compilation, all
45 v24 tests, and diff check passed. CAMP/DP tracked state remained clean at
`39227dd51131ca79f7649ddbe02bb1e5ad9c8024` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Immutable corrected review artifact/root:
`/root/autodl-tmp/camp_dp_v24_split_seed_namespace_remediation_independent_review_39227dd5_20260715T212743CST`
/
`2b4a1a99af7cc369853d95f9f762cf81dbb6e56dda991adec5e78fd7698f5d3c`.

The corrected manifest is now the sole v24 split input for corpus and later
evaluation. The next gate plans and statically preflights train-only causal K=8
snapshot generation. It may materialize source-derived route assets but may not
run a simulator, generate a candidate, access calibration/holdout outcomes, or
tune any atom.

current_v24_status=v24_split_seed_namespace_remediation_independent_review_passed
current_v24_artifact_source_head=39227dd51131ca79f7649ddbe02bb1e5ad9c8024
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_split_seed_namespace_remediation_independent_review_39227dd5_20260715T212743CST
current_v24_artifact_root_sha256=2b4a1a99af7cc369853d95f9f762cf81dbb6e56dda991adec5e78fd7698f5d3c
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=split_seed_remediation_review_passed_corpus_plan_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_corpus_plan_tdd_static_preflight_only

## Gate 21: Native Corpus Plan, TDD, and Static Preflight

Status: passed. Independent static review is next.

The plan freezes `375 / 5 / 1875` train routes / seeds / route-seed runs.
Every run permits at most `64` native ticks and `sample_every_ticks=1`, with no
thinning, for a theoretical ceiling of `120000` causal K=8 snapshots. Feature
payload remains the approved 14D atom matrix, source-valid mask, and candidate
row hashes. Map-family, corridor, route, split, and seed identities remain
receipt-only. Candidate immutability and candidate-0/default identity remain
mandatory.

Execution is preregistered in two phases: all 375 train routes with seed
`24001`, then the same routes with seeds `24002-24005`. The first phase is only
a breadth/disk/runtime pilot. It cannot tune atoms, weights, thresholds,
routes, seeds, or failure policy. Every attempt remains in the denominator;
there is no outcome-based thinning, redraw, or replacement.

The AutoDL preflight rehashed the corrected split and route census, the fixed
DP inputs, four selector/template assets, and every unique source map. It
materialized 375 source-derived route assets and validated all 1875 run configs.
All `64 / 0` checks and all `54` v24 tests passed. The evidence artifact is
2.9 MiB and left `46.2881 GiB` free, above the 10 GiB floor. CAMP and DP tracked
state remained clean at `8d9398d750d77075b662fa0741b69fc5e944e0cd` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`.

Model, simulator, candidate generation, outcomes, calibration, holdout, and
training execution all remained unopened. Plan and corpus-manifest SHA256 are
`d1431ec7a0583d24e16b655b06264450761c770d503262658e5b63612e745e7b`
and
`87e65ae8347aa225282cfa05a1330d2f7b39464ecda83cae997f1a8c081895fc`.

Immutable preflight artifact/root:
`/root/autodl-tmp/camp_dp_v24_native_corpus_static_preflight_8d9398d7_20260715T213749CST`
/
`17b5a8ca7c974997b1cd89905b50e86e95f5a032cab171e44898c48973867e72`.

The next gate independently rehashes the preflight and recomputes the plan,
manifest, route assets, config receipts, boundaries, and disk gate. It may not
load the model, run the simulator, generate candidates, train, or open outcomes.

current_v24_status=v24_native_corpus_plan_tdd_static_preflight_passed
current_v24_artifact_source_head=8d9398d750d77075b662fa0741b69fc5e944e0cd
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_native_corpus_static_preflight_8d9398d7_20260715T213749CST
current_v24_artifact_root_sha256=17b5a8ca7c974997b1cd89905b50e86e95f5a032cab171e44898c48973867e72
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=native_corpus_static_preflight_passed_review_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_native_corpus_static_preflight_independent_review_only

## Gate 22: Native Corpus Static-Preflight Independent Review

Status: passed. The frozen first-seed capability pilot is next.

The reviewer verified the preflight, corrected split, and route-census evidence
roots independently. It recomputed the corpus plan and manifest SHA values,
confirmed exact train membership, independently reloaded all 375 route assets,
checked six live source-map paths, and rebuilt all 1875 run configs and their
content hashes without importing or calling the preflight builder. All
`3829 / 0` checks passed.

The review reconfirmed the `375 / 5 / 1875` train denominator, distinct train
seed namespace `24001-24005`, per-tick/no-thinning capture, `120000` theoretical
snapshot ceiling, route/corridor/source identities, candidate immutability
requirements, and closed calibration/holdout/outcome boundaries. It did not
call the preflight builder, run the simulator, load the model, generate a
candidate, train, or access an outcome.

All `59` v24 tests, remote compilation, and diff check passed. CAMP/DP tracked
state remained clean at `8b520eb14426b796edb3812df8499d7cd97557cc` and
`7a1d33da277a1992ec474b5383a0c963c72e04e4`. The review left `46.2872 GiB`
free, above the 10 GiB floor.

Immutable review artifact/root:
`/root/autodl-tmp/camp_dp_v24_native_corpus_static_preflight_review_8b520eb1_20260715T214248CST`
/
`fe69c61e9da0a11233bb6c5862e2becc8fddb4e1e8e133c60cb21e80a5efe6db`.

The next gate is the capability pilot over all 375 train routes at seed
`24001` only. It may exercise fixed-DP K=8 generation and capture causal
snapshots, but it may not tune or remove any route, seed, atom, threshold, or
failure receipt. Before launch it must prove no duplicate pilot is active and
retain more than 10 GiB free.

current_v24_status=v24_native_corpus_static_preflight_independent_review_passed
current_v24_artifact_source_head=8b520eb14426b796edb3812df8499d7cd97557cc
current_v24_final_synced_head=pending_current_docs_commit_not_source_drift
fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4
current_v24_artifact=/root/autodl-tmp/camp_dp_v24_native_corpus_static_preflight_review_8b520eb1_20260715T214248CST
current_v24_artifact_root_sha256=fe69c61e9da0a11233bb6c5862e2becc8fddb4e1e8e133c60cb21e80a5efe6db
source_a_status=source_ineligible_missing_authorized_build_prerequisites
source_a_terminal=true
source_b_status=native_corpus_static_preflight_review_passed_pilot_pending
source_b_terminal=false
authorized_source_count=2
source_terminal_count=1
global_stop_authorized=false
global_stop_reason=none
next_work_target=v24_native_corpus_capability_pilot_all_train_routes_seed_24001_only
