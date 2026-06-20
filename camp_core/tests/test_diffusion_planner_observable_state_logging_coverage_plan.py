from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_observable_state_logging_coverage import (
    CoveragePlanSpec,
    EvidenceRunSpec,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


def test_broader_observable_state_logging_plan_authorizes_exact_scope() -> None:
    report = build_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is True
    assert report["final_decision"]["full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used"] is False
    assert report["coverage_targets"]["planned_logs"] == 4
    assert report["coverage_targets"]["planned_records"] == 48
    assert report["coverage_targets"]["min_red_context_records"] == 1

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
    assert all("--camp_observable_state_logging" not in command for command in baseline_commands)
    assert all("--camp_observable_state_logging" in command for command in candidate_commands)
    assert {
        command[command.index("--traffic_lights") + 1]
        for command in candidate_commands
    } == {"on", "off"}
    assert {
        command[command.index("--max_npcs") + 1]
        for command in candidate_commands
    } == {"0", "4"}

    coverage_command = report["commands"]["payload_coverage_audit"]
    assert "--root" in coverage_command
    assert "--min_records_for_materiality" in coverage_command
    assert coverage_command[
        coverage_command.index("--min_records_for_materiality") + 1
    ] == "12"
    assert "--require_valid" in coverage_command


def test_broader_observable_state_logging_plan_rejects_missing_coverage_audit(
    tmp_path: Path,
) -> None:
    report = build_report(
        payload_coverage_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["closed_loop_replay_authorized"] is False
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == [
        "payload_coverage_audit_available"
    ]


def test_broader_observable_state_logging_plan_rejects_formal_seed() -> None:
    spec = CoveragePlanSpec(
        runs=(
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
            *CoveragePlanSpec().runs[1:],
        )
    )

    report = build_report(spec=spec)

    assert report["final_decision"]["status"] == REJECT_STATUS
    formal_check = next(
        check for check in report["plan_checks"] if check["name"] == "formal_seeds_excluded"
    )
    assert formal_check["passed"] is False


def test_broader_observable_state_logging_plan_rejects_missing_normal_context() -> None:
    base = CoveragePlanSpec()
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
    report = build_report(spec=replace(base, runs=runs))

    assert report["final_decision"]["status"] == REJECT_STATUS
    context_check = next(
        check
        for check in report["plan_checks"]
        if check["name"] == "scenario_buckets_cover_required_contexts"
    )
    assert context_check["passed"] is False
