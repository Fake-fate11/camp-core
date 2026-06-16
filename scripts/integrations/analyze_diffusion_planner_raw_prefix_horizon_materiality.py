#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
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


RAW_METRICS = (
    "raw_endpoint_pairwise_mean_m",
    "raw_prefix_pairwise_mean_m",
    "raw_selected_distance_mean_m",
)
STATE_VALUE_KEYS = (
    "selected_union_red",
    "selected_full_red",
    "selected_progress_shortfall_atom",
    "selected_lateral_atom",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Raw-only multi-horizon materiality audit for logged DP candidate "
            "prefixes. This is an offline diagnostic over fixed finite "
            "candidate constants."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument(
        "--horizons",
        type=_parse_horizons,
        default=(10, 30, 80),
        help="Comma-separated positive horizon steps, default 10,30,80.",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        [*args.root, *args.selection_log],
        horizons=tuple(args.horizons),
        label=args.label,
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
    horizons: tuple[int, ...] = (10, 30, 80),
    label: str | None = None,
) -> dict[str, Any]:
    horizons = tuple(sorted(set(int(horizon) for horizon in horizons)))
    if not horizons or any(horizon <= 0 for horizon in horizons):
        raise ValueError("horizons must contain positive integers.")
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    records_total = 0
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        path_state = _path_state(log_path)
        for record_index, record in enumerate(payload):
            records_total += 1
            label_for_error = f"{log_path} record {record_index}"
            row = _row(record, path_state, horizons, label_for_error)
            rows.append(row)
            for group in _groups(row):
                groups[group].append(row)

    return {
        "analysis": {
            "name": "dp_camp_raw_prefix_horizon_materiality_v1",
            "role": (
                "offline raw-only multi-horizon materiality audit of logged "
                "Diffusion Planner candidate prefixes"
            ),
            "label": label,
            "horizons": list(horizons),
            "training": False,
            "online_selector_change": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "convexity_boundary": (
                "All quantities are fixed finite-candidate constants at the "
                "current tick. This audit does not define Benders cuts and "
                "does not claim trajectory-coordinate convexity."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": records_total,
        },
        "summary": _summarize_rows(rows, horizons),
        "groups": {
            name: _summarize_rows(group_rows, horizons)
            for name, group_rows in sorted(groups.items())
        },
    }


def _row(
    record: dict[str, Any],
    path_state: dict[str, str],
    horizons: tuple[int, ...],
    label: str,
) -> dict[str, Any]:
    raw = _raw_prefix(record, label)
    candidate_count = raw.shape[0]
    logged_steps = raw.shape[1]
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= candidate_count:
        raise ValueError(f"{label} selected_index is out of range.")
    if max(horizons) > logged_steps:
        raise ValueError(
            f"{label} requested horizon {max(horizons)} exceeds logged "
            f"raw prefix length {logged_steps}."
        )

    feasible_mask = record.get("feasible_mask") or []
    feasible_count = int(sum(1 for value in feasible_mask if bool(value)))
    selected_feasible = (
        bool(feasible_mask[selected_index])
        if 0 <= selected_index < len(feasible_mask)
        else False
    )
    row: dict[str, Any] = {
        "logged_steps": logged_steps,
        "traffic_lights": path_state.get("traffic_lights", "unknown"),
        "npc": path_state.get("npc", "unknown"),
        "used_fallback": str(bool(record.get("used_fallback", False))).lower(),
        "selected_index": str(selected_index),
        "selected_index_bucket": "candidate0"
        if selected_index == 0
        else "nonzero",
        "selected_feasible": str(selected_feasible).lower(),
        "feasible_bucket": _feasible_bucket(feasible_count, candidate_count),
        "any_union_red": str(
            _max_value(record, "candidate_horizon_union_planned_red_light_cost")
            > 0.0
        ).lower(),
        "selected_union_red_positive": str(
            _selected_value(
                record,
                "candidate_horizon_union_planned_red_light_cost",
                selected_index,
            )
            > 0.0
        ).lower(),
        "any_full_red": str(
            _max_value(record, "candidate_full_horizon_planned_red_light_cost")
            > 0.0
        ).lower(),
        "selected_full_red_positive": str(
            _selected_value(
                record,
                "candidate_full_horizon_planned_red_light_cost",
                selected_index,
            )
            > 0.0
        ).lower(),
        "selected_progress_shortfall_positive": str(
            _selected_atom(record, selected_index, "progress_shortfall") > 0.0
        ).lower(),
        "selected_lateral_atom_positive": str(
            _selected_atom(record, selected_index, "planned_lateral_acceleration_cost")
            > 0.0
        ).lower(),
        "state_values": {
            "selected_union_red": _selected_value(
                record,
                "candidate_horizon_union_planned_red_light_cost",
                selected_index,
            ),
            "selected_full_red": _selected_value(
                record,
                "candidate_full_horizon_planned_red_light_cost",
                selected_index,
            ),
            "selected_progress_shortfall_atom": _selected_atom(
                record,
                selected_index,
                "progress_shortfall",
            ),
            "selected_lateral_atom": _selected_atom(
                record,
                selected_index,
                "planned_lateral_acceleration_cost",
            ),
        },
        "horizons": {},
    }
    for horizon in horizons:
        prefix = raw[:, :horizon, :]
        endpoint_pairwise = _pairwise_distances(prefix[:, -1, :])
        prefix_pairwise = _pairwise_prefix_distances(prefix)
        selected_distance = _candidate_distances_to_selected(prefix, selected_index)
        row["horizons"][f"h{horizon}"] = {
            "raw_endpoint_pairwise_mean_m": _mean_or_zero(endpoint_pairwise),
            "raw_prefix_pairwise_mean_m": _mean_or_zero(prefix_pairwise),
            "raw_selected_distance_mean_m": _mean_or_zero(selected_distance),
        }
    return row


def _raw_prefix(record: dict[str, Any], label: str) -> np.ndarray:
    prefix = np.asarray(record.get("candidate_raw_trajectory_prefix"), dtype=np.float64)
    candidate_count = int(record.get("num_candidates", 0))
    if candidate_count <= 0:
        raise ValueError(f"{label} must declare positive num_candidates.")
    if prefix.ndim != 3 or prefix.shape[0] != candidate_count or prefix.shape[2] < 2:
        raise ValueError(f"{label} candidate_raw_trajectory_prefix must be [K,T,D>=2].")
    if not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} raw prefix xy values must be finite.")
    return prefix[:, :, :2]


def _groups(row: dict[str, Any]) -> list[str]:
    return [
        "all",
        f"traffic_lights={row['traffic_lights']}",
        f"npc={row['npc']}",
        f"fallback={row['used_fallback']}",
        f"selected_index_bucket={row['selected_index_bucket']}",
        f"selected_index={row['selected_index']}",
        f"selected_feasible={row['selected_feasible']}",
        f"feasible_bucket={row['feasible_bucket']}",
        f"any_union_red={row['any_union_red']}",
        f"selected_union_red_positive={row['selected_union_red_positive']}",
        f"any_full_red={row['any_full_red']}",
        f"selected_full_red_positive={row['selected_full_red_positive']}",
        (
            "selected_progress_shortfall_positive="
            f"{row['selected_progress_shortfall_positive']}"
        ),
        f"selected_lateral_atom_positive={row['selected_lateral_atom_positive']}",
    ]


def _summarize_rows(rows: list[dict[str, Any]], horizons: tuple[int, ...]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "logged_steps": _finite_summary([float(row["logged_steps"]) for row in rows]),
        "state_values": {
            key: _finite_summary([float(row["state_values"][key]) for row in rows])
            for key in STATE_VALUE_KEYS
        },
        "horizons": {
            f"h{horizon}": {
                metric: _finite_summary(
                    [
                        float(row["horizons"][f"h{horizon}"][metric])
                        for row in rows
                    ]
                )
                for metric in RAW_METRICS
            }
            for horizon in horizons
        },
    }


def _path_state(path: Path) -> dict[str, str]:
    parts = set(path.parts)
    traffic_lights = "unknown"
    if "tl_on" in parts:
        traffic_lights = "on"
    elif "tl_off" in parts:
        traffic_lights = "off"
    npc = "unknown"
    for part in path.parts:
        if part.startswith("npc_"):
            npc = part.removeprefix("npc_")
            break
    return {"traffic_lights": traffic_lights, "npc": npc}


def _feasible_bucket(feasible_count: int, candidate_count: int) -> str:
    if feasible_count <= 0:
        return "none"
    if feasible_count >= candidate_count:
        return "all"
    return "partial"


def _selected_value(record: dict[str, Any], field: str, selected_index: int) -> float:
    values = record.get(field)
    if not isinstance(values, list) or not (0 <= selected_index < len(values)):
        return 0.0
    value = values[selected_index]
    return float(value) if value is not None and np.isfinite(value) else 0.0


def _max_value(record: dict[str, Any], field: str) -> float:
    values = record.get(field)
    if not isinstance(values, list) or not values:
        return 0.0
    finite = [float(value) for value in values if value is not None and np.isfinite(value)]
    return max(finite) if finite else 0.0


def _selected_atom(record: dict[str, Any], selected_index: int, atom_name: str) -> float:
    names = record.get("atom_names") or []
    atoms = record.get("atoms") or []
    if atom_name not in names or not (0 <= selected_index < len(atoms)):
        return 0.0
    atom_index = int(names.index(atom_name))
    selected_atoms = atoms[selected_index]
    if not isinstance(selected_atoms, list) or atom_index >= len(selected_atoms):
        return 0.0
    value = selected_atoms[atom_index]
    return float(value) if value is not None and np.isfinite(value) else 0.0


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


def render_markdown(report: dict[str, Any]) -> str:
    horizons = [int(value) for value in report["analysis"]["horizons"]]
    lines = [
        "# Raw Prefix Horizon Materiality Audit",
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
        "## Overall Horizon Summary",
        "",
        "| Horizon | Raw Endpoint Mean | Raw Endpoint P95 | Raw Prefix Mean | Raw Prefix P95 | Selected Distance Mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for horizon in horizons:
        horizon_summary = report["summary"]["horizons"][f"h{horizon}"]
        lines.append(
            f"| h{horizon} | "
            f"{_fmt(horizon_summary['raw_endpoint_pairwise_mean_m']['mean'])} | "
            f"{_fmt(horizon_summary['raw_endpoint_pairwise_mean_m']['p95'])} | "
            f"{_fmt(horizon_summary['raw_prefix_pairwise_mean_m']['mean'])} | "
            f"{_fmt(horizon_summary['raw_prefix_pairwise_mean_m']['p95'])} | "
            f"{_fmt(horizon_summary['raw_selected_distance_mean_m']['mean'])} |"
        )

    lines.extend(
        [
            "",
            "## Group Summary At Longest Horizon",
            "",
            "| Group | Count | Raw Endpoint Mean | Raw Prefix Mean | Selected Union Red Mean | Progress Atom Mean |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    longest = max(horizons)
    groups = sorted(
        report["groups"].items(),
        key=lambda item: (-int(item[1]["count"]), item[0]),
    )
    for name, summary in groups:
        horizon_summary = summary["horizons"][f"h{longest}"]
        values = summary["state_values"]
        lines.append(
            "| "
            + name
            + " | "
            + str(summary["count"])
            + " | "
            + _fmt(horizon_summary["raw_endpoint_pairwise_mean_m"]["mean"])
            + " | "
            + _fmt(horizon_summary["raw_prefix_pairwise_mean_m"]["mean"])
            + " | "
            + _fmt(values["selected_union_red"]["mean"])
            + " | "
            + _fmt(values["selected_progress_shortfall_atom"]["mean"])
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


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            return str(value)
        return f"{float(value):.6g}"
    return str(value)


def _parse_horizons(value: str) -> tuple[int, ...]:
    horizons = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not horizons:
        raise argparse.ArgumentTypeError("horizons must not be empty.")
    if any(horizon <= 0 for horizon in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive.")
    return horizons


if __name__ == "__main__":
    main()
