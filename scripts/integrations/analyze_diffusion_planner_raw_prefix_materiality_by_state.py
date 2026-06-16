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
from scripts.integrations.analyze_diffusion_planner_raw_prefix_geometry import (  # noqa: E402
    _row as geometry_row,
)


GEOMETRY_KEYS = (
    "raw_endpoint_pairwise_mean_m",
    "post_endpoint_pairwise_mean_m",
    "endpoint_pairwise_mean_delta_m",
    "raw_prefix_pairwise_mean_m",
    "post_prefix_pairwise_mean_m",
    "prefix_pairwise_mean_delta_m",
    "raw_to_post_mean_m",
    "raw_to_post_max_m",
)
STATE_VALUE_KEYS = (
    "selected_union_red",
    "selected_full_red",
    "selected_red_stopping_margin",
    "selected_progress_shortfall_atom",
    "selected_lateral_atom",
    "selected_dp_prior_jerk_excess_atom",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "State-conditioned raw-prefix materiality audit for fixed DP+CAMP "
            "selection logs. This is an offline diagnostic over logged finite "
            "candidate constants."
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

    groups: dict[str, list[dict[str, float]]] = defaultdict(list)
    records_total = 0
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        path_state = _path_state(log_path)
        for record_index, record in enumerate(payload):
            records_total += 1
            label_for_error = f"{log_path} record {record_index}"
            row = _materiality_row(record, path_state, label_for_error)
            for group in _groups(row):
                groups[group].append(row)

    return {
        "analysis": {
            "name": "dp_camp_raw_prefix_materiality_by_state_v1",
            "role": (
                "offline state-conditioned audit of raw and postprocessed "
                "candidate-prefix geometry"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "uses_outcome_labels": False,
            "future_outcome_leakage": False,
            "convexity_boundary": (
                "All grouped values are fixed finite-candidate constants at "
                "the current selection tick. This report is diagnostic only; "
                "it is not Benders and introduces no online selector rule."
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": records_total,
        },
        "groups": {
            name: _summarize_rows(rows)
            for name, rows in sorted(groups.items())
        },
    }


def _materiality_row(
    record: dict[str, Any],
    path_state: dict[str, str],
    label: str,
) -> dict[str, float | str]:
    geometry = geometry_row(record, label)
    selected_index = int(record.get("selected_index"))
    feasible_mask = record.get("feasible_mask") or []
    feasible_count = int(sum(1 for value in feasible_mask if bool(value)))
    selected_feasible = (
        bool(feasible_mask[selected_index])
        if 0 <= selected_index < len(feasible_mask)
        else False
    )

    row: dict[str, float | str] = {
        key: float(geometry[key])
        for key in GEOMETRY_KEYS
    }
    row.update(
        {
            "traffic_lights": path_state.get("traffic_lights", "unknown"),
            "npc": path_state.get("npc", "unknown"),
            "used_fallback": str(bool(record.get("used_fallback", False))).lower(),
            "selected_index": str(selected_index),
            "selected_index_bucket": "candidate0"
            if selected_index == 0
            else "nonzero",
            "selected_feasible": str(selected_feasible).lower(),
            "feasible_bucket": _feasible_bucket(feasible_count, int(record.get("num_candidates", 0))),
            "any_union_red": str(
                _max_value(record, "candidate_horizon_union_planned_red_light_cost") > 0.0
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
                _max_value(record, "candidate_full_horizon_planned_red_light_cost") > 0.0
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
                _selected_atom(
                    record,
                    selected_index,
                    "planned_lateral_acceleration_cost",
                )
                > 0.0
            ).lower(),
            "selected_dp_prior_jerk_excess_positive": str(
                _selected_atom(record, selected_index, "dp_prior_jerk_excess_cost") > 0.0
            ).lower(),
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
            "selected_red_stopping_margin": _selected_value(
                record,
                "candidate_red_stopping_margin_cost",
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
            "selected_dp_prior_jerk_excess_atom": _selected_atom(
                record,
                selected_index,
                "dp_prior_jerk_excess_cost",
            ),
        }
    )
    return row


def _groups(row: dict[str, float | str]) -> list[str]:
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
        (
            "selected_dp_prior_jerk_excess_positive="
            f"{row['selected_dp_prior_jerk_excess_positive']}"
        ),
    ]


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


def _summarize_rows(rows: list[dict[str, float | str]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "geometry": {
            key: _finite_summary([float(row[key]) for row in rows])
            for key in GEOMETRY_KEYS
        },
        "state_values": {
            key: _finite_summary([float(row[key]) for row in rows])
            for key in STATE_VALUE_KEYS
        },
    }


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
    lines = [
        "# Raw Prefix Materiality By State",
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
        "## Group Summary",
        "",
        "| Group | Count | Raw Endpoint Mean | Endpoint Delta Mean | Raw Prefix Mean | Prefix Delta Mean | Selected Union Red Mean | Selected Progress Atom Mean |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    groups = sorted(
        report["groups"].items(),
        key=lambda item: (-int(item[1]["count"]), item[0]),
    )
    for name, summary in groups:
        geometry = summary["geometry"]
        values = summary["state_values"]
        lines.append(
            "| "
            + name
            + " | "
            + str(summary["count"])
            + " | "
            + _fmt(geometry["raw_endpoint_pairwise_mean_m"]["mean"])
            + " | "
            + _fmt(geometry["endpoint_pairwise_mean_delta_m"]["mean"])
            + " | "
            + _fmt(geometry["raw_prefix_pairwise_mean_m"]["mean"])
            + " | "
            + _fmt(geometry["prefix_pairwise_mean_delta_m"]["mean"])
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


if __name__ == "__main__":
    main()
