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
BOOL_OUTCOMES = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline candidate availability/diversity audit for fixed DP "
            "K=8 candidate pools with stored candidate outcomes."
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

    budgets = [_budget_report(records, budget) for budget in PROGRESS_BUDGETS_M]
    return {
        "analysis": {
            "name": "dp_camp_k8_candidate_availability_v1",
            "role": "offline outcome-labeled candidate availability audit",
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "offline labels only",
            "progress_budgets_m": list(PROGRESS_BUDGETS_M),
            "outcome_pareto_definition": (
                "candidate outcome progress within budget, collision/near-miss/"
                "lane/red no worse than selected, jerk and lateral nonworse, "
                "and at least one comfort metric strictly better"
            ),
            "proxy_pareto_definition": (
                "base-feasible candidate with raw progress_shortfall within "
                "budget, union-red and red-stopping nonworse, jerk-excess and "
                "horizon-lateral nonworse, and at least one proxy comfort "
                "metric strictly better"
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
        },
        "diversity": _diversity_report(records),
        "budgets": budgets,
    }


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    feasible = _bool_vector(record.get("feasible_mask"), candidate_count, f"{label} feasible_mask")
    outcomes = _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label)
    atom_names = tuple(record.get("atom_names") or ())
    if "progress_shortfall" not in atom_names:
        raise ValueError(f"{label} is missing progress_shortfall atom.")
    atoms = _matrix(record.get("atoms"), len(atom_names), f"{label} atoms")
    progress_shortfall = atoms[:, atom_names.index("progress_shortfall")]
    return {
        "selected_index": selected_index,
        "feasible": feasible,
        "outcomes": outcomes,
        "progress_shortfall": _finite_nonnegative(
            progress_shortfall,
            candidate_count,
            f"{label} progress_shortfall",
        ),
        "proxy_lateral": _vector(
            record.get("candidate_horizon_lateral_acceleration_cost"),
            candidate_count,
            f"{label} candidate_horizon_lateral_acceleration_cost",
        ),
        "proxy_jerk": _vector(
            record.get("candidate_dp_prior_jerk_excess_cost"),
            candidate_count,
            f"{label} candidate_dp_prior_jerk_excess_cost",
        ),
        "union_red": _vector(
            record.get("candidate_horizon_union_planned_red_light_cost"),
            candidate_count,
            f"{label} candidate_horizon_union_planned_red_light_cost",
        ),
        "red_stopping": _vector(
            record.get("candidate_red_stopping_margin_cost"),
            candidate_count,
            f"{label} candidate_red_stopping_margin_cost",
        ),
    }


def _budget_report(records: list[dict[str, Any]], budget: float) -> dict[str, Any]:
    nonfallback = 0
    outcome_weak = 0
    outcome_joint = 0
    proxy_weak = 0
    proxy_joint = 0
    both_weak = 0
    hidden_outcome_weak = 0
    proxy_only_weak = 0
    best_outcome_deltas: dict[str, list[float]] = {
        "progress_m": [],
        "mean_jerk_mps3": [],
        "mean_lateral_acceleration_mps2": [],
    }
    best_proxy_deltas: dict[str, list[float]] = {
        "progress_shortfall": [],
        "proxy_jerk": [],
        "proxy_lateral": [],
    }
    for record in records:
        feasible = record["feasible"]
        if not feasible.any():
            continue
        nonfallback += 1
        selected = record["selected_index"]
        outcome_mask = _outcome_pareto_mask(record, budget)
        proxy_mask = _proxy_pareto_mask(record, budget)
        outcome_has = bool(outcome_mask.any())
        proxy_has = bool(proxy_mask.any())
        outcome_joint_mask = outcome_mask & _outcome_joint_comfort_mask(record)
        proxy_joint_mask = proxy_mask & _proxy_joint_comfort_mask(record)
        outcome_weak += int(outcome_has)
        outcome_joint += int(outcome_joint_mask.any())
        proxy_weak += int(proxy_has)
        proxy_joint += int(proxy_joint_mask.any())
        both_weak += int(outcome_has and proxy_has)
        hidden_outcome_weak += int(outcome_has and not proxy_has)
        proxy_only_weak += int(proxy_has and not outcome_has)
        if outcome_has:
            best = _best_outcome_candidate(record, outcome_mask)
            best_outcome_deltas["progress_m"].append(
                _outcome_float(record, best, "progress_m")
                - _outcome_float(record, selected, "progress_m")
            )
            best_outcome_deltas["mean_jerk_mps3"].append(
                _outcome_float(record, best, "mean_jerk_mps3")
                - _outcome_float(record, selected, "mean_jerk_mps3")
            )
            best_outcome_deltas["mean_lateral_acceleration_mps2"].append(
                _outcome_float(record, best, "mean_lateral_acceleration_mps2")
                - _outcome_float(record, selected, "mean_lateral_acceleration_mps2")
            )
        if proxy_has:
            best = _best_proxy_candidate(record, proxy_mask)
            best_proxy_deltas["progress_shortfall"].append(
                float(record["progress_shortfall"][best] - record["progress_shortfall"][selected])
            )
            best_proxy_deltas["proxy_jerk"].append(
                float(record["proxy_jerk"][best] - record["proxy_jerk"][selected])
            )
            best_proxy_deltas["proxy_lateral"].append(
                float(record["proxy_lateral"][best] - record["proxy_lateral"][selected])
            )
    denom = max(nonfallback, 1)
    return {
        "progress_budget_m": float(budget),
        "nonfallback_records": int(nonfallback),
        "outcome_weak_records": int(outcome_weak),
        "outcome_weak_rate": outcome_weak / denom,
        "outcome_joint_records": int(outcome_joint),
        "outcome_joint_rate": outcome_joint / denom,
        "proxy_weak_records": int(proxy_weak),
        "proxy_weak_rate": proxy_weak / denom,
        "proxy_joint_records": int(proxy_joint),
        "proxy_joint_rate": proxy_joint / denom,
        "both_weak_records": int(both_weak),
        "both_weak_rate": both_weak / denom,
        "hidden_outcome_weak_records": int(hidden_outcome_weak),
        "hidden_outcome_weak_rate": hidden_outcome_weak / denom,
        "proxy_only_weak_records": int(proxy_only_weak),
        "proxy_only_weak_rate": proxy_only_weak / denom,
        "best_outcome_delta_mean": {
            name: _mean(values) for name, values in best_outcome_deltas.items()
        },
        "best_proxy_delta_mean": {
            name: _mean(values) for name, values in best_proxy_deltas.items()
        },
    }


