from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_fixed_snapshot_execution import (
    AUTHORIZED_NEXT_WORK,
    BLOCKED_ACTIONS,
    GUARD_ENV_ASSIGNMENT,
    GUARD_ENV_VAR,
    POLICY_NAME,
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
    policy: str = POLICY_NAME,
    default_policy: str = "lane_centerline_red_stop",
) -> dict[str, object]:
    decision = {
        "status": status,
        "passed": passed,
        "authorized_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "implementation_unit_tests_ready": passed,
        "fixed_snapshot_execution_plan_authorized": passed,
        "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "failed_checks": [],
    }
    for key in BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_action:
        decision["atom_promotion_authorized"] = True
    return {
        "final_decision": decision,
        "implementation": {
            "policy": policy,
            "default_policy_remains": default_policy,
            "generated_shape": [1, 80, 4],
            "jerk_abs_max_mps3": 5.999999,
        },
    }


def _write_source_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "implementation_unit_tests"
    root.mkdir()
    (root / SOURCE_JSON).write_text(
        json.dumps(payload or _source_payload()),
        encoding="utf-8",
    )
    (root / SOURCE_MD).write_text("# implementation unit tests\n", encoding="utf-8")
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


def test_fixed_snapshot_execution_plan_ready(tmp_path: Path) -> None:
    report = build_report(
        implementation_root=_write_source_root(tmp_path),
        execution_root=tmp_path / "execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]
    plan = report["fixed_snapshot_execution_plan"]
    runbook = report["runbook"]["text"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_execution_plan_ready"] is True
    assert decision["guarded_fixed_snapshot_screen_next_gate_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_candidate_generation_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert plan["snapshot_scope"]["seed"] == 2
    assert plan["snapshot_scope"]["expected_snapshot_count"] == 57
    assert plan["candidate_config"]["generator_policy"] == POLICY_NAME
    assert GUARD_ENV_VAR in runbook
    assert GUARD_ENV_ASSIGNMENT in render_markdown(report)


def test_fixed_snapshot_execution_plan_rejects_source_sha_mismatch(
    tmp_path: Path,
) -> None:
    source = _write_source_root(tmp_path)
    (source / SOURCE_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        implementation_root=source,
        execution_root=tmp_path / "execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_sha256sums_ok" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_fixed_snapshot_execution_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = build_report(
        implementation_root=_write_source_root(tmp_path),
        execution_root=tmp_path / "execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fixed_snapshot_execution_plan_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_root=_write_source_root(
            tmp_path,
            payload=_source_payload(
                status="candidate_set_consensus_lane_projected_bad",
                passed=False,
            ),
        ),
        execution_root=tmp_path / "execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_unit_tests_ready" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_fixed_snapshot_execution_plan_rejects_source_blocked_action(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_root=_write_source_root(
            tmp_path,
            payload=_source_payload(blocked_action=True),
        ),
        execution_root=tmp_path / "execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_fixed_snapshot_execution_plan_rejects_wrong_policy(tmp_path: Path) -> None:
    report = build_report(
        implementation_root=_write_source_root(
            tmp_path,
            payload=_source_payload(policy="lane_projected_red_stop"),
        ),
        execution_root=tmp_path / "execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_policy" in report["final_decision"]["failed_checks"]


def test_fixed_snapshot_execution_plan_markdown_and_runbook_boundaries(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_root=_write_source_root(tmp_path),
        execution_root=tmp_path / "execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)
    runbook = report["runbook"]["text"]

    assert "Fixed-Snapshot Execution Plan" in markdown
    assert "plan-only" in markdown
    assert "single_existing_nonformal_fixed_snapshot_corpus" in markdown
    assert "formal seeds" in markdown
    assert "replay is not authorized" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown
    assert "latency" in markdown
    assert "absolute lateral guard" in markdown
    assert GUARD_ENV_VAR in runbook
    assert '!= "yes"' in runbook
    assert "exit 2" in runbook
    assert "git pull" not in runbook.lower()
    assert POLICY_NAME in runbook
    assert "analyze_diffusion_planner_route_topology_candidate_screen.py" in runbook
    assert "analyze_diffusion_planner_route_topology_absolute_comfort_guard.py" in runbook
    assert "SHA256SUMS" in runbook


def test_fixed_snapshot_execution_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_source_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    output_bash = tmp_path / "out" / "run.sh"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--implementation_root",
            str(source),
            "--execution_root",
            str(tmp_path / "execution"),
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
            "--output_bash",
            str(output_bash),
        ],
    )

    main()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Lane-Projected Jerk/Progress Fixed-Snapshot Execution Plan"
    )
    assert output_bash.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
