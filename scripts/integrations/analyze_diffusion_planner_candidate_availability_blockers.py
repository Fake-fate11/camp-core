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


BOOL_OUTCOMES = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
DEFAULT_PROGRESS_BUDGETS_M = (0.0, 0.05, 0.10, 0.25)
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline blocker audit for DP+CAMP candidate availability. "
            "Uses stored candidate outcomes as labels only and does not change "
            "the online selector."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--progress_budget_m",
        type=float,
        action="append",
        default=[],
        help="Repeat to override default budgets 0, 0.05, 0.10, 0.25.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    budgets = (
        tuple(args.progress_budget_m)
        if args.progress_budget_m
        else DEFAULT_PROGRESS_BUDGETS_M
    )
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        progress_budgets_m=budgets,
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


def analyze(
    paths: list[Path],
    *,
    label: str | None = None,
    progress_budgets_m: tuple[float, ...] = DEFAULT_PROGRESS_BUDGETS_M,
) -> dict[str, Any]:
    budgets = tuple(_canonical_budget(value) for value in progress_budgets_m)
    if len(set(budgets)) != len(budgets):
        raise ValueError("Progress budgets must be unique.")
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

    nonfallback = [record for record in records if record["feasible"].any()]
    fallback_count = len(records) - len(nonfallback)
    safety_joint_deficits = [
        deficit
        for record in nonfallback
        if (deficit := _min_progress_deficit_for_safety_joint(record)) is not None
    ]
    report = {
        "analysis": {
            "name": "dp_camp_candidate_availability_blockers_v1",
            "role": "offline outcome-labeled blocker audit",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": "candidate outcomes are offline labels only",
            "progress_budgets_m": list(budgets),
            "definitions": {
                "joint_comfort": (
                    "candidate has strictly lower outcome jerk and strictly "
                    "lower outcome lateral acceleration than the selected "
                    "candidate"
                ),
                "safety_nonworse": (
                    "collision, near miss, lane violation, and red-light "
                    "violation are no worse than the selected candidate"
                ),
                "progress_deficit": (
                    "max(0, selected outcome progress minus candidate outcome "
                    "progress)"
                ),
            },
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": len(nonfallback),
            "fallback": fallback_count,
        },
        "funnel": _funnel(nonfallback),
        "safety_joint_progress_deficit_m": _deficit_summary(
            safety_joint_deficits,
            len(nonfallback),
            budgets,
        ),
        "budgets": [_budget_report(nonfallback, budget) for budget in budgets],
    }
    return report


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    feasible = _bool_vector(record.get("feasible_mask"), candidate_count, f"{label} feasible_mask")
    outcomes = _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label)
    return {
        "selected_index": selected_index,
        "feasible": feasible,
        "outcomes": outcomes,
    }


def _funnel(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "feasible_alternative_records": 0,
        "joint_comfort_records": 0,
        "safety_joint_comfort_records": 0,
    }
    candidate_counts = {
        "feasible_alternatives": [],
        "joint_comfort": [],
        "safety_joint_comfort": [],
    }
    for record in records:
        masks = _masks(record, 0.0)
        counts["feasible_alternative_records"] += int(masks["alternative"].any())
        counts["joint_comfort_records"] += int(masks["joint_comfort"].any())
        counts["safety_joint_comfort_records"] += int(
            (masks["joint_comfort"] & masks["safety_nonworse"]).any()
        )
        candidate_counts["feasible_alternatives"].append(
            int(masks["alternative"].sum())
        )
        candidate_counts["joint_comfort"].append(int(masks["joint_comfort"].sum()))
        candidate_counts["safety_joint_comfort"].append(
            int((masks["joint_comfort"] & masks["safety_nonworse"]).sum())
        )
    denom = max(len(records), 1)
    return {
        **{
            key: {
                "records": int(value),
                "rate": value / denom,
            }
            for key, value in counts.items()
        },
        "mean_candidate_counts": {
            key: _mean(values) for key, values in candidate_counts.items()
        },
    }


