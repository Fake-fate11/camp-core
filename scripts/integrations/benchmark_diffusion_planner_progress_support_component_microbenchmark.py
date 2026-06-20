#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_progress_support import (  # noqa: E402
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_LATENCY_KEYS,
    build_progress_support_logging_payload,
)
from scripts.integrations.plan_diffusion_planner_progress_support_component_microbenchmark import (  # noqa: E402
    AUTHORIZED_NEXT_WORK as PLAN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as PLAN_READY_STATUS,
    BenchmarkCaseSpec,
    MicrobenchmarkSpec,
)


READY_STATUS = "progress_support_component_microbenchmark_synthetic_completed"
REJECT_STATUS = "progress_support_component_microbenchmark_synthetic_rejected"
AUTHORIZED_NEXT_WORK = "progress_support_component_microbenchmark_result_review_only"

PayloadBuilder = Callable[..., dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the predeclared synthetic current-tick progress-support "
            "component microbenchmark. This does not import or execute "
            "Diffusion Planner, replay, formal seeds, online selection, or "
            "CAMP training."
        )
    )
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(plan_json=args.plan_json, label=args.label)
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
    plan_json: Path,
    label: str | None = None,
    payload_builder: PayloadBuilder = build_progress_support_logging_payload,
    latency_keys: tuple[str, ...] = PROGRESS_SUPPORT_LATENCY_KEYS,
) -> dict[str, Any]:
    plan = _read_json(plan_json)
    source_checks = _source_checks(plan)
    source_passed = all(check["passed"] for check in source_checks)
    if source_passed:
        spec = _spec_from_plan(plan)
        case_reports = [
            _benchmark_case(
                case,
                spec=spec,
                payload_builder=payload_builder,
                latency_keys=latency_keys,
            )
            for case in spec.cases
        ]
    else:
        spec = _spec_from_plan(plan, allow_fallback=True)
        case_reports = []
    case_passed = all(report["passed"] for report in case_reports)
    passed = source_passed and case_passed and bool(case_reports)
    return {
        "analysis": {
            "name": "dp_camp_progress_support_component_microbenchmark_v1",
            "label": label,
            "source_status": PLAN_READY_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay": False,
            "formal_seed_use": False,
            "future_outcome_labels_used": False,
            "unit_tests_are_latency_evidence": False,
            "math_boundary": (
                "This benchmark measures existing progress-support logging on "
                "deterministic current-tick synthetic arrays. It reads no "
                "closed-loop outcomes, imports no Diffusion Planner model or "
                "map, and changes no CAMP scoring. Progress-support atoms "
                "remain fixed finite-candidate coefficients a_k, preserving "
                "affine score_k(w)=a_k^T w and the simplex/CVaR/L2 convex "
                "master."
            ),
        },
        "source": {
            "plan_json": str(plan_json),
        },
        "source_checks": source_checks,
        "protocol": {
            "cpu_warmups": spec.cpu_warmups,
            "cpu_repetitions": spec.cpu_repetitions,
            "exact_equivalence_atol": spec.exact_equivalence_atol,
            "exact_equivalence_rtol": spec.exact_equivalence_rtol,
        },
        "environment": _environment(),
        "cases": case_reports,
        "aggregate": _aggregate(case_reports),
        "blocked_actions": {
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
            "replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "optimization_authorized": False,
        },
    }


def _source_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    final = plan.get("final_decision", {})
    analysis = plan.get("analysis", {})
    return [
        {
            "name": "plan_ready",
            "passed": final.get("status") == PLAN_READY_STATUS
            and final.get("passed") is True,
            "status": final.get("status"),
            "passed_value": final.get("passed"),
        },
        {
            "name": "plan_authorizes_implementation_unit_tests_only",
            "passed": final.get("authorized_next_work") == PLAN_AUTHORIZED_NEXT_WORK,
            "authorized_next_work": final.get("authorized_next_work"),
        },
        {
            "name": "plan_blocks_replay_training_and_dp_modification",
            "passed": final.get("replay_authorized") is False
            and final.get("Full36_authorized") is False
            and final.get("formal_seeds_authorized") is False
            and final.get("online_selector_authorized") is False
            and final.get("CAMP_retraining_authorized") is False
            and final.get("DP_modification_authorized") is False,
            "final_decision": final,
        },
        {
            "name": "plan_declares_no_dp_execution_or_training",
            "passed": analysis.get("diffusion_planner_execution") is False
            and analysis.get("training") is False
            and analysis.get("future_outcome_labels_used") is False,
            "analysis": analysis,
        },
        {
            "name": "plan_contains_benchmark_cases",
            "passed": bool(plan.get("microbenchmark_spec", {}).get("cases")),
            "case_count": len(plan.get("microbenchmark_spec", {}).get("cases", [])),
        },
    ]


