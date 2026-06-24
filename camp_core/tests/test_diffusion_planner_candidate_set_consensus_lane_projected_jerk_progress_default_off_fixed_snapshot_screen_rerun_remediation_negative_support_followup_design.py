from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_guarded_fixed_snapshot_screen_rerun_failure_attribution import (
    AUTHORIZED_NEXT_WORK as FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as FAILURE_ATTRIBUTION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_design import (
    AUTHORIZED_NEXT_WORK,
    FAILURE_JSON,
    FAILURE_MD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_AUDIT_AUTHORIZATION,
    build_report,
    main,
    render_markdown,
)


def _audit_text() -> str:
    return f"""
Decision:

Accept with negative support evidence.

Next admissible gate:

`{REQUIRED_AUDIT_AUTHORIZATION}`.

primary_blocker_family=hard_support_below_threshold_and_comfort_support_zero
"""


def _failure_payload(
    *,
    status: str = FAILURE_ATTRIBUTION_READY_STATUS,
    passed: bool = True,
    authorized_next_work: str = FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    positive_support: bool = False,
    training_ready: bool = False,
    blocked_action: bool = False,
    primary_blocker: str = "hard_support_below_threshold_and_comfort_support_zero",
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "positive_support_evidence": positive_support,
        "training_ready": training_ready,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["fixed_snapshot_screen_rerun_authorized"] = True
    return {
        "final_decision": decision,
        "source_summary": {
            "status": "route_topology_candidate_support_insufficient",
            "snapshots": 57,
            "snapshots_with_generated_candidates": 27,
            "generated_candidate_rows": 324,
            "hard_support_rate": 0.14814814814814814,
            "comfort_support_rate": 0.0,
            "comfort_admissible_rows": 0,
        },
        "read_only_attribution": {
            "primary_blocker_family": primary_blocker,
            "construction_status_ranking": [
                {"name": "fail_closed", "count": 30},
                {"name": "ready", "count": 27},
            ],
            "comfort_blocker_ranking": [
                {
                    "name": "route_topology_comfort_blocked_command_lateral",
                    "count": 37,
                    "hard_progress_feasible_count": 37,
                }
            ],
            "hard_blocker_ranking": [{"name": "dp_red_light", "count": 275}],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    audit_text: str | None = None,
    markdown_text: str | None = None,
) -> tuple[Path, Path]:
    root = tmp_path / "failure"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / FAILURE_JSON).write_text(
        json.dumps(payload or _failure_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / FAILURE_MD).write_text(
        markdown_text
        if markdown_text is not None
        else "# Failure\n\n## Boundaries\n\nread only\n",
        encoding="utf-8",
    )
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    audit_text: str | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(tmp_path, payload=payload, audit_text=audit_text)
    return build_report(
        failure_attribution_root=root,
        audit_path=audit,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_negative_support_followup_design_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["design_plan"]
    component_names = {component["name"] for component in plan["components"]}

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_authorized"] is True
    assert decision["production_implementation_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert "coverage_first_fail_closed_partition" in component_names
    assert "hard_feasibility_support_floor" in component_names
    assert "comfort_feasibility_after_hard_progress" in component_names
    assert "nonformal_screen_only_readiness" in component_names


def test_negative_support_followup_design_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_negative_support_followup_design_rejects_missing_audit_authorization(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="no current gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_design_plan" in report["final_decision"]["failed_checks"]


def test_negative_support_followup_design_rejects_positive_support(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(positive_support=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_no_positive_support" in report["final_decision"][
        "failed_checks"
    ]


def test_negative_support_followup_design_rejects_blocked_action_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_negative_support_followup_design_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Negative-Support Follow-Up Design Plan" in markdown
    assert "coverage_first_fail_closed_partition" in markdown
    assert "comfort_feasibility_after_hard_progress" in markdown
    assert "production implementation edits are not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_negative_support_followup_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "design_plan.json"
    output_md = tmp_path / "out" / "design_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "design",
            "--failure_attribution_root",
            str(root),
            "--audit_path",
            str(audit),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
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
    assert "Negative-Support Follow-Up Design Plan" in markdown
