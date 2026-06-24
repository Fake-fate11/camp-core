from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_failure_attribution import (
    AUTHORIZED_NEXT_WORK as FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    READY_STATUS as FAILURE_ATTRIBUTION_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_design import (
    AUTHORIZED_NEXT_WORK,
    FAILURE_JSON,
    FAILURE_MD,
    PRIMARY_BLOCKER_FAMILY,
    READY_STATUS,
    REJECT_STATUS,
    RESIDUAL_FAILURE_FAMILY,
    TOP_COMFORT_BLOCKER,
    build_report,
    main,
    render_markdown,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={FAILURE_ATTRIBUTION_READY_STATUS}
authorized_next_work={FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK}
residual_failure_family={RESIDUAL_FAILURE_FAMILY}
top_comfort_blocker={TOP_COMFORT_BLOCKER}
candidate_generation_execution_authorized=False
fixed_snapshot_screen_rerun_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _failure_payload(
    *,
    status: str = FAILURE_ATTRIBUTION_READY_STATUS,
    authorized_next_work: str = FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    residual_family: str = RESIDUAL_FAILURE_FAMILY,
    top_blocker: str = TOP_COMFORT_BLOCKER,
    comfort_rows: int = 0,
    blocked_action: bool = False,
    training_ready: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "remediation_design_plan_authorized": True,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "read_only_attribution": {
            "primary_blocker_family": PRIMARY_BLOCKER_FAMILY,
            "residual_failure_family": residual_family,
            "hard_progress_survivor_rows": 58,
            "comfort_admissible_rows": comfort_rows,
            "comfort_blocker_ranking": [
                {"name": top_blocker, "count": 58},
                {
                    "name": "route_topology_comfort_blocked_rollout_lateral",
                    "count": 11,
                },
            ],
            "top_comfort_blocker": top_blocker,
            "remediation_design_needed": True,
            "replay_evidence_ready": False,
            "training_ready": training_ready,
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str = "# Residual Comfort Diagnostic Failure Attribution\n",
) -> tuple[Path, Path]:
    root = tmp_path / "failure_attribution"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / FAILURE_JSON).write_text(
        json.dumps(payload or _failure_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / FAILURE_MD).write_text(markdown_text, encoding="utf-8")
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
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
        failure_attribution_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_remediation_design_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["remediation_design_plan"]
    tracks = {item["name"] for item in plan["remediation_tracks"]}

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["remediation_design_plan_ready"] is True
    assert decision["static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["target_failure"]["residual_failure_family"] == RESIDUAL_FAILURE_FAMILY
    assert plan["target_failure"]["top_comfort_blocker"] == TOP_COMFORT_BLOCKER
    assert "hard_progress_survivor_comfort_gap_partition" in tracks
    assert "command_jerk_hinge_descriptor_family" in tracks
    assert "jerk_bounded_support_intervention_boundary" in tracks
    assert "positive_support_before_training_gate" in tracks
    assert "dp_fixed_black_box_boundary" in tracks


def test_residual_comfort_remediation_design_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_residual_comfort_remediation_design_rejects_missing_audit_authorization(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_remediation_design" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_rejects_wrong_attribution_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(status="wrong"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_status_complete" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_rejects_wrong_next_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(authorized_next_work="wrong"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_rejects_wrong_residual_family(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(residual_family="mixed"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_residual_family" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_rejects_wrong_top_blocker(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(top_blocker="wrong"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_top_comfort_blocker" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_rejects_blocked_action_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_rejects_training_ready_source(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_failure_payload(training_ready=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_attribution_training_not_ready" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_design_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Residual Comfort Failure Remediation Design Plan" in markdown
    assert "command_jerk_hinge_descriptor_family" in markdown
    assert "current-tick finite candidate features" in markdown
    assert "no mutation of candidates" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "CAMP-over-DP-Top-1" in markdown


def test_residual_comfort_remediation_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "remediation_design_plan.json"
    output_md = tmp_path / "out" / "remediation_design_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "design",
            "--failure_attribution_root",
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

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Residual Comfort Failure Remediation Design Plan" in markdown
