from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_support_optimized_nonformal_smoke import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    SmokeSpec,
    build_report,
)


def _optimized_benchmark(
    *,
    status: str = "progress_support_component_microbenchmark_synthetic_completed",
    passed: bool = True,
    total_p95: float = 12.0,
    route_p95: float = 11.8,
    final_updates: dict | None = None,
) -> dict:
    final = {
        "status": status,
        "passed": passed,
        "replay_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "CAMP_retraining_authorized": False,
        "DP_modification_authorized": False,
        "optimization_authorized": False,
    }
    if final_updates:
        final.update(final_updates)
    return {
        "final_decision": final,
        "aggregate": {
            "latency_ms_progress_support_logging": {
                "max_case_p95_ms": total_p95,
            },
            "latency_ms_progress_support_route_projection": {
                "max_case_p95_ms": route_p95,
            },
        },
        "cases": [
            {
                "name": "unit_case",
                "passed": True,
                "checks": [
                    {"name": "payload_equivalence_without_latency", "passed": True}
                ],
            }
        ],
    }


def _previous_smoke(
    *,
    status: str = "progress_support_logging_smoke_passed",
    passed: bool = True,
    max_latency: float = 142.0,
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
        },
        "latency_ms": {
            "latency_ms_progress_support_logging": max_latency,
        },
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_optimized_nonformal_smoke_plan_ready(tmp_path: Path) -> None:
    report = build_report(
        optimized_benchmark_json=_write_json(
            tmp_path / "optimized.json",
            _optimized_benchmark(),
        ),
        previous_smoke_audit_json=_write_json(
            tmp_path / "previous.json",
            _previous_smoke(),
        ),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["paired_smoke_execution_authorized"] is False
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["DP_modification_authorized"] is False
    assert report["blocked_actions"]["run_replay_now"] is True
    assert report["comparison"]["comparison_is_cross_context"] is True
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])

    baseline = report["commands"]["baseline_replay"]
    candidate = report["commands"]["candidate_replay"]
    assert "--camp_progress_support_logging" not in baseline
    assert "--camp_progress_support_logging" in candidate
    assert baseline[baseline.index("--steps") + 1] == "3"
    assert candidate[candidate.index("--seed") + 1] == "1"
    assert "optimized" in report["smoke_spec"]["root"]


def test_optimized_nonformal_smoke_plan_rejects_failed_optimized_benchmark(
    tmp_path: Path,
) -> None:
    report = build_report(
        optimized_benchmark_json=_write_json(
            tmp_path / "optimized.json",
            _optimized_benchmark(
                status="progress_support_component_microbenchmark_synthetic_rejected",
                passed=False,
            ),
        ),
        previous_smoke_audit_json=_write_json(
            tmp_path / "previous.json",
            _previous_smoke(),
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["final_decision"]["authorized_next_work"] is None
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["optimized_synthetic_benchmark_completed"]


def test_optimized_nonformal_smoke_plan_rejects_optimized_latency_above_threshold(
    tmp_path: Path,
) -> None:
    report = build_report(
        optimized_benchmark_json=_write_json(
            tmp_path / "optimized.json",
            _optimized_benchmark(total_p95=40.0, route_p95=30.0),
        ),
        previous_smoke_audit_json=_write_json(
            tmp_path / "previous.json",
            _previous_smoke(),
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "optimized_total_logging_p95_below_design_threshold",
        "optimized_route_projection_p95_below_design_threshold",
        "synthetic_improvement_large_enough_to_plan_smoke",
    ]


def test_optimized_nonformal_smoke_plan_requires_previous_latency_block(
    tmp_path: Path,
) -> None:
    report = build_report(
        optimized_benchmark_json=_write_json(
            tmp_path / "optimized.json",
            _optimized_benchmark(),
        ),
        previous_smoke_audit_json=_write_json(
            tmp_path / "previous.json",
            _previous_smoke(max_latency=40.0),
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "previous_smoke_passed_but_latency_blocked",
        "synthetic_improvement_large_enough_to_plan_smoke",
    ]


def test_optimized_nonformal_smoke_plan_rejects_forbidden_source_scope(
    tmp_path: Path,
) -> None:
    report = build_report(
        optimized_benchmark_json=_write_json(
            tmp_path / "optimized.json",
            _optimized_benchmark(final_updates={"DP_modification_authorized": True}),
        ),
        previous_smoke_audit_json=_write_json(
            tmp_path / "previous.json",
            _previous_smoke(),
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["optimized_benchmark_blocks_replay_training_dp_and_promotion"]


def test_optimized_nonformal_smoke_plan_rejects_formal_seed_scope(
    tmp_path: Path,
) -> None:
    smoke = SmokeSpec(seed=11)

    report = build_report(
        optimized_benchmark_json=_write_json(
            tmp_path / "optimized.json",
            _optimized_benchmark(),
        ),
        previous_smoke_audit_json=_write_json(
            tmp_path / "previous.json",
            _previous_smoke(),
        ),
        smoke=smoke,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["nonformal_seed", "optimized_root_is_distinct"]
