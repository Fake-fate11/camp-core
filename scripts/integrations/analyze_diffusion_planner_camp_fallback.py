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

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    atom_schema_for_dimension,
    load_dp_camp_atom_scales,
)
from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)


OUTCOME_COST_FIELDS = (
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Paired counterfactual audit of uniform versus learned CAMP "
            "fallback on logged all-infeasible candidate sets."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--atom_scales", type=Path, required=True)
    parser.add_argument("--learned_weights", type=Path, required=True)
    parser.add_argument("--atom_clip", type=float, default=10.0)
    parser.add_argument("--require_atom_schema", action="store_true")
    parser.add_argument("--output_json", type=Path, default=None)
    return parser.parse_args()


def compute_fallback_ablation_report(
    paths: list[Path],
    *,
    atom_scales: np.ndarray,
    learned_weights: np.ndarray,
    atom_clip: float = 10.0,
    require_atom_schema: bool = False,
) -> dict[str, Any]:
    scales = np.asarray(atom_scales, dtype=np.float64).reshape(-1)
    weights = np.asarray(learned_weights, dtype=np.float64).reshape(-1)
    if scales.size == 0 or scales.shape != weights.shape:
        raise ValueError("atom_scales and learned_weights must have equal nonzero shape.")
    if not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise ValueError("atom_scales must contain finite positive values.")
    if not np.all(np.isfinite(weights)) or np.any(weights < -1e-9):
        raise ValueError("learned_weights must contain finite nonnegative values.")
    if not np.isclose(np.sum(weights), 1.0, atol=1e-6):
        raise ValueError("learned_weights must satisfy the simplex unit-sum constraint.")
    weights = np.maximum(weights, 0.0)
    uniform_weights = np.full(weights.size, 1.0 / weights.size)
    schema_version, atom_names = atom_schema_for_dimension(weights.size)

    rows: list[dict[str, Any]] = []
    total_records = 0
    schema_verified = 0
    for log_path in iter_selection_log_paths(paths):
        records = json.loads(log_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError(f"{log_path} must contain a JSON list.")
        for record_idx, record in enumerate(records):
            total_records += 1
            declared_version = record.get("atom_schema_version")
            declared_names = record.get("atom_names")
            if declared_version is None and declared_names is None:
                if require_atom_schema:
                    raise ValueError(
                        f"{log_path} record {record_idx} has no atom schema metadata."
                    )
            elif (
                declared_version != schema_version
                or tuple(declared_names or ()) != atom_names
            ):
                raise ValueError(
                    f"{log_path} record {record_idx} has an incompatible atom schema."
                )
            else:
                schema_verified += 1

            feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
            if feasible.any():
                continue
            atoms = np.asarray(record.get("atoms"), dtype=np.float64)
            if atoms.ndim != 2 or atoms.shape[1] != weights.size:
                raise ValueError(
                    f"{log_path} record {record_idx} has atoms shape {atoms.shape}."
                )
            if atoms.shape[0] != feasible.size:
                raise ValueError("Atom candidate count must match feasible_mask.")
            if not np.all(np.isfinite(atoms)) or np.any(atoms < 0.0):
                raise ValueError("Fallback atoms must be finite nonnegative costs.")
            outcomes = record.get("candidate_closed_loop_outcomes")
            if not isinstance(outcomes, list) or len(outcomes) != atoms.shape[0]:
                raise ValueError(
                    f"{log_path} record {record_idx} lacks complete candidate outcomes."
                )

            normalized = np.nan_to_num(
                atoms / scales.reshape(1, -1),
                nan=0.0,
                posinf=atom_clip,
                neginf=0.0,
            )
            normalized = np.clip(normalized, 0.0, atom_clip)
            uniform_index = int(np.argmin(normalized @ uniform_weights))
            learned_index = int(np.argmin(normalized @ weights))
            outcome_values = np.asarray(
                [float(outcome["value"]) for outcome in outcomes],
                dtype=np.float64,
            )
            finite = np.isfinite(outcome_values)
            if not finite.any():
                raise ValueError("Every fallback record needs a finite outcome value.")
            oracle_index = int(np.argmax(np.where(finite, outcome_values, -np.inf)))
            rows.append(
                {
                    "uniform_index": uniform_index,
                    "learned_index": learned_index,
                    "oracle_index": oracle_index,
                    "uniform": _selected_outcome(outcomes[uniform_index]),
                    "learned": _selected_outcome(outcomes[learned_index]),
                    "oracle_value": float(outcome_values[oracle_index]),
                }
            )

    return {
        "analysis": {
            "name": "dp_camp_all_infeasible_fallback_counterfactual",
            "scope": "all_infeasible_ticks_only",
            "interpretation": (
                "Paired short-horizon counterfactual diagnostic; it does not replace "
                "matched closed-loop fallback evaluation."
            ),
            "atom_schema_version": schema_version,
            "atom_names": list(atom_names),
        },
        "records": {
            "total": total_records,
            "all_infeasible": len(rows),
            "schema_verified": schema_verified,
        },
        "uniform": _policy_summary(rows, "uniform"),
        "learned": _policy_summary(rows, "learned"),
        "paired": _paired_summary(rows),
    }


def _selected_outcome(outcome: dict[str, Any]) -> dict[str, float]:
    selected = {"value": float(outcome["value"])}
    for field in OUTCOME_COST_FIELDS:
        selected[field] = float(outcome.get(field, 0.0))
    return selected


def _policy_summary(rows: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    if not rows:
        return {"records": 0}
    selected = [row[policy] for row in rows]
    return {
        "records": len(rows),
        "oracle_match_rate": float(
            np.mean(
                [
                    row[f"{policy}_index"] == row["oracle_index"]
                    for row in rows
                ]
            )
        ),
        "mean_outcome_value": float(np.mean([item["value"] for item in selected])),
        "mean_outcome_regret": float(
            np.mean(
                [
                    row["oracle_value"] - row[policy]["value"]
                    for row in rows
                ]
            )
        ),
        **{
            f"mean_{field}": float(np.mean([item[field] for item in selected]))
            for field in OUTCOME_COST_FIELDS
        },
    }


def _paired_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"records": 0}
    return {
        "records": len(rows),
        "selection_disagreement_rate": float(
            np.mean(
                [
                    row["uniform_index"] != row["learned_index"]
                    for row in rows
                ]
            )
        ),
        "learned_minus_uniform_outcome_value": float(
            np.mean(
                [
                    row["learned"]["value"] - row["uniform"]["value"]
                    for row in rows
                ]
            )
        ),
        **{
            f"learned_minus_uniform_{field}": float(
                np.mean(
                    [
                        row["learned"][field] - row["uniform"][field]
                        for row in rows
                    ]
                )
            )
            for field in OUTCOME_COST_FIELDS
        },
    }


def main() -> None:
    args = parse_args()
    inputs = list(args.root) + list(args.selection_log)
    if not inputs:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = compute_fallback_ablation_report(
        inputs,
        atom_scales=load_dp_camp_atom_scales(args.atom_scales),
        learned_weights=np.load(args.learned_weights),
        atom_clip=args.atom_clip,
        require_atom_schema=args.require_atom_schema,
    )
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output_json is None:
        print(text)
    else:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text + "\n", encoding="utf-8")
        print(f"Fallback ablation report: {args.output_json}")


if __name__ == "__main__":
    main()
