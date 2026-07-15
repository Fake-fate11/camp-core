from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v23_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v23_status=v23_license_source_freeze_passed",
    "current_v23_artifact_source_head=51c97eb24a2076247e892d2e4dfab82852e30914",
    "current_v23_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v23_artifact=/root/autodl-tmp/camp_dp_v23_source_license_freeze_retry2_51c97eb2_20260715T172832CST",
    "current_v23_artifact_root_sha256=c49f129f092497f6eb30cf887cf3bfbf36fc924244055ada0d0ff221d5ab3265",
    "next_work_target=v23_adapter_design_tdd_static_review_only",
)


def test_v23_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert text.rstrip().endswith("\n".join(POINTER))


def test_current_status_v23_pointer_matches_audit() -> None:
    text = STATUS.read_text(encoding="utf-8")
    section = text.split("## Current V23 Status", 1)[1].split(
        "## Current V22 Status", 1
    )[0]
    for line in POINTER:
        assert section.count(line) == 1


def test_v23_startup_records_frozen_history_and_failed_receipt() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "V22 and earlier audits are historical and read-only",
        "436afe23998b18b578b06bf901f9b0b45f6119612342a230d9777a5e72da786d",
        "transient GitHub HTTP 503",
        "49,761,910,784",
        "No simulator, model, training, calibration, or holdout execution occurred",
    ):
        assert phrase in text


def test_v23_records_license_source_freeze_receipts() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "15 OSM paths / 13 unique file SHA256 values",
        "14 paths / 12 unique files",
        "cda848e3d440aaf48e532f8ab33afdff0bf8b8f1a45abd3d7724637a287ed660",
        "028ef16a80b515cfdc65d13d7ada190dd578cf2d",
        "5ea83543ae9a4447c385c26b918f24e0af8ab18967943eeaeffd9a784b1a5662",
        "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
        "9082255fb4bbb2bdf6e83e0d40ac749f49942953c123d7453e6ea67ce12e7119",
        "8a44cb16207e1c8bb4cfa9c7b250a40d4d9f7d16c71949da79357b817eb77d72",
        "361cec4cb2dba84d0560a3476104696a8973d8b2d3331ac0410dc156c047adc4",
        "7ad99da785c33c0d2f15448d27064737de08fa97b412e9877601ed2f137066e9",
        "source bytes modified: false",
        "No map loader, simulator, model, training, calibration, or holdout ran",
    ):
        assert phrase in text
