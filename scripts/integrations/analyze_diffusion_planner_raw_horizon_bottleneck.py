#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
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


TOL = 1e-12


@dataclass(frozen=True)
class BudgetScreen:
    name: str
    progress_loss_budget_m: float
    target_speed_loss_budget_mps: float
    h10_distance_loss_budget_m: float
    h3_max_lateral_limit_mps2: float


DEFAULT_PROGRESS_BUDGETS_M = (0.10, 0.25, 0.50)
DEFAULT_TARGET_SPEED_LOSS_BUDGET_MPS = 0.10
DEFAULT_H10_DISTANCE_LOSS_BUDGET_M = 0.10
DEFAULT_H3_MAX_LATERAL_LIMIT_MPS2 = 2.0
DEFAULT_MODE_THRESHOLD_M = 0.50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit how logged raw DP horizon geometry survives base feasibility "
            "and bounded lower-red masks. This is an offline diagnostic over "
            "fixed finite candidate constants."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--horizon", type=int, default=80)
    parser.add_argument(
        "--progress_loss_budget_m",
        type=float,
        action="append",
        default=[],
        help=(
            "Progress-loss budget for lower-red bounded masks. May be repeated; "
            "defaults to 0.10, 0.25, and 0.50 m."
        ),
    )
    parser.add_argument(
        "--target_speed_loss_budget_mps",
        type=float,
        default=DEFAULT_TARGET_SPEED_LOSS_BUDGET_MPS,
    )
    parser.add_argument(
        "--h10_distance_loss_budget_m",
        type=float,
        default=DEFAULT_H10_DISTANCE_LOSS_BUDGET_M,
    )
    parser.add_argument(
        "--h3_max_lateral_limit_mps2",
        type=float,
        default=DEFAULT_H3_MAX_LATERAL_LIMIT_MPS2,
    )
    parser.add_argument("--mode_threshold_m", type=float, default=DEFAULT_MODE_THRESHOLD_M)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    progress_budgets = tuple(args.progress_loss_budget_m) or DEFAULT_PROGRESS_BUDGETS_M
    screens = tuple(
        BudgetScreen(
            name=f"p{_slug_float(progress)}",
            progress_loss_budget_m=progress,
            target_speed_loss_budget_mps=args.target_speed_loss_budget_mps,
            h10_distance_loss_budget_m=args.h10_distance_loss_budget_m,
            h3_max_lateral_limit_mps2=args.h3_max_lateral_limit_mps2,
        )
        for progress in progress_budgets
    )
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        horizon=args.horizon,
        mode_threshold_m=args.mode_threshold_m,
        screens=screens,
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
    horizon: int = 80,
    mode_threshold_m: float = DEFAULT_MODE_THRESHOLD_M,
    screens: tuple[BudgetScreen, ...] | None = None,
) -> dict[str, Any]:
    if horizon <= 0:
        raise ValueError("horizon must be positive.")
    if not np.isfinite(mode_threshold_m) or mode_threshold_m < 0.0:
        raise ValueError("mode_threshold_m must be finite and nonnegative.")
    if screens is None:
        screens = tuple(
            BudgetScreen(
                name=f"p{_slug_float(progress)}",
                progress_loss_budget_m=progress,
                target_speed_loss_budget_mps=DEFAULT_TARGET_SPEED_LOSS_BUDGET_MPS,
                h10_distance_loss_budget_m=DEFAULT_H10_DISTANCE_LOSS_BUDGET_M,
                h3_max_lateral_limit_mps2=DEFAULT_H3_MAX_LATERAL_LIMIT_MPS2,
            )
            for progress in DEFAULT_PROGRESS_BUDGETS_M
        )
    _validate_screens(screens)
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    totals = {"logs": len(log_paths), "total": 0, "fallback": 0, "nonfallback": 0}
    groups: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    budget_groups: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    budget_blockers: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    event_counts: dict[str, int] = defaultdict(int)

    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(payload):
            totals["total"] += 1
            label_text = f"{log_path} record {record_index}"
            record_data = _record_data(record, horizon, label_text)
            totals["fallback"] += int(record_data["fallback"])
            totals["nonfallback"] += int(not record_data["fallback"])
            for event_name, value in record_data["events"].items():
                event_counts[event_name] += int(value)
            group_names = _group_names(record_data)
            static_masks = _static_masks(record_data)
            for group_name in group_names:
                for mask_name, mask in static_masks.items():
                    groups[group_name][mask_name].append(
                        _mask_metrics(record_data, mask, mode_threshold_m)
                    )
                for screen in screens:
                    for mask_name, mask in _budget_masks(record_data, screen).items():
                        budget_groups[group_name][screen.name][mask_name].append(
                            _mask_metrics(record_data, mask, mode_threshold_m)
                        )
                    budget_blockers[group_name][screen.name].append(
                        _budget_blocker_row(record_data, screen)
                    )

    return {
        "analysis": {
            "name": "dp_camp_raw_horizon_bottleneck_v1",
            "role": (
                "offline raw-horizon candidate-set bottleneck audit over logged "
                "Diffusion Planner candidate prefixes"
            ),
            "label": label,
            "horizon": horizon,
            "training": False,
            "online_selector_change": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "convexity_boundary": (
                "All masks and raw-horizon geometry descriptors are fixed "
                "finite-candidate constants at the current tick. If later "
                "atomized, fixed-set CAMP scoring remains affine in w and "
                "compatible with the simplex/CVaR/L2 convex master. This audit "
                "is not Benders and makes no trajectory-coordinate convexity "
                "claim."
            ),
        },
        "thresholds": {
            "mode_threshold_m": mode_threshold_m,
        },
        "budget_screens": [screen.__dict__ for screen in screens],
        "records": totals,
        "events": dict(sorted(event_counts.items())),
        "groups": {
            group_name: {
                "records": len(next(iter(mask_rows.values()))) if mask_rows else 0,
                "masks": {
                    mask_name: _summarize_metrics(rows)
                    for mask_name, rows in sorted(mask_rows.items())
                },
                "budget_masks": {
                    screen_name: {
                        mask_name: _summarize_metrics(rows)
                        for mask_name, rows in sorted(screen_rows.items())
                    }
                    for screen_name, screen_rows in sorted(
                        budget_groups[group_name].items()
                    )
                },
                "budget_blockers": {
                    screen_name: _summarize_budget_blockers(rows)
                    for screen_name, rows in sorted(
                        budget_blockers[group_name].items()
                    )
                },
            }
            for group_name, mask_rows in sorted(groups.items())
        },
    }


