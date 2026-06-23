from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (
    AUTHORIZED_NEXT_WORK,
    PLAN_JSON,
    PLAN_JSON_COMPAT,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (
    ABSOLUTE_ERR,
    ABSOLUTE_JSON,
    ABSOLUTE_READY_STATUS,
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    CANDIDATE_ERR,
    EXIT_CODE,
    HEADS,
    READY_STATUS as PLAN_READY_STATUS,
    RUNBOOK_EXIT,
    SCREEN_JSON,
    SCREEN_REJECT_STATUS,
    SHA256SUMS,
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _screen_payload(
    *,
    status: str = SCREEN_REJECT_STATUS,
    comfort_pass: bool = False,
    latency_pass: bool = False,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision = {
        "status": status,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
        "new_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "atom_promotion_authorized": blocked_action,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_evidence": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    candidate_build_p95 = 5.0 if latency_pass else 36.27
    total_p95 = 80.0 if latency_pass else 106.16
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
            "candidate_build": {
                "count": 57,
                "mean": 9.96,
                "max": 39.97,
                "p95": candidate_build_p95,
            },
            "total": {
                "count": 57,
                "mean": 62.98,
                "max": 1011.78,
                "p95": total_p95,
            },
            "baseline_reward": {
                "count": 57,
                "mean": 10.0,
                "max": 40.0,
                "p95": 31.0,
            },
        },
        "failure_class_counts": {
            "route_topology_comfort_blocked_command_jerk": 64,
            "route_topology_comfort_blocked_rollout_lateral": 63,
            "route_topology_comfort_blocked_command_lateral": 60,
            "route_topology_comfort_blocked_rollout_jerk": 60,
            "route_topology_comfort_blocked_progress_loss": 58,
            "route_topology_dp_kinematic": 197,
        },
        "hard_reason_counts": {
            "dp_kinematic": 197,
            "dp_road_border": 108,
            "dp_red_light": 51,
        },
        "by_snapshot": [
            {
                "selection_step": 128,
                "candidate_rows": 18,
                "lower_union_red_hard_feasible": 18,
                "lower_union_red_progress_feasible": 18,
                "lower_union_red_comfort_admissible": 0,
                "failure_class_counts": {
                    "route_topology_comfort_blocked_command_jerk": 18,
                    "route_topology_comfort_blocked_rollout_lateral": 18,
                },
            }
        ],
    }


def _absolute_payload(
    *,
    status: str = ABSOLUTE_READY_STATUS,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision = {
        "status": status,
        "candidate_generation_execution_authorized": False,
        "fixed_snapshot_screen_rerun_authorized": False,
        "fixed_snapshot_screen_rerun_execution_authorized": False,
        "new_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "atom_promotion_authorized": blocked_action,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_evidence": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    return {
        "final_decision": decision,
        "records": {
            "candidate_rows": 276,
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
            "absolute_command_lateral_guard_failed": 36,
            "hard_dp_kinematic": 197,
        },
    }


def _plan_payload(
    *,
    status: str = PLAN_READY_STATUS,
    authorized_next_work: str | None = PLAN_AUTHORIZED_NEXT_WORK,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": authorized_next_work,
            "read_only_failure_attribution_authorized": True,
            "candidate_generation_execution_authorized": False,
            "fixed_snapshot_screen_rerun_authorized": False,
            "new_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "atom_promotion_authorized": blocked_action,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "safety_benefit_evidence": False,
            "camp_over_dp_top1_claim_authorized": False,
            "classic_benders_claim_authorized": False,
        }
    }


def _write_screen_root(
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
        json.dumps(screen or _screen_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / ABSOLUTE_JSON).write_text(
        json.dumps(absolute or _absolute_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / CANDIDATE_ERR).write_text("", encoding="utf-8")
    (root / ABSOLUTE_ERR).write_text("", encoding="utf-8")
    (root / EXIT_CODE).write_text(f"{exit_code}\n", encoding="utf-8")
    if include_runbook_exit:
        (root / RUNBOOK_EXIT).write_text(f"{runbook_exit}\n", encoding="utf-8")
    (root / HEADS).write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    sha_files = [
        SCREEN_JSON,
        ABSOLUTE_JSON,
        CANDIDATE_ERR,
        ABSOLUTE_ERR,
        EXIT_CODE,
        HEADS,
    ]
    if include_runbook_exit:
        sha_files.append(RUNBOOK_EXIT)
    _write_sha256sums(root, tuple(sha_files))
    return root


def _write_plan_root(
    tmp_path: Path,
    *,
    plan: dict[str, object] | None = None,
    plan_json_name: str = PLAN_JSON,
) -> Path:
    root = tmp_path / "plan"
    root.mkdir()
    (root / plan_json_name).write_text(
        json.dumps(plan or _plan_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / EXIT_CODE).write_text(
        "PY_COMPILE_EXIT=0\n"
        "PYTEST_PLAN_EXIT=0\n"
        "PYTEST_RELATED_EXIT=0\n"
        "PLAN_EXIT=0\n",
        encoding="utf-8",
    )
    (root / HEADS).write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(root, (plan_json_name, EXIT_CODE, HEADS))
    return root


def _build(tmp_path: Path, **kwargs: object) -> dict[str, object]:
    screen_root = _write_screen_root(
        tmp_path,
        screen=kwargs.get("screen"),  # type: ignore[arg-type]
        absolute=kwargs.get("absolute"),  # type: ignore[arg-type]
    )
    plan_root = _write_plan_root(
        tmp_path,
        plan=kwargs.get("plan"),  # type: ignore[arg-type]
    )
    return build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_default_off_rerun_read_only_analysis_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    attribution = report["read_only_attribution"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["safety_benefit_evidence"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert attribution["primary_blocker_family"] == "comfort_support_deficit"
    assert attribution["primary_comfort_blocker"] == (
        "route_topology_comfort_blocked_command_jerk"
    )
    assert attribution["primary_hard_blocker"] == "dp_kinematic"
    assert attribution["primary_latency_source"] == "total"
    assert attribution["absolute_lateral_guard_retained"] is True
    assert attribution["recommendation_category"] == "design-new-policy-plan-only"


def test_default_off_rerun_read_only_analysis_accepts_exit_code_only_screen(
    tmp_path: Path,
) -> None:
    screen_root = _write_screen_root(tmp_path, include_runbook_exit=False)
    plan_root = _write_plan_root(tmp_path)

    report = build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["failed_checks"] == []
    assert report["screen_artifact"]["runbook_exit"] is None


def test_default_off_rerun_read_only_analysis_accepts_current_plan_filename(
    tmp_path: Path,
) -> None:
    screen_root = _write_screen_root(tmp_path, include_runbook_exit=False)
    plan_root = _write_plan_root(tmp_path, plan_json_name=PLAN_JSON_COMPAT)

    report = build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["plan_artifact"]["required_files"][PLAN_JSON_COMPAT] is True


def test_default_off_rerun_read_only_analysis_rejects_plan_sha_mismatch(
    tmp_path: Path,
) -> None:
    screen_root = _write_screen_root(tmp_path)
    plan_root = _write_plan_root(tmp_path)
    (plan_root / PLAN_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_read_only_analysis_rejects_plan_not_authorized(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        plan=_plan_payload(authorized_next_work="candidate_generation_not_allowed"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_authorizes_read_only_analysis" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_rerun_read_only_analysis_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    screen_root = _write_screen_root(tmp_path)
    plan_root = _write_plan_root(tmp_path)

    report = build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_read_only_analysis_rejects_screen_not_rejected(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        screen=_screen_payload(status="route_topology_candidate_support_present"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_status_rejected" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_read_only_analysis_rejects_missing_latency_failure(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, screen=_screen_payload(latency_pass=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latency_gate_failure_present" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_read_only_analysis_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, plan=_plan_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_blocked_actions_clear" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_read_only_analysis_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Read-Only Analysis" in markdown
    assert "Comfort Blocker Ranking" in markdown
    assert "Hard Blocker Ranking" in markdown
    assert "Absolute Guard Failure Ranking" in markdown
    assert "Latency Ranking" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown


def test_default_off_rerun_read_only_analysis_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen_root = _write_screen_root(tmp_path)
    plan_root = _write_plan_root(tmp_path)
    output_json = tmp_path / "out" / "analysis.json"
    output_md = tmp_path / "out" / "analysis.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "analysis",
            "--screen_root",
            str(screen_root),
            "--plan_root",
            str(plan_root),
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
        "# Default-Off Fixed-Snapshot Rerun Failure Attribution Read-Only Analysis"
    )
