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
SCREENS = (
    {
        "name": "tight_lateral",
        "progress_proxy_loss_budget_m": 0.05,
        "target_speed_loss_budget_mps": 0.10,
        "h10_displacement_loss_budget_m": 0.10,
        "require_raw_jerk_nondegrading": False,
    },
    {
        "name": "moderate_lateral",
        "progress_proxy_loss_budget_m": 0.50,
        "target_speed_loss_budget_mps": 0.10,
        "h10_displacement_loss_budget_m": 0.10,
        "require_raw_jerk_nondegrading": False,
    },
    {
        "name": "moderate_lateral_jerk_nondegrading",
        "progress_proxy_loss_budget_m": 0.50,
        "target_speed_loss_budget_mps": 0.10,
        "h10_displacement_loss_budget_m": 0.10,
        "require_raw_jerk_nondegrading": True,
    },
    {
        "name": "loose_anchor_lateral",
        "progress_proxy_loss_budget_m": 0.50,
        "target_speed_loss_budget_mps": 0.10,
        "h10_displacement_loss_budget_m": 0.25,
        "require_raw_jerk_nondegrading": False,
    },
)
OUTCOME_DELTA_FIELDS = (
    "progress_m",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
    "value",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline outcome-free bounded selector screen. Uses current-tick "
            "finite candidate fields for selection and candidate outcomes only "
            "for posterior evaluation."
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
    progress_proxy_source_counts = {
        "route_progress": 0,
        "dp_reward_progress": 0,
        "step_reach_fallback": 0,
    }
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, record in enumerate(payload):
            loaded = _load_record(record, f"{log_path} record {index}")
            progress_proxy_source_counts[loaded["progress_proxy_source"]] += 1
            records.append(loaded)

    screen_reports = [_screen(records, screen) for screen in SCREENS]
    return {
        "analysis": {
            "name": "dp_camp_outcome_free_bounded_selector_screen_v1",
            "role": (
                "offline screen for an outcome-free finite-candidate bounded "
                "tradeoff rule"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": False,
            "selection_rule": (
                "base feasible and red-guarded candidates within progress-proxy, "
                "target-speed, and H10 displacement budgets; require raw horizon "
                "lateral improvement; optionally require raw jerk nondegradation; "
                "tie-break by raw lateral, raw jerk, budget losses, original CAMP "
                "selection score, then candidate index; retain baseline if empty"
            ),
            "progress_proxy": (
                "candidate_route_progress if logged and finite, else DP reward "
                "progress if logged and finite, else candidate_step_reach"
            ),
            "convexity_boundary": (
                "For fixed finite candidates all rule inputs are current-tick "
                "constants. Later CAMP scoring remains affine in w. This screen "
                "is not Benders and does not claim trajectory-coordinate convexity."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
            "progress_proxy_source_counts": progress_proxy_source_counts,
        },
        "screens": screen_reports,
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
    progress_proxy, source = _progress_proxy(record, candidate_count, label)
    return {
        "selected_index": selected_index,
        "feasible": _bool_vector(
            record.get("feasible_mask"),
            candidate_count,
            f"{label} feasible_mask",
        ),
        "outcomes": _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label),
        "selection_scores": _score_vector(
            record.get("selection_scores"),
            candidate_count,
            f"{label} selection_scores",
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
        "progress_proxy": progress_proxy,
        "progress_proxy_source": source,
        "target_speed": _vector(
            record.get("candidate_perfect_tracker_target_speed_mps"),
            candidate_count,
            f"{label} candidate_perfect_tracker_target_speed_mps",
        ),
        "h10_displacement": np.linalg.norm(prefix[:, 9, :2], axis=1),
        "raw_lateral": _vector(
            record.get("candidate_horizon_lateral_acceleration_cost"),
            candidate_count,
            f"{label} candidate_horizon_lateral_acceleration_cost",
        ),
        "raw_jerk": _vector(
            record.get("candidate_dp_prior_jerk_excess_cost"),
            candidate_count,
            f"{label} candidate_dp_prior_jerk_excess_cost",
        ),
    }


def _progress_proxy(
    record: dict[str, Any],
    candidate_count: int,
    label: str,
) -> tuple[np.ndarray, str]:
    route_progress = record.get("candidate_route_progress")
    if route_progress is not None:
        try:
            values = _vector(
                route_progress,
                candidate_count,
                f"{label} candidate_route_progress",
            )
            return values, "route_progress"
        except ValueError:
            pass
    rewards = record.get("dp_candidate_rewards")
    if isinstance(rewards, list) and len(rewards) == candidate_count:
        try:
            values = _vector(
                [reward.get("progress") for reward in rewards],
                candidate_count,
                f"{label} dp_candidate_rewards progress",
                allow_negative=True,
            )
            return values, "dp_reward_progress"
        except (AttributeError, ValueError):
            pass
    values = _vector(
        record.get("candidate_step_reach"),
        candidate_count,
        f"{label} candidate_step_reach",
    )
    return values, "step_reach_fallback"


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _screen(records: list[dict[str, Any]], screen: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for record in records:
        rows.append(_screen_record(record, screen))
    nonfallback = [row for row in rows if not row["fallback"]]
    changed = [row for row in nonfallback if row["changed"]]
    return {
        "name": screen["name"],
        "budgets": {
            "progress_proxy_loss_m": screen["progress_proxy_loss_budget_m"],
            "target_speed_loss_mps": screen["target_speed_loss_budget_mps"],
            "h10_displacement_loss_m": screen["h10_displacement_loss_budget_m"],
            "require_raw_jerk_nondegrading": screen["require_raw_jerk_nondegrading"],
        },
        "records": {
            "total": len(records),
            "nonfallback": len(nonfallback),
            "changed": len(changed),
            "admissible_opportunity": sum(int(row["opportunity"]) for row in nonfallback),
            "outcome_safety_regressions": sum(
                int(row["outcome_safety_regression"]) for row in changed
            ),
            "posterior_joint_comfort_improvements": sum(
                int(row["posterior_joint_comfort_improvement"]) for row in changed
            ),
        },
        "rates": {
            "change_rate": len(changed) / max(len(nonfallback), 1),
            "opportunity_rate": sum(int(row["opportunity"]) for row in nonfallback)
            / max(len(nonfallback), 1),
            "changed_safety_regression_rate": sum(
                int(row["outcome_safety_regression"]) for row in changed
            )
            / max(len(changed), 1),
            "changed_joint_comfort_improvement_rate": sum(
                int(row["posterior_joint_comfort_improvement"]) for row in changed
            )
            / max(len(changed), 1),
        },
        "outcome_delta_summary": {
            field: _summary([float(row[f"outcome_{field}_delta"]) for row in rows])
            for field in OUTCOME_DELTA_FIELDS
        },
        "changed_outcome_delta_summary": {
            field: _summary([float(row[f"outcome_{field}_delta"]) for row in changed])
            for field in OUTCOME_DELTA_FIELDS
        },
        "diagnostic_delta_summary": {
            key: _summary([float(row[key]) for row in rows])
            for key in _diagnostic_delta_keys()
        },
        "changed_diagnostic_delta_summary": {
            key: _summary([float(row[key]) for row in changed])
            for key in _diagnostic_delta_keys()
        },
    }


def _screen_record(record: dict[str, Any], screen: dict[str, Any]) -> dict[str, Any]:
    selected = record["selected_index"]
    fallback = not record["feasible"].any()
    if fallback:
        chosen = selected
        admissible = np.zeros_like(record["feasible"], dtype=bool)
    else:
        admissible = _admissible_mask(record, screen)
        chosen = _choose(record, admissible) if admissible.any() else selected
    return _result_row(record, chosen, opportunity=bool(admissible.any()), fallback=fallback)


def _admissible_mask(record: dict[str, Any], screen: dict[str, Any]) -> np.ndarray:
    selected = record["selected_index"]
    progress_loss = np.maximum(0.0, record["progress_proxy"][selected] - record["progress_proxy"])
    target_loss = np.maximum(0.0, record["target_speed"][selected] - record["target_speed"])
    h10_loss = np.maximum(0.0, record["h10_displacement"][selected] - record["h10_displacement"])
    admissible = (
        record["feasible"].copy()
        & (record["union_red"] <= record["union_red"][selected] + TOL)
        & (record["red_stopping"] <= record["red_stopping"][selected] + TOL)
        & (progress_loss <= float(screen["progress_proxy_loss_budget_m"]) + TOL)
        & (target_loss <= float(screen["target_speed_loss_budget_mps"]) + TOL)
        & (h10_loss <= float(screen["h10_displacement_loss_budget_m"]) + TOL)
        & (record["raw_lateral"] < record["raw_lateral"][selected] - TOL)
    )
    if bool(screen["require_raw_jerk_nondegrading"]):
        admissible &= record["raw_jerk"] <= record["raw_jerk"][selected] + TOL
    admissible[selected] = False
    return admissible


def _choose(record: dict[str, Any], admissible: np.ndarray) -> int:
    indices = np.flatnonzero(admissible)
    selected = record["selected_index"]
    progress_loss = np.maximum(0.0, record["progress_proxy"][selected] - record["progress_proxy"])
    target_loss = np.maximum(0.0, record["target_speed"][selected] - record["target_speed"])
    h10_loss = np.maximum(0.0, record["h10_displacement"][selected] - record["h10_displacement"])
    order = np.lexsort(
        (
            indices,
            record["selection_scores"][indices],
            h10_loss[indices],
            target_loss[indices],
            progress_loss[indices],
            record["raw_jerk"][indices],
            record["raw_lateral"][indices],
        )
    )
    return int(indices[order[0]])


def _result_row(
    record: dict[str, Any],
    chosen: int,
    *,
    opportunity: bool,
    fallback: bool,
) -> dict[str, Any]:
    selected = record["selected_index"]
    progress_loss = max(0.0, float(record["progress_proxy"][selected] - record["progress_proxy"][chosen]))
    target_loss = max(0.0, float(record["target_speed"][selected] - record["target_speed"][chosen]))
    h10_loss = max(0.0, float(record["h10_displacement"][selected] - record["h10_displacement"][chosen]))
    row: dict[str, Any] = {
        "fallback": bool(fallback),
        "opportunity": bool(opportunity),
        "changed": bool(chosen != selected),
        "chosen_index": int(chosen),
        "progress_proxy_loss_m": progress_loss,
        "target_speed_loss_mps": target_loss,
        "h10_displacement_loss_m": h10_loss,
        "raw_lateral_delta": float(record["raw_lateral"][chosen] - record["raw_lateral"][selected]),
        "raw_jerk_delta": float(record["raw_jerk"][chosen] - record["raw_jerk"][selected]),
        "union_red_delta": float(record["union_red"][chosen] - record["union_red"][selected]),
        "red_stopping_delta": float(record["red_stopping"][chosen] - record["red_stopping"][selected]),
    }
    for field in OUTCOME_DELTA_FIELDS:
        row[f"outcome_{field}_delta"] = _outcome_number(record, chosen, field) - _outcome_number(
            record,
            selected,
            field,
        )
    row["outcome_safety_regression"] = _outcome_safety_regression(record, chosen)
    row["posterior_joint_comfort_improvement"] = (
        row["outcome_mean_jerk_mps3_delta"] < -TOL
        and row["outcome_mean_lateral_acceleration_mps2_delta"] < -TOL
        and not row["outcome_safety_regression"]
    )
    return row


def _outcome_safety_regression(record: dict[str, Any], chosen: int) -> bool:
    selected = record["selected_index"]
    return any(
        bool(record["outcomes"][chosen].get(field))
        and not bool(record["outcomes"][selected].get(field))
        for field in BOOL_OUTCOMES
    )


def _diagnostic_delta_keys() -> tuple[str, ...]:
    return (
        "progress_proxy_loss_m",
        "target_speed_loss_mps",
        "h10_displacement_loss_m",
        "raw_lateral_delta",
        "raw_jerk_delta",
        "union_red_delta",
        "red_stopping_delta",
    )


def _vector(
    values: Any,
    size: int,
    label: str,
    *,
    allow_negative: bool = False,
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain finite values.")
    if not allow_negative and np.any(array < 0.0):
        raise ValueError(f"{label} must be nonnegative.")
    return array


def _score_vector(values: Any, size: int, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.size != size:
        raise ValueError(f"{label} has {array.size} values; expected {size}.")
    return np.nan_to_num(array, nan=1.0e12, posinf=1.0e12, neginf=-1.0e12)


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _outcome_number(record: dict[str, Any], index: int, field: str) -> float:
    value = float(record["outcomes"][index].get(field))
    if not np.isfinite(value):
        raise ValueError(f"Outcome {field} must be finite.")
    return value


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    source_counts = records["progress_proxy_source_counts"]
    lines = [
        "# DP CAMP Outcome-Free Bounded Selector Screen",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- Progress proxy source counts: route progress "
        f"{source_counts['route_progress']}, DP reward progress "
        f"{source_counts['dp_reward_progress']}, step-reach fallback "
        f"{source_counts['step_reach_fallback']}",
        "",
        "The screen uses current-tick finite candidate fields only for "
        "selection. Candidate outcomes are used only for posterior evaluation.",
        "",
        "| Screen | Changed | Change rate | Opportunity | Posterior joint comfort | Safety regressions | Progress delta mean | Jerk delta mean | Lateral delta mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for screen in report["screens"]:
        records_summary = screen["records"]
        rates = screen["rates"]
        outcomes = screen["outcome_delta_summary"]
        lines.append(
            f"| `{screen['name']}` | {records_summary['changed']} | "
            f"{rates['change_rate']:.6f} | {rates['opportunity_rate']:.6f} | "
            f"{rates['changed_joint_comfort_improvement_rate']:.6f} | "
            f"{records_summary['outcome_safety_regressions']} | "
            f"{_fmt(outcomes['progress_m']['mean'])} | "
            f"{_fmt(outcomes['mean_jerk_mps3']['mean'])} | "
            f"{_fmt(outcomes['mean_lateral_acceleration_mps2']['mean'])} |"
        )
    lines.extend(["", "## Changed-Record Diagnostics", ""])
    for screen in report["screens"]:
        lines.extend(
            [
                f"### `{screen['name']}`",
                "",
                "| Quantity | Mean | P50 | P90 | P95 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for label_text, key, group in (
            ("Outcome progress delta m", "progress_m", "changed_outcome_delta_summary"),
            ("Outcome jerk delta m/s^3", "mean_jerk_mps3", "changed_outcome_delta_summary"),
            (
                "Outcome lateral delta m/s^2",
                "mean_lateral_acceleration_mps2",
                "changed_outcome_delta_summary",
            ),
            ("Progress proxy loss m", "progress_proxy_loss_m", "changed_diagnostic_delta_summary"),
            ("Target-speed loss m/s", "target_speed_loss_mps", "changed_diagnostic_delta_summary"),
            ("H10 displacement loss m", "h10_displacement_loss_m", "changed_diagnostic_delta_summary"),
            ("Raw lateral delta", "raw_lateral_delta", "changed_diagnostic_delta_summary"),
            ("Raw jerk delta", "raw_jerk_delta", "changed_diagnostic_delta_summary"),
        ):
            lines.append(_summary_row(label_text, screen[group][key]))
        lines.append("")
    return "\n".join(lines)


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p50'])} | "
        f"{_fmt(values['p90'])} | {_fmt(values['p95'])} |"
    )


if __name__ == "__main__":
    main()
