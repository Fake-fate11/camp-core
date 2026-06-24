from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.plan_diffusion_planner_residual_comfort_remediation_"
    "followup_unit_tests"
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
    omit_finding: str | None = None,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "unit_tests_plan_authorized": True,
        "implementation_code_edit_authorized": False,
        "candidate_generation_execution_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
    }
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "static_contract_review": {
            "findings": [
                {"name": name, "finding": "ok"}
                for name in target.REQUIRED_REVIEW_FINDINGS
                if name != omit_finding
            ],
            "required_unit_test_families": [
                "default-off no candidate/score/selection/fallback mutation",
                "opt-in current-tick finite candidate-local descriptor payload",
                "nonnegative or legal hinge/signed-split descriptor contract",
                "affine score and convex master preservation",
                "DP/replay/training/formal-seed blocked-action contract",
                "CLI/report artifact boundary contract",
            ],
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Residual Comfort Remediation Follow-Up Implementation Static Contract Review\n",
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


def test_followup_unit_tests_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["unit_tests_plan"]
    families = {item["name"] for item in plan["test_families"]}

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["unit_tests_plan_ready"] is True
    assert decision["unit_tests_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["planned_test_file"] == target.PLANNED_CONTRACT_TEST
    assert set(target.REQUIRED_UNIT_TEST_FAMILIES).issubset(families)


def test_followup_unit_tests_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_followup_unit_tests_plan_rejects_missing_audit(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_unit_tests_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_unit_tests_plan_rejects_wrong_status(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_static_review_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_status_complete" in report["final_decision"]["failed_checks"]


def test_followup_unit_tests_plan_rejects_wrong_next_gate(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(authorized_next_work="wrong"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_unit_tests_plan_rejects_missing_finding(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        payload=_static_review_payload(omit_finding="affine_descriptor_contract"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_finding_affine_descriptor_contract" in report[
        "final_decision"
    ]["failed_checks"]


def test_followup_unit_tests_plan_rejects_blocked_action(tmp_path: Path) -> None:
    report = _build(tmp_path, payload=_static_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_followup_unit_tests_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "unit_tests_plan.json"
    output_md = tmp_path / "out" / "unit_tests_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "unit-tests-plan",
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
    assert "Residual Comfort Remediation Follow-Up Unit-Tests Plan" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "formal seeds 11/12/13" in markdown
