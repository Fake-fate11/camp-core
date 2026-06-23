from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (
    ABSOLUTE_JSON,
    ABSOLUTE_MD,
    ABSOLUTE_READY_STATUS,
    AUTHORIZED_NEXT_WORK,
    DEFAULT_SCREEN_ROOT,
    READY_STATUS,
    REJECT_STATUS,
    SCREEN_JSON,
    SCREEN_MD,
    SCREEN_REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _screen_payload(
    *,
    status: str = SCREEN_REJECT_STATUS,
    comfort_pass: bool = False,
    missing_comfort_blocker: bool = False,
    latency_pass: bool = False,
    blocked_action: bool = False,
) -> dict[str, object]:
    failure_classes = {
        "route_topology_comfort_blocked_command_jerk": 64,
        "route_topology_comfort_blocked_command_lateral": 60,
        "route_topology_comfort_blocked_progress_loss": 58,
        "route_topology_comfort_blocked_rollout_jerk": 60,
        "route_topology_comfort_blocked_rollout_lateral": 63,
        "route_topology_dp_kinematic": 197,
        "route_topology_dp_road_border": 108,
        "route_topology_lane_invalid": 114,
        "route_topology_red_timing_invalid": 51,
    }
    if missing_comfort_blocker:
        failure_classes.pop("route_topology_comfort_blocked_progress_loss")
    candidate_build_p95 = 5.0 if latency_pass else 36.27
    total_p95 = 80.0 if latency_pass else 106.16
    decision = {
        "status": status,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
        "candidate_generation_execution_authorized": False,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "atom_promotion_authorized": blocked_action,
    }
    return {
        "final_decision": decision,
        "records": {
            "snapshots": 57,
            "snapshots_with_generated_candidates": 21,
            "generated_candidate_rows": 276,
            "lower_union_red_hard_feasible_rows": 67,
            "lower_union_red_progress_feasible_rows": 64,
            "lower_union_red_comfort_admissible_rows": 0,
        },
        "support_gate": {
            "hard_feasible_snapshot_support_pass": True,
            "hard_feasible_snapshot_support_rate": 0.38095238095238093,
            "comfort_admissible_snapshot_support_pass": comfort_pass,
            "comfort_admissible_snapshot_support_rate": 0.0,
            "min_snapshot_support_rate": 0.25,
        },
        "latency_ms": {
            "candidate_build": {"p95": candidate_build_p95},
            "total": {"p95": total_p95},
        },
        "failure_class_counts": failure_classes,
        "hard_reason_counts": {
            "dp_kinematic": 197,
            "dp_red_light": 51,
            "dp_road_border": 108,
        },
        "progress_comfort_delta": {
            "command_jerk_worse_mps3": {"p95": 749.58},
            "progress_loss_m": {"p95": 8.37},
        },
    }


def _absolute_payload(
    *,
    status: str = ABSOLUTE_READY_STATUS,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision = {
        "status": status,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
        "candidate_generation_execution_authorized": False,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "atom_promotion_authorized": blocked_action,
    }
    return {
        "final_decision": decision,
        "records": {
            "absolute_lateral_guard_rows": 28,
            "lower_union_red_hard_progress_rows": 64,
        },
        "support_gate": {
            "absolute_lateral_guard_snapshot_support_pass": True,
            "absolute_lateral_guard_snapshot_support_rate": 0.3333333333333333,
            "min_snapshot_support_rate": 0.25,
        },
        "failure_class_counts": {
            "absolute_lateral_guard_support": 28,
            "absolute_command_lateral_guard_failed": 105,
        },
    }


def _write_source_root(
    tmp_path: Path,
    *,
    screen: dict[str, object] | None = None,
    absolute: dict[str, object] | None = None,
    exit_code: str = "0",
    runbook_exit: str = "0",
    include_runbook_exit: bool = True,
) -> Path:
    root = tmp_path / "screen"
    root.mkdir()
    (root / SCREEN_JSON).write_text(
        json.dumps(screen or _screen_payload()),
        encoding="utf-8",
    )
    (root / SCREEN_MD).write_text("# screen\n", encoding="utf-8")
    (root / ABSOLUTE_JSON).write_text(
        json.dumps(absolute or _absolute_payload()),
        encoding="utf-8",
    )
    (root / ABSOLUTE_MD).write_text("# absolute\n", encoding="utf-8")
    files = {
        "CANDIDATE_SCREEN.log": "screen\n",
        "CANDIDATE_SCREEN.err": "",
        "ABSOLUTE_GUARD.log": "absolute\n",
        "ABSOLUTE_GUARD.err": "",
        "EXIT_CODE": f"{exit_code}\n",
        "HEADS.txt": f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
    }
    if include_runbook_exit:
        files["RUNBOOK_EXIT"] = f"{runbook_exit}\n"
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    _write_sha256sums(
        root,
        (
            SCREEN_JSON,
            SCREEN_MD,
            ABSOLUTE_JSON,
            ABSOLUTE_MD,
            *files,
        ),
    )
    return root


def _build(tmp_path: Path, **source_kwargs) -> dict:
    return build_report(
        screen_root=_write_source_root(tmp_path, **source_kwargs),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_default_off_rerun_failure_attribution_default_source_is_current_rerun() -> None:
    assert DEFAULT_SCREEN_ROOT.endswith(
        "candidate_set_consensus_lane_projected_"
        "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_24c7760"
    )


def test_default_off_rerun_failure_attribution_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["failure_attribution_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["read_only_failure_attribution_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["safety_benefit_evidence"] is False
    assert plan["selection_type"] == "read_only_failure_attribution_plan_only"
    assert report["screen_summary"]["comfort_rows"] == 0
    assert report["absolute_summary"]["absolute_rows"] == 28


def test_default_off_rerun_failure_attribution_accepts_exit_code_only_artifact(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, include_runbook_exit=False)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["failed_checks"] == []
    assert report["screen_artifact"]["optional_files_present"]["RUNBOOK_EXIT"] is False


def test_default_off_rerun_failure_attribution_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    source = _write_source_root(tmp_path)
    (source / SCREEN_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        screen_root=source,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_failure_attribution_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        screen_root=_write_source_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_failure_attribution_rejects_screen_not_rejected(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        screen=_screen_payload(status="route_topology_candidate_support_present"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_status_rejected" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_failure_attribution_rejects_missing_comfort_blockers(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        screen=_screen_payload(missing_comfort_blocker=True),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "evidence_comfort_blockers_present" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_rerun_failure_attribution_rejects_latency_not_failed(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, screen=_screen_payload(latency_pass=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "evidence_latency_gates_failed" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_rerun_failure_attribution_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, screen=_screen_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_failure_attribution_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Failure Attribution Plan" in markdown
    assert "read-only failure attribution" in markdown
    assert "comfort blocker" in markdown
    assert "hard blocker" in markdown
    assert "latency" in markdown
    assert "absolute lateral guard" in markdown
    assert "overlap" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "screen rerun is not authorized" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_default_off_rerun_failure_attribution_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_source_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--screen_root",
            str(source),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
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
    assert report["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Default-Off Remediation Fixed-Snapshot Rerun"
    )
