from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.plan_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_guarded_fixed_snapshot_screen_"
    "rerun_failure_attribution_remediation_guarded_fixed_snapshot_screen_"
    "rerun_failure_attribution_remediation_implementation"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.STATIC_REVIEW_READY_STATUS}
passed=True
failed_checks=[]
authorized_next_work={target.STATIC_REVIEW_AUTHORIZED_NEXT_WORK}
training_execution_authorized=False
dp_modification_authorized=False
dp_head={target.EXPECTED_DP_HEAD}
"""


def _review_payload(
    *,
    status: str = target.STATIC_REVIEW_READY_STATUS,
    authorized_next_work: str = target.STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    implementation_plan_authorized: bool = True,
    blocked_action: bool = False,
    missing_contract: str | None = None,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "implementation_plan_authorized": implementation_plan_authorized,
    }
    for key in target.BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["training_execution_authorized"] = True
    contract = {key: True for key in target.REQUIRED_CONTRACTS}
    if missing_contract is not None:
        contract[missing_contract] = False
    return {"final_decision": decision, "static_contract": contract}


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    payload: dict[str, object] | None = None,
    markdown: str = "# Material Generator V2 Remediation Design Static Contract Review\n",
) -> tuple[Path, Path]:
    root = tmp_path / "static_review"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / target.STATIC_REVIEW_JSON).write_text(
        json.dumps(payload or _review_payload(), indent=2, sort_keys=True)
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
) -> dict[str, object]:
    audit, root = _write_inputs(tmp_path, audit_text=audit_text, payload=payload)
    return target.build_report(
        static_review_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_v3_remediation_implementation_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]
    slices = {item["name"] for item in plan["implementation_slices"]}
    tests = {item["name"] for item in plan["required_tests"]}

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["remediation_implementation_plan_ready"] is True
    assert decision["implementation_only_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["new_default_off_profile"] == target.NEW_PROFILE
    assert plan["new_generator_policy"] == target.NEW_POLICY
    assert target.PRODUCTION_FILE in plan["allowed_files"]
    assert target.ROUTE_TEST_FILE in plan["allowed_files"]
    assert target.UNIT_TEST_FILE in plan["allowed_files"]
    assert "explicit_v3_profile_policy_pair" in slices
    assert "near_threshold_hard_support_precheck_v3" in slices
    assert "comfort_first_profile_precheck_v3" in slices
    assert "lane_corridor_continuity_tightening_v3" in slices
    assert "stop_creep_progress_balance_v3" in slices
    assert "diagnostic_descriptor_payload_v3_report_only" in slices
    assert "default_off_v1_v2_behavior_unchanged" in tests
    assert "v3_explicit_pair_required" in tests
    assert "candidate0_and_dp_rows_preserved" in tests
    assert "hard_support_precheck_fail_closed" in tests
    assert "comfort_first_precheck_fail_closed" in tests
    assert "finite_current_tick_inputs_only" in tests
    assert "descriptor_legality_and_affine_contract" in tests


def test_v3_remediation_implementation_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_v3_remediation_implementation_plan_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_implementation_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_v3_remediation_implementation_plan_rejects_wrong_review_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_review_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_status_complete" in report["final_decision"][
        "failed_checks"
    ]


def test_v3_remediation_implementation_plan_rejects_wrong_next(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_review_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_v3_remediation_implementation_plan_rejects_unapproved_review(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_review_payload(implementation_plan_authorized=False),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_implementation_plan_authorized" in report[
        "final_decision"
    ]["failed_checks"]


def test_v3_remediation_implementation_plan_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_review_payload(missing_contract="affine_convex_master_contract"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_required_contracts_true" in report["final_decision"][
        "failed_checks"
    ]


def test_v3_remediation_implementation_plan_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_no_blocked_actions" in report["final_decision"][
        "failed_checks"
    ]


def test_v3_remediation_implementation_plan_cli_writes_outputs(
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
            target.EXPECTED_DP_HEAD,
            "--label",
            "unit_cli",
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
    assert report["final_decision"]["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert "Implementation Plan" in markdown
    assert target.PRODUCTION_FILE in markdown
    assert target.NEW_PROFILE in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown
