from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v21_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v21_status=v21_native_simulator_task1_causal_input_and_k8_contracts_passed",
    "current_v21_artifact_source_head=abda0bcf5d5874d0994bda4f8187879eaff614f3",
    "current_v21_prior_gate_final_synced_head=14b1a2394ba3e75ff5744e408f77e71be8f15d1b",
    "current_v21_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v21_artifact=/root/autodl-tmp/camp_dp_v21_native_task1_causal_k8_contracts_abda0bcf_20260714T160847CST",
    "current_v21_artifact_root_sha256=99cef3fed4ff2b570c67f5cea6de5f17ac43db0942bd449c722ba61065eb5447",
    "next_work_target=v21_native_simulator_task2_native_hook_and_immutable_selection_tdd_only",
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
