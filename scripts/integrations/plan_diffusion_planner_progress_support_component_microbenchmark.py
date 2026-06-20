#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HELPER_SOURCE = (
    ROOT / "camp_core/camp_core/integrations/diffusion_planner_progress_support.py"
)

READY_STATUS = "progress_support_component_microbenchmark_plan_ready"
REJECT_STATUS = "progress_support_component_microbenchmark_plan_rejected"
SOURCE_STATUS = "progress_support_latency_component_instrumentation_unit_tested"
AUTHORIZED_NEXT_WORK = (
    "progress_support_component_microbenchmark_implementation_unit_tests_only"
)


@dataclass(frozen=True)
class BenchmarkCaseSpec:
    name: str
    candidate_count: int
    support_steps: int
    route_points: int
    route_shape: str


@dataclass(frozen=True)
class MicrobenchmarkSpec:
    root: str = "/root/autodl-tmp/camp_dp_progress_support_component_microbenchmark"
    cpu_warmups: int = 20
    cpu_repetitions: int = 100
    exact_equivalence_atol: float = 1e-9
    exact_equivalence_rtol: float = 1e-9
    cases: tuple[BenchmarkCaseSpec, ...] = (
        BenchmarkCaseSpec(
            name="smoke_like_straight",
            candidate_count=8,
            support_steps=10,
            route_points=256,
            route_shape="straight",
        ),
        BenchmarkCaseSpec(
            name="curved_route",
            candidate_count=8,
            support_steps=10,
            route_points=512,
            route_shape="sine",
        ),
        BenchmarkCaseSpec(
            name="long_route_projection_stress",
            candidate_count=8,
            support_steps=10,
            route_points=2048,
            route_shape="sine",
        ),
        BenchmarkCaseSpec(
            name="candidate_scale_stress",
            candidate_count=32,
            support_steps=10,
            route_points=512,
            route_shape="straight",
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for a progress-support component microbenchmark. "
            "It predeclares deterministic benchmark cases and exact-equivalence "
            "criteria, but does not run benchmark timings or replay."
        )
    )
    parser.add_argument("--diagnosis_plan_json", type=Path, required=True)
    parser.add_argument("--helper_source", type=Path, default=HELPER_SOURCE)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        diagnosis_plan_json=args.diagnosis_plan_json,
        helper_source=args.helper_source,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def build_report(
    *,
    diagnosis_plan_json: Path,
    helper_source: Path = HELPER_SOURCE,
    label: str | None = None,
    spec: MicrobenchmarkSpec = MicrobenchmarkSpec(),
) -> dict[str, Any]:
    diagnosis = _read_json(diagnosis_plan_json)
    helper_text = _read_text(helper_source)
    source_checks = _source_checks(
        diagnosis=diagnosis,
        helper_text=helper_text,
        spec=spec,
    )
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_progress_support_component_microbenchmark_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay_authorized": False,
            "microbenchmark_execution_authorized": False,
            "future_outcome_labels_used": False,
            "math_boundary": (
                "The planned benchmark measures existing progress-support "
                "logging code on deterministic current-tick synthetic arrays. "
                "It must not read closed-loop outcomes, run Diffusion Planner, "
                "or change CAMP scoring. Logged progress-support atoms remain "
                "fixed finite-candidate coefficients a_k, preserving affine "
                "score_k(w)=a_k^T w and the simplex/CVaR/L2 convex master."
            ),
        },
        "source": {
            "diagnosis_plan_json": str(diagnosis_plan_json),
            "helper_source": str(helper_source),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "microbenchmark_spec": {
            **asdict(spec),
            "cases": [asdict(case) for case in spec.cases],
        },
        "planned_measurements": _planned_measurements(),
        "exact_equivalence_criteria": _exact_equivalence_criteria(spec),
        "accept_criteria": _accept_criteria(),
        "reject_criteria": _reject_criteria(),
        "blocked_actions": {
            "run_microbenchmark_now": True,
            "new_replay": True,
            "broader_replay": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
            "optimization_implementation": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "microbenchmark_execution_authorized": False,
            "replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
        },
    }


def _source_checks(
    *,
    diagnosis: dict[str, Any],
    helper_text: str | None,
    spec: MicrobenchmarkSpec,
) -> list[dict[str, Any]]:
    final = diagnosis.get("final_decision", {})
    hypothesis = diagnosis.get("dominant_hypothesis", {})
    return [
        {
            "name": "latency_diagnosis_plan_ready",
            "passed": final.get("status") == "progress_support_latency_diagnosis_plan_ready"
            and final.get("passed") is True,
            "status": final.get("status"),
            "passed_value": final.get("passed"),
        },
        {
            "name": "diagnosis_identifies_route_projection",
            "passed": hypothesis.get("name")
            == "route_projection_nested_loop_dominates_latency",
            "hypothesis": hypothesis.get("name"),
        },
        {
            "name": "diagnosis_blocks_replay_and_training",
            "passed": final.get("replay_authorized") is False
            and final.get("Full36_authorized") is False
            and final.get("formal_seeds_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
            and final.get("DP_modification_authorized") is False,
            "final_decision": final,
        },
        _check_tokens(
            "helper_exports_component_latency_keys",
            helper_text,
            (
                "PROGRESS_SUPPORT_LATENCY_KEYS",
                "latency_ms_progress_support_route_projection",
                "latency_ms_progress_support_plan_arc",
                "latency_ms_progress_support_speed_profile",
                "latency_ms_progress_support_route_remaining",
                "latency_ms_progress_support_goal_alignment",
                "latency_ms_progress_support_atom_compute",
                "latency_ms_progress_support_payload_serialization",
            ),
        ),
        _check_tokens(
            "helper_preserves_payload_builder_and_atoms",
            helper_text,
            (
                "def build_progress_support_logging_payload(",
                "progress_support_atoms",
                "progress_support_atom_names",
                "finite_checks",
                "score_k(w)=a_k^T w",
            ),
        ),
        {
            "name": "benchmark_cases_are_current_tick_synthetic",
            "passed": all(
                case.candidate_count > 0
                and case.support_steps >= 2
                and case.route_points >= case.support_steps + 1
                and case.route_shape in {"straight", "sine"}
                for case in spec.cases
            ),
            "case_count": len(spec.cases),
        },
    ]


def _plan_checks(spec: MicrobenchmarkSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": "cpu_repetitions_positive",
            "passed": spec.cpu_warmups >= 1 and spec.cpu_repetitions >= 1,
            "warmups": spec.cpu_warmups,
            "repetitions": spec.cpu_repetitions,
        },
        {
            "name": "exact_equivalence_tolerance_positive",
            "passed": spec.exact_equivalence_atol >= 0.0
            and spec.exact_equivalence_rtol >= 0.0,
            "atol": spec.exact_equivalence_atol,
            "rtol": spec.exact_equivalence_rtol,
        },
        {
            "name": "route_projection_stress_case_present",
            "passed": any(
                case.route_points >= 2048 and case.candidate_count >= 8
                for case in spec.cases
            ),
            "max_route_points": max(case.route_points for case in spec.cases),
        },
    ]


