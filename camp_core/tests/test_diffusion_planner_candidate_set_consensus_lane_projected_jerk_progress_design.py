from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_design import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_AUTHORIZED_NEXT_WORK,
    SOURCE_JSON,
    SOURCE_MD,
    SOURCE_READY_STATUS,
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


def _source_payload(
    *,
    status: str = SOURCE_READY_STATUS,
    passed: bool = True,
    blocked_action: bool = False,
    lane_status: str = "route_topology_absolute_lateral_guard_support_present",
    prefix_lane_status: str = "route_topology_absolute_lateral_guard_support_present",
) -> dict[str, object]:
    decision = {
        "status": status,
        "passed": passed,
        "authorized_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "route_topology_comfort_support_preflight_ready": passed,
        "lane_projected_jerk_progress_support_design_plan_authorized": passed,
        "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "failed_checks": [],
    }
    for key in BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["atom_promotion_authorized"] = True

    return {
        "final_decision": decision,
        "preflight_plan": {
            "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
            "evidence_contract": {
                "lane_projected_absolute_lateral_guard": lane_status,
                "prefix_lane_projected_absolute_lateral_guard": prefix_lane_status,
            },
        },
    }


def _write_source_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "route_topology_preflight"
    root.mkdir()
    (root / SOURCE_JSON).write_text(
        json.dumps(payload or _source_payload()),
        encoding="utf-8",
    )
    (root / SOURCE_MD).write_text("# route topology preflight\n", encoding="utf-8")
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (
            SOURCE_JSON,
            SOURCE_MD,
            "COMMAND.log",
            "COMMAND.err",
            "EXIT_CODE",
            "HEADS.txt",
        ),
    )
    return root


def test_lane_projected_jerk_progress_design_plan_ready(tmp_path: Path) -> None:
    report = build_report(
        preflight_root=_write_source_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]
    plan = report["design_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_unit_tests_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["closed_loop_replay_authorized"] is False
    assert plan["selection_type"] == "implementation_unit_tests_only"
    assert plan["proposed_policy_name"] == "lane_projected_jerk_progress_red_stop"
    assert report["analysis"]["plan_only"] is True
    assert report["analysis"]["diffusion_planner_execution"] is False


def test_lane_projected_jerk_progress_rejects_source_sha_mismatch(tmp_path: Path) -> None:
    source = _write_source_root(tmp_path)
    (source / SOURCE_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        preflight_root=source,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "preflight_sha256sums_ok" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_lane_projected_jerk_progress_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = build_report(
        preflight_root=_write_source_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_lane_projected_jerk_progress_rejects_source_not_ready(tmp_path: Path) -> None:
    report = build_report(
        preflight_root=_write_source_root(
            tmp_path,
            payload=_source_payload(
                status="candidate_set_consensus_route_topology_preflight_rejected",
                passed=False,
            ),
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_preflight_ready" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_lane_projected_jerk_progress_rejects_source_blocked_action(
    tmp_path: Path,
) -> None:
    report = build_report(
        preflight_root=_write_source_root(
            tmp_path,
            payload=_source_payload(blocked_action=True),
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_lane_projected_jerk_progress_rejects_missing_lane_projected_support(
    tmp_path: Path,
) -> None:
    report = build_report(
        preflight_root=_write_source_root(
            tmp_path,
            payload=_source_payload(
                lane_status="route_topology_absolute_lateral_guard_support_insufficient"
            ),
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_lane_projected_absolute_support_present" in failed
    assert "source_prefix_lane_projected_absolute_support_present" not in failed


def test_lane_projected_jerk_progress_markdown_boundaries(tmp_path: Path) -> None:
    report = build_report(
        preflight_root=_write_source_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Lane-Projected Jerk/Progress Support Design Plan" in markdown
    assert "lane-projected" in markdown
    assert "jerk" in markdown
    assert "progress" in markdown
    assert "implementation unit tests" in markdown
    assert "no candidate generation execution" in markdown
    assert "no DP execution" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_lane_projected_jerk_progress_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_source_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--preflight_root",
            str(root),
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
        "# Lane-Projected Jerk/Progress Support Design Plan"
    )
