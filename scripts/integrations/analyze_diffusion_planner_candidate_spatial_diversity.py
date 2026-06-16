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
from scripts.integrations.analyze_diffusion_planner_outcome_free_alternative_candidates import (  # noqa: E402
    DEFAULT_SCREENS,
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


@dataclass(frozen=True)
class SpatialThresholds:
    lateral_mode_threshold_m: float = 0.25
    longitudinal_mode_threshold_m: float = 0.25
    mode_count_gap_min: float = 0.50
    endpoint_pairwise_gap_min_m: float = 0.10


SPATIAL_KEYS = (
    "admissible_count",
    "endpoint_pairwise_mean_m",
    "endpoint_pairwise_max_m",
    "endpoint_distance_mean_m",
    "endpoint_distance_max_m",
    "lateral_range_m",
    "longitudinal_range_m",
    "path_length_range_m",
    "heading_range_rad",
    "mode_count",
    "left_count",
    "right_count",
    "center_count",
    "ahead_count",
    "behind_count",
    "near_count",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit current-tick spatial/mode diversity inside bounded "
            "admissible DP+CAMP candidate sets. Outcomes are used only as "
            "offline labels for failure-tick grouping."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--screen", action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--lateral_mode_threshold_m", type=float, default=0.25)
    parser.add_argument("--longitudinal_mode_threshold_m", type=float, default=0.25)
    parser.add_argument("--mode_count_gap_min", type=float, default=0.50)
    parser.add_argument("--endpoint_pairwise_gap_min_m", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = SpatialThresholds(
        lateral_mode_threshold_m=args.lateral_mode_threshold_m,
        longitudinal_mode_threshold_m=args.longitudinal_mode_threshold_m,
        mode_count_gap_min=args.mode_count_gap_min,
        endpoint_pairwise_gap_min_m=args.endpoint_pairwise_gap_min_m,
    )
    report = analyze(
        [*args.root, *args.selection_log],
        label=args.label,
        screen_names=tuple(args.screen) or DEFAULT_SCREENS,
        thresholds=thresholds,
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
    thresholds: SpatialThresholds = SpatialThresholds(),
) -> dict[str, Any]:
    _validate_thresholds(thresholds)
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
            prefix = _prefix(raw_record, int(raw_record["num_candidates"]), label_text)
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
                    _failure_row(
                        record,
                        prefix,
                        admissible,
                        posterior_success,
                        thresholds,
                        log_path=log_path,
                        record_index=record_index,
                    )
                )

    return {
        "analysis": {
            "name": "dp_camp_candidate_spatial_diversity_v1",
            "role": (
                "offline current-tick endpoint and spatial-mode diversity "
                "audit for bounded-selector posterior failure ticks"
            ),
            "label": label,
            "screens": [screen["name"] for screen in screens],
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "posterior outcomes only split failure ticks by whether a "
                "successful alternative existed; spatial descriptors use "
                "current-tick finite candidate prefixes"
            ),
            "convexity_boundary": (
                "Endpoint and mode descriptors are fixed finite-candidate "
                "constants. If atomized later, fixed-set CAMP scoring remains "
                "affine in w and compatible with the simplex/CVaR/L2 convex "
                "master. This audit is not Benders and makes no "
                "trajectory-coordinate convexity claim."
            ),
        },
        "thresholds": thresholds.__dict__,
        "records": totals,
        "screens": [_screen_report(name, rows, thresholds) for name, rows in rows_by_screen.items()],
    }


def _validate_thresholds(thresholds: SpatialThresholds) -> None:
    values = thresholds.__dict__.values()
    if any(not np.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("Spatial thresholds must be finite and nonnegative.")


def _prefix(raw_record: dict[str, Any], candidate_count: int, label: str) -> np.ndarray:
    prefix = np.asarray(
        raw_record.get("candidate_perfect_tracker_postprocessed_reference_prefix"),
        dtype=np.float64,
    )
    if prefix.ndim != 3 or prefix.shape[0] != candidate_count or prefix.shape[1] < 2:
        raise ValueError(
            f"{label} candidate_perfect_tracker_postprocessed_reference_prefix "
            "must have shape [K,T>=2,D]."
        )
    if prefix.shape[2] < 2 or not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} prefix xy values must be finite.")
    if prefix.shape[2] >= 3 and not np.all(np.isfinite(prefix[:, :, 2])):
        raise ValueError(f"{label} prefix heading values must be finite.")
    return prefix


def _failure_row(
    record: dict[str, Any],
    prefix: np.ndarray,
    admissible: np.ndarray,
    posterior_success: np.ndarray,
    thresholds: SpatialThresholds,
    *,
    log_path: Path,
    record_index: int,
) -> dict[str, Any]:
    success = admissible & posterior_success
    return {
        "log_path": str(log_path),
        "record_index": int(record_index),
        "selected_index": int(record["selected_index"]),
        "has_any_admissible_success": bool(success.any()),
        "admissible_success_count": int(success.sum()),
        "spatial": _spatial_descriptors(prefix, int(record["selected_index"]), admissible, thresholds),
        "success_spatial": (
            None
            if not success.any()
            else _spatial_descriptors(prefix, int(record["selected_index"]), success, thresholds)
        ),
    }


