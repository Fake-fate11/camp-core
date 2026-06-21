#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from scripts.integrations.analyze_diffusion_planner_temporal_consistency_shadow_safety_proxy import (
    BLOCKED_ACTIONS,
    DELTA_TOLERANCE,
    LOG_NAME,
    NO_EVIDENCE_NEXT_WORK,
    PROXY_SPECS,
    READY_STATUS as SOURCE_READY_STATUS,
)


READY_STATUS = "alternative_safety_source_materiality_ready"
REJECT_STATUS = "alternative_safety_source_materiality_rejected"
EXISTING_SOURCE_NEXT_WORK = "predeclare_no_leak_atom_schema_from_existing_safety_source_only"
TARGETED_SUPPORT_NEXT_WORK = "targeted_safety_support_scenario_or_source_design_only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only materiality preflight for alternative current-tick safety "
            "sources after temporal consistency fails the safety-proxy gate."
        )
    )
    parser.add_argument("--safety_proxy_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, required=True)
    parser.add_argument("--expected_records", type=int, required=True)
    parser.add_argument("--expected_candidates", type=int, required=True)
    parser.add_argument("--expected_available_records", type=int, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        safety_proxy_report=_load_json(args.safety_proxy_json),
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        expected_available_records=args.expected_available_records,
        label=args.label,
        paths={
            "safety_proxy_json": str(args.safety_proxy_json),
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


def analyze(
    *,
    safety_proxy_report: dict[str, Any],
    candidate_root: Path,
    expected_logs: int,
    expected_records: int,
    expected_candidates: int,
    expected_available_records: int,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_logs <= 0:
        raise ValueError("expected_logs must be positive.")
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    if expected_available_records < 0:
        raise ValueError("expected_available_records must be nonnegative.")

    source = _source_summary(safety_proxy_report)
    logs = _load_selection_logs(candidate_root)
    records = [
        _record_materiality(
            record=record,
            run_id=run_id,
            record_index=record_index,
            global_index=global_index,
            expected_candidates=expected_candidates,
        )
        for global_index, (run_id, record_index, record) in enumerate(_iter_records(logs))
    ]
    summary = _summary(records, logs)
    checks = [
        *_source_checks(source),
        *_record_count_checks(
            summary,
            expected_logs=expected_logs,
            expected_records=expected_records,
            expected_available_records=expected_available_records,
        ),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_alternative_safety_source_materiality_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "selection_effect": False,
            "paths": paths or {},
            "math_boundary": (
                "This preflight reads existing current-tick candidate proxy "
                "fields after temporal consistency failed to show safety benefit. "
                "Each inspected safety source is a fixed finite nonnegative "
                "candidate coefficient before scoring. If later atomized as "
                "max(source_k, 0) or an equivalent nonnegative hinge, it can enter "
                "score_k(w)=a_k^T w as an affine term and keeps the simplex/CVaR/L2 "
                "master convex. This gate does not train CAMP, execute DP, deploy "
                "a selector, read future outcomes, or claim a DP-side classical "
                "Benders decomposition."
            ),
        },
        "source_summary": source,
        "materiality_records": records,
        "materiality_summary": summary,
        "materiality_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, summary),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "safety_proxy_evidence": bool(final.get("safety_proxy_evidence")),
        "safety_benefit_evidence": bool(final.get("safety_benefit_evidence")),
        "blocked_action_conflicts": conflicts,
    }


def _record_materiality(
    *,
    record: dict[str, Any],
    run_id: str,
    record_index: int,
    global_index: int,
    expected_candidates: int,
) -> dict[str, Any]:
    errors: list[str] = []
    payload = record.get("temporal_consistency_payload_logging")
    available = isinstance(payload, dict) and bool(payload.get("available"))
    if not available:
        return {
            "run_id": run_id,
            "record_index": record_index,
            "global_index": global_index,
            "available": False,
            "passed": True,
            "errors": [],
            "safety_sources": [],
        }
    if record.get("candidate_closed_loop_outcomes") is not None:
        errors.append("candidate_closed_loop_outcomes_present")
    selected_index = _optional_int(record.get("selected_index"))
    if selected_index is None or selected_index < 0 or selected_index >= expected_candidates:
        errors.append("selected_index_invalid")
    source_rows = []
    for spec in [item for item in PROXY_SPECS if item.family == "safety"]:
        vector = _float_vector(_get_path(record, spec.path))
        if len(vector) != expected_candidates:
            errors.append(f"source_shape_mismatch:{spec.name}")
            continue
        if any(value < -DELTA_TOLERANCE or not math.isfinite(value) for value in vector):
            errors.append(f"source_nonfinite_or_negative:{spec.name}")
            continue
        best_value = min(vector)
        selected_value = vector[selected_index] if selected_index is not None else math.nan
        top1_value = vector[0]
        source_rows.append(
            {
                "name": spec.name,
                "range": max(vector) - min(vector),
                "selected_value": selected_value,
                "best_value": best_value,
                "top1_value": top1_value,
                "selected_improvement_available": selected_value - best_value,
                "top1_improvement_available": top1_value - best_value,
                "selected_already_best": selected_value <= best_value + DELTA_TOLERANCE,
                "top1_already_best": top1_value <= best_value + DELTA_TOLERANCE,
                "nonzero_selected": selected_value > DELTA_TOLERANCE,
            }
        )
    return {
        "run_id": run_id,
        "record_index": record_index,
        "global_index": global_index,
        "available": True,
        "selected_index": selected_index,
        "passed": not errors,
        "errors": errors,
        "safety_sources": source_rows,
    }


def _summary(
    records: list[dict[str, Any]],
    logs: list[tuple[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    available = [record for record in records if record.get("available") is True]
    valid = [record for record in available if record.get("passed") is True]
    source_names = [spec.name for spec in PROXY_SPECS if spec.family == "safety"]
    by_source = []
    for name in source_names:
        rows = [
            source
            for record in valid
            for source in record["safety_sources"]
            if source["name"] == name
        ]
        selected_gaps = [
            row["selected_improvement_available"]
            for row in rows
            if row["selected_improvement_available"] > DELTA_TOLERANCE
        ]
        top1_gaps = [
            row["top1_improvement_available"]
            for row in rows
            if row["top1_improvement_available"] > DELTA_TOLERANCE
        ]
        by_source.append(
            {
                "name": name,
                "records": len(rows),
                "nonzero_range_records": sum(row["range"] > DELTA_TOLERANCE for row in rows),
                "selected_not_best_records": len(selected_gaps),
                "selected_improvement_sum": sum(selected_gaps),
                "selected_nonzero_records": sum(bool(row["nonzero_selected"]) for row in rows),
                "top1_not_best_records": len(top1_gaps),
                "top1_improvement_sum": sum(top1_gaps),
                "mean_range": _mean([row["range"] for row in rows]),
            }
        )
    actionable = [
        row for row in by_source if int(row["selected_not_best_records"]) > 0
    ]
    material_but_current_best = [
        row
        for row in by_source
        if int(row["nonzero_range_records"]) > 0
        and int(row["selected_not_best_records"]) == 0
    ]
    return {
        "log_count": len(logs),
        "records": len(records),
        "available_records": len(available),
        "valid_available_records": len(valid),
        "invalid_available_records": len(available) - len(valid),
        "record_error_counts": _error_counts(records),
        "by_source": by_source,
        "actionable_existing_safety_sources": [row["name"] for row in actionable],
        "material_but_current_selection_already_best": [
            row["name"] for row in material_but_current_best
        ],
        "has_actionable_existing_safety_source": bool(actionable),
        "has_material_safety_source": any(
            int(row["nonzero_range_records"]) > 0 for row in by_source
        ),
    }


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal("source_authorizes_alternative_source", source["authorized_next_work"], NO_EVIDENCE_NEXT_WORK),
        _check_equal("source_safety_proxy_evidence_false", source["safety_proxy_evidence"], False),
        _check_equal("source_safety_benefit_evidence_false", source["safety_benefit_evidence"], False),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
    ]


def _record_count_checks(
    summary: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
    expected_available_records: int,
) -> list[dict[str, Any]]:
    return [
        _check_equal("log_count", summary["log_count"], expected_logs),
        _check_equal("record_count", summary["records"], expected_records),
        _check_equal("available_record_count", summary["available_records"], expected_available_records),
        _check_equal("invalid_available_records_zero", summary["invalid_available_records"], 0),
        _check_equal("record_errors_empty", summary["record_error_counts"], {}),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    actionable = bool(summary["has_actionable_existing_safety_source"])
    next_work = None
    if passed:
        next_work = EXISTING_SOURCE_NEXT_WORK if actionable else TARGETED_SUPPORT_NEXT_WORK
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": next_work,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "has_actionable_existing_safety_source": actionable,
        "has_material_safety_source": bool(summary["has_material_safety_source"]),
        "actionable_existing_safety_sources": summary["actionable_existing_safety_sources"],
        "material_but_current_selection_already_best": (
            summary["material_but_current_selection_already_best"]
        ),
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_replay_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Predeclare a no-leak atom schema from the existing actionable safety source."
            if passed and actionable
            else (
                "Design targeted nonformal safety support or a new current-tick source; "
                "existing smoke safety proxies do not expose an improvement opportunity "
                "over the current selected candidates."
                if passed
                else "Repair source or log contract before choosing a new safety source."
            )
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["materiality_summary"]
    lines = [
        "# Alternative Safety Source Materiality",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Has actionable existing safety source: `{decision['has_actionable_existing_safety_source']}`",
        f"- Has material safety source: `{decision['has_material_safety_source']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        "",
        "## Source Summary",
        "",
        "| Source | Nonzero Range Records | Selected Not Best | Selected Gap Sum | Top1 Not Best | Top1 Gap Sum | Mean Range |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["by_source"]:
        lines.append(
            f"| `{row['name']}` | `{row['nonzero_range_records']}` | "
            f"`{row['selected_not_best_records']}` | "
            f"`{row['selected_improvement_sum']}` | "
            f"`{row['top1_not_best_records']}` | "
            f"`{row['top1_improvement_sum']}` | `{row['mean_range']}` |"
        )
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    lines.extend(["## Checks", "", "| Check | Passed | Observed | Expected |", "| --- | ---: | --- | --- |"])
    for check in report["materiality_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _load_selection_logs(root: Path) -> list[tuple[str, list[dict[str, Any]]]]:
    paths = sorted(root.rglob(LOG_NAME))
    result = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        result.append((path.parent.name, [row for row in payload if isinstance(row, dict)]))
    return result


def _iter_records(
    logs: list[tuple[str, list[dict[str, Any]]]],
) -> list[tuple[str, int, dict[str, Any]]]:
    rows: list[tuple[str, int, dict[str, Any]]] = []
    for run_id, records in logs:
        rows.extend((run_id, index, record) for index, record in enumerate(records))
    return rows


def _get_path(record: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = record
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _float_vector(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return []
    return result


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else math.nan


def _error_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for error in record.get("errors") or []:
            counts[error] = counts.get(error, 0) + 1
    return counts


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
