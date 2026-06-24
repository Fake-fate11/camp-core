from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_implementation_plan import (
    ALLOWED_NEXT_FILES,
    PLANNED_POLICY,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    IMPLEMENTATION_READY_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_AUDIT_AUTHORIZATION,
    SHA256SUMS,
    SUMMARY_JSON,
    SUMMARY_MD,
    build_report,
    main,
    render_markdown,
)


def _audit_text() -> str:
    return f"""
## 2026-06-23 - implementation only

status={IMPLEMENTATION_READY_STATUS}
training_execution_authorized=False
dp_modification_authorized=False

Next admissible gate:

`{REQUIRED_AUDIT_AUTHORIZATION}`.
"""


def _source_text() -> str:
    return f'''
class RouteTopologyCandidateConfig:
    generator_policy: str = "lane_centerline_red_stop"
    max_remediation_candidates: int = 12

def parse_args():
    choices = ("lane_centerline_red_stop", "{PLANNED_POLICY}")

def build_route_topology_candidates():
    _load_runtime
    if config.generator_policy == "{PLANNED_POLICY}":
        red_stop_distance_partition = "close_red_current_tick_fallback"
        profile = "comfort_first_jerk_limited_lane_station"
        current_tick_features_only = True
        candidate = _monotonic_lane_station_candidate(candidate)
        _prefix_comfort_candidates()
        metadata.append({{
            "variant": "{PLANNED_POLICY}",
            "candidate_budget_cap": int(config.max_remediation_candidates),
            "current_tick_features_only": True,
        }})
    math_boundary = "affine a_k^T w"
    convex = "simplex/CVaR/L2 robust master remains convex"

def _requires_current_tick_scalar_evidence(config):
    return config.generator_policy in {{"lane_projected_jerk_progress_red_stop", "{PLANNED_POLICY}"}}

def _requires_finite_selected_candidate_evidence(config):
    return config.generator_policy in {{"lane_projected_jerk_progress_red_stop", "{PLANNED_POLICY}"}}

def _monotonic_lane_station_candidate(): pass
'''


def _test_text() -> str:
    return f"""
def test_route_topology_generator_builds_comfort_first_remediation_policy():
    assert "lane_centerline_red_stop"
    assert "{PLANNED_POLICY}"
    assert "close_red_current_tick_fallback"
    assert "candidate_budget_cap"

def test_route_topology_comfort_first_remediation_candidate_budget_cap():
    assert "max_remediation_candidates"

def test_route_topology_comfort_first_requires_current_tick_scalars():
    assert "current_tick_scalar_invalid"

def test_route_topology_report_rejects_invalid_remediation_candidate_cap():
    assert "max_remediation_candidates"
"""


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    source_text: str | None = None,
    test_text: str | None = None,
    summary_updates: dict[str, object] | None = None,
    corrupt_sha: bool = False,
) -> tuple[Path, Path, Path, Path]:
    audit = tmp_path / "audit.md"
    source = tmp_path / "screen.py"
    tests = tmp_path / "test_screen.py"
    root = tmp_path / "implementation"
    root.mkdir()
    audit.write_text(
        audit_text if audit_text is not None else _audit_text(),
        encoding="utf-8",
    )
    source.write_text(
        source_text if source_text is not None else _source_text(),
        encoding="utf-8",
    )
    tests.write_text(test_text if test_text is not None else _test_text(), encoding="utf-8")
    summary: dict[str, object] = {
        "status": IMPLEMENTATION_READY_STATUS,
        "passed": True,
        "allowed_files_modified": list(ALLOWED_NEXT_FILES),
        "planned_policy": PLANNED_POLICY,
        "local_default_policy_preserved": True,
        "candidate_generation_execution": False,
        "fixed_snapshot_screen_rerun_execution": False,
        "replay_execution": False,
        "formal_seeds_used": False,
        "full36_used": False,
        "camp_retraining": False,
        "dp_modification": False,
        "online_selector_promotion": False,
        "atom_promotion": False,
        "safety_benefit_claim": False,
        "camp_over_dp_top1_claim": False,
        "verification": {
            "py_compile": "passed",
            "route_pytest": "23 passed",
            "related_pytest": "41 passed",
        },
        "file_sha256": {
            ALLOWED_NEXT_FILES[0]: hashlib.sha256(source.read_bytes()).hexdigest(),
            ALLOWED_NEXT_FILES[1]: hashlib.sha256(tests.read_bytes()).hexdigest(),
        },
    }
    if summary_updates:
        summary.update(summary_updates)
    (root / SUMMARY_JSON).write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / SUMMARY_MD).write_text(
        "# Implementation\n\n## Verification\n\n- route pytest: 23 passed\n",
        encoding="utf-8",
    )
    _write_sha256sums(root, (SUMMARY_JSON, SUMMARY_MD))
    if corrupt_sha:
        (root / SUMMARY_MD).write_text("mutated\n", encoding="utf-8")
    return audit, source, tests, root


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    source_text: str | None = None,
    test_text: str | None = None,
    summary_updates: dict[str, object] | None = None,
    corrupt_sha: bool = False,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, source, tests, root = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        source_text=source_text,
        test_text=test_text,
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


def test_post_implementation_static_review_complete(tmp_path: Path) -> None:
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


def test_post_implementation_static_review_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_post_implementation_static_review_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, corrupt_sha=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_rejects_source_contract_drift(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace("close_red_current_tick_fallback", "missing"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_contract_close_red_partition_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_post_implementation_static_review_rejects_test_contract_drift(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        test_text=_test_text().replace(
            "test_route_topology_comfort_first_requires_current_tick_scalars",
            "missing_test",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "test_contract_required_tests_present" in report["final_decision"][
        "failed_checks"
    ]


def test_post_implementation_static_review_rejects_blocked_summary(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        summary_updates={"fixed_snapshot_screen_rerun_execution": True},
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "summary_no_screen_rerun" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_review_markdown_boundaries(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Post-Implementation Static Review" in markdown
    assert "default_policy_preserved" in markdown
    assert "required_tests_present" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "CAMP retraining" in markdown
    assert "DP weights, DP code, DP configs, and DP invocation must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "classical Benders" in markdown


def test_post_implementation_static_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, source, tests, root = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
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
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Default-Off Fixed-Snapshot Screen Rerun Remediation Post-Implementation Static Review"
    )
