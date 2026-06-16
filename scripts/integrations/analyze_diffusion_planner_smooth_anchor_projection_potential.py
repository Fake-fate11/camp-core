#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
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
    HORIZONS,
    TOL,
    _fmt,
    _load_record,
    _mean_third_difference_norm,
    _min_deficit_candidate,
    _outcome_float,
    _path_length,
    _safety_joint_comfort_mask,
    _summary,
)


ANCHOR_HORIZONS = (1, 3, 5, 10)
ANCHOR_INDICES = tuple(horizon - 1 for horizon in ANCHOR_HORIZONS)
DEFAULT_RIDGE_VALUES = (0.0, 1e-4, 1e-3, 1e-2, 1e-1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline oracle-potential audit for an H1/H3/H5/H10 anchored "
            "smooth least-squares projection. Outcome labels choose diagnostic "
            "donors only; the projection uses current-tick prefixes."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument(
        "--ridge",
        type=float,
        action="append",
        default=[],
        help=(
            "Nonnegative selected-prefix ridge weight. May be repeated. "
            "Defaults to a fixed diagnostic grid."
        ),
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ridge_values = tuple(args.ridge) if args.ridge else DEFAULT_RIDGE_VALUES
    report = analyze([*args.root, *args.selection_log], label=args.label, ridge_values=ridge_values)
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
    ridge_values: tuple[float, ...] = DEFAULT_RIDGE_VALUES,
) -> dict[str, Any]:
    if not ridge_values:
        raise ValueError("At least one ridge value is required.")
    for ridge in ridge_values:
        if not math.isfinite(ridge) or ridge < 0.0:
            raise ValueError("Ridge values must be finite and nonnegative.")

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
    rows_by_ridge: dict[float, list[dict[str, float]]] = {ridge: [] for ridge in ridge_values}
    no_donor = 0
    for record in nonfallback:
        donor_mask = _safety_joint_comfort_mask(record)
        if not donor_mask.any():
            no_donor += 1
            continue
        donor = _min_deficit_candidate(record, donor_mask)
        for ridge in ridge_values:
            rows_by_ridge[ridge].append(_projection_row(record, donor, ridge))

    return {
        "analysis": {
            "name": "dp_camp_smooth_anchor_projection_potential_v1",
            "role": (
                "offline cheap-proof screen for H1/H3/H5/H10 "
                "progress-anchor-preserving smooth candidate construction"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate outcomes choose oracle donors for diagnosis only; "
                "the audited projection uses current-tick reference prefixes"
            ),
            "anchor_horizons": ANCHOR_HORIZONS,
            "ridge_values": tuple(float(value) for value in ridge_values),
            "projection_definition": (
                "minimize ||D3 G - D3 D||_2^2 + rho ||G - S||_2^2 subject "
                "to G_A = S_A for A={H1,H3,H5,H10}; solved independently "
                "for x and y by equality-constrained least squares"
            ),
            "convexity_boundary": (
                "for fixed selected/donor prefixes and rho>=0 this is a convex "
                "quadratic least-squares projection; it is not Benders and "
                "does not imply global convexity over trajectory coordinates"
            ),
            "diagnostic_gate": (
                "candidate-worthy only if anchors are preserved exactly and "
                "the prefix jerk proxy has negative mean delta with a useful "
                "improvement rate; deviation metrics are reported for later "
                "engineering constraints"
            ),
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": len(nonfallback),
            "fallback": len(records) - len(nonfallback),
            "with_oracle_donor": max((len(rows) for rows in rows_by_ridge.values()), default=0),
            "without_oracle_donor": no_donor,
        },
        "ridge_reports": [
            {
                "ridge": float(ridge),
                "rates": _rates(rows_by_ridge[ridge]),
                "summary": {
                    key: _summary([row[key] for row in rows_by_ridge[ridge]])
                    for key in _row_keys()
                },
            }
            for ridge in ridge_values
        ],
    }


def _projection_row(record: dict[str, Any], donor: int, ridge: float) -> dict[str, float]:
    selected = record["selected_index"]
    prefix = record["prefix_xy"][:, : max(HORIZONS)]
    selected_prefix = prefix[selected]
    donor_prefix = prefix[donor]
    projected_prefix = _smooth_anchor_projection(selected_prefix, donor_prefix, ridge)
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
        "max_anchor_xy_error_m": _max_anchor_error(selected_prefix, projected_prefix),
        "max_xy_deviation_from_selected_m": float(
            np.linalg.norm(projected_prefix - selected_prefix, axis=1).max()
        ),
        "mean_xy_deviation_from_selected_m": float(
            np.linalg.norm(projected_prefix - selected_prefix, axis=1).mean()
        ),
        "first_step_reach_delta_m": float(
            np.linalg.norm(projected_prefix[0]) - np.linalg.norm(selected_prefix[0])
        ),
        "donor_first_step_reach_delta_m": float(
            np.linalg.norm(donor_prefix[0]) - np.linalg.norm(selected_prefix[0])
        ),
        "prefix_jerk_proxy_delta": _mean_third_difference_norm(projected_prefix)
        - _mean_third_difference_norm(selected_prefix),
        "donor_prefix_jerk_proxy_delta": _mean_third_difference_norm(donor_prefix)
        - _mean_third_difference_norm(selected_prefix),
        "third_difference_target_error": _third_difference_target_error(
            projected_prefix,
            donor_prefix,
        ),
    }
    for horizon in HORIZONS:
        row[f"projection_h{horizon}_displacement_delta_m"] = float(
            np.linalg.norm(projected_prefix[horizon - 1])
            - np.linalg.norm(selected_prefix[horizon - 1])
        )
        row[f"donor_h{horizon}_displacement_delta_m"] = float(
            np.linalg.norm(donor_prefix[horizon - 1])
            - np.linalg.norm(selected_prefix[horizon - 1])
        )
        row[f"projection_h{horizon}_path_delta_m"] = (
            _path_length(projected_prefix[:horizon])
            - _path_length(selected_prefix[:horizon])
        )
        row[f"donor_h{horizon}_path_delta_m"] = (
            _path_length(donor_prefix[:horizon])
            - _path_length(selected_prefix[:horizon])
        )
    return row


