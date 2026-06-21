#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_REJECT_STATUS = "external_context_payload_materiality_rejected"
DIAGNOSED_STATUS = "external_context_materiality_gap_diagnosed"
REJECT_STATUS = "external_context_materiality_gap_diagnosis_rejected"
AUTHORIZED_NEXT_WORK = "external_context_targeted_materiality_smoke_plan_only"
LOG_NAME = "camp_selection_log.json"

TRAFFIC_SIGNAL_FIELDS = (
    "candidate_first_signal_arrival_time_s",
    "candidate_signal_phase_change_margin_s",
    "candidate_right_of_way_blocked_indicator",
)
ROUTE_SPEED_FIELDS = (
    "candidate_route_speed_limit_min_mps",
    "candidate_speed_limit_excess_integral_mps",
    "candidate_speed_limit_available_fraction",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose why an existing external-context payload smoke failed "
            "materiality. This reads logs only and authorizes only a plan-only "
            "targeted materiality smoke design."
        )
    )
    parser.add_argument("--materiality_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = diagnose(
        materiality=_load_json(args.materiality_json),
        candidate_root=args.candidate_root,
        label=args.label,
        paths={
            "materiality_json": str(args.materiality_json),
            "candidate_root": str(args.candidate_root),
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
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def diagnose(
    *,
    materiality: dict[str, Any],
    candidate_root: Path,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    records = _load_selection_records(candidate_root)
    decision = materiality.get("final_decision") or {}
    source_checks = [
        _check_equal(
            "source_status_is_materiality_rejected",
            decision.get("status"),
            SOURCE_REJECT_STATUS,
        ),
        _check_equal("source_passed_false", decision.get("passed"), False),
        _check_equal(
            "source_authorizes_no_atomization",
            decision.get("authorized_next_work"),
            None,
        ),
        _check_equal(
            "source_material_families_empty",
            materiality.get("material_families") or [],
            [],
        ),
    ]
    record_checks = _record_checks(records)
    gap_reports = _gap_reports(materiality=materiality, records=records)
    gap_names = [gap["name"] for gap in gap_reports if gap["present"]]
    passed = (
        all(check["passed"] for check in source_checks)
        and all(check["passed"] for check in record_checks)
        and bool(gap_names)
    )
    return {
        "analysis": {
            "name": "dp_camp_external_context_materiality_gap_diagnosis_v1",
            "label": label,
            "role": (
                "read-only diagnosis of rejected external-context materiality "
                "over existing paired smoke logs"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "paths": paths or {},
            "math_boundary": (
                "This diagnosis reads only current-tick finite-candidate payload "
                "logs and the materiality report. It does not create atoms, run "
                "DP, train CAMP, change the selector, or authorize new replay. "
                "The next allowed action is plan-only targeted smoke design; "
                "any future atom must still preserve score_k(w)=a_k^T w and the "
                "convex simplex/CVaR/L2 master."
            ),
        },
        "source_checks": source_checks,
        "record_checks": record_checks,
        "gap_reports": gap_reports,
        "present_gap_names": gap_names,
        "candidate_payload_snapshot": _payload_snapshot(records),
        "final_decision": _final_decision(passed, gap_names),
    }


def _record_checks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [_check_equal("records_nonempty", bool(records), True)]
    for index, record in enumerate(records):
        payload = record.get("external_context_payload_logging")
        present = isinstance(payload, dict)
        checks.append(_check_equal(f"record_{index}_payload_present", present, True))
        if not present:
            continue
        checks.extend(
            [
                _check_equal(
                    f"record_{index}_selection_effect",
                    payload.get("selection_effect"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_future_outcome_leakage",
                    payload.get("future_outcome_leakage"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_closed_loop_outcome_fields_read",
                    payload.get("closed_loop_outcome_fields_read"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_closed_loop_outcomes_absent",
                    record.get("candidate_closed_loop_outcomes"),
                    None,
                ),
            ]
        )
    return checks


def _gap_reports(
    *,
    materiality: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    field_reports = {
        str(row.get("field")): row for row in materiality.get("field_reports") or []
    }
    traffic_available = [
        bool((record.get("external_context_payload_logging") or {}).get(
            "traffic_signal_context_available"
        ))
        for record in records
    ]
    route_available = [
        bool((record.get("external_context_payload_logging") or {}).get(
            "route_speed_context_available"
        ))
        for record in records
    ]
    speed_excess_values = _collect_field(records, "candidate_speed_limit_excess_integral_mps")
    speed_limit_values = _collect_field(records, "candidate_route_speed_limit_min_mps")
    availability_values = _collect_field(records, "candidate_speed_limit_available_fraction")
    return [
        {
            "name": "traffic_signal_context_absent",
            "present": not any(traffic_available),
            "evidence": {
                "records": len(records),
                "available_records": sum(1 for value in traffic_available if value),
                "fields": list(TRAFFIC_SIGNAL_FIELDS),
            },
            "interpretation": (
                "traffic-signal atom candidates cannot be material because the "
                "runtime payload recorded signal_context=None for this smoke"
            ),
        },
        {
            "name": "route_speed_context_available_but_no_candidate_excess",
            "present": any(route_available) and speed_excess_values and max(speed_excess_values) == 0.0,
            "evidence": {
                "route_speed_available_records": sum(1 for value in route_available if value),
                "speed_excess_min": min(speed_excess_values) if speed_excess_values else None,
                "speed_excess_max": max(speed_excess_values) if speed_excess_values else None,
                "speed_limit_min": min(speed_limit_values) if speed_limit_values else None,
                "speed_limit_max": max(speed_limit_values) if speed_limit_values else None,
            },
            "interpretation": (
                "route speed context was logged, but every candidate stayed at "
                "or below the route speed limit, so the excess atom has no ranking signal"
            ),
        },
        {
            "name": "route_speed_availability_constant",
            "present": bool(availability_values)
            and min(availability_values) == max(availability_values),
            "evidence": {
                "available_fraction_min": min(availability_values) if availability_values else None,
                "available_fraction_max": max(availability_values) if availability_values else None,
                "field_material": bool(
                    (field_reports.get("candidate_speed_limit_available_fraction") or {}).get(
                        "material"
                    )
                ),
            },
            "interpretation": (
                "speed-limit availability was constant across candidates, so a "
                "missing-context atom would not change candidate ordering"
            ),
        },
        {
            "name": "nonmaterial_constant_speed_limit",
            "present": bool(speed_limit_values) and min(speed_limit_values) == max(speed_limit_values),
            "evidence": {
                "speed_limit_min": min(speed_limit_values) if speed_limit_values else None,
                "speed_limit_max": max(speed_limit_values) if speed_limit_values else None,
                "field_material": bool(
                    (field_reports.get("candidate_route_speed_limit_min_mps") or {}).get(
                        "material"
                    )
                ),
            },
            "interpretation": (
                "absolute route speed limit is useful context, but constant "
                "values alone are not a finite-candidate ranking atom"
            ),
        },
    ]


def _payload_snapshot(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    snapshot = []
    for index, record in enumerate(records):
        payload = record.get("external_context_payload_logging")
        if not isinstance(payload, dict):
            continue
        row = {
            "record_index": index,
            "selected_index": record.get("selected_index"),
            "candidate_count": payload.get("candidate_count"),
            "route_speed_context_available": payload.get("route_speed_context_available"),
            "traffic_signal_context_available": payload.get("traffic_signal_context_available"),
        }
        for field in (*ROUTE_SPEED_FIELDS, *TRAFFIC_SIGNAL_FIELDS):
            row[field] = payload.get(field)
        snapshot.append(row)
    return snapshot


def _collect_field(records: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        payload = record.get("external_context_payload_logging")
        if not isinstance(payload, dict):
            continue
        raw = payload.get(field)
        if isinstance(raw, list):
            values.extend(float(value) for value in raw if value is not None)
    return values


def _final_decision(passed: bool, gap_names: list[str]) -> dict[str, Any]:
    return {
        "status": DIAGNOSED_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "gap_names": gap_names,
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
            "Design a plan-only targeted materiality smoke that can expose "
            "candidate-level external-context variation without training, "
            "online selection, Full36, formal seeds, or DP modification."
            if passed
            else "Reject further external-context work until the materiality failure can be diagnosed."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Materiality Gap Diagnosis",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Gap names: `{decision['gap_names']}`",
        f"- New replay authorized: `{decision['new_replay_authorized']}`",
        "",
        "## Gaps",
        "",
    ]
    for gap in report["gap_reports"]:
        lines.append(
            f"- `{gap['name']}`: present=`{gap['present']}`; "
            f"{gap['interpretation']}"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _load_selection_records(candidate_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(candidate_root.rglob(LOG_NAME)):
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        records.extend(row for row in payload if isinstance(row, dict))
    return records


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