def _spatial_descriptors(
    prefix: np.ndarray,
    selected: int,
    mask: np.ndarray,
    thresholds: SpatialThresholds,
) -> dict[str, float | int | bool]:
    indices = np.flatnonzero(mask)
    if indices.size == 0:
        raise ValueError("Spatial descriptors require at least one candidate.")
    endpoints = prefix[:, -1, :2]
    starts = prefix[:, 0, :2]
    path_lengths = np.asarray([_path_length(prefix[index, :, :2]) for index in range(prefix.shape[0])])
    axis = _selected_axis(prefix, selected)
    lateral_axis = np.asarray([-axis[1], axis[0]], dtype=np.float64)
    deltas = endpoints - endpoints[selected]
    longitudinal = deltas @ axis
    lateral = deltas @ lateral_axis
    candidate_endpoints = endpoints[indices]
    pairwise = _pairwise_distances(candidate_endpoints)
    endpoint_distance = np.linalg.norm(deltas[indices], axis=1)
    heading_range = _heading_range(prefix, indices)
    lateral_bins = [_mode_bin(float(lateral[index]), thresholds.lateral_mode_threshold_m) for index in indices]
    longitudinal_bins = [
        _mode_bin(float(longitudinal[index]), thresholds.longitudinal_mode_threshold_m)
        for index in indices
    ]
    modes = set(zip(lateral_bins, longitudinal_bins))
    left_count = sum(int(value == "positive") for value in lateral_bins)
    right_count = sum(int(value == "negative") for value in lateral_bins)
    ahead_count = sum(int(value == "positive") for value in longitudinal_bins)
    behind_count = sum(int(value == "negative") for value in longitudinal_bins)
    return {
        "admissible_count": int(indices.size),
        "endpoint_pairwise_mean_m": float(np.mean(pairwise)) if pairwise.size else 0.0,
        "endpoint_pairwise_max_m": float(np.max(pairwise)) if pairwise.size else 0.0,
        "endpoint_distance_mean_m": float(np.mean(endpoint_distance)),
        "endpoint_distance_max_m": float(np.max(endpoint_distance)),
        "lateral_range_m": float(np.ptp(lateral[indices])),
        "longitudinal_range_m": float(np.ptp(longitudinal[indices])),
        "path_length_range_m": float(np.ptp(path_lengths[indices])),
        "heading_range_rad": heading_range,
        "mode_count": int(len(modes)),
        "left_count": int(left_count),
        "right_count": int(right_count),
        "center_count": int(indices.size - left_count - right_count),
        "ahead_count": int(ahead_count),
        "behind_count": int(behind_count),
        "near_count": int(indices.size - ahead_count - behind_count),
        "has_lateral_both_sides": bool(left_count > 0 and right_count > 0),
        "has_longitudinal_both_sides": bool(ahead_count > 0 and behind_count > 0),
    }


def _path_length(xy: np.ndarray) -> float:
    return float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1)))


def _selected_axis(prefix: np.ndarray, selected: int) -> np.ndarray:
    vector = prefix[selected, -1, :2] - prefix[selected, 0, :2]
    norm = float(np.linalg.norm(vector))
    if norm > TOL:
        return vector / norm
    if prefix.shape[2] >= 3:
        heading = float(prefix[selected, 0, 2])
        return np.asarray([np.cos(heading), np.sin(heading)], dtype=np.float64)
    return np.asarray([1.0, 0.0], dtype=np.float64)


def _pairwise_distances(points: np.ndarray) -> np.ndarray:
    if points.shape[0] < 2:
        return np.asarray([], dtype=np.float64)
    values = []
    for left in range(points.shape[0] - 1):
        for right in range(left + 1, points.shape[0]):
            values.append(float(np.linalg.norm(points[left] - points[right])))
    return np.asarray(values, dtype=np.float64)


def _heading_range(prefix: np.ndarray, indices: np.ndarray) -> float:
    if prefix.shape[2] < 3:
        return 0.0
    headings = prefix[indices, -1, 2]
    unwrapped = np.unwrap(headings)
    return float(np.ptp(unwrapped))


def _mode_bin(value: float, threshold: float) -> str:
    if value > threshold:
        return "positive"
    if value < -threshold:
        return "negative"
    return "near"


