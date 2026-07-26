from __future__ import annotations

import hashlib
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "docs" / "diffusion_planner_current_status.md"
AUDIT = ROOT / "docs" / "diffusion_planner_v25_iteration_audit.md"
REPORT = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_amendment_report.md"
INDEX = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_evidence_index.md"
MIGRATION = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_migration_matrix.md"
FUTURE = ROOT / "docs" / "diffusion_planner_v25_industrial_evaluation_future_prereg_plan.md"

CURRENT_HEADING = (
    "## Current V25 Status - Industrial-Oriented Evaluation-System Amendment "
    "Independently Reviewed"
)
AUDIT_HEADING = (
    "## 2026-07-26 - Industrial-Oriented Evaluation-System Amendment "
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


def test_current_named_section_and_audit_eof_are_exact_837_field_twins() -> None:
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
    assert len(current_tuple) == 837
    assert current.count("current_v25_status=") == 1
    assert current_tuple["current_v25_status"] == (
        "industrial_oriented_evaluation_system_amendment_independently_"
        "reviewed_scientific_contract_review_required"
    )
    assert audit_text.rstrip().endswith(
        "next_work_target=high_control_review_of_industrial_evaluation_amendment_"
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
        "2e04cbfdd386ccb04a0efb0b818a1d481aea7ddfb3ad8ba580ecfbc0b91fb31e",
        "9d82089ad6ce3b41789662c0d232c33c45a86103d1cd5348da54b51d5516335a",
        "7736d35f5a33d47967b83ad3c5a236dd3d9e5d9d0d66450e8bf6dbe4109f9d31",
        "6d252bd2a52eb974e77234ab0ed85104f0dbc068f08bc5d08204bc2c1024136a",
        "0902230a0640622667c0fb79b1c9f8f069070010cf84abe894ac2e6f7afa26d2",
    )
    index = INDEX.read_text(encoding="utf-8")
    assert all(root in index and root in text for root in roots)
    assert "__" not in index


def test_report_preserves_vector_missing_and_no_claim_boundaries() -> None:
    report = " ".join(REPORT.read_text(encoding="utf-8").split())
    for phrase in (
        "56-endpoint vector",
        "No weighted total is allowed",
        "immutable_legacy_exploratory_diagnostic_only",
        "numeric_margin_not_authorized_until_future_preregistration",
        "Missing is never converted to zero",
        "0.4 m/s crossing remains a crossing",
        "not ISO VDV",
        "not occupant comfort",
        "not_assessed",
        "honest_no_claim_under_frozen_preregistered_all_gate",
    ):
        assert phrase in report
    assert "Fresh benefit" in report
    assert "promotion, deployment" in report


def test_migration_and_future_plan_do_not_reauthorize_legacy_or_runs() -> None:
    migration = " ".join(MIGRATION.read_text(encoding="utf-8").split())
    future = " ".join(FUTURE.read_text(encoding="utf-8").split())
    assert "SafetyCost weighted sum" in migration
    assert "Never primary, PASS, claim, training support, or adaptation evidence" in migration
    assert "Five-point is never a polygon substitute" in migration
    assert "Stateless segment jumps forbidden" in migration
    assert "No SafetyCost" in future
    assert "authorizes no model, pool, selector, calibration, validation" in future
    assert "Never create a weighted total" in future


def test_current_machine_zero_run_and_capability_counts() -> None:
    status = _tuple(
        STATUS.read_text(encoding="utf-8")
        .split(CURRENT_HEADING, 1)[1]
        .split("## Historical V25 Status Through A1.6.11", 1)[0]
    )
    assert status["current_v25_industrial_evaluation_endpoint_count"] == "56"
    assert (
        status[
            "current_v25_industrial_evaluation_reconstructable_with_frozen_transform_count"
        ]
        == "42"
    )
    assert status["current_v25_industrial_evaluation_evidence_missing_count"] == "13"
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
