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
from scripts.integrations.analyze_diffusion_planner_first_step_graft_potential import (  # noqa: E402
    TOL,
    _fmt,
    _outcome_float,
    _summary,
)


BOOL_OUTCOMES = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
PROGRESS_BUDGETS_M = (0.05, 0.10, 0.25, 0.50, 1.00)
TARGET_SPEED_LOSS_BUDGETS_MPS = (0.02, 0.05, 0.10, 0.25)
H10_DISPLACEMENT_LOSS_BUDGETS_M = (0.01, 0.05, 0.10, 0.25)
REPORT_TARGET_SPEED_BUDGET_MPS = 0.10
REPORT_H10_BUDGET_M = 0.10
REPORT_PROGRESS_BUDGET_M = 0.50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline bounded tradeoff audit for raw DP candidate geometry. "
            "Outcome labels define oracle comfort donors only; no online "
            "selector is changed."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze([*args.root, *args.selection_log], label=args.label)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(paths: list[Path], *, label: str | None = None) -> dict[str, Any]:
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
    donor_rows = [_donor_rows(record) for record in nonfallback]
    with_donor = sum(int(rows["count"] > 0) for rows in donor_rows)
    grids = []
    for progress_budget in PROGRESS_BUDGETS_M:
        for target_budget in TARGET_SPEED_LOSS_BUDGETS_MPS:
            for h10_budget in H10_DISPLACEMENT_LOSS_BUDGETS_M:
                grids.append(
                    _budget_report(
                        donor_rows,
                        progress_budget=progress_budget,
                        target_budget=target_budget,
                        h10_budget=h10_budget,
                    )
                )

    return {
        "analysis": {
            "name": "dp_camp_bounded_tradeoff_v1",
            "role": (
                "offline budget screen for raw DP candidate geometry and "
                "bounded progress/anchor tradeoffs"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate outcomes define oracle safety-nonworse joint-comfort "
                "donors for diagnosis only"
            ),
            "budgets": {
                "progress_loss_m": list(PROGRESS_BUDGETS_M),
                "target_speed_loss_mps": list(TARGET_SPEED_LOSS_BUDGETS_MPS),
                "h10_displacement_loss_m": list(H10_DISPLACEMENT_LOSS_BUDGETS_M),
            },
            "convexity_boundary": (
                "This is a fixed finite-candidate audit. Budget predicates are "
                "constants per tick. If later atomized, fixed-candidate CAMP "
                "scores remain affine in w. This is not Benders and no global "
                "trajectory convexity is claimed."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": len(nonfallback),
            "fallback": len(records) - len(nonfallback),
            "with_oracle_donor": with_donor,
            "without_oracle_donor": len(nonfallback) - with_donor,
        },
        "oracle_donor_summary": _oracle_summary(donor_rows),
        "budget_grid": grids,
    }


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    prefix = np.asarray(
        record.get("candidate_perfect_tracker_postprocessed_reference_prefix"),
        dtype=np.float64,
    )
    if prefix.ndim != 3 or prefix.shape[0] != candidate_count or prefix.shape[1] < 10:
        raise ValueError(
            f"{label} candidate_perfect_tracker_postprocessed_reference_prefix "
            "must have shape [K,T>=10,D]."
        )
    if prefix.shape[2] < 2 or not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} prefix xy values must be finite.")
    return {
        "selected_index": selected_index,
        "feasible": _bool_vector(
            record.get("feasible_mask"),
            candidate_count,
            f"{label} feasible_mask",
        ),
        "outcomes": _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label),
        "prefix_xy": prefix[:, :, :2],
        "target_speed": _vector(
            record.get("candidate_perfect_tracker_target_speed_mps"),
            candidate_count,
            f"{label} candidate_perfect_tracker_target_speed_mps",
        ),
        "raw_horizon_lateral": _vector(
            record.get("candidate_horizon_lateral_acceleration_cost"),
            candidate_count,
            f"{label} candidate_horizon_lateral_acceleration_cost",
        ),
        "raw_jerk_excess": _vector(
            record.get("candidate_dp_prior_jerk_excess_cost"),
            candidate_count,
            f"{label} candidate_dp_prior_jerk_excess_cost",
        ),
    }


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _donor_rows(record: dict[str, Any]) -> dict[str, Any]:
    selected = record["selected_index"]
    donor_mask = _safety_joint_comfort_mask(record)
    rows = []
    selected_h10 = float(np.linalg.norm(record["prefix_xy"][selected, 9]))
    selected_target = float(record["target_speed"][selected])
    selected_progress = _outcome_float(record, selected, "progress_m")
    for candidate in np.flatnonzero(donor_mask):
        candidate = int(candidate)
        candidate_h10 = float(np.linalg.norm(record["prefix_xy"][candidate, 9]))
        progress_loss = max(
            0.0,
            selected_progress - _outcome_float(record, candidate, "progress_m"),
        )
        target_loss = max(0.0, selected_target - float(record["target_speed"][candidate]))
        h10_loss = max(0.0, selected_h10 - candidate_h10)
        prefix_distance = float(
            np.linalg.norm(
                record["prefix_xy"][candidate, :10] - record["prefix_xy"][selected, :10],
                axis=1,
            ).max()
        )
        rows.append(
            {
                "candidate_index": candidate,
                "progress_loss_m": progress_loss,
                "target_speed_loss_mps": target_loss,
                "h10_displacement_loss_m": h10_loss,
                "prefix_max_distance_m": prefix_distance,
                "outcome_progress_delta_m": _outcome_float(record, candidate, "progress_m")
                - selected_progress,
                "outcome_jerk_delta_mps3": _outcome_float(record, candidate, "mean_jerk_mps3")
                - _outcome_float(record, selected, "mean_jerk_mps3"),
                "outcome_lateral_delta_mps2": _outcome_float(
                    record,
                    candidate,
                    "mean_lateral_acceleration_mps2",
                )
                - _outcome_float(record, selected, "mean_lateral_acceleration_mps2"),
                "raw_horizon_lateral_delta": float(
                    record["raw_horizon_lateral"][candidate]
                    - record["raw_horizon_lateral"][selected]
                ),
                "raw_jerk_excess_delta": float(
                    record["raw_jerk_excess"][candidate]
                    - record["raw_jerk_excess"][selected]
                ),
            }
        )
    return {"count": len(rows), "rows": rows}


