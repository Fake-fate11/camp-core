from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_support_route_projection_optimization import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    EquivalenceCaseSpec,
    OptimizationPlanSpec,
    build_report,
)


def _benchmark(
    *,
    status: str = "progress_support_component_microbenchmark_synthetic_completed",
    passed: bool = True,
    dominant: str = "latency_ms_progress_support_route_projection",
    route_projection_p95: float = 100.0,
    next_component_p95: float = 0.05,
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
            "dominant_component_by_max_case_p95": {
                "field": dominant,
                "max_case_p95_ms": route_projection_p95,
            },
            "latency_ms_progress_support_route_projection": {
                "max_case_p95_ms": route_projection_p95,
            },
            "latency_ms_progress_support_plan_arc": {
                "max_case_p95_ms": next_component_p95,
            },
        },
        "cases": [
            {
                "name": "unit_case",
                "dominant_component": {
                    "field": dominant,
                    "p95_ms": route_projection_p95,
                },
            }
        ],
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _helper_source(
    tmp_path: Path,
    *,
    omit_token: str | None = None,
) -> Path:
    tokens = [
        "def _route_progress_profiles(",
        "for cand_idx in range(candidates_xy.shape[0]):",
        "for step_idx in range(candidates_xy.shape[1]):",
        "for seg_idx, segment in enumerate(segments):",
        "if distance < best_distance:",
        "profiles[cand_idx, step_idx] = best_s",
    ]
    path = tmp_path / "diffusion_planner_progress_support.py"
    path.write_text(
        "\n".join(token for token in tokens if token != omit_token),
        encoding="utf-8",
    )
    return path


def test_route_projection_optimization_plan_ready(tmp_path: Path) -> None:
    report = build_report(
        benchmark_json=_write_json(tmp_path / "benchmark.json", _benchmark()),
        helper_source=_helper_source(tmp_path),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["optimization_implementation_authorized"] is False
    assert report["final_decision"]["replay_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["DP_modification_authorized"] is False
    assert report["analysis"]["diffusion_planner_execution"] is False
    assert report["analysis"]["optimization_implementation"] is False
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])
    assert any(
        "strictly smaller" in item
        for item in report["optimization_plan"]["algorithm"]
    )
    assert any(
        "fail-closed" in item
        for item in report["optimization_plan"]["exact_equivalence_criteria"]
    )


def test_route_projection_optimization_plan_rejects_bad_source_status(
    tmp_path: Path,
) -> None:
    report = build_report(
        benchmark_json=_write_json(
            tmp_path / "benchmark.json",
            _benchmark(status="progress_support_component_microbenchmark_synthetic_rejected"),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["synthetic_benchmark_completed"]


def test_route_projection_optimization_plan_requires_route_projection_dominance(
    tmp_path: Path,
) -> None:
    report = build_report(
        benchmark_json=_write_json(
            tmp_path / "benchmark.json",
            _benchmark(dominant="latency_ms_progress_support_atom_compute"),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "aggregate_dominant_component_is_route_projection",
        "all_cases_route_projection_dominant",
    ]


def test_route_projection_optimization_plan_requires_dominance_margin(
    tmp_path: Path,
) -> None:
    report = build_report(
        benchmark_json=_write_json(
            tmp_path / "benchmark.json",
            _benchmark(route_projection_p95=10.0, next_component_p95=0.02),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["route_projection_dominance_margin_present"]


def test_route_projection_optimization_plan_rejects_forbidden_source_scope(
    tmp_path: Path,
) -> None:
    report = build_report(
        benchmark_json=_write_json(
            tmp_path / "benchmark.json",
            _benchmark(final_updates={"optimization_authorized": True}),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["benchmark_blocks_replay_training_dp_and_optimization"]


def test_route_projection_optimization_plan_requires_reference_loop_source(
    tmp_path: Path,
) -> None:
    report = build_report(
        benchmark_json=_write_json(tmp_path / "benchmark.json", _benchmark()),
        helper_source=_helper_source(
            tmp_path,
            omit_token="if distance < best_distance:",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == [
        "helper_has_reference_route_projection_loop"
    ]
    assert failed[0]["missing_tokens"] == ["if distance < best_distance:"]


def test_route_projection_optimization_plan_requires_stress_and_fail_closed_cases(
    tmp_path: Path,
) -> None:
    spec = OptimizationPlanSpec(
        cases=(
            EquivalenceCaseSpec(
                name="short_only",
                candidate_count=8,
                support_steps=10,
                route_points=256,
                route_shape="straight",
            ),
        )
    )

    report = build_report(
        benchmark_json=_write_json(tmp_path / "benchmark.json", _benchmark()),
        helper_source=_helper_source(tmp_path),
        spec=spec,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["stress_and_fail_closed_cases_present"]
