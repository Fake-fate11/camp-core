from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_implementation_plan import (
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK,
    PY_COMPILE_ERR,
    PY_COMPILE_LOG,
    PYTEST_ERR,
    PYTEST_LOG,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    EXIT_CODE,
    HEADS,
)


def _write_test_artifact(
    tmp_path: Path,
    *,
    exit_text: str = "PY_COMPILE_EXIT=0\nPYTEST_EXIT=0\n",
    pytest_text: str = "69 passed in 0.45s\n",
    py_compile_err: str = "",
    pytest_err: str = "",
) -> Path:
    root = tmp_path / "unit_test_artifact"
    root.mkdir()
    (root / PY_COMPILE_LOG).write_text("", encoding="utf-8")
    (root / PY_COMPILE_ERR).write_text(py_compile_err, encoding="utf-8")
    (root / PYTEST_LOG).write_text(pytest_text, encoding="utf-8")
    (root / PYTEST_ERR).write_text(pytest_err, encoding="utf-8")
    (root / EXIT_CODE).write_text(exit_text, encoding="utf-8")
    (root / HEADS).write_text("HEADS\n", encoding="utf-8")
    return root


def _build(tmp_path: Path, **kwargs) -> dict:
    root = _write_test_artifact(tmp_path, **kwargs)
    return build_report(
        test_artifact_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_implementation_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    plan = report["implementation_plan"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["next_gate_implementation_code_edit_authorized"] is True
    assert decision["next_gate_allowed_files"] == list(ALLOWED_NEXT_FILES)
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert plan["allowed_next_files"] == list(ALLOWED_NEXT_FILES)
    assert len(plan["components"]) == 5


def test_implementation_plan_rejects_missing_artifact(tmp_path: Path) -> None:
    report = build_report(
        test_artifact_root=tmp_path / "missing",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "unit_test_artifact_exists" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_implementation_plan_rejects_failed_unit_test_artifact(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        exit_text="PY_COMPILE_EXIT=0\nPYTEST_EXIT=1\n",
        pytest_text="1 failed\n",
        pytest_err="failure\n",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = report["final_decision"]["failed_checks"]
    assert "unit_test_pytest_exit_ok" in failed
    assert "unit_test_pytest_err_empty" in failed


def test_implementation_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_test_artifact(tmp_path)

    report = build_report(
        test_artifact_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_implementation_plan_rejects_camp_head_mismatch(tmp_path: Path) -> None:
    root = _write_test_artifact(tmp_path)

    report = build_report(
        test_artifact_root=root,
        camp_head="abc",
        camp_origin_main="def",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "camp_head_matches_origin_main" in report["final_decision"][
        "failed_checks"
    ]


def test_implementation_plan_markdown_records_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Default-Off Remediation Implementation Plan" in markdown
    for path in ALLOWED_NEXT_FILES:
        assert path in markdown
    assert "current gate is plan-only" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "formal seeds" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown


def test_implementation_plan_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    root = _write_test_artifact(tmp_path)
    output_json = tmp_path / "out" / "implementation_plan.json"
    output_md = tmp_path / "out" / "implementation_plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--test_artifact_root",
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
        "# Lane-Projected Jerk/Progress Default-Off Remediation Implementation Plan"
    )
