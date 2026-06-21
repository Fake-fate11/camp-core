#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


PAYLOAD_READY_STATUS = "temporal_consistency_payload_smoke_audit_passed"
READY_STATUS = "temporal_consistency_payload_smoke_result_ready"
REJECT_STATUS = "temporal_consistency_payload_smoke_result_rejected"
AUTHORIZED_NEXT_WORK = "default_off_temporal_consistency_broader_nonformal_coverage_plan_only"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
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
            "Evaluate the tiny paired temporal-consistency payload smoke result "
            "without running additional replay or changing selector behavior."
        )
    )
    parser.add_argument("--payload_smoke_json", type=Path, required=True)
    parser.add_argument("--selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--dataset_audit_json", type=Path, required=True)
    parser.add_argument("--baseline_summary_json", type=Path, required=True)
    parser.add_argument("--candidate_summary_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        payload_smoke=_load_json(args.payload_smoke_json),
        selector_equivalence=_load_json(args.selector_equivalence_json),
        dataset_audit=_load_json(args.dataset_audit_json),
        baseline_summary=_load_json(args.baseline_summary_json),
        candidate_summary=_load_json(args.candidate_summary_json),
        label=args.label,
        paths={
            "payload_smoke_json": str(args.payload_smoke_json),
            "selector_equivalence_json": str(args.selector_equivalence_json),
            "dataset_audit_json": str(args.dataset_audit_json),
            "baseline_summary_json": str(args.baseline_summary_json),
            "candidate_summary_json": str(args.candidate_summary_json),
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
    payload_smoke: dict[str, Any],
    selector_equivalence: dict[str, Any],
    dataset_audit: dict[str, Any],
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = _payload_summary(payload_smoke)
    selector = _selector_summary(selector_equivalence)
    dataset = _dataset_summary(dataset_audit)
    summaries = _summary_metadata(baseline_summary, candidate_summary)
    materiality = _materiality_summary(payload)
    checks = [
        *_payload_checks(payload),
        *_selector_checks(selector),
        *_dataset_checks(dataset),
        *_summary_checks(summaries),
        *_materiality_checks(materiality),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_temporal_consistency_payload_smoke_result_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "paths": paths or {},
            "math_boundary": (
                "This result gate evaluates default-off logging evidence only. "
                "The temporal consistency coefficient is fixed before CAMP "
                "scoring and nonnegative when available, so future atomization "
                "could preserve score_k(w)=a_k^T w and the simplex/CVaR/L2 "
                "convex master. The tiny smoke constructs no DP-side classical "
                "Benders master/subproblem, dual, or valid cuts."
            ),
        },
        "payload_summary": payload,
        "selector_equivalence_summary": selector,
        "dataset_audit_summary": dataset,
        "summary_metadata": summaries,
        "materiality_summary": materiality,
        "result_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, materiality),
    }


def _payload_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    counts = report.get("counts") or {}
    latency = (report.get("latency_ms") or {}).get(
        "latency_ms_temporal_consistency_payload",
        {},
    )
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "errors": list(report.get("errors") or []),
        "candidate_records": int(counts.get("candidate_records", -1)),
        "candidate_payload_records": int(counts.get("candidate_payload_records", -1)),
        "available_payload_records": int(counts.get("available_payload_records", -1)),
        "first_tick_fail_closed_records": int(
            counts.get("first_tick_fail_closed_records", -1)
        ),
        "latency_count": int(latency.get("count", 0) or 0),
        "latency_max_ms": latency.get("max"),
        "latency_mean_ms": latency.get("mean"),
    }


def _selector_summary(report: dict[str, Any]) -> dict[str, Any]:
    numeric_mismatches = report.get("numeric_field_mismatches") or {}
    exact_mismatches = report.get("exact_field_mismatches") or {}
    return {
        "equivalent": bool(report.get("equivalent")),
        "records": int(report.get("records", -1)),
        "exact_mismatch_total": int(sum(int(value) for value in exact_mismatches.values())),
        "numeric_mismatch_total": int(
            sum(int(value) for value in numeric_mismatches.values())
        ),
        "numeric_max_abs_diff": report.get("numeric_max_abs_diff") or {},
    }


def _dataset_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": bool(report.get("passed")),
        "errors": list(report.get("errors") or []),
    }


