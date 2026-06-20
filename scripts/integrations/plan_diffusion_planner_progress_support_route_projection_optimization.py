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

READY_STATUS = "progress_support_route_projection_optimization_plan_ready"
REJECT_STATUS = "progress_support_route_projection_optimization_plan_rejected"
SOURCE_STATUS = "progress_support_component_microbenchmark_result_review_passed"
AUTHORIZED_NEXT_WORK = (
    "progress_support_route_projection_exact_equivalent_optimization_"
    "implementation_unit_tests_only"
)
REQUIRED_DOMINANT_FIELD = "latency_ms_progress_support_route_projection"


@dataclass(frozen=True)
class EquivalenceCaseSpec:
    name: str
    candidate_count: int
    support_steps: int
    route_points: int
    route_shape: str
    include_degenerate_segments: bool = False


@dataclass(frozen=True)
class OptimizationPlanSpec:
    segment_chunk_size: int = 256
    exact_equivalence_atol: float = 1e-12
    exact_equivalence_rtol: float = 1e-12
    max_intermediate_elements: int = 4_000_000
    cases: tuple[EquivalenceCaseSpec, ...] = (
        EquivalenceCaseSpec(
            name="straight_reference",
            candidate_count=8,
            support_steps=10,
            route_points=256,
            route_shape="straight",
        ),
        EquivalenceCaseSpec(
            name="curved_reference",
            candidate_count=8,
            support_steps=10,
            route_points=512,
            route_shape="sine",
        ),
        EquivalenceCaseSpec(
            name="long_route_projection_stress",
            candidate_count=8,
            support_steps=10,
            route_points=2048,
            route_shape="sine",
        ),
        EquivalenceCaseSpec(
            name="candidate_scale_stress",
            candidate_count=32,
            support_steps=10,
            route_points=512,
            route_shape="straight",
        ),
        EquivalenceCaseSpec(
            name="degenerate_segment_fail_closed",
            candidate_count=4,
            support_steps=6,
            route_points=64,
            route_shape="straight",
            include_degenerate_segments=True,
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for an exact-equivalent route projection "
            "optimization. It predeclares assumptions, fail-closed behavior, "
            "and equivalence tests, but does not implement the optimization."
        )
    )
    parser.add_argument("--benchmark_json", type=Path, required=True)
    parser.add_argument("--helper_source", type=Path, default=HELPER_SOURCE)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        benchmark_json=args.benchmark_json,
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
    benchmark_json: Path,
    helper_source: Path = HELPER_SOURCE,
    label: str | None = None,
    spec: OptimizationPlanSpec = OptimizationPlanSpec(),
) -> dict[str, Any]:
    benchmark = _read_json(benchmark_json)
    helper_text = _read_text(helper_source)
    source_checks = _source_checks(benchmark=benchmark, helper_text=helper_text)
    plan_checks = _plan_checks(spec)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    return {
        "analysis": {
            "name": "dp_camp_progress_support_route_projection_optimization_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay_authorized": False,
            "future_outcome_labels_used": False,
            "optimization_implementation": False,
            "math_boundary": (
                "The plan concerns an exact-equivalent implementation of a "
                "current-tick geometric projection helper. It changes no CAMP "
                "score, atom schema, candidate generation, or closed-loop "
                "policy. Progress-support atoms remain fixed finite-candidate "
                "coefficients a_k, preserving affine score_k(w)=a_k^T w and "
                "the simplex/CVaR/L2 convex master."
            ),
        },
        "source": {
            "benchmark_json": str(benchmark_json),
            "helper_source": str(helper_source),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "optimization_plan": {
            **asdict(spec),
            "cases": [asdict(case) for case in spec.cases],
            "algorithm": _algorithm_plan(spec),
            "fail_closed_conditions": _fail_closed_conditions(),
            "exact_equivalence_criteria": _exact_equivalence_criteria(spec),
            "implementation_boundaries": _implementation_boundaries(),
            "required_tests": _required_tests(),
        },
        "blocked_actions": {
            "new_replay": True,
            "broader_replay": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
            "optimization_implementation_now": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "optimization_implementation_authorized": False,
        },
    }


def _source_checks(
    *,
    benchmark: dict[str, Any],
    helper_text: str | None,
) -> list[dict[str, Any]]:
    final = benchmark.get("final_decision", {})
    aggregate = benchmark.get("aggregate", {})
    dominant = aggregate.get("dominant_component_by_max_case_p95", {})
    cases = benchmark.get("cases", [])
    route_projection_p95 = aggregate.get(REQUIRED_DOMINANT_FIELD, {}).get(
        "max_case_p95_ms",
        0.0,
    )
    next_component_p95 = _max_non_route_projection_p95(aggregate)
    dominance_ratio = (
        float(route_projection_p95) / float(next_component_p95)
        if next_component_p95
        else float("inf")
    )
    return [
        {
            "name": "synthetic_benchmark_completed",
            "passed": final.get("status")
            == "progress_support_component_microbenchmark_synthetic_completed"
            and final.get("passed") is True,
            "status": final.get("status"),
            "passed_value": final.get("passed"),
        },
        {
            "name": "benchmark_blocks_replay_training_dp_and_optimization",
            "passed": final.get("replay_authorized") is False
            and final.get("Full36_authorized") is False
            and final.get("formal_seeds_authorized") is False
            and final.get("online_selector_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
            and final.get("DP_modification_authorized") is False
            and final.get("optimization_authorized") is False,
            "final_decision": final,
        },
        {
            "name": "aggregate_dominant_component_is_route_projection",
            "passed": dominant.get("field") == REQUIRED_DOMINANT_FIELD,
            "dominant_field": dominant.get("field"),
        },
        {
            "name": "all_cases_route_projection_dominant",
            "passed": bool(cases)
            and all(
                case.get("dominant_component", {}).get("field")
                == REQUIRED_DOMINANT_FIELD
                for case in cases
            ),
            "case_count": len(cases),
        },
        {
            "name": "route_projection_dominance_margin_present",
            "passed": dominance_ratio >= 1000.0,
            "route_projection_max_case_p95_ms": route_projection_p95,
            "next_component_max_case_p95_ms": next_component_p95,
            "dominance_ratio": dominance_ratio,
        },
        _check_tokens(
            "helper_has_reference_route_projection_loop",
            helper_text,
            (
                "def _route_progress_profiles(",
                "for cand_idx in range(candidates_xy.shape[0]):",
                "for step_idx in range(candidates_xy.shape[1]):",
                "for seg_idx, segment in enumerate(segments):",
                "if distance < best_distance:",
                "profiles[cand_idx, step_idx] = best_s",
            ),
        ),
    ]


def _plan_checks(spec: OptimizationPlanSpec) -> list[dict[str, Any]]:
    return [
        {
            "name": "chunk_size_positive",
            "passed": spec.segment_chunk_size >= 1,
            "segment_chunk_size": spec.segment_chunk_size,
        },
        {
            "name": "intermediate_limit_positive",
            "passed": spec.max_intermediate_elements >= 1,
            "max_intermediate_elements": spec.max_intermediate_elements,
        },
        {
            "name": "exact_equivalence_tolerances_nonnegative",
            "passed": spec.exact_equivalence_atol >= 0.0
            and spec.exact_equivalence_rtol >= 0.0,
            "atol": spec.exact_equivalence_atol,
            "rtol": spec.exact_equivalence_rtol,
        },
        {
            "name": "stress_and_fail_closed_cases_present",
            "passed": any(case.route_points >= 2048 for case in spec.cases)
            and any(case.candidate_count >= 32 for case in spec.cases)
            and any(case.include_degenerate_segments for case in spec.cases),
            "case_count": len(spec.cases),
        },
    ]


def _algorithm_plan(spec: OptimizationPlanSpec) -> list[str]:
    return [
        "keep the public build_progress_support_logging_payload signature unchanged",
        "preserve _route_progress_profiles(candidates_xy, route_xy) as the replacement boundary",
        "convert candidates and route to float64 exactly as the current helper does",
        "flatten candidate points from [K,H,2] to [K*H,2]",
        "compute route cumulative lengths and segment vectors with the same formulas as the reference loop",
        "skip segments whose squared length is <= 1e-12 exactly as the reference loop does",
        f"process route segments in deterministic chunks of at most {spec.segment_chunk_size}",
        "for each chunk, compute t=clip(dot(point-start, segment)/denom, 0, 1), projection, squared distance, and s",
        "update best segment only when the new squared distance is strictly smaller, preserving earliest-segment tie behavior",
        "reshape the selected s values back to [K,H]",
        "fall back to the reference loop whenever input validation or memory guard conditions fail",
    ]


def _fail_closed_conditions() -> list[str]:
    return [
        "candidates_xy is not finite float-compatible [K,H,2]",
        "route_xy is not finite float-compatible [N,2] with N>=2",
        "all route segments are degenerate after applying the reference denom <= 1e-12 rule",
        "K*H*segment_chunk_size would exceed the predeclared intermediate element guard",
        "optimized output shape differs from the reference shape",
        "any optimized output value is non-finite",
    ]


def _exact_equivalence_criteria(spec: OptimizationPlanSpec) -> list[str]:
    return [
        "unit tests must compare optimized _route_progress_profiles against the current reference loop before replacing it",
        f"reference-vs-optimized route progress must satisfy atol={spec.exact_equivalence_atol}, rtol={spec.exact_equivalence_rtol}",
        "payloads from build_progress_support_logging_payload must match after removing latency_ms",
        "progress_support_atom_names must match exactly",
        "progress_support_atoms must remain finite and nonnegative",
        "component latency keys must remain present, finite, and nonnegative",
        "tie behavior must preserve the reference loop's strict less-than first-segment preference",
        "fail-closed paths must call the reference implementation, not an approximate projection",
    ]


def _implementation_boundaries() -> list[str]:
    return [
        "no change to DP candidate generation",
        "no change to postprocess_reference or PerfectTracker",
        "no change to CAMP atom schema or affine score",
        "no change to simplex/CVaR/L2 convex master",
        "no replay, formal seed, online selector, CAMP retraining, or DP modification",
        "optimization implementation is not authorized by this design gate",
    ]


def _required_tests() -> list[str]:
    return [
        "source gate rejects non-completed or non-dominant synthetic benchmark artifacts",
        "optimized route projection matches reference on straight and curved routes",
        "optimized route projection matches reference on long route and candidate-scale stress cases",
        "degenerate segments trigger or preserve fail-closed exact behavior",
        "tie case preserves earliest-segment behavior",
        "payload excluding latency metadata remains exactly equivalent within tolerance",
        "missing latency keys or atom drift fails closed",
    ]


def _max_non_route_projection_p95(aggregate: dict[str, Any]) -> float:
    values = []
    for field, summary in aggregate.items():
        if field in {
            REQUIRED_DOMINANT_FIELD,
            "latency_ms_progress_support_logging",
            "dominant_component_by_max_case_p95",
        }:
            continue
        if isinstance(summary, dict) and "max_case_p95_ms" in summary:
            values.append(float(summary["max_case_p95_ms"]))
    return max(values, default=0.0)


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
        "# Progress-Support Route Projection Optimization Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- optimization implementation authorized: `{decision['optimization_implementation_authorized']}`",
        f"- replay authorized: `{decision['replay_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        detail = (
            check.get("status")
            or check.get("dominant_field")
            or check.get("dominance_ratio")
            or check.get("missing_tokens", "")
        )
        lines.append(f"| `{check['name']}` | `{check['passed']}` | `{detail}` |")
    lines.extend(["", "## Algorithm Plan", ""])
    lines.extend(f"- {item}" for item in report["optimization_plan"]["algorithm"])
    lines.extend(["", "## Fail-Closed Conditions", ""])
    lines.extend(
        f"- {item}" for item in report["optimization_plan"]["fail_closed_conditions"]
    )
    lines.extend(["", "## Exact Equivalence Criteria", ""])
    lines.extend(
        f"- {item}" for item in report["optimization_plan"]["exact_equivalence_criteria"]
    )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