def _budget_report(records: list[dict[str, Any]], budget: float) -> dict[str, Any]:
    failed = 0
    outcome_joint = 0
    blockers = {
        "no_feasible_alternative": 0,
        "no_joint_comfort_alternative": 0,
        "joint_comfort_progress_blocked": 0,
        "joint_comfort_safety_blocked": 0,
        "joint_comfort_split_progress_safety_blocked": 0,
        "progress_safety_available_but_no_joint_comfort": 0,
        "weak_only_after_progress_safety": 0,
    }
    counts = {
        "feasible_alternatives": [],
        "joint_comfort": [],
        "progress_joint_comfort": [],
        "safety_joint_comfort": [],
        "progress_safety": [],
        "outcome_joint": [],
    }
    for record in records:
        masks = _masks(record, budget)
        outcome_mask = (
            masks["joint_comfort"]
            & masks["progress_ok"]
            & masks["safety_nonworse"]
        )
        has_outcome = bool(outcome_mask.any())
        outcome_joint += int(has_outcome)
        counts["feasible_alternatives"].append(int(masks["alternative"].sum()))
        counts["joint_comfort"].append(int(masks["joint_comfort"].sum()))
        counts["progress_joint_comfort"].append(
            int((masks["joint_comfort"] & masks["progress_ok"]).sum())
        )
        counts["safety_joint_comfort"].append(
            int((masks["joint_comfort"] & masks["safety_nonworse"]).sum())
        )
        counts["progress_safety"].append(
            int((masks["alternative"] & masks["progress_ok"] & masks["safety_nonworse"]).sum())
        )
        counts["outcome_joint"].append(int(outcome_mask.sum()))
        if has_outcome:
            continue
        failed += 1
        _accumulate_blockers(blockers, masks)
    denom = max(len(records), 1)
    failed_denom = max(failed, 1)
    return {
        "progress_budget_m": float(budget),
        "nonfallback_records": len(records),
        "outcome_joint_records": int(outcome_joint),
        "outcome_joint_rate": outcome_joint / denom,
        "failed_records": int(failed),
        "failed_rate": failed / denom,
        "blockers_among_failed": {
            key: {
                "records": int(value),
                "rate": value / failed_denom,
            }
            for key, value in blockers.items()
        },
        "mean_candidate_counts": {key: _mean(value) for key, value in counts.items()},
    }


def _accumulate_blockers(blockers: dict[str, int], masks: dict[str, np.ndarray]) -> None:
    alternative = masks["alternative"]
    joint = masks["joint_comfort"]
    progress = masks["progress_ok"]
    safety = masks["safety_nonworse"]
    progress_safety = alternative & progress & safety
    weak_after_progress_safety = progress_safety & masks["weak_comfort"]
    if not alternative.any():
        blockers["no_feasible_alternative"] += 1
    if not joint.any():
        blockers["no_joint_comfort_alternative"] += 1
    if joint.any() and not (joint & progress).any():
        blockers["joint_comfort_progress_blocked"] += 1
    if joint.any() and not (joint & safety).any():
        blockers["joint_comfort_safety_blocked"] += 1
    if (
        joint.any()
        and (joint & progress).any()
        and (joint & safety).any()
        and not (joint & progress & safety).any()
    ):
        blockers["joint_comfort_split_progress_safety_blocked"] += 1
    if progress_safety.any() and not (progress_safety & joint).any():
        blockers["progress_safety_available_but_no_joint_comfort"] += 1
    if weak_after_progress_safety.any() and not (progress_safety & joint).any():
        blockers["weak_only_after_progress_safety"] += 1