def _spec_from_plan(
    plan: dict[str, Any],
    *,
    allow_fallback: bool = False,
) -> MicrobenchmarkSpec:
    raw = plan.get("microbenchmark_spec", {})
    if not raw:
        if allow_fallback:
            return MicrobenchmarkSpec(cases=())
        raise ValueError("Plan is missing microbenchmark_spec.")
    cases = tuple(
        BenchmarkCaseSpec(
            name=str(case["name"]),
            candidate_count=int(case["candidate_count"]),
            support_steps=int(case["support_steps"]),
            route_points=int(case["route_points"]),
            route_shape=str(case["route_shape"]),
        )
        for case in raw.get("cases", [])
    )
    return MicrobenchmarkSpec(
        root=str(raw.get("root", MicrobenchmarkSpec.root)),
        cpu_warmups=int(raw.get("cpu_warmups", MicrobenchmarkSpec.cpu_warmups)),
        cpu_repetitions=int(
            raw.get("cpu_repetitions", MicrobenchmarkSpec.cpu_repetitions)
        ),
        exact_equivalence_atol=float(
            raw.get(
                "exact_equivalence_atol",
                MicrobenchmarkSpec.exact_equivalence_atol,
            )
        ),
        exact_equivalence_rtol=float(
            raw.get(
                "exact_equivalence_rtol",
                MicrobenchmarkSpec.exact_equivalence_rtol,
            )
        ),
        cases=cases,
    )


def _benchmark_case(
    case: BenchmarkCaseSpec,
    *,
    spec: MicrobenchmarkSpec,
    payload_builder: PayloadBuilder,
    latency_keys: tuple[str, ...],
) -> dict[str, Any]:
    candidates, route = _synthetic_current_tick(case)
    baseline_payload = payload_builder(
        candidates=candidates,
        route_centerline_ego=route,
        support_steps=case.support_steps,
        dt_s=0.1,
    )
    baseline_checks = _payload_checks(baseline_payload, latency_keys)
    baseline_without_latency = _without_latency(baseline_payload)
    for _ in range(spec.cpu_warmups):
        payload = payload_builder(
            candidates=candidates,
            route_centerline_ego=route,
            support_steps=case.support_steps,
            dt_s=0.1,
        )
        baseline_checks.extend(_payload_checks(payload, latency_keys))
        baseline_checks.append(
            _equivalence_check(
                baseline_without_latency,
                _without_latency(payload),
                spec=spec,
                phase="warmup",
            )
        )

    latency_samples = {key: [] for key in latency_keys}
    outer_wall_samples: list[float] = []
    equivalence_checks = []
    for _ in range(spec.cpu_repetitions):
        start = time.perf_counter()
        payload = payload_builder(
            candidates=candidates,
            route_centerline_ego=route,
            support_steps=case.support_steps,
            dt_s=0.1,
        )
        outer_wall_samples.append((time.perf_counter() - start) * 1000.0)
        baseline_checks.extend(_payload_checks(payload, latency_keys))
        equivalence_checks.append(
            _equivalence_check(
                baseline_without_latency,
                _without_latency(payload),
                spec=spec,
                phase="sample",
            )
        )
        for key in latency_keys:
            value = payload.get("latency_ms", {}).get(key)
            if isinstance(value, (int, float, np.number)):
                latency_samples[key].append(float(value))

    checks = baseline_checks + equivalence_checks
    passed = all(check["passed"] for check in checks)
    return {
        "name": case.name,
        "passed": passed,
        "dimensions": {
            "candidates": list(candidates.shape),
            "route_centerline_ego": list(route.shape),
            "support_steps": int(case.support_steps),
            "route_shape": case.route_shape,
        },
        "checks": checks,
        "latency": {
            key: {
                "stats": _stats(samples),
                "samples_ms": samples,
            }
            for key, samples in latency_samples.items()
        },
        "outer_wall": {
            "stats": _stats(outer_wall_samples),
            "samples_ms": outer_wall_samples,
        },
        "dominant_component": _dominant_component(latency_samples),
    }