def _outcome_pareto_mask(record: dict[str, Any], budget: float) -> np.ndarray:
    selected = record["selected_index"]
    size = record["feasible"].size
    mask = record["feasible"].copy()
    mask[selected] = False
    selected_progress = _outcome_float(record, selected, "progress_m")
    mask &= np.asarray(
        [
            _outcome_float(record, idx, "progress_m")
            >= selected_progress - budget - 1e-12
            for idx in range(size)
        ],
        dtype=bool,
    )
    for field in BOOL_OUTCOMES:
        selected_value = bool(record["outcomes"][selected].get(field))
        mask &= np.asarray(
            [
                float(bool(record["outcomes"][idx].get(field)))
                <= float(selected_value)
                for idx in range(size)
            ],
            dtype=bool,
        )
    jerk = np.asarray(
        [_outcome_float(record, idx, "mean_jerk_mps3") for idx in range(size)]
    )
    lateral = np.asarray(
        [
            _outcome_float(record, idx, "mean_lateral_acceleration_mps2")
            for idx in range(size)
        ]
    )
    jerk_nonworse = jerk <= jerk[selected] + 1e-12
    lateral_nonworse = lateral <= lateral[selected] + 1e-12
    jerk_strict = jerk < jerk[selected] - 1e-12
    lateral_strict = lateral < lateral[selected] - 1e-12
    return mask & jerk_nonworse & lateral_nonworse & (jerk_strict | lateral_strict)


def _outcome_joint_comfort_mask(record: dict[str, Any]) -> np.ndarray:
    selected = record["selected_index"]
    size = record["feasible"].size
    jerk = np.asarray(
        [_outcome_float(record, idx, "mean_jerk_mps3") for idx in range(size)]
    )
    lateral = np.asarray(
        [
            _outcome_float(record, idx, "mean_lateral_acceleration_mps2")
            for idx in range(size)
        ]
    )
    return (jerk < jerk[selected] - 1e-12) & (lateral < lateral[selected] - 1e-12)


def _proxy_pareto_mask(record: dict[str, Any], budget: float) -> np.ndarray:
    selected = record["selected_index"]
    mask = record["feasible"].copy()
    mask[selected] = False
    mask &= (
        record["progress_shortfall"]
        <= record["progress_shortfall"][selected] + budget + 1e-12
    )
    mask &= record["union_red"] <= record["union_red"][selected] + 1e-12
    mask &= record["red_stopping"] <= record["red_stopping"][selected] + 1e-12
    jerk_nonworse = record["proxy_jerk"] <= record["proxy_jerk"][selected] + 1e-12
    lateral_nonworse = (
        record["proxy_lateral"] <= record["proxy_lateral"][selected] + 1e-12
    )
    jerk_strict = record["proxy_jerk"] < record["proxy_jerk"][selected] - 1e-12
    lateral_strict = (
        record["proxy_lateral"] < record["proxy_lateral"][selected] - 1e-12
    )
    return mask & jerk_nonworse & lateral_nonworse & (jerk_strict | lateral_strict)


def _proxy_joint_comfort_mask(record: dict[str, Any]) -> np.ndarray:
    selected = record["selected_index"]
    return (
        (record["proxy_jerk"] < record["proxy_jerk"][selected] - 1e-12)
        & (record["proxy_lateral"] < record["proxy_lateral"][selected] - 1e-12)
    )


