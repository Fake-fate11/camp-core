from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_"
    "remediation_followup_implementation_static_contract"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.IMPLEMENTATION_PLAN_READY_STATUS}
authorized_next_work={target.IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK}
implementation_code_edit_authorized=False
candidate_generation_execution_authorized=False
training_execution_authorized=False
dp_modification_authorized=False
"""


def _implementation_plan_payload(
    *,
    status: str = target.IMPLEMENTATION_PLAN_READY_STATUS,
    authorized_next_work: str = target.IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK,
    omit_file: str | None = None,
    omit_slice: str | None = None,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "implementation_plan": {
            "selection_type": "residual_comfort_remediation_followup_implementation_plan_only",
            "authorized_next_work": target.IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK,
            "target_contract": {
                "residual_family": target.RESIDUAL_FAMILY,
                "formal_seeds": [11, 12, 13],
                "score_contract": "score_k(w)=a_k^T w",
                "master_contract": "convex simplex/CVaR/L2 master unchanged",
            },
            "planned_files": [
                {"path": path, "purpose": "planned"}
                for path in target.REQUIRED_FILES
                if path != omit_file
            ],
            "implementation_slices": [
                {
                    "name": name,
                    "purpose": "default-off current-tick candidate-local plan",
                    "contract": (
                        "nonnegative hinge/signed-split score_k(w)=a_k^T w "
                        "simplex/CVaR/L2 online selector DP weights "
                        "DP modification formal seeds 11/12/13"
                    ),
                }
                for name in target.REQUIRED_SLICES
                if name != omit_slice
            ],
            "required_tests": ["unit test"] * 6,
            "blocked_boundaries": ["blocked"],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Residual Comfort Remediation Follow-Up Implementation Plan\n",
) -> tuple[Path, Path]:
    root = tmp_path / "implementation_plan"
    root.mkdir()
    audit = tmp_path / "audit.md"
    (root / target.IMPLEMENTATION_PLAN_JSON).write_text(
        json.dumps(payload or _implementation_plan_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / target.IMPLEMENTATION_PLAN_MD).write_text(markdown, encoding="utf-8")
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
        implementation_plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_followup_implementation_static_contract_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["implementation_static_contract_review_complete"] is True
    assert decision["unit_tests_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_followup_implementation_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_followup_implementation_static_contract_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_implementation_static_contract_rejects_wrong_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_implementation_plan_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "implementation_plan_status_ready" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_implementation_static_contract_rejects_missing_file(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_implementation_plan_payload(omit_file=target.PLANNED_CONTRACT_TEST),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert f"implementation_plan_file_{target.PLANNED_CONTRACT_TEST}" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_implementation_static_contract_rejects_missing_slice(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_implementation_plan_payload(
            omit_slice="command_jerk_rollout_lateral_hinge_terms"
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "implementation_plan_slice_command_jerk_rollout_lateral_hinge_terms" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_implementation_static_contract_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_implementation_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "implementation_plan_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_implementation_static_contract_cli_writes_outputs(
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
            "--implementation_plan_root",
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
    assert "Residual Comfort Remediation Follow-Up Implementation Static Contract Review" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
