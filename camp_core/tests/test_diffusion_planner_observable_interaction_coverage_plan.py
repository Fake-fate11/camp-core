from __future__ import annotations

from dataclasses import replace

from scripts.integrations.plan_diffusion_planner_observable_interaction_coverage import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    CoveragePlanSpec,
    EvidenceRunSpec,
    build_report,
)


def _bottleneck_source(
    *,
    status: str = "observable_interaction_descriptor_bottleneck_diagnosed",
    passed: bool = True,
    next_work: str = "predeclare_broader_nonformal_observable_interaction_coverage_plan_only",
) -> dict:
    return {
        "records": {
            "records": 48,
            "candidate_rows": 384,
            "alternative_rows": 336,
            "formal_seed_records": 0,
        },
        "payload_materiality": {
            "records_with_red_risk_candidate_variation": 0,
            "records_with_clearance_deficit_candidate_variation": 0,
        },
        "descriptor_diagnostics": {
            "collapsed_descriptors": [
                "red_aligned_stopline_proximity_hinge_v1",
                "clearance_progress_tradeoff_hinge_v1",
                "turn_lateral_clearance_context_hinge_v1",
            ],
            "varying_descriptors": [
                "top1_deviation_without_current_safety_gain_v1"
            ],
        },
        "diagnosis": {
            "missing_context_families": ["red_context", "clearance_context"],
        },
        "final_decision": {
            "status": status,
            "passed": passed,
            "primary_gap": (
                "interaction_descriptors_collapse_due_to_missing_context_variation"
            ),
            "authorized_next_work": next_work,
        },
    }


def test_observable_interaction_coverage_plan_authorizes_next_gate_only() -> None:
    report = build_report(bottleneck_report=_bottleneck_source(), label="unit")

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["paired_smoke_execution_authorized"] is False
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["classic_Benders_claim_authorized"] is False
    assert report["analysis"]["future_outcome_labels_used"] is False
    assert report["coverage_targets"]["planned_logs"] == 4
    assert report["coverage_targets"]["planned_records"] == 48
    assert report["coverage_targets"]["planned_candidate_rows"] == 384

    buckets = report["coverage_targets"]["scenario_bucket_counts"]
    assert buckets["red_light"] >= 1
    assert buckets["clearance"] >= 1
    assert buckets["turn_lateral"] >= 1
    assert buckets["normal_control"] >= 1

    context = report["coverage_targets"]["target_context_family_counts"]
    assert context["red_context"] >= 1
    assert context["clearance_context"] >= 1
    assert context["turn_lateral_context"] >= 1
    assert context["normal_control"] >= 1

    replay_commands = report["commands"]["paired_replays"]
    assert len(replay_commands) == 8
    baseline = [item for item in replay_commands if item["variant"] == "baseline"]
    logging = [
        item
        for item in replay_commands
        if item["variant"] == "observable_logging_enabled"
    ]
    assert len(baseline) == len(logging) == 4
    assert all("--camp_observable_state_logging" not in item["command"] for item in baseline)
    assert all("--camp_observable_state_logging" in item["command"] for item in logging)
    unsupported_runner_args = {
        "--camp_enable",
        "--camp_shadow_only",
        "--camp_emit_selection_log",
    }
    for item in replay_commands:
        assert unsupported_runner_args.isdisjoint(item["command"])
    followup = report["commands"]["required_followup_checks"]
    assert "selector_equivalence_contract" in followup
    assert "observable_interaction_coverage_contract" in followup
    assert all(
        "scripts/integrations/analyze_diffusion_planner_selector_log_equivalence.py"
        not in " ".join(items)
        for items in followup.values()
    )


def test_observable_interaction_coverage_plan_blocks_invalid_source() -> None:
    report = build_report(
        bottleneck_report=_bottleneck_source(
            status="observable_interaction_descriptor_bottleneck_source_not_rejected",
            passed=False,
            next_work="fix_interaction_separability_source_before_bottleneck",
        )
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["source_bottleneck_gate_authorizes_plan_only"]


def test_observable_interaction_coverage_plan_rejects_formal_seed() -> None:
    base = CoveragePlanSpec()
    report = build_report(
        bottleneck_report=_bottleneck_source(),
        spec=replace(
            base,
            runs=(
                replace(base.runs[0], seed=11),
                *base.runs[1:],
            ),
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    formal_check = next(
        check for check in report["plan_checks"] if check["name"] == "formal_seeds_excluded"
    )
    assert formal_check["passed"] is False


def test_observable_interaction_coverage_plan_rejects_missing_normal_control() -> None:
    base = CoveragePlanSpec()
    runs = tuple(
        run
        for run in base.runs
        if "normal_control" not in run.target_context_families
    )
    report = build_report(
        bottleneck_report=_bottleneck_source(),
        spec=replace(base, runs=runs),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    context_check = next(
        check
        for check in report["plan_checks"]
        if check["name"] == "target_context_families_covered"
    )
    assert context_check["passed"] is False


def test_observable_interaction_coverage_plan_rejects_missing_clearance_target() -> None:
    base = CoveragePlanSpec()
    runs = tuple(
        replace(
            run,
            scenario_buckets=tuple(
                bucket for bucket in run.scenario_buckets if bucket != "clearance"
            ),
            target_context_families=tuple(
                family
                for family in run.target_context_families
                if family != "clearance_context"
            ),
            expected_descriptor_targets=tuple(
                target
                for target in run.expected_descriptor_targets
                if target != "clearance_progress_tradeoff_hinge_v1"
            ),
        )
        for run in base.runs
    )
    report = build_report(
        bottleneck_report=_bottleneck_source(),
        spec=replace(base, runs=runs),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    descriptor_check = next(
        check
        for check in report["plan_checks"]
        if check["name"] == "collapsed_descriptor_targets_revisited"
    )
    assert descriptor_check["passed"] is False
