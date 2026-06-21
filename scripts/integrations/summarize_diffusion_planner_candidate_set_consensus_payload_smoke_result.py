#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


READY_STATUS = "candidate_set_consensus_payload_smoke_result_ready"
REJECT_STATUS = "candidate_set_consensus_payload_smoke_result_rejected"
PAYLOAD_AUDIT_STATUS = "candidate_set_consensus_payload_smoke_audit_passed"
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_payload_tiny_smoke_materiality_diagnosis_only"
)
SUMMARY_KEY = "camp_candidate_set_consensus_payload_logging"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize a paired default-off candidate-set consensus payload "
            "tiny smoke after selector, payload, dataset, and summary audits."
        )
    )
    parser.add_argument("--selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--payload_smoke_json", type=Path, required=True)
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
        selector_equivalence=_load_json(args.selector_equivalence_json),
        payload_smoke=_load_json(args.payload_smoke_json),
        dataset_audit=_load_json(args.dataset_audit_json),
        baseline_summary=_load_json(args.baseline_summary_json),
        candidate_summary=_load_json(args.candidate_summary_json),
        label=args.label,
        paths={
            "selector_equivalence_json": str(args.selector_equivalence_json),
            "payload_smoke_json": str(args.payload_smoke_json),
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
    selector_equivalence: dict[str, Any],
    payload_smoke: dict[str, Any],
    dataset_audit: dict[str, Any],
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    selector = _selector_summary(selector_equivalence)
    payload = _payload_summary(payload_smoke)
    dataset = _dataset_summary(dataset_audit)
    baseline = _logging_summary(baseline_summary)
    candidate = _logging_summary(candidate_summary)
    checks = [
        *_selector_checks(selector),
        *_payload_checks(payload),
        *_dataset_checks(dataset),
        *_summary_checks(baseline, expected_enabled=False, expected_records=0),
        *_summary_checks(candidate, expected_enabled=True, expected_records=3),
    ]
    passed = all(check["passed"] for check in checks)
    failed_checks = [check["name"] for check in checks if not check["passed"]]
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_payload_smoke_result_v1",
            "label": label,
            "paths": paths or {},
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "formal_seed_records": 0,
            "safety_benefit_evidence": False,
            "math_boundary": (
                "This result gate proves only that default-off candidate-set "
                "consensus payload logging executed in a paired tiny nonformal "
                "smoke without changing selector-visible CAMP fields. It does "
                "not prove that CAMP is safer than DP Top-1 and does not "
                "authorize atom promotion, retraining, Full36, formal seeds, "
                "online selector changes, DP modification, or a DP-side "
                "classical Benders claim. The logged coefficient remains a "
                "fixed finite-candidate nonnegative diagnostic; if later "
                "atomized after separate materiality gates, score_k(w)=a_k^T w "
                "and the simplex/CVaR/L2 master remain convex in w."
            ),
        },
        "selector_summary": selector,
        "payload_summary": payload,
        "dataset_summary": dataset,
        "baseline_summary": baseline,
        "candidate_summary": candidate,
        "checks": checks,
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "failed_checks": failed_checks,
            "runtime_equivalence_ready": passed,
            "payload_logging_ready": passed,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Candidate-Set Consensus Payload Smoke Result",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Runtime equivalence ready: `{decision['runtime_equivalence_ready']}`",
        f"- Payload logging ready: `{decision['payload_logging_ready']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Observed Counts",
        "",
        f"- selector records: `{report['selector_summary']['records']}`",
        f"- payload records: `{report['payload_summary']['candidate_payload_records']}`",
        f"- available payload records: `{report['payload_summary']['available_payload_records']}`",
        f"- dataset records: `{report['dataset_summary']['records']}`",
        f"- dataset candidates: `{report['dataset_summary']['candidates']}`",
        "",
        "## Latency",
        "",
        f"- candidate-set consensus payload max ms: `{report['payload_summary']['latency_max_ms']}`",
        f"- candidate-set consensus payload mean ms: `{report['payload_summary']['latency_mean_ms']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _selector_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "equivalent": bool(report.get("equivalent")),
        "records": report.get("records"),
        "exact_mismatch_total": _sum_values(report.get("exact_field_mismatches")),
        "numeric_mismatch_total": _sum_values(report.get("numeric_field_mismatches")),
        "numeric_max_abs_diff": max(
            [0.0, *[float(value) for value in _dict(report.get("numeric_max_abs_diff")).values()]]
        ),
    }


def _payload_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    counts = _dict(report.get("counts"))
    latency = _dict(report.get("latency_ms"))
    component = _dict(latency.get("latency_ms_candidate_set_consensus_payload"))
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "errors": list(report.get("errors") or []),
        "baseline_logs": counts.get("baseline_logs"),
        "candidate_logs": counts.get("candidate_logs"),
        "records": counts.get("records"),
        "baseline_payload_records": counts.get("baseline_payload_records"),
        "candidate_payload_records": counts.get("candidate_payload_records"),
        "available_payload_records": counts.get("available_payload_records"),
        "invalid_payload_records": counts.get("invalid_payload_records"),
        "latency_count": component.get("count"),
        "latency_mean_ms": component.get("mean"),
        "latency_max_ms": component.get("max"),
    }