def _smooth_anchor_projection(
    selected_prefix: np.ndarray,
    donor_prefix: np.ndarray,
    ridge: float,
) -> np.ndarray:
    if selected_prefix.shape != donor_prefix.shape:
        raise ValueError("Selected and donor prefixes must have the same shape.")
    length, dims = selected_prefix.shape
    if length < max(HORIZONS) or dims < 2:
        raise ValueError("Prefixes must contain at least H10 xy coordinates.")

    free_indices = np.asarray(
        [idx for idx in range(length) if idx not in ANCHOR_INDICES],
        dtype=np.int64,
    )
    fixed_indices = np.asarray(ANCHOR_INDICES, dtype=np.int64)
    d3 = _third_difference_matrix(length)
    d3_free = d3[:, free_indices]
    d3_fixed = d3[:, fixed_indices]
    projected = selected_prefix.copy()

    for dim in range(dims):
        fixed_values = selected_prefix[fixed_indices, dim]
        target = d3 @ donor_prefix[:, dim] - d3_fixed @ fixed_values
        matrices = [d3_free]
        rhs = [target]
        if ridge > 0.0:
            sqrt_ridge = math.sqrt(ridge)
            matrices.append(sqrt_ridge * np.eye(len(free_indices), dtype=np.float64))
            rhs.append(sqrt_ridge * selected_prefix[free_indices, dim])
        design = np.vstack(matrices)
        response = np.concatenate(rhs)
        solution, *_ = np.linalg.lstsq(design, response, rcond=None)
        projected[free_indices, dim] = solution
        projected[fixed_indices, dim] = fixed_values
    return projected


def _third_difference_matrix(length: int) -> np.ndarray:
    if length < 4:
        return np.zeros((0, length), dtype=np.float64)
    matrix = np.zeros((length - 3, length), dtype=np.float64)
    for row in range(length - 3):
        matrix[row, row : row + 4] = (-1.0, 3.0, -3.0, 1.0)
    return matrix


def _third_difference_target_error(projected: np.ndarray, donor: np.ndarray) -> float:
    projected_d3 = np.diff(projected, n=3, axis=0)
    donor_d3 = np.diff(donor, n=3, axis=0)
    if projected_d3.size == 0:
        return 0.0
    return float(np.linalg.norm(projected_d3 - donor_d3, axis=1).mean())


def _max_anchor_error(selected_prefix: np.ndarray, projected_prefix: np.ndarray) -> float:
    errors = [
        np.linalg.norm(projected_prefix[index] - selected_prefix[index])
        for index in ANCHOR_INDICES
    ]
    return float(max(errors))


def _row_keys() -> tuple[str, ...]:
    keys = [
        "outcome_progress_deficit_m",
        "outcome_jerk_delta_mps3",
        "outcome_lateral_delta_mps2",
        "max_anchor_xy_error_m",
        "max_xy_deviation_from_selected_m",
        "mean_xy_deviation_from_selected_m",
        "first_step_reach_delta_m",
        "donor_first_step_reach_delta_m",
        "prefix_jerk_proxy_delta",
        "donor_prefix_jerk_proxy_delta",
        "third_difference_target_error",
    ]
    for horizon in HORIZONS:
        keys.extend(
            [
                f"projection_h{horizon}_displacement_delta_m",
                f"donor_h{horizon}_displacement_delta_m",
                f"projection_h{horizon}_path_delta_m",
                f"donor_h{horizon}_path_delta_m",
            ]
        )
    return tuple(keys)


