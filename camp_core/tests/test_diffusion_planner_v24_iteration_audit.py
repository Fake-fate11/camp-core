from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DESIGN = (
    ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-15-v24-independent-lanelet2-source-control-design.md"
)
AUDIT = ROOT / "docs" / "diffusion_planner_v24_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"
BRANCH_A_PLAN = (
    ROOT
    / "docs"
    / "superpowers"
    / "plans"
    / "2026-07-15-v24-autoware-extension-isolated-build.md"
)

POINTER = (
    "current_v24_status=v24_native_corpus_static_preflight_independent_review_passed",
    "current_v24_artifact_source_head=8b520eb14426b796edb3812df8499d7cd97557cc",
    "current_v24_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v24_artifact=/root/autodl-tmp/camp_dp_v24_native_corpus_static_preflight_review_8b520eb1_20260715T214248CST",
    "current_v24_artifact_root_sha256=fe69c61e9da0a11233bb6c5862e2becc8fddb4e1e8e133c60cb21e80a5efe6db",
    "source_a_status=source_ineligible_missing_authorized_build_prerequisites",
    "source_a_terminal=true",
    "source_b_status=native_corpus_static_preflight_review_passed_pilot_pending",
    "source_b_terminal=false",
    "authorized_source_count=2",
    "source_terminal_count=1",
    "global_stop_authorized=false",
    "global_stop_reason=none",
    "next_work_target=v24_native_corpus_capability_pilot_all_train_routes_seed_24001_only",
)


def test_v24_design_keeps_source_failures_local() -> None:
    text = DESIGN.read_text(encoding="utf-8")
    for phrase in (
        "Source-local terminal states never imply a global stop.",
        "Branch A failure cannot close Branch B.",
        "global_stop_authorized",
        "all authorized sources finish per-source map, route, and K=8 paired-support accounting",
        "No new runtime controller abstraction is introduced",
    ):
        assert phrase in text


def test_v24_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert text.rstrip().endswith("\n".join(POINTER))


def test_current_status_v24_pointer_matches_audit() -> None:
    text = STATUS.read_text(encoding="utf-8")
    section = text.split("## Current V24 Status", 1)[1].split(
        "## Current V23 Status", 1
    )[0]
    for line in POINTER:
        assert section.count(line) == 1


def test_v24_startup_records_frozen_history_and_independent_sources() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "V23 and earlier audits are historical and read-only",
        "dependency-capability diagnosis, not a CAMP/DP performance failure",
        "49,752,203,264",
        "zero related tasks",
        "Branch A and Branch B remain independently eligible",
        "No map loader, simulator, corpus, training, calibration, holdout, or paired evaluation ran",
    ):
        assert phrase in text


def test_v24_native_corpus_preflight_is_train_only_and_per_tick() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`375 / 5 / 1875` train routes / seeds / route-seed runs",
        "`64` native ticks and `sample_every_ticks=1`",
        "`120000` causal K=8 snapshots",
        "no outcome-based thinning",
        "all 375 train routes with seed `24001`",
        "all `54` v24 tests",
        "`64 / 0` checks",
        "Model, simulator, candidate generation, outcomes, calibration, holdout, and training execution all remained unopened",
        "17b5a8ca7c974997b1cd89905b50e86e95f5a032cab171e44898c48973867e72",
    ):
        assert phrase in text


def test_v24_native_corpus_preflight_review_rebuilds_every_config() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`3829 / 0` checks",
        "independently reloaded all 375 route assets",
        "rebuilt all 1875 run configs",
        "six live source-map paths",
        "did not call the preflight builder",
        "`59` v24 tests",
        "fe69c61e9da0a11233bb6c5862e2becc8fddb4e1e8e133c60cb21e80a5efe6db",
        "capability pilot over all 375 train routes at seed `24001` only",
    ):
        assert phrase in text


def test_v24_records_v23_source_scope_control_error() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "14 paths / 12 unique blobs",
        "reviewed source-preserving adapter impossibility",
        "no TIER IV map-family, route, or K=8 support census",
        "v23_global_stop_was_source_scope_control_error",
        "`16 / 0` checks",
        "Branch B remains independently pending raw map census",
    ):
        assert phrase in text


