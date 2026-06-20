from __future__ import annotations

from dataclasses import replace

from scripts.integrations.plan_diffusion_planner_progress_support_broader_nonformal_smoke import (
    AUTHORIZED_NEXT_WORK,
    BroaderSmokeSpec,
    EvidenceRunSpec,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    render_markdown,
)


def _optimized_smoke(*, passed: bool = True, logging_ms: float = 2.4) -> dict:
    return {
        "final_decision": {
            "status": (
                "progress_support_logging_smoke_passed"
                if passed
                else "progress_support_logging_smoke_rejected"
            ),
            "passed": passed,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
        "latency_ms": {
            "latency_ms_progress_support_logging": logging_ms,
            "latency_ms_progress_support_route_projection": 2.2,
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
        optimized_smoke_audit=kwargs.pop("optimized_smoke", _optimized_smoke()),
        optimized_selector_equivalence=kwargs.pop(
            "selector_equivalence",
            _selector_equivalence(),
        ),
        optimized_dataset_audit=kwargs.pop("dataset_audit", _dataset_audit()),
        **kwargs,
    )


def test_broader_progress_support_plan_ready_for_exact_next_scope() -> None:
    report = _ready_report(label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["paired_smoke_execution_authorized"] is False
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["DP_modification_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used"] is False
    assert report["coverage_targets"]["planned_logs"] == 4
    assert report["coverage_targets"]["planned_records"] == 48
    assert report["coverage_targets"]["planned_candidate_rows"] == 384
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])

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
    assert all("--camp_progress_support_logging" not in command for command in baseline_commands)
    assert all("--camp_progress_support_logging" in command for command in candidate_commands)
    assert {
        command[command.index("--traffic_lights") + 1]
        for command in candidate_commands
    } == {"on", "off"}
    assert {
        command[command.index("--max_npcs") + 1]
        for command in candidate_commands
    } == {"0", "4"}

    payload_audit = report["commands"]["payload_audit"]
    assert payload_audit[payload_audit.index("--expected_logs") + 1] == "4"
    assert payload_audit[payload_audit.index("--expected_records") + 1] == "12"
    assert "--require_pass" in payload_audit

    dataset_audit = report["commands"]["dataset_audit"]
    assert "--root" in dataset_audit
    assert "--require_finite_candidate_contract" in dataset_audit
    assert dataset_audit[dataset_audit.index("--expected_logs") + 1] == "4"

    markdown = render_markdown(report)
    assert "\n+  " not in markdown
    assert "PYTHONPATH=/root/autodl-tmp/camp_core" in markdown


def test_broader_progress_support_plan_rejects_latency_blocked_source() -> None:
    report = _ready_report(optimized_smoke=_optimized_smoke(logging_ms=42.0))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["optimized_logging_latency_within_source_budget"]


def test_broader_progress_support_plan_rejects_selector_mismatch() -> None:
    report = _ready_report(
        selector_equivalence=_selector_equivalence(equivalent=False, mismatches=1)
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["optimized_selector_exact_equivalence"]


def test_broader_progress_support_plan_rejects_dataset_failure() -> None:
    report = _ready_report(dataset_audit=_dataset_audit(passed=False))

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["optimized_dataset_audit_passed"]


def test_broader_progress_support_plan_rejects_formal_seed() -> None:
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


def test_broader_progress_support_plan_rejects_missing_normal_context() -> None:
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
