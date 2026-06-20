from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from camp_core.integrations.diffusion_planner_progress_support import (
    PROGRESS_SUPPORT_LATENCY_KEYS,
    build_progress_support_logging_payload,
)
from scripts.integrations.benchmark_diffusion_planner_progress_support_component_microbenchmark import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    BenchmarkCaseSpec,
    MicrobenchmarkSpec,
    _synthetic_current_tick,
    build_report,
)
from scripts.integrations.plan_diffusion_planner_progress_support_component_microbenchmark import (
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
)


def _plan(
    *,
    status: str = PLAN_READY_STATUS,
    passed: bool = True,
    authorized_next_work: str | None = PLAN_AUTHORIZED_NEXT_WORK,
    analysis_updates: dict | None = None,
    final_updates: dict | None = None,
) -> dict:
    spec = MicrobenchmarkSpec(
        cpu_warmups=1,
        cpu_repetitions=2,
        cases=(
            BenchmarkCaseSpec(
                name="unit_straight",
                candidate_count=2,
                support_steps=4,
                route_points=16,
                route_shape="straight",
            ),
        ),
    )
    analysis = {
        "diffusion_planner_execution": False,
        "training": False,
        "future_outcome_labels_used": False,
    }
    if analysis_updates:
        analysis.update(analysis_updates)
    final = {
        "status": status,
        "passed": passed,
        "authorized_next_work": authorized_next_work,
        "replay_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "CAMP_retraining_authorized": False,
        "DP_modification_authorized": False,
    }
    if final_updates:
        final.update(final_updates)
    return {
        "analysis": analysis,
        "final_decision": final,
        "microbenchmark_spec": {
            **asdict(spec),
            "cases": [asdict(case) for case in spec.cases],
        },
    }


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_progress_support_component_microbenchmark_ready(tmp_path: Path) -> None:
    report = build_report(
        plan_json=_write_json(tmp_path / "plan.json", _plan()),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["replay_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["DP_modification_authorized"] is False
    assert report["analysis"]["diffusion_planner_execution"] is False
    assert report["analysis"]["training"] is False
    assert len(report["cases"]) == 1
    case = report["cases"][0]
    assert case["passed"] is True
    assert case["dimensions"]["candidates"] == [2, 4, 2]
    assert case["dimensions"]["route_centerline_ego"] == [16, 2]
    assert set(case["latency"]) == set(PROGRESS_SUPPORT_LATENCY_KEYS)
    assert all(
        values["stats"]["count"] == 2
        for values in case["latency"].values()
    )
    assert "dominant_component_by_max_case_p95" in report["aggregate"]


def test_progress_support_component_microbenchmark_rejects_bad_source_without_execution(
    tmp_path: Path,
) -> None:
    def _raise_if_called(**_kwargs):
        raise AssertionError("payload builder must not execute")

    report = build_report(
        plan_json=_write_json(
            tmp_path / "plan.json",
            _plan(status="progress_support_component_microbenchmark_plan_rejected"),
        ),
        payload_builder=_raise_if_called,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["cases"] == []
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["plan_ready"]


def test_progress_support_component_microbenchmark_rejects_forbidden_scope(
    tmp_path: Path,
) -> None:
    def _raise_if_called(**_kwargs):
        raise AssertionError("payload builder must not execute")

    report = build_report(
        plan_json=_write_json(
            tmp_path / "plan.json",
            _plan(
                analysis_updates={"diffusion_planner_execution": True},
                final_updates={"formal_seeds_authorized": True},
            ),
        ),
        payload_builder=_raise_if_called,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert report["cases"] == []
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == [
        "plan_blocks_replay_training_and_dp_modification",
        "plan_declares_no_dp_execution_or_training",
    ]


def test_progress_support_component_microbenchmark_rejects_missing_latency_key(
    tmp_path: Path,
) -> None:
    def _missing_route_projection(**kwargs):
        payload = build_progress_support_logging_payload(**kwargs)
        payload["latency_ms"].pop("latency_ms_progress_support_route_projection")
        return payload

    report = build_report(
        plan_json=_write_json(tmp_path / "plan.json", _plan()),
        payload_builder=_missing_route_projection,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [
        check
        for check in report["cases"][0]["checks"]
        if check["name"] == "latency_keys_exact" and not check["passed"]
    ]
    assert failed
    assert failed[0]["missing"] == ["latency_ms_progress_support_route_projection"]


def test_progress_support_component_microbenchmark_rejects_equivalence_drift(
    tmp_path: Path,
) -> None:
    call_count = 0

    def _drifting_payload(**kwargs):
        nonlocal call_count
        call_count += 1
        payload = build_progress_support_logging_payload(**kwargs)
        if call_count > 1:
            payload["candidate_count"] += 1
        return payload

    report = build_report(
        plan_json=_write_json(tmp_path / "plan.json", _plan()),
        payload_builder=_drifting_payload,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [
        check
        for check in report["cases"][0]["checks"]
        if check["name"] == "payload_equivalence_without_latency"
        and not check["passed"]
    ]
    assert failed
    assert failed[0]["error"] == "max_abs_numeric_difference exceeds tolerance"
    assert failed[0]["max_abs_numeric_difference"] > failed[0]["tolerance"]


def test_progress_support_synthetic_current_tick_shapes() -> None:
    candidates, route = _synthetic_current_tick(
        BenchmarkCaseSpec(
            name="shape_check",
            candidate_count=3,
            support_steps=5,
            route_points=64,
            route_shape="sine",
        )
    )

    assert candidates.shape == (3, 5, 2)
    assert route.shape == (64, 2)
