from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_implementation_plan import (
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK,
    HEADS,
    PY_COMPILE_ERR,
    PY_COMPILE_EXIT,
    PYTEST_RELATED_ERR,
    PYTEST_RELATED_EXIT,
    PYTEST_UNIT_ERR,
    PYTEST_UNIT_EXIT,
    READY_STATUS,
    REJECT_STATUS,
    SHA256SUMS,
    SOURCE_AUTHORIZED_NEXT_WORK,
    SOURCE_READY_STATUS,
    SUMMARY_JSON,
    SUMMARY_MD,
    build_report,
    main,
    render_markdown,
)


def _write_artifact(
    tmp_path: Path,
    *,
    summary_updates: dict | None = None,
    scope_updates: dict | None = None,
    camp_head: str = "abc",
    camp_origin_main: str = "abc",
    dp_head: str = EXPECTED_DP_HEAD,
    py_compile_exit: str = "0\n",
    pytest_unit_exit: str = "0\n",
    pytest_related_exit: str = "0\n",
    py_compile_err: str = "",
    pytest_unit_err: str = "",
    pytest_related_err: str = "",
    corrupt_sha_after_write: bool = False,
) -> Path:
    root = tmp_path / "unit_tests_artifact"
    root.mkdir()
    scope = {
        "tests_only": True,
        "production_code_modified": False,
        "screen_rerun_executed": False,
        "candidate_generation_executed": False,
        "replay_executed": False,
        "formal_seeds_used": False,
        "full36_used": False,
        "camp_retraining": False,
        "online_selector_promotion": False,
        "atom_promotion": False,
        "dp_modification": False,
        "safety_benefit_claim": False,
        "camp_over_dp_top1_claim": False,
        "classic_benders_claim": False,
    }
    if scope_updates:
        scope.update(scope_updates)

    summary = {
        "status": SOURCE_READY_STATUS,
        "passed": True,
        "authorized_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        "failed_checks": [],
        "tests_pinned": [
            "relative comfort prerequisites",
            "comfort failure budget labels",
            "hard blocker separation",
            "latency diagnostics",
            "absolute guard subset",
            "default-off policy",
            "math boundary",
        ],
        "scope": scope,
        "heads": {
            "camp_head": camp_head,
            "camp_origin_main": camp_origin_main,
            "dp_head": dp_head,
            "expected_dp_head": EXPECTED_DP_HEAD,
        },
    }
    if summary_updates:
        summary.update(summary_updates)

    files = {
        SUMMARY_JSON: json.dumps(summary, indent=2, sort_keys=True) + "\n",
        SUMMARY_MD: "# unit tests\n",
        HEADS: "HEADS\n",
        PY_COMPILE_ERR: py_compile_err,
        PY_COMPILE_EXIT: py_compile_exit,
        PYTEST_UNIT_ERR: pytest_unit_err,
        PYTEST_UNIT_EXIT: pytest_unit_exit,
        PYTEST_RELATED_ERR: pytest_related_err,
        PYTEST_RELATED_EXIT: pytest_related_exit,
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")

    sha_lines = []
    for name in sorted(files):
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        sha_lines.append(f"{digest}  {name}\n")
    (root / SHA256SUMS).write_text("".join(sha_lines), encoding="utf-8")

    if corrupt_sha_after_write:
        (root / SUMMARY_JSON).write_text(
            json.dumps({**summary, "passed": False}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return root


def _build(tmp_path: Path, **kwargs) -> dict:
    root = _write_artifact(tmp_path, **kwargs)
    return build_report(
        test_artifact_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_implementation_plan_accepts_completed_unit_test_artifact(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    plan = report["implementation_plan"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["production_implementation_edit_authorized"] is False
    assert decision["next_gate_implementation_code_edit_authorized"] is True
    assert decision["next_gate_allowed_files"] == list(ALLOWED_NEXT_FILES)
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["dp_modification_authorized"] is False
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
    assert report["final_decision"]["next_gate_allowed_files"] == []


def test_implementation_plan_rejects_sha_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, corrupt_sha_after_write=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "unit_test_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_implementation_plan_rejects_failed_unit_summary(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        summary_updates={
            "status": "wrong",
            "passed": False,
            "failed_checks": ["unit_test_pytest_unit_exit_zero"],
        },
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "unit_test_status_ready" in failed
    assert "unit_tests_passed" in failed
    assert "unit_test_failed_checks_clear" in failed


def test_implementation_plan_rejects_blocked_scope(tmp_path: Path) -> None:
    report = _build(tmp_path, scope_updates={"screen_rerun_executed": True})

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "unit_test_blocked_scope_clear" in report["final_decision"]["failed_checks"]


def test_implementation_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_artifact(tmp_path)

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
    root = _write_artifact(tmp_path)

    report = build_report(
        test_artifact_root=root,
        camp_head="abc",
        camp_origin_main="def",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "camp_head_matches_origin_main" in report["final_decision"]["failed_checks"]


def test_implementation_plan_markdown_records_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Fixed-Snapshot Screen Rerun Implementation Plan" in markdown
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
    root = _write_artifact(tmp_path)
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
        "# Fixed-Snapshot Screen Rerun Implementation Plan"
    )
