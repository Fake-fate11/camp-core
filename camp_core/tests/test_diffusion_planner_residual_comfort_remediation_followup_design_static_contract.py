from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_"
    "remediation_followup_design_static_contract"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.PLAN_READY_STATUS}
authorized_next_work={target.PLAN_AUTHORIZED_NEXT_WORK}
candidate_generation_execution_authorized=False
fixed_snapshot_screen_rerun_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _plan_payload(
    *,
    status: str = target.PLAN_READY_STATUS,
    authorized_next_work: str = target.PLAN_AUTHORIZED_NEXT_WORK,
    residual_family: str = target.RESIDUAL_FAMILY,
    omit_track: str | None = None,
    omit_rejected: str | None = None,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    tracks = [
        {
            "name": name,
            "purpose": "current-tick finite candidate-local plan",
            "evidence": "evidence",
            "contract": (
                "no candidate, score, selected-index, fallback, online selector, "
                "or deployed atom-schema mutation; nonnegative hinge/signed-split "
                "score_k(w)=a_k^T w simplex/CVaR/L2 DP weights DP code "
                "formal seeds 11/12/13"
            ),
        }
        for name in target.REQUIRED_TRACKS
        if name != omit_track
    ]
    rejected = [
        {"name": name, "reason": "blocked"}
        for name in target.REQUIRED_REJECTED_NON_FIXES
        if name != omit_rejected
    ]
    return {
        "analysis": {"plan_only": True},
        "final_decision": decision,
        "followup_design_plan": {
            "selection_type": "residual_comfort_remediation_followup_design_plan_only",
            "authorized_next_work": target.PLAN_AUTHORIZED_NEXT_WORK,
            "target_failure": {
                "residual_family": residual_family,
                "primary_blocker_family": "comfort_support_zero_after_hard_support_pass",
            },
            "tracks": tracks,
            "static_review_requirements": [
                "finite current-tick candidate-local features",
                "nonnegative hinge/signed-split score_k(w)=a_k^T w simplex/CVaR/L2",
                "formal seeds 11/12/13 frozen; DP weights and DP code fixed",
            ],
            "rejected_non_fixes": rejected,
            "blocked_boundaries": [
                "candidate generation and screen rerun are not authorized",
                "CAMP retraining is not authorized",
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Residual Comfort Remediation Follow-Up Design Plan\n",
) -> tuple[Path, Path]:
    root = tmp_path / "plan"
    root.mkdir()
    audit = tmp_path / "audit.md"
    (root / target.PLAN_JSON).write_text(
        json.dumps(payload or _plan_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / target.PLAN_MD).write_text(markdown, encoding="utf-8")
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
        plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_followup_design_static_contract_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    contract = report["static_contract_review"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_complete"] is True
    assert decision["implementation_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert contract["residual_family"] == target.RESIDUAL_FAMILY


def test_followup_design_static_contract_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_followup_design_static_contract_rejects_missing_audit(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_design_static_contract_rejects_wrong_plan_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "plan_status_ready" in report["final_decision"]["failed_checks"]


def test_followup_design_static_contract_rejects_missing_track(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(omit_track="command_jerk_rollout_lateral_descriptor_family"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "plan_track_command_jerk_rollout_lateral_descriptor_family"
        in report["final_decision"]["failed_checks"]
    )


def test_followup_design_static_contract_rejects_missing_rejected_non_fix(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_plan_payload(omit_rejected="train_on_negative_support"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "plan_rejects_train_on_negative_support" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_design_static_contract_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "plan_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_followup_design_static_contract_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "static_contract_review.json"
    output_md = tmp_path / "out" / "static_contract_review.md"
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
    assert "Residual Comfort Remediation Follow-Up Design Static Contract Review" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
