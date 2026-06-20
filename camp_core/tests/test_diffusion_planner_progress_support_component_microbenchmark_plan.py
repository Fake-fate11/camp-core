from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_progress_support_component_microbenchmark import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    BenchmarkCaseSpec,
    MicrobenchmarkSpec,
    build_report,
)


def _diagnosis_plan(
    *,
    status: str = "progress_support_latency_diagnosis_plan_ready",
    passed: bool = True,
    hypothesis: str = "route_projection_nested_loop_dominates_latency",
) -> dict:
    return {
        "dominant_hypothesis": {
            "name": hypothesis,
        },
        "final_decision": {
            "status": status,
            "passed": passed,
            "replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
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
        "PROGRESS_SUPPORT_LATENCY_KEYS",
        "latency_ms_progress_support_route_projection",
        "latency_ms_progress_support_plan_arc",
        "latency_ms_progress_support_speed_profile",
        "latency_ms_progress_support_route_remaining",
        "latency_ms_progress_support_goal_alignment",
        "latency_ms_progress_support_atom_compute",
        "latency_ms_progress_support_payload_serialization",
        "def build_progress_support_logging_payload(",
        "progress_support_atoms",
        "progress_support_atom_names",
        "finite_checks",
        "score_k(w)=a_k^T w",
    ]
    path = tmp_path / "diffusion_planner_progress_support.py"
    path.write_text(
        "\n".join(token for token in tokens if token != omit_token),
        encoding="utf-8",
    )
    return path


def test_progress_support_component_microbenchmark_plan_ready(
    tmp_path: Path,
) -> None:
    report = build_report(
        diagnosis_plan_json=_write_json(tmp_path / "diagnosis.json", _diagnosis_plan()),
        helper_source=_helper_source(tmp_path),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["microbenchmark_execution_authorized"] is False
    assert report["final_decision"]["replay_authorized"] is False
    assert report["final_decision"]["Full36_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["DP_modification_authorized"] is False
    assert report["analysis"]["training"] is False
    assert report["analysis"]["diffusion_planner_execution"] is False
    assert report["blocked_actions"]["run_microbenchmark_now"] is True
    assert all(check["passed"] for check in report["source_checks"])
    assert all(check["passed"] for check in report["plan_checks"])
    assert any(
        case["name"] == "long_route_projection_stress"
        and case["route_points"] >= 2048
        for case in report["microbenchmark_spec"]["cases"]
    )
    assert any(
        item["field"] == "latency_ms_progress_support_route_projection"
        and item["role"] == "expected_dominant_component"
        for item in report["planned_measurements"]
    )
    assert any(
        "no Diffusion Planner import" in item
        for item in report["exact_equivalence_criteria"]
    )


def test_progress_support_component_microbenchmark_rejects_bad_source_status(
    tmp_path: Path,
) -> None:
    report = build_report(
        diagnosis_plan_json=_write_json(
            tmp_path / "diagnosis.json",
            _diagnosis_plan(status="progress_support_latency_diagnosis_plan_rejected"),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["latency_diagnosis_plan_ready"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_progress_support_component_microbenchmark_requires_route_projection_hypothesis(
    tmp_path: Path,
) -> None:
    report = build_report(
        diagnosis_plan_json=_write_json(
            tmp_path / "diagnosis.json",
            _diagnosis_plan(hypothesis="payload_serialization_dominates_latency"),
        ),
        helper_source=_helper_source(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["diagnosis_identifies_route_projection"]


def test_progress_support_component_microbenchmark_requires_component_latency_keys(
    tmp_path: Path,
) -> None:
    report = build_report(
        diagnosis_plan_json=_write_json(tmp_path / "diagnosis.json", _diagnosis_plan()),
        helper_source=_helper_source(
            tmp_path,
            omit_token="latency_ms_progress_support_route_projection",
        ),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check for check in report["source_checks"] if not check["passed"]]
    assert [check["name"] for check in failed] == [
        "helper_exports_component_latency_keys"
    ]
    assert failed[0]["missing_tokens"] == [
        "latency_ms_progress_support_route_projection"
    ]


def test_progress_support_component_microbenchmark_requires_route_stress_case(
    tmp_path: Path,
) -> None:
    spec = MicrobenchmarkSpec(
        cases=(
            BenchmarkCaseSpec(
                name="short_route_only",
                candidate_count=8,
                support_steps=10,
                route_points=512,
                route_shape="sine",
            ),
        )
    )

    report = build_report(
        diagnosis_plan_json=_write_json(tmp_path / "diagnosis.json", _diagnosis_plan()),
        helper_source=_helper_source(tmp_path),
        spec=spec,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["plan_checks"] if not check["passed"]]
    assert failed == ["route_projection_stress_case_present"]