def _safety_joint_comfort_mask(record: dict[str, Any]) -> np.ndarray:
    selected = record["selected_index"]
    size = record["feasible"].size
    mask = record["feasible"].copy()
    mask[selected] = False
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
    return mask & (jerk < jerk[selected] - TOL) & (lateral < lateral[selected] - TOL)


def _budget_report(
    donor_rows: list[dict[str, Any]],
    *,
    progress_budget: float,
    target_budget: float,
    h10_budget: float,
) -> dict[str, Any]:
    chosen = []
    available = 0
    candidate_counts = []
    for record in donor_rows:
        eligible = [
            row
            for row in record["rows"]
            if row["progress_loss_m"] <= progress_budget + TOL
            and row["target_speed_loss_mps"] <= target_budget + TOL
            and row["h10_displacement_loss_m"] <= h10_budget + TOL
        ]
        candidate_counts.append(len(eligible))
        if not eligible:
            continue
        available += 1
        chosen.append(_choose_budget_candidate(eligible))
    return {
        "progress_budget_m": float(progress_budget),
        "target_speed_loss_budget_mps": float(target_budget),
        "h10_displacement_loss_budget_m": float(h10_budget),
        "available_records": int(available),
        "availability_rate": available / max(len(donor_rows), 1),
        "mean_eligible_candidates": float(np.mean(candidate_counts)) if candidate_counts else 0.0,
        "chosen_summary": _chosen_summary(chosen),
    }


def _choose_budget_candidate(rows: list[dict[str, float]]) -> dict[str, float]:
    order = sorted(
        rows,
        key=lambda row: (
            row["progress_loss_m"],
            row["target_speed_loss_mps"],
            row["h10_displacement_loss_m"],
            row["outcome_jerk_delta_mps3"],
            row["outcome_lateral_delta_mps2"],
            row["candidate_index"],
        ),
    )
    return order[0]


def _oracle_summary(donor_rows: list[dict[str, Any]]) -> dict[str, Any]:
    first_rows = [
        _choose_budget_candidate(record["rows"])
        for record in donor_rows
        if record["rows"]
    ]
    return _chosen_summary(first_rows)