def _summary_metadata(
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
) -> dict[str, Any]:
    key = "camp_temporal_consistency_payload_logging"
    baseline = baseline_summary.get(key) or {}
    candidate = candidate_summary.get(key) or {}
    return {
        "baseline_enabled": bool(baseline.get("enabled")),
        "baseline_records": int(baseline.get("records", -1)),
        "candidate_enabled": bool(candidate.get("enabled")),
        "candidate_records": int(candidate.get("records", -1)),
        "candidate_available_records": int(candidate.get("available_records", -1)),
        "candidate_first_tick_fail_closed_records": int(
            candidate.get("first_tick_fail_closed_records", -1)
        ),
        "selection_effect": bool(candidate.get("selection_effect")),
        "future_outcome_leakage": bool(candidate.get("future_outcome_leakage")),
        "classic_benders_claim": bool(candidate.get("classical_benders_claim")),
    }


def _materiality_summary(payload: dict[str, Any]) -> dict[str, Any]:
    records = payload["candidate_records"]
    available = payload["available_payload_records"]
    tiny_scope = records <= 3
    return {
        "tiny_scope": tiny_scope,
        "available_fraction": (available / records) if records > 0 else 0.0,
        "runtime_equivalence_evidence": True,
        "safety_benefit_evidence": False,
        "sufficient_for_atom_promotion": False,
        "sufficient_for_training": False,
        "sufficient_for_broader_plan": bool(
            payload["passed"]
            and payload["first_tick_fail_closed_records"] == 1
            and available >= 2
        ),
    }


def _payload_checks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("payload_status", payload["status"], PAYLOAD_READY_STATUS),
        _check_equal("payload_passed", payload["passed"], True),
        _check_equal("payload_errors_empty", payload["errors"], []),
        _check_equal("payload_records", payload["candidate_records"], 3),
        _check_equal("payload_records_all_present", payload["candidate_payload_records"], 3),
        _check_equal("payload_available_records", payload["available_payload_records"], 2),
        _check_equal(
            "payload_first_tick_fail_closed",
            payload["first_tick_fail_closed_records"],
            1,
        ),
        _check_equal("payload_latency_count", payload["latency_count"], 3),
    ]


def _selector_checks(selector: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("selector_equivalent", selector["equivalent"], True),
        _check_equal("selector_records", selector["records"], 3),
        _check_equal("selector_exact_mismatch_total", selector["exact_mismatch_total"], 0),
        _check_equal(
            "selector_numeric_mismatch_total",
            selector["numeric_mismatch_total"],
            0,
        ),
    ]


def _dataset_checks(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("dataset_audit_passed", dataset["passed"], True),
        _check_equal("dataset_errors_empty", dataset["errors"], []),
    ]


def _summary_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("baseline_payload_disabled", summary["baseline_enabled"], False),
        _check_equal("baseline_payload_records_zero", summary["baseline_records"], 0),
        _check_equal("candidate_payload_enabled", summary["candidate_enabled"], True),
        _check_equal("candidate_payload_records", summary["candidate_records"], 3),
        _check_equal(
            "candidate_payload_available_records",
            summary["candidate_available_records"],
            2,
        ),
        _check_equal(
            "candidate_first_tick_fail_closed_records",
            summary["candidate_first_tick_fail_closed_records"],
            1,
        ),
        _check_equal("summary_selection_effect_false", summary["selection_effect"], False),
        _check_equal(
            "summary_future_outcome_leakage_false",
            summary["future_outcome_leakage"],
            False,
        ),
        _check_equal(
            "summary_classic_benders_claim_false",
            summary["classic_benders_claim"],
            False,
        ),
    ]


def _materiality_checks(materiality: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal(
            "materiality_not_sufficient_for_atom_promotion",
            materiality["sufficient_for_atom_promotion"],
            False,
        ),
        _check_equal(
            "materiality_not_sufficient_for_training",
            materiality["sufficient_for_training"],
            False,
        ),
        _check_equal(
            "materiality_sufficient_for_broader_plan",
            materiality["sufficient_for_broader_plan"],
            True,
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
        "safety_benefit_evidence": bool(materiality["safety_benefit_evidence"]),
        "atom_promotion_authorized": False,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "next_step": (
            "Plan a broader nonformal coverage smoke that remains default-off "
            "and paired; do not promote atoms, train CAMP, or run Full36 yet."
            if passed
            else "Reject or repair the tiny smoke evidence before broader planning."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Temporal Consistency Payload Smoke Result",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        "",
        "## Summaries",
        "",
        f"- Payload: `{report['payload_summary']}`",
        f"- Selector equivalence: `{report['selector_equivalence_summary']}`",
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


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