def _validate_screens(screens: tuple[BudgetScreen, ...]) -> None:
    if not screens:
        raise ValueError("At least one budget screen is required.")
    names = [screen.name for screen in screens]
    if len(set(names)) != len(names):
        raise ValueError("Budget screen names must be unique.")
    for screen in screens:
        values = (
            screen.progress_loss_budget_m,
            screen.target_speed_loss_budget_mps,
            screen.h10_distance_loss_budget_m,
            screen.h3_max_lateral_limit_mps2,
        )
        if any(not np.isfinite(value) or value < 0.0 for value in values):
            raise ValueError("Budget screen values must be finite and nonnegative.")


def _record_data(record: dict[str, Any], horizon: int, label: str) -> dict[str, Any]:
    raw = _raw_prefix(record, horizon, label)
    candidate_count = raw.shape[0]
    selected = int(record.get("selected_index"))
    if selected < 0 or selected >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    feasible = _bool_vector(record.get("feasible_mask"), candidate_count, label, "feasible_mask")
    union_red = _union_red(record, candidate_count, label)
    planned_red = _short_red_vector(record, candidate_count, label)
    full_red = _optional_vector(
        record.get("candidate_full_horizon_planned_red_light_cost"), candidate_count
    )
    progress = _progress_vector(record, candidate_count, label)
    target_speed = _vector(
        record.get("candidate_perfect_tracker_target_speed_mps"),
        candidate_count,
        label,
        "candidate_perfect_tracker_target_speed_mps",
    )
    rollout = record.get("candidate_perfect_tracker_open_loop_rollout")
    if not isinstance(rollout, dict):
        raise ValueError(f"{label} candidate_perfect_tracker_open_loop_rollout is required.")
    h3 = _rollout_horizon(rollout, 3, candidate_count, label)
    h10 = _rollout_horizon(rollout, 10, candidate_count, label)
    fallback = not feasible.any()
    selected_union = float(union_red[selected])
    selected_planned_red = float(planned_red[selected])
    selected_full_red = float(full_red[selected]) if full_red is not None else selected_union
    selected_h30_safe_full_red = selected_planned_red <= TOL and selected_full_red > TOL
    return {
        "raw_xy": raw[:, :horizon, :2],
        "candidate_count": candidate_count,
        "selected": selected,
        "feasible": feasible,
        "fallback": fallback,
        "union_red": union_red,
        "progress": progress,
        "target_speed": target_speed,
        "h3_distance": _rollout_metric(h3, "distance_m", candidate_count, label),
        "h10_distance": _rollout_metric(h10, "distance_m", candidate_count, label),
        "h3_mean_jerk": _rollout_metric(
            h3, "mean_vector_jerk_mps3", candidate_count, label
        ),
        "h3_max_lateral": _rollout_metric(
            h3, "max_lateral_acceleration_mps2", candidate_count, label
        ),
        "events": {
            "fallback_records": fallback,
            "selected_union_red_positive": selected_union > TOL,
            "selected_h30_safe_full_red": selected_h30_safe_full_red,
            "any_lower_red_candidate": bool((union_red < selected_union - TOL).any()),
            "any_lower_red_base_feasible_candidate": bool(
                ((union_red < selected_union - TOL) & feasible).any()
            ),
        },
        "selected_union_red_positive": selected_union > TOL,
        "selected_h30_safe_full_red": selected_h30_safe_full_red,
        "feasible_bucket": _feasible_bucket(int(feasible.sum()), candidate_count),
    }


