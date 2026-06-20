#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_progress_support_logging_smoke import (
    DATASET_AUDIT,
    PAYLOAD_AUDIT,
    RUNNER,
    SELECTOR_EQUIVALENCE,
    SmokeSpec,
    _dataset_audit_command,
    _payload_audit_command,
    _runner_command,
    _selector_equivalence_command,
    _source_checks as _logging_smoke_source_checks,
)


READY_STATUS = "progress_support_route_projection_optimized_nonformal_smoke_plan_ready"
REJECT_STATUS = (
    "progress_support_route_projection_optimized_nonformal_smoke_plan_rejected"
)
SOURCE_STATUS = "progress_support_route_projection_optimized_synthetic_benchmark_passed"
AUTHORIZED_NEXT_WORK = (
    "progress_support_route_projection_optimized_paired_three_step_smoke_only"
)
REQUIRED_LATENCY_FIELD = "latency_ms_progress_support_logging"
REQUIRED_ROUTE_PROJECTION_FIELD = "latency_ms_progress_support_route_projection"
DEFAULT_PREVIOUS_SMOKE_MAX_LATENCY_MS = 100.0
DEFAULT_OPTIMIZED_MAX_LOGGING_P95_MS = 25.0
DEFAULT_OPTIMIZED_MAX_ROUTE_PROJECTION_P95_MS = 20.0
DEFAULT_MIN_SYNTHETIC_TO_SMOKE_SPEEDUP = 5.0

DEFAULT_SMOKE = replace(
    SmokeSpec(),
    root="/root/autodl-tmp/camp_dp_progress_support_logging_smoke_optimized_5e80a85",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for a paired nonformal smoke after the "
            "exact-equivalent progress-support route projection optimization. "
            "It emits commands and acceptance criteria but does not run replay."
        )
    )
    parser.add_argument("--optimized_benchmark_json", type=Path, required=True)
    parser.add_argument("--previous_smoke_audit_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--replay_source", type=Path, default=RUNNER)
    parser.add_argument("--payload_audit_source", type=Path, default=PAYLOAD_AUDIT)
    parser.add_argument(
        "--selector_equivalence_source",
        type=Path,
        default=SELECTOR_EQUIVALENCE,
    )
    parser.add_argument("--dataset_audit_source", type=Path, default=DATASET_AUDIT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        optimized_benchmark_json=args.optimized_benchmark_json,
        previous_smoke_audit_json=args.previous_smoke_audit_json,
        label=args.label,
        replay_source=args.replay_source,
        payload_audit_source=args.payload_audit_source,
        selector_equivalence_source=args.selector_equivalence_source,
        dataset_audit_source=args.dataset_audit_source,
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
    optimized_benchmark_json: Path,
    previous_smoke_audit_json: Path,
    label: str | None = None,
    replay_source: Path = RUNNER,
    payload_audit_source: Path = PAYLOAD_AUDIT,
    selector_equivalence_source: Path = SELECTOR_EQUIVALENCE,
    dataset_audit_source: Path = DATASET_AUDIT,
    smoke: SmokeSpec = DEFAULT_SMOKE,
) -> dict[str, Any]:
    optimized_benchmark = _read_json(optimized_benchmark_json)
    previous_smoke = _read_json(previous_smoke_audit_json)
    source_checks = [
        *_benchmark_source_checks(
            optimized_benchmark=optimized_benchmark,
            previous_smoke=previous_smoke,
        ),
        *_logging_smoke_source_checks(
            replay_source=replay_source,
            payload_audit_source=payload_audit_source,
            selector_equivalence_source=selector_equivalence_source,
            dataset_audit_source=dataset_audit_source,
        ),
    ]
    plan_checks = _plan_checks(smoke)
    passed = all(check["passed"] for check in source_checks + plan_checks)
    baseline_dir = f"{smoke.root}/baseline"
    candidate_dir = f"{smoke.root}/logging_enabled"
    audit_dir = f"{smoke.root}/audit"
    commands = {
        "baseline_replay": _runner_command(smoke, baseline_dir, logging=False),
        "candidate_replay": _runner_command(smoke, candidate_dir, logging=True),
        "selector_equivalence": _selector_equivalence_command(
            baseline_dir,
            candidate_dir,
            audit_dir,
        ),
        "payload_audit": _payload_audit_command(
            baseline_dir,
            candidate_dir,
            audit_dir,
            smoke,
        ),
        "dataset_audit": _dataset_audit_command(candidate_dir, audit_dir, smoke),
    }
    return {
        "analysis": {
            "name": "dp_camp_progress_support_optimized_nonformal_smoke_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "math_boundary": (
                "The planned smoke only verifies default-off logging overhead "
                "after an exact-equivalent current-tick route projection "
                "implementation. It must not change CAMP scores, feasibility, "
                "selected indices, DP candidates, or PerfectTracker execution. "
                "Progress-support atoms remain fixed finite-candidate "
                "coefficients a_k preserving affine score_k(w)=a_k^T w and "
                "the simplex/CVaR/L2 convex master."
            ),
        },
        "source": {
            "optimized_benchmark_json": str(optimized_benchmark_json),
            "previous_smoke_audit_json": str(previous_smoke_audit_json),
        },
        "source_checks": source_checks,
        "plan_checks": plan_checks,
        "smoke_spec": asdict(smoke),
        "comparison": _comparison(optimized_benchmark, previous_smoke),
        "accept_criteria": _accept_criteria(smoke),
        "reject_criteria": _reject_criteria(),
        "commands": commands,
        "blocked_actions": {
            "run_replay_now": True,
            "broader_replay": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
            "online_optimization_promotion": True,
        },
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "paired_smoke_execution_authorized": False,
            "paired_smoke_execution_scope": (
                "next gate only: paired nonformal sample_map_tl_route_59_to_86 "
                "seed1 npc4 traffic_lights_off static, 3 steps"
                if passed
                else None
            ),
            "new_replay_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "CAMP_retraining_authorized": False,
            "DP_modification_authorized": False,
            "online_optimization_promotion_authorized": False,
        },
    }