def _best_outcome_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    jerk = np.asarray(
        [_outcome_float(record, idx, "mean_jerk_mps3") for idx in indices]
    )
    lateral = np.asarray(
        [
            _outcome_float(record, idx, "mean_lateral_acceleration_mps2")
            for idx in indices
        ]
    )
    order = np.lexsort((indices, jerk, lateral))
    return int(indices[order[0]])


def _best_proxy_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    indices = np.flatnonzero(mask)
    order = np.lexsort(
        (
            indices,
            record["proxy_jerk"][indices],
            record["proxy_lateral"][indices],
        )
    )
    return int(indices[order[0]])


def _diversity_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    feasible_counts: list[int] = []
    ranges = {
        "progress_shortfall": [],
        "proxy_jerk": [],
        "proxy_lateral": [],
        "outcome_progress": [],
        "outcome_jerk": [],
        "outcome_lateral": [],
    }
    for record in records:
        feasible = record["feasible"]
        if not feasible.any():
            continue
        feasible_counts.append(int(feasible.sum()))
        for key in ("progress_shortfall", "proxy_jerk", "proxy_lateral"):
            ranges[key].append(float(np.ptp(record[key][feasible])))
        for key, field in (
            ("outcome_progress", "progress_m"),
            ("outcome_jerk", "mean_jerk_mps3"),
            ("outcome_lateral", "mean_lateral_acceleration_mps2"),
        ):
            values = np.asarray(
                [
                    _outcome_float(record, idx, field)
                    for idx in np.flatnonzero(feasible)
                ],
                dtype=np.float64,
            )
            ranges[key].append(float(np.ptp(values)))
    return {
        "mean_feasible_candidates": _mean(feasible_counts),
        "range_mean": {key: _mean(value) for key, value in ranges.items()},
        "range_p50": {key: _percentile(value, 50.0) for key, value in ranges.items()},
        "range_p90": {key: _percentile(value, 90.0) for key, value in ranges.items()},
    }


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _outcome_float(record: dict[str, Any], index: int, field: str) -> float:
    value = float(record["outcomes"][index].get(field))
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"Outcome {field} must be finite and nonnegative.")
    return value


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    return _finite_nonnegative(np.asarray(values, dtype=np.float64), size, label)


def _matrix(values: Any, width: int, label: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != width:
        raise ValueError(f"{label} must have shape [K,{width}].")
    if not np.all(np.isfinite(matrix)) or np.any(matrix < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return matrix


def _finite_nonnegative(values: np.ndarray, size: int, label: str) -> np.ndarray:
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


def _mean(values: list[float] | list[int]) -> float | None:
    return None if not values else float(np.mean(np.asarray(values, dtype=np.float64)))


def _percentile(values: list[float], percentile: float) -> float | None:
    return (
        None
        if not values
        else float(np.percentile(np.asarray(values, dtype=np.float64), percentile))
    )


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    lines = [
        "# DP CAMP K=8 Candidate Availability Audit",
        "",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- Fallback records: {records['fallback']}",
        "",
        "| Progress budget | Outcome weak | Outcome joint | Proxy weak | "
        "Proxy joint | Hidden outcome | Proxy-only | Best progress delta | "
        "Best jerk delta | Best lateral delta |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for budget in report["budgets"]:
        best = budget["best_outcome_delta_mean"]
        lines.append(
            f"| {budget['progress_budget_m']:.2f} | "
            f"{budget['outcome_weak_records']} ({budget['outcome_weak_rate']:.6f}) | "
            f"{budget['outcome_joint_records']} ({budget['outcome_joint_rate']:.6f}) | "
            f"{budget['proxy_weak_records']} ({budget['proxy_weak_rate']:.6f}) | "
            f"{budget['proxy_joint_records']} ({budget['proxy_joint_rate']:.6f}) | "
            f"{budget['hidden_outcome_weak_records']} ({budget['hidden_outcome_weak_rate']:.6f}) | "
            f"{budget['proxy_only_weak_records']} ({budget['proxy_only_weak_rate']:.6f}) | "
            f"{_fmt(best['progress_m'])} | "
            f"{_fmt(best['mean_jerk_mps3'])} | "
            f"{_fmt(best['mean_lateral_acceleration_mps2'])} |"
        )
    diversity = report["diversity"]
    lines.extend(
        [
            "",
            f"- Mean feasible candidates: `{_fmt(diversity['mean_feasible_candidates'])}`",
            f"- Mean outcome jerk range: `{_fmt(diversity['range_mean']['outcome_jerk'])}`",
            f"- Mean outcome lateral range: `{_fmt(diversity['range_mean']['outcome_lateral'])}`",
            f"- Mean proxy jerk range: `{_fmt(diversity['range_mean']['proxy_jerk'])}`",
            f"- Mean proxy lateral range: `{_fmt(diversity['range_mean']['proxy_lateral'])}`",
            "",
            "Candidate outcomes are offline labels only. The proxy side uses "
            "fixed current-tick nonnegative candidate quantities.",
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
