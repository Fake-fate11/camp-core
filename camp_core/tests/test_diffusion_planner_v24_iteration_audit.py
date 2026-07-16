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
    "current_v24_status=v24_paired_calibration_capability_pilot_execution_passed",
    "current_v24_artifact_source_head=3ac4b0096c0ed25181c5f90dcc3957e852fd13fb",
    "current_v24_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v24_artifact=/root/autodl-tmp/camp_dp_v24_paired_calibration_pilot_execution_3ac4b009_20260717T013123CST",
    "current_v24_artifact_root_sha256=dad15b52154ab3b10d1a407e7aeae61626dc3f8deddac98a2c17b55ac2a0e73d",
    "source_a_status=source_ineligible_missing_authorized_build_prerequisites",
    "source_a_terminal=true",
    "source_b_status=paired_calibration_capability_pilot_execution_passed_independent_review_pending",
    "source_b_terminal=false",
    "authorized_source_count=2",
    "source_terminal_count=1",
    "global_stop_authorized=false",
    "global_stop_reason=none",
    "next_work_target=v24_paired_calibration_capability_pilot_independent_review_only",
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


def test_v24_convex_training_execution_is_sealed_before_result_review() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Gate 46: Convex Selector Training Execution and Result-Review Preparation",
        "`1,875 / 1,054 / 821` retained / complete / failed route-seeds",
        "`67,796 / 542,368 / 470,138 / 7,783` snapshots / candidates / physical-feasible candidates / all-K-high-risk snapshots",
        "`4,241.870738078374` seconds",
        "`4 / 101,391 / 0` iterations / final cuts / final new cuts",
        "`1.1185675308222898e-07`",
        "`91ddd978d383d66488215e2fc8135dee37f4e3d40efb7f801389b40d6fb2c175`",
        "does not call CLARABEL, CVXPY, a solver, or a training entry point",
        "Calibration, holdout, outcomes, paired evaluation, tuning, and claims remain closed",
    ):
        assert phrase in text


def test_v24_convex_training_result_review_is_independently_sealed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Gate 47: Convex Selector Training Independent Result Review",
        "passed `25 / 0` independent checks",
        "verified all `20` execution files",
        "`0b2539ef6c8fa195dfefac6f330775cdc8cb6c0ec7a7ca3aec96d19d0e0b5e6c`",
        "`e9ba9db86f1c63e12112467d65364af2bc74623e87dfa1b5bb4aae871e40911f`",
        "`1.1185675338754031e-07`",
        "training was not reexecuted and no solver was called",
        "Only paired-evaluation plan TDD/static preflight is authorized next",
    ):
        assert phrase in text


def test_v24_paired_plan_freezes_order_and_keeps_holdout_closed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Gate 48: Paired Evaluation Plan TDD, Static Preflight, and Independent Review",
        "`31 / 0` static checks",
        "`23 / 0` independent checks",
        "`1 / 2 / 120` capability / pilot / main pairs",
        "`1/1` and `60/60`",
        "camp-v24-paired-arm-order-v1",
        "independent simulator reset",
        "latency remains descriptive instrumented output only",
        "post-divergence cross-arm K=8 tensors are expected to be non-comparable",
        "`1,875 / 1,054 / 821` retained / complete / failed",
        "`[7, 8, 13]`",
        "one map family and three indivisible corridor groups",
        "`06bd51a06814a11ae395edfecfc3febddc1ba646dfcd391e33962e15fe46a56c`",
        "`8ce3a270f367c3b8ac590e1469002982a8cf34e9b70ea9cfc448a3eb3637ce88`",
        "Calibration capability/pilot is the only authorized next execution",
    ):
        assert phrase in text


def test_v24_paired_calibration_pilot_is_complete_but_noninferential() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "## Gate 49: Paired Calibration Capability and Pilot Execution",
        "`1 / 1 / 1` planned / retained / complete",
        "`2 / 2 / 2`",
        "pilot AB/BA order is exactly `1/1`",
        "`128` ticks per arm",
        "`61 / 67` candidate-0 / non-0 selections",
        "one better and one worse pair with mean delta zero",
        "No effect or safety conclusion is permitted",
        "`0bc821da6976a6e320d2d0dc8975e7e2b46f33ea21a3295e9223bb90a2a94930`",
        "`dad15b52154ab3b10d1a407e7aeae61626dc3f8deddac98a2c17b55ac2a0e73d`",
        "Holdout remained unopened at count zero",
        "Only independent result review is authorized next",
    ):
        assert phrase in text


def test_v24_remaining_execution_and_independent_review_are_sealed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`1500 / 1500` route-seed runs are retained",
        "`842` complete, `658` failed, `0` pending",
        "`54,191` causal per-tick K=8 snapshots",
        "`6,182` all-K-high-risk snapshots",
        "`29,678.080113993958` seconds",
        "Candidate-tensor before/after hashes",
        "6b0d2fd186457ccc94028e9606f7680dd871539a44ff62babd42f15734d381c7",
        "`892,535 / 0` checks",
        "all `112` v24 tests",
        "c0ccbce09d6ff0f9c9bdf085773ca6962d91e5019a044b0e0cc2c894b3779501",
        "authorizes only deterministic assembly",
    ):
        assert phrase in text


