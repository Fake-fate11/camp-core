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
HORIZONS = (3, 5, 10)
TOL = 1e-12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline oracle-potential audit for a first-step-preserving "
            "reference graft. Uses outcome labels only to choose diagnostic "
            "donors; it does not define an online selector."
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
    rows: list[dict[str, float]] = []
    no_donor = 0
    for record in nonfallback:
        donor_mask = _safety_joint_comfort_mask(record)
        if not donor_mask.any():
            no_donor += 1
            continue
        donor = _min_deficit_candidate(record, donor_mask)
        rows.append(_graft_row(record, donor))

    return {
        "analysis": {
            "name": "dp_camp_first_step_graft_potential_v1",
            "role": "offline cheap-proof screen for first-step-preserving candidate construction",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate outcomes choose oracle donors for diagnosis only; "
                "the audited graft formula itself uses current-tick reference "
                "prefixes"
            ),
            "graft_definition": (
                "for selected anchor s and donor d, g_t = p_s0 + p_dt - p_d0 "
                "over the stored postprocessed reference prefix; this preserves "
                "the selected first reference xy exactly"
            ),
            "not_repeated_routes": (
                "not prefix-blend because it does not interpolate toward "
                "candidate 0; not a step-reach guard because it constructs a "
                "new reference prefix instead of filtering candidates"
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": len(nonfallback),
            "fallback": len(records) - len(nonfallback),
            "with_oracle_donor": len(rows),
            "without_oracle_donor": no_donor,
        },
        "rates": _rates(rows),
        "summary": {key: _summary([row[key] for row in rows]) for key in _row_keys()},
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
    if prefix.ndim != 3 or prefix.shape[0] != candidate_count or prefix.shape[2] < 2:
        raise ValueError(
            f"{label} candidate_perfect_tracker_postprocessed_reference_prefix "
            "must have shape [K,T,D>=2]."
        )
    if prefix.shape[1] < max(HORIZONS):
        raise ValueError(f"{label} reference prefix is shorter than H{max(HORIZONS)}.")
    if not np.all(np.isfinite(prefix[:, :, :2])):
        raise ValueError(f"{label} reference prefix xy values must be finite.")
    return {
        "selected_index": selected_index,
        "feasible": _bool_vector(
            record.get("feasible_mask"), candidate_count, f"{label} feasible_mask"
        ),
        "outcomes": _outcomes(record.get("candidate_closed_loop_outcomes"), candidate_count, label),
        "prefix_xy": prefix[:, :, :2],
    }


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


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


def _min_deficit_candidate(record: dict[str, Any], mask: np.ndarray) -> int:
    selected = record["selected_index"]
    indices = np.flatnonzero(mask)
    selected_progress = _outcome_float(record, selected, "progress_m")
    deficits = np.asarray(
        [
            max(0.0, selected_progress - _outcome_float(record, int(idx), "progress_m"))
            for idx in indices
        ],
        dtype=np.float64,
    )
    jerk = np.asarray(
        [_outcome_float(record, int(idx), "mean_jerk_mps3") for idx in indices],
        dtype=np.float64,
    )
    lateral = np.asarray(
        [
            _outcome_float(record, int(idx), "mean_lateral_acceleration_mps2")
            for idx in indices
        ],
        dtype=np.float64,
    )
    order = np.lexsort((indices, lateral, jerk, deficits))
    return int(indices[order[0]])


def _graft_row(record: dict[str, Any], donor: int) -> dict[str, float]:
    selected = record["selected_index"]
    prefix = record["prefix_xy"]
    selected_prefix = prefix[selected]
    donor_prefix = prefix[donor]
    graft_prefix = selected_prefix[0] + donor_prefix - donor_prefix[0]
    selected_progress = _outcome_float(record, selected, "progress_m")
    donor_progress = _outcome_float(record, donor, "progress_m")
    row = {
        "outcome_progress_deficit_m": max(0.0, selected_progress - donor_progress),
        "outcome_jerk_delta_mps3": _outcome_float(record, donor, "mean_jerk_mps3")
        - _outcome_float(record, selected, "mean_jerk_mps3"),
        "outcome_lateral_delta_mps2": _outcome_float(
            record,
            donor,
            "mean_lateral_acceleration_mps2",
        )
        - _outcome_float(record, selected, "mean_lateral_acceleration_mps2"),
        "first_step_reach_delta_m": float(
            np.linalg.norm(graft_prefix[0]) - np.linalg.norm(selected_prefix[0])
        ),
        "donor_first_step_reach_delta_m": float(
            np.linalg.norm(donor_prefix[0]) - np.linalg.norm(selected_prefix[0])
        ),
        "prefix_jerk_proxy_delta": _mean_third_difference_norm(graft_prefix)
        - _mean_third_difference_norm(selected_prefix),
        "donor_prefix_jerk_proxy_delta": _mean_third_difference_norm(donor_prefix)
        - _mean_third_difference_norm(selected_prefix),
    }
    for horizon in HORIZONS:
        row[f"graft_h{horizon}_displacement_delta_m"] = float(
            np.linalg.norm(graft_prefix[horizon - 1])
            - np.linalg.norm(selected_prefix[horizon - 1])
        )
        row[f"donor_h{horizon}_displacement_delta_m"] = float(
            np.linalg.norm(donor_prefix[horizon - 1])
            - np.linalg.norm(selected_prefix[horizon - 1])
        )
        row[f"graft_h{horizon}_path_delta_m"] = (
            _path_length(graft_prefix[:horizon])
            - _path_length(selected_prefix[:horizon])
        )
        row[f"donor_h{horizon}_path_delta_m"] = (
            _path_length(donor_prefix[:horizon])
            - _path_length(selected_prefix[:horizon])
        )
    return row


def _path_length(points: np.ndarray) -> float:
    if points.shape[0] == 0:
        return 0.0
    origin = np.zeros((1, 2), dtype=np.float64)
    stacked = np.vstack([origin, points])
    return float(np.linalg.norm(np.diff(stacked, axis=0), axis=1).sum())


def _mean_third_difference_norm(points: np.ndarray) -> float:
    if points.shape[0] < 4:
        return 0.0
    return float(np.linalg.norm(np.diff(points, n=3, axis=0), axis=1).mean())


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


def _row_keys() -> tuple[str, ...]:
    keys = [
        "outcome_progress_deficit_m",
        "outcome_jerk_delta_mps3",
        "outcome_lateral_delta_mps2",
        "first_step_reach_delta_m",
        "donor_first_step_reach_delta_m",
        "prefix_jerk_proxy_delta",
        "donor_prefix_jerk_proxy_delta",
    ]
    for horizon in HORIZONS:
        keys.extend(
            [
                f"graft_h{horizon}_displacement_delta_m",
                f"donor_h{horizon}_displacement_delta_m",
                f"graft_h{horizon}_path_delta_m",
                f"donor_h{horizon}_path_delta_m",
            ]
        )
    return tuple(keys)


def _rates(rows: list[dict[str, float]]) -> dict[str, float | int]:
    denom = max(len(rows), 1)
    if not rows:
        return {
            "records": 0,
            "first_step_exact_preservation_rate": 0.0,
            "donor_lower_first_step_rate": 0.0,
            "graft_h3_displacement_nonloss_rate": 0.0,
            "graft_h5_displacement_nonloss_rate": 0.0,
            "graft_h10_displacement_nonloss_rate": 0.0,
            "graft_prefix_jerk_proxy_improvement_rate": 0.0,
        }
    return {
        "records": len(rows),
        "first_step_exact_preservation_rate": sum(
            abs(row["first_step_reach_delta_m"]) <= TOL for row in rows
        )
        / denom,
        "donor_lower_first_step_rate": sum(
            row["donor_first_step_reach_delta_m"] < -TOL for row in rows
        )
        / denom,
        "graft_h3_displacement_nonloss_rate": sum(
            row["graft_h3_displacement_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "graft_h5_displacement_nonloss_rate": sum(
            row["graft_h5_displacement_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "graft_h10_displacement_nonloss_rate": sum(
            row["graft_h10_displacement_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "graft_prefix_jerk_proxy_improvement_rate": sum(
            row["prefix_jerk_proxy_delta"] < -TOL for row in rows
        )
        / denom,
    }


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "p50": None,
            "p90": None,
            "p95": None,
        }
    arr = np.asarray(values, dtype=np.float64)
    return {
        "count": int(arr.size),
        "mean": float(np.mean(arr)),
        "p50": float(np.percentile(arr, 50.0)),
        "p90": float(np.percentile(arr, 90.0)),
        "p95": float(np.percentile(arr, 95.0)),
    }


def _fmt(value: float | int | None) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    rates = report["rates"]
    lines = [
        "# DP CAMP First-Step Graft Potential",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- With oracle donors: {records['with_oracle_donor']}",
        "",
        "The audited graft translates the donor postprocessed reference prefix "
        "onto the selected candidate's first reference point. Outcome labels "
        "choose donors for this diagnostic only; no online selector is changed.",
        "",
        f"- First-step exact preservation rate: "
        f"`{rates['first_step_exact_preservation_rate']:.6f}`",
        f"- Donor lower first-step rate before graft: "
        f"`{rates['donor_lower_first_step_rate']:.6f}`",
        f"- Graft H3/H5/H10 displacement nonloss rates: "
        f"`{rates['graft_h3_displacement_nonloss_rate']:.6f}` / "
        f"`{rates['graft_h5_displacement_nonloss_rate']:.6f}` / "
        f"`{rates['graft_h10_displacement_nonloss_rate']:.6f}`",
        f"- Graft prefix jerk-proxy improvement rate: "
        f"`{rates['graft_prefix_jerk_proxy_improvement_rate']:.6f}`",
        "",
        "| Quantity | Mean | P50 | P90 | P95 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label_text, key in (
        ("Outcome progress deficit m", "outcome_progress_deficit_m"),
        ("Outcome jerk delta m/s^3", "outcome_jerk_delta_mps3"),
        ("Outcome lateral delta m/s^2", "outcome_lateral_delta_mps2"),
        ("First-step reach delta after graft m", "first_step_reach_delta_m"),
        ("Donor first-step reach delta before graft m", "donor_first_step_reach_delta_m"),
        ("Graft H3 displacement delta m", "graft_h3_displacement_delta_m"),
        ("Graft H5 displacement delta m", "graft_h5_displacement_delta_m"),
        ("Graft H10 displacement delta m", "graft_h10_displacement_delta_m"),
        ("Graft H3 path delta m", "graft_h3_path_delta_m"),
        ("Graft H5 path delta m", "graft_h5_path_delta_m"),
        ("Graft H10 path delta m", "graft_h10_path_delta_m"),
        ("Graft prefix jerk-proxy delta", "prefix_jerk_proxy_delta"),
        ("Donor prefix jerk-proxy delta", "donor_prefix_jerk_proxy_delta"),
    ):
        lines.append(_summary_row(label_text, report["summary"][key]))
    lines.append("")
    return "\n".join(lines)


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p50'])} | "
        f"{_fmt(values['p90'])} | {_fmt(values['p95'])} |"
    )


if __name__ == "__main__":
    main()