def _raw_prefix(record: dict[str, Any], horizon: int, label: str) -> np.ndarray:
    raw = np.asarray(record.get("candidate_raw_trajectory_prefix"), dtype=np.float64)
    if raw.ndim != 3 or raw.shape[0] <= 0 or raw.shape[2] < 2:
        raise ValueError(f"{label} candidate_raw_trajectory_prefix must be [K,T,D>=2].")
    if raw.shape[1] < horizon:
        raise ValueError(
            f"{label} requested horizon {horizon} exceeds logged raw prefix length "
            f"{raw.shape[1]}."
        )
    if not np.all(np.isfinite(raw[:, :horizon, :2])):
        raise ValueError(f"{label} raw prefix xy values must be finite.")
    return raw


def _union_red(record: dict[str, Any], count: int, label: str) -> np.ndarray:
    union = _optional_vector(record.get("candidate_horizon_union_planned_red_light_cost"), count)
    if union is not None:
        return union
    planned = _optional_vector(record.get("candidate_planned_red_light_cost"), count)
    full = _optional_vector(record.get("candidate_full_horizon_planned_red_light_cost"), count)
    if planned is None and full is None:
        raise ValueError(f"{label} union or planned/full red-light costs are required.")
    if planned is None:
        return full
    if full is None:
        return planned
    return np.maximum(planned, full)


