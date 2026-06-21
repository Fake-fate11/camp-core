#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


READY_STATUS = "external_context_payload_smoke_result_ready"
REJECT_STATUS = "external_context_payload_smoke_result_rejected"
AUTHORIZED_NEXT_WORK = "external_context_payload_materiality_diagnosis_existing_smoke_only"
PAYLOAD_PASS_STATUS = "external_context_payload_smoke_audit_passed"
SUMMARY_KEY = "camp_external_context_payload_logging"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize external-context payload paired smoke outputs and decide "
            "the next allowed evidence gate. This reads audit JSON only; it "
            "does not run Diffusion Planner."
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
    checks = _source_checks(
        selector_equivalence=selector_equivalence,
        payload_smoke=payload_smoke,
        dataset_audit=dataset_audit,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
    )
    passed = all(check["passed"] for check in checks)
    payload_counts = payload_smoke.get("counts") or {}
    decision = {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "closed_loop_replay_authorized": False,
        "new_replay_authorized": False,
        "full36_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_authorized": False,
        "online_selector_authorized": False,
        "camp_retraining_authorized": False,
        "CAMP_retraining_authorized": False,
        "dp_modification_authorized": False,
        "DP_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Diagnose materiality and coverage using the existing paired smoke "
            "logs only. Do not run new replay or train CAMP."
            if passed
            else "Reject this smoke result and inspect the failed source checks."
        ),
    }
    return {
        "analysis": {
            "name": "dp_camp_external_context_payload_smoke_result_v1",
            "label": label,
            "role": (
                "read-only result gate for the paired default-off external-context "
                "payload smoke"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This gate reads only selector-equivalence, payload-audit, "
                "dataset-audit, and validation-summary JSON from an already "
                "executed tiny smoke. It does not create atoms, change CAMP "
                "scores, train CAMP, execute DP, or authorize more replay. Any "
                "future atomization must still use fixed current-tick "
                "finite-candidate coefficients preserving score_k(w)=a_k^T w "
                "and the convex simplex/CVaR/L2 master. No classical Benders "
                "claim is made."
            ),
        },
        "source_checks": checks,
        "observed_counts": {
            "payload_records": int(payload_counts.get("candidate_payload_records", 0)),
            "available_payload_records": int(
                payload_counts.get("available_payload_records", 0)
            ),
            "route_speed_available_records": int(
                payload_counts.get("route_speed_available_records", 0)
            ),
            "traffic_signal_available_records": int(
                payload_counts.get("traffic_signal_available_records", 0)
            ),
        },
        "accept_criteria": [
            "selector equivalence passes with zero exact and numeric mismatches",
            "payload audit passes and has at least one available route-speed payload",
            "dataset audit passes with closed-loop outcomes forbidden",
            "baseline summary has external-context logging disabled with zero records",
            "candidate summary has external-context logging enabled with three records",
            "candidate summary reports no future outcome leakage and no selection effect",
        ],
        "reject_criteria": [
            "any selector, payload, dataset, or summary check fails",
            "all payload records are unavailable",
            "traffic-signal availability is claimed as a pass condition",
            "any closed-loop outcome label appears in deployable smoke logs",
            "any formal seed, Full36, online selector, CAMP retraining, or DP modification is requested",
        ],
        "final_decision": decision,
    }


def _source_checks(
    *,
    selector_equivalence: dict[str, Any],
    payload_smoke: dict[str, Any],
    dataset_audit: dict[str, Any],
    baseline_summary: dict[str, Any],
    candidate_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    selector_exact = selector_equivalence.get("exact_field_mismatches") or {}
    selector_numeric = selector_equivalence.get("numeric_field_mismatches") or {}
    payload_final = payload_smoke.get("final_decision") or {}
    payload_counts = payload_smoke.get("counts") or {}
    dataset_counts = dataset_audit.get("counts") or {}
    dataset_checks = dataset_audit.get("checks") or {}
    baseline_logging = baseline_summary.get(SUMMARY_KEY) or {}
    candidate_logging = candidate_summary.get(SUMMARY_KEY) or {}
    return [
        _check_equal("selector_equivalent", selector_equivalence.get("equivalent"), True),
        _check_equal("selector_records_three", int(selector_equivalence.get("records", 0)), 3),
        _check_equal("selector_exact_mismatches_zero", sum(selector_exact.values()), 0),
        _check_equal("selector_numeric_mismatches_zero", sum(selector_numeric.values()), 0),
        _check_equal("payload_status_passed", payload_final.get("status"), PAYLOAD_PASS_STATUS),
        _check_equal("payload_passed", payload_final.get("passed"), True),
        _check_equal(
            "payload_candidate_records_three",
            int(payload_counts.get("candidate_payload_records", -1)),
            3,
        ),
        _check_greater_equal(
            "payload_available_records_nonzero",
            int(payload_counts.get("available_payload_records", 0)),
            1,
        ),
        _check_greater_equal(
            "payload_route_speed_available_records_nonzero",
            int(payload_counts.get("route_speed_available_records", 0)),
            1,
        ),
        _check_equal("payload_errors_empty", payload_smoke.get("errors") or [], []),
        _check_equal("dataset_passed", dataset_audit.get("passed"), True),
        _check_equal("dataset_records_three", int(dataset_counts.get("records", 0)), 3),
        _check_equal("dataset_candidates_twenty_four", int(dataset_counts.get("candidates", 0)), 24),
        _check_equal(
            "dataset_forbids_closed_loop_outcomes",
            dataset_checks.get("closed_loop_outcomes_forbidden"),
            True,
        ),
        _check_equal("dataset_forbidden_seed_check", dataset_checks.get("forbidden_seed_check"), True),
        _check_equal(
            "dataset_finite_candidate_contract",
            dataset_checks.get("finite_candidate_contract_verified"),
            True,
        ),
        _check_equal("baseline_logging_disabled", baseline_logging.get("enabled"), False),
        _check_equal("baseline_logging_records_zero", int(baseline_logging.get("records", -1)), 0),
        _check_equal("candidate_logging_enabled", candidate_logging.get("enabled"), True),
        _check_equal("candidate_logging_records_three", int(candidate_logging.get("records", -1)), 3),
        _check_equal("candidate_logging_no_leak", candidate_logging.get("future_outcome_leakage"), False),
        _check_equal("candidate_logging_no_selection_effect", candidate_logging.get("selection_effect"), False),
        _check_equal(
            "candidate_logging_no_closed_loop_reads",
            candidate_logging.get("closed_loop_outcome_fields_read"),
            False,
        ),
        _check_equal(
            "candidate_logging_no_classical_benders_claim",
            candidate_logging.get("classical_benders_claim"),
            False,
        ),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Payload Smoke Result",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- New replay authorized: `{decision['new_replay_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Actual | Expected |",
        "| --- | --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('actual')}` | `{check.get('expected')}` |"
        )
    lines.extend(["", "## Observed Counts", ""])
    lines.extend(
        f"- `{key}`: `{value}`" for key, value in report["observed_counts"].items()
    )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _check_greater_equal(name: str, actual: int, expected: int) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual >= expected,
        "actual": actual,
        "expected": f">={expected}",
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
