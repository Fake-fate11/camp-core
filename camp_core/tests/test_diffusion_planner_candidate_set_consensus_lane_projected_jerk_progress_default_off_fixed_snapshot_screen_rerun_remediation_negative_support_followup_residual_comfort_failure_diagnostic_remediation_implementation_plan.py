from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_implementation_plan import (
    AUTHORIZED_NEXT_WORK,
    PLANNED_CONTRACT_TEST,
    PLANNED_ROUTE_TEST,
    PLANNED_SCREEN_SOURCE,
    READY_STATUS,
    REJECT_STATUS,
    STATIC_REVIEW_JSON,
    STATIC_REVIEW_MD,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_remediation_design_static_contract import (
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={STATIC_REVIEW_READY_STATUS}
authorized_next_work={STATIC_REVIEW_AUTHORIZED_NEXT_WORK}
implementation_code_edit_authorized=False
candidate_generation_execution_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _static_review_payload(
    *,
    status: str = STATIC_REVIEW_READY_STATUS,
    authorized_next_work: str = STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    contract_name: str | None = None,
    contract_status: str = "pass",
    blocked_action: bool = False,
) -> dict[str, object]:
    contracts = [
        {"name": "required_tracks_present", "status": "pass"},
        {"name": "rejected_non_fixes_present", "status": "pass"},
        {"name": "atom_math_contract", "status": "pass"},
        {"name": "convex_master_contract", "status": "pass"},
        {"name": "execution_training_boundary", "status": "pass"},
        {"name": "dp_fixed_boundary", "status": "pass"},
        {"name": "claim_boundary", "status": "pass"},
    ]
    if contract_name:
        for item in contracts:
            if item["name"] == contract_name:
                item["status"] = contract_status
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "remediation_implementation_plan_authorized": True,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["candidate_generation_execution_authorized"] = True
    return {
        "final_decision": decision,
        "static_contract_review": {
            "all_contracts_pass": all(item["status"] == "pass" for item in contracts),
            "contracts": contracts,
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown_text: str = "# Residual Comfort Remediation Design Static Contract Review\n",
) -> tuple[Path, Path]:
    root = tmp_path / "static_review"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / STATIC_REVIEW_JSON).write_text(
        json.dumps(payload or _static_review_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / STATIC_REVIEW_MD).write_text(markdown_text, encoding="utf-8")
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
        static_review_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_remediation_implementation_plan_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["remediation_implementation_plan"]
    scope = plan["implementation_scope"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["remediation_implementation_plan_ready"] is True
    assert decision["remediation_implementation_static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert PLANNED_SCREEN_SOURCE in scope["planned_files"]
    assert PLANNED_ROUTE_TEST in scope["planned_files"]
    assert PLANNED_CONTRACT_TEST in scope["planned_files"]
    assert scope["default_off"] is True
    assert scope["report_only_until_execution_gate"] is True
    assert scope["no_candidate_mutation"] is True
    assert scope["no_online_selector_change"] is True
    assert scope["no_dp_import"] is True


def test_residual_comfort_remediation_implementation_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_plan_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_authorizes_implementation_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_implementation_plan_rejects_wrong_review_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_static_review_payload(status="wrong"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_status_complete" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_plan_rejects_wrong_next_gate(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(authorized_next_work="wrong"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_implementation_plan_rejects_failed_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(
            contract_name="atom_math_contract",
            contract_status="fail",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_all_contracts_pass" in report["final_decision"][
        "failed_checks"
    ]
    assert "static_review_math_contract" in report["final_decision"]["failed_checks"]


def test_residual_comfort_remediation_implementation_plan_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_static_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_remediation_implementation_plan_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Residual Comfort Remediation Implementation Plan" in markdown
    assert PLANNED_SCREEN_SOURCE in markdown
    assert "command_jerk_descriptor_payload" in markdown
    assert "no mutation of candidates" in markdown
    assert "implementation code edits are not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_residual_comfort_remediation_implementation_plan_cli_writes_outputs(
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
    assert markdown.startswith("# Residual Comfort Remediation Implementation Plan")
