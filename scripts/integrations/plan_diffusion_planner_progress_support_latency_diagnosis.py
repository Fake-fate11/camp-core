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

READY_STATUS = "progress_support_latency_diagnosis_plan_ready"
REJECT_STATUS = "progress_support_latency_diagnosis_plan_rejected"
SOURCE_STATUS = "progress_support_logging_smoke_passed_latency_blocked"
AUTHORIZED_NEXT_WORK = (
    "progress_support_latency_component_instrumentation_unit_tests_only"
)


@dataclass(frozen=True)
class DiagnosisSpec:
    latency_field: str = "latency_ms_progress_support_logging"
    min_blocking_latency_ms: float = 50.0
    exact_equivalence_atol: float = 1e-9
    exact_equivalence_rtol: float = 1e-9
    expected_candidate_count: int = 8
    expected_support_steps: int = 10
    expected_atom_count: int = 7
    component_latency_fields: tuple[str, ...] = (
        "latency_ms_progress_support_route_projection",
        "latency_ms_progress_support_plan_arc",
        "latency_ms_progress_support_speed_profile",
        "latency_ms_progress_support_route_remaining",
        "latency_ms_progress_support_goal_alignment",
        "latency_ms_progress_support_atom_compute",
        "latency_ms_progress_support_payload_serialization",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only gate for progress-support logging latency diagnosis. "
            "It reads the existing smoke audit and helper source, predeclares "
            "component instrumentation and exact-equivalence criteria, and does "
            "not run replay or optimize code."
        )
    )
    parser.add_argument("--smoke_audit_json", type=Path, required=True)
    parser.add_argument("--helper_source", type=Path, default=HELPER_SOURCE)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        smoke_audit_json=args.smoke_audit_json,
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
    smoke_audit_json: Path,
    helper_source: Path = HELPER_SOURCE,
    label: str | None = None,
    spec: DiagnosisSpec = DiagnosisSpec(),
) -> dict[str, Any]:
    smoke_report = _read_json(smoke_audit_json)
    helper_text = _read_text(helper_source)
    source_checks = _source_checks(
        smoke_report=smoke_report,
        helper_text=helper_text,
        spec=spec,
    )
    component_plan = _component_plan()
    exact_equivalence = _exact_equivalence_criteria(spec)
    passed = all(check["passed"] for check in source_checks)
    return {
        "analysis": {
            "name": "dp_camp_progress_support_latency_diagnosis_plan_v1",
            "label": label,
            "source_status": SOURCE_STATUS,
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_modification": False,
            "diffusion_planner_execution": False,
            "closed_loop_replay_authorized": False,
            "future_outcome_labels_used": False,
            "math_boundary": (
                "Latency diagnosis is engineering instrumentation over "
                "current-tick progress-support logging. It must preserve the "
                "same fixed finite-candidate fields and nonnegative atom "
                "coefficients. If atoms later enter CAMP, they remain fixed "
                "coefficients a_k, preserving affine score_k(w)=a_k^T w and "
                "the simplex/CVaR/L2 convex master. This is not a DP-side "
                "classical Benders decomposition."
            ),
        },
        "source": {
            "smoke_audit_json": str(smoke_audit_json),
            "helper_source": str(helper_source),
        },
        "source_checks": source_checks,
        "diagnosis_spec": asdict(spec),
        "dominant_hypothesis": {
            "name": "route_projection_nested_loop_dominates_latency",
            "evidence": (
                "Current helper computes route progress by looping over "
                "candidate, support step, and route segment. The paired smoke "
                "measured progress-support logging max latency above the "
                "blocking threshold."
            ),
            "not_training_explanation": (
                "The observed bottleneck is logging implementation cost, not "
                "CAMP weight quality. Retraining would not reduce the route "
                "projection overhead."
            ),
        },
        "component_plan": component_plan,
        "exact_equivalence_criteria": exact_equivalence,
        "reject_criteria": _reject_criteria(),
        "blocked_actions": {
            "new_replay": True,
            "broader_replay": True,
            "Full36": True,
            "formal_seeds": True,
            "online_selector_promotion": True,
            "CAMP_retraining": True,
            "DP_modification": True,
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
        },
    }


