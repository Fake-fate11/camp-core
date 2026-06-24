from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


MODULE = (
    "scripts.integrations."
    "plan_diffusion_planner_guarded_material_v3_remediation_implementation"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.STATIC_REVIEW_READY_STATUS}
passed=True
failed_checks=[]
authorized_next_work={target.STATIC_REVIEW_AUTHORIZED_NEXT_WORK}
implementation_plan_authorized=True
training_execution_authorized=False
dp_modification_authorized=False
"""


def _review_payload(
    *,
    status: str = target.STATIC_REVIEW_READY_STATUS,
    authorized_next_work: str = target.STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    implementation_plan_authorized: bool = True,
    blocked_action: bool = False,
    missing_contract: Optional[str] = None,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "static_contract_review_complete": True,
        "implementation_plan_authorized": implementation_plan_authorized,
    }
    for key in target.BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["training_execution_authorized"] = True
    contracts = [
        {"name": name, "passed": name != missing_contract}
        for name in target.REQUIRED_STATIC_CONTRACTS
    ]
    return {
        "final_decision": decision,
        "static_contract_review": {"required_contracts": contracts},
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: Optional[str] = None,
    payload: Optional[dict[str, object]] = None,
    markdown: str = "# Guarded Material v3 Remediation Design Static Contract Review\n",
) -> tuple[Path, Path]:
    root = tmp_path / "static_review"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / target.STATIC_REVIEW_JSON).write_text(
        json.dumps(payload or _review_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / target.STATIC_REVIEW_MD).write_text(markdown, encoding="utf-8")
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    return audit, root


def _build(
    tmp_path: Path,
    *,
    audit_text: Optional[str] = None,
    payload: Optional[dict[str, object]] = None,
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


def test_guarded_material_v4_implementation_plan_ready(tmp_path: Path) -> None:
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
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["new_default_off_profile"] == target.NEW_PROFILE
    assert plan["new_generator_policy"] == target.NEW_POLICY
    assert target.PRODUCTION_FILE in plan["allowed_files"]
    assert target.ROUTE_TEST_FILE in plan["allowed_files"]
    assert target.IMPLEMENTATION_TEST_FILE in plan["allowed_files"]
    assert "explicit_v4_profile_policy_pair" in slices
    assert "ready_diagnostic_candidate_materialization" in slices
    assert "row_generation_accounting_guard" in slices
    assert "red_stop_distance_window_fail_closed_partition" in slices
    assert "comfort_first_budget_preservation" in slices
    assert "descriptor_payload_report_only" in slices
    assert "v4_explicit_pair_required" in tests
    assert "ready_diagnostics_materialize_candidate_rows" in tests
    assert "generated_count_matches_candidate_rows" in tests
    assert "red_stop_distance_fail_closed_no_candidates" in tests
    assert "finite_current_tick_inputs_only" in tests
    assert "descriptor_legality_and_affine_contract" in tests


def test_guarded_material_v4_implementation_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_guarded_material_v4_implementation_plan_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_implementation_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_implementation_plan_rejects_wrong_review_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_review_payload(status="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_status_complete" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_implementation_plan_rejects_wrong_next(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_review_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_implementation_plan_rejects_unapproved_review(
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


def test_guarded_material_v4_implementation_plan_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_review_payload(
            missing_contract="affine_score_and_convex_master_preserved"
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "static_review_contract_affine_score_and_convex_master_preserved"
        in report["final_decision"]["failed_checks"]
    )


def test_guarded_material_v4_implementation_plan_rejects_blocked_action(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_review_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "static_review_no_blocked_authorizations" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_implementation_plan_cli_writes_outputs(
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
    assert report["final_decision"]["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert "Guarded Material v4 Materialization Implementation Plan" in markdown
    assert "score_k(w)=a_k^T w" in markdown


def test_guarded_material_v4_implementation_plan_file_entrypoint(
    tmp_path: Path,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "subprocess" / "implementation_plan.json"
    output_md = tmp_path / "subprocess" / "implementation_plan.md"
    script_path = Path(target.__file__).resolve()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
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
            "file_entrypoint_unit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == target.READY_STATUS
