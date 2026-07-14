from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v21_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"

POINTER = (
    "current_v21_status=v21_native_simulator_gate_d_capability_and_independent_review_passed",
    "current_v21_artifact_source_head=11f1421646780b1ffe2a4c0fe7957b17158456d0",
    "current_v21_prior_gate_final_synced_head=4e79dc3999045fb8cd293c0794f2226b64084000",
    "current_v21_final_synced_head=pending_current_docs_commit_not_source_drift",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "current_v21_artifact=/root/autodl-tmp/camp_dp_v21_native_gate_d_independent_review_11f14216_20260714T171411CST",
    "current_v21_artifact_root_sha256=852c5c2190d828cc6f8825ab0f0edbb211859e941743d8e16600eccdd59a3a1c",
    "next_work_target=v21_native_simulator_gate_e_two_route_paired_smoke",
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


def test_v21_gate_d_records_one_tick_capability_without_claim() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    for phrase in (
        "31 / 0",
        "selected index 7",
        "86f91da26f61f00a2e73cddab9a900b2526b7781a940dd983cf4649c6290fd1b",
        "823b2e604297bf2229e8079999e5d57c0a74949bfdeb0ec91fd41a841de72913",
        "125d14dc3de12bd4bf515f0f00ed5bc31b457e88248f604450142caadb3a83fa",
        "26 / 0",
        "Gate D cannot support a safety or CAMP-over-DP claim",
    ):
        assert phrase in text
