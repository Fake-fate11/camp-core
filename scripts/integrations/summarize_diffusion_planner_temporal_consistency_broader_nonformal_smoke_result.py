#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PLAN_READY_STATUS = "temporal_consistency_broader_nonformal_smoke_plan_ready"
PLAN_READY_NEXT_WORK = (
    "default_off_temporal_consistency_broader_nonformal_paired_smoke_only"
)
PAYLOAD_READY_STATUS = "temporal_consistency_payload_smoke_audit_passed"
READY_STATUS = "temporal_consistency_broader_nonformal_smoke_result_ready"
REJECT_STATUS = "temporal_consistency_broader_nonformal_smoke_result_rejected"
AUTHORIZED_NEXT_WORK = "temporal_consistency_materiality_diagnosis_existing_broader_smoke_only"
MAX_PAYLOAD_LATENCY_MS = 2.0

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
    "atom_promotion_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize broader nonformal temporal-consistency paired smoke "
            "outputs without executing Diffusion Planner."
        )
    )
    parser.add_argument("--plan_json", type=Path, required=True)
    parser.add_argument("--selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--dataset_audit_json", type=Path, required=True)
    parser.add_argument(
        "--payload_audit_json",
        type=Path,
        action="append",
        default=[],
        help="Per-run temporal consistency payload audit JSON. May be repeated.",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        plan=_load_json(args.plan_json),
        selector_equivalence=_load_json(args.selector_equivalence_json),
        dataset_audit=_load_json(args.dataset_audit_json),
        payload_audits=[
            _load_json(path) for path in sorted(args.payload_audit_json, key=str)
        ],
        label=args.label,
        paths={
            "plan_json": str(args.plan_json),
            "selector_equivalence_json": str(args.selector_equivalence_json),
            "dataset_audit_json": str(args.dataset_audit_json),
            "payload_audit_json": [str(path) for path in sorted(args.payload_audit_json, key=str)],
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    plan: dict[str, Any],
    selector_equivalence: dict[str, Any],
    dataset_audit: dict[str, Any],
    payload_audits: list[dict[str, Any]],
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan_summary = _plan_summary(plan)
    selector_summary = _selector_summary(selector_equivalence)
    dataset_summary = _dataset_summary(dataset_audit)
    payload_summary = _payload_summary(payload_audits)
    materiality = _materiality_summary(plan_summary, payload_summary)
    checks = [
        *_plan_checks(plan_summary),
        *_selector_checks(selector_summary, plan_summary),
        *_dataset_checks(dataset_summary),
        *_payload_checks(payload_summary, plan_summary),
        *_materiality_checks(materiality),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_broader_nonformal_smoke_result_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "paths": paths or {},
            "math_boundary": (
                "This result gate evaluates default-off broader logging "
                "evidence only. The temporal-consistency coefficient is a "
                "fixed current-tick finite-candidate descriptor computed before "
                "CAMP scoring and before closed-loop outcomes; it is nonnegative "
                "when available and fail-closed on the first tick. Future "
                "atomization would still enter as fixed candidate coefficients "
                "a_k, preserving affine score_k(w)=a_k^T w and the "
                "simplex/CVaR/L2 convex master. No DP-side classical Benders "
                "claim is made."
            ),
        },
        "plan_summary": plan_summary,
        "selector_equivalence_summary": selector_summary,
        "dataset_audit_summary": dataset_summary,
        "payload_summary": payload_summary,
        "materiality_summary": materiality,
        "result_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, materiality),
    }


def _plan_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    plan_spec = report.get("plan_spec") or {}
    coverage = report.get("coverage_targets") or {}
    runs = plan_spec.get("runs") or []
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "blocked_action_conflicts": conflicts,
        "run_count": len(runs),
        "steps": int(plan_spec.get("steps", -1)),
        "num_candidates": int(plan_spec.get("num_candidates", -1)),
        "planned_records": int(coverage.get("planned_records", -1)),
        "planned_candidate_rows": int(coverage.get("planned_candidate_rows", -1)),
        "expected_payload_records_per_run": int(
            coverage.get("expected_payload_records_per_run", -1)
        ),
        "expected_available_payload_records_min_per_run": int(
            coverage.get("expected_available_payload_records_min_per_run", -1)
        ),
        "expected_first_tick_fail_closed_per_run": int(
            coverage.get("expected_first_tick_fail_closed_per_run", -1)
        ),
        "max_payload_latency_ms": float(
            coverage.get("max_payload_latency_ms", MAX_PAYLOAD_LATENCY_MS)
        ),
        "scenario_bucket_counts": dict(coverage.get("scenario_bucket_counts") or {}),
    }


