from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_implementation_plan import (
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    PLANNED_DIAGNOSTIC_SCRIPT,
    PLANNED_DIAGNOSTIC_TEST,
    READY_STATUS as PLAN_READY_STATUS,
    REQUIRED_TESTS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_implementation_static_contract import (
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK,
    PLAN_JSON,
    PLAN_MD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_static_contract import (
    REQUIRED_AXES,
    REQUIRED_TABLES,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={PLAN_READY_STATUS}
authorized_next_work={PLAN_AUTHORIZED_NEXT_WORK}
candidate_generation_execution_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _plan_payload(
    *,
    status: str = PLAN_READY_STATUS,
    authorized_next_work: str = PLAN_AUTHORIZED_NEXT_WORK,
    missing_table: str | None = None,
    missing_test: str | None = None,
    blocked_action: bool = False,
    no_dp_import: bool = True,
) -> dict[str, object]:
    tables = [item for item in REQUIRED_TABLES if item != missing_table]
    tests = [item for item in REQUIRED_TESTS if item != missing_test]
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "diagnostic_implementation_plan_ready": True,
        "diagnostic_implementation_static_contract_review_authorized": True,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "diagnostic_implementation_plan": {
            "implementation_scope": {
                "planned_script": PLANNED_DIAGNOSTIC_SCRIPT,
                "planned_test": PLANNED_DIAGNOSTIC_TEST,
                "read_only_existing_artifacts": True,
                "current_tick_only": True,
                "json_serializable_scalars_only": True,
                "no_candidate_reconstruction": True,
                "no_reward_recompute": True,
                "no_tracker_recompute": True,
                "no_dp_import": no_dp_import,
                "score_contract": "score_k(w)=a_k^T w remains unchanged",
                "convex_master_contract": "simplex/CVaR/L2 master remains unchanged",
            },
            "observed_gap": {
                "primary_blocker_family": "comfort_support_zero_after_hard_support_pass",
                "hard_support_positive": True,
                "comfort_support_positive": False,
                "positive_support_evidence": False,
                "replay_evidence_ready": False,
                "training_ready": False,
            },
            "components": [
                {"name": "artifact_loader_contract"},
                {"name": "row_scalar_projection_contract"},
                {"name": "comfort_blocker_tables_contract"},
                {"name": "authorization_boundary_contract"},
            ],
            "required_tables": tables,
            "required_axes": list(REQUIRED_AXES),
            "required_tests": tests,
            "forbidden_actions": [
                "candidate generation execution is not authorized",
                "CAMP retraining and training execution are not authorized",
                "DP weights, DP code, DP configs, and DP invocation must remain fixed",
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str = "# Residual Comfort Diagnostic Implementation Plan\n",
) -> tuple[Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "plan"
    root.mkdir()
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    (root / PLAN_JSON).write_text(
        json.dumps(payload or _plan_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / PLAN_MD).write_text(markdown_text, encoding="utf-8")
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
        plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_diagnostic_implementation_static_review_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["diagnostic_implementation_only_authorized"] is True
    assert decision["next_gate_allowed_files"] == list(ALLOWED_NEXT_FILES)
    assert decision["next_gate_implementation_code_edit_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["production_implementation_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_residual_comfort_diagnostic_implementation_static_review_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_implementation_static_review_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_implementation_static_review_rejects_missing_table(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(missing_table="comfort_delta_quantiles"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_table_comfort_delta_quantiles" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_implementation_static_review_rejects_missing_test(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(
            missing_test="test_residual_comfort_failure_diagnostics_cli_writes_outputs"
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "contract_test_test_residual_comfort_failure_diagnostics_cli_writes_outputs"
        in report["final_decision"]["failed_checks"]
    )


def test_residual_comfort_diagnostic_implementation_static_review_rejects_dp_import(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(no_dp_import=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_no_dp_import" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_implementation_static_review_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_implementation_static_review_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Residual Comfort Diagnostic Implementation Static Contract Review" in markdown
    assert PLANNED_DIAGNOSTIC_SCRIPT in markdown
    assert PLANNED_DIAGNOSTIC_TEST in markdown
    assert "production implementation edits are not authorized" in markdown
    assert "candidate generation" in markdown
    assert "formal seeds" in markdown
    assert "DP modification" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_diagnostic_implementation_static_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "static_review.json"
    output_md = tmp_path / "out" / "static_review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--plan_root",
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
    assert "Residual Comfort Diagnostic Implementation Static Contract Review" in markdown