def _benchmark_source_checks(
    *,
    optimized_benchmark: dict[str, Any],
    previous_smoke: dict[str, Any],
) -> list[dict[str, Any]]:
    benchmark_final = optimized_benchmark.get("final_decision", {})
    previous_final = previous_smoke.get("final_decision", {})
    optimized_aggregate = optimized_benchmark.get("aggregate", {})
    optimized_total = _aggregate_max_p95(
        optimized_aggregate,
        REQUIRED_LATENCY_FIELD,
    )
    optimized_route = _aggregate_max_p95(
        optimized_aggregate,
        REQUIRED_ROUTE_PROJECTION_FIELD,
    )
    previous_latency = _previous_smoke_latency(previous_smoke, REQUIRED_LATENCY_FIELD)
    speedup = (
        previous_latency / optimized_total
        if optimized_total and optimized_total > 0.0
        else float("inf")
    )
    return [
        {
            "name": "optimized_synthetic_benchmark_completed",
            "passed": benchmark_final.get("status")
            == "progress_support_component_microbenchmark_synthetic_completed"
            and benchmark_final.get("passed") is True,
            "status": benchmark_final.get("status"),
            "passed_value": benchmark_final.get("passed"),
        },
        {
            "name": "optimized_benchmark_blocks_replay_training_dp_and_promotion",
            "passed": benchmark_final.get("replay_authorized") is False
            and benchmark_final.get("Full36_authorized") is False
            and benchmark_final.get("formal_seeds_authorized") is False
            and benchmark_final.get("online_selector_authorized") is False
            and benchmark_final.get("CAMP_retraining_authorized") is False
            and benchmark_final.get("DP_modification_authorized") is False
            and benchmark_final.get("optimization_authorized") is False,
            "final_decision": benchmark_final,
        },
        {
            "name": "optimized_total_logging_p95_below_design_threshold",
            "passed": optimized_total <= DEFAULT_OPTIMIZED_MAX_LOGGING_P95_MS,
            "optimized_total_logging_max_case_p95_ms": optimized_total,
            "threshold_ms": DEFAULT_OPTIMIZED_MAX_LOGGING_P95_MS,
        },
        {
            "name": "optimized_route_projection_p95_below_design_threshold",
            "passed": optimized_route <= DEFAULT_OPTIMIZED_MAX_ROUTE_PROJECTION_P95_MS,
            "optimized_route_projection_max_case_p95_ms": optimized_route,
            "threshold_ms": DEFAULT_OPTIMIZED_MAX_ROUTE_PROJECTION_P95_MS,
        },
        {
            "name": "previous_smoke_passed_but_latency_blocked",
            "passed": previous_final.get("status") == "progress_support_logging_smoke_passed"
            and previous_final.get("passed") is True
            and previous_latency >= DEFAULT_PREVIOUS_SMOKE_MAX_LATENCY_MS,
            "previous_status": previous_final.get("status"),
            "previous_max_latency_ms": previous_latency,
            "threshold_ms": DEFAULT_PREVIOUS_SMOKE_MAX_LATENCY_MS,
        },
        {
            "name": "synthetic_improvement_large_enough_to_plan_smoke",
            "passed": speedup >= DEFAULT_MIN_SYNTHETIC_TO_SMOKE_SPEEDUP,
            "previous_smoke_max_latency_ms": previous_latency,
            "optimized_total_logging_max_case_p95_ms": optimized_total,
            "speedup_vs_previous_smoke": speedup,
            "threshold": DEFAULT_MIN_SYNTHETIC_TO_SMOKE_SPEEDUP,
        },
        {
            "name": "optimized_cases_have_no_failed_checks",
            "passed": bool(optimized_benchmark.get("cases"))
            and all(
                case.get("passed") is True
                and not [c for c in case.get("checks", []) if not c.get("passed")]
                for case in optimized_benchmark.get("cases", [])
            ),
            "case_count": len(optimized_benchmark.get("cases", [])),
        },
    ]


