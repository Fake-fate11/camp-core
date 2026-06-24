from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (
    AUTHORIZED_NEXT_WORK as DIAGNOSTICS_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DIAGNOSTICS_READY_STATUS,
    REQUIRED_TABLES,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DIAGNOSTICS_JSON,
    DIAGNOSTICS_MD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_TEST_NAMES,
    build_report,
    main,
    render_markdown,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={DIAGNOSTICS_READY_STATUS}
authorized_next_work={DIAGNOSTICS_AUTHORIZED_NEXT_WORK}
training_execution_authorized=False
dp_modification_authorized=False
"""


def _diagnostics_payload(
    *,
    status: str = DIAGNOSTICS_READY_STATUS,
    authorized_next_work: str = DIAGNOSTICS_AUTHORIZED_NEXT_WORK,
    missing_table: str | None = None,
    comfort_rows: int = 0,
    blocked_action: bool = False,
) -> dict[str, object]:
    tables = {
        name: [] if name != "diagnostic_decision_boundary" else {}
        for name in REQUIRED_TABLES
        if name != missing_table
    }
    tables["diagnostic_decision_boundary"] = {
        "primary_blocker_family": "comfort_support_zero_after_hard_support_pass",
        "generated_candidate_rows": 3,
        "hard_progress_survivor_rows": 2,
        "comfort_admissible_rows": comfort_rows,
        "hard_support_positive": True,
        "comfort_support_positive": False,
        "positive_support_evidence": False,
        "replay_evidence_ready": False,
        "training_ready": False,
    }
    if missing_table == "diagnostic_decision_boundary":
        tables.pop("diagnostic_decision_boundary")
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "post_implementation_static_contract_review_authorized": True,
        "production_implementation_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "analysis": {
            "read_only": True,
            "production_implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "reward_recompute": False,
            "tracker_recompute": False,
            "candidate_reconstruction": False,
            "training": False,
        },
        "source_summary": {
            "screen": {"generated_candidate_rows": 3},
        },
        "diagnostic_tables": tables,
        "final_decision": decision,
    }


def _source_text() -> str:
    return """
STATIC_REVIEW_AUTHORIZED_NEXT_WORK = "gate"
REQUIRED_TABLES = ("comfort_blocker_by_snapshot",)
BLOCKED_ACTIONS = ("training_execution_authorized",)
analysis = {
    "reward_recompute": False,
    "tracker_recompute": False,
    "candidate_reconstruction": False,
}
math_boundary = "does not import DP and preserves score_k(w)=a_k^T w and simplex/CVaR/L2"
"""


def _test_text() -> str:
    return "\n".join(f"def {name}(): pass" for name in REQUIRED_TEST_NAMES)


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    diagnostics_payload: dict[str, object] | None = None,
    source_text: str | None = None,
    test_text: str | None = None,
    markdown_text: str = "# Residual Comfort Failure Diagnostics\n",
) -> tuple[Path, Path, Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "diagnostics"
    source = tmp_path / "analyze.py"
    tests = tmp_path / "test_analyze.py"
    root.mkdir()
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    (root / DIAGNOSTICS_JSON).write_text(
        json.dumps(diagnostics_payload or _diagnostics_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / DIAGNOSTICS_MD).write_text(markdown_text, encoding="utf-8")
    source.write_text(source_text if source_text is not None else _source_text(), encoding="utf-8")
    tests.write_text(test_text if test_text is not None else _test_text(), encoding="utf-8")
    return audit, root, source, tests


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    diagnostics_payload: dict[str, object] | None = None,
    source_text: str | None = None,
    test_text: str | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root, source, tests = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        diagnostics_payload=diagnostics_payload,
        source_text=source_text,
        test_text=test_text,
    )
    return build_report(
        diagnostics_root=root,
        audit_path=audit,
        source_path=source,
        test_path=tests,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_diagnostic_post_static_review_complete(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["diagnostic_failure_attribution_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_residual_comfort_diagnostic_post_static_review_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_post_static_review_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_post_review" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_post_static_review_rejects_missing_table(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        diagnostics_payload=_diagnostics_payload(missing_table="comfort_delta_quantiles"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "diagnostics_table_comfort_delta_quantiles" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_post_static_review_rejects_comfort_rows(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, diagnostics_payload=_diagnostics_payload(comfort_rows=1))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "diagnostics_comfort_admissible_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_post_static_review_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, diagnostics_payload=_diagnostics_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "diagnostics_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_post_static_review_rejects_source_contract(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, source_text=_source_text().replace("does not import DP", "missing"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_contract_source_token_3" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_post_static_review_rejects_test_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        test_text=_test_text().replace(
            "test_residual_comfort_failure_diagnostics_cli_writes_outputs",
            "missing_test",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "test_contract_test_residual_comfort_failure_diagnostics_cli_writes_outputs"
        in report["final_decision"]["failed_checks"]
    )


def test_residual_comfort_diagnostic_post_static_review_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Review" in markdown
    assert "failure attribution only may follow" in markdown
    assert "formal seeds" in markdown
    assert "CAMP-over-DP" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_diagnostic_post_static_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root, source, tests = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--diagnostics_root",
            str(root),
            "--audit_path",
            str(audit),
            "--source_path",
            str(source),
            "--test_path",
            str(tests),
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
    assert "Residual Comfort Diagnostic Post-Implementation Static Review" in markdown
