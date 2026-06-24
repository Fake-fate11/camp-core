from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from scripts.integrations.analyze_diffusion_planner_guarded_material_v3_rerun_failure_attribution import (
    BLOCKED_ACTIONS,
    EXPECTED_CAMP_HEAD,
    EXPECTED_DP_HEAD,
    PLANNED_POLICY,
    REMEDIATION_PROFILE,
    SCREEN_REJECT_STATUS,
    build_report,
)
from scripts.integrations import (
    analyze_diffusion_planner_guarded_material_v3_rerun_failure_attribution as target,
)


def _row(index: int, *, ready: bool) -> dict[str, object]:
    if ready:
        if index == 0:
            feasible = 0
        elif index <= 10:
            feasible = 6
        elif index <= 14:
            feasible = 5
        else:
            feasible = 2
        diagnostics: dict[str, object] = {
            "construction_status": "ready",
            "fail_closed_partition": "material_standard_ready",
            "failure_reason": None,
            "hard_feasibility_precheck_passed": True,
            "comfort_first_precheck_passed": True,
            "candidate_count": 8,
            "feasible_stop_windows": feasible,
            "red_distance_m": 12.0 + index * 0.1,
            "current_speed_mps": 3.2 + index * 0.01,
            "current_tick_features_only": True,
            "diagnostic_descriptor_payload_v3_report_only": True,
            "generator_policy": PLANNED_POLICY,
            "material_support_profile_evidence": True,
        }
    else:
        diagnostics = {
            "construction_status": "fail_closed",
            "fail_closed_partition": "red_stop_distance_window",
            "failure_reason": "red_stop_distance_window",
            "hard_feasibility_precheck_passed": False,
            "comfort_first_precheck_passed": False,
            "candidate_count": 8,
            "feasible_stop_windows": 0,
            "red_distance_m": 0.8 + index * 0.01,
            "current_speed_mps": 2.8 + index * 0.01,
            "current_tick_features_only": True,
            "diagnostic_descriptor_payload_v3_report_only": True,
            "generator_policy": PLANNED_POLICY,
            "material_support_profile_evidence": True,
        }
    return {
        "snapshot_path": f"/snapshots/{index:03d}.json",
        "selection_step": index,
        "selected_index": 0,
        "selected_union_red": 22 + index % 20,
        "generated_count": 0,
        "candidate_rows": [],
        "candidate_construction_diagnostics": diagnostics,
        "timings_ms": {},
    }