def _plan_checks(smoke: SmokeSpec) -> list[dict[str, Any]]:
    formal_seeds = {11, 12, 13}
    return [
        {
            "name": "nonformal_seed",
            "passed": smoke.seed not in formal_seeds,
            "value": smoke.seed,
        },
        {
            "name": "tiny_three_step_scope",
            "passed": smoke.steps == 3,
            "value": smoke.steps,
        },
        {
            "name": "fixed_candidate_pool_size",
            "passed": smoke.num_candidates == 8,
            "value": smoke.num_candidates,
        },
        {
            "name": "optimized_root_is_distinct",
            "passed": "optimized" in smoke.root
            and not smoke.root.rstrip("/").endswith("camp_dp_progress_support_logging_smoke"),
            "root": smoke.root,
        },
        {
            "name": "progress_support_horizon_unchanged",
            "passed": smoke.progress_support_steps == 10,
            "value": smoke.progress_support_steps,
        },
        {
            "name": "progress_support_dt_unchanged",
            "passed": abs(smoke.progress_support_dt_s - 0.1) <= 1e-12,
            "value": smoke.progress_support_dt_s,
        },
    ]


def _aggregate_max_p95(aggregate: dict[str, Any], field: str) -> float:
    summary = aggregate.get(field, {})
    if not isinstance(summary, dict):
        return float("inf")
    return float(summary.get("max_case_p95_ms", float("inf")))


def _previous_smoke_latency(smoke: dict[str, Any], field: str) -> float:
    latency = smoke.get("latency_ms", {})
    if not isinstance(latency, dict):
        return 0.0
    return float(latency.get(field, 0.0))


def _comparison(
    optimized_benchmark: dict[str, Any],
    previous_smoke: dict[str, Any],
) -> dict[str, Any]:
    optimized_total = _aggregate_max_p95(
        optimized_benchmark.get("aggregate", {}),
        REQUIRED_LATENCY_FIELD,
    )
    previous_latency = _previous_smoke_latency(previous_smoke, REQUIRED_LATENCY_FIELD)
    return {
        "previous_smoke_max_progress_support_logging_ms": previous_latency,
        "optimized_synthetic_total_logging_max_case_p95_ms": optimized_total,
        "ratio_previous_smoke_to_optimized_synthetic": (
            previous_latency / optimized_total
            if optimized_total and optimized_total > 0.0
            else float("inf")
        ),
        "comparison_is_cross_context": True,
        "interpretation": (
            "The old value is replay-smoke record latency while the optimized "
            "value is synthetic microbenchmark p95. This is sufficient to "
            "justify a paired smoke design, not to claim online replay "
            "improvement."
        ),
    }


def _accept_criteria(smoke: SmokeSpec) -> list[str]:
    return [
        "both paired replay commands exit 0 in the next gate",
        "no formal seed 11/12/13 appears in any output path or summary",
        "baseline summary reports camp_progress_support_logging.enabled=false",
        "candidate summary reports camp_progress_support_logging.enabled=true",
        "candidate records contain non-null progress_support_logging payloads",
        "payload schema, shapes, finite checks, latency fields, and atom names pass audit",
        "progress_support_atoms are finite and nonnegative for all candidates",
        "candidate_closed_loop_outcomes remain absent",
        "selector log equivalence passes with selected_index, feasibility, atoms, scores, and weights unchanged",
        "dataset audit passes finite-candidate contract checks",
        f"candidate max {REQUIRED_LATENCY_FIELD} is below 25 ms",
        f"scope remains one paired nonformal run with seed={smoke.seed}, steps={smoke.steps}, candidates={smoke.num_candidates}",
    ]


def _reject_criteria() -> list[str]:
    return [
        "optimized synthetic benchmark source is missing, failed, or above design threshold",
        "previous progress-support smoke did not pass or was not latency-blocked",
        "any replay, selector-equivalence, payload, or dataset audit fails in the next gate",
        "any formal seed is detected",
        "any selected_index or CAMP score/atom field changes between baseline and logging-enabled runs",
        "any payload uses future outcome labels or reports selection_effect=true",
        "any progress-support atom is negative, nonfinite, or has an unexpected shape",
        "the smoke is expanded beyond the paired 3-step nonformal scope",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Optimized Progress-Support Logging Smoke Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- paired smoke execution authorized now: `{decision['paired_smoke_execution_authorized']}`",
        f"- replay authorized now: `{decision['new_replay_authorized']}`",
        "",
        "## Comparison",
        "",
        f"- previous smoke max logging ms: `{report['comparison']['previous_smoke_max_progress_support_logging_ms']:.6f}`",
        f"- optimized synthetic max total p95 ms: `{report['comparison']['optimized_synthetic_total_logging_max_case_p95_ms']:.6f}`",
        f"- ratio: `{report['comparison']['ratio_previous_smoke_to_optimized_synthetic']:.6f}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        detail = (
            check.get("status")
            or check.get("previous_status")
            or check.get("optimized_total_logging_max_case_p95_ms")
            or check.get("missing_tokens", "")
        )
        lines.append(f"| `{check['name']}` | `{check['passed']}` | `{detail}` |")
    lines.extend(["", "## Commands", ""])
    for name, command in report["commands"].items():
        lines.append(f"- `{name}`: `{' '.join(command)}`")
    lines.extend(["", "## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