def _synthetic_current_tick(
    case: BenchmarkCaseSpec,
) -> tuple[np.ndarray, np.ndarray]:
    if case.candidate_count < 1:
        raise ValueError("candidate_count must be >= 1.")
    if case.support_steps < 2:
        raise ValueError("support_steps must be >= 2.")
    if case.route_points < case.support_steps + 1:
        raise ValueError("route_points must exceed support_steps.")
    if case.route_shape not in {"straight", "sine"}:
        raise ValueError(f"Unsupported route_shape: {case.route_shape}")

    route_x = np.linspace(0.0, float(case.route_points - 1), case.route_points)
    if case.route_shape == "straight":
        route_y = np.zeros_like(route_x)
    else:
        route_y = 3.0 * np.sin(route_x / 31.0)
    route = np.column_stack([route_x, route_y]).astype(np.float64)

    horizon_x = np.linspace(0.0, min(route_x[-1], 2.0 * case.support_steps), case.support_steps)
    candidates = np.zeros((case.candidate_count, case.support_steps, 2), dtype=np.float64)
    for cand_idx in range(case.candidate_count):
        progress_scale = max(0.35, 1.0 - 0.025 * cand_idx)
        lateral_offset = ((cand_idx % 5) - 2) * 0.15
        x = np.clip(horizon_x * progress_scale + 0.05 * cand_idx, 0.0, route_x[-1])
        if case.route_shape == "straight":
            y = np.full_like(x, lateral_offset)
        else:
            y = 3.0 * np.sin(x / 31.0) + lateral_offset
        candidates[cand_idx, :, 0] = x
        candidates[cand_idx, :, 1] = y
    return candidates, route


