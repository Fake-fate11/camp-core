from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


MODULE = (
    "scripts.integrations."
    "plan_diffusion_planner_guarded_material_v3_failure_attribution_remediation_design"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={target.FAILURE_ATTRIBUTION_READY_STATUS}
passed=True
failed_checks=[]
authorized_next_work={target.FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK}
primary_attribution={target.PRIMARY_ATTRIBUTION}
zero_support_evidence=True
training_ready=False
formal seeds 11/12/13 remain frozen
"""


def _attribution_payload(
    *,
    status: str = target.FAILURE_ATTRIBUTION_READY_STATUS,
    authorized_next_work: str = target.FAILURE_ATTRIBUTION_AUTHORIZED_NEXT_WORK,
    primary: str = target.PRIMARY_ATTRIBUTION,
    secondary: str = target.SECONDARY_ATTRIBUTION,
    blocked_action: bool = False,
    positive_support: bool = False,
    training_ready: bool = False,
    replay_ready: bool = False,
    zero_support: bool = True,
    diagnostic_windows: bool = True,
    ready_rows: int = 21,
    red_failures: int = 36,
    candidate_count_sum: int = 456,
    candidate_rows_sum: int = 0,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": authorized_next_work,
        "failure_attribution_complete": True,
        "remediation_design_plan_authorized": True,
        "positive_support_evidence": positive_support,
        "training_ready": training_ready,
        "replay_evidence_ready": replay_ready,
    }
    for key in target.BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["training_execution_authorized"] = True
    return {
        "final_decision": decision,
        "read_only_attribution": {
            "primary_attribution": primary,
            "secondary_attribution": secondary,
            "zero_support_evidence": zero_support,
            "diagnostic_windows_present_without_candidate_rows": diagnostic_windows,
            "ready_rows": ready_rows,
            "red_stop_distance_window_failures": red_failures,
        },
        "construction_summary": {
            "candidate_count_sum": candidate_count_sum,
            "feasible_stop_windows_sum": 92,
            "row_generated_count_sum": 0,
            "candidate_rows_sum": candidate_rows_sum,
        },
        "source_summary": {
            "generated_candidate_rows": 0,
            "lower_union_red_rows": 0,
            "hard_support_rate": 0.0,
            "comfort_support_rate": 0.0,
        },
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: Optional[str] = None,
    payload: Optional[dict[str, object]] = None,
    markdown: str = "# Guarded Material v3 Screen Rerun Failure Attribution\n",
) -> tuple[Path, Path]:
    root = tmp_path / "failure_attribution"
    audit = tmp_path / "audit.md"
    root.mkdir()
    (root / target.FAILURE_ATTRIBUTION_JSON).write_text(
        json.dumps(payload or _attribution_payload(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    (root / target.FAILURE_ATTRIBUTION_MD).write_text(markdown, encoding="utf-8")
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
        failure_attribution_root=root,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_guarded_material_v3_remediation_design_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["remediation_design_plan"]
    tracks = {item["name"] for item in plan["remediation_tracks"]}
    descriptors = {item["name"] for item in plan["descriptor_atom_contract"]}
    rejected = {item["name"] for item in plan["rejected_non_fixes"]}

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["remediation_design_plan_ready"] is True
    assert decision["static_contract_review_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["target_failure"]["primary_attribution"] == target.PRIMARY_ATTRIBUTION
    assert plan["target_failure"]["candidate_count_sum"] == 456
    assert plan["target_failure"]["candidate_rows_sum"] == 0
    assert "ready_diagnostic_candidate_materialization" in tracks
    assert "row_generation_accounting_guard" in tracks
    assert "red_stop_distance_window_fail_closed_partition" in tracks
    assert "comfort_first_budget_preservation" in tracks
    assert "positive_support_before_execution_gate" in tracks
    assert "stop_window_margin_hinges_v4" in descriptors
    assert "lane_progress_comfort_signed_splits_v4" in descriptors
    assert "candidate_accounting_gap_report_only_v4" in descriptors
    assert "affine_convex_master_preservation" in descriptors
    assert "train_on_zero_support" in rejected
    assert "rerun_v3_as_is" in rejected
    assert "gate_relaxation" in rejected
    assert "formal_seed_probe" in rejected
    assert "dp_side_change" in rejected


def test_guarded_material_v3_remediation_design_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_guarded_material_v3_remediation_design_rejects_missing_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_this_design_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_remediation_design_rejects_wrong_next_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(authorized_next_work="bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_authorizes_this_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_remediation_design_rejects_wrong_primary(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(primary="wrong"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_primary_zero_candidate" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_remediation_design_rejects_positive_support(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(positive_support=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_no_positive_support" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_remediation_design_rejects_training_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(training_ready=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_training_not_ready" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_remediation_design_rejects_missing_diagnostic_windows(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_attribution_payload(diagnostic_windows=False),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_diagnostic_windows_present" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_remediation_design_rejects_nonzero_candidate_rows(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_attribution_payload(candidate_rows_sum=1))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "failure_attribution_candidate_rows_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_remediation_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "design_plan.json"
    output_md = tmp_path / "out" / "design_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
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
    assert report["final_decision"]["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert "Zero Candidate Support Remediation Design Plan" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "formal seeds" in markdown


def test_guarded_material_v3_remediation_design_file_entrypoint(
    tmp_path: Path,
) -> None:
    audit, root = _write_inputs(tmp_path)
    output_json = tmp_path / "subprocess" / "design_plan.json"
    output_md = tmp_path / "subprocess" / "design_plan.md"
    script_path = Path(target.__file__).resolve()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
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
