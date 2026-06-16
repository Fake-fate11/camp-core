#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
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


OUTCOME_FIELDS = (
    "progress_m",
    "value",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
)
ATOM_FIELDS = (
    "progress_shortfall",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
    "jerk_early",
    "jerk_full",
)


@dataclass(frozen=True)
class Variant:
    name: str
    transfers: tuple[tuple[str, str, float], ...]


PREDECLARED_VARIANTS = (
    Variant("baseline_redstopfloor05", ()),
    Variant("progress_to_lateral_0p01", (("progress_shortfall", "planned_lateral_acceleration_cost", 0.01),)),
    Variant("progress_to_lateral_0p03", (("progress_shortfall", "planned_lateral_acceleration_cost", 0.03),)),
    Variant("progress_to_lateral_0p05", (("progress_shortfall", "planned_lateral_acceleration_cost", 0.05),)),
    Variant("progress_to_jerk_0p02", (("progress_shortfall", "dp_prior_jerk_excess_cost", 0.02),)),
    Variant("progress_to_jerk_0p05", (("progress_shortfall", "dp_prior_jerk_excess_cost", 0.05),)),
    Variant(
        "progress_to_lateral_0p02_jerk_0p02",
        (
            ("progress_shortfall", "planned_lateral_acceleration_cost", 0.02),
            ("progress_shortfall", "dp_prior_jerk_excess_cost", 0.02),
        ),
    ),
    Variant(
        "progress_to_lateral_0p03_jerk_0p03",
        (
            ("progress_shortfall", "planned_lateral_acceleration_cost", 0.03),
            ("progress_shortfall", "dp_prior_jerk_excess_cost", 0.03),
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline fixed-candidate sensitivity screen for DP CAMP static "
            "weights. This does not train, deploy, or alter Diffusion Planner."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def analyze(paths: list[Path]) -> dict[str, Any]:
    log_paths = iter_selection_log_paths(paths)
    if not log_paths:
        raise ValueError("No selection logs were found.")

    records = []
    atom_names: tuple[str, ...] | None = None
    base_weights: np.ndarray | None = None
    for log_path in log_paths:
        payload = json.loads(log_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, list) or not payload:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for index, record in enumerate(payload):
            loaded = _load_record(record, f"{log_path} record {index}")
            if atom_names is None:
                atom_names = loaded["atom_names"]
                base_weights = loaded["weights"]
            elif atom_names != loaded["atom_names"]:
                raise ValueError("All records must use the same atom schema.")
            else:
                np.testing.assert_allclose(base_weights, loaded["weights"])
            records.append(loaded)
    assert atom_names is not None and base_weights is not None

    variants = [
        _variant_report(variant, records, atom_names, base_weights)
        for variant in PREDECLARED_VARIANTS
    ]
    return {
        "analysis": {
            "name": "dp_camp_static_weight_transfer_sensitivity_v1",
            "role": "offline fixed-candidate counterfactual screen",
            "training": False,
            "online_selector_change": False,
            "future_outcome_leakage": False,
            "fallback_policy": "retain baseline selected index for all-infeasible records",
            "convexity_scope": (
                "Every screened weight vector is a fixed point in the "
                "nonnegative simplex with the red-stopping lower bound "
                "preserved. For fixed candidates, scores remain affine in w."
            ),
            "predeclared_variants": [
                {
                    "name": variant.name,
                    "transfers": [
                        {"source": src, "target": dst, "amount": amount}
                        for src, dst, amount in variant.transfers
                    ],
                }
                for variant in PREDECLARED_VARIANTS
            ],
        },
        "records": {
            "logs": len(log_paths),
            "total": len(records),
            "nonfallback": sum(int(record["feasible"].any()) for record in records),
            "fallback": sum(int(not record["feasible"].any()) for record in records),
        },
        "atom_names": list(atom_names),
        "baseline_weights": {
            name: float(value) for name, value in zip(atom_names, base_weights)
        },
        "variants": variants,
    }


def _load_record(record: dict[str, Any], label: str) -> dict[str, Any]:
    atom_names = tuple(record.get("atom_names") or ())
    if not atom_names:
        raise ValueError(f"{label} is missing atom_names.")
    weights = _vector(record.get("weights"), len(atom_names), f"{label} weights")
    normalized_atoms = _matrix(
        record.get("normalized_atoms"),
        len(atom_names),
        f"{label} normalized_atoms",
    )
    feasible = _bool_vector(
        record.get("feasible_mask"),
        normalized_atoms.shape[0],
        f"{label} feasible_mask",
    )
    selected_index = int(record.get("selected_index"))
    if selected_index < 0 or selected_index >= normalized_atoms.shape[0]:
        raise ValueError(f"{label} selected_index is out of range.")
    outcomes = _outcomes(
        record.get("candidate_closed_loop_outcomes"),
        normalized_atoms.shape[0],
        label,
    )
    raw_atoms = _matrix(record.get("atoms"), len(atom_names), f"{label} atoms")
    if raw_atoms.shape != normalized_atoms.shape:
        raise ValueError(f"{label} atoms and normalized_atoms shape mismatch.")
    return {
        "atom_names": atom_names,
        "weights": weights,
        "normalized_atoms": normalized_atoms,
        "raw_atoms": raw_atoms,
        "feasible": feasible,
        "selected_index": selected_index,
        "outcomes": outcomes,
    }


def _variant_report(
    variant: Variant,
    records: list[dict[str, Any]],
    atom_names: tuple[str, ...],
    base_weights: np.ndarray,
) -> dict[str, Any]:
    weights = _apply_transfers(base_weights, atom_names, variant)
    changed = 0
    nonfallback = 0
    deltas: dict[str, list[float]] = {field: [] for field in OUTCOME_FIELDS}
    changed_deltas: dict[str, list[float]] = {field: [] for field in OUTCOME_FIELDS}
    atom_deltas: dict[str, list[float]] = {field: [] for field in ATOM_FIELDS}
    changed_atom_deltas: dict[str, list[float]] = {field: [] for field in ATOM_FIELDS}

    for record in records:
        baseline_index = record["selected_index"]
        feasible = record["feasible"]
        if feasible.any():
            nonfallback += 1
            selected_index = _select(record["normalized_atoms"], weights, feasible)
        else:
            selected_index = baseline_index
        changed_record = selected_index != baseline_index
        changed += int(changed_record)
        for field in OUTCOME_FIELDS:
            delta = _outcome_delta(
                record["outcomes"][selected_index],
                record["outcomes"][baseline_index],
                field,
            )
            deltas[field].append(delta)
            if changed_record:
                changed_deltas[field].append(delta)
        for field in ATOM_FIELDS:
            if field not in atom_names:
                continue
            atom_idx = atom_names.index(field)
            delta = (
                record["raw_atoms"][selected_index, atom_idx]
                - record["raw_atoms"][baseline_index, atom_idx]
            )
            atom_deltas[field].append(float(delta))
            if changed_record:
                changed_atom_deltas[field].append(float(delta))

    return {
        "name": variant.name,
        "weights": {
            name: float(value) for name, value in zip(atom_names, weights)
        },
        "simplex_sum": float(np.sum(weights)),
        "minimum_weight": float(np.min(weights)),
        "red_stopping_lower_bound_preserved": bool(
            weights[atom_names.index("red_stopping_margin_cost")] >= 0.05 - 1e-12
            if "red_stopping_margin_cost" in atom_names
            else False
        ),
        "changed_records": int(changed),
        "nonfallback_records": int(nonfallback),
        "change_rate": changed / max(len(records), 1),
        "nonfallback_change_rate": changed / max(nonfallback, 1),
        "outcome_delta_mean": {
            field: _mean(values) for field, values in deltas.items()
        },
        "changed_outcome_delta_mean": {
            field: _mean(values) for field, values in changed_deltas.items()
        },
        "atom_delta_mean": {
            field: _mean(values) for field, values in atom_deltas.items()
        },
        "changed_atom_delta_mean": {
            field: _mean(values) for field, values in changed_atom_deltas.items()
        },
    }


def _apply_transfers(
    base_weights: np.ndarray,
    atom_names: tuple[str, ...],
    variant: Variant,
) -> np.ndarray:
    weights = np.asarray(base_weights, dtype=np.float64).copy()
    name_to_index = {name: idx for idx, name in enumerate(atom_names)}
    for source, target, amount in variant.transfers:
        if source not in name_to_index or target not in name_to_index:
            raise ValueError(f"Unknown transfer atom in {variant.name}.")
        if not np.isfinite(amount) or amount < 0.0:
            raise ValueError(f"Invalid transfer amount in {variant.name}.")
        weights[name_to_index[source]] -= amount
        weights[name_to_index[target]] += amount
    if np.any(weights < -1e-12):
        raise ValueError(f"Variant {variant.name} leaves the simplex.")
    weights = np.maximum(weights, 0.0)
    if not math.isclose(float(np.sum(weights)), 1.0, abs_tol=1e-9):
        raise ValueError(f"Variant {variant.name} does not preserve simplex sum.")
    if (
        "red_stopping_margin_cost" in name_to_index
        and weights[name_to_index["red_stopping_margin_cost"]] < 0.05 - 1e-12
    ):
        raise ValueError(f"Variant {variant.name} violates red-stopping lower bound.")
    return weights


def _select(
    normalized_atoms: np.ndarray,
    weights: np.ndarray,
    feasible: np.ndarray,
) -> int:
    scores = normalized_atoms @ weights
    masked = np.where(feasible, scores, np.inf)
    return int(np.argmin(masked))


def _outcome_delta(
    selected: dict[str, Any],
    baseline: dict[str, Any],
    field: str,
) -> float:
    left = selected.get(field)
    right = baseline.get(field)
    if isinstance(left, bool) and isinstance(right, bool):
        return float(left) - float(right)
    if left is None or right is None:
        return 0.0
    return float(left) - float(right)


def _outcomes(values: Any, size: int, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != size:
        raise ValueError(f"{label} must contain {size} candidate outcomes.")
    for index, outcome in enumerate(values):
        if not isinstance(outcome, dict) or outcome.get("candidate_index") != index:
            raise ValueError(f"{label} outcome indices must be contiguous.")
    return values


def _matrix(values: Any, width: int, label: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != width:
        raise ValueError(f"{label} must have shape [K,{width}].")
    if not np.all(np.isfinite(matrix)) or np.any(matrix < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return matrix


def _vector(values: Any, size: int, label: str) -> np.ndarray:
    vector = np.asarray(values, dtype=np.float64).reshape(-1)
    if vector.shape != (size,):
        raise ValueError(f"{label} must have shape [{size}].")
    if not np.all(np.isfinite(vector)) or np.any(vector < 0.0):
        raise ValueError(f"{label} must be finite and nonnegative.")
    return vector


def _bool_vector(values: Any, size: int, label: str) -> np.ndarray:
    raw = np.asarray(values, dtype=object).reshape(-1)
    if raw.shape != (size,) or not all(isinstance(value, (bool, np.bool_)) for value in raw):
        raise ValueError(f"{label} must contain {size} booleans.")
    return raw.astype(bool)


def _mean(values: list[float]) -> float | None:
    return None if not values else float(np.mean(np.asarray(values, dtype=np.float64)))


def render_markdown(report: dict[str, Any]) -> str:
    records = report["records"]
    lines = [
        "# DP CAMP Static Weight Sensitivity",
        "",
        f"- Logs: {records['logs']}",
        f"- Records: {records['total']}",
        f"- Nonfallback records: {records['nonfallback']}",
        f"- Fallback records retained: {records['fallback']}",
        "",
        "| Variant | Changed | Nonfallback changed | Progress delta | Red delta | "
        "Jerk delta | Lateral delta | Value delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant in report["variants"]:
        outcome = variant["outcome_delta_mean"]
        lines.append(
            f"| `{variant['name']}` | "
            f"{variant['changed_records']} | "
            f"{_fmt(variant['nonfallback_change_rate'])} | "
            f"{_fmt(outcome['progress_m'])} | "
            f"{_fmt(outcome['red_light_violation'])} | "
            f"{_fmt(outcome['mean_jerk_mps3'])} | "
            f"{_fmt(outcome['mean_lateral_acceleration_mps2'])} | "
            f"{_fmt(outcome['value'])} |"
        )
    lines.extend(
        [
            "",
            "This is an offline fixed-candidate sensitivity screen. It does "
            "not train weights, change online selection, alter Diffusion "
            "Planner, or use formal seeds.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def main() -> None:
    args = parse_args()
    paths = list(args.root) + list(args.selection_log)
    if not paths:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = analyze(paths)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


if __name__ == "__main__":
    main()