def _payload_checks(
    payload: dict[str, Any],
    latency_keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    latency = payload.get("latency_ms", {})
    missing_latency = [key for key in latency_keys if key not in latency]
    extra_latency = [key for key in latency if key not in latency_keys]
    checks.append(
        {
            "name": "latency_keys_exact",
            "passed": not missing_latency and not extra_latency,
            "missing": missing_latency,
            "extra": extra_latency,
        }
    )
    latency_values = [
        float(latency[key])
        for key in latency_keys
        if key in latency and isinstance(latency[key], (int, float, np.number))
    ]
    checks.append(
        {
            "name": "latency_values_finite_nonnegative",
            "passed": len(latency_values) == len(latency_keys)
            and bool(np.all(np.isfinite(latency_values)))
            and bool(np.all(np.asarray(latency_values) >= 0.0)),
        }
    )
    atom_names = payload.get("progress_support_atom_names")
    atoms = np.asarray(payload.get("progress_support_atoms", []), dtype=np.float64)
    checks.append(
        {
            "name": "atom_names_exact",
            "passed": atom_names == list(PROGRESS_SUPPORT_ATOM_NAMES),
        }
    )
    checks.append(
        {
            "name": "atoms_finite_nonnegative",
            "passed": atoms.ndim == 2
            and atoms.shape[1] == len(PROGRESS_SUPPORT_ATOM_NAMES)
            and bool(np.all(np.isfinite(atoms)))
            and bool(np.all(atoms >= -1e-12)),
        }
    )
    checks.append(
        {
            "name": "runtime_scope_metadata_no_outcome_or_benders_claim",
            "passed": payload.get("future_outcome_leakage") is False
            and payload.get("closed_loop_outcome_fields_read") is False
            and payload.get("classical_benders_claim") is False,
        }
    )
    return checks


def _without_latency(payload: dict[str, Any]) -> dict[str, Any]:
    stripped = dict(payload)
    stripped.pop("latency_ms", None)
    return stripped


def _equivalence_check(
    first: Any,
    second: Any,
    *,
    spec: MicrobenchmarkSpec,
    phase: str,
) -> dict[str, Any]:
    try:
        max_abs = _max_abs_numeric_difference(first, second)
        scale = max(_max_abs_numeric_difference(first, _zeros_like(first)), 1.0)
        tolerance = spec.exact_equivalence_atol + spec.exact_equivalence_rtol * scale
        passed = max_abs <= tolerance
    except AssertionError as exc:
        return {
            "name": "payload_equivalence_without_latency",
            "phase": phase,
            "passed": False,
            "error": str(exc),
        }
    result = {
        "name": "payload_equivalence_without_latency",
        "phase": phase,
        "passed": passed,
        "max_abs_numeric_difference": float(max_abs),
        "atol": spec.exact_equivalence_atol,
        "rtol": spec.exact_equivalence_rtol,
        "tolerance": float(tolerance),
    }
    if not passed:
        result["error"] = "max_abs_numeric_difference exceeds tolerance"
    return result


def _max_abs_numeric_difference(first: Any, second: Any) -> float:
    if first is None or second is None:
        if first is not second:
            raise AssertionError(f"Optional values differ: {first!r} != {second!r}")
        return 0.0
    if isinstance(first, dict) and isinstance(second, dict):
        if first.keys() != second.keys():
            raise AssertionError(
                f"Dictionary keys differ: {first.keys()} != {second.keys()}"
            )
        return max(
            (_max_abs_numeric_difference(first[key], second[key]) for key in first),
            default=0.0,
        )
    if isinstance(first, (list, tuple)) and isinstance(second, (list, tuple)):
        if len(first) != len(second):
            raise AssertionError("Sequence lengths differ.")
        return max(
            (
                _max_abs_numeric_difference(left, right)
                for left, right in zip(first, second)
            ),
            default=0.0,
        )
    if isinstance(first, (int, float, np.number, bool)) and isinstance(
        second,
        (int, float, np.number, bool),
    ):
        return abs(float(first) - float(second))
    if first != second:
        raise AssertionError(f"Values differ: {first!r} != {second!r}")
    return 0.0


def _zeros_like(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _zeros_like(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_zeros_like(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_zeros_like(item) for item in value)
    if isinstance(value, (int, float, np.number, bool)):
        return 0.0
    if value is None:
        return None
    return value


def _stats(samples: list[float]) -> dict[str, float | int]:
    values = np.asarray(samples, dtype=np.float64)
    if values.size == 0:
        return {
            "count": 0,
            "mean_ms": float("nan"),
            "median_ms": float("nan"),
            "p95_ms": float("nan"),
            "min_ms": float("nan"),
            "max_ms": float("nan"),
        }
    return {
        "count": int(values.size),
        "mean_ms": float(np.mean(values)),
        "median_ms": float(np.median(values)),
        "p95_ms": float(np.percentile(values, 95)),
        "min_ms": float(np.min(values)),
        "max_ms": float(np.max(values)),
    }


def _dominant_component(samples_by_key: dict[str, list[float]]) -> dict[str, Any]:
    component_stats = {
        key: _stats(samples)
        for key, samples in samples_by_key.items()
        if key != "latency_ms_progress_support_logging"
    }
    if not component_stats:
        return {"field": None, "p95_ms": None}
    field = max(
        component_stats,
        key=lambda key: float(component_stats[key]["p95_ms"]),
    )
    return {"field": field, "p95_ms": component_stats[field]["p95_ms"]}


def _aggregate(case_reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not case_reports:
        return {}
    latency_fields = sorted(
        {
            field
            for report in case_reports
            for field in report.get("latency", {})
        }
    )
    aggregate: dict[str, Any] = {}
    for field in latency_fields:
        p95_values = [
            report["latency"][field]["stats"]["p95_ms"]
            for report in case_reports
            if field in report.get("latency", {})
        ]
        aggregate[field] = {
            "case_count": len(p95_values),
            "median_case_p95_ms": float(np.median(p95_values)),
            "max_case_p95_ms": float(np.max(p95_values)),
        }
    non_total = {
        field: values
        for field, values in aggregate.items()
        if field != "latency_ms_progress_support_logging"
    }
    if non_total:
        dominant = max(
            non_total,
            key=lambda field: float(non_total[field]["max_case_p95_ms"]),
        )
        aggregate["dominant_component_by_max_case_p95"] = {
            "field": dominant,
            "max_case_p95_ms": non_total[dominant]["max_case_p95_ms"],
        }
    return aggregate


def _environment() -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
    }


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Progress-Support Component Microbenchmark",
        "",
        f"- status: `{decision['status']}`",
        f"- passed: `{decision['passed']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- replay authorized: `{decision['replay_authorized']}`",
        f"- CAMP retraining authorized: `{decision['CAMP_retraining_authorized']}`",
        f"- DP modification authorized: `{decision['DP_modification_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        detail = check.get("status") or check.get("authorized_next_work") or ""
        lines.append(f"| `{check['name']}` | `{check['passed']}` | `{detail}` |")
    lines.extend(
        [
            "",
            "## Case P95 Latency",
            "",
            "| Case | Total p95 (ms) | Route projection p95 (ms) | Dominant component |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for case in report["cases"]:
        total = case["latency"]["latency_ms_progress_support_logging"]["stats"][
            "p95_ms"
        ]
        route_projection = case["latency"][
            "latency_ms_progress_support_route_projection"
        ]["stats"]["p95_ms"]
        dominant = case["dominant_component"]["field"]
        lines.append(
            f"| `{case['name']}` | {total:.6f} | "
            f"{route_projection:.6f} | `{dominant}` |"
        )
    lines.extend(
        [
            "",
            "This synthetic benchmark is engineering evidence only. It does not "
            "authorize replay expansion, online promotion, CAMP retraining, DP "
            "modification, or optimization implementation by itself.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
