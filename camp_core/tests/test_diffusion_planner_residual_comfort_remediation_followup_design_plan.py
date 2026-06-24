from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.plan_diffusion_planner_residual_comfort_remediation_"
    "followup_design"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.FAILURE_ATTRIBUTION_READY_STATUS}
authorized_next_work={target.FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK}
top_comfort_blockers={target.TOP_COMMAND_JERK_BLOCKER}:58,{target.TOP_ROLLOUT_LATERAL_BLOCKER}:57
candidate_generation_execution_authorized=False
fixed_snapshot_screen_rerun_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _attribution_payload(
    *,
    status: str = target.FAILURE_ATTRIBUTION_READY_STATUS,
    authorized_next_work: str = target.FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    primary: str = target.PRIMARY_BLOCKER_FAMILY,
    blocked_action: bool = False,
    training_ready: bool = False,
    comfort_gap: float = 0.25,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "positive_support_evidence": False,
        "replay_evidence_ready": False,
        "training_ready": training_ready,
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
            "primary_blocker_family": primary,
            "hard_support_positive": True,
            "comfort_support_positive": False,
            "positive_support_evidence": False,
            "replay_evidence_ready": False,
            "training_ready": training_ready,
            "comfort_support_gap": comfort_gap,
            "candidate_coverage_rate": 0.47368421052631576,
            "comfort_blocker_ranking": [
                {"name": target.TOP_COMMAND_JERK_BLOCKER, "count": 58},
                {"name": target.TOP_ROLLOUT_LATERAL_BLOCKER, "count": 57},
                {
                    "name": "route_topology_comfort_blocked_command_lateral",
                    "count": 54,
                },
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Residual Comfort Remediation Screen Failure Attribution\n",
) -> tuple[Path, Path]:
    root = tmp_path / "failure_attribution"
    root.mkdir()
    audit = tmp_path / "audit.md"
    (root / target.ATTRIBUTION_JSON).write_text(
        json.dumps(payload or _attribution_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / target.ATTRIBUTION_MD).write_text(markdown, encoding="utf-8")
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    dp_head: str = target.EXPECTED_DP_HEAD,
) -> dict:
    audit, root = _write_inputs(tmp_path, audit_text=audit_text, payload=payload)
    return target.build_report(
        failure_attribution_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_remediation_followup_design_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["followup_design_plan"]
    tracks = {item["name"] for item in plan["tracks"]}

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["followup_design_plan_ready"] is True
    assert decision["static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["target_failure"]["residual_family"] == target.RESIDUAL_FAMILY
    assert "comfort_gap_blocker_partition" in tracks
    assert "command_jerk_rollout_lateral_descriptor_family" in tracks
    assert "support_intervention_static_boundary" in tracks
    assert "positive_support_before_training_gate" in tracks
    assert "dp_fixed_black_box_boundary" in tracks


def test_residual_comfort_remediation_followup_design_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_residual_comfort_remediation_followup_design_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_followup_design" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_followup_design_rejects_wrong_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_status_complete" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_followup_design_rejects_wrong_next_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_followup_design_rejects_missing_blocker(
    tmp_path: Path,
) -> None:
    payload = _attribution_payload()
    attribution = payload["read_only_attribution"]
    assert isinstance(attribution, dict)
    attribution["comfort_blocker_ranking"] = [
        {"name": target.TOP_COMMAND_JERK_BLOCKER, "count": 58}
    ]
    report = _build(tmp_path, payload=payload)

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_rollout_lateral_blocker" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_followup_design_rejects_training_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(training_ready=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_training_not_ready" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_followup_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "followup_design_plan.json"
    output_md = tmp_path / "out" / "followup_design_plan.md"
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
            target.EXPECTED_DP_HEAD,
            "--label",
            "unit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    target.main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert report["final_decision"]["status"] == target.READY_STATUS
    assert "Residual Comfort Remediation Follow-Up Design Plan" in markdown
    assert "command_jerk_rollout_lateral_descriptor_family" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
