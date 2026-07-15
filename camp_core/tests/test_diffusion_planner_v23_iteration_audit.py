from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v23_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v23_status=v23_startup_reconciliation_passed",
    "current_v23_artifact_source_head=f895b71f65c5971412a8d0be0c3ce492b25bbbe0",
    "current_v23_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v23_artifact=/root/autodl-tmp/camp_dp_v23_startup_reconciliation_retry_f895b71f_20260715T170517CST",
    "current_v23_artifact_root_sha256=637eb928b5210bfc8096c4a6b533d5600dc795c76407e1105dd3829fd80f2cc9",
    "next_work_target=v23_license_source_freeze_only",
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