def _dataset_summary(report: dict[str, Any]) -> dict[str, Any]:
    counts = _dict(report.get("counts"))
    checks = _dict(report.get("checks"))
    return {
        "passed": bool(report.get("passed")),
        "errors": list(report.get("errors") or []),
        "logs": counts.get("logs"),
        "records": counts.get("records"),
        "candidates": counts.get("candidates"),
        "closed_loop_outcomes_forbidden": checks.get("closed_loop_outcomes_forbidden"),
        "forbidden_seed_check": checks.get("forbidden_seed_check"),
        "finite_candidate_contract_verified": checks.get(
            "finite_candidate_contract_verified"
        ),
    }


def _logging_summary(summary: dict[str, Any]) -> dict[str, Any]:
    metadata = _dict(summary.get(SUMMARY_KEY))
    return {
        "enabled": metadata.get("enabled"),
        "records": metadata.get("records"),
        "available_records": metadata.get("available_records"),
        "invalid_records": metadata.get("invalid_records"),
        "selection_effect": metadata.get("selection_effect"),
        "future_outcome_leakage": metadata.get("future_outcome_leakage"),
        "closed_loop_outcome_fields_read": metadata.get(
            "closed_loop_outcome_fields_read"
        ),
        "online_selector_change": metadata.get("online_selector_change"),
        "deployed_atom_vector_change": metadata.get("deployed_atom_vector_change"),
        "classical_benders_claim": metadata.get("classical_benders_claim"),
    }


def _selector_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("selector_equivalent", summary["equivalent"], True),
        _check_equal("selector_records", summary["records"], 3),
        _check_equal("selector_exact_mismatch_total", summary["exact_mismatch_total"], 0),
        _check_equal(
            "selector_numeric_mismatch_total",
            summary["numeric_mismatch_total"],
            0,
        ),
        _check_equal("selector_numeric_max_abs_diff", summary["numeric_max_abs_diff"], 0.0),
    ]


def _payload_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("payload_audit_status", summary["status"], PAYLOAD_AUDIT_STATUS),
        _check_equal("payload_audit_passed", summary["passed"], True),
        _check_equal("payload_errors_empty", summary["errors"], []),
        _check_equal("payload_baseline_logs", summary["baseline_logs"], 1),
        _check_equal("payload_candidate_logs", summary["candidate_logs"], 1),
        _check_equal("payload_records", summary["records"], 3),
        _check_equal("payload_baseline_records_disabled", summary["baseline_payload_records"], 0),
        _check_equal("payload_candidate_records", summary["candidate_payload_records"], 3),
        _check_equal("payload_available_records", summary["available_payload_records"], 3),
        _check_equal("payload_invalid_records", summary["invalid_payload_records"], 0),
        _check_equal("payload_latency_count", summary["latency_count"], 3),
        _check_lte("payload_latency_max_ms_under_1ms", summary["latency_max_ms"], 1.0),
    ]


def _dataset_checks(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("dataset_audit_passed", summary["passed"], True),
        _check_equal("dataset_errors_empty", summary["errors"], []),
        _check_equal("dataset_logs", summary["logs"], 1),
        _check_equal("dataset_records", summary["records"], 3),
        _check_equal("dataset_candidates", summary["candidates"], 24),
        _check_equal(
            "dataset_closed_loop_outcomes_forbidden",
            summary["closed_loop_outcomes_forbidden"],
            True,
        ),
        _check_equal("dataset_forbidden_seed_check", summary["forbidden_seed_check"], True),
        _check_equal(
            "dataset_finite_candidate_contract",
            summary["finite_candidate_contract_verified"],
            True,
        ),
    ]


def _summary_checks(
    summary: dict[str, Any],
    *,
    expected_enabled: bool,
    expected_records: int,
) -> list[dict[str, Any]]:
    prefix = "candidate" if expected_enabled else "baseline"
    expected_available = expected_records if expected_enabled else 0
    return [
        _check_equal(f"{prefix}_summary_enabled", summary["enabled"], expected_enabled),
        _check_equal(f"{prefix}_summary_records", summary["records"], expected_records),
        _check_equal(
            f"{prefix}_summary_available_records",
            summary["available_records"],
            expected_available,
        ),
        _check_equal(f"{prefix}_summary_invalid_records", summary["invalid_records"], 0),
        _check_equal(f"{prefix}_summary_selection_effect", summary["selection_effect"], False),
        _check_equal(
            f"{prefix}_summary_future_outcome_leakage",
            summary["future_outcome_leakage"],
            False,
        ),
        _check_equal(
            f"{prefix}_summary_closed_loop_fields_read",
            summary["closed_loop_outcome_fields_read"],
            False,
        ),
        _check_equal(
            f"{prefix}_summary_online_selector_change",
            summary["online_selector_change"],
            False,
        ),
        _check_equal(
            f"{prefix}_summary_deployed_atom_vector_change",
            summary["deployed_atom_vector_change"],
            False,
        ),
        _check_equal(
            f"{prefix}_summary_classic_benders_claim",
            summary["classical_benders_claim"],
            False,
        ),
    ]


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_lte(name: str, observed: Any, expected: float) -> dict[str, Any]:
    try:
        value = float(observed)
    except (TypeError, ValueError):
        value = float("inf")
    return {
        "name": name,
        "observed": observed,
        "expected": f"<= {expected}",
        "passed": value <= expected,
    }


def _sum_values(value: Any) -> int:
    return int(sum(int(item) for item in _dict(value).values()))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