def test_current_status_distinguishes_execution_from_review_boundaries() -> None:
    section = " ".join(
        STATUS.read_text(encoding="utf-8")
        .split("## Current V24 Status", 1)[1]
        .split("## Current V23 Status", 1)[0]
        .split()
    )
    assert "fixed K=8 candidate generation necessarily ran" in section
    assert "the independent review did not rerun them" in section
    assert "Candidate modification, training, outcomes" in section


def test_v24_merged_corpus_assembly_and_review_are_sealed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`375 / 5 / 1875` routes / seeds / retained route-seed rows",
        "`1054` complete, `821` retained failures, `0` pending",
        "`67,796` unique causal per-tick K=8 snapshots",
        "exact pilot/remaining snapshot overlap is `0`",
        "`7,783` all-K-high-risk snapshots",
        "`37,251.28229829995` seconds",
        "creates no `snapshots/` directory",
        "d8278d030cabd71af88f60d13c410a37c515f22e0ea4c606a592abecc598bdcc",
        "verified `77,822` files",
        "passed `27 / 0` checks",
        "all `129` v24 tests",
        "925db2aa58f136c20b3e9054d87dbd8d73d4162d18d079b10abbcacc63f09490",
        "train-only active atom mask",
    ):
        assert phrase in text


def test_v24_atom_availability_freeze_and_review_are_sealed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "target suite (`24 passed`)",
        "all v24 tests (`155 passed`)",
        "tests were not repeated",
        "dc959a09e554311ca57362e8431f6345bbdb31ac141c0150fd2afe3d95e70d33",
        "all `67,796` causal snapshots and `542,368` K=8 candidate rows",
        "All 14 approved atoms are source-available and train-nonconstant",
        "the excluded set is empty",
        "b82b3ffe2579c567ab4460a78d630a9191bd18bea7874e9d85e32d1219bc50de",
        "ced620a4a5852e9e4196a2d272ef9b0ac1963512ecd62c2bf3612a3ed252438b",
        "passed `21 / 0` checks",
        "a88e6d43041e4f8005a7df5cccd9dd64510758a9c2a4af1de15e339e250e80b8",
        "training execution remains unauthorized",
    ):
        assert phrase in text


def test_v24_train_only_labels_and_independent_review_are_sealed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "untracked runner could have claimed the current HEAD",
        "Final independent code review returned Go with no remaining P1/P2",
        "combined label, atom-freeze, merged, training-preflight, and v24 audit suite passed `107` tests",
        "f78ce33ea7c38b8ef44d4e11fd4c0ace3d0bec928ab83d03b2f719596ebc416f",
        "failed closed before producer invocation",
        "2ac7714cff733e36c2cec4f5d6caf1e70eb9396129faf556f2837c376d9d418b",
        "`67,796 / 542,368`",
        "`375 / 5 / 1,875`",
        "`1,054 / 821`",
        "`[4067, 9062, 9010, 9159, 9135, 9028, 9251, 9084]`",
        "`4,067 / 63,729`",
        "9a14fb003fe9145e62b24c20fcecc013baedd72e312add82a8c6a6e6dcde966c",
        "verified `155,678` sealed-file receipts",
        "All `17 / 0` checks passed",
        "d23d09564ea675b0ef7ce35d968c6dd03ead1df5e1282c498704827986eab468",
        "does not authorize a corpus solve",
    ):
        assert phrase in text


def test_v24_training_executor_static_preflight_and_review_are_sealed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "exact CLARABEL `optimal` only",
        "post-cap final resolve is forbidden",
        "full-K saved-weight gap at most `1e-6`",
        "`pilot` exactly to seed `24001`",
        "`remaining` exactly to seeds `24002` through `24005`",
        "`118` tests",
        "5a08c0d9bab995b1c8ce8d21c91dfcec76116289919b4decedf3eaa81e7459df",
        "fe265ed7be9beaf1ad9faba91316ccf7f944b1cb213ff6cf266651b27ba9af80",
        "passed `22 / 0` checks",
        "ee73c6611fbf369e09f29f2fc9d852815ba15bb8e2077299aef524667de3cce7",
        "Only train-only convex execution is authorized next",
    ):
        assert phrase in text


def test_v24_first_training_failure_is_independently_reviewed_before_repair() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "PID `89986`",
        "projected saved-weight full-K gap exceeds tolerance",
        "zero completed learning-curve levels",
        "275f5a652173f95e6ee3ef34b4b7954703799e5e4c5d8c575648aa6e9227d866",
        "raw CLARABEL weights",
        "projected strict-simplex weights",
        "passed `14 / 0` checks",
        "deb19426cb8bbe508f08068c2f95bc861fbb3f513a8a5338462a3a8accedd538",
        "1838014fbfb4b40a92449df32c360ed1922a00c44f54650b407fec5d36da340d",
        "Training retry remains unauthorized",
    ):
        assert phrase in text


