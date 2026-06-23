from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_product_code_implementation_plan import (
    EXIT_CODE,
    GATE_NAME,
    HEADS,
    PRODUCT_IMPLEMENTATION_CANDIDATE_FILES,
    PYTEST_RELATED_ERR,
    PYTEST_RELATED_EXIT,
    PYTEST_UNIT_TESTS_ERR,
    PYTEST_UNIT_TESTS_EXIT,
    PY_COMPILE_ERR,
    PY_COMPILE_EXIT,
    READY_STATUS,
    RECOMMENDED_NEXT_GATE,
    REJECT_STATUS,
    REQUIRED_SOURCE_FILES,
    SHA256SUMS,
    SHA256SUMS_CHECK_EXIT,
    SOURCE_COMPLETE_STATUS,
    UNIT_TESTS_DECISION,
    build_report,
    main,
    render_markdown,
)


def _write_artifact(
    tmp_path: Path,
    *,
    camp_head: str = "abc",
    camp_origin_main: str = "abc",
    dp_head: str = EXPECTED_DP_HEAD,
    decision_updates: dict[str, str] | None = None,
    corrupt_sha_after_write: bool = False,
    missing_file: str | None = None,
    py_compile_exit: str = "0\n",
    pytest_unit_exit: str = "0\n",
    pytest_related_exit: str = "0\n",
    sha_check_exit: str = "0\n",
    py_compile_err: str = "",
    pytest_unit_err: str = "",
    pytest_related_err: str = "",
) -> Path:
    root = tmp_path / "unit_tests_only"
    root.mkdir()
    decision = {
        "status": SOURCE_COMPLETE_STATUS,
        "unit_tests_only_complete": "True",
        "implementation_code_edit_authorized": "False",
        "candidate_generation_execution_authorized": "False",
        "fixed_snapshot_screen_rerun_authorized": "False",
        "new_replay_authorized": "False",
        "formal_seeds_authorized": "False",
        "full36_authorized": "False",
        "camp_retraining_authorized": "False",
        "dp_modification_authorized": "False",
        "safety_benefit_evidence": "False",
        "camp_over_dp_top1_claim_authorized": "False",
        "test_groups": (
            "relative_comfort_static_contract_unit_tests,"
            "hard_blocker_separation_unit_tests,"
            "latency_static_contract_unit_tests,"
            "absolute_guard_subset_unit_tests,"
            "policy_default_off_unit_tests,"
            "math_boundary_unit_tests"
        ),
    }
    if decision_updates:
        decision.update(decision_updates)

    files = {
        HEADS: (
            f"CAMP_HEAD={camp_head}\n"
            f"CAMP_ORIGIN_MAIN={camp_origin_main}\n"
            f"DP_HEAD={dp_head}\n"
        ),
        UNIT_TESTS_DECISION: "\n".join(f"{k}={v}" for k, v in decision.items())
        + "\n",
        EXIT_CODE: "0\n",
        PY_COMPILE_EXIT: py_compile_exit,
        PY_COMPILE_ERR: py_compile_err,
        PYTEST_UNIT_TESTS_EXIT: pytest_unit_exit,
        PYTEST_UNIT_TESTS_ERR: pytest_unit_err,
        PYTEST_RELATED_EXIT: pytest_related_exit,
        PYTEST_RELATED_ERR: pytest_related_err,
        SHA256SUMS_CHECK_EXIT: sha_check_exit,
    }
    for name in REQUIRED_SOURCE_FILES:
        if name == SHA256SUMS or name == missing_file:
            continue
        (root / name).write_text(files[name], encoding="utf-8")

    sha_lines = []
    for path in sorted(root.iterdir()):
        if path.name == SHA256SUMS:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        sha_lines.append(f"{digest}  {path.name}\n")
    if missing_file != SHA256SUMS:
        (root / SHA256SUMS).write_text("".join(sha_lines), encoding="utf-8")

    if corrupt_sha_after_write:
        (root / UNIT_TESTS_DECISION).write_text(
            "status=corrupted\n",
            encoding="utf-8",
        )

    return root


