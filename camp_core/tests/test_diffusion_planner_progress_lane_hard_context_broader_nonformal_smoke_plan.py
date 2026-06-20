from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_lane_hard_context_broader_nonformal_smoke import (
    AUTHORIZED_NEXT_WORK,
    BroaderSmokeSpec,
    EvidenceRunSpec,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    render_markdown,
)


def _coverage_audit(
    *,
    status: str = "progress_lane_hard_context_payload_coverage_insufficient_for_materiality",
    logging_ms: float = 3.8,
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "primary_gap": "too_few_logged_records_for_materiality",
            "authorized_next_work": "progress_lane_hard_context_broader_nonformal_plan_only",
            "materiality_gate_passed": False,
        },
        "validation": {"errors": [], "warnings": []},
        "context": {"context_records": 3},
        "material_atom_fields": [
            "curvature_conditioned_lateral_rate_excess_v1",
            "heading_curvature_residual_v1",
        ],
        "latency_ms": {
            "latency_ms_progress_lane_hard_context_logging": {
                "max_ms": logging_ms,
            },
        },
    }


def _source_smoke(*, passed: bool = True, logging_ms: float = 3.8) -> dict:
    return {
        "final_decision": {
            "status": (
                "progress_lane_hard_context_logging_smoke_passed"
                if passed
                else "progress_lane_hard_context_logging_smoke_rejected"
            ),
            "passed": passed,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
        "latency_ms": {
            "latency_ms_progress_lane_hard_context_logging": logging_ms,
        },
    }


def _selector_equivalence(*, equivalent: bool = True, mismatches: int = 0) -> dict:
    return {
        "equivalent": equivalent,
        "exact_field_mismatches": {"selected_index": mismatches},
        "numeric_field_mismatches": {"atoms": 0},
        "numeric_shape_mismatches": {"atoms": 0},
        "numeric_nonexact_entries": {"atoms": 0},
    }


def _dataset_audit(*, passed: bool = True) -> dict:
    return {"passed": passed}


def _ready_report(**kwargs) -> dict:
    return build_report(
        source_coverage_audit=kwargs.pop("coverage_audit", _coverage_audit()),
        source_smoke_audit=kwargs.pop("source_smoke", _source_smoke()),
        source_selector_equivalence=kwargs.pop(
            "selector_equivalence",
            _selector_equivalence(),
        ),
        source_dataset_audit=kwargs.pop("dataset_audit", _dataset_audit()),
        **kwargs,
    )


def test_broader_context_plan_ready_for_exact_next_scope() -> None:
    report = _ready_report(label="unit")

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["paired_smoke_execution_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["Full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["CAMP_retraining_authorized"] is False
    assert decision["DP_modification_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used"] is False
    assert report["coverage_targets"]["planned_logs"] == 4
    assert report["coverage_targets"]["planned_records"] == 48
    assert report["coverage_targets"]["planned_candidate_rows"] == 384

    replay_commands = report["commands"]["paired_replays"]
    assert len(replay_commands) == 8
    baseline_commands = [
        item["command"] for item in replay_commands if item["variant"] == "baseline"
    ]
    candidate_commands = [
        item["command"]
        for item in replay_commands
        if item["variant"] == "logging_enabled"
    ]
    assert all(
        "--camp_progress_lane_hard_context_logging" not in command
        for command in baseline_commands
    )
    assert all(
        "--camp_progress_lane_hard_context_logging" in command
        for command in candidate_commands
    )
    assert {
        command[command.index("--traffic_lights") + 1]
        for command in candidate_commands
    } == {"on", "off"}
    assert {
        command[command.index("--max_npcs") + 1]
        for command in candidate_commands
    } == {"0", "4"}

    coverage_command = report["commands"]["payload_coverage_audit"]
    assert coverage_command[coverage_command.index("--min_records_for_materiality") + 1] == "12"
    assert coverage_command[coverage_command.index("--min_material_atom_fields") + 1] == "2"
    assert "--require_valid" in coverage_command

    markdown = render_markdown(report)
    assert "\n+  " not in markdown
    assert "PYTHONPATH=/root/autodl-tmp/camp_core" in markdown


def test_broader_context_plan_rejects_latency_blocked_source() -> None:
    report = _ready_report(source_smoke=_source_smoke(logging_ms=42.0))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["source_logging_latency_within_budget"]


def test_broader_context_plan_rejects_selector_mismatch() -> None:
    report = _ready_report(
        selector_equivalence=_selector_equivalence(equivalent=False, mismatches=1)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["source_selector_exact_equivalence"]


def test_broader_context_plan_rejects_dataset_failure() -> None:
    report = _ready_report(dataset_audit=_dataset_audit(passed=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["source_dataset_audit_passed"]


def test_broader_context_plan_rejects_missing_coverage_audit_source(
    tmp_path: Path,
) -> None:
    report = _ready_report(
        payload_coverage_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "payload_coverage_audit_available" in failed


def test_broader_context_plan_rejects_formal_seed() -> None:
    base = BroaderSmokeSpec()
    runs = (
        EvidenceRunSpec(
            run_id="formal_seed",
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            seed=11,
            max_npcs=0,
            spawn_probability=0.3,
            traffic_lights="on",
            scenario_buckets=("traffic_light", "red_light_turn", "sharp_turn"),
        ),
        *base.runs[1:],
    )

    report = _ready_report(spec=replace(base, runs=runs))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["formal_seeds_excluded"]


def test_broader_context_plan_rejects_missing_normal_context() -> None:
    base = BroaderSmokeSpec()
    runs = tuple(
        replace(
            run,
            route_name="sample_map_tl_route_59_to_86",
            route="/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl",
            scenario_buckets=tuple(
                bucket for bucket in run.scenario_buckets if bucket != "normal"
            )
            or ("sharp_turn",),
        )
        for run in base.runs
    )

    report = _ready_report(spec=replace(base, runs=runs))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == [
        "red_turn_and_normal_routes_covered",
        "scenario_buckets_cover_required_contexts",
    ]