def _progress_vector(record: dict[str, Any], count: int, label: str) -> np.ndarray:
    route_progress = _optional_vector(record.get("candidate_route_progress"), count)
    if route_progress is not None:
        return route_progress
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != count:
        raise ValueError(
            f"{label} candidate_route_progress or dp_candidate_rewards progress is required."
        )
    progress = []
    for index, reward in enumerate(rewards):
        if not isinstance(reward, dict) or "progress" not in reward:
            raise ValueError(f"{label} dp_candidate_rewards[{index}].progress is required.")
        progress.append(float(reward["progress"]))
    arr = np.asarray(progress, dtype=np.float64)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{label} progress values must be finite.")
    return arr


def _short_red_vector(record: dict[str, Any], count: int, label: str) -> np.ndarray:
    planned = _optional_vector(record.get("candidate_planned_red_light_cost"), count)
    if planned is not None:
        return planned
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != count:
        raise ValueError(
            f"{label} candidate_planned_red_light_cost or dp_candidate_rewards red_light is required."
        )
    red = np.asarray(
        [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in rewards],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(red)):
        raise ValueError(f"{label} short-horizon red values must be finite.")
    return red


def _optional_vector(value: Any, count: int) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (count,):
        return None
    if not np.all(np.isfinite(arr)):
        return None
    return arr


def _vector(value: Any, count: int, label: str, field: str) -> np.ndarray:
    arr = _optional_vector(value, count)
    if arr is None:
        raise ValueError(f"{label} {field} must be a finite vector of length {count}.")
    return arr


def _bool_vector(value: Any, count: int, label: str, field: str) -> np.ndarray:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f"{label} {field} must have length {count}.")
    return np.asarray([bool(item) for item in value], dtype=bool)


def _rollout_horizon(
    rollout: dict[str, Any], horizon: int, count: int, label: str
) -> dict[str, Any]:
    data = rollout.get(str(horizon), rollout.get(horizon))
    if not isinstance(data, dict):
        raise ValueError(f"{label} missing PerfectTracker H{horizon} rollout metrics.")
    for field in ("distance_m", "mean_vector_jerk_mps3", "max_lateral_acceleration_mps2"):
        _vector(data.get(field), count, label, f"H{horizon}.{field}")
    return data


def _rollout_metric(
    horizon_data: dict[str, Any], field: str, count: int, label: str
) -> np.ndarray:
    return _vector(horizon_data.get(field), count, label, field)


def _feasible_bucket(feasible_count: int, candidate_count: int) -> str:
    if feasible_count == 0:
        return "none"
    if feasible_count == candidate_count:
        return "all"
    return "partial"


def _group_names(data: dict[str, Any]) -> list[str]:
    return [
        "all",
        f"fallback={str(data['fallback']).lower()}",
        (
            "selected_union_red_positive="
            f"{str(data['selected_union_red_positive']).lower()}"
        ),
        (
            "selected_h30_safe_full_red="
            f"{str(data['selected_h30_safe_full_red']).lower()}"
        ),
        f"feasible_bucket={data['feasible_bucket']}",
    ]


def _static_masks(data: dict[str, Any]) -> dict[str, np.ndarray]:
    count = int(data["candidate_count"])
    selected = int(data["selected"])
    selected_union = float(data["union_red"][selected])
    lower_red = data["union_red"] < selected_union - TOL
    feasible = data["feasible"]
    return {
        "all_candidates": np.ones(count, dtype=bool),
        "base_feasible": feasible,
        "lower_red_any": lower_red,
        "lower_red_base_feasible": lower_red & feasible,
    }