def _masks(record: dict[str, Any], budget: float) -> dict[str, np.ndarray]:
    selected = record["selected_index"]
    size = record["feasible"].size
    alternative = record["feasible"].copy()
    alternative[selected] = False
    selected_progress = _outcome_float(record, selected, "progress_m")
    progress = np.asarray(
        [
            _outcome_float(record, idx, "progress_m")
            >= selected_progress - budget - TOL
            for idx in range(size)
        ],
        dtype=bool,
    )
    safety = alternative.copy()
    for field in BOOL_OUTCOMES:
        selected_value = bool(record["outcomes"][selected].get(field))
        safety &= np.asarray(
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
    jerk_nonworse = jerk <= jerk[selected] + TOL
    lateral_nonworse = lateral <= lateral[selected] + TOL
    jerk_strict = jerk < jerk[selected] - TOL
    lateral_strict = lateral < lateral[selected] - TOL
    joint_comfort = alternative & jerk_strict & lateral_strict
    weak_comfort = (
        alternative
        & jerk_nonworse
        & lateral_nonworse
        & (jerk_strict | lateral_strict)
    )
    return {
        "alternative": alternative,
        "progress_ok": progress,
        "safety_nonworse": safety,
        "joint_comfort": joint_comfort,
        "weak_comfort": weak_comfort,
    }


def _min_progress_deficit_for_safety_joint(record: dict[str, Any]) -> float | None:
    masks = _masks(record, 0.0)
    selected = record["selected_index"]
    candidate_mask = masks["joint_comfort"] & masks["safety_nonworse"]
    indices = np.flatnonzero(candidate_mask)
    if indices.size == 0:
        return None
    selected_progress = _outcome_float(record, selected, "progress_m")
    deficits = [
        max(0.0, selected_progress - _outcome_float(record, int(idx), "progress_m"))
        for idx in indices
    ]
    return float(min(deficits))


def _deficit_summary(
    values: list[float],
    total_records: int,
    budgets: tuple[float, ...],
) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64)
    denom = max(total_records, 1)
    if arr.size == 0:
        return {
            "records_with_safety_joint_comfort": 0,
            "record_rate": 0.0,
            "mean": None,
            "p50": None,
            "p90": None,
            "p95": None,
            "within_budget": {
                f"{budget:.2f}": {"records": 0, "rate": 0.0} for budget in budgets
            },
        }
    return {
        "records_with_safety_joint_comfort": int(arr.size),
        "record_rate": arr.size / denom,
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
        "p95": float(np.percentile(arr, 95.0)),
        "within_budget": {
            f"{budget:.2f}": {
                "records": int(np.sum(arr <= budget + TOL)),
                "rate": float(np.sum(arr <= budget + TOL) / denom),
            }
            for budget in budgets
        },
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


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _canonical_budget(value: float) -> float:
    budget = round(float(value), 8)
    if budget < -TOL:
        raise ValueError("Progress budgets must be nonnegative.")
    return budget


def _mean(values: list[int] | list[float]) -> float | None:
    return None if not values else float(np.mean(np.asarray(values, dtype=np.float64)))


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    lines = [
        "# DP CAMP Candidate Availability Blocker Audit",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- Fallback records: {records['fallback']}",
        "",
        "Candidate outcomes are offline labels only; this report does not change "
        "the online selector.",
        "",
    ]
    funnel = report["funnel"]
    lines.extend(
        [
            "| Funnel quantity | Records | Rate | Mean candidates |",
            "| --- | ---: | ---: | ---: |",
            _funnel_row(
                "feasible alternatives",
                funnel["feasible_alternative_records"],
                funnel["mean_candidate_counts"]["feasible_alternatives"],
            ),
            _funnel_row(
                "joint comfort alternatives",
                funnel["joint_comfort_records"],
                funnel["mean_candidate_counts"]["joint_comfort"],
            ),
            _funnel_row(
                "safety-preserving joint comfort alternatives",
                funnel["safety_joint_comfort_records"],
                funnel["mean_candidate_counts"]["safety_joint_comfort"],
            ),
            "",
        ]
    )
    deficit = report["safety_joint_progress_deficit_m"]
    lines.extend(
        [
            "Safety-preserving joint-comfort minimum progress deficit:",
            "",
            f"- Records: {deficit['records_with_safety_joint_comfort']} "
            f"({deficit['record_rate']:.6f})",
            f"- Mean: `{_fmt(deficit['mean'])}` m",
            f"- P50/P90/P95: `{_fmt(deficit['p50'])}` / "
            f"`{_fmt(deficit['p90'])}` / `{_fmt(deficit['p95'])}` m",
            "",
            "| Progress budget | Outcome joint | Failed | No joint comfort | "
            "Progress blocked | Safety blocked | Split progress/safety | "
            "Progress+safety but no joint | Weak only |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for budget in report["budgets"]:
        blockers = budget["blockers_among_failed"]
        lines.append(
            f"| {budget['progress_budget_m']:.2f} | "
            f"{budget['outcome_joint_records']} ({budget['outcome_joint_rate']:.6f}) | "
            f"{budget['failed_records']} ({budget['failed_rate']:.6f}) | "
            f"{_blocker_cell(blockers['no_joint_comfort_alternative'])} | "
            f"{_blocker_cell(blockers['joint_comfort_progress_blocked'])} | "
            f"{_blocker_cell(blockers['joint_comfort_safety_blocked'])} | "
            f"{_blocker_cell(blockers['joint_comfort_split_progress_safety_blocked'])} | "
            f"{_blocker_cell(blockers['progress_safety_available_but_no_joint_comfort'])} | "
            f"{_blocker_cell(blockers['weak_only_after_progress_safety'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def _funnel_row(
    label: str,
    records: dict[str, float],
    mean_candidates: float | None,
) -> str:
    return (
        f"| {label} | {records['records']} | {records['rate']:.6f} | "
        f"{_fmt(mean_candidates)} |"
    )


def _blocker_cell(value: dict[str, float]) -> str:
    return f"{value['records']} ({value['rate']:.6f})"


if __name__ == "__main__":
    main()
