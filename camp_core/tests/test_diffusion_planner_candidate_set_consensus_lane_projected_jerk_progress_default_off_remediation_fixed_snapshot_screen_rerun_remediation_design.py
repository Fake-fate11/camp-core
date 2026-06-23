from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_failure_attribution import (
    AUTHORIZED_NEXT_WORK as ANALYSIS_AUTHORIZED_NEXT_WORK,
    READY_STATUS as ANALYSIS_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_remediation_design import (
    ANALYSIS_COMMAND_EXIT,
    ANALYSIS_EXIT,
    ANALYSIS_JSON,
    ANALYSIS_JSON_COMPAT,
    AUTHORIZED_NEXT_WORK,
    DEFAULT_ANALYSIS_ROOT,
    EXIT_CODE,
    HEADS,
    READY_STATUS,
    REJECT_STATUS,
    SHA256SUMS,
    build_report,
    main,
    render_markdown,
)


def _analysis_payload(
    *,
    status: str = ANALYSIS_READY_STATUS,
    authorized_next_work: str | None = ANALYSIS_AUTHORIZED_NEXT_WORK,
    primary_blocker_family: str = "comfort_support_deficit",
    latency_failures: bool = True,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": authorized_next_work,
            "candidate_generation_execution_authorized": False,
            "fixed_snapshot_screen_rerun_authorized": False,
            "fixed_snapshot_screen_rerun_execution_authorized": False,
            "new_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "atom_promotion_authorized": blocked_action,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "safety_benefit_evidence": False,
            "camp_over_dp_top1_claim_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "source_summary": {
            "screen": {
                "generated_candidate_rows": 276,
                "comfort_rows": 0,
            }
        },
        "read_only_attribution": {
            "primary_blocker_family": primary_blocker_family,
            "primary_comfort_blocker": "route_topology_comfort_blocked_command_jerk",
            "primary_hard_blocker": "dp_kinematic",
            "primary_latency_source": "total",
            "recommendation_category": "design-new-policy-plan-only",
            "absolute_lateral_guard_retained": True,
            "comfort_blocker_ranking": [
                {
                    "name": "route_topology_comfort_blocked_command_jerk",
                    "count": 64,
                    "share_of_generated_rows": 0.2318840579710145,
                }
            ],
            "hard_blocker_ranking": [
                {
                    "name": "dp_kinematic",
                    "count": 197,
                    "share_of_generated_rows": 0.7137681159420289,
                }
            ],
            "latency_ranking": [
                {
                    "name": "total",
                    "p95_ms": 106.16,
                    "threshold_ms": 100.0,
                    "gate_passed": False,
                },
                {
                    "name": "candidate_build",
                    "p95_ms": 36.27,
                    "threshold_ms": 10.0,
                    "gate_passed": False,
                },
            ],
            "latency_gate_failures": [
                {
                    "name": "total",
                    "p95_ms": 106.16,
                    "threshold_ms": 100.0,
                    "gate_passed": False,
                }
            ]
            if latency_failures
            else [],
            "absolute_guard_failure_ranking": [
                {
                    "name": "hard_dp_kinematic",
                    "count": 197,
                    "share_of_generated_rows": 0.7137681159420289,
                }
            ],
        },
    }


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_analysis_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    analysis_exit: str = "0",
    analysis_json_name: str = ANALYSIS_JSON,
    analysis_exit_name: str = ANALYSIS_EXIT,
) -> Path:
    root = tmp_path / "analysis"
    root.mkdir()
    (root / analysis_json_name).write_text(
        json.dumps(payload or _analysis_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / analysis_exit_name).write_text(f"{analysis_exit}\n", encoding="utf-8")
    (root / HEADS).write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(root, (analysis_json_name, analysis_exit_name, HEADS))
    return root


def _build(tmp_path: Path, payload: dict[str, object] | None = None) -> dict[str, object]:
    return build_report(
        analysis_root=_write_analysis_root(tmp_path, payload=payload),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_default_off_rerun_remediation_design_default_source_is_current_analysis() -> None:
    assert DEFAULT_ANALYSIS_ROOT.endswith(
        "candidate_set_consensus_lane_projected_"
        "jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_"
        "failure_attribution_read_only_analysis_63e9cf2"
    )
    assert ANALYSIS_JSON == (
        "fixed_snapshot_screen_rerun_failure_attribution_read_only_analysis.json"
    )


def test_default_off_rerun_remediation_design_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    design = report["remediation_design"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["safety_benefit_evidence"] is False
    assert design["selected_next_work"] == AUTHORIZED_NEXT_WORK
    assert design["design_priorities"][0]["focus"].startswith("restore comfort")
    assert len(design["remediation_threads"]) == 4


def test_default_off_rerun_remediation_design_accepts_current_analysis_artifact(
    tmp_path: Path,
) -> None:
    report = build_report(
        analysis_root=_write_analysis_root(
            tmp_path,
            analysis_json_name=ANALYSIS_JSON_COMPAT,
            analysis_exit_name=ANALYSIS_COMMAND_EXIT,
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis_artifact"]["required_files"][ANALYSIS_JSON_COMPAT] is True
    assert report["analysis_artifact"]["analysis_exit_file"] == ANALYSIS_COMMAND_EXIT


def test_default_off_rerun_remediation_design_accepts_exit_code_fallback(
    tmp_path: Path,
) -> None:
    report = build_report(
        analysis_root=_write_analysis_root(
            tmp_path,
            analysis_json_name=ANALYSIS_JSON_COMPAT,
            analysis_exit_name=EXIT_CODE,
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis_artifact"]["analysis_exit_file"] == EXIT_CODE


def test_default_off_rerun_remediation_design_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    root = _write_analysis_root(tmp_path)
    (root / ANALYSIS_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        analysis_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "analysis_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_remediation_design_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        analysis_root=_write_analysis_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_remediation_design_rejects_missing_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_analysis_payload(authorized_next_work="not_allowed"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "analysis_authorizes_remediation_design" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_rerun_remediation_design_rejects_wrong_blocker_family(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_analysis_payload(primary_blocker_family="latency"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "primary_blocker_family_comfort_deficit" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_rerun_remediation_design_rejects_missing_latency_failure(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_analysis_payload(latency_failures=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latency_gate_failures_present" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_remediation_design_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_analysis_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "analysis_blocked_actions_clear" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_rerun_remediation_design_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Remediation Design Plan" in markdown
    assert "Design Priorities" in markdown
    assert "Plan-Only Remediation Threads" in markdown
    assert "implementation is not authorized" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown


def test_default_off_rerun_remediation_design_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_analysis_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--analysis_root",
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
        "# Default-Off Fixed-Snapshot Rerun Remediation Design Plan"
    )
