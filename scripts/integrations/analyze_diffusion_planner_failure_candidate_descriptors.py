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
from scripts.integrations.analyze_diffusion_planner_outcome_free_alternative_candidates import (  # noqa: E402
    DEFAULT_SCREENS,
    GUARD_SETS,
    _current_tick_feature_values,
    _posterior_success_mask,
    _selected_screens,
)
from scripts.integrations.analyze_diffusion_planner_outcome_free_bounded_selector import (  # noqa: E402
    TOL,
    _admissible_mask,
    _choose,
    _load_record,
    _result_row,
)


CORE_FEATURES = (
    "progress_proxy",
    "target_speed",
    "h10_displacement",
    "raw_lateral",
    "raw_jerk",
)
OPTIONAL_FEATURES = (
    "tracker_command_jerk_mps3",
    "prefix_jerk_proxy",
    "rollout_h3_mean_vector_jerk_mps3",
    "rollout_h3_distance_m",
)
HIGHER_IS_BETTER = {
    "progress_proxy",
    "target_speed",
    "h10_displacement",
    "rollout_h3_distance_m",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize current-tick finite-candidate descriptors on bounded "
            "selector failure ticks. Outcomes are used only to split failure "
            "ticks by posterior alternative availability."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--screen", action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        screen_names=tuple(args.screen) or DEFAULT_SCREENS,
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
    screen_names: tuple[str, ...] = DEFAULT_SCREENS,
) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")
    screens = _selected_screens(screen_names)
    rows_by_screen = {screen["name"]: [] for screen in screens}
    totals = {"logs": len(log_paths), "total": 0, "nonfallback": 0, "fallback": 0}

    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, raw_record in enumerate(payload):
            totals["total"] += 1
            label_text = f"{log_path} record {record_index}"
            record = _load_record(raw_record, label_text)
            fallback = not record["feasible"].any()
            totals["fallback"] += int(fallback)
            totals["nonfallback"] += int(not fallback)
            if fallback:
                continue
            features = _feature_values(raw_record, record, label_text)
            posterior_success = _posterior_success_mask(record)
            for screen in screens:
                admissible = _admissible_mask(record, screen)
                if not admissible.any():
                    continue
                chosen = _choose(record, admissible)
                result = _result_row(record, chosen, opportunity=True, fallback=False)
                if not result["changed"] or bool(result["posterior_joint_comfort_improvement"]):
                    continue
                rows_by_screen[screen["name"]].append(
                    _descriptor_row(
                        record,
                        admissible,
                        posterior_success,
                        features,
                        log_path=log_path,
                        record_index=record_index,
                    )
                )

    return {
        "analysis": {
            "name": "dp_camp_failure_candidate_descriptors_v1",
            "role": (
                "outcome-free descriptor audit for bounded-selector posterior "
                "joint-comfort failure ticks"
            ),
            "label": label,
            "screens": [screen["name"] for screen in screens],
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "posterior outcomes only split failure ticks by whether a "
                "successful alternative existed; descriptors use current-tick "
                "finite candidate constants"
            ),
            "convexity_boundary": (
                "All descriptor quantities are fixed finite-candidate values. "
                "If atomized later, fixed-set CAMP scoring remains affine in "
                "w and compatible with the simplex/CVaR/L2 convex master. "
                "This diagnostic is not Benders and makes no "
                "trajectory-coordinate convexity claim."
            ),
            "descriptor_features": list(CORE_FEATURES + OPTIONAL_FEATURES),
        },
        "records": totals,
        "screens": [_screen_report(name, rows) for name, rows in rows_by_screen.items()],
    }


def _feature_values(
    raw_record: dict[str, Any],
    record: dict[str, Any],
    label: str,
) -> dict[str, np.ndarray]:
    features = {name: np.asarray(record[name], dtype=np.float64) for name in CORE_FEATURES}
    features.update(
        _current_tick_feature_values(
            raw_record,
            int(raw_record["num_candidates"]),
            label,
        )
    )
    return features


