from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_implementation_plan import (
    AUTHORIZED_NEXT_WORK,
    PLANNED_DIAGNOSTIC_SCRIPT,
    PLANNED_DIAGNOSTIC_TEST,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_TESTS,
    STATIC_REVIEW_JSON,
    STATIC_REVIEW_MD,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_static_contract import (
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
    REQUIRED_AXES,
    REQUIRED_TABLES,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={STATIC_REVIEW_READY_STATUS}
authorized_next_work={STATIC_REVIEW_AUTHORIZED_NEXT_WORK}
candidate_generation_execution_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _static_review_payload(
    *,
    status: str = STATIC_REVIEW_READY_STATUS,
    authorized_next_work: str = STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    diagnostic_plan_authorized: bool = True,
    missing_table: str | None = None,
    missing_axis: str | None = None,
    blocked_action: bool = False,
) -> dict[str, object]:
    tables = [item for item in REQUIRED_TABLES if item != missing_table]
    axes = [item for item in REQUIRED_AXES if item != missing_axis]
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "diagnostic_implementation_plan_authorized": diagnostic_plan_authorized,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["candidate_generation_execution_authorized"] = True
    return {
        "final_decision": decision,
        "plan_summary": {
            "primary_blocker_family": "comfort_support_zero_after_hard_support_pass",
            "hard_support_positive": True,
            "comfort_support_positive": False,
            "positive_support_evidence": False,
            "replay_evidence_ready": False,
            "training_ready": False,
            "read_only_existing_artifacts": True,
            "no_candidate_reconstruction": True,
            "json_serializable_scalars_only": True,
            "diagnostic_tables": tables,
            "correlation_axes": axes,
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str = "# Residual Comfort Diagnostic Static Contract Review\n",
) -> tuple[Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "static_review"
    root.mkdir()
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    (root / STATIC_REVIEW_JSON).write_text(
        json.dumps(payload or _static_review_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / STATIC_REVIEW_MD).write_text(markdown_text, encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(tmp_path, audit_text=audit_text, payload=payload)
    return build_report(
        static_review_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_diagnostic_implementation_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["diagnostic_implementation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["diagnostic_implementation_plan_ready"] is True
    assert decision["diagnostic_implementation_static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["implementation_scope"]["planned_script"] == PLANNED_DIAGNOSTIC_SCRIPT
    assert plan["implementation_scope"]["planned_test"] == PLANNED_DIAGNOSTIC_TEST
    assert set(REQUIRED_TABLES).issubset(set(plan["required_tables"]))
    assert set(REQUIRED_AXES).issubset(set(plan["required_axes"]))
    assert set(REQUIRED_TESTS).issubset(set(plan["required_tests"]))


def test_residual_comfort_diagnostic_implementation_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_residual_comfort_diagnostic_implementation_plan_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_implementation_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_implementation_plan_rejects_missing_table(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(missing_table="diagnostic_decision_boundary"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_table_diagnostic_decision_boundary" in report[
        "final_decision"
    ]["failed_checks"]


def test_residual_comfort_diagnostic_implementation_plan_rejects_missing_axis(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(missing_axis="comfort_admissible"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_axis_comfort_admissible" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_implementation_plan_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_static_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_implementation_plan_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Residual Comfort Diagnostic Implementation Plan" in markdown
    assert PLANNED_DIAGNOSTIC_SCRIPT in markdown
    assert PLANNED_DIAGNOSTIC_TEST in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_diagnostic_implementation_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "implementation_plan.json"
    output_md = tmp_path / "out" / "implementation_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--static_review_root",
            str(root),
            "--audit_path",
            str(audit),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "unit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Residual Comfort Diagnostic Implementation Plan" in markdown
