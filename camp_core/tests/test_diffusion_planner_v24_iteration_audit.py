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
    "current_v24_status=v24_v23_boundary_review_passed",
    "current_v24_artifact_source_head=aad8b1a588e9569a28674a67df5456aa21d7de4d",
    "current_v24_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v24_artifact=/root/autodl-tmp/camp_dp_v24_v23_boundary_review_aad8b1a5_20260715T191632CST",
    "current_v24_artifact_root_sha256=3f127806be14984c7ca08b595bb8947565fa12f74c6a922e0b9fedd9d646c64d",
    "source_a_status=pending_extension_source_qualification",
    "source_a_terminal=false",
    "source_b_status=pending_raw_map_census",
    "source_b_terminal=false",
    "authorized_source_count=2",
    "source_terminal_count=0",
    "global_stop_authorized=false",
    "global_stop_reason=none",
    "next_work_target=v24_extension_source_qualification_only",
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