def _budget_masks(data: dict[str, Any], screen: BudgetScreen) -> dict[str, np.ndarray]:
    selected = int(data["selected"])
    lower_red_base = _static_masks(data)["lower_red_base_feasible"]
    bounded = (
        lower_red_base
        & (
            data["progress"]
            >= float(data["progress"][selected]) - screen.progress_loss_budget_m - TOL
        )
        & (
            data["target_speed"]
            >= float(data["target_speed"][selected])
            - screen.target_speed_loss_budget_mps
            - TOL
        )
        & (
            data["h10_distance"]
            >= float(data["h10_distance"][selected])
            - screen.h10_distance_loss_budget_m
            - TOL
        )
        & (data["h3_max_lateral"] <= screen.h3_max_lateral_limit_mps2 + TOL)
    )
    jerk_safe = bounded & (data["h3_mean_jerk"] <= data["h3_mean_jerk"][selected] + TOL)
    return {
        "lower_red_budget": bounded,
        "lower_red_budget_jerk_nondegrading": jerk_safe,
    }


def _budget_condition_masks(
    data: dict[str, Any], screen: BudgetScreen
) -> dict[str, np.ndarray]:
    selected = int(data["selected"])
    lower_red_base = _static_masks(data)["lower_red_base_feasible"]
    progress_ok = (
        data["progress"]
        >= float(data["progress"][selected]) - screen.progress_loss_budget_m - TOL
    )
    target_speed_ok = (
        data["target_speed"]
        >= float(data["target_speed"][selected])
        - screen.target_speed_loss_budget_mps
        - TOL
    )
    h10_distance_ok = (
        data["h10_distance"]
        >= float(data["h10_distance"][selected])
        - screen.h10_distance_loss_budget_m
        - TOL
    )
    h3_lateral_ok = data["h3_max_lateral"] <= screen.h3_max_lateral_limit_mps2 + TOL
    h3_jerk_ok = data["h3_mean_jerk"] <= data["h3_mean_jerk"][selected] + TOL
    bounded = (
        lower_red_base
        & progress_ok
        & target_speed_ok
        & h10_distance_ok
        & h3_lateral_ok
    )
    return {
        "lower_red_base": lower_red_base,
        "progress_ok": progress_ok,
        "target_speed_ok": target_speed_ok,
        "h10_distance_ok": h10_distance_ok,
        "h3_lateral_ok": h3_lateral_ok,
        "h3_jerk_ok": h3_jerk_ok,
        "bounded": bounded,
        "bounded_jerk_nondegrading": bounded & h3_jerk_ok,
    }


def _budget_blocker_row(
    data: dict[str, Any], screen: BudgetScreen
) -> dict[str, Any]:
    selected = int(data["selected"])
    lower_red_any = _static_masks(data)["lower_red_any"]
    masks = _budget_condition_masks(data, screen)
    lower_red_base = masks["lower_red_base"]
    bounded = masks["bounded"]
    bounded_jerk = masks["bounded_jerk_nondegrading"]
    row: dict[str, Any] = {
        "has_lower_red_any": bool(lower_red_any.any()),
        "has_lower_red_base_feasible": bool(lower_red_base.any()),
        "has_bounded": bool(bounded.any()),
        "has_bounded_jerk_nondegrading": bool(bounded_jerk.any()),
        "lower_red_base_feasible_count": int(lower_red_base.sum()),
        "bounded_count": int(bounded.sum()),
        "bounded_jerk_nondegrading_count": int(bounded_jerk.sum()),
        "progress_blocks_all": False,
        "target_speed_blocks_all": False,
        "h10_distance_blocks_all": False,
        "h3_lateral_blocks_all": False,
        "combination_blocks": False,
        "h3_jerk_blocks_bounded": False,
        "min_progress_loss_m": None,
        "min_target_speed_loss_mps": None,
        "min_h10_distance_loss_m": None,
        "min_h3_max_lateral_mps2": None,
        "min_h3_jerk_delta_mps3": None,
    }
    if not lower_red_base.any():
        return row

    row.update(
        {
            "min_progress_loss_m": _min_positive_loss(
                float(data["progress"][selected]), data["progress"], lower_red_base
            ),
            "min_target_speed_loss_mps": _min_positive_loss(
                float(data["target_speed"][selected]),
                data["target_speed"],
                lower_red_base,
            ),
            "min_h10_distance_loss_m": _min_positive_loss(
                float(data["h10_distance"][selected]),
                data["h10_distance"],
                lower_red_base,
            ),
            "min_h3_max_lateral_mps2": float(
                np.min(data["h3_max_lateral"][lower_red_base])
            ),
            "min_h3_jerk_delta_mps3": float(
                np.min(
                    data["h3_mean_jerk"][lower_red_base]
                    - float(data["h3_mean_jerk"][selected])
                )
            ),
        }
    )
    if not bounded.any():
        row["progress_blocks_all"] = not bool(
            (lower_red_base & masks["progress_ok"]).any()
        )
        row["target_speed_blocks_all"] = not bool(
            (lower_red_base & masks["target_speed_ok"]).any()
        )
        row["h10_distance_blocks_all"] = not bool(
            (lower_red_base & masks["h10_distance_ok"]).any()
        )
        row["h3_lateral_blocks_all"] = not bool(
            (lower_red_base & masks["h3_lateral_ok"]).any()
        )
        row["combination_blocks"] = not any(
            bool(row[key])
            for key in (
                "progress_blocks_all",
                "target_speed_blocks_all",
                "h10_distance_blocks_all",
                "h3_lateral_blocks_all",
            )
        )
    elif not bounded_jerk.any():
        row["h3_jerk_blocks_bounded"] = True
    return row