def test_v24_projection_boundary_repair_is_reviewed_before_retry() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "both raw and projected worst candidates",
        "unchanged acceptance limit `1e-6`",
        "`122` tests",
        "f9fd55bb00759ed0fa2c42fc609b47bf7d5769f4100fe45b1b225ee3d4ec0155",
        "dd37d8992af680bd034e1bd9d38cfef41cc693bec25141abed1f2d24e040e77b",
        "passed `24 / 0` checks",
        "6cd16510b7cf2c82277d086271a56ebc36a803a5db2ce1a2289e86616bbe2e13",
        "Only the exact train-only retry is authorized next",
    ):
        assert phrase in text


def test_v24_training_retry_failure_is_reviewed_before_cut_relative_repair() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "PID `91691`",
        "No learning-curve level completed",
        "4f7b28cfbb24c49dd9682d899acf32dd87016d6050e6acab059703d236d3c1c3",
        "full-K minus master_losses",
        "full-K minus the serialized cut set",
        "requiring all four gaps at most `1e-6`",
        "passed `57` tests",
        "02f94b4c1095d4723f7713b6381ef2b7c197599f6b0b69cb35f0aac0d95e3b37",
        "passed `14 / 0` checks",
        "4cd55a260ceff5e06c337d53329c8b07219f685797f092c6555a8979b4a4b61b",
        "a third training execution remains unauthorized",
    ):
        assert phrase in text


def test_v24_cut_relative_gap_repair_is_reviewed_before_training_retry() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "per-snapshot full-K and current-cut-set losses",
        "all four maximum gaps at most `1e-6`",
        "old source converged after one mocked master call",
        "repaired source requires a second call",
        "passed `128` tests",
        "a5cd24e2b37c41c53b44d074d6d86691fb7f26de42e739c7cbb3d39f0afed65a",
        "60018ce01740096f157755757d0508def9f887f2f24691c167de8b2fe6741862",
        "passed `26 / 0` checks",
        "1a863b7b9710f53d6374c4b203223611e131aaca0d57d39e629bf95588723418",
        "Only the exact repaired train-only retry",
    ):
        assert phrase in text


def test_v24_repaired_training_authorization_contract_is_reviewed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "executor's own authorization reader still named the Gate 40",
        "No training process or artifact was started",
        "rejecting the historical Gate 40 tuple",
        "incorrect full HEAD constant",
        "passed `130` tests",
        "de34373318a0c4f93ecd34eabd233ec326d04757e19cfe8280ec1846445ec3bd",
        "95721dd54fd9947aad4c19f3bd8366e939ad1c8817ff531dded1cde1b13e0952",
        "passed `27 / 0` checks",
        "f5b23d9d8c4a1c4e51f7028678408a6a9a199d2d066088242709ff86497dd357",
        "Only the exact repaired train-only retry",
    ):
        assert phrase in text


def test_v24_stable_training_authorization_is_source_bound() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "no longer depends on advancing gate names",
        "current_v24_artifact_source_head",
        "authorization review's `executor_source_sha256`",
        "mismatched executor SHA fail closed",
        "passed `131` tests",
        "e4381c57dcfd646b80926c557b53a12799852c02bc28f80cbdd9e6f5f0600187",
        "ee28903152c0fc15dc90a523bfcbc79de15a39e703e45722f16d2b21c0d80e5f",
        "passed `27 / 0` checks",
        "a68ade86682ab98cf554d4175d0123902fef43a6c31e6535187a4bdcd6ecc90e",
        "Only one exact repaired train-only retry",
    ):
        assert phrase in text


def test_v24_source_blob_authorization_final_review_is_sealed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "docs-only HEAD distinction is now closed",
        "review CAMP HEAD must equal the live artifact source HEAD",
        "executor Git blob must equal the current live executor bytes",
        "passed `132` tests",
        "7a1bf1fa184f57451fd0454c820a6f0c87132e44070dfe63bd1a39fa94915f12",
        "74df36f9825c66aa6130a724add4a2134387dbce5c116605a498306c108f112a",
        "passed `27 / 0` checks",
        "25bc6fe4c6e5a8512b524d62402f8de1fcc65db018337ce6d09cc202f27c86d7",
        "The one exact repaired train-only retry",
    ):
        assert phrase in text


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


def test_v24_native_corpus_pilot_execution_preflight_is_fail_closed() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "`403 / 0` checks",
        "all 375 seed-24001 run configs",
        "six live source maps",
        "`24000` theoretical pilot snapshot ceiling",
        "`63` v24 tests",
        "verified-asset receipt count assumption",
        "created no scientific output artifact",
        "49dfd7e0ac0d5385101452a9f9b852d79da854e8e7e20ccc1ece9803112ba866",
        "unique background pilot execution",
    ):
        assert phrase in text


def test_v24_records_unique_corpus_pilot_launch() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "PID `41080`",
        "exactly one background pilot",
        "seed `24001` over all 375 train routes",
        "pending_unique_long_task_running_unsealed",
        "must not launch or resume another pilot",
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
