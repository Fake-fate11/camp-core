from __future__ import annotations

import hashlib
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"
AUDIT = ROOT / "docs" / "diffusion_planner_v25_iteration_audit.md"
REPORT = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_amendment_v3_report.md"
INDEX = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_evidence_index_v3.md"
MIGRATION = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_migration_matrix_v3.md"
FUTURE = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_future_prereg_plan_v3.md"

CURRENT_HEADING = (
    "## Current V25 Status - Industrial-Oriented Evaluation-System Amendment v3 "
    "Independently Reviewed"
)
AUDIT_HEADING = (
    "## 2026-07-26 - Industrial-Oriented Evaluation-System Amendment v3 "
    "Independently Reviewed"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tuple(text: str) -> dict[str, str]:
    rows = [
        line for line in text.splitlines() if re.fullmatch(r"[a-z][a-z0-9_]*=.*", line)
    ]
    result = dict(row.split("=", 1) for row in rows)
    assert len(result) == len(rows)
    return result


def test_current_named_section_and_audit_eof_are_exact_904_field_twins() -> None:
    status_text = STATUS.read_text(encoding="utf-8")
    audit_text = AUDIT.read_text(encoding="utf-8")
    assert status_text.count(CURRENT_HEADING) == 1
    assert audit_text.count(AUDIT_HEADING) == 1
    current = status_text.split(CURRENT_HEADING, 1)[1].split(
        "## Historical V25 Status Through A1.6.11", 1
    )[0]
    audit_eof = audit_text.split(AUDIT_HEADING, 1)[1]
    current_tuple = _tuple(current)
    audit_tuple = _tuple(audit_eof)
    assert current_tuple == audit_tuple
    assert len(current_tuple) == 904
    assert current.count("current_v25_status=") == 1
    assert current_tuple["current_v25_status"] == (
        "industrial_oriented_evaluation_system_amendment_v3_independently_"
        "reviewed_scientific_contract_review_required"
    )
    assert audit_text.rstrip().endswith(
        "next_work_target=high_control_review_of_industrial_evaluation_amendment_v3_"
        "before_any_training_support_or_batch8_calibration_decision"
    )


def test_document_hashes_and_sealed_roots_are_bound() -> None:
    text = STATUS.read_text(encoding="utf-8")
    current = _tuple(
        text.split(CURRENT_HEADING, 1)[1].split(
            "## Historical V25 Status Through A1.6.11", 1
        )[0]
    )
    assert current["current_v25_industrial_evaluation_report_sha256"] == _sha(REPORT)
    assert current["current_v25_industrial_evaluation_evidence_index_sha256"] == _sha(
        INDEX
    )
    assert current["current_v25_industrial_evaluation_migration_matrix_sha256"] == _sha(
        MIGRATION
    )
    assert current[
        "current_v25_industrial_evaluation_future_prereg_plan_sha256"
    ] == _sha(FUTURE)
    roots = (
        "908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb",
        "23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556",
        "fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d",
        "f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3",
        "06f221f4cf8fc86ae19f632fcc2fa74080575966224090fc552db89a190abb5b",
    )
    index = INDEX.read_text(encoding="utf-8")
    assert all(root in index and root in text for root in roots)
    assert "__" not in index


def test_report_preserves_vector_missing_and_no_claim_boundaries() -> None:
    report = " ".join(REPORT.read_text(encoding="utf-8").split())
    for phrase in (
        "161-scalar-leaf",
        "No weighted total",
        "immutable_legacy_exploratory_diagnostic_only",
        "numeric_margin_not_authorized_until_future_preregistration",
        "holm_bonferroni_step_down_within_exact_family",
        "collision_onset_relative_closing_speed_kinematic_proxy_mps",
        "max(0,-dot(r_tau,v_rel_tau)/max(norm(r_tau),1e-9))",
        "(p_value,leaf_id)",
        "ordinary 95% CI is descriptive only",
        "distinct from occupant/seat comfort",
        "honest_no_claim_under_frozen_preregistered_all_gate",
    ):
        assert phrase in report
    assert "Fresh benefit" in report
    assert "promotion, deployment" in report


def test_migration_and_future_plan_do_not_reauthorize_legacy_or_runs() -> None:
    migration = " ".join(MIGRATION.read_text(encoding="utf-8").split())
    future = " ".join(FUTURE.read_text(encoding="utf-8").split())
    assert "SafetyCost weighted sum" in migration
    assert "Never primary, PASS, claim, training-support or adaptation evidence" in migration
    assert "exact sealed root/review root" in migration
    assert "Nonnegative closing-speed formula" in migration
    assert "Keep SafetyCost" in future
    assert "No model, pool, selector, training" in future
    assert "Never create a weighted total" in future


def test_current_machine_zero_run_and_capability_counts() -> None:
    status = _tuple(
        STATUS.read_text(encoding="utf-8")
        .split(CURRENT_HEADING, 1)[1]
        .split("## Historical V25 Status Through A1.6.11", 1)[0]
    )
    assert status["current_v25_industrial_evaluation_parent_endpoint_count"] == "56"
    assert status["current_v25_industrial_evaluation_scalar_leaf_count"] == "161"
    assert (
        status[
            "current_v25_industrial_evaluation_reconstructable_with_frozen_transform_count"
        ]
        == "119"
    )
    assert status["current_v25_industrial_evaluation_evidence_missing_count"] == "41"
    assert (
        status["current_v25_industrial_evaluation_scientifically_inapplicable_count"]
        == "1"
    )
    assert status["current_v25_industrial_evaluation_new_weighted_total"] == "false"
    assert (
        status["current_v25_industrial_evaluation_model_pool_selector_call_count"]
        == "0"
    )
    assert status["current_v25_industrial_evaluation_outcome_values_read"] == "false"
    assert (
        status["current_v25_industrial_evaluation_old_artifact_or_cas_write_count"]
        == "0"
    )
    assert status["current_v25_industrial_evaluation_claim_authorized"] == "false"
    assert status["current_v25_industrial_evaluation_local_tracked_clean"] == (
        "false_due_to_preserved_superseded_training_support_draft"
    )
    assert (
        status[
            "current_v25_industrial_evaluation_superseded_diagnostic_in_accepted_"
            "amendment_roots"
        ]
        == "false"
    )
    assert (
        status[
            "current_v25_industrial_evaluation_superseded_diagnostic_"
            "model_pool_selector_call_count"
        ]
        == "0"
    )


def test_superseded_v1_and_pre_capability_fixture_are_preserved() -> None:
    report = REPORT.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    expected = (
        "2e04cbfd",
        "9d82089a",
        "7736d35f",
        "6d252bd2",
        "0902230a",
        "2981e632",
        "c9b79252",
        "663977da",
        "8ed937f5",
        "86ab14e2",
        "0c6f25de",
        "0bccb132",
    )
    assert all(value in index for value in expected)
    assert "superseded v1 roots" in report
    assert "superseded v2 roots" in report
    assert "pre-capability inventory-SHA fixture diagnostic" in index
