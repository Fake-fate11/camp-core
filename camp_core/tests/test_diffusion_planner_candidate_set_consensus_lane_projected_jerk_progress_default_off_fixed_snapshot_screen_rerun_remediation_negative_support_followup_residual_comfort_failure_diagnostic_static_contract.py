from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_static_contract import (
    AUTHORIZED_NEXT_WORK,
    PLAN_JSON,
    PLAN_MD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
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
    blocked_action: bool = False,
) -> dict[str, object]:
    tables = [
        {"name": "comfort_blocker_by_snapshot", "contract": "table"},
        {"name": "comfort_blocker_by_red_stop_partition", "contract": "table"},
        {"name": "comfort_blocker_by_offset_margin", "contract": "table"},
        {"name": "hard_progress_survivor_distribution", "contract": "table"},
        {"name": "comfort_delta_quantiles", "contract": "table"},
        {"name": "diagnostic_decision_boundary", "contract": "table"},
    ]
    if missing_table:
        tables = [item for item in tables if item["name"] != missing_table]
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "static_contract_review_authorized": True,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "residual_comfort_diagnostic_plan": {
            "diagnostic_scope": {
                "planned_policy": "negative_support_coverage_first_lane_projected_red_stop",
                "read_only_existing_artifacts": True,
                "no_candidate_reconstruction": True,
                "json_serializable_scalars_only": True,
            },
            "observed_gap": {
                "primary_blocker_family": "comfort_support_zero_after_hard_support_pass",
                "hard_support_positive": True,
                "comfort_support_positive": False,
                "positive_support_evidence": False,
                "replay_evidence_ready": False,
                "training_ready": False,
            },
            "diagnostic_tables": tables,
            "correlation_axes": [
                "failure_class",
                "snapshot_name",
                "red_stop_distance_partition",
                "lateral_offset_scale",
                "red_stop_margin_m",
                "backup_stop_offset_m",
                "hard_feasible",
                "progress_feasible",
                "comfort_admissible",
            ],
            "static_review_requirements": [
                "prove no DP import, reward recompute, tracker recompute, candidate generation, screen rerun, or replay is required",
                "prove score_k(w)=a_k^T w and the convex simplex/CVaR/L2 master remain unchanged",
            ],
            "blocked_boundaries": [
                "candidate generation execution is not authorized",
                "fixed-snapshot screen rerun is not authorized",
                "formal seeds 11/12/13 remain frozen and unused",
                "no safety-benefit claim, CAMP-over-DP-Top-1 claim, or classical Benders claim is authorized",
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    plan_payload: dict[str, object] | None = None,
    markdown_text: str = "# Negative-Support Residual Comfort Diagnostic Plan\n",
) -> tuple[Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "plan"
    root.mkdir()
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    (root / PLAN_JSON).write_text(
        json.dumps(plan_payload or _plan_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / PLAN_MD).write_text(markdown_text, encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    plan_payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        plan_payload=plan_payload,
    )
    return build_report(
        plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_diagnostic_static_contract_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["diagnostic_implementation_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_residual_comfort_diagnostic_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_static_contract_rejects_missing_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        audit_text=_audit_text().replace(PLAN_AUTHORIZED_NEXT_WORK, "not_this_gate"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_static_contract_rejects_missing_table(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        plan_payload=_plan_payload(missing_table="comfort_delta_quantiles"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_table_comfort_delta_quantiles" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_diagnostic_static_contract_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, plan_payload=_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_static_contract_rejects_missing_markdown(
    tmp_path: Path,
) -> None:
    audit, root = _write_inputs(tmp_path, markdown_text="# other\n")
    report = build_report(
        plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_markdown_records_title" in report["final_decision"]["failed_checks"]


def test_residual_comfort_diagnostic_static_contract_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Static Contract Review" in markdown
    assert "implementation edits are not authorized" in markdown
    assert "candidate generation and screen rerun are not authorized" in markdown
    assert "formal seeds" in markdown
    assert "DP modification" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_diagnostic_static_contract_cli_writes_outputs(
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
            "cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert report["analysis"]["label"] == "cli"
    assert report["final_decision"]["status"] == READY_STATUS
    assert markdown.startswith("# Residual Comfort Diagnostic Static Contract Review")
