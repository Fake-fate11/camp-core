#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


DESIGN_READY_STATUS = "candidate_set_consensus_payload_design_ready"
DESIGN_READY_NEXT_WORK = "candidate_set_consensus_existing_log_materiality_screen_only"

READY_STATUS = "candidate_set_consensus_existing_log_materiality_ready"
INSUFFICIENT_STATUS = "candidate_set_consensus_existing_log_materiality_insufficient"
BLOCKED_STATUS = "candidate_set_consensus_existing_log_materiality_blocked"

READY_NEXT_WORK = "candidate_set_consensus_payload_implementation_unit_tests_only"
INSUFFICIENT_NEXT_WORK = "candidate_set_consensus_default_off_payload_logging_preflight_only"

MIN_VALID_RECORDS = 12
MIN_NONZERO_SPREAD_RATE = 0.25
EPS = 1e-9

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
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only existing-log materiality screen for the candidate-set "
            "consensus coefficient. It consumes existing selection logs or "
            "search roots only; it does not run DP, replay, training, or online "
            "selection."
        )
    )
    parser.add_argument("--payload_design_json", type=Path, required=True)
    parser.add_argument("--selection_log_json", type=Path, action="append", default=[])
    parser.add_argument("--search_root", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_materiality", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        payload_design=_load_json(args.payload_design_json),
        selection_log_paths=args.selection_log_json,
        search_roots=args.search_root,
        label=args.label,
        paths={
            "payload_design_json": str(args.payload_design_json),
            "selection_log_json": [str(path) for path in args.selection_log_json],
            "search_root": [str(path) for path in args.search_root],
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
    if args.require_materiality and not report["final_decision"]["materiality_gate_passed"]:
        raise SystemExit(1)


def build_report(
    *,
    payload_design: dict[str, Any],
    selection_log_paths: list[Path] | None = None,
    search_roots: list[Path] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selection_log_paths = selection_log_paths or []
    search_roots = search_roots or []
    design = _design_summary(payload_design)
    discovered = _discover_selection_logs(selection_log_paths, search_roots)
    records = _load_records(discovered)
    record_summaries = [_record_summary(row) for row in records]
    materiality = _materiality_summary(record_summaries)
    checks = [*_design_checks(design), *_materiality_checks(materiality)]
    final = _final_decision(design=design, checks=checks, materiality=materiality)
    return {
        "analysis": {
            "name": "dp_camp_candidate_set_consensus_existing_log_materiality_v1",
            "label": label,
            "role": (
                "read-only existing-log materiality screen for the predeclared "
                "candidate-set consensus coefficient"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used_for_runtime_features": False,
            "paths": paths or {},
            "math_boundary": (
                "The screen recomputes fixed current-tick finite-candidate "
                "coefficients from logged candidate prefixes only. Safety or "
                "oracle outcomes are not used to compute coefficients. If the "
                "coefficient is later atomized, it remains a fixed a_k in "
                "score_k(w)=a_k^T w, preserving convex simplex/CVaR/L2 "
                "optimization over w. No DP-side classical Benders "
                "master/subproblem, dual, or valid cut is constructed."
            ),
        },
        "design_summary": design,
        "input_summary": {
            "explicit_selection_logs": [str(path) for path in selection_log_paths],
            "search_roots": [str(path) for path in search_roots],
            "selection_logs_found": [str(path) for path in discovered],
        },
        "record_summary": materiality,
        "example_records": record_summaries[:5],
        "materiality_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["record_summary"]
    lines = [
        "# Candidate-Set Consensus Existing-Log Materiality",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Materiality gate passed: `{decision['materiality_gate_passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Input Summary",
        "",
        f"- Selection logs found: `{len(report['input_summary']['selection_logs_found'])}`",
        f"- Records scanned: `{summary['records_scanned']}`",
        f"- Valid coefficient records: `{summary['valid_records']}`",
        f"- Missing-prefix records: `{summary['missing_prefix_records']}`",
        f"- Invalid records: `{summary['invalid_records']}`",
        f"- Nonzero-spread rate: `{summary['nonzero_spread_rate']}`",
        f"- Lower-than-selected rate: `{summary['lower_than_selected_rate']}`",
        "",
        "## Checks",
        "",
        "| Check | Passed | Observed | Expected |",
        "| --- | ---: | --- | --- |",
    ]
    for check in report["materiality_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This materiality screen does not authorize replay, CAMP training, "
            "online selector promotion, Full36, formal seeds, DP modification, "
            "or a DP-side classical Benders claim.",
            "",
        ]
    )
    return "\n".join(lines)


def compute_candidate_set_consensus_center_rms(prefix: Any) -> np.ndarray:
    candidates = np.asarray(prefix, dtype=np.float64)
    if candidates.ndim != 3 or candidates.shape[0] < 2 or candidates.shape[1] < 2 or candidates.shape[2] < 2:
        raise ValueError("candidate prefix must have shape [K,T,D>=2] with K>=2 and T>=2.")
    if not np.all(np.isfinite(candidates)):
        raise ValueError("candidate prefix must contain only finite values.")
    xy = candidates[:, :, :2]
    center = np.median(xy, axis=0)
    squared_distance = np.sum((xy - center[None, :, :]) ** 2, axis=2)
    costs = np.sqrt(np.mean(squared_distance, axis=1))
    if not np.all(np.isfinite(costs)) or np.any(costs < -EPS):
        raise RuntimeError("candidate-set consensus costs violated the nonnegative finite contract.")
    return np.maximum(costs, 0.0)


def _design_summary(report: dict[str, Any]) -> dict[str, Any]:
    decision = _dict(report.get("final_decision"))
    coefficient = _dict(report.get("coefficient_contract"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(decision.get(key))]
    return {
        "status": decision.get("status"),
        "passed": bool(decision.get("passed")),
        "authorized_next_work": decision.get("authorized_next_work"),
        "payload_design_ready": bool(decision.get("payload_design_ready")),
        "primary_coefficient_name": coefficient.get("primary_coefficient_name"),
        "domain": coefficient.get("domain"),
        "blocked_action_conflicts": conflicts,
    }


def _discover_selection_logs(
    explicit_paths: list[Path],
    search_roots: list[Path],
) -> list[Path]:
    paths: list[Path] = []
    for path in explicit_paths:
        if path.is_file():
            paths.append(path)
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in ("camp_selection_log.json", "selection_log.json"):
            paths.extend(path for path in root.rglob(pattern) if path.is_file())
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return sorted(unique)


def _load_records(selection_logs: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in selection_logs:
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            rows.append({"_path": str(path), "_load_error": str(exc)})
            continue
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            records = payload.get("records") or payload.get("selection_records") or []
        else:
            records = []
        for index, record in enumerate(records):
            if isinstance(record, dict):
                row = dict(record)
                row["_path"] = str(path)
                row["_record_index"] = index
                rows.append(row)
    return rows


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    path = str(record.get("_path") or "")
    index = int(record.get("_record_index") or 0)
    if record.get("_load_error"):
        return {
            "path": path,
            "record_index": index,
            "valid": False,
            "reason": "selection_log_load_error",
            "error": record["_load_error"],
        }
    prefix = record.get("candidate_raw_trajectory_prefix")
    if prefix is None:
        return {
            "path": path,
            "record_index": index,
            "valid": False,
            "reason": "candidate_raw_trajectory_prefix_missing",
        }
    try:
        costs = compute_candidate_set_consensus_center_rms(prefix)
    except (TypeError, ValueError, RuntimeError) as exc:
        return {
            "path": path,
            "record_index": index,
            "valid": False,
            "reason": "candidate_raw_trajectory_prefix_invalid",
            "error": str(exc),
        }
    selected = record.get("selected_index")
    if selected is None:
        selected = record.get("baseline_selected_index")
    selected_valid = isinstance(selected, (int, np.integer)) and 0 <= int(selected) < costs.size
    selected_cost = float(costs[int(selected)]) if selected_valid else None
    lower_than_selected = (
        bool(np.any(costs < float(selected_cost) - EPS)) if selected_valid else None
    )
    return {
        "path": path,
        "record_index": index,
        "valid": True,
        "reason": "ok",
        "candidate_count": int(costs.size),
        "selected_index": int(selected) if selected_valid else None,
        "selected_index_valid": bool(selected_valid),
        "coefficient_min": float(np.min(costs)),
        "coefficient_max": float(np.max(costs)),
        "coefficient_mean": float(np.mean(costs)),
        "coefficient_selected": selected_cost,
        "nonzero_spread": bool(float(np.max(costs) - np.min(costs)) > EPS),
        "lower_than_selected_exists": lower_than_selected,
    }


def _materiality_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in records if row.get("valid") is True]
    invalid = [row for row in records if row.get("valid") is not True]
    missing = [
        row for row in invalid if row.get("reason") == "candidate_raw_trajectory_prefix_missing"
    ]
    nonzero = [row for row in valid if bool(row.get("nonzero_spread"))]
    selected_valid = [row for row in valid if bool(row.get("selected_index_valid"))]
    lower = [
        row
        for row in selected_valid
        if row.get("lower_than_selected_exists") is True
    ]
    valid_count = len(valid)
    return {
        "records_scanned": len(records),
        "valid_records": valid_count,
        "invalid_records": len(invalid),
        "missing_prefix_records": len(missing),
        "selected_index_valid_records": len(selected_valid),
        "minimum_valid_records": MIN_VALID_RECORDS,
        "nonzero_spread_records": len(nonzero),
        "nonzero_spread_rate": _ratio(len(nonzero), valid_count),
        "minimum_nonzero_spread_rate": MIN_NONZERO_SPREAD_RATE,
        "lower_than_selected_records": len(lower),
        "lower_than_selected_rate": _ratio(len(lower), len(selected_valid)),
        "materiality_gate_passed": (
            valid_count >= MIN_VALID_RECORDS
            and _ratio(len(nonzero), valid_count) >= MIN_NONZERO_SPREAD_RATE
        ),
    }


def _design_checks(design: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("design_status", design["status"], DESIGN_READY_STATUS),
        _check_equal("design_gate_passed", design["passed"], True),
        _check_equal("design_payload_ready", design["payload_design_ready"], True),
        _check_equal(
            "design_authorizes_existing_log_materiality",
            design["authorized_next_work"],
            DESIGN_READY_NEXT_WORK,
        ),
        _check_equal(
            "design_primary_coefficient",
            design["primary_coefficient_name"],
            "candidate_set_consensus_center_rms_cost_v1",
        ),
        _check_equal(
            "design_domain_nonnegative",
            design["domain"],
            "nonnegative_finite_scalar_per_candidate",
        ),
        _check_empty("design_no_blocked_actions", design["blocked_action_conflicts"]),
    ]


def _materiality_checks(materiality: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_at_least(
            "materiality_minimum_valid_records",
            materiality["valid_records"],
            MIN_VALID_RECORDS,
        ),
        _check_at_least(
            "materiality_nonzero_spread_rate",
            materiality["nonzero_spread_rate"],
            MIN_NONZERO_SPREAD_RATE,
        ),
    ]


def _final_decision(
    *,
    design: dict[str, Any],
    checks: list[dict[str, Any]],
    materiality: dict[str, Any],
) -> dict[str, Any]:
    design_ready = all(check["passed"] for check in _design_checks(design))
    if not design_ready:
        status = BLOCKED_STATUS
        materiality_gate_passed = False
        primary_gap = "payload_design_not_ready"
        authorized_next_work = None
        next_step = "Repair the candidate-set consensus payload design gate first."
    elif materiality["materiality_gate_passed"]:
        status = READY_STATUS
        materiality_gate_passed = True
        primary_gap = "candidate_set_consensus_existing_logs_show_source_variation"
        authorized_next_work = READY_NEXT_WORK
        next_step = (
            "Implement only default-off candidate-set consensus payload unit "
            "tests. Replay, training, and online selector promotion remain blocked."
        )
    else:
        status = INSUFFICIENT_STATUS
        materiality_gate_passed = False
        if materiality["valid_records"] < MIN_VALID_RECORDS:
            primary_gap = "too_few_existing_candidate_prefix_records"
        else:
            primary_gap = "candidate_set_consensus_spread_below_materiality_threshold"
        authorized_next_work = INSUFFICIENT_NEXT_WORK
        next_step = (
            "Existing logs do not prove materiality. Design only a default-off "
            "payload logging/runtime preflight, or reject this source; do not "
            "run replay, train CAMP, or change online selection yet."
        )
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "screen_completed": design_ready,
        "materiality_gate_passed": materiality_gate_passed,
        "primary_gap": primary_gap,
        "authorized_next_work": authorized_next_work,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "payload_implementation_authorized": status == READY_STATUS,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": next_step,
    }


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _check_empty(name: str, observed: Any) -> dict[str, Any]:
    value = list(observed or [])
    return {
        "name": name,
        "observed": value,
        "expected": [],
        "passed": len(value) == 0,
    }


def _check_at_least(name: str, observed: Any, minimum: float) -> dict[str, Any]:
    try:
        value = float(observed)
    except (TypeError, ValueError):
        value = float("nan")
    return {
        "name": name,
        "observed": observed,
        "expected": f">= {minimum}",
        "passed": bool(np.isfinite(value) and value >= float(minimum)),
    }


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
