from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs" / "diffusion_planner_v25_iteration_audit.md"
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"
V24_AUDIT = ROOT / "docs" / "diffusion_planner_v24_iteration_audit.md"
V24_PAIRED_CONFIG = (
    ROOT / "configs" / "integrations" / "diffusion_planner_v24_paired_evaluation.json"
)

POINTER = (
    "current_v25_status=v25_startup_v24_reconciliation_complete",
    "current_v25_startup_base_head=3f25b697eb99b55e79388c90147b1fc3d18423ef",
    "fixed_dp_head=7a1d33da277a1992ec474b5383a0c963c72e04e4",
    "v24_legacy_benchmark_status=frozen_read_only_honest_no_claim",
    "v24_holdout_open_count=1",
    "v24_holdout_rerun_authorized=false",
    "local_origin_github_aligned=true",
    "autodl_camp_aligned=true",
    "autodl_dp_clean=true",
    "minimum_free_disk_gib=10",
    "observed_autodl_free_bytes=48674500608",
    "current_v25_phase=1_startup_v24_reconciliation",
    "next_work_target=v25_atom_context_audit_and_freeze",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v25_audit_ends_with_authoritative_pointer() -> None:
    text = AUDIT.read_text(encoding="utf-8")
    assert text.rstrip().endswith("\n".join(POINTER))


def test_current_status_has_one_v25_pointer_matching_audit() -> None:
    text = STATUS.read_text(encoding="utf-8")
    assert text.count("## Current V25 Status") == 1
    section = text.split("## Current V25 Status", 1)[1].split(
        "## Current V24 Status", 1
    )[0]
    for line in POINTER:
        assert section.count(line) == 1


def test_v24_authority_files_remain_byte_frozen() -> None:
    assert _sha256(V24_AUDIT) == (
        "cd9a33655e1919182f33256dd07d3bd7a6bdbe7fd8aab1107199859ccf39f228"
    )
    assert _sha256(V24_PAIRED_CONFIG) == (
        "9dc0ab9415239211f16e65495362d83c2a11ffe04a96f4ddd2881b12fc193c0f"
    )


def test_v25_startup_record_bounds_legacy_evidence_and_baseline_language() -> None:
    text = " ".join(AUDIT.read_text(encoding="utf-8").split())
    for phrase in (
        "Legacy Benchmark A",
        "67,796 causal K=8 snapshots",
        "1,054 complete and 821 retained failures",
        "lane_deviation, clearance, and dp_prior_jerk_excess_cost",
        "only near_miss_noncollision_rate had a nonzero primary-component delta",
        "candidate 0 is the DP operational default",
        "not native-ranked Top-1",
        "must not tune V25 atoms, weights, thresholds, margins, or sample composition",
    ):
        assert phrase in text
