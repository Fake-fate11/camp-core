from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.plan_diffusion_planner_residual_comfort_remediation_"
    "followup_implementation"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.STATIC_REVIEW_READY_STATUS}
authorized_next_work={target.STATIC_REVIEW_AUTHORIZED_NEXT_WORK}
implementation_code_edit_authorized=False
candidate_generation_execution_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _static_review_payload(
    *,
    status: str = target.STATIC_REVIEW_READY_STATUS,
    authorized_next_work: str = target.STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    residual_family: str = target.RESIDUAL_FAMILY,
    omit_finding: str | None = None,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "implementation_plan_authorized": True,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    findings = [
        {"name": name, "finding": "ok"}
        for name in target.REQUIRED_STATIC_FINDINGS
        if name != omit_finding
    ]
    return {
        "final_decision": decision,
        "static_contract_review": {
            "residual_family": residual_family,
            "contract_findings": findings,
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Residual Comfort Remediation Follow-Up Design Static Contract Review\n",
) -> tuple[Path, Path]:
    root = tmp_path / "static_review"
    root.mkdir()
    audit = tmp_path / "audit.md"
    (root / target.STATIC_REVIEW_JSON).write_text(
        json.dumps(payload or _static_review_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / target.STATIC_REVIEW_MD).write_text(markdown, encoding="utf-8")
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
        static_review_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_followup_implementation_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    files = {item["path"] for item in plan["planned_files"]}
    slices = {item["name"] for item in plan["implementation_slices"]}

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_ready"] is True
    assert decision["implementation_static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert target.PLANNED_SCREEN_SOURCE in files
    assert target.PLANNED_ROUTE_TEST in files
    assert target.PLANNED_CONTRACT_TEST in files
    assert "default_off_report_only_descriptor_payload" in slices
    assert "command_jerk_rollout_lateral_hinge_terms" in slices
    assert "positive_support_gate_stays_external" in slices


def test_followup_implementation_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_followup_implementation_plan_rejects_missing_audit(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_implementation_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_implementation_plan_rejects_wrong_static_review_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_static_review_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_status_complete" in report["final_decision"]["failed_checks"]


def test_followup_implementation_plan_rejects_missing_static_finding(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(omit_finding="affine_convex_math_boundary"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_finding_affine_convex_math_boundary" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_implementation_plan_rejects_blocked_action(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_static_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_implementation_plan_rejects_wrong_residual_family(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_static_review_payload(residual_family="mixed"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_residual_family" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_implementation_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "implementation_plan.json"
    output_md = tmp_path / "out" / "implementation_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "implementation-plan",
            "--static_review_root",
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
    assert "Residual Comfort Remediation Follow-Up Implementation Plan" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "formal seeds 11/12/13" in markdown