def _build(tmp_path: Path, **kwargs) -> dict:
    root = _write_artifact(tmp_path, **kwargs)
    return build_report(
        unit_test_artifact_root=root,
        camp_head=kwargs.get("camp_head", "abc"),
        camp_origin_main=kwargs.get("camp_origin_main", "abc"),
        dp_head=kwargs.get("dp_head", EXPECTED_DP_HEAD),
        label="unit",
    )


def test_product_code_implementation_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    plan = report["implementation_plan"]
    assert report["analysis"]["gate"] == GATE_NAME
    assert decision["status"] == READY_STATUS
    assert decision["implementation_plan_ready"] is True
    assert decision["authorized_next_work"] is None
    assert decision["selected_next_work"] is None
    assert decision["recommended_next_gate"] == RECOMMENDED_NEXT_GATE
    assert decision["recommended_next_gate_requires_explicit_authorization"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["full36_authorized"] is False
    assert decision["camp_retraining_authorized"] is False
    assert decision["online_selector_promotion_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_evidence"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert plan["product_code_candidate_files"] == list(
        PRODUCT_IMPLEMENTATION_CANDIDATE_FILES
    )
    assert len(plan["components"]) == 5


def test_product_code_plan_rejects_missing_artifact(tmp_path: Path) -> None:
    report = build_report(
        unit_test_artifact_root=tmp_path / "missing",
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == REJECT_STATUS
    assert "source_artifact_exists" in decision["failed_checks"]
    assert decision["recommended_next_gate"] is None


def test_product_code_plan_rejects_sha_mismatch(tmp_path: Path) -> None:
    report = _build(tmp_path, corrupt_sha_after_write=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_product_code_plan_rejects_failed_source_decision(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        decision_updates={
            "status": "wrong",
            "unit_tests_only_complete": "False",
        },
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status_complete" in failed
    assert "source_unit_tests_only_complete" in failed


def test_product_code_plan_rejects_forbidden_source_flag(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        decision_updates={"fixed_snapshot_screen_rerun_authorized": "True"},
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_forbidden_flags_clear" in report["final_decision"]["failed_checks"]


def test_product_code_plan_rejects_failed_exit_or_stderr(tmp_path: Path) -> None:
    report = _build(
        tmp_path,
        pytest_unit_exit="1\n",
        pytest_unit_err="failed\n",
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_pytest_unit_tests_exit_zero" in failed
    assert "source_pytest_unit_tests_err_empty" in failed


def test_product_code_plan_rejects_head_mismatch(tmp_path: Path) -> None:
    root = _write_artifact(tmp_path, camp_head="artifact-head")
    report = build_report(
        unit_test_artifact_root=root,
        camp_head="current-head",
        camp_origin_main="current-head",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_camp_head_matches_current" in failed


def test_product_code_plan_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_artifact(tmp_path, dp_head="wrong")
    report = build_report(
        unit_test_artifact_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
        label="unit",
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in failed
    assert "source_dp_head_fixed" in failed


def test_product_code_plan_markdown_records_required_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "# Candidate-Set Consensus Product-Code Implementation Plan" in markdown
    assert GATE_NAME in markdown
    assert "current gate is plan-only" in markdown
    assert "Product-code edit authorized now: `False`" in markdown
    assert "requires separate explicit authorization: `True`" in markdown
    for path in PRODUCT_IMPLEMENTATION_CANDIDATE_FILES:
        assert path in markdown
    assert "default-off" in markdown
    assert "opt-in" in markdown
    assert "payload no-leak" in markdown
    assert "current-tick" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "absolute lateral guard" in markdown
    assert "DP weights, config, source code" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown


def test_product_code_plan_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    root = _write_artifact(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--unit_test_artifact_root",
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
        "# Candidate-Set Consensus Product-Code Implementation Plan"
    )