def _descriptor_row(
    record: dict[str, Any],
    admissible: np.ndarray,
    posterior_success: np.ndarray,
    features: dict[str, np.ndarray],
    *,
    log_path: Path,
    record_index: int,
) -> dict[str, Any]:
    selected = int(record["selected_index"])
    admissible_success = admissible & posterior_success
    feature_rows = {
        name: _feature_descriptor(name, values, selected, admissible)
        for name, values in features.items()
        if admissible.any()
    }
    guard_rows = [
        _guard_descriptor(
            guard,
            admissible,
            posterior_success,
            features,
            selected=selected,
        )
        for guard in GUARD_SETS
    ]
    return {
        "log_path": str(log_path),
        "record_index": int(record_index),
        "selected_index": selected,
        "admissible_count": int(admissible.sum()),
        "admissible_success_count": int(admissible_success.sum()),
        "has_any_admissible_success": bool(admissible_success.any()),
        "features": feature_rows,
        "guard_sets": guard_rows,
    }


def _feature_descriptor(
    name: str,
    values: np.ndarray,
    selected: int,
    admissible: np.ndarray,
) -> dict[str, float]:
    candidate_values = values[admissible]
    selected_value = float(values[selected])
    deltas = candidate_values - selected_value
    if name in HIGHER_IS_BETTER:
        best_delta = float(np.max(deltas))
    else:
        best_delta = float(np.min(deltas))
    return {
        "selected_value": selected_value,
        "range": float(np.ptp(candidate_values)),
        "best_delta": best_delta,
    }


def _guard_descriptor(
    guard: dict[str, Any],
    admissible: np.ndarray,
    posterior_success: np.ndarray,
    features: dict[str, np.ndarray],
    *,
    selected: int,
) -> dict[str, Any]:
    required = tuple(str(feature) for feature in guard["features"])
    missing = [feature for feature in required if feature not in features]
    guard_mask = admissible.copy()
    if missing:
        guard_mask &= False
    else:
        for feature in required:
            values = features[feature]
            if feature.endswith("distance_m"):
                guard_mask &= values >= values[selected] - TOL
            else:
                guard_mask &= values <= values[selected] + TOL
    return {
        "name": str(guard["name"]),
        "missing_features": missing,
        "guarded_admissible_count": int(guard_mask.sum()),
        "guarded_success_count": int((guard_mask & posterior_success).sum()),
        "has_guarded_success": bool((guard_mask & posterior_success).any()),
    }


