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

POINTER = (
    "current_v24_status=v24_extension_source_qualification_passed",
    "current_v24_artifact_source_head=78bf6eda5ec0383d0156e395a170497691ecd714",
    "current_v24_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v24_artifact=/root/autodl-tmp/camp_dp_v24_extension_source_qualification_78bf6eda_20260715T193857CST",
    "current_v24_artifact_root_sha256=fea4418715467376102bd8127bdf366ddecbec7dd01f408657b54b84835219e3",
    "source_a_status=official_extension_source_qualified_build_feasibility_pending",
    "source_a_terminal=false",
    "source_b_status=pending_raw_map_census",
    "source_b_terminal=false",
    "authorized_source_count=2",
    "source_terminal_count=0",
    "global_stop_authorized=false",
    "global_stop_reason=none",
    "next_work_target=v24_branch_a_isolated_build_design_tdd_static_preflight_only",
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
