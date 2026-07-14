from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v21_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v21_status=v21_native_simulator_minimal_tdd_plan_review_passed",
    "current_v21_artifact_source_head=90937b0eda431e1365d41f1f5ef55864568d0a2d",
    "current_v21_prior_gate_final_synced_head=90937b0eda431e1365d41f1f5ef55864568d0a2d",
    "current_v21_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v21_artifact=/root/autodl-tmp/camp_dp_v21_native_simulator_minimal_tdd_plan_90937b0e_20260714T155950CST",
    "current_v21_artifact_root_sha256=2625188c0d9346e5d1f53ec4d8cb8bc1390a9c0bec428cfb0dddff47b186f40e",
    "next_work_target=v21_native_simulator_task1_causal_input_and_k8_contracts_tdd_only",
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