def _payload(
    *,
    status: str = SCREEN_REJECT_STATUS,
    generated_rows: int = 0,
    lower_union_red_rows: int = 0,
    blocked_authorization: bool = False,
) -> dict[str, object]:
    rows = [_row(index, ready=index < 21) for index in range(57)]
    decision: dict[str, object] = {
        "status": status,
        "next_step": "inspect failure classes before designing a materially different generator",
        "source_authorization_conflicts": [],
    }
    for key in BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_authorization:
        decision["training_execution_authorized"] = True
    return {
        "analysis": {
            "candidate_generation_executed": True,
            "future_outcome_leakage": False,
            "closed_loop_replay": False,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
        },
        "config": {
            "generator_policy": PLANNED_POLICY,
            "default_off_remediation_profile": REMEDIATION_PROFILE,
            "red_stop_margins_m": [2.0, 4.0, 6.0],
            "backup_stop_offsets_m": [0.0, 1.0],
            "prefix_steps": [1],
            "bridge_steps": [0],
            "lane_projected_offset_scales": [0.0],
            "max_remediation_candidates": 12,
            "command_jerk_worse_budget_mps3": 0.0,
            "rollout_jerk_worse_budget_mps3": 0.0,
            "rollout_lateral_worse_budget_mps2": 0.0,
        },
        "records": {
            "snapshots": 57,
            "snapshots_with_generated_candidates": 0,
            "generated_candidate_rows": generated_rows,
            "lower_union_red_rows": lower_union_red_rows,
            "lower_union_red_hard_feasible_rows": 0,
            "lower_union_red_progress_feasible_rows": 0,
            "lower_union_red_comfort_admissible_rows": 0,
        },
        "support_gate": {
            "snapshots": 0,
            "min_snapshot_support_rate": 0.25,
            "hard_feasible_snapshot_support_rate": 0.0,
            "hard_feasible_snapshot_support_pass": False,
            "comfort_admissible_snapshot_support_rate": 0.0,
            "comfort_admissible_snapshot_support_pass": False,
        },
        "rows": rows,
        "final_decision": decision,
    }


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / target.SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_screen_root(
    tmp_path: Path,
    *,
    payload: Optional[dict[str, object]] = None,
    err_text: str = "",
    exit_code: str = "0\n",
) -> Path:
    root = tmp_path / "screen"
    root.mkdir()
    (root / target.SCREEN_JSON).write_text(
        json.dumps(payload or _payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / target.SCREEN_MD).write_text(
        "# Route/Topology Candidate Augmentation Screen\n\n## Verdict\n\nsupport insufficient\n",
        encoding="utf-8",
    )
    (root / target.CANDIDATE_LOG).write_text("screen completed\n", encoding="utf-8")
    (root / target.CANDIDATE_ERR).write_text(err_text, encoding="utf-8")
    (root / target.EXIT_CODE).write_text(exit_code, encoding="utf-8")
    (root / target.HEADS).write_text(
        "\n".join(
            [
                f"CAMP_HEAD={EXPECTED_CAMP_HEAD}",
                f"CAMP_ORIGIN_MAIN={EXPECTED_CAMP_HEAD}",
                f"DP_HEAD={EXPECTED_DP_HEAD}",
                "SNAPSHOT_COUNT=57",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (
            target.SCREEN_JSON,
            target.SCREEN_MD,
            target.CANDIDATE_LOG,
            target.CANDIDATE_ERR,
            target.EXIT_CODE,
            target.HEADS,
        ),
    )
    return root


def _build(
    tmp_path: Path,
    *,
    payload: Optional[dict[str, object]] = None,
    camp_head: str = EXPECTED_CAMP_HEAD,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict[str, object]:
    return build_report(
        screen_root=_write_screen_root(tmp_path, payload=payload),
        camp_head=camp_head,
        camp_origin_main=camp_head,
        dp_head=dp_head,
        label="unit",
    )


def test_guarded_material_v3_rerun_failure_attribution_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    attribution = report["read_only_attribution"]
    construction = report["construction_summary"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["failure_attribution_complete"] is True
    assert decision["remediation_design_plan_authorized"] is True
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert attribution["primary_attribution"] == (
        "zero_lower_union_red_support_after_v3_candidate_construction"
    )
    assert attribution["secondary_attribution"] == "red_stop_distance_window_fail_closed"
    assert attribution["diagnostic_windows_present_without_candidate_rows"] is True
    assert attribution["training_ready"] is False
    assert construction["construction_status_counts"] == {"fail_closed": 36, "ready": 21}
    assert construction["failure_reason_counts"] == {
        "null": 21,
        "red_stop_distance_window": 36,
    }
    assert construction["candidate_count_sum"] == 456
    assert construction["feasible_stop_windows_sum"] == 92


def test_guarded_material_v3_rerun_failure_attribution_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_guarded_material_v3_rerun_failure_attribution_rejects_camp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, camp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "camp_head_matches_expected" in report["final_decision"]["failed_checks"]


def test_guarded_material_v3_rerun_failure_attribution_rejects_blocked_authorization(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_payload(blocked_authorization=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_no_blocked_authorizations" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_rerun_failure_attribution_rejects_positive_status(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_payload(status="support_ready"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_status_is_support_insufficient" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_rerun_failure_attribution_rejects_generated_rows(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_payload(generated_rows=1, lower_union_red_rows=1))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_generated_candidate_rows_zero" in report["final_decision"][
        "failed_checks"
    ]
    assert "screen_lower_union_red_rows_zero" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v3_rerun_failure_attribution_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = _write_screen_root(tmp_path)
    output_json = tmp_path / "out" / "failure_attribution.json"
    output_md = tmp_path / "out" / "failure_attribution.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "attr",
            "--screen_root",
            str(root),
            "--camp_head",
            EXPECTED_CAMP_HEAD,
            "--camp_origin_main",
            EXPECTED_CAMP_HEAD,
            "--dp_head",
            EXPECTED_DP_HEAD,
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
    assert "Guarded Material v3 Screen Rerun Failure Attribution" in markdown
    assert "CAMP retraining" in markdown
    assert "score_k(w)=a_k^T w" in markdown


def test_guarded_material_v3_rerun_failure_attribution_file_entrypoint(
    tmp_path: Path,
) -> None:
    root = _write_screen_root(tmp_path)
    output_json = tmp_path / "subprocess" / "failure_attribution.json"
    output_md = tmp_path / "subprocess" / "failure_attribution.md"
    script_path = Path(target.__file__).resolve()

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--screen_root",
            str(root),
            "--camp_head",
            EXPECTED_CAMP_HEAD,
            "--camp_origin_main",
            EXPECTED_CAMP_HEAD,
            "--dp_head",
            EXPECTED_DP_HEAD,
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
