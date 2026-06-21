#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_observable_state_logging_coverage import (
    CoveragePlanSpec,
    READY_STATUS as BASE_READY_STATUS,
    build_report as build_base_coverage_report,
    render_markdown as render_base_markdown,
)


READY_STATUS = "missing_candidate_state_logging_broader_coverage_plan_ready"
REJECT_STATUS = "missing_candidate_state_logging_broader_coverage_plan_rejected"
AUTHORIZED_NEXT_WORK = "default_off_missing_candidate_state_logging_broader_nonformal_paired_smoke_only"

DEFAULT_ROOT = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/"
    "missing_candidate_state_logging_broader_coverage_current_chain"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Current-chain plan gate for broader default-off missing "
            "candidate-state logging coverage after the tiny smoke execution."
        )
    )
    parser.add_argument("--selector_equivalence_json", type=Path, required=True)
    parser.add_argument("--payload_smoke_json", type=Path, required=True)
    parser.add_argument("--dataset_audit_json", type=Path, required=True)
    parser.add_argument("--baseline_summary_json", type=Path, required=True)
    parser.add_argument("--candidate_summary_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=DEFAULT_ROOT)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spec = replace(CoveragePlanSpec(), root=args.output_root)
    report = build_report(
        selector_equivalence=_load_json(args.selector_equivalence_json),
        payload_smoke=_load_json(args.payload_smoke_json),
        dataset_audit=_load_json(args.dataset_audit_json),
        baseline_summary=_load_json(args.baseline_summary_json),
        candidate_summary=_load_json(args.candidate_summary_json),
        label=args.label,
        spec=spec,
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
    spec: CoveragePlanSpec | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    spec = spec or replace(CoveragePlanSpec(), root=DEFAULT_ROOT)
    source_checks = _source_checks(
        selector_equivalence=selector_equivalence,
        payload_smoke=payload_smoke,
        dataset_audit=dataset_audit,
        baseline_summary=baseline_summary,
        candidate_summary=candidate_summary,
    )
    base_report = build_base_coverage_report(label=label, spec=spec)
    passed = (
        all(check["passed"] for check in source_checks)
        and base_report["final_decision"]["status"] == BASE_READY_STATUS
        and bool(base_report["final_decision"]["passed"])
    )
    return {
        "analysis": {
            "name": "dp_camp_missing_candidate_state_broader_coverage_plan_v1",
            "label": label,
            "role": (
                "current-chain plan gate for broader nonformal coverage after "
                "default-off missing candidate-state tiny smoke"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": base_report["analysis"]["math_boundary"],
        },
        "source_tiny_smoke_checks": source_checks,
        "base_coverage_plan": base_report,
        "coverage_targets": base_report["coverage_targets"],
        "commands": base_report["commands"],
        "accept_criteria": [
            "tiny smoke source checks remain passed",
            *base_report["accept_criteria"],
        ],
        "reject_criteria": [
            "tiny smoke source checks fail",
            *base_report["reject_criteria"],
        ],
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "closed_loop_replay_authorized": passed,
            "closed_loop_replay_scope": (
                base_report["final_decision"]["closed_loop_replay_scope"]
                if passed
                else None
            ),
            "full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
            "next_step": (
                "Run only the broader nonformal paired logging commands and "
                "audits emitted in this plan."
                if passed
                else "Repair the tiny-smoke source evidence or base coverage plan."
            ),
        },
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
    dataset_checks = dataset_audit.get("checks") or {}
    baseline_logging = baseline_summary.get("camp_observable_state_logging") or {}
    candidate_logging = candidate_summary.get("camp_observable_state_logging") or {}
    return [
        _check_equal("tiny_selector_equivalent", selector_equivalence.get("equivalent"), True),
        _check_equal("tiny_selector_records", int(selector_equivalence.get("records", 0)), 3),
        _check_equal("tiny_selector_exact_mismatches_zero", sum(selector_exact.values()), 0),
        _check_equal("tiny_selector_numeric_mismatches_zero", sum(selector_numeric.values()), 0),
        _check_equal("tiny_payload_status_passed", payload_final.get("status"), "observable_state_logging_smoke_passed"),
        _check_equal("tiny_payload_passed", payload_final.get("passed"), True),
        _check_equal("tiny_payload_baseline_records_zero", int(payload_counts.get("baseline_payload_records", -1)), 0),
        _check_equal("tiny_payload_candidate_records_three", int(payload_counts.get("candidate_payload_records", -1)), 3),
        _check_equal("tiny_payload_errors_empty", payload_smoke.get("errors") or [], []),
        _check_equal("tiny_dataset_passed", dataset_audit.get("passed"), True),
        _check_equal("tiny_dataset_records", int((dataset_audit.get("counts") or {}).get("records", 0)), 3),
        _check_equal("tiny_dataset_candidates", int((dataset_audit.get("counts") or {}).get("candidates", 0)), 24),
        _check_equal(
            "tiny_dataset_forbids_closed_loop_outcomes",
            dataset_checks.get("closed_loop_outcomes_forbidden"),
            True,
        ),
        _check_equal("tiny_dataset_forbidden_seed_check", dataset_checks.get("forbidden_seed_check"), True),
        _check_equal(
            "tiny_dataset_finite_candidate_contract",
            dataset_checks.get("finite_candidate_contract_verified"),
            True,
        ),
        _check_equal("tiny_baseline_logging_disabled", baseline_logging.get("enabled"), False),
        _check_equal("tiny_baseline_logging_records_zero", int(baseline_logging.get("records", -1)), 0),
        _check_equal("tiny_candidate_logging_enabled", candidate_logging.get("enabled"), True),
        _check_equal("tiny_candidate_logging_records_three", int(candidate_logging.get("records", -1)), 3),
        _check_equal("tiny_candidate_logging_no_leak", candidate_logging.get("future_outcome_leakage"), False),
        _check_equal("tiny_candidate_logging_no_selection_effect", candidate_logging.get("selection_effect"), False),
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    base_md = render_base_markdown(report["base_coverage_plan"])
    lines = [
        "# Missing Candidate-State Broader Coverage Plan",
        "",
        f"- Status: `{decision['status']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Closed-loop replay authorized: `{decision['closed_loop_replay_authorized']}`",
        f"- Scope: `{decision['closed_loop_replay_scope']}`",
        "",
        "## Tiny Smoke Source Checks",
        "",
        "| Check | Passed | Actual | Expected |",
        "| --- | --- | --- | --- |",
    ]
    for check in report["source_tiny_smoke_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('actual')}` | `{check.get('expected')}` |"
        )
    lines.extend(
        [
            "",
            "## Base Coverage Plan",
            "",
            base_md,
            "",
            "This is a plan-only current-chain bridge. It does not itself run DP, "
            "train CAMP, modify DP, promote an online selector, run Full36, or "
            "touch formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