def _min_positive_loss(selected_value: float, values: np.ndarray, mask: np.ndarray) -> float:
    losses = np.maximum(selected_value - values[mask], 0.0)
    return float(np.min(losses))


def _mask_metrics(
    data: dict[str, Any], mask: np.ndarray, mode_threshold_m: float
) -> dict[str, Any]:
    raw_xy = data["raw_xy"]
    selected = int(data["selected"])
    endpoint = raw_xy[:, -1, :]
    selected_endpoint = endpoint[selected]
    count = int(mask.sum())
    metrics: dict[str, Any] = {
        "candidate_count": count,
        "nonempty": count > 0,
    }
    if count == 0:
        metrics.update(
            {
                "endpoint_pairwise_mean_m": None,
                "endpoint_pairwise_max_m": None,
                "selected_distance_mean_m": None,
                "selected_distance_min_m": None,
                "mode_count": 0,
            }
        )
        return metrics
    points = endpoint[mask]
    pairwise = _pairwise_distances(points)
    selected_distances = np.linalg.norm(points - selected_endpoint[None, :], axis=1)
    metrics.update(
        {
            "endpoint_pairwise_mean_m": _mean_or_zero(pairwise),
            "endpoint_pairwise_max_m": float(pairwise.max()) if pairwise.size else 0.0,
            "selected_distance_mean_m": float(selected_distances.mean()),
            "selected_distance_min_m": float(selected_distances.min()),
            "mode_count": _connected_mode_count(points, mode_threshold_m),
        }
    )
    return metrics


def _pairwise_distances(points: np.ndarray) -> np.ndarray:
    if points.shape[0] < 2:
        return np.asarray([], dtype=np.float64)
    diffs = points[:, None, :] - points[None, :, :]
    distances = np.linalg.norm(diffs, axis=2)
    rows, cols = np.triu_indices(points.shape[0], k=1)
    return distances[rows, cols]


def _connected_mode_count(points: np.ndarray, threshold: float) -> int:
    count = points.shape[0]
    if count == 0:
        return 0
    visited = np.zeros(count, dtype=bool)
    modes = 0
    for start in range(count):
        if visited[start]:
            continue
        modes += 1
        stack = [start]
        visited[start] = True
        while stack:
            current = stack.pop()
            distances = np.linalg.norm(points - points[current], axis=1)
            neighbors = np.flatnonzero((distances <= threshold + TOL) & ~visited)
            for neighbor in neighbors.tolist():
                visited[neighbor] = True
                stack.append(neighbor)
    return modes