def _source_checks(
    *,
    smoke_report: dict[str, Any],
    helper_text: str | None,
    spec: DiagnosisSpec,
) -> list[dict[str, Any]]:
    final = smoke_report.get("final_decision", {})
    counts = smoke_report.get("counts", {})
    latency = smoke_report.get("latency_ms", {})
    records = smoke_report.get("records", [])
    max_latency = latency.get(spec.latency_field)
    return [
        {
            "name": "smoke_audit_passed",
            "passed": final.get("status") == "progress_support_logging_smoke_passed"
            and final.get("passed") is True,
            "status": final.get("status"),
            "passed_value": final.get("passed"),
        },
        {
            "name": "payload_records_present",
            "passed": int(counts.get("candidate_payload_records", 0)) > 0
            and int(counts.get("baseline_payload_records", -1)) == 0,
            "counts": counts,
        },
        {
            "name": "latency_blocking_threshold_met",
            "passed": isinstance(max_latency, (int, float))
            and float(max_latency) >= spec.min_blocking_latency_ms,
            "latency_field": spec.latency_field,
            "max_latency_ms": max_latency,
            "threshold_ms": spec.min_blocking_latency_ms,
        },
        {
            "name": "payload_shape_scope_matches_plan",
            "passed": all(
                int(record.get("candidate_count", -1)) == spec.expected_candidate_count
                and int(record.get("support_steps", -1)) == spec.expected_support_steps
                and int(record.get("atom_count", -1)) == spec.expected_atom_count
                for record in records
            )
            and bool(records),
            "records": records,
        },
        _check_tokens(
            "helper_has_progress_payload_builder",
            helper_text,
            (
                "def build_progress_support_logging_payload(",
                "_route_progress_profiles(",
                "_plan_arc_length_profiles(",
                "_speed_profiles(",
                "_progress_support_atoms(",
            ),
        ),
        _check_tokens(
            "helper_has_nested_route_projection_loop",
            helper_text,
            (
                "for cand_idx in range(candidates_xy.shape[0])",
                "for step_idx in range(candidates_xy.shape[1])",
                "for seg_idx, segment in enumerate(segments)",
            ),
        ),
    ]


def _component_plan() -> list[dict[str, Any]]:
    return [
        {
            "component": "route_projection",
            "source_function": "_route_progress_profiles",
            "expected_role": "dominant",
            "reason": "O(K * support_steps * route_segments) nearest-segment search",
        },
        {
            "component": "plan_arc",
            "source_function": "_plan_arc_length_profiles",
            "expected_role": "minor",
            "reason": "vectorized candidate step differences",
        },
        {
            "component": "speed_profile",
            "source_function": "_speed_profiles",
            "expected_role": "minor",
            "reason": "vectorized candidate step differences divided by dt",
        },
        {
            "component": "route_remaining",
            "source_function": "_route_cumulative_lengths plus final progress",
            "expected_role": "minor",
            "reason": "route cumulative length plus vectorized final subtraction",
        },
        {
            "component": "goal_alignment",
            "source_function": "_goal_alignment_progress",
            "expected_role": "minor",
            "reason": "single route tangent dot product for candidate endpoints",
        },
        {
            "component": "atom_compute",
            "source_function": "_progress_support_atoms",
            "expected_role": "minor",
            "reason": "small K x atom_count reductions after route progress exists",
        },
        {
            "component": "payload_serialization",
            "source_function": "build_progress_support_logging_payload",
            "expected_role": "measure",
            "reason": "tolist conversion may matter but must not change values",
        },
    ]


def _exact_equivalence_criteria(spec: DiagnosisSpec) -> list[str]:
    return [
        "public build_progress_support_logging_payload signature remains unchanged",
        "schema_version, default_off, selection_effect, future_outcome_leakage, closed_loop_outcome_fields_read, and classical_benders_claim metadata remain unchanged",
        "all five logged field arrays match baseline within "
        f"atol={spec.exact_equivalence_atol}, rtol={spec.exact_equivalence_rtol}",
        "progress_support_atom_names match exactly",
        "progress_support_atoms match baseline within "
        f"atol={spec.exact_equivalence_atol}, rtol={spec.exact_equivalence_rtol}",
        "all finite_checks remain true, including progress_support_atoms_nonnegative",
        "component latency fields are additive diagnostics only and never enter CAMP scoring or feasibility",
        "any later replay smoke must pass selector log equivalence against logging-only baseline",
        "no closed-loop outcomes, formal seeds, DP modification, or CAMP retraining may be used",
    ]


def _reject_criteria() -> list[str]:
    return [
        "source smoke did not pass or has no candidate payload records",
        "progress-support latency is not actually above the blocking threshold",
        "helper source no longer contains the audited progress-support builder",
        "instrumentation would alter payload fields, atoms, scores, feasibility, selected index, or candidate generation",
        "diagnosis requires DP modification, formal seeds, broader replay, online selector promotion, or CAMP retraining",
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
        "# Progress-Support Latency Diagnosis Plan",
        "",
        f"- status: `{decision['status']}`",
        f"- authorized next work: `{decision['authorized_next_work']}`",
        f"- replay authorized: `{decision['replay_authorized']}`",
        "",
        "## Dominant Hypothesis",
        "",
        f"- `{report['dominant_hypothesis']['name']}`",
        f"- {report['dominant_hypothesis']['evidence']}",
        "",
        "## Source Checks",
        "",
        "| Check | Passed | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["source_checks"]:
        detail = check.get("status") or check.get("max_latency_ms") or check.get(
            "missing_tokens", ""
        )
        lines.append(f"| `{check['name']}` | `{check['passed']}` | `{detail}` |")
    lines.extend(["", "## Component Plan", ""])
    lines.extend(
        f"- `{item['component']}`: {item['reason']}"
        for item in report["component_plan"]
    )
    lines.extend(["", "## Exact Equivalence Criteria", ""])
    lines.extend(f"- {item}" for item in report["exact_equivalence_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
