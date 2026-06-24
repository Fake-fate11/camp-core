from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


MODULE = (
    "scripts.integrations."
    "review_diffusion_planner_guarded_material_v3_remediation_design_static_contract"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.PLAN_READY_STATUS}
passed=True
failed_checks=[]
authorized_next_work={target.PLAN_AUTHORIZED_NEXT_WORK}
"""


def _design_payload(
    *,
    status: str = target.PLAN_READY_STATUS,
    authorized_next_work: str = target.PLAN_AUTHORIZED_NEXT_WORK,
    blocked_action: bool = False,
    missing_track: Optional[str] = None,
    descriptor_override: Optional[dict[str, str]] = None,
    future_exit_criteria: Optional[list[str]] = None,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "remediation_design_plan_ready": True,
        "static_contract_review_authorized": True,
    }
    for key in target.BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["implementation_code_edit_authorized"] = True

    tracks = [
        {"name": name, "purpose": "p", "evidence_driver": "e", "contract": "c"}
        for name in target.REQUIRED_TRACKS
        if name != missing_track
    ]
    descriptor_contracts = {
        "finite_candidate_materialization_flag_v4": (
            "binary current-tick diagnostic; nonnegative and affine"
        ),
        "stop_window_margin_hinges_v4": (
            "nonnegative hinge channels from current red distance"
        ),
        "lane_progress_comfort_signed_splits_v4": (
            "signed values split into nonnegative parts"
        ),
        "candidate_accounting_gap_report_only_v4": (
            "report-only and cannot alter candidates or selected index"
        ),
        "affine_convex_master_preservation": (
            "all scores remain score_k(w)=a_k^T w and master remains convex"
        ),
    }
    if descriptor_override:
        descriptor_contracts.update(descriptor_override)
    descriptors = [
        {"name": name, "contract": contract}
        for name, contract in descriptor_contracts.items()
    ]
    return {
        "analysis": {
            "plan_only": True,
            "implementation_code_edit": False,
            "production_implementation_edit": False,
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "safety_benefit_claim": False,
            "math_boundary": "score_k(w)=a_k^T w and convex simplex/CVaR/L2",
        },
        "final_decision": decision,
        "remediation_design_plan": {
            "target_failure": {
                "primary_attribution": "zero_lower_union_red_support_after_v3_candidate_construction",
                "candidate_rows_sum": 0,
            },
            "remediation_tracks": tracks,
            "descriptor_atom_contract": descriptors,
            "rejected_non_fixes": [
                {"name": name, "reason": "r"}
                for name in target.REQUIRED_REJECTED_NON_FIXES
            ],
            "future_exit_criteria": (
                future_exit_criteria
                if future_exit_criteria is not None
                else list(target.REQUIRED_FUTURE_EXIT_CRITERIA)
            ),
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: Optional[str] = None,
    payload: Optional[dict[str, object]] = None,
    markdown: str = "# Guarded Material v3 Zero Candidate Support Remediation Design Plan\n",
) -> tuple[Path, Path]:
    root = tmp_path / "plan"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / target.PLAN_JSON).write_text(
        json.dumps(payload or _design_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / target.PLAN_MD).write_text(markdown, encoding="utf-8")
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
        plan_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_guarded_material_v3_static_contract_review_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_complete"] is True
    assert decision["implementation_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert all(item["passed"] for item in review["required_contracts"])


def test_guarded_material_v3_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_guarded_material_v3_static_contract_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_static_contract_review" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_static_contract_rejects_wrong_next_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_design_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "plan_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_guarded_material_v3_static_contract_rejects_blocked_authorization(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_design_payload(blocked_action=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "plan_no_blocked_authorizations" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_static_contract_rejects_missing_track(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(missing_track="row_generation_accounting_guard"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "plan_track_row_generation_accounting_guard" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_static_contract_rejects_bad_hinge_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(
            descriptor_override={"stop_window_margin_hinges_v4": "raw margin"}
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "review_contract_nonnegative_stop_window_hinges"
        in report["final_decision"]["failed_checks"]
    )


def test_guarded_material_v3_static_contract_rejects_bad_affine_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(
            descriptor_override={"affine_convex_master_preservation": "nonlinear"}
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "review_contract_affine_score_and_convex_master_preserved"
        in report["final_decision"]["failed_checks"]
    )


def test_guarded_material_v3_static_contract_rejects_missing_exit_criterion(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_design_payload(future_exit_criteria=[]))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "review_contract_future_execution_requires_positive_materialization_tests"
        in report["final_decision"]["failed_checks"]
    )


def test_guarded_material_v3_static_contract_cli_writes_outputs(
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
    assert report["final_decision"]["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert "Static Contract Review" in markdown
    assert "score_k(w)=a_k^T w" in markdown


def test_guarded_material_v3_static_contract_file_entrypoint(
    tmp_path: Path,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "subprocess" / "static_contract_review.json"
    output_md = tmp_path / "subprocess" / "static_contract_review.md"
    script_path = Path(target.__file__).resolve()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
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
