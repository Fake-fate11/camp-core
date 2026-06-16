#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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
DT_S = 0.1


@dataclass(frozen=True)
class SpliceConfig:
    anchor_steps: int = 10
    blend_steps: int = 10
    material_endpoint_threshold_m: float = 1.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline stop-aware raw-H80 tail-splice potential audit. The audit "
            "constructs diagnostic H10-preserving splice geometry from logged "
            "current-tick candidates only; it is not an online selector and does "
            "not recompute DP red-light or feasibility rewards."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--anchor_steps", type=int, default=10)
    parser.add_argument("--blend_steps", type=int, default=10)
    parser.add_argument("--material_endpoint_threshold_m", type=float, default=1.0)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        config=SpliceConfig(
            anchor_steps=args.anchor_steps,
            blend_steps=args.blend_steps,
            material_endpoint_threshold_m=args.material_endpoint_threshold_m,
        ),
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
    config: SpliceConfig = SpliceConfig(),
) -> dict[str, Any]:
    _validate_config(config)
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    totals = {
        "logs": len(log_paths),
        "records": 0,
        "selected_h30_safe_full_red": 0,
    }
    rows_by_pool = {
        "lower_red_any": [],
        "lower_red_base_feasible": [],
    }

    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(payload):
            totals["records"] += 1
            label_text = f"{log_path} record {record_index}"
            data = _record_data(record, config, label_text)
            if not data["selected_h30_safe_full_red"]:
                continue
            totals["selected_h30_safe_full_red"] += 1
            for pool_name, mask in _donor_masks(data).items():
                rows_by_pool[pool_name].append(
                    _record_pool_summary(data, mask, config)
                )

    return {
        "analysis": {
            "name": "dp_camp_stop_aware_splice_potential_v1",
            "role": (
                "offline raw-H80 H10-preserving lower-red tail-splice potential "
                "audit over logged Diffusion Planner candidate prefixes"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "red_or_feasibility_recomputed_for_splice": False,
            "convexity_boundary": (
                "The splice geometry is deterministic from fixed current-tick "
                "candidate prefixes and a fixed donor rule. It is a finite "
                "candidate-set diagnostic, not Benders; no trajectory-coordinate "
                "convexity or red-light feasibility certificate is claimed for "
                "the synthetic splice without a separate DP reward recomputation."
            ),
        },
        "config": config.__dict__,
        "records": totals,
        "donor_pools": {
            pool_name: _summarize_pool(rows, config)
            for pool_name, rows in rows_by_pool.items()
        },
    }


def _validate_config(config: SpliceConfig) -> None:
    if config.anchor_steps < 2:
        raise ValueError("anchor_steps must be at least 2.")
    if config.blend_steps < 0:
        raise ValueError("blend_steps must be nonnegative.")
    if (
        not np.isfinite(config.material_endpoint_threshold_m)
        or config.material_endpoint_threshold_m < 0.0
    ):
        raise ValueError("material_endpoint_threshold_m must be finite and nonnegative.")


def _record_data(
    record: dict[str, Any], config: SpliceConfig, label: str
) -> dict[str, Any]:
    raw = np.asarray(record.get("candidate_raw_trajectory_prefix"), dtype=np.float64)
    if raw.ndim != 3 or raw.shape[0] <= 0 or raw.shape[2] < 2:
        raise ValueError(f"{label} candidate_raw_trajectory_prefix must be [K,T,D>=2].")
    if raw.shape[1] <= config.anchor_steps:
        raise ValueError(
            f"{label} raw prefix length must exceed anchor_steps={config.anchor_steps}."
        )
    if not np.all(np.isfinite(raw[:, :, :2])):
        raise ValueError(f"{label} raw prefix xy values must be finite.")
    count = raw.shape[0]
    selected = int(record.get("selected_index"))
    if selected < 0 or selected >= count:
        raise ValueError(f"{label} selected_index is out of range.")
    feasible = _bool_vector(record.get("feasible_mask"), count, label, "feasible_mask")
    short_red = _short_red(record, count, label)
    full_red = _vector(
        record.get("candidate_full_horizon_planned_red_light_cost"),
        count,
        label,
        "candidate_full_horizon_planned_red_light_cost",
    )
    union_red = _union_red(record, count, label)
    selected_h30_safe_full_red = bool(short_red[selected] <= TOL and full_red[selected] > TOL)
    return {
        "xy": raw[:, :, :2],
        "selected": selected,
        "feasible": feasible,
        "union_red": union_red,
        "selected_h30_safe_full_red": selected_h30_safe_full_red,
    }


def _donor_masks(data: dict[str, Any]) -> dict[str, np.ndarray]:
    selected = int(data["selected"])
    lower_red = data["union_red"] < float(data["union_red"][selected]) - TOL
    lower_red[selected] = False
    return {
        "lower_red_any": lower_red,
        "lower_red_base_feasible": lower_red & data["feasible"],
    }


def _record_pool_summary(
    data: dict[str, Any], donor_mask: np.ndarray, config: SpliceConfig
) -> dict[str, Any]:
    donor_indices = np.flatnonzero(donor_mask)
    row: dict[str, Any] = {
        "candidate_count": int(donor_indices.size),
        "has_donor": bool(donor_indices.size),
        "has_material_splice": False,
        "has_jerk_nondegrading_splice": False,
        "has_material_and_jerk_nondegrading_splice": False,
        "best_splice": None,
    }
    if donor_indices.size == 0:
        return row

    selected_xy = data["xy"][int(data["selected"])]
    selected_jerk = _mean_third_difference(selected_xy)
    splice_rows = []
    for donor in donor_indices.tolist():
        donor_xy = data["xy"][donor]
        splice_xy = _h10_preserving_tail_splice(
            selected_xy,
            donor_xy,
            anchor_steps=config.anchor_steps,
            blend_steps=config.blend_steps,
        )
        endpoint_distance = float(np.linalg.norm(splice_xy[-1] - selected_xy[-1]))
        splice_jerk = _mean_third_difference(splice_xy)
        jerk_delta = splice_jerk - selected_jerk
        h10_max_deviation = float(
            np.max(
                np.linalg.norm(
                    splice_xy[: config.anchor_steps] - selected_xy[: config.anchor_steps],
                    axis=1,
                )
            )
        )
        row_metrics = {
            "donor_index": donor,
            "endpoint_distance_to_selected_m": endpoint_distance,
            "endpoint_distance_to_donor_m": float(
                np.linalg.norm(splice_xy[-1] - donor_xy[-1])
            ),
            "max_selected_deviation_m": float(
                np.max(np.linalg.norm(splice_xy - selected_xy, axis=1))
            ),
            "h10_max_deviation_m": h10_max_deviation,
            "selected_mean_third_difference_mps3": selected_jerk,
            "splice_mean_third_difference_mps3": splice_jerk,
            "splice_mean_third_difference_delta_mps3": jerk_delta,
            "material_endpoint": endpoint_distance
            >= config.material_endpoint_threshold_m - TOL,
            "jerk_nondegrading": jerk_delta <= TOL,
        }
        splice_rows.append(row_metrics)

    row["has_material_splice"] = any(item["material_endpoint"] for item in splice_rows)
    row["has_jerk_nondegrading_splice"] = any(
        item["jerk_nondegrading"] for item in splice_rows
    )
    row["has_material_and_jerk_nondegrading_splice"] = any(
        item["material_endpoint"] and item["jerk_nondegrading"] for item in splice_rows
    )
    row["best_splice"] = min(
        splice_rows,
        key=lambda item: (
            item["splice_mean_third_difference_delta_mps3"],
            -item["endpoint_distance_to_selected_m"],
            item["donor_index"],
        ),
    )
    return row


def _h10_preserving_tail_splice(
    selected_xy: np.ndarray,
    donor_xy: np.ndarray,
    *,
    anchor_steps: int,
    blend_steps: int,
) -> np.ndarray:
    if selected_xy.shape != donor_xy.shape:
        raise ValueError("selected and donor prefixes must have the same shape.")
    anchor_index = anchor_steps - 1
    tail = selected_xy[anchor_index] + (donor_xy - donor_xy[anchor_index])
    splice = selected_xy.copy()
    for step in range(anchor_index + 1, selected_xy.shape[0]):
        if blend_steps == 0:
            weight = 1.0
        else:
            u = min(max((step - anchor_index) / float(blend_steps), 0.0), 1.0)
            weight = u * u * (3.0 - 2.0 * u)
        splice[step] = (1.0 - weight) * selected_xy[step] + weight * tail[step]
    splice[:anchor_steps] = selected_xy[:anchor_steps]
    return splice


def _mean_third_difference(xy: np.ndarray) -> float:
    if xy.shape[0] < 4:
        return 0.0
    third = np.diff(xy, n=3, axis=0) / (DT_S**3)
    return float(np.linalg.norm(third, axis=1).mean())


def _short_red(record: dict[str, Any], count: int, label: str) -> np.ndarray:
    planned = _optional_vector(record.get("candidate_planned_red_light_cost"), count)
    if planned is not None:
        return planned
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != count:
        raise ValueError(
            f"{label} candidate_planned_red_light_cost or dp_candidate_rewards red_light is required."
        )
    values = np.asarray(
        [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in rewards],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{label} short red values must be finite.")
    return values


def _union_red(record: dict[str, Any], count: int, label: str) -> np.ndarray:
    union = _optional_vector(record.get("candidate_horizon_union_planned_red_light_cost"), count)
    if union is not None:
        return union
    short = _short_red(record, count, label)
    full = _vector(
        record.get("candidate_full_horizon_planned_red_light_cost"),
        count,
        label,
        "candidate_full_horizon_planned_red_light_cost",
    )
    return np.maximum(short, full)


def _optional_vector(value: Any, count: int) -> np.ndarray | None:
    if value is None:
        return None
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (count,) or not np.all(np.isfinite(arr)):
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


def _summarize_pool(rows: list[dict[str, Any]], config: SpliceConfig) -> dict[str, Any]:
    best = [row["best_splice"] for row in rows if row["best_splice"] is not None]
    return {
        "records": len(rows),
        "with_donor": _count_rate(rows, "has_donor"),
        "with_material_splice": _count_rate(rows, "has_material_splice"),
        "with_jerk_nondegrading_splice": _count_rate(
            rows, "has_jerk_nondegrading_splice"
        ),
        "with_material_and_jerk_nondegrading_splice": _count_rate(
            rows, "has_material_and_jerk_nondegrading_splice"
        ),
        "candidate_count": _summary([row["candidate_count"] for row in rows]),
        "best_splice": {
            "endpoint_distance_to_selected_m": _summary(
                [item["endpoint_distance_to_selected_m"] for item in best]
            ),
            "endpoint_distance_to_donor_m": _summary(
                [item["endpoint_distance_to_donor_m"] for item in best]
            ),
            "max_selected_deviation_m": _summary(
                [item["max_selected_deviation_m"] for item in best]
            ),
            "h10_max_deviation_m": _summary(
                [item["h10_max_deviation_m"] for item in best]
            ),
            "splice_mean_third_difference_delta_mps3": _summary(
                [item["splice_mean_third_difference_delta_mps3"] for item in best]
            ),
        },
        "material_endpoint_threshold_m": config.material_endpoint_threshold_m,
    }


def _count_rate(rows: list[dict[str, Any]], key: str) -> dict[str, float | int]:
    count = sum(1 for row in rows if bool(row[key]))
    total = len(rows)
    return {"count": count, "total": total, "rate": count / total if total else 0.0}


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
        "# Stop-Aware Splice Potential Audit",
        "",
        "This is an offline raw-H80 geometry diagnostic. It does not recompute DP red-light rewards, feasibility, or CAMP scores.",
        "",
        "## Records",
        "",
        f"- Logs: `{report['records']['logs']}`",
        f"- Records: `{report['records']['records']}`",
        f"- Selected h30-safe/full-red records: `{report['records']['selected_h30_safe_full_red']}`",
        "",
        "## Donor Pools",
        "",
        "| Pool | Donor records | Material splice | Jerk nondegrading | Material + jerk | Best endpoint distance | Best jerk delta | H10 deviation |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for pool_name, summary in report["donor_pools"].items():
        best = summary["best_splice"]
        lines.append(
            "| "
            + " | ".join(
                [
                    pool_name,
                    _count(summary["with_donor"]),
                    _count(summary["with_material_splice"]),
                    _count(summary["with_jerk_nondegrading_splice"]),
                    _count(summary["with_material_and_jerk_nondegrading_splice"]),
                    _fmt(best["endpoint_distance_to_selected_m"]["mean"]),
                    _fmt(best["splice_mean_third_difference_delta_mps3"]["mean"]),
                    _fmt(best["h10_max_deviation_m"]["max"]),
                ]
            )
            + " |"
        )
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


def _count(payload: dict[str, Any]) -> str:
    return f"{payload['count']}/{payload['total']}"


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.6f}"


if __name__ == "__main__":
    main()
