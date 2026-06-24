from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_failure_attribution import (
    AUTHORIZED_NEXT_WORK,
    DIAGNOSTICS_JSON,
    POST_REVIEW_JSON,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (
    READY_STATUS as DIAGNOSTICS_READY_STATUS,
    REQUIRED_TABLES,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK as POST_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as POST_REVIEW_READY_STATUS,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={POST_REVIEW_READY_STATUS}
authorized_next_work={POST_REVIEW_AUTHORIZED_NEXT_WORK}
training_execution_authorized=False
dp_modification_authorized=False
"""


def _diagnostics_payload(
    *,
    missing_table: str | None = None,
    comfort_rows: int = 0,
    no_blockers: bool = False,
) -> dict[str, object]:
    tables: dict[str, object] = {
        name: [] if name != "diagnostic_decision_boundary" else {}
        for name in REQUIRED_TABLES
        if name != missing_table
    }
    blocker_counts = (
        {}
        if no_blockers
        else {
            "route_topology_comfort_blocked_command_jerk": 4,
            "route_topology_comfort_blocked_rollout_lateral": 2,
        }
    )
    tables["hard_progress_survivor_distribution"] = {
        "hard_progress_survivor_rows": 4,
        "comfort_admissible_rows": comfort_rows,
        "comfort_blocker_counts": blocker_counts,
    }
    tables["comfort_blocker_by_snapshot"] = [
        {
            "snapshot_name": "s0.npz",
            "comfort_blocker_counts": blocker_counts,
        }
    ]
    tables["diagnostic_decision_boundary"] = {
        "primary_blocker_family": "comfort_support_zero_after_hard_support_pass",
        "hard_progress_survivor_rows": 4,
        "comfort_admissible_rows": comfort_rows,
        "hard_support_positive": True,
        "comfort_support_positive": False,
        "positive_support_evidence": False,
        "replay_evidence_ready": False,
        "training_ready": False,
    }
    if missing_table:
        tables.pop(missing_table, None)
    return {
        "diagnostic_tables": tables,
        "final_decision": {
            "status": DIAGNOSTICS_READY_STATUS,
            "passed": True,
            "failed_checks": [],
        },
    }


def _post_review_payload(
    *,
    authorized_next_work: str = POST_REVIEW_AUTHORIZED_NEXT_WORK,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": POST_REVIEW_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "diagnostic_failure_attribution_authorized": True,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {"final_decision": decision}


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    diagnostics_payload: dict[str, object] | None = None,
    post_review_payload: dict[str, object] | None = None,
) -> tuple[Path, Path, Path]:
    audit = tmp_path / "audit.md"
    diagnostics = tmp_path / "diagnostics"
    post_review = tmp_path / "post_review"
    diagnostics.mkdir()
    post_review.mkdir()
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    (diagnostics / DIAGNOSTICS_JSON).write_text(
        json.dumps(diagnostics_payload or _diagnostics_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (post_review / POST_REVIEW_JSON).write_text(
        json.dumps(post_review_payload or _post_review_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return audit, diagnostics, post_review


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    diagnostics_payload: dict[str, object] | None = None,
    post_review_payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, diagnostics, post_review = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        diagnostics_payload=diagnostics_payload,
        post_review_payload=post_review_payload,
    )
    return build_report(
        diagnostics_root=diagnostics,
        post_review_root=post_review,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_diagnostic_failure_attribution_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    attribution = report["read_only_attribution"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["remediation_design_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert attribution["residual_failure_family"] == (
        "jerk_dominated_comfort_gap_after_hard_progress_survival"
    )


def test_residual_comfort_diagnostic_failure_attribution_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_failure_attribution_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_failure_attribution" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_failure_attribution_rejects_missing_table(
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


def test_residual_comfort_diagnostic_failure_attribution_rejects_comfort_rows(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, diagnostics_payload=_diagnostics_payload(comfort_rows=1))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "diagnostics_comfort_zero" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_failure_attribution_rejects_missing_blockers(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, diagnostics_payload=_diagnostics_payload(no_blockers=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "attribution_has_ranked_blockers" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_failure_attribution_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, post_review_payload=_post_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "post_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_failure_attribution_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Residual Comfort Diagnostic Failure Attribution" in markdown
    assert "remediation design planning only may follow" in markdown
    assert "formal seeds" in markdown
    assert "CAMP-over-DP" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_diagnostic_failure_attribution_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, diagnostics, post_review = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "failure_attribution.json"
    output_md = tmp_path / "out" / "failure_attribution.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze",
            "--diagnostics_root",
            str(diagnostics),
            "--post_review_root",
            str(post_review),
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
    assert "Residual Comfort Diagnostic Failure Attribution" in markdown
