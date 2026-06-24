from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_implementation_plan import (
    ALLOWED_NEXT_FILES,
    AUTHORIZED_NEXT_WORK as IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK,
    PLANNED_POLICY,
    REQUIRED_TESTS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    IMPLEMENTATION_AUDIT_STATUS,
    IMPLEMENTATION_READY_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    SHA256SUMS,
    SUMMARY_JSON,
    SUMMARY_MD,
    build_report,
    main,
    render_markdown,
)


def _audit_text() -> str:
    return f"""
status={IMPLEMENTATION_AUDIT_STATUS}

Next admissible gate:

`{IMPLEMENTATION_PLAN_AUTHORIZED_NEXT_WORK}`.
"""


def _source_text() -> str:
    return f'''
class RouteTopologyCandidateConfig:
    generator_policy: str = "lane_centerline_red_stop"
    max_remediation_candidates: int = 12

def parse_args():
    choices = ("lane_centerline_red_stop", "{PLANNED_POLICY}")

def build_route_topology_candidates():
    if config.generator_policy == "{PLANNED_POLICY}":
        fail_closed_partition = "fallback_ready"
        hard_feasibility_floor_current_tick = True
        comfort_after_hard_progress = True
        current_tick_features_only = True
        candidate_budget_cap = int(config.max_remediation_candidates)

def _requires_current_tick_scalar_evidence(config):
    return config.generator_policy in {{"lane_projected_jerk_progress_red_stop", "{PLANNED_POLICY}"}}

def _requires_finite_selected_candidate_evidence(config):
    return config.generator_policy in {{"lane_projected_jerk_progress_red_stop", "{PLANNED_POLICY}"}}

def _is_negative_support_followup_policy(config): pass
def _negative_support_offset_scales(config): pass
def _add_negative_support_fail_closed_partition(diagnostics): pass
'''


def _test_text() -> str:
    return "\n".join(f"def {name}(): pass" for name in REQUIRED_TESTS)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_inputs(
    tmp_path: Path,
    *,
    source_text: str | None = None,
    test_text: str | None = None,
    audit_text: str | None = None,
    summary_updates: dict[str, object] | None = None,
    corrupt_sha: bool = False,
) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "implementation"
    audit = tmp_path / "audit.md"
    source = tmp_path / "screen.py"
    tests = tmp_path / "test_screen.py"
    root.mkdir()
    source.write_text(source_text if source_text is not None else _source_text(), encoding="utf-8")
    tests.write_text(test_text if test_text is not None else _test_text(), encoding="utf-8")
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    summary: dict[str, object] = {
        "status": IMPLEMENTATION_READY_STATUS,
        "passed": True,
        "planned_policy": PLANNED_POLICY,
        "allowed_files_modified": list(ALLOWED_NEXT_FILES),
        "file_sha256": {
            ALLOWED_NEXT_FILES[0]: hashlib.sha256(source.read_bytes()).hexdigest(),
            ALLOWED_NEXT_FILES[1]: hashlib.sha256(tests.read_bytes()).hexdigest(),
        },
        "verification": {
            "py_compile": "passed",
            "route_pytest": "28 passed",
            "related_pytest": "56 passed",
        },
        "implementation_summary": {
            "default_policy_preserved": True,
            "new_policy_opt_in": True,
        },
        "blocked_actions": {
            "candidate_generation_execution": False,
            "fixed_snapshot_screen_rerun_execution": False,
            "replay_execution": False,
            "formal_seeds_used": False,
            "camp_retraining": False,
            "dp_modification": False,
        },
    }
    if summary_updates:
        summary.update(summary_updates)
    (root / SUMMARY_JSON).write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / SUMMARY_MD).write_text(
        "# Negative-Support Follow-Up Implementation Summary\n",
        encoding="utf-8",
    )
    _write_sha256sums(root, (SUMMARY_JSON, SUMMARY_MD))
    if corrupt_sha:
        (root / SUMMARY_MD).write_text("mutated\n", encoding="utf-8")
    return audit, source, tests, root


def _build(
    tmp_path: Path,
    *,
    source_text: str | None = None,
    test_text: str | None = None,
    audit_text: str | None = None,
    summary_updates: dict[str, object] | None = None,
    corrupt_sha: bool = False,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, source, tests, root = _write_inputs(
        tmp_path,
        source_text=source_text,
        test_text=test_text,
        audit_text=audit_text,
        summary_updates=summary_updates,
        corrupt_sha=corrupt_sha,
    )
    return build_report(
        implementation_root=root,
        audit_path=audit,
        source_path=source,
        test_path=tests,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=dp_head,
        label="unit",
    )


def test_negative_support_post_implementation_static_review_complete(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fixed_snapshot_screen_rerun_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_negative_support_post_implementation_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_negative_support_post_implementation_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, corrupt_sha=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_negative_support_post_implementation_rejects_missing_source_contract(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, source_text=_source_text().replace("fail_closed_partition", "missing"))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_contract_fail_closed_partition_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_negative_support_post_implementation_rejects_missing_test_contract(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        test_text=_test_text().replace(
            "test_route_topology_negative_support_followup_candidate_budget_cap",
            "missing_test",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "test_contract_required_tests_present" in report["final_decision"][
        "failed_checks"
    ]


def test_negative_support_post_implementation_markdown_records_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Post-Implementation Static Review" in markdown
    assert "fixed-snapshot screen rerun planning only may follow" in markdown
    assert "formal seeds" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown


def test_negative_support_post_implementation_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, source, tests, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "post_review.json"
    output_md = tmp_path / "out" / "post_review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--implementation_root",
            str(root),
            "--audit_path",
            str(audit),
            "--source_path",
            str(source),
            "--test_path",
            str(tests),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "unit",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Post-Implementation Static Review" in markdown