def _mean_or_zero(values: np.ndarray) -> float:
    return float(values.mean()) if values.size else 0.0


def _summarize_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"records": 0, "nonempty_records": 0}
    nonempty = [row for row in rows if row["nonempty"]]
    summary = {
        "records": len(rows),
        "nonempty_records": len(nonempty),
        "nonempty_rate": len(nonempty) / len(rows),
        "candidate_count": _summary([row["candidate_count"] for row in rows]),
    }
    for key in (
        "endpoint_pairwise_mean_m",
        "endpoint_pairwise_max_m",
        "selected_distance_mean_m",
        "selected_distance_min_m",
        "mode_count",
    ):
        values = [row[key] for row in nonempty if row[key] is not None]
        summary[key] = _summary(values)
    return summary


def _summarize_budget_blockers(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"records": 0}
    base_rows = [row for row in rows if row["has_lower_red_base_feasible"]]
    bounded_rows = [row for row in rows if row["has_bounded"]]
    return {
        "records": len(rows),
        "with_lower_red_any": _count_rate(rows, "has_lower_red_any"),
        "with_lower_red_base_feasible": _count_rate(
            rows, "has_lower_red_base_feasible"
        ),
        "with_bounded": _count_rate(rows, "has_bounded"),
        "with_bounded_jerk_nondegrading": _count_rate(
            rows, "has_bounded_jerk_nondegrading"
        ),
        "progress_blocks_all": _count_rate(base_rows, "progress_blocks_all"),
        "target_speed_blocks_all": _count_rate(base_rows, "target_speed_blocks_all"),
        "h10_distance_blocks_all": _count_rate(base_rows, "h10_distance_blocks_all"),
        "h3_lateral_blocks_all": _count_rate(base_rows, "h3_lateral_blocks_all"),
        "combination_blocks": _count_rate(base_rows, "combination_blocks"),
        "h3_jerk_blocks_bounded": _count_rate(bounded_rows, "h3_jerk_blocks_bounded"),
        "lower_red_base_feasible_count": _summary(
            [row["lower_red_base_feasible_count"] for row in rows]
        ),
        "bounded_count": _summary([row["bounded_count"] for row in rows]),
        "bounded_jerk_nondegrading_count": _summary(
            [row["bounded_jerk_nondegrading_count"] for row in rows]
        ),
        "min_progress_loss_m": _summary_present(
            [row["min_progress_loss_m"] for row in rows]
        ),
        "min_target_speed_loss_mps": _summary_present(
            [row["min_target_speed_loss_mps"] for row in rows]
        ),
        "min_h10_distance_loss_m": _summary_present(
            [row["min_h10_distance_loss_m"] for row in rows]
        ),
        "min_h3_max_lateral_mps2": _summary_present(
            [row["min_h3_max_lateral_mps2"] for row in rows]
        ),
        "min_h3_jerk_delta_mps3": _summary_present(
            [row["min_h3_jerk_delta_mps3"] for row in rows]
        ),
    }


def _count_rate(rows: list[dict[str, Any]], key: str) -> dict[str, float | int]:
    count = sum(1 for row in rows if bool(row[key]))
    total = len(rows)
    return {
        "count": count,
        "total": total,
        "rate": count / total if total else 0.0,
    }


def _summary_present(values: list[float | int | None]) -> dict[str, float | None]:
    present = [value for value in values if value is not None]
    return _summary(present)


