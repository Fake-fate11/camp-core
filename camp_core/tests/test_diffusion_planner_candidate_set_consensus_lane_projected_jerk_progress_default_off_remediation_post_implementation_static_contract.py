from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    HEADS,
    SHA256SUMS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DEFAULT_SOURCE,
    DEFAULT_TEST,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _write_artifact(tmp_path: Path, *, pytest_related_exit: int = 0) -> Path:
    root = tmp_path / "artifact"
    root.mkdir()
    files = {
        HEADS: "CAMP_HEAD=abc\nCAMP_ORIGIN_MAIN=abc\nDP_HEAD=expected\n",
        "PY_COMPILE.log": "",
        "PY_COMPILE.err": "",
        "PY_COMPILE_EXIT": "0\n",
        "PYTEST_UNIT.log": "18 passed in 0.34s\n",
        "PYTEST_UNIT.err": "",
        "PYTEST_UNIT_EXIT": "0\n",
        "PYTEST_RELATED.log": "78 passed in 0.46s\n",
        "PYTEST_RELATED.err": "",
        "PYTEST_RELATED_EXIT": f"{pytest_related_exit}\n",
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    lines = []
    for name in files:
        path = root / name
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _build(tmp_path: Path, **artifact_kwargs) -> dict:
    return build_report(
        implementation_artifact_root=_write_artifact(tmp_path, **artifact_kwargs),
        source_path=DEFAULT_SOURCE,
        test_path=DEFAULT_TEST,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_post_implementation_static_contract_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_plan_authorized"] is True
    assert decision["dp_modification_authorized"] is False
    assert report["implementation_artifact"]["required_files"]["PYTEST_UNIT.log"]
    assert all(report["source_contract"]["contracts"].values())
    assert all(report["test_contract"]["contracts"].values())
    assert report["source_contract"]["contracts"]["current_tick_scalar_guard_present"]
    assert report["source_contract"]["contracts"]["config_budget_failure_labels_present"]
    assert report["test_contract"]["contracts"]["current_tick_scalar_guard_test_present"]
    assert report["test_contract"]["contracts"]["config_budget_failure_label_test_present"]


def test_post_implementation_static_contract_rejects_artifact_failure(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, pytest_related_exit=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_pytest_related_exit_ok" in report["final_decision"][
        "failed_checks"
    ]
    assert report["final_decision"]["authorized_next_work"] is None


def test_post_implementation_static_contract_rejects_source_contract_missing(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.py"
    source.write_text("def unrelated():\n    pass\n", encoding="utf-8")
    report = build_report(
        implementation_artifact_root=_write_artifact(tmp_path),
        source_path=source,
        test_path=DEFAULT_TEST,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_diagnostic_function_present" in report["final_decision"][
        "failed_checks"
    ]


def test_post_implementation_static_contract_rejects_test_contract_missing(
    tmp_path: Path,
) -> None:
    test_path = tmp_path / "test_route.py"
    test_path.write_text("def test_unrelated():\n    pass\n", encoding="utf-8")
    report = build_report(
        implementation_artifact_root=_write_artifact(tmp_path),
        source_path=DEFAULT_SOURCE,
        test_path=test_path,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "test_fail_closed_test_present" in report["final_decision"][
        "failed_checks"
    ]


def test_post_implementation_static_contract_rejects_head_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_artifact_root=_write_artifact(tmp_path),
        source_path=DEFAULT_SOURCE,
        test_path=DEFAULT_TEST,
        camp_head="abc",
        camp_origin_main="def",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "camp_head_matches_origin_main" in report["final_decision"][
        "failed_checks"
    ]


def test_post_implementation_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_artifact_root=_write_artifact(tmp_path),
        source_path=DEFAULT_SOURCE,
        test_path=DEFAULT_TEST,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_contract_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Contract Review" in markdown
    assert "static review only" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun execution is not authorized" in markdown
    assert "formal seeds" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown
    assert "plan-only gate" in markdown


def test_post_implementation_static_contract_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact = _write_artifact(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--implementation_artifact_root",
            str(artifact),
            "--source_path",
            str(DEFAULT_SOURCE),
            "--test_path",
            str(DEFAULT_TEST),
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
        "# Lane-Projected Jerk/Progress Default-Off Remediation"
    )
