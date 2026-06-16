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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline oracle-potential audit for an H1/H3/H5/H10 anchored "
            "residual reference graft. Outcome labels choose diagnostic donors "
            "only; the audited graft formula uses current-tick prefixes."
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
            "name": "dp_camp_anchored_residual_graft_potential_v1",
            "role": (
                "offline cheap-proof screen for H1/H3/H5/H10 "
                "progress-anchor-preserving candidate construction"
            ),
            "label": label,
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": (
                "candidate outcomes choose oracle donors for diagnosis only; "
                "the audited residual graft formula itself uses current-tick "
                "reference prefixes"
            ),
            "anchor_horizons": ANCHOR_HORIZONS,
            "graft_definition": (
                "within each adjacent anchor interval, subtract the donor "
                "linear interpolation between anchor endpoints, then add that "
                "donor residual to the selected linear interpolation; this "
                "preserves selected H1/H3/H5/H10 anchor xy exactly"
            ),
            "not_repeated_routes": (
                "not prefix-blend because it does not interpolate toward "
                "candidate 0; not a step-reach guard because it constructs a "
                "diagnostic prefix instead of filtering candidates"
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


def _graft_row(record: dict[str, Any], donor: int) -> dict[str, float]:
    selected = record["selected_index"]
    prefix = record["prefix_xy"][:, : max(HORIZONS)]
    selected_prefix = prefix[selected]
    donor_prefix = prefix[donor]
    graft_prefix = _anchored_residual_graft(selected_prefix, donor_prefix)
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
        "max_anchor_xy_error_m": _max_anchor_error(selected_prefix, graft_prefix),
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


def _anchored_residual_graft(
    selected_prefix: np.ndarray,
    donor_prefix: np.ndarray,
) -> np.ndarray:
    graft = np.empty_like(selected_prefix)
    for start, end in zip(ANCHOR_INDICES[:-1], ANCHOR_INDICES[1:]):
        span = end - start
        selected_start = selected_prefix[start]
        selected_delta = selected_prefix[end] - selected_start
        donor_start = donor_prefix[start]
        donor_delta = donor_prefix[end] - donor_start
        for index in range(start, end + 1):
            fraction = (index - start) / span
            selected_linear = selected_start + fraction * selected_delta
            donor_linear = donor_start + fraction * donor_delta
            graft[index] = selected_linear + (donor_prefix[index] - donor_linear)
    return graft


def _max_anchor_error(selected_prefix: np.ndarray, graft_prefix: np.ndarray) -> float:
    errors = [
        np.linalg.norm(graft_prefix[index] - selected_prefix[index])
        for index in ANCHOR_INDICES
    ]
    return float(max(errors))


def _row_keys() -> tuple[str, ...]:
    keys = [
        "outcome_progress_deficit_m",
        "outcome_jerk_delta_mps3",
        "outcome_lateral_delta_mps2",
        "max_anchor_xy_error_m",
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
            "anchor_exact_preservation_rate": 0.0,
            "donor_lower_first_step_rate": 0.0,
            "graft_h3_displacement_nonloss_rate": 0.0,
            "graft_h5_displacement_nonloss_rate": 0.0,
            "graft_h10_displacement_nonloss_rate": 0.0,
            "graft_h3_path_nonloss_rate": 0.0,
            "graft_h5_path_nonloss_rate": 0.0,
            "graft_h10_path_nonloss_rate": 0.0,
            "graft_prefix_jerk_proxy_improvement_rate": 0.0,
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
        "graft_h3_path_nonloss_rate": sum(
            row["graft_h3_path_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "graft_h5_path_nonloss_rate": sum(
            row["graft_h5_path_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "graft_h10_path_nonloss_rate": sum(
            row["graft_h10_path_delta_m"] >= -TOL for row in rows
        )
        / denom,
        "graft_prefix_jerk_proxy_improvement_rate": sum(
            row["prefix_jerk_proxy_delta"] < -TOL for row in rows
        )
        / denom,
    }


def render_markdown(report: dict[str, Any]) -> str:
    label = report["analysis"].get("label") or "candidate set"
    records = report["records"]
    rates = report["rates"]
    lines = [
        "# DP CAMP Anchored Residual Graft Potential",
        "",
        f"- Label: `{label}`",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- With oracle donors: {records['with_oracle_donor']}",
        "",
        "The audited graft preserves the selected H1/H3/H5/H10 reference "
        "anchors exactly, then injects the donor residual relative to each "
        "donor anchor interval's linear interpolation. Outcome labels choose "
        "donors for this diagnostic only; no online selector is changed.",
        "",
        f"- Anchor exact preservation rate: "
        f"`{rates['anchor_exact_preservation_rate']:.6f}`",
        f"- Donor lower first-step rate before graft: "
        f"`{rates['donor_lower_first_step_rate']:.6f}`",
        f"- Graft H3/H5/H10 displacement nonloss rates: "
        f"`{rates['graft_h3_displacement_nonloss_rate']:.6f}` / "
        f"`{rates['graft_h5_displacement_nonloss_rate']:.6f}` / "
        f"`{rates['graft_h10_displacement_nonloss_rate']:.6f}`",
        f"- Graft H3/H5/H10 path nonloss rates: "
        f"`{rates['graft_h3_path_nonloss_rate']:.6f}` / "
        f"`{rates['graft_h5_path_nonloss_rate']:.6f}` / "
        f"`{rates['graft_h10_path_nonloss_rate']:.6f}`",
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
        ("Max anchor xy error m", "max_anchor_xy_error_m"),
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