def _screen_report(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    with_success = [row for row in rows if row["has_any_admissible_success"]]
    without_success = [row for row in rows if not row["has_any_admissible_success"]]
    return {
        "name": name,
        "records": {
            "failure_ticks": len(rows),
            "with_any_admissible_success": len(with_success),
            "without_any_admissible_success": len(without_success),
        },
        "candidate_counts": {
            group: {
                "admissible": _summary([float(row["admissible_count"]) for row in group_rows]),
                "admissible_success": _summary(
                    [float(row["admissible_success_count"]) for row in group_rows]
                ),
            }
            for group, group_rows in _groups(rows, with_success, without_success)
        },
        "feature_range_summary": _feature_summary(rows, with_success, without_success, "range"),
        "feature_best_delta_summary": _feature_summary(
            rows,
            with_success,
            without_success,
            "best_delta",
        ),
        "guard_summary": _guard_summary(rows, with_success, without_success),
    }


def _groups(
    rows: list[dict[str, Any]],
    with_success: list[dict[str, Any]],
    without_success: list[dict[str, Any]],
) -> tuple[tuple[str, list[dict[str, Any]]], ...]:
    return (
        ("all", rows),
        ("with_any_success", with_success),
        ("without_any_success", without_success),
    )


def _feature_summary(
    rows: list[dict[str, Any]],
    with_success: list[dict[str, Any]],
    without_success: list[dict[str, Any]],
    key: str,
) -> dict[str, dict[str, dict[str, float | int | None]]]:
    feature_names = sorted({name for row in rows for name in row["features"]})
    return {
        feature: {
            group: _summary(
                [
                    float(row["features"][feature][key])
                    for row in group_rows
                    if feature in row["features"]
                ]
            )
            for group, group_rows in _groups(rows, with_success, without_success)
        }
        for feature in feature_names
    }


def _guard_summary(
    rows: list[dict[str, Any]],
    with_success: list[dict[str, Any]],
    without_success: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    names = sorted({guard["name"] for row in rows for guard in row["guard_sets"]})
    result: dict[str, dict[str, Any]] = {}
    for name in names:
        result[name] = {}
        for group, group_rows in _groups(rows, with_success, without_success):
            guards = [
                guard
                for row in group_rows
                for guard in row["guard_sets"]
                if guard["name"] == name
            ]
            result[name][group] = {
                "records": len(group_rows),
                "with_guarded_success": sum(
                    int(guard["has_guarded_success"]) for guard in guards
                ),
                "guarded_success_rate": (
                    sum(int(guard["has_guarded_success"]) for guard in guards)
                    / max(len(group_rows), 1)
                ),
                "guarded_admissible_count": _summary(
                    [float(guard["guarded_admissible_count"]) for guard in guards]
                ),
                "guarded_success_count": _summary(
                    [float(guard["guarded_success_count"]) for guard in guards]
                ),
            }
    return result


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p90": None, "p95": None}
    arr = np.asarray(values, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
        "p95": float(np.percentile(arr, 95.0)),
    }


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    lines = [
        "# DP CAMP Failure Candidate Descriptor Audit",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        "",
        "This diagnostic summarizes current-tick finite-candidate descriptors "
        "only on posterior joint-comfort failure ticks. Outcomes are used only "
        "to split those failure ticks by whether a posterior-success "
        "alternative existed.",
        "",
    ]
    key_features = (
        "progress_proxy",
        "raw_lateral",
        "raw_jerk",
        "prefix_jerk_proxy",
        "tracker_command_jerk_mps3",
        "rollout_h3_mean_vector_jerk_mps3",
    )
    for screen in report["screens"]:
        counts = screen["records"]
        lines.extend(
            [
                f"## `{screen['name']}`",
                "",
                f"- Failure ticks: {counts['failure_ticks']}",
                f"- With any admissible posterior-success alternative: "
                f"{counts['with_any_admissible_success']}",
                "",
                "| Feature | Best delta all | Best delta with success | "
                "Best delta without success | Range without success |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for feature in key_features:
            if feature not in screen["feature_best_delta_summary"]:
                continue
            best = screen["feature_best_delta_summary"][feature]
            ranges = screen["feature_range_summary"][feature]
            lines.append(
                f"| `{feature}` | {_fmt(best['all']['mean'])} | "
                f"{_fmt(best['with_any_success']['mean'])} | "
                f"{_fmt(best['without_any_success']['mean'])} | "
                f"{_fmt(ranges['without_any_success']['mean'])} |"
            )
        lines.extend(
            [
                "",
                "### Guard Availability",
                "",
                "| Guard set | Guarded success rate all | With-success group | "
                "Without-success group guarded admissible mean |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for guard_name, groups in screen["guard_summary"].items():
            lines.append(
                f"| `{guard_name}` | "
                f"{groups['all']['guarded_success_rate']:.6f} | "
                f"{groups['with_any_success']['guarded_success_rate']:.6f} | "
                f"{_fmt(groups['without_any_success']['guarded_admissible_count']['mean'])} |"
            )
        lines.append("")
    return "\n".join(lines)


def _fmt(value: float | int | None) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"


if __name__ == "__main__":
    main()
