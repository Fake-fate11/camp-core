#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)


PROGRESS_BUDGETS_M = (0.0, 0.05, 0.10, 0.25)
PROGRESS_DENOMINATOR_FLOOR_M = 1.0
METRICS = (
    "horizon_lateral",
    "jerk_excess",
    "horizon_lateral_per_progress",
    "jerk_excess_per_progress",
)
OUTCOME_FIELDS = (
    "progress_m",
    "value",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline progress-normalized comfort diagnostic for DP CAMP "
            "candidate sets. It does not train or change online selection."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def analyze(paths: list[Path]) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    records: list[dict[str, Any]] = []
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, record in enumerate(payload):
            records.append(_load_record(record, f"{log_path} record {index}"))

    screens: list[dict[str, Any]] = []
    for budget in PROGRESS_BUDGETS_M:
        for metric in METRICS:
            screens.append(_screen(records, metric, budget))

    return {
        "analysis": {
            "name": "dp_camp_progress_normalized_comfort_v1",
            "role": "offline fixed-candidate diagnostic",
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": False,
            "progress_budgets_m": list(PROGRESS_BUDGETS_M),
            "progress_denominator_floor_m": PROGRESS_DENOMINATOR_FLOOR_M,
            "metrics": list(METRICS),
            "admissible_set": (
                "base feasible candidates with route progress no worse than "
                "selected minus budget, union-red nonworse, and red-stopping "
                "cost nonworse; baseline retention makes the set nonempty."
            ),
            "convexity_scope": (
                "For a fixed finite candidate set, each diagnostic value is a "
                "current-tick nonnegative constant. If later atomized with "
                "fixed scales, the score remains affine in w. No trajectory "
                "coordinate convexity is claimed."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
        },
        "screens": screens,
    }


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare a positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")

    feasible = _bool_vector(record.get("feasible_mask"), candidate_count, f"{label} feasible_mask")
    route_progress = _vector(
        record.get("candidate_route_progress"),
        candidate_count,
        f"{label} candidate_route_progress",
    )
    horizon_lateral = _vector(
        record.get("candidate_horizon_lateral_acceleration_cost"),
        candidate_count,
        f"{label} candidate_horizon_lateral_acceleration_cost",
    )
    jerk_excess = _vector(
        record.get("candidate_dp_prior_jerk_excess_cost"),
        candidate_count,
        f"{label} candidate_dp_prior_jerk_excess_cost",
    )
    union_red = _vector(
        record.get("candidate_horizon_union_planned_red_light_cost"),
        candidate_count,
        f"{label} candidate_horizon_union_planned_red_light_cost",
    )
    red_stopping = _vector(
        record.get("candidate_red_stopping_margin_cost"),
        candidate_count,
        f"{label} candidate_red_stopping_margin_cost",
    )
    scores = _vector(record.get("selection_scores"), candidate_count, f"{label} selection_scores")
    outcomes = _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label)
    return {
        "selected_index": selected_index,
        "feasible": feasible,
        "route_progress": route_progress,
        "horizon_lateral": horizon_lateral,
        "jerk_excess": jerk_excess,
        "union_red": union_red,
        "red_stopping": red_stopping,
        "scores": scores,
        "outcomes": outcomes,
    }


def _screen(
    records: list[dict[str, Any]],
    metric: str,
    progress_budget_m: float,
) -> dict[str, Any]:
    changed = 0
    nonfallback = 0
    opportunity = 0
    deltas: dict[str, list[float]] = {field: [] for field in OUTCOME_FIELDS}
    changed_deltas: dict[str, list[float]] = {field: [] for field in OUTCOME_FIELDS}
    diagnostic_deltas: dict[str, list[float]] = {
        "route_progress": [],
        "union_red": [],
        "red_stopping": [],
        "horizon_lateral": [],
        "jerk_excess": [],
        "metric": [],
    }
    changed_diagnostic_deltas: dict[str, list[float]] = {
        name: [] for name in diagnostic_deltas
    }

    for record in records:
        baseline = record["selected_index"]
        feasible = record["feasible"]
        if feasible.any():
            nonfallback += 1
            metric_values = _metric_values(record, metric)
            admissible = _admissible(record, progress_budget_m)
            if not admissible[baseline]:
                raise ValueError("Baseline candidate must remain admissible.")
            selected = _argmin_with_tie(metric_values, record["scores"], admissible)
            opportunity += int(
                np.any(metric_values[admissible] < metric_values[baseline] - 1e-12)
            )
        else:
            selected = baseline
            metric_values = _metric_values(record, metric)
        changed_record = selected != baseline
        changed += int(changed_record)
        for field in OUTCOME_FIELDS:
            delta = _outcome_delta(
                record["outcomes"][selected],
                record["outcomes"][baseline],
                field,
            )
            deltas[field].append(delta)
            if changed_record:
                changed_deltas[field].append(delta)
        for field in ("route_progress", "union_red", "red_stopping", "horizon_lateral", "jerk_excess"):
            delta = float(record[field][selected] - record[field][baseline])
            diagnostic_deltas[field].append(delta)
            if changed_record:
                changed_diagnostic_deltas[field].append(delta)
        metric_delta = float(metric_values[selected] - metric_values[baseline])
        diagnostic_deltas["metric"].append(metric_delta)
        if changed_record:
            changed_diagnostic_deltas["metric"].append(metric_delta)

    return {
        "metric": metric,
        "progress_budget_m": float(progress_budget_m),
        "changed_records": int(changed),
        "opportunity_records": int(opportunity),
        "nonfallback_records": int(nonfallback),
        "nonfallback_change_rate": changed / max(nonfallback, 1),
        "nonfallback_opportunity_rate": opportunity / max(nonfallback, 1),
        "outcome_delta_mean": {
            field: _mean(values) for field, values in deltas.items()
        },
        "changed_outcome_delta_mean": {
            field: _mean(values) for field, values in changed_deltas.items()
        },
        "diagnostic_delta_mean": {
            field: _mean(values) for field, values in diagnostic_deltas.items()
        },
        "changed_diagnostic_delta_mean": {
            field: _mean(values) for field, values in changed_diagnostic_deltas.items()
        },
    }


def _metric_values(record: dict[str, Any], metric: str) -> np.ndarray:
    progress = np.maximum(record["route_progress"], PROGRESS_DENOMINATOR_FLOOR_M)
    if metric == "horizon_lateral":
        return record["horizon_lateral"]
    if metric == "jerk_excess":
        return record["jerk_excess"]
    if metric == "horizon_lateral_per_progress":
        return record["horizon_lateral"] / progress
    if metric == "jerk_excess_per_progress":
        return record["jerk_excess"] / progress
    raise ValueError(f"Unknown metric: {metric}")


def _admissible(record: dict[str, Any], progress_budget_m: float) -> np.ndarray:
    baseline = record["selected_index"]
    return (
        record["feasible"]
        & (record["route_progress"] >= record["route_progress"][baseline] - progress_budget_m - 1e-12)
        & (record["union_red"] <= record["union_red"][baseline] + 1e-12)
        & (record["red_stopping"] <= record["red_stopping"][baseline] + 1e-12)
    )


def _argmin_with_tie(
    metric_values: np.ndarray,
    scores: np.ndarray,
    admissible: np.ndarray,
) -> int:
    indices = np.flatnonzero(admissible)
    order = np.lexsort((indices, scores[indices], metric_values[indices]))
    return int(indices[order[0]])


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _outcome_delta(
    selected: dict[str, Any],
    baseline: dict[str, Any],
    field: str,
) -> float:
    left = selected.get(field)
    right = baseline.get(field)
    if isinstance(left, bool) and isinstance(right, bool):
        return float(left) - float(right)
    if left is None or right is None:
        return 0.0
    return float(left) - float(right)


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return vector


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _mean(values: list[float]) -> float | None:
    return None if not values else float(np.mean(np.asarray(values, dtype=np.float64)))


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    lines = [
        "# DP CAMP Progress-Normalized Comfort Diagnostic",
        "",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- Fallback records retained: {records['fallback']}",
        "",
        "| Metric | Progress budget | Changed | Opportunity | Progress delta | "
        "Red delta | Jerk delta | Lateral delta | Value delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for screen in report["screens"]:
        outcome = screen["outcome_delta_mean"]
        lines.append(
            f"| `{screen['metric']}` | "
            f"{screen['progress_budget_m']:.2f} | "
            f"{screen['changed_records']} | "
            f"{screen['opportunity_records']} | "
            f"{_fmt(outcome['progress_m'])} | "
            f"{_fmt(outcome['red_light_violation'])} | "
            f"{_fmt(outcome['mean_jerk_mps3'])} | "
            f"{_fmt(outcome['mean_lateral_acceleration_mps2'])} | "
            f"{_fmt(outcome['value'])} |"
        )
    lines.extend(
        [
            "",
            "The admissible set keeps only base-feasible candidates with "
            "route-progress, union-red, and red-stopping certificates no worse "
            "than the selected candidate within the declared progress budget. "
            "Outcomes are used only for offline evaluation.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def main() -> None:
    args = parse_args()
    paths = list(args.root) + list(args.selection_log)
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(paths)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


if __name__ == "__main__":
    main()
