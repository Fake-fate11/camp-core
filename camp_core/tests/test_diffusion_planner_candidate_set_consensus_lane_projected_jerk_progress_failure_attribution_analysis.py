from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    AUTHORIZED_NEXT_WORK,
    PLAN_JSON,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    ABSOLUTE_JSON,
    ABSOLUTE_READY_STATUS,
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    EXIT_CODE,
    HEADS,
    READY_STATUS as PLAN_READY_STATUS,
    SCREEN_JSON,
    SCREEN_REJECT_STATUS,
    SHA256SUMS,
)


def _screen_payload(status: str = SCREEN_REJECT_STATUS) -> dict:
    return {
        "final_decision": {"status": status},
        "records": {
            "snapshots": 57,
            "snapshots_with_generated_candidates": 21,
            "generated_candidate_rows": 276,
            "lower_union_red_rows": 276,
            "lower_union_red_hard_feasible_rows": 67,
            "lower_union_red_progress_feasible_rows": 64,
            "lower_union_red_comfort_admissible_rows": 0,
        },
        "support_gate": {
            "hard_feasible_snapshot_support_rate": 0.38095238095238093,
            "comfort_admissible_snapshot_support_rate": 0.0,
        },
        "latency_ms": {
            "candidate_build": {
                "count": 57,
                "mean": 9.96,
                "max": 39.97,
                "p95": 35.61,
            },
            "total": {
                "count": 57,
                "mean": 62.98,
                "max": 1011.78,
                "p95": 102.54,
            },
            "generated_reward": {
                "count": 57,
                "mean": 11.39,
                "max": 39.54,
                "p95": 37.14,
            },
        },
        "failure_class_counts": {
            "route_topology_comfort_blocked_command_jerk": 64,
            "route_topology_comfort_blocked_rollout_lateral": 63,
            "route_topology_comfort_blocked_command_lateral": 60,
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


def _absolute_payload(status: str = ABSOLUTE_READY_STATUS) -> dict:
    return {
        "final_decision": {"status": status},
        "records": {
            "absolute_lateral_guard_rows": 28,
            "lower_union_red_hard_progress_rows": 64,
        },
        "support_gate": {
            "absolute_lateral_guard_snapshot_support_rate": 0.3333333333333333,
        },
        "failure_class_counts": {
            "absolute_lateral_guard_support": 28,
            "absolute_command_lateral_guard_failed": 36,
        },
    }


def _plan_payload(
    *,
    status: str = PLAN_READY_STATUS,
    authorized_next_work: str | None = PLAN_AUTHORIZED_NEXT_WORK,
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": authorized_next_work,
            "read_only_failure_attribution_authorized": True,
            "candidate_generation_execution_authorized": False,
            "fixed_snapshot_screen_rerun_authorized": False,
            "new_replay_authorized": False,
            "formal_seeds_authorized": False,
            "dp_modification_authorized": False,
        }
    }


def _write_sha256sums(root: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        data = (root / name).read_bytes()
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_root(
    root: Path,
    payloads: dict[str, dict],
    *,
    heads_text: str = "HEADS\n",
) -> None:
    root.mkdir(parents=True)
    names = []
    for name, payload in payloads.items():
        (root / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        names.append(name)
    (root / EXIT_CODE).write_text("0\n", encoding="utf-8")
    (root / HEADS).write_text(heads_text, encoding="utf-8")
    names.extend([EXIT_CODE, HEADS])
    _write_sha256sums(root, names)


def _write_artifacts(
    tmp_path: Path,
    *,
    screen: dict | None = None,
    absolute: dict | None = None,
    plan: dict | None = None,
) -> tuple[Path, Path]:
    screen_root = tmp_path / "screen"
    plan_root = tmp_path / "plan"
    _write_root(
        screen_root,
        {
            SCREEN_JSON: screen or _screen_payload(),
            ABSOLUTE_JSON: absolute or _absolute_payload(),
        },
    )
    _write_root(plan_root, {PLAN_JSON: plan or _plan_payload()})
    return screen_root, plan_root


def _build(tmp_path: Path, **kwargs: object) -> dict:
    screen_root, plan_root = _write_artifacts(tmp_path, **kwargs)
    return build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_read_only_analysis_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    attribution = report["read_only_attribution"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert attribution["primary_blocker_family"] == "relative_comfort_support"
    assert attribution["primary_comfort_blocker"] == (
        "route_topology_comfort_blocked_command_jerk"
    )
    assert attribution["primary_hard_blocker"] == "dp_kinematic"
    assert attribution["absolute_lateral_guard_retained"] is True


def test_read_only_analysis_rejects_plan_sha_mismatch(tmp_path: Path) -> None:
    screen_root, plan_root = _write_artifacts(tmp_path)
    (plan_root / PLAN_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_read_only_analysis_rejects_plan_not_authorized(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        plan=_plan_payload(authorized_next_work="candidate_generation_not_allowed"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_authorizes_read_only_analysis" in report["final_decision"][
        "failed_checks"
    ]


def test_read_only_analysis_rejects_dp_mismatch(tmp_path: Path) -> None:
    screen_root, plan_root = _write_artifacts(tmp_path)
    report = build_report(
        screen_root=screen_root,
        plan_root=plan_root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_read_only_analysis_rejects_screen_not_rejected(tmp_path: Path) -> None:
    report = _build(tmp_path, screen=_screen_payload(status="unexpected"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_status_rejected" in report["final_decision"]["failed_checks"]


def test_read_only_analysis_rejects_missing_latency_failure(tmp_path: Path) -> None:
    screen = _screen_payload()
    screen["latency_ms"]["candidate_build"]["p95"] = 5.0
    screen["latency_ms"]["total"]["p95"] = 80.0
    report = _build(tmp_path, screen=screen)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latency_failure_present" in report["final_decision"]["failed_checks"]


def test_read_only_analysis_markdown_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Read-Only Analysis" in markdown
    assert "Comfort Blocker Ranking" in markdown
    assert "Hard Blocker Ranking" in markdown
    assert "Latency Ranking" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_read_only_analysis_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    screen_root, plan_root = _write_artifacts(tmp_path)
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
        "# Lane-Projected Jerk/Progress Failure Attribution Read-Only Analysis"
    )