def _selector_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "equivalent": bool(report.get("equivalent")),
        "records": int(report.get("records", -1)),
        "exact_mismatch_total": _sum_nested_numbers(report.get("exact_field_mismatches")),
        "numeric_mismatch_total": _sum_nested_numbers(
            report.get("numeric_field_mismatches")
        ),
        "numeric_shape_mismatch_total": _sum_nested_numbers(
            report.get("numeric_shape_mismatches")
        ),
        "numeric_nonexact_total": _sum_nested_numbers(
            report.get("numeric_nonexact_entries")
        ),
    }


def _dataset_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": bool(report.get("passed")),
        "errors": list(report.get("errors") or []),
    }


def _payload_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    per_run = []
    total_records = 0
    total_payload_records = 0
    total_available = 0
    total_first_tick_fail_closed = 0
    latency_max = 0.0
    latency_mean_values = []
    failed_runs = []
    for index, report in enumerate(reports):
        decision = report.get("final_decision") or {}
        counts = report.get("counts") or {}
        latency = (report.get("latency_ms") or {}).get(
            "latency_ms_temporal_consistency_payload",
            {},
        )
        run_id = _run_id_from_analysis(report, fallback=f"payload_{index}")
        passed = decision.get("status") == PAYLOAD_READY_STATUS and decision.get("passed") is True
        records = int(counts.get("candidate_records", -1))
        payload_records = int(counts.get("candidate_payload_records", -1))
        available = int(counts.get("available_payload_records", -1))
        first_tick = int(counts.get("first_tick_fail_closed_records", -1))
        run_latency_max = _float(latency.get("max"))
        run_latency_mean = _float(latency.get("mean"))
        if not passed:
            failed_runs.append(run_id)
        total_records += max(records, 0)
        total_payload_records += max(payload_records, 0)
        total_available += max(available, 0)
        total_first_tick_fail_closed += max(first_tick, 0)
        latency_max = max(latency_max, run_latency_max)
        if run_latency_mean != float("inf"):
            latency_mean_values.append(run_latency_mean)
        per_run.append(
            {
                "run_id": run_id,
                "status": decision.get("status"),
                "passed": passed,
                "records": records,
                "payload_records": payload_records,
                "available_records": available,
                "first_tick_fail_closed_records": first_tick,
                "latency_max_ms": run_latency_max,
                "latency_mean_ms": run_latency_mean,
                "errors": list(report.get("errors") or []),
            }
        )
    return {
        "run_count": len(reports),
        "total_records": total_records,
        "total_payload_records": total_payload_records,
        "total_available_records": total_available,
        "total_first_tick_fail_closed_records": total_first_tick_fail_closed,
        "latency_max_ms": latency_max,
        "latency_mean_of_means_ms": (
            sum(latency_mean_values) / len(latency_mean_values)
            if latency_mean_values
            else float("inf")
        ),
        "failed_runs": failed_runs,
        "per_run": per_run,
    }


def _run_id_from_analysis(report: dict[str, Any], *, fallback: str) -> str:
    analysis = report.get("analysis") or {}
    candidate_root = str(analysis.get("candidate_root") or "")
    if candidate_root:
        return Path(candidate_root).name
    return fallback


