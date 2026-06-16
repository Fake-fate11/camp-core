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


TOL = 1.0e-9
THRESHOLDS_M = (0.001, 0.01, 0.1)
SUMMARY_KEYS = (
    "prefix_steps",
    "raw_endpoint_pairwise_mean_m",
    "post_endpoint_pairwise_mean_m",
    "endpoint_pairwise_mean_ratio",
    "raw_prefix_pairwise_mean_m",
    "post_prefix_pairwise_mean_m",
    "prefix_pairwise_mean_ratio",
    "raw_selected_distance_mean_m",
    "post_selected_distance_mean_m",
    "selected_distance_mean_ratio",
    "raw_to_post_mean_m",
    "raw_to_post_max_m",
    "selected_raw_to_post_mean_m",
    "selected_raw_to_post_max_m",
    "raw_post_selected_distance_corr",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit how much raw Diffusion Planner candidate prefix geometry is "
            "preserved after PerfectTracker reference postprocessing. This is "
            "an offline geometry diagnostic over fixed logged candidates."
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

    rows: list[dict[str, float]] = []
    records_total = 0
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_index, record in enumerate(payload):
            records_total += 1
            rows.append(_row(record, f"{log_path} record {record_index}"))

    return {
        "analysis": {
            "name": "dp_camp_raw_prefix_geometry_v1",
            "role": (
                "offline geometry audit comparing raw DP candidate prefixes "
                "with PerfectTracker postprocessed reference prefixes"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "convexity_boundary": (
                "All measured quantities are fixed finite-candidate constants "
                "from the current tick. If atomized later, fixed-set CAMP "
                "scoring can remain affine in w and compatible with the "
                "simplex/CVaR/L2 convex master. This audit is not Benders and "
                "makes no trajectory-coordinate convexity claim."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": records_total,
            "with_raw_prefix": len(rows),
            "missing_raw_prefix": records_total - len(rows),
        },
        "summary": {
            key: _finite_summary([row[key] for row in rows])
            for key in SUMMARY_KEYS
        },
        "rates": _rates(rows),
    }


def _row(record: dict[str, Any], label: str) -> dict[str, float]:
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")

    raw = _prefix_xy(
        record.get("candidate_raw_trajectory_prefix"),
        candidate_count,
        label,
        "candidate_raw_trajectory_prefix",
    )
    post = _prefix_xy(
        record.get("candidate_perfect_tracker_postprocessed_reference_prefix"),
        candidate_count,
        label,
        "candidate_perfect_tracker_postprocessed_reference_prefix",
    )
    steps = min(raw.shape[1], post.shape[1])
    if steps < 2:
        raise ValueError(f"{label} comparable prefixes must contain at least 2 steps.")
    raw = raw[:, :steps, :]
    post = post[:, :steps, :]

    raw_endpoint_pairwise = _pairwise_distances(raw[:, -1, :])
    post_endpoint_pairwise = _pairwise_distances(post[:, -1, :])
    raw_prefix_pairwise = _pairwise_prefix_distances(raw)
    post_prefix_pairwise = _pairwise_prefix_distances(post)
    raw_selected_dist = _candidate_distances_to_selected(raw, selected_index)
    post_selected_dist = _candidate_distances_to_selected(post, selected_index)
    raw_to_post = np.linalg.norm(post - raw, axis=2)
    selected_raw_to_post = raw_to_post[selected_index]

    return {
        "prefix_steps": float(steps),
        "raw_endpoint_pairwise_mean_m": _mean_or_zero(raw_endpoint_pairwise),
        "post_endpoint_pairwise_mean_m": _mean_or_zero(post_endpoint_pairwise),
        "endpoint_pairwise_mean_ratio": _ratio(
            _mean_or_zero(post_endpoint_pairwise),
            _mean_or_zero(raw_endpoint_pairwise),
        ),
        "raw_prefix_pairwise_mean_m": _mean_or_zero(raw_prefix_pairwise),
        "post_prefix_pairwise_mean_m": _mean_or_zero(post_prefix_pairwise),
        "prefix_pairwise_mean_ratio": _ratio(
            _mean_or_zero(post_prefix_pairwise),
            _mean_or_zero(raw_prefix_pairwise),
        ),
        "raw_selected_distance_mean_m": _mean_or_zero(raw_selected_dist),
        "post_selected_distance_mean_m": _mean_or_zero(post_selected_dist),
        "selected_distance_mean_ratio": _ratio(
            _mean_or_zero(post_selected_dist),
            _mean_or_zero(raw_selected_dist),
        ),
        "raw_to_post_mean_m": float(np.mean(raw_to_post)),
        "raw_to_post_max_m": float(np.max(raw_to_post)),
        "selected_raw_to_post_mean_m": float(np.mean(selected_raw_to_post)),
        "selected_raw_to_post_max_m": float(np.max(selected_raw_to_post)),
        "raw_post_selected_distance_corr": _corr(raw_selected_dist, post_selected_dist),
    }


def _prefix_xy(values: Any, size: int, label: str, field: str) -> np.ndarray:
    prefix = np.asarray(values, dtype=np.float64)
    if prefix.ndim != 3 or prefix.shape[0] != size or prefix.shape[2] < 2:
        raise ValueError(f"{label} {field} must have shape [K,T,D>=2].")
    if not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} {field} xy values must be finite.")
    return prefix[:, :, :2]


def _pairwise_distances(points: np.ndarray) -> np.ndarray:
    distances: list[float] = []
    for i in range(points.shape[0]):
        for j in range(i + 1, points.shape[0]):
            distances.append(float(np.linalg.norm(points[i] - points[j])))
    return np.asarray(distances, dtype=np.float64)


def _pairwise_prefix_distances(prefix: np.ndarray) -> np.ndarray:
    distances: list[float] = []
    for i in range(prefix.shape[0]):
        for j in range(i + 1, prefix.shape[0]):
            step_distances = np.linalg.norm(prefix[i] - prefix[j], axis=1)
            distances.append(float(np.mean(step_distances)))
    return np.asarray(distances, dtype=np.float64)


def _candidate_distances_to_selected(prefix: np.ndarray, selected_index: int) -> np.ndarray:
    distances: list[float] = []
    selected = prefix[selected_index]
    for index in range(prefix.shape[0]):
        if index == selected_index:
            continue
        distances.append(float(np.mean(np.linalg.norm(prefix[index] - selected, axis=1))))
    return np.asarray(distances, dtype=np.float64)


def _mean_or_zero(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def _ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= TOL:
        return 0.0 if abs(numerator) <= TOL else float("inf")
    return float(numerator / denominator)


def _corr(lhs: np.ndarray, rhs: np.ndarray) -> float:
    if lhs.size < 2 or rhs.size < 2:
        return float("nan")
    if float(np.std(lhs)) <= TOL or float(np.std(rhs)) <= TOL:
        return float("nan")
    return float(np.corrcoef(lhs, rhs)[0, 1])


def _finite_summary(values: list[float]) -> dict[str, float | int | None]:
    finite = np.asarray(
        [value for value in values if np.isfinite(value)],
        dtype=np.float64,
    )
    if finite.size == 0:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "p95": None,
            "min": None,
            "max": None,
        }
    return {
        "count": int(finite.size),
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "p95": float(np.percentile(finite, 95)),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
    }


def _rates(rows: list[dict[str, float]]) -> dict[str, float | int]:
    total = len(rows)
    rates: dict[str, float | int] = {"records": total}
    if total == 0:
        for threshold in THRESHOLDS_M:
            label = _threshold_label(threshold)
            rates[f"endpoint_raw_ge_{label}_post_lt_{label}"] = 0.0
            rates[f"prefix_raw_ge_{label}_post_lt_{label}"] = 0.0
        return rates
    for threshold in THRESHOLDS_M:
        label = _threshold_label(threshold)
        rates[f"endpoint_raw_ge_{label}_post_lt_{label}"] = _rate(
            rows,
            lambda row, threshold=threshold: (
                row["raw_endpoint_pairwise_mean_m"] >= threshold
                and row["post_endpoint_pairwise_mean_m"] < threshold
            ),
        )
        rates[f"prefix_raw_ge_{label}_post_lt_{label}"] = _rate(
            rows,
            lambda row, threshold=threshold: (
                row["raw_prefix_pairwise_mean_m"] >= threshold
                and row["post_prefix_pairwise_mean_m"] < threshold
            ),
        )
    rates["endpoint_pairwise_mean_compression_rate"] = _rate(
        rows,
        lambda row: row["endpoint_pairwise_mean_ratio"] < 1.0,
    )
    rates["prefix_pairwise_mean_compression_rate"] = _rate(
        rows,
        lambda row: row["prefix_pairwise_mean_ratio"] < 1.0,
    )
    return rates


def _rate(rows: list[dict[str, float]], predicate) -> float:
    if not rows:
        return 0.0
    return float(sum(1 for row in rows if predicate(row)) / len(rows))


def _threshold_label(value: float) -> str:
    return str(value).replace(".", "p")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Raw Prefix Geometry Audit",
        "",
        f"Label: `{report['analysis']['label']}`",
        "",
        "## Scope",
        "",
        f"- Logs: {report['records']['logs']}",
        f"- Records: {report['records']['total']}",
        "- Training: false",
        "- Online selector change: false",
        "- Uses outcome labels: false",
        "",
        "## Geometry Summary",
        "",
        "| Metric | Mean | Median | P95 | Min | Max |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key in SUMMARY_KEYS:
        summary = report["summary"][key]
        lines.append(
            "| "
            + key
            + " | "
            + " | ".join(_fmt(summary[field]) for field in ("mean", "median", "p95", "min", "max"))
            + " |"
        )
    lines.extend(
        [
            "",
            "## Rates",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["rates"].items():
        lines.append(f"| {key} | {_fmt(value)} |")
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


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not np.isfinite(value):
            return "n/a"
        return f"{value:.6f}"
    return str(value)


if __name__ == "__main__":
    main()
