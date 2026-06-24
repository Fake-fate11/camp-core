from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostics import (
    ATTRIBUTION_JSON,
    AUTHORIZED_NEXT_WORK,
    PLAN_JSON,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_TABLES,
    SCREEN_JSON,
    STATIC_REVIEW_JSON,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_implementation_plan import (
    PLANNED_DIAGNOSTIC_SCRIPT,
    PLANNED_DIAGNOSTIC_TEST,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_fixed_snapshot_screen_rerun_remediation_negative_support_followup_residual_comfort_failure_diagnostic_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK as STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    READY_STATUS as STATIC_REVIEW_READY_STATUS,
)


CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
status={STATIC_REVIEW_READY_STATUS}
authorized_next_work={STATIC_REVIEW_AUTHORIZED_NEXT_WORK}
{PLANNED_DIAGNOSTIC_SCRIPT}
{PLANNED_DIAGNOSTIC_TEST}
training_execution_authorized=False
dp_modification_authorized=False
"""


def _candidate_row(
    *,
    snapshot: str = "s0.npz",
    partition: str = "standard_min_stop_distance",
    offset: float = 0.0,
    margin: float = 2.0,
    backup: float = 0.0,
    command_jerk: bool = True,
) -> dict[str, object]:
    failures = ["route_topology_comfort_blocked_rollout_lateral"]
    if command_jerk:
        failures.append("route_topology_comfort_blocked_command_jerk")
    return {
        "snapshot_path": snapshot,
        "selection_step": 1,
        "candidate_index": 0,
        "hard_feasible": True,
        "progress_feasible": True,
        "comfort_admissible": False,
        "progress_loss_m": 1.25,
        "smoothness_loss": 0.5,
        "failure_classes": failures,
        "candidate_meta": {
            "red_stop_distance_partition": partition,
            "lateral_offset_scale": offset,
            "red_stop_margin_m": margin,
            "backup_stop_offset_m": backup,
            "current_tick_features_only": True,
        },
    }


def _screen_payload() -> dict[str, object]:
    row0 = _candidate_row(snapshot="/tmp/s0.npz", offset=0.0)
    row1 = _candidate_row(snapshot="/tmp/s0.npz", offset=1.0, command_jerk=False)
    row2 = _candidate_row(snapshot="/tmp/s1.npz", partition="near_stop", backup=1.0)
    return {
        "analysis": {
            "future_outcome_leakage": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "training": False,
        },
        "config": {
            "generator_policy": "negative_support_coverage_first_lane_projected_red_stop",
        },
        "records": {
            "snapshots": 2,
            "snapshots_with_generated_candidates": 2,
            "generated_candidate_rows": 3,
            "lower_union_red_rows": 3,
            "lower_union_red_hard_feasible_rows": 3,
            "lower_union_red_progress_feasible_rows": 3,
            "lower_union_red_comfort_admissible_rows": 0,
        },
        "support_gate": {
            "hard_feasible_snapshot_support_pass": True,
            "comfort_admissible_snapshot_support_pass": False,
            "hard_feasible_snapshot_support_rate": 1.0,
            "comfort_admissible_snapshot_support_rate": 0.0,
            "min_snapshot_support_rate": 0.25,
        },
        "final_decision": {"status": "route_topology_candidate_support_insufficient"},
        "progress_comfort_delta": {
            "command_jerk_worse_mps3": {"count": 3, "p50": 10.0, "p95": 20.0},
            "rollout_lateral_worse_mps2": {"count": 3, "p50": 1.0, "p95": 2.0},
        },
        "by_snapshot": [
            {
                "snapshot_path": "/tmp/s0.npz",
                "selection_step": 1,
                "failure_class_counts": {
                    "route_topology_comfort_blocked_command_jerk": 1,
                    "route_topology_comfort_blocked_rollout_lateral": 2,
                },
            },
            {
                "snapshot_path": "/tmp/s1.npz",
                "selection_step": 2,
                "failure_class_counts": {
                    "route_topology_comfort_blocked_command_jerk": 1,
                    "route_topology_comfort_blocked_rollout_lateral": 1,
                },
            },
        ],
        "rows": [
            {
                "snapshot_path": "/tmp/s0.npz",
                "candidate_rows": [row0, row1],
            },
            {
                "snapshot_path": "/tmp/s1.npz",
                "candidate_rows": [row2],
            },
        ],
    }


def _attribution_payload() -> dict[str, object]:
    return {
        "final_decision": {"passed": True, "failed_checks": []},
        "read_only_attribution": {
            "primary_blocker_family": "comfort_support_zero_after_hard_support_pass",
            "hard_support_positive": True,
            "comfort_support_positive": False,
            "positive_support_evidence": False,
            "replay_evidence_ready": False,
            "training_ready": False,
            "comfort_support_gap": 0.25,
            "comfort_blocker_ranking": [
                {"name": "route_topology_comfort_blocked_command_jerk", "count": 2}
            ],
        },
    }


def _plan_payload(*, no_dp_import: bool = True) -> dict[str, object]:
    return {
        "final_decision": {"passed": True},
        "diagnostic_implementation_plan": {
            "implementation_scope": {
                "planned_script": PLANNED_DIAGNOSTIC_SCRIPT,
                "planned_test": PLANNED_DIAGNOSTIC_TEST,
                "read_only_existing_artifacts": True,
                "no_candidate_reconstruction": True,
                "no_reward_recompute": True,
                "no_tracker_recompute": True,
                "no_dp_import": no_dp_import,
            },
            "required_tables": list(REQUIRED_TABLES),
        },
    }


def _static_review_payload(
    *,
    authorized_next_work: str = STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
    allowed_files: list[str] | None = None,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": STATIC_REVIEW_READY_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": authorized_next_work,
            "diagnostic_implementation_only_authorized": True,
            "next_gate_allowed_files": allowed_files
            if allowed_files is not None
            else [PLANNED_DIAGNOSTIC_SCRIPT, PLANNED_DIAGNOSTIC_TEST],
            "next_gate_implementation_code_edit_authorized": True,
            "production_implementation_edit_authorized": False,
            "candidate_generation_execution_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
        }
    }


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    screen_payload: dict[str, object] | None = None,
    attribution_payload: dict[str, object] | None = None,
    plan_payload: dict[str, object] | None = None,
    static_review_payload: dict[str, object] | None = None,
) -> tuple[Path, Path, Path, Path, Path]:
    audit = tmp_path / "audit.md"
    screen = tmp_path / "screen"
    attrib = tmp_path / "attrib"
    plan = tmp_path / "plan"
    review = tmp_path / "review"
    for root in (screen, attrib, plan, review):
        root.mkdir()
    audit.write_text(audit_text if audit_text is not None else _audit_text(), encoding="utf-8")
    (screen / SCREEN_JSON).write_text(
        json.dumps(screen_payload or _screen_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (attrib / ATTRIBUTION_JSON).write_text(
        json.dumps(attribution_payload or _attribution_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (plan / PLAN_JSON).write_text(
        json.dumps(plan_payload or _plan_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (review / STATIC_REVIEW_JSON).write_text(
        json.dumps(static_review_payload or _static_review_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return audit, screen, attrib, plan, review


def _build(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    screen_payload: dict[str, object] | None = None,
    attribution_payload: dict[str, object] | None = None,
    plan_payload: dict[str, object] | None = None,
    static_review_payload: dict[str, object] | None = None,
    dp_head: str = EXPECTED_DP_HEAD,
) -> dict:
    audit, screen, attrib, plan, review = _write_inputs(
        tmp_path,
        audit_text=audit_text,
        screen_payload=screen_payload,
        attribution_payload=attribution_payload,
        plan_payload=plan_payload,
        static_review_payload=static_review_payload,
    )
    return build_report(
        screen_root=screen,
        attribution_root=attrib,
        implementation_plan_root=plan,
        static_review_root=review,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=dp_head,
        label="unit",
    )


def test_residual_comfort_failure_diagnostics_reads_existing_artifacts_only(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_code_edit_authorized"] is True
    assert decision["production_implementation_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["analysis"]["candidate_generation_execution"] is False
    assert report["analysis"]["reward_recompute"] is False
    assert report["analysis"]["tracker_recompute"] is False


def test_residual_comfort_failure_diagnostics_emits_required_tables(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    tables = report["diagnostic_tables"]

    assert set(REQUIRED_TABLES).issubset(set(tables))
    assert tables["comfort_blocker_by_snapshot"]
    assert tables["comfort_blocker_by_red_stop_partition"]
    assert tables["comfort_blocker_by_offset_margin"]
    assert tables["hard_progress_survivor_distribution"]["hard_progress_survivor_rows"] == 3
    assert tables["diagnostic_decision_boundary"]["comfort_admissible_rows"] == 0
    assert tables["diagnostic_decision_boundary"]["training_ready"] is False


def test_residual_comfort_failure_diagnostics_rejects_missing_artifacts(
    tmp_path: Path,
) -> None:
    audit, screen, attrib, plan, review = _write_inputs(tmp_path)
    missing_screen = tmp_path / "missing_screen"
    report = build_report(
        screen_root=missing_screen,
        attribution_root=attrib,
        implementation_plan_root=plan,
        static_review_root=review,
        audit_path=audit,
        camp_head=CAMP_COMMIT,
        camp_origin_main=CAMP_COMMIT,
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "screen_root_exists" in report["final_decision"]["failed_checks"]
    assert "screen_json_exists" in report["final_decision"]["failed_checks"]


def test_residual_comfort_failure_diagnostics_blocks_execution_flags(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        static_review_payload=_static_review_payload(
            authorized_next_work="not_this_gate",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_authorizes_this_implementation" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_failure_diagnostics_preserves_math_boundary(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
    assert "no DP import" in markdown
    assert "candidate reconstruction" in markdown
    assert "formal seeds" in markdown
    assert "CAMP-over-DP-Top-1" in markdown


def test_residual_comfort_failure_diagnostics_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_residual_comfort_failure_diagnostics_rejects_unscoped_allowed_files(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        static_review_payload=_static_review_payload(allowed_files=["other.py"]),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_review_next_gate_scoped_files" in report["final_decision"][
        "failed_checks"
    ]


def test_residual_comfort_failure_diagnostics_rejects_plan_dp_import(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, plan_payload=_plan_payload(no_dp_import=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_no_dp_import" in report["final_decision"]["failed_checks"]


def test_residual_comfort_failure_diagnostics_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, screen, attrib, plan, review = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "diagnostics.json"
    output_md = tmp_path / "out" / "diagnostics.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "analyze",
            "--screen_root",
            str(screen),
            "--attribution_root",
            str(attrib),
            "--implementation_plan_root",
            str(plan),
            "--static_review_root",
            str(review),
            "--audit_path",
            str(audit),
            "--camp_head",
            CAMP_COMMIT,
            "--camp_origin_main",
            CAMP_COMMIT,
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Residual Comfort Failure Diagnostics" in markdown