def _planned_measurements() -> list[dict[str, Any]]:
    return [
        {
            "field": "latency_ms_progress_support_logging",
            "role": "total",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
        {
            "field": "latency_ms_progress_support_route_projection",
            "role": "expected_dominant_component",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
        {
            "field": "latency_ms_progress_support_plan_arc",
            "role": "secondary_component",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
        {
            "field": "latency_ms_progress_support_speed_profile",
            "role": "secondary_component",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
        {
            "field": "latency_ms_progress_support_route_remaining",
            "role": "secondary_component",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
        {
            "field": "latency_ms_progress_support_goal_alignment",
            "role": "secondary_component",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
        {
            "field": "latency_ms_progress_support_atom_compute",
            "role": "secondary_component",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
        {
            "field": "latency_ms_progress_support_payload_serialization",
            "role": "secondary_component",
            "expected_summary": ["mean_ms", "median_ms", "p95_ms", "max_ms"],
        },
    ]


def _exact_equivalence_criteria(spec: MicrobenchmarkSpec) -> list[str]:
    return [
        "benchmark inputs are deterministic synthetic current-tick arrays only",
        "no Diffusion Planner import, model load, map load, replay, or formal seed appears in benchmark execution",
        "each repetition calls build_progress_support_logging_payload without changing its public signature",
        "for every benchmark case, payloads after removing latency_ms match the first payload exactly for metadata and within "
        f"atol={spec.exact_equivalence_atol}, rtol={spec.exact_equivalence_rtol} for numeric fields",
        "progress_support_atom_names match exactly across repetitions",
        "progress_support_atoms remain finite and nonnegative across repetitions",
        "component latency keys are present, finite, and nonnegative in every repetition",
        "raw timing samples and environment metadata are recorded in the future benchmark artifact",
        "benchmark output is engineering evidence only and cannot authorize replay expansion, online promotion, CAMP retraining, or DP modification",
    ]


def _accept_criteria() -> list[str]:
    return [
        "future benchmark script has unit tests for source gate, exact-equivalence failure, and missing latency key failure",
        "future benchmark script reports per-case raw samples plus mean, median, p95, min, and max",
        "future benchmark script records Python, NumPy, platform, candidate dimensions, route dimensions, and artifact SHA",
        "route_projection is reported separately from total logging latency",
        "no optimization is accepted until a benchmark artifact identifies a dominant component and an exact-equivalent implementation plan is documented",
    ]


def _reject_criteria() -> list[str]:
    return [
        "diagnosis source is not ready or does not identify route projection",
        "helper source lacks component latency fields",
        "plan requires replay, DP import/model loading, formal seeds, online selection, or CAMP retraining",
        "planned benchmark cannot prove payload exact-equivalence after removing latency metadata",
        "planned cases omit route-length stress needed to test the nested projection hypothesis",
    ]


def _check_tokens(
    name: str,
    text: str | None,
    tokens: tuple[str, ...],
) -> dict[str, Any]:
    missing = [token for token in tokens if text is None or token not in text]
    return {
        "name": name,
        "passed": not missing,
        "missing_tokens": missing,
    }


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Progress-Support Component Microbenchmark Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- microbenchmark execution authorized: `{decision['microbenchmark_execution_authorized']}`",
        f"- replay authorized: `{decision['replay_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        detail = check.get("status") or check.get("hypothesis") or check.get(
            "missing_tokens", ""
        )
        lines.append(f"| `{check['name']}` | `{check['passed']}` | `{detail}` |")
    lines.extend(["", "## Benchmark Cases", ""])
    for case in report["microbenchmark_spec"]["cases"]:
        lines.append(
            f"- `{case['name']}`: K={case['candidate_count']}, "
            f"H={case['support_steps']}, route_points={case['route_points']}, "
            f"shape={case['route_shape']}"
        )
    lines.extend(["", "## Planned Measurements", ""])
    lines.extend(
        f"- `{item['field']}`: {item['role']}"
        for item in report["planned_measurements"]
    )
    lines.extend(["", "## Exact Equivalence Criteria", ""])
    lines.extend(f"- {item}" for item in report["exact_equivalence_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