def _screen_report(
    name: str,
    rows: list[dict[str, Any]],
    thresholds: SpatialThresholds,
) -> dict[str, Any]:
    with_success = [row for row in rows if row["has_any_admissible_success"]]
    without_success = [row for row in rows if not row["has_any_admissible_success"]]
    groups = _groups(rows, with_success, without_success)
    summaries = {
        group: {
            key: _summary([float(row["spatial"][key]) for row in group_rows])
            for key in SPATIAL_KEYS
        }
        for group, group_rows in groups.items()
    }
    success_summaries = {
        key: _summary(
            [
                float(row["success_spatial"][key])
                for row in with_success
                if row["success_spatial"] is not None
            ]
        )
        for key in SPATIAL_KEYS
    }
    evidence = _spatial_bottleneck_evidence(summaries, thresholds)
    return {
        "name": name,
        "records": {
            "failure_ticks": len(rows),
            "with_any_admissible_success": len(with_success),
            "without_any_admissible_success": len(without_success),
        },
        "group_summaries": summaries,
        "success_candidate_summaries": success_summaries,
        "spatial_bottleneck_evidence": evidence,
        "next_step": (
            "inspect_generator_spatial_modes"
            if evidence["evidence_present"]
            else "reject_simple_spatial_spread_explanation"
        ),
    }


def _groups(
    rows: list[dict[str, Any]],
    with_success: list[dict[str, Any]],
    without_success: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "all": rows,
        "with_any_success": with_success,
        "without_any_success": without_success,
    }


def _spatial_bottleneck_evidence(
    summaries: dict[str, dict[str, dict[str, float | int | None]]],
    thresholds: SpatialThresholds,
) -> dict[str, Any]:
    with_group = summaries["with_any_success"]
    without_group = summaries["without_any_success"]
    mode_gap = _gap(with_group["mode_count"]["mean"], without_group["mode_count"]["mean"])
    pairwise_gap = _gap(
        with_group["endpoint_pairwise_mean_m"]["mean"],
        without_group["endpoint_pairwise_mean_m"]["mean"],
    )
    lateral_gap = _gap(with_group["lateral_range_m"]["mean"], without_group["lateral_range_m"]["mean"])
    mode_evidence = mode_gap is not None and mode_gap >= thresholds.mode_count_gap_min
    pairwise_evidence = (
        pairwise_gap is not None
        and pairwise_gap >= thresholds.endpoint_pairwise_gap_min_m
    )
    return {
        "mode_count_gap_with_minus_without": mode_gap,
        "endpoint_pairwise_gap_m_with_minus_without": pairwise_gap,
        "lateral_range_gap_m_with_minus_without": lateral_gap,
        "mode_count_evidence": bool(mode_evidence),
        "endpoint_pairwise_evidence": bool(pairwise_evidence),
        "evidence_present": bool(mode_evidence or pairwise_evidence),
    }


def _gap(left: float | int | None, right: float | int | None) -> float | None:
    if left is None or right is None:
        return None
    return float(left) - float(right)


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
    thresholds = report["thresholds"]
    lines = [
        "# DP CAMP Candidate Spatial Diversity Audit",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        "",
        "This report audits current-tick endpoint and spatial-mode diversity "
        "inside bounded admissible candidate sets on posterior failure ticks. "
        "Outcomes are labels only.",
        "",
        "Mode thresholds: lateral "
        f"`{thresholds['lateral_mode_threshold_m']}` m, longitudinal "
        f"`{thresholds['longitudinal_mode_threshold_m']}` m.",
        "",
    ]
    for screen in report["screens"]:
        records = screen["records"]
        evidence = screen["spatial_bottleneck_evidence"]
        lines.extend(
            [
                f"## `{screen['name']}`",
                "",
                f"- Failure ticks: {records['failure_ticks']}",
                f"- With posterior-success alternative: {records['with_any_admissible_success']}",
                f"- Without posterior-success alternative: {records['without_any_admissible_success']}",
                f"- Spatial bottleneck evidence: {_pass_fail(evidence['evidence_present'])}",
                f"- Next step: `{screen['next_step']}`",
                "",
                "| Group | Mode count | Endpoint pairwise mean | Endpoint max | "
                "Lateral range | Longitudinal range | Path length range |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for group in ("all", "with_any_success", "without_any_success"):
            summary = screen["group_summaries"][group]
            lines.append(
                f"| `{group}` | {_fmt(summary['mode_count']['mean'])} | "
                f"{_fmt(summary['endpoint_pairwise_mean_m']['mean'])} | "
                f"{_fmt(summary['endpoint_pairwise_max_m']['mean'])} | "
                f"{_fmt(summary['lateral_range_m']['mean'])} | "
                f"{_fmt(summary['longitudinal_range_m']['mean'])} | "
                f"{_fmt(summary['path_length_range_m']['mean'])} |"
            )
        lines.extend(
            [
                "",
                f"- Mode-count gap with-minus-without: "
                f"`{_fmt(evidence['mode_count_gap_with_minus_without'])}`",
                f"- Endpoint-pairwise gap with-minus-without: "
                f"`{_fmt(evidence['endpoint_pairwise_gap_m_with_minus_without'])}` m",
                "",
            ]
        )
    lines.extend(
        [
            "Mathematical boundary: endpoint and spatial-mode descriptors are "
            "fixed finite-candidate constants. This audit is not Benders and "
            "does not claim trajectory-coordinate convexity.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | int | None) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"


def _pass_fail(value: bool) -> str:
    return "present" if value else "absent"


if __name__ == "__main__":
    main()
