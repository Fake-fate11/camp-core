from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v21_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v21_status=v21_native_simulator_task4_paired_runner_and_frozen_smoke_config_passed",
    "current_v21_artifact_source_head=ac9cf98cafa0f27bc30acc7ca51d90f3d96766b8",
    "current_v21_prior_gate_final_synced_head=12e98803f3f0fa2b0b3eccc1279d8b41756c2496",
    "current_v21_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v21_artifact=/root/autodl-tmp/camp_dp_v21_native_task4_paired_runner_ac9cf98c_20260714T165318CST",
    "current_v21_artifact_root_sha256=443a2a663347e4b5a825336da96653bc3803dd8fed787f8e721275f402e705a6",
    "next_work_target=v21_native_simulator_gate_d_one_tick_capability_smoke",
)


def test_v21_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert text.rstrip().endswith("\n".join(POINTER))


def test_current_status_v21_pointer_matches_audit() -> None:
    text = STATUS.read_text(encoding="utf-8")
    section = text.split("## Current V21 Status", 1)[1].split(
        "## Current V20 Status", 1
    )[0]
    for line in POINTER:
        assert section.count(line) == 1


def test_v21_capability_audit_preserves_scientific_guards() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    required = (
        "sg_smooth_enabled=false",
        "max_steps < 400",
        "candidate 0 identity is not claimed in Gate A",
        "future-derived",
        "dp_camp_v10_14d",
        "ADE/FDE/miss",
        "No inference, simulation, training, holdout access",
    )
    for phrase in required:
        assert phrase in text


def test_v21_task4_records_runner_without_simulator_claim() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "DP then CAMP",
        "native_zero_left_pad_to_31_v1",
        "43 passed",
        "No simulator execution occurred",
        "claim_authorized=false",
        "44a861b85f4335dfbd0dc02e92d7da3ea889c4093539ea4ac616b3b1290a9fc0",
    ):
        assert phrase in text