def _summary(values: list[float | int]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "p95": None, "max": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "p95": float(np.percentile(arr, 95)),
        "max": float(arr.max()),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Raw Horizon Candidate-Set Bottleneck Audit",
        "",
        "This is an offline diagnostic over fixed current-tick candidate constants.",
        "It does not change DP, CAMP weights, candidate generation, or selection.",
        "",
        "## Records",
        "",
        f"- Logs: `{report['records']['logs']}`",
        f"- Records: `{report['records']['total']}`",
        f"- Fallback records: `{report['records']['fallback']}`",
        f"- Nonfallback records: `{report['records']['nonfallback']}`",
        "",
        "## Event Counts",
        "",
    ]
    for name, value in report["events"].items():
        lines.append(f"- `{name}`: `{value}`")
    lines.extend(
        [
            "",
            "## Static Masks",
            "",
            "| Group | Mask | Nonempty | Candidate count | Mode count | Endpoint pairwise mean | Selected distance mean |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group_name in _preferred_groups(report):
        group = report["groups"][group_name]
        for mask_name in (
            "all_candidates",
            "base_feasible",
            "lower_red_any",
            "lower_red_base_feasible",
        ):
            summary = group["masks"][mask_name]
            lines.append(_summary_row(group_name, mask_name, summary))
    lines.extend(
        [
            "",
            "## Bounded Lower-Red Masks",
            "",
            "| Group | Screen | Mask | Nonempty | Candidate count | Mode count | Endpoint pairwise mean | Selected distance mean |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group_name in _preferred_groups(report):
        group = report["groups"][group_name]
        for screen_name, screen in group["budget_masks"].items():
            for mask_name in (
                "lower_red_budget",
                "lower_red_budget_jerk_nondegrading",
            ):
                lines.append(
                    _summary_row(
                        group_name,
                        f"{screen_name} / {mask_name}",
                        screen[mask_name],
                        columns=8,
                    )
                )
    lines.extend(
        [
            "",
            "## Budget Blockers",
            "",
            "| Group | Screen | Lower-red base feasible | Bounded | Bounded + jerk | Progress blocks all | Target-speed blocks all | H10 blocks all | Jerk blocks bounded | Min progress loss | Min H10 loss |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group_name in _preferred_groups(report):
        group = report["groups"][group_name]
        for screen_name, summary in group["budget_blockers"].items():
            lines.append(_blocker_row(group_name, screen_name, summary))
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["convexity_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _preferred_groups(report: dict[str, Any]) -> list[str]:
    preferred = [
        "all",
        "fallback=false",
        "selected_union_red_positive=true",
        "selected_h30_safe_full_red=true",
        "feasible_bucket=partial",
    ]
    return [name for name in preferred if name in report["groups"]]


def _summary_row(
    group_name: str, mask_name: str, summary: dict[str, Any], *, columns: int = 7
) -> str:
    values = [
        group_name,
        mask_name,
        f"{summary['nonempty_records']}/{summary['records']}",
        _fmt(summary["candidate_count"]["mean"]),
        _fmt(summary["mode_count"]["mean"]),
        _fmt(summary["endpoint_pairwise_mean_m"]["mean"]),
        _fmt(summary["selected_distance_mean_m"]["mean"]),
    ]
    if columns == 8:
        group, screen_mask, nonempty, count, modes, pairwise, selected = values
        screen, mask = screen_mask.split(" / ", 1)
        values = [group, screen, mask, nonempty, count, modes, pairwise, selected]
    return "| " + " | ".join(values) + " |"


def _blocker_row(group_name: str, screen_name: str, summary: dict[str, Any]) -> str:
    values = [
        group_name,
        screen_name,
        _count(summary["with_lower_red_base_feasible"]),
        _count(summary["with_bounded"]),
        _count(summary["with_bounded_jerk_nondegrading"]),
        _count(summary["progress_blocks_all"]),
        _count(summary["target_speed_blocks_all"]),
        _count(summary["h10_distance_blocks_all"]),
        _count(summary["h3_jerk_blocks_bounded"]),
        _fmt(summary["min_progress_loss_m"]["median"]),
        _fmt(summary["min_h10_distance_loss_m"]["median"]),
    ]
    return "| " + " | ".join(values) + " |"


def _count(payload: dict[str, Any]) -> str:
    return f"{payload['count']}/{payload['total']}"


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"


def _slug_float(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


if __name__ == "__main__":
    main()