def test_v24_freezes_official_extension_source_before_build() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "highest official semantic-version tag",
        "dated no later than the frozen Universe commit",
        "autowarefoundation/autoware_lanelet2_extension",
        "`1.2.0`",
        "`4a3420d8cc19906e7739618f8a1686400f79b4ac`",
        "`76ba5b7b3b74bc5539b6ea55dcfb205538ad5362`",
        "Apache-2.0",
        "NOTICE is absent",
        "RegisterRegulatoryElement<DetectionArea>",
        "Lanelet2 Python package is `1.2.2`",
        "Lanelet2 headers, Lanelet2 CMake package files, ROS, ament, and Autoware build dependencies are absent",
        "Binary compatibility and process-local factory registration remain unproved",
        "`17 / 0` checks",
        "Branch B remains independently pending raw map census",
    ):
        assert phrase in text


def test_v24_branch_a_plan_fails_closed_before_unauthorized_build() -> None:
    text = " ".join(BRANCH_A_PLAN.read_text(encoding="utf-8").split())
    for phrase in (
        "Build authorization predicate",
        "the unmodified official CMake targets",
        "No system package operation",
        "No additional source checkout",
        "Compiling only `detection_area.cpp`",
        "must not start a compiler",
        "Branch A becomes source-ineligible",
        "Branch B raw census remains mandatory",
        "original OSM is read-only",
        "10 GiB",
    ):
        assert phrase in text


def test_v24_branch_a_preflight_fails_source_locally_and_continues_b() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "branch_a_fail_closed_before_build",
        "`32 / 0` checks",
        "Lanelet2 1.2.2 runtime shared library and factory symbols",
        "development headers or CMake package",
        "ROS/ament/Autoware build dependencies",
        "unfrozen `main` sources",
        "No compiler, build, install, extension load, map load, or scientific execution ran",
        "source_ineligible_missing_authorized_build_prerequisites",
        "Branch B raw-map census remains mandatory",
        "global stop remains unauthorized",
        "9df3f1958408a68841ff1dd074dd7d36774af182b43b8e51ee1f7415a7a4b2b6",
    ):
        assert phrase in text


def test_v24_branch_b_static_census_keeps_full_denominator() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`14 paths / 12 unique blobs`",
        "`14 / 14 / 13`",
        "`11 / 11`",
        "Map-family count remains unset",
        "`crosswalk: 4`",
        "`right_of_way: 10`",
        "`road_marking: 2`",
        "`traffic_light: 24`",
        "`traffic_sign: 10`",
        "one `no_lanelets` receipt",
        "Source bytes modified: `false`",
        "Builder, route census, outcomes, and holdout remained unopened",
        "`26 / 0` checks",
        "2dbe704a7f244b7ac09648de006a67cdc03fa283079ff2a3bb213c894635fb8c",
    ):
        assert phrase in text


def test_v24_branch_b_builder_smoke_keeps_failures_map_local() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`14 paths / 12 unique blobs / 12 executed blobs`",
        "`10 / 2 / 0`",
        "`12` loadable path receipts",
        "`projection_failure`",
        "simulation/traffic_simulator/test/map/empty/lanelet2_map.osm",
        "`unsupported_autoware_regulatory_element`",
        "simulation/traffic_simulator/test/map/intersection/lanelet2_map.osm",
        "`road_marking`",
        "12 distinct worker PIDs",
        "All 12 worker return codes were zero",
        "Source bytes modified: `false`",
        "Route, model, candidate generation, outcomes, and holdout remained unopened",
        "`27 / 0` checks",
        "26b4b58bf19559cafc3c2f0c3681cf3e52cd5f5f4873d1f5317e8cdc17587733",
    ):
        assert phrase in text


def test_v24_builder_review_recomputes_support_without_reexecution() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "builder_smoke_review_passed_loadable_support",
        "independently reconstructed all `12` blob groups and `14` path receipts",
        "`10 / 2 / 0`",
        "`12` loadable paths",
        "review did not reexecute the builder",
        "execution artifact root",
        "26b4b58bf19559cafc3c2f0c3681cf3e52cd5f5f4873d1f5317e8cdc17587733",
        "Map-family count remains unset",
        "`34 / 0` checks",
        "6f8ee2ec104530d143c65d40f4f11007f853b43ecd3929439db5f19b4483fd08",
    ):
        assert phrase in text


