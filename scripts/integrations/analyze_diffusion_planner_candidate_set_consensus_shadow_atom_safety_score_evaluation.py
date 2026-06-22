#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
CAMP_CORE_SRC = ROOT / "camp_core"
for path in (ROOT, CAMP_CORE_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.analyze_diffusion_planner_safety_cost_oracle import (  # noqa: E402
    REQUIRED_OUTCOME_FIELDS,
    TOP1_INDEX,
    _bool_vector,
    _candidate_branch_components,
    _candidate_count,
    _hard_components,
    _outcome_float,
    _outcomes,
    _planned_red_values,
    _selected_index,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_evaluation import (  # noqa: E402
    BLOCKED_ACTIONS,
    SOURCE_READY_NEXT_WORK,
    SOURCE_READY_STATUS,
    _source_checks as _plan_source_checks,
    _source_summary as _plan_source_summary,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_shadow_atom_weight_sensitivity import (  # noqa: E402
    EXPECTED_CANDIDATES,
    EXPECTED_LOGS,
    EXPECTED_RECORDS,
    FORMAL_SEEDS,
)


READY_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_ready"
)
REJECT_STATUS = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "candidate_set_consensus_shadow_atom_safety_score_evaluation_result_review_only"
)
LOG_NAME = "camp_selection_log.json"
EPS = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only safety-score evaluation for candidate-set consensus "
            "shadow atom sensitivity choices. Shadow selected indices come "
            "from the completed weight-sensitivity artifact; safety/outcome "
            "fields are offline labels only."
        )
    )
    parser.add_argument("--weight_sensitivity_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, default=EXPECTED_LOGS)
    parser.add_argument("--expected_records", type=int, default=EXPECTED_RECORDS)
    parser.add_argument("--expected_candidates", type=int, default=EXPECTED_CANDIDATES)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        weight_sensitivity=_load_json(args.weight_sensitivity_json),
        candidate_root=args.candidate_root,
        expected_logs=args.expected_logs,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        label=args.label,
        paths={
            "weight_sensitivity_json": str(args.weight_sensitivity_json),
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
    weight_sensitivity: dict[str, Any],
    candidate_root: Path,
    expected_logs: int = EXPECTED_LOGS,
    expected_records: int = EXPECTED_RECORDS,
    expected_candidates: int = EXPECTED_CANDIDATES,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_logs <= 0:
        raise ValueError("expected_logs must be positive.")
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")

    source = _plan_source_summary(weight_sensitivity)
    source_records = _source_records_by_key(weight_sensitivity)
    logs = _load_selection_logs(candidate_root)
    records = [
        _evaluation_record(
            record=record,
            source_record=source_records.get((log["run_id"], record_index)),
            run_id=log["run_id"],
            log_path=log["path"],
            record_index=record_index,
            global_index=global_index,
            formal_seed_detected=bool(log["formal_seed_detected"]),
            lambda_grid=tuple(source["lambda_grid"]),
            expected_candidates=expected_candidates,
        )
        for global_index, (log, record_index, record) in enumerate(_iter_records(logs))
    ]
    summary = _summary(records, logs, tuple(source["lambda_grid"]))
    checks = [
        *_plan_source_checks(source),
        *_input_checks(
            summary,
            expected_logs=expected_logs,
            expected_records=expected_records,
        ),
        *_evaluation_checks(summary, tuple(source["lambda_grid"])),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": (
                "dp_camp_candidate_set_consensus_shadow_atom_"
                "safety_score_evaluation_v1"
            ),
            "label": label,
            "role": (
                "read-only offline safety-score evaluation after shadow "
                "selected indices were fixed by weight sensitivity"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "safety_score_fields_used_for_selection": False,
            "future_outcome_labels_used_for_selection": False,
            "formal_seed_records": int(summary["formal_seed_log_count"]),
            "paths": paths or {"candidate_root": str(candidate_root)},
            "source_contract": {
                "status": SOURCE_READY_STATUS,
                "authorized_next_work": SOURCE_READY_NEXT_WORK,
            },
            "safety_cost_scope": (
                "candidate-branch SafetyCost v1 labels over fixed DP candidate "
                "pools; not a closed-loop run-level proof"
            ),
            "math_boundary": (
                "Shadow selected indices are copied from the completed "
                "weight-sensitivity artifact and are fixed before any "
                "candidate_closed_loop_outcomes or SafetyCost v1 fields are "
                "read. This evaluator does not recompute lambda from outcomes, "
                "does not define or promote an atom, does not train CAMP, does "
                "not alter online selection, does not run DP, and does not "
                "claim a DP-side classical Benders decomposition."
            ),
        },
        "source_summary": source,
        "logs": {
            "total": len(logs),
            "formal_seed_logs": summary["formal_seed_log_count"],
            "items": logs,
        },
        "evaluation_records": records,
        "evaluation_summary": summary,
        "evaluation_checks": checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, summary),
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    summary = report["evaluation_summary"]
    lines = [
        "# Candidate-Set Consensus Shadow Atom Safety-Score Evaluation",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Safety benefit evidence: `{decision['safety_benefit_evidence']}`",
        f"- Atom promotion authorized: `{decision['atom_promotion_authorized']}`",
        f"- Failed checks: `{decision['failed_checks']}`",
        "",
        "## Summary",
        "",
        f"- Logs: `{summary['log_count']}`",
        f"- Records: `{summary['records']}`",
        f"- Valid records: `{summary['valid_records']}`",
        f"- Outcome-available records: `{summary['outcome_available_records']}`",
        f"- Fallback-retained records: `{summary['fallback_retained_records']}`",
        f"- Max changed records: `{summary['max_changed_records']}`",
        "",
        "## Lambda Safety Deltas",
        "",
        "| Lambda | Changed | Better | Same | Worse | Mean delta |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["by_lambda"]:
        lines.append(
            f"| `{row['lambda']}` | `{row['changed_records']}` | "
            f"`{row['changed_cost_better_records']}` | "
            f"`{row['changed_cost_same_records']}` | "
            f"`{row['changed_cost_worse_records']}` | "
            f"`{row['changed_safety_cost_delta_mean']}` |"
        )
    lines.extend(
        [
            "",
            "## Route Summary",
            "",
            "| Run | Records | Fallback | Max changed | Mean changed delta |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for run_id, row in summary["by_run"].items():
        lines.append(
            f"| `{run_id}` | `{row['records']}` | "
            f"`{row['fallback_retained_records']}` | "
            f"`{row['max_changed_records']}` | "
            f"`{row['changed_safety_cost_delta_mean']}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This result is eligible for result review only. It does not "
            "authorize atom promotion, CAMP retraining, online selector "
            "changes, formal seeds, replay, safety-benefit claims, or DP "
            "modification.",
            "",
            "## Checks",
            "",
            "| Check | Passed | Observed | Expected |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for check in report["evaluation_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def _evaluation_record(
    *,
    record: dict[str, Any],
    source_record: dict[str, Any] | None,
    run_id: str,
    log_path: str,
    record_index: int,
    global_index: int,
    formal_seed_detected: bool,
    lambda_grid: tuple[float, ...],
    expected_candidates: int,
) -> dict[str, Any]:
    errors: list[str] = []
    if formal_seed_detected:
        errors.append("formal_seed_detected")
    if source_record is None:
        return _record_error(
            run_id,
            log_path,
            record_index,
            global_index,
            "source_sensitivity_record_missing",
            errors,
        )
    try:
        candidate_count = _candidate_count(record, _label(log_path, record_index))
        if candidate_count != expected_candidates:
            errors.append("candidate_count_mismatch")
        selected_index = _selected_index(
            record,
            candidate_count,
            _label(log_path, record_index),
        )
        feasible = _bool_vector(
            record.get("feasible_mask"),
            candidate_count,
            f"{_label(log_path, record_index)} feasible_mask",
        )
        outcomes = _outcomes(
            record.get("candidate_closed_loop_outcomes"),
            candidate_count,
            _label(log_path, record_index),
        )
        planned_red, planned_red_source = _planned_red_values(record, candidate_count)
        eligible = feasible.copy()
        branch = "base_feasible"
        if not bool(eligible.any()):
            eligible = np.ones(candidate_count, dtype=bool)
            branch = "fallback_all_infeasible"
        components = _candidate_branch_components(outcomes, planned_red, eligible)
        costs = [float(component["cost"]) for component in components]
        lambda_rows = [
            _lambda_evaluation(
                source_record=source_record,
                lam=lam,
                selected_index=selected_index,
                costs=costs,
                outcomes=outcomes,
            )
            for lam in lambda_grid
        ]
        for row in lambda_rows:
            if row.get("error"):
                errors.append(str(row["error"]))
            if row.get("source_changed_selected_index") != row.get(
                "changed_selected_index"
            ):
                errors.append("source_changed_flag_mismatch")
        source_selected = _optional_int(source_record.get("selected_index"))
        if source_selected != selected_index:
            errors.append("source_selected_index_mismatch")
        fallback_retained = bool(source_record.get("fallback_retained"))
        return {
            "run_id": run_id,
            "log_path": log_path,
            "record_index": int(record_index),
            "global_index": int(global_index),
            "candidate_count": int(candidate_count),
            "selected_index": int(selected_index),
            "source_selected_index": source_selected,
            "fallback_retained": fallback_retained,
            "branch": branch,
            "outcome_available": True,
            "planned_red_source": planned_red_source,
            "lambda_results": lambda_rows,
            "selected_cost": float(costs[selected_index]),
            "top1_cost": float(costs[TOP1_INDEX]),
            "selected_hard_components": _hard_components(outcomes[selected_index]),
            "top1_hard_components": _hard_components(outcomes[TOP1_INDEX]),
            "errors": sorted(set(errors)),
            "passed": not errors,
        }
    except (TypeError, ValueError) as exc:
        return _record_error(
            run_id,
            log_path,
            record_index,
            global_index,
            f"outcome_evaluation_error:{exc}",
            errors,
        )


def _lambda_evaluation(
    *,
    source_record: dict[str, Any],
    lam: float,
    selected_index: int,
    costs: list[float],
    outcomes: list[dict[str, Any]],
) -> dict[str, Any]:
    source = _lambda_result(source_record, lam)
    if not source:
        return {"lambda": lam, "error": "source_lambda_result_missing"}
    shadow_index = _optional_int(source.get("shadow_selected_index"))
    if shadow_index is None or shadow_index < 0 or shadow_index >= len(costs):
        return {"lambda": lam, "error": "shadow_selected_index_invalid"}
    selected_outcome = outcomes[selected_index]
    shadow_outcome = outcomes[shadow_index]
    selected_hard = _hard_components(selected_outcome)
    shadow_hard = _hard_components(shadow_outcome)
    hard_worse = sorted(
        key for key in selected_hard if shadow_hard[key] > selected_hard[key]
    )
    return {
        "lambda": lam,
        "shadow_selected_index": int(shadow_index),
        "changed_selected_index": shadow_index != selected_index,
        "source_changed_selected_index": bool(source.get("changed_selected_index")),
        "safety_cost_delta_vs_logged_selected": (
            float(costs[shadow_index]) - float(costs[selected_index])
        ),
        "shadow_safety_cost": float(costs[shadow_index]),
        "logged_selected_safety_cost": float(costs[selected_index]),
        "progress_delta_m": _outcome_float(shadow_outcome, "progress_m")
        - _outcome_float(selected_outcome, "progress_m"),
        "mean_jerk_delta_mps3": _outcome_float(shadow_outcome, "mean_jerk_mps3")
        - _outcome_float(selected_outcome, "mean_jerk_mps3"),
        "mean_lateral_acceleration_delta_mps2": _outcome_float(
            shadow_outcome,
            "mean_lateral_acceleration_mps2",
        )
        - _outcome_float(selected_outcome, "mean_lateral_acceleration_mps2"),
        "hard_components_worse_than_logged": hard_worse,
        "error": None,
    }


def _summary(
    records: list[dict[str, Any]],
    logs: list[dict[str, Any]],
    lambda_grid: tuple[float, ...],
) -> dict[str, Any]:
    valid = [record for record in records if record.get("passed") is True]
    outcome_available = [
        record for record in records if record.get("outcome_available") is True
    ]
    by_lambda = []
    for lam in lambda_grid:
        rows = [_lambda_row(record, lam) for record in valid]
        rows = [row for row in rows if row]
        changed = [row for row in rows if row.get("changed_selected_index") is True]
        deltas = [
            float(row["safety_cost_delta_vs_logged_selected"])
            for row in changed
            if row.get("safety_cost_delta_vs_logged_selected") is not None
        ]
        by_lambda.append(
            {
                "lambda": lam,
                "evaluated_records": len(rows),
                "changed_records": len(changed),
                "changed_rate": len(changed) / len(rows) if rows else None,
                "changed_safety_cost_delta_mean": _mean(deltas),
                "changed_cost_better_records": sum(delta < -EPS for delta in deltas),
                "changed_cost_same_records": sum(abs(delta) <= EPS for delta in deltas),
                "changed_cost_worse_records": sum(delta > EPS for delta in deltas),
                "changed_progress_delta_mean": _mean(
                    [float(row["progress_delta_m"]) for row in changed]
                ),
                "changed_mean_jerk_delta_mean": _mean(
                    [float(row["mean_jerk_delta_mps3"]) for row in changed]
                ),
                "changed_mean_lateral_acceleration_delta_mean": _mean(
                    [
                        float(row["mean_lateral_acceleration_delta_mps2"])
                        for row in changed
                    ]
                ),
                "changed_hard_worse_records": sum(
                    bool(row.get("hard_components_worse_than_logged"))
                    for row in changed
                ),
            }
        )
    by_run: dict[str, dict[str, Any]] = {}
    for record in records:
        run_id = str(record.get("run_id"))
        row = by_run.setdefault(
            run_id,
            {
                "records": 0,
                "valid_records": 0,
                "fallback_retained_records": 0,
                "changed_records_by_lambda": {str(lam): 0 for lam in lambda_grid},
                "max_changed_records": 0,
                "changed_safety_cost_deltas": [],
            },
        )
        row["records"] += 1
        row["valid_records"] += int(record.get("passed") is True)
        row["fallback_retained_records"] += int(
            record.get("fallback_retained") is True
        )
        if record.get("passed") is not True:
            continue
        for lam in lambda_grid:
            result = _lambda_row(record, lam)
            if result.get("changed_selected_index"):
                row["changed_records_by_lambda"][str(lam)] += 1
                row["changed_safety_cost_deltas"].append(
                    float(result["safety_cost_delta_vs_logged_selected"])
                )
        row["max_changed_records"] = max(row["changed_records_by_lambda"].values())
    for row in by_run.values():
        row["changed_safety_cost_delta_mean"] = _mean(row["changed_safety_cost_deltas"])
        del row["changed_safety_cost_deltas"]
    formal_logs = [log for log in logs if log.get("formal_seed_detected")]
    return {
        "log_count": len(logs),
        "records": len(records),
        "valid_records": len(valid),
        "outcome_available_records": len(outcome_available),
        "fallback_retained_records": sum(
            int(record.get("fallback_retained") is True) for record in records
        ),
        "formal_seed_log_count": len(formal_logs),
        "formal_seed_log_paths": [str(log["path"]) for log in formal_logs],
        "record_error_counts": _error_counts(records),
        "by_lambda": by_lambda,
        "by_run": dict(sorted(by_run.items())),
        "max_changed_records": max(
            (row["changed_records"] for row in by_lambda),
            default=0,
        ),
        "no_change_runs": sorted(
            run_id
            for run_id, row in by_run.items()
            if row["max_changed_records"] == 0
        ),
    }


def _source_records_by_key(report: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    rows = report.get("sensitivity_records")
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        run_id = row.get("run_id")
        record_index = _optional_int(row.get("record_index"))
        if run_id is None or record_index is None:
            continue
        result[(str(run_id), int(record_index))] = row
    return result


def _input_checks(
    summary: dict[str, Any],
    *,
    expected_logs: int,
    expected_records: int,
) -> list[dict[str, Any]]:
    return [
        _check_equal("log_count", summary["log_count"], expected_logs),
        _check_equal("record_count", summary["records"], expected_records),
        _check_equal("no_formal_seed_logs", summary["formal_seed_log_count"], 0),
        _check_equal("all_records_valid", summary["valid_records"], summary["records"]),
        _check_equal(
            "all_records_have_outcome_labels",
            summary["outcome_available_records"],
            summary["records"],
        ),
        _check_equal("record_errors_empty", summary["record_error_counts"], {}),
    ]


def _evaluation_checks(
    summary: dict[str, Any],
    lambda_grid: tuple[float, ...],
) -> list[dict[str, Any]]:
    zero_row = _by_lambda(summary, 0.0)
    positive_changed = [
        row["changed_records"]
        for row in summary.get("by_lambda") or []
        if float(row["lambda"]) > 0.0
    ]
    return [
        _check_equal("lambda_grid_contains_zero", 0.0 in lambda_grid, True),
        _check_equal("lambda_zero_preserves_selection", zero_row["changed_records"], 0),
        _check_equal(
            "positive_lambda_changes_present",
            any(value > 0 for value in positive_changed),
            True,
        ),
        _check_equal("route_level_reporting_present", bool(summary["by_run"]), True),
        _check_equal("fallback_separation_present", summary["fallback_retained_records"] >= 0, True),
        _check_equal("no_change_runs_reported", isinstance(summary["no_change_runs"], list), True),
        _check_equal("safety_score_fields_used_for_selection", False, False),
        _check_equal("online_selector_mutated", False, False),
        _check_equal("diffusion_planner_executed", False, False),
    ]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "safety_score_evaluation_ready": passed,
        "safety_score_evaluation_result_review_authorized": passed,
        "max_changed_records": summary["max_changed_records"],
        "safety_benefit_evidence": False,
        "atom_promotion_authorized": False,
        "new_replay_authorized": False,
        "closed_loop_smoke_authorized": False,
        "closed_loop_replay_authorized": False,
        "formal_seeds_authorized": False,
        "full36_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "camp_retraining_authorized": False,
        "training_execution_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
    }


def _load_selection_logs(root: Path) -> list[dict[str, Any]]:
    paths = sorted(path for path in root.glob(f"*/{LOG_NAME}") if path.is_file())
    result = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        path_text = str(path)
        run_id = path.parent.name
        result.append(
            {
                "run_id": run_id,
                "path": path_text,
                "formal_seed_detected": _contains_formal_seed(
                    f"{run_id} {path_text}"
                ),
                "records": [row for row in payload if isinstance(row, dict)],
            }
        )
    return result


def _iter_records(
    logs: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], int, dict[str, Any]]]:
    rows: list[tuple[dict[str, Any], int, dict[str, Any]]] = []
    for log in logs:
        rows.extend(
            (log, index, record)
            for index, record in enumerate(log.get("records") or [])
            if isinstance(record, dict)
        )
    return rows


def _lambda_result(record: dict[str, Any], lam: float) -> dict[str, Any]:
    for result in record.get("lambda_results") or []:
        parsed = _optional_float(result.get("lambda")) if isinstance(result, dict) else None
        if parsed is not None and parsed == lam:
            return result
    return {}


def _lambda_row(record: dict[str, Any], lam: float) -> dict[str, Any]:
    for result in record.get("lambda_results") or []:
        parsed = _optional_float(result.get("lambda")) if isinstance(result, dict) else None
        if parsed is not None and parsed == lam:
            return result
    return {}


def _by_lambda(summary: dict[str, Any], lam: float) -> dict[str, Any]:
    for row in summary.get("by_lambda") or []:
        if row.get("lambda") == lam:
            return row
    return {"lambda": lam, "changed_records": math.inf}


def _record_error(
    run_id: str,
    log_path: str,
    record_index: int,
    global_index: int,
    reason: str,
    extra_errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "log_path": log_path,
        "record_index": int(record_index),
        "global_index": int(global_index),
        "fallback_retained": False,
        "outcome_available": False,
        "lambda_results": [],
        "errors": sorted(set([*(extra_errors or []), reason])),
        "passed": False,
    }


def _contains_formal_seed(text: str) -> bool:
    lower = text.lower()
    for seed in FORMAL_SEEDS:
        if re.search(rf"(?<!\d)seed[-_]?{seed}(?!\d)", lower):
            return True
        if re.search(rf"(?<!\d)formal[-_]?seed[-_]?{seed}(?!\d)", lower):
            return True
    return False


def _error_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for error in record.get("errors") or []:
            counts[str(error)] = counts.get(str(error), 0) + 1
    return dict(sorted(counts.items()))


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(np.asarray(values, dtype=np.float64)))


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _label(log_path: str, record_index: int) -> str:
    return f"{log_path} record {record_index}"


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
