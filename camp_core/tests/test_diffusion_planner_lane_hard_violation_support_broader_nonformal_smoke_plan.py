from __future__ import annotations

from pathlib import Path

from scripts.integrations.plan_diffusion_planner_lane_hard_violation_support_broader_nonformal_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
)


def _source_smoke(*, status: str = "lane_hard_violation_support_logging_smoke_passed") -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "lane_hard_violation_support_logging_smoke_passed",
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
        "latency_ms": {
            "latency_ms_lane_hard_violation_support_logging": 2.2,
        },
    }


def _selector_equivalence(*, equivalent: bool = True) -> dict:
    return {
        "equivalent": equivalent,
        "exact_field_mismatches": {
            "selected_index": 0,
            "feasible_mask": 0,
        },
        "numeric_field_mismatches": {
            "atoms": 0,
            "scores": 0,
        },
        "numeric_shape_mismatches": {
            "atoms": 0,
            "scores": 0,
        },
        "numeric_nonexact_entries": {
            "atoms": 0,
            "scores": 0,
        },
    }


def _dataset_audit(*, passed: bool = True) -> dict:
    return {"passed": passed}


def test_lane_hard_violation_broader_plan_ready_and_design_only() -> None:
    report = build_report(
        source_smoke_audit=_source_smoke(),
        source_selector_equivalence=_selector_equivalence(),
        source_dataset_audit=_dataset_audit(),
        label="unit",
    )

    decision = report["final_decision"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["paired_smoke_execution_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert decision["Full36_authorized"] is False
    assert decision["formal_seeds_authorized"] is False
    assert decision["CAMP_retraining_authorized"] is False
    assert report["coverage_targets"]["planned_logs"] == 4
    assert report["coverage_targets"]["planned_records"] == 48
    assert report["coverage_targets"]["planned_candidate_rows"] == 384
    buckets = report["coverage_targets"]["scenario_bucket_counts"]
    for bucket in (
        "traffic_light",
        "red_light_turn",
        "sharp_turn",
        "npc_interaction",
        "normal",
    ):
        assert buckets[bucket] > 0

    paired = report["commands"]["paired_replays"]
    assert len(paired) == 8
    baseline = [item for item in paired if item["variant"] == "baseline"]
    enabled = [item for item in paired if item["variant"] == "logging_enabled"]
    assert len(baseline) == len(enabled) == 4
    assert all(
        "--camp_lane_hard_violation_support_logging" not in item["command"]
        for item in baseline
    )
    assert all(
        "--camp_lane_hard_violation_support_logging" in item["command"]
        for item in enabled
    )


def test_lane_hard_violation_broader_plan_rejects_failed_source_smoke() -> None:
    report = build_report(
        source_smoke_audit=_source_smoke(
            status="lane_hard_violation_support_logging_smoke_rejected"
        ),
        source_selector_equivalence=_selector_equivalence(),
        source_dataset_audit=_dataset_audit(),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "source_smoke_passed" in failed


def test_lane_hard_violation_broader_plan_rejects_missing_payload_audit(
    tmp_path: Path,
) -> None:
    report = build_report(
        source_smoke_audit=_source_smoke(),
        source_selector_equivalence=_selector_equivalence(),
        source_dataset_audit=_dataset_audit(),
        payload_audit_source=tmp_path / "missing.py",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert "payload_audit_available" in failed