def test_v24_map_family_census_is_outcome_blind_and_keeps_failures_local() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`14 paths / 12 unique blobs`",
        "`5` map families",
        "`4` loadable families",
        "bbox containment `>=0.98`",
        "absolute segment containment `>=0.80`",
        "connected components",
        "map_family_d7f16a17d3eb",
        "intersection family remains nonloadable",
        "empty map remains an unassigned source receipt",
        "map-family-level train/calibration/holdout split regime",
        "Route census, candidate generation, outcomes, and holdout remained unopened",
        "`16 / 0` checks",
        "33626198d8945e7f102946005bfa6b9db4762d93b1146896c9ebfd99ad633717",
    ):
        assert phrase in text


def test_v24_route_census_preflight_freezes_execution_without_starting_it() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "one attempt per fixed-builder drivable start lanelet",
        "smallest numeric unvisited successor",
        "first source-arc prefix reaching `>=80m`",
        "`10 blobs / 12 paths / 4 map families`",
        "`3m / 20 samples / 15 degrees`",
        "`30 / 0` checks",
        "`49,740,017,664` free bytes",
        "zero active route-census processes",
        "Route census execution did not start",
        "model, candidate generation, outcome, and holdout remained unopened",
        "2550ecef112c79be18c1ec4a11e5425db543e7f58e7a167f1c854ee84eb9475a",
    ):
        assert phrase in text


def test_v24_route_census_execution_preserves_full_attempt_accounting() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`10 / 0 / 0` completed / failed / execution-invalid blobs",
        "`603 / 552 / 51` start attempts / qualifying / below-threshold",
        "`552 / 401 / 151 / 5` raw / exact-deduplicated / duplicate / corridor-group counts",
        "`375 / 24 / 2`",
        "slope family has zero `>=80m` support",
        "All `20 / 0` execution checks passed",
        "Source bytes modified: `false`",
        "model, candidate generation, outcomes, and holdout remained unopened",
        "did not create an execution artifact or worker",
        "e933cc37f8635867d3f34c4efeb3a54858a0f1c20c0db387dc73df20dd81bf5d",
    ):
        assert phrase in text


def test_v24_route_census_review_recomputes_without_workers() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`31 / 0` independent checks",
        "10 distinct worker PIDs",
        "all return codes zero",
        "51 nonqualifying attempts are exactly `dead_end_before_80m`",
        "five corridor groups cover all 401 retained records exactly once",
        "all 14 live source SHA values",
        "review did not execute a route worker",
        "route_census_review_passed_three_family_source_valid_support",
        "single-record fixed-DP source probe",
        "210cec6201e098169b2c606e265c6e95efc40f6593489d41802ddd1b1010795f",
    ):
        assert phrase in text


def test_v24_single_record_probe_preflight_freezes_one_source_record() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`map_family_828a913c2f9a`",
        "`1962e44a5dd0ace089aeb9011d5b70e05dfa6ae5adeec4450a6c20e3e09776b2`",
        "`24001 / 8 / 1` seed / candidates / ticks",
        "`29 / 0` preflight checks",
        "native runner reported zero arms and zero routes executed",
        "checkpoint was hashed but not loaded",
        "`63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd`",
        "`1e734165f7a614e93019df0a5c22b5e36722298cb50b21c5ce8fd0e4e2cf82bc`",
        "`58c9b506dee7ebd27095d223ce4ff52aafcdbbf8bef306b898f5d6f9f0497441`",
        "Python 3.9 evidence-sealer compatibility defect",
        "`b1886120e0b39d29ae9f7926ba59921851d248b9f769128eecd74459f47f3323`",
        "`35` remote v24 tests",
        "cedcc6fe8ca00fff7bbab4eeb92faa2f4cd5d172ec8b1d9d1cb9168ead955394",
    ):
        assert phrase in text
