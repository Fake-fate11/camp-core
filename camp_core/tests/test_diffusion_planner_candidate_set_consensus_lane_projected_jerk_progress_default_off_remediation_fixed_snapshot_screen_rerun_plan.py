from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
    FORMAL_SEEDS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun import (
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
    authorized_next_work: str | None = SOURCE_AUTHORIZED_NEXT_WORK,
    selected_next_work: str | None = SOURCE_AUTHORIZED_NEXT_WORK,
    plan_authorized: bool = True,
    rerun_authorized: bool = False,
    blocked_action: bool = False,
) -> dict[str, object]:
    decision: dict[str, object] = {
        "status": status,
        "passed": passed,
        "authorized_next_work": authorized_next_work,
        "selected_next_work": selected_next_work,
        "failed_checks": [],
        "post_implementation_static_contract_review_complete": passed,
        "fixed_snapshot_screen_rerun_plan_authorized": plan_authorized,
    }
    for key in BLOCKED_ACTIONS:
        decision[key] = False
    decision["fixed_snapshot_screen_rerun_authorized"] = rerun_authorized
    if blocked_action:
        decision["atom_promotion_authorized"] = True
    return {"final_decision": decision}


def _write_review_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    pytest_related_exit: int = 0,
    review_exit: int = 0,
) -> Path:
    root = tmp_path / "post_review"
    root.mkdir()
    files = {
        SOURCE_JSON: json.dumps(payload or _source_payload()),
        SOURCE_MD: "# post implementation static contract review\n",
        "HEADS.txt": f"CAMP_HEAD=abc\nCAMP_ORIGIN_MAIN=abc\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        "PY_COMPILE.log": "",
        "PY_COMPILE.err": "",
        "PYTEST_REVIEW.log": "8 passed in 0.04s\n",
        "PYTEST_REVIEW.err": "",
        "PYTEST_RELATED.log": "86 passed in 0.46s\n",
        "PYTEST_RELATED.err": "",
        "REVIEW_COMMAND.log": "review command\n",
        "REVIEW_COMMAND.err": "",
        "EXIT_CODE": (
            "PY_COMPILE_EXIT=0\n"
            "PYTEST_REVIEW_EXIT=0\n"
            f"PYTEST_RELATED_EXIT={pytest_related_exit}\n"
            f"REVIEW_EXIT={review_exit}\n"
        ),
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    _write_sha256sums(root, tuple(files))
    return root


def _build(tmp_path: Path, **review_kwargs) -> dict:
    return build_report(
        review_root=_write_review_root(tmp_path, **review_kwargs),
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_fixed_snapshot_screen_rerun_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    plan = report["fixed_snapshot_rerun_plan"]
    matrix = plan["route_seed_matrix"]
    seeds = {row["seed"] for row in matrix}

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_plan_ready"] is True
    assert decision["fixed_snapshot_screen_rerun_execution_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["next_gate_requires_user_authorization"] is True
    assert plan["selection_type"] == "guarded_fixed_snapshot_screen_rerun_plan_only"
    assert plan["coverage_summary"]["traffic_light_covered"] is True
    assert plan["coverage_summary"]["turn_covered"] is True
    assert plan["coverage_summary"]["normal_covered"] is True
    assert plan["coverage_summary"]["nishishinjuku_assets_declared"] is True
    assert plan["coverage_summary"]["included_guarded_rerun_count"] == 1
    assert not (seeds & FORMAL_SEEDS)
    assert plan["candidate_config"]["generator_policy"] == POLICY_NAME
    assert plan["candidate_config"]["default_policy_preserved"] == "lane_centerline_red_stop"
    assert report["runbook"]["guard_env_assignment"] == GUARD_ENV_ASSIGNMENT


def test_fixed_snapshot_screen_rerun_plan_rejects_review_sha_mismatch(
    tmp_path: Path,
) -> None:
    review_root = _write_review_root(tmp_path)
    (review_root / SOURCE_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        review_root=review_root,
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_sha256sums_ok" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_fixed_snapshot_screen_rerun_plan_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        review_root=_write_review_root(tmp_path),
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fixed_snapshot_screen_rerun_plan_rejects_camp_head_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        review_root=_write_review_root(tmp_path),
        planned_execution_root=tmp_path / "planned_execution",
        camp_head="abc",
        camp_origin_main="def",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "camp_head_equals_origin_main" in report["final_decision"]["failed_checks"]


def test_fixed_snapshot_screen_rerun_plan_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_source_payload(
            status="candidate_set_consensus_lane_projected_bad",
            passed=False,
            authorized_next_work=None,
            selected_next_work=None,
            plan_authorized=False,
        ),
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert "source_authorizes_rerun_plan" in failed
    assert "source_static_review_complete" in failed


def test_fixed_snapshot_screen_rerun_plan_rejects_execution_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_source_payload(rerun_authorized=True),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_rerun_execution_not_authorized" in report["final_decision"][
        "failed_checks"
    ]
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_fixed_snapshot_screen_rerun_plan_rejects_review_command_failure(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, review_exit=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_command_exit_ok" in report["final_decision"]["failed_checks"]


def test_fixed_snapshot_screen_rerun_plan_markdown_and_runbook_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)
    runbook = report["runbook"]["text"]

    assert "Fixed-Snapshot Screen Rerun Plan" in markdown
    assert "plan-only" in markdown
    assert "traffic_light" in markdown
    assert "turn" in markdown
    assert "normal" in markdown
    assert "nishishinjuku_release_auto_route" in markdown
    assert "selector_equivalence" in markdown
    assert "payload_no_leak_default_off" in markdown
    assert "spread" in markdown
    assert "rank" in markdown
    assert "sensitivity" in markdown
    assert "formal seeds" in markdown
    assert "safety benefit" in markdown.lower()
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown
    assert "requires user authorization" in markdown
    assert GUARD_ENV_VAR in runbook
    assert '!= "yes"' in runbook
    assert "exit 2" in runbook
    assert "git pull" not in runbook.lower()
    assert EXPECTED_DP_HEAD in runbook
    assert POLICY_NAME in runbook
    assert "SNAPSHOT_COUNT" in runbook
    assert "HEADS.txt" in runbook
    assert "SHA256SUMS" in runbook
    assert "analyze_diffusion_planner_route_topology_candidate_screen.py" in runbook
    assert "analyze_diffusion_planner_route_topology_absolute_comfort_guard.py" in runbook


def test_fixed_snapshot_screen_rerun_plan_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_root = _write_review_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    output_bash = tmp_path / "out" / "run.sh"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--review_root",
            str(review_root),
            "--planned_execution_root",
            str(tmp_path / "planned_execution"),
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
        "# Lane-Projected Jerk/Progress Default-Off Remediation"
    )
    assert output_bash.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
