from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_guarded_fixed_snapshot_screen_rerun_failure_attribution import (
    AUTHORIZED_NEXT_WORK as FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as FAILURE_ATTRIBUTION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_implementation_plan import (
    PLANNED_POLICY,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (
    ATTRIBUTION_JSON,
    ATTRIBUTION_MD,
    AUTHORIZED_NEXT_WORK,
    PRIMARY_BLOCKER_FAMILY,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={FAILURE_ATTRIBUTION_READY_STATUS}
authorized_next_work={FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK}
primary_blocker_family={PRIMARY_BLOCKER_FAMILY}
training_execution_authorized=False
dp_modification_authorized=False
"""


def _attribution_payload(
    *,
    status: str = FAILURE_ATTRIBUTION_READY_STATUS,
    authorized_next_work: str = FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    primary_blocker: str = PRIMARY_BLOCKER_FAMILY,
    hard_positive: bool = True,
    comfort_positive: bool = False,
    training_ready: bool = False,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "hard_support_positive": hard_positive,
        "comfort_support_positive": comfort_positive,
        "positive_support_evidence": False,
        "replay_evidence_ready": False,
        "training_ready": training_ready,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "read_only_attribution": {
            "primary_blocker_family": primary_blocker,
            "comfort_blocker_ranking": [
                {"name": "route_topology_comfort_blocked_command_jerk", "count": 58},
                {"name": "route_topology_comfort_blocked_rollout_lateral", "count": 57},
                {"name": "route_topology_comfort_blocked_command_lateral", "count": 54},
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    attribution_payload: dict[str, object] | None = None,
    attribution_markdown: str = "# Failure Attribution\n",
) -> tuple[Path, Path]:
    audit = tmp_path / "audit.md"
    root = tmp_path / "attribution"
    root.mkdir()
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    (root / ATTRIBUTION_JSON).write_text(
        json.dumps(
            attribution_payload or _attribution_payload(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / ATTRIBUTION_MD).write_text(attribution_markdown, encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    attribution_payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        attribution_payload=attribution_payload,
    )
    return build_report(
        attribution_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_failure_diagnostic_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["residual_comfort_diagnostic_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["diagnostic_scope"]["planned_policy"] == PLANNED_POLICY
    assert plan["observed_gap"]["primary_blocker_family"] == PRIMARY_BLOCKER_FAMILY
    assert plan["observed_gap"]["hard_support_positive"] is True
    assert plan["observed_gap"]["comfort_support_positive"] is False


def test_residual_comfort_failure_diagnostic_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_failure_diagnostic_plan_rejects_missing_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        audit_text=_audit_text().replace(
            FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
            "not_this_gate",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_this_plan" in report["final_decision"]["failed_checks"]


def test_residual_comfort_failure_diagnostic_plan_rejects_wrong_attribution_shape(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        attribution_payload=_attribution_payload(
            primary_blocker="wrong_blocker",
            hard_positive=False,
            comfort_positive=True,
            training_ready=True,
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = set(report["final_decision"]["failed_checks"])
    assert "attribution_primary_blocker" in failed
    assert "attribution_hard_support_positive" in failed
    assert "attribution_comfort_support_absent" in failed
    assert "attribution_training_not_ready" in failed


def test_residual_comfort_failure_diagnostic_plan_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        attribution_payload=_attribution_payload(blocked_action=True),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "attribution_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_failure_diagnostic_plan_components_are_scoped(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    plan = report["residual_comfort_diagnostic_plan"]
    table_names = {item["name"] for item in plan["diagnostic_tables"]}
    axes = set(plan["correlation_axes"])
    text = json.dumps(plan, sort_keys=True)

    assert "comfort_blocker_by_snapshot" in table_names
    assert "comfort_blocker_by_red_stop_partition" in table_names
    assert "comfort_blocker_by_offset_margin" in table_names
    assert "hard_progress_survivor_distribution" in table_names
    assert "comfort_delta_quantiles" in table_names
    assert "diagnostic_decision_boundary" in table_names
    assert "failure_class" in axes
    assert "lateral_offset_scale" in axes
    assert "red_stop_distance_partition" in axes
    assert "score_k(w)=a_k^T w" in text
    assert "simplex/CVaR/L2" in text


def test_residual_comfort_failure_diagnostic_plan_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Residual Comfort Diagnostic Plan" in markdown
    assert PRIMARY_BLOCKER_FAMILY in markdown
    assert "implementation edits are not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "formal seeds 11/12/13" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown


def test_residual_comfort_failure_diagnostic_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "diagnostic_plan.json"
    output_md = tmp_path / "out" / "diagnostic_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--attribution_root",
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
    assert markdown.startswith("# Negative-Support Residual Comfort Diagnostic Plan")