def _materiality_summary(
    plan: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    enough_records = payload["total_available_records"] >= 40
    coverage_ready = payload["run_count"] == plan["run_count"] and enough_records
    return {
        "coverage_ready_for_existing_smoke_materiality_diagnosis": coverage_ready,
        "available_fraction": (
            payload["total_available_records"] / payload["total_records"]
            if payload["total_records"] > 0
            else 0.0
        ),
        "runtime_equivalence_evidence": True,
        "safety_benefit_evidence": False,
        "sufficient_for_atom_promotion": False,
        "sufficient_for_training": False,
    }


def _plan_checks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("plan_status", plan["status"], PLAN_READY_STATUS),
        _check_equal("plan_passed", plan["passed"], True),
        _check_equal(
            "plan_authorized_paired_smoke",
            plan["authorized_next_work"],
            PLAN_READY_NEXT_WORK,
        ),
        _check_empty("plan_no_blocked_action_conflicts", plan["blocked_action_conflicts"]),
        _check_equal("plan_run_count", plan["run_count"], 5),
        _check_equal("plan_steps", plan["steps"], 10),
        _check_equal("plan_num_candidates", plan["num_candidates"], 8),
        _check_equal("plan_records", plan["planned_records"], 50),
    ]


def _selector_checks(
    selector: dict[str, Any],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_equal("selector_equivalent", selector["equivalent"], True),
        _check_equal("selector_records", selector["records"], plan["planned_records"]),
        _check_equal("selector_exact_mismatch_total", selector["exact_mismatch_total"], 0),
        _check_equal(
            "selector_numeric_mismatch_total",
            selector["numeric_mismatch_total"],
            0,
        ),
        _check_equal(
            "selector_numeric_shape_mismatch_total",
            selector["numeric_shape_mismatch_total"],
            0,
        ),
        _check_equal(
            "selector_numeric_nonexact_total",
            selector["numeric_nonexact_total"],
            0,
        ),
    ]


def _dataset_checks(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("dataset_audit_passed", dataset["passed"], True),
        _check_equal("dataset_errors_empty", dataset["errors"], []),
    ]


def _payload_checks(
    payload: dict[str, Any],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_equal("payload_run_count", payload["run_count"], plan["run_count"]),
        _check_equal("payload_failed_runs", payload["failed_runs"], []),
        _check_equal("payload_total_records", payload["total_records"], plan["planned_records"]),
        _check_equal(
            "payload_records_all_present",
            payload["total_payload_records"],
            plan["planned_records"],
        ),
        _check_equal(
            "payload_available_records",
            payload["total_available_records"],
            plan["run_count"]
            * plan["expected_available_payload_records_min_per_run"],
        ),
        _check_equal(
            "payload_first_tick_fail_closed",
            payload["total_first_tick_fail_closed_records"],
            plan["run_count"] * plan["expected_first_tick_fail_closed_per_run"],
        ),
        _check_equal(
            "payload_latency_within_broader_budget",
            payload["latency_max_ms"] <= plan["max_payload_latency_ms"],
            True,
        ),
    ]


def _materiality_checks(materiality: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "coverage_ready_for_existing_smoke_materiality_diagnosis",
            materiality["coverage_ready_for_existing_smoke_materiality_diagnosis"],
            True,
        ),
        _check_equal("safety_benefit_not_claimed", materiality["safety_benefit_evidence"], False),
        _check_equal(
            "atom_promotion_not_authorized",
            materiality["sufficient_for_atom_promotion"],
            False,
        ),
        _check_equal(
            "training_not_authorized",
            materiality["sufficient_for_training"],
            False,
        ),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    materiality: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "runtime_equivalence_ready": passed,
        "coverage_ready_for_materiality_diagnosis": bool(
            materiality["coverage_ready_for_existing_smoke_materiality_diagnosis"]
        ),
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Run a read-only existing-smoke materiality diagnosis over temporal "
            "consistency coefficients; do not promote atoms, train CAMP, run "
            "Full36, or use formal seeds."
            if passed
            else "Reject this broader smoke result and inspect failed checks."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Temporal Consistency Broader Nonformal Smoke Result",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        "",
        "## Summaries",
        "",
        f"- Plan: `{report['plan_summary']}`",
        f"- Selector equivalence: `{report['selector_equivalence_summary']}`",
        f"- Dataset audit: `{report['dataset_audit_summary']}`",
        f"- Payload: `{report['payload_summary']}`",
        f"- Materiality: `{report['materiality_summary']}`",
        "",
        "## Mathematical Boundary",
        "",
        report["analysis"]["math_boundary"],
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["result_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _sum_nested_numbers(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_sum_nested_numbers(item) for item in value.values())
    if isinstance(value, list):
        return sum(_sum_nested_numbers(item) for item in value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {"name": name, "observed": value, "expected": [], "passed": len(value) == 0}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