def _rates(rows: list[dict[str, float]]) -> dict[str, float | int]:
    denom = max(len(rows), 1)
    if not rows:
        return {
            "records": 0,
            "anchor_exact_preservation_rate": 0.0,
            "donor_lower_first_step_rate": 0.0,
            "projection_h3_displacement_nonloss_rate": 0.0,
            "projection_h5_displacement_nonloss_rate": 0.0,
            "projection_h10_displacement_nonloss_rate": 0.0,
            "projection_h3_path_nonloss_rate": 0.0,
            "projection_h5_path_nonloss_rate": 0.0,
            "projection_h10_path_nonloss_rate": 0.0,
            "projection_prefix_jerk_proxy_improvement_rate": 0.0,
        }
    return {
        "records": len(rows),
        "anchor_exact_preservation_rate": sum(
            row["max_anchor_xy_error_m"] <= TOL for row in rows
        )
        / denom,
        "donor_lower_first_step_rate": sum(
            row["donor_first_step_reach_delta_m"] < -TOL for row in rows
        )
        / denom,
        "projection_h3_displacement_nonloss_rate": sum(
            row["projection_h3_displacement_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "projection_h5_displacement_nonloss_rate": sum(
            row["projection_h5_displacement_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "projection_h10_displacement_nonloss_rate": sum(
            row["projection_h10_displacement_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "projection_h3_path_nonloss_rate": sum(
            row["projection_h3_path_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "projection_h5_path_nonloss_rate": sum(
            row["projection_h5_path_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "projection_h10_path_nonloss_rate": sum(
            row["projection_h10_path_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "projection_prefix_jerk_proxy_improvement_rate": sum(
            row["prefix_jerk_proxy_delta"] < -TOL for row in rows
        )
        / denom,
    }


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    lines = [
        "# DP CAMP Smooth Anchor Projection Potential",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- With oracle donors: {records['with_oracle_donor']}",
        "",
        "The audited projection fixes selected H1/H3/H5/H10 anchors exactly "
        "and solves a convex least-squares projection toward the donor third "
        "difference profile. Outcome labels choose donors for this diagnostic "
        "only; no online selector is changed.",
        "",
        "| Ridge | Anchor exact | H3/H5/H10 displacement nonloss | "
        "H3/H5/H10 path nonloss | Jerk-proxy improvement | "
        "Jerk-proxy delta mean | Max selected deviation P95 |",
        "| ---: | ---: | --- | --- | ---: | ---: | ---: |",
    ]
    for ridge_report in report["ridge_reports"]:
        ridge = float(ridge_report["ridge"])
        rates = ridge_report["rates"]
        summary = ridge_report["summary"]
        lines.append(
            f"| {ridge:.6g} | "
            f"{rates['anchor_exact_preservation_rate']:.6f} | "
            f"{rates['projection_h3_displacement_nonloss_rate']:.6f} / "
            f"{rates['projection_h5_displacement_nonloss_rate']:.6f} / "
            f"{rates['projection_h10_displacement_nonloss_rate']:.6f} | "
            f"{rates['projection_h3_path_nonloss_rate']:.6f} / "
            f"{rates['projection_h5_path_nonloss_rate']:.6f} / "
            f"{rates['projection_h10_path_nonloss_rate']:.6f} | "
            f"{rates['projection_prefix_jerk_proxy_improvement_rate']:.6f} | "
            f"{_fmt(summary['prefix_jerk_proxy_delta']['mean'])} | "
            f"{_fmt(summary['max_xy_deviation_from_selected_m']['p95'])} |"
        )
    lines.extend(
        [
            "",
            "## Per-Ridge Details",
            "",
        ]
    )
    for ridge_report in report["ridge_reports"]:
        ridge = float(ridge_report["ridge"])
        summary = ridge_report["summary"]
        lines.extend(
            [
                f"### Ridge `{ridge:.6g}`",
                "",
                "| Quantity | Mean | P50 | P90 | P95 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for label_text, key in (
            ("Outcome progress deficit m", "outcome_progress_deficit_m"),
            ("Outcome jerk delta m/s^3", "outcome_jerk_delta_mps3"),
            ("Outcome lateral delta m/s^2", "outcome_lateral_delta_mps2"),
            ("Max anchor xy error m", "max_anchor_xy_error_m"),
            ("Max selected xy deviation m", "max_xy_deviation_from_selected_m"),
            ("Mean selected xy deviation m", "mean_xy_deviation_from_selected_m"),
            ("Projection jerk-proxy delta", "prefix_jerk_proxy_delta"),
            ("Donor jerk-proxy delta", "donor_prefix_jerk_proxy_delta"),
            ("Third-difference target error", "third_difference_target_error"),
            ("Projection H3 path delta m", "projection_h3_path_delta_m"),
            ("Projection H5 path delta m", "projection_h5_path_delta_m"),
            ("Projection H10 path delta m", "projection_h10_path_delta_m"),
        ):
            lines.append(_summary_row(label_text, summary[key]))
        lines.append("")
    return "\n".join(lines)


def _summary_row(label: str, values: dict[str, float | int | None]) -> str:
    return (
        f"| {label} | {_fmt(values['mean'])} | {_fmt(values['p50'])} | "
        f"{_fmt(values['p90'])} | {_fmt(values['p95'])} |"
    )


if __name__ == "__main__":
    main()