def _chosen_summary(rows: list[dict[str, float]]) -> dict[str, Any]:
    keys = (
        "progress_loss_m",
        "target_speed_loss_mps",
        "h10_displacement_loss_m",
        "prefix_max_distance_m",
        "outcome_progress_delta_m",
        "outcome_jerk_delta_mps3",
        "outcome_lateral_delta_mps2",
        "raw_horizon_lateral_delta",
        "raw_jerk_excess_delta",
    )
    return {
        "records": len(rows),
        **{key: _summary([float(row[key]) for row in rows]) for key in keys},
    }


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values.")
    return array


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    lines = [
        "# DP CAMP Bounded Tradeoff",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- With oracle donors: {records['with_oracle_donor']}",
        "",
        "Oracle donors are safety-nonworse candidates that strictly improve "
        "closed-loop outcome jerk and lateral acceleration. This report asks "
        "how much progress, target-speed, and H10 anchor loss budget is needed "
        "to retain such donors; it does not define an online selector.",
        "",
        "## Oracle Donor Baseline",
        "",
        "| Quantity | Mean | P50 | P90 | P95 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    oracle = report["oracle_donor_summary"]
    for label_text, key in (
        ("Progress loss m", "progress_loss_m"),
        ("Target-speed loss m/s", "target_speed_loss_mps"),
        ("H10 displacement loss m", "h10_displacement_loss_m"),
        ("Prefix max distance m", "prefix_max_distance_m"),
        ("Outcome jerk delta m/s^3", "outcome_jerk_delta_mps3"),
        ("Outcome lateral delta m/s^2", "outcome_lateral_delta_mps2"),
    ):
        lines.append(_summary_row(label_text, oracle[key]))
    lines.extend(
        [
            "",
            "## Progress Budget Slice",
            "",
            f"Fixed target-speed loss <= `{REPORT_TARGET_SPEED_BUDGET_MPS}` m/s "
            f"and H10 displacement loss <= `{REPORT_H10_BUDGET_M}` m.",
            "",
            "| Progress budget m | Available records | Availability | Mean eligible candidates | Chosen progress loss mean | Chosen jerk delta mean |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in _slice(
        report["budget_grid"],
        target_speed_loss_budget_mps=REPORT_TARGET_SPEED_BUDGET_MPS,
        h10_displacement_loss_budget_m=REPORT_H10_BUDGET_M,
    ):
        lines.append(_budget_row(row, "progress_budget_m"))
    lines.extend(
        [
            "",
            "## Target-Speed Budget Slice",
            "",
            f"Fixed progress loss <= `{REPORT_PROGRESS_BUDGET_M}` m and H10 "
            f"displacement loss <= `{REPORT_H10_BUDGET_M}` m.",
            "",
            "| Target-speed loss budget m/s | Available records | Availability | Mean eligible candidates | Chosen progress loss mean | Chosen jerk delta mean |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in _slice(
        report["budget_grid"],
        progress_budget_m=REPORT_PROGRESS_BUDGET_M,
        h10_displacement_loss_budget_m=REPORT_H10_BUDGET_M,
    ):
        lines.append(_budget_row(row, "target_speed_loss_budget_mps"))
    lines.extend(
        [
            "",
            "## H10 Anchor Budget Slice",
            "",
            f"Fixed progress loss <= `{REPORT_PROGRESS_BUDGET_M}` m and "
            f"target-speed loss <= `{REPORT_TARGET_SPEED_BUDGET_MPS}` m/s.",
            "",
            "| H10 loss budget m | Available records | Availability | Mean eligible candidates | Chosen progress loss mean | Chosen jerk delta mean |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in _slice(
        report["budget_grid"],
        progress_budget_m=REPORT_PROGRESS_BUDGET_M,
        target_speed_loss_budget_mps=REPORT_TARGET_SPEED_BUDGET_MPS,
    ):
        lines.append(_budget_row(row, "h10_displacement_loss_budget_m"))
    lines.append("")
    return "\n".join(lines)


def _slice(rows: list[dict[str, Any]], **filters: float) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        if all(abs(float(row[key]) - float(value)) <= 1e-12 for key, value in filters.items()):
            result.append(row)
    return sorted(result, key=lambda row: tuple(float(row[key]) for key in row if key.endswith("_m") or key.endswith("_mps")))


def _budget_row(row: dict[str, Any], budget_key: str) -> str:
    summary = row["chosen_summary"]
    return (
        f"| {float(row[budget_key]):.6f} | {row['available_records']} | "
        f"{row['availability_rate']:.6f} | {row['mean_eligible_candidates']:.6f} | "
        f"{_fmt(summary['progress_loss_m']['mean'])} | "
        f"{_fmt(summary['outcome_jerk_delta_mps3']['mean'])} |"
    )


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p50'])} | "
        f"{_fmt(values['p90'])} | {_fmt(values['p95'])} |"
    )


if __name__ == "__main__":
    main()
