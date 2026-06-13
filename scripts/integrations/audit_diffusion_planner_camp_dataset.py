#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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


REQUIRED_OUTCOME_FIELDS = {
    "value",
    "feasible",
    "collision",
    "near_miss",
    "lane_violation",
    "red_light_violation",
    "mean_jerk_mps3",
    "mean_lateral_acceleration_mps2",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail-closed audit for DP-compatible CAMP training logs."
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--atom_scales", type=Path, required=True)
    parser.add_argument("--expected_logs", type=int, default=None)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument(
        "--expected_advance_mode",
        choices=("perfect", "mpc", "teleport"),
        default=None,
    )
    parser.add_argument("--output_json", type=Path, required=True)
    return parser.parse_args()


def audit_training_dataset(
    paths: list[Path],
    *,
    atom_scales: np.ndarray,
    expected_logs: int | None,
    expected_candidates: int,
    expected_advance_mode: str | None = None,
) -> dict[str, Any]:
    scales = np.asarray(atom_scales, dtype=np.float64).reshape(-1)
    if scales.size == 0 or not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise ValueError("atom_scales must contain finite positive values.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    schema_version, atom_names = atom_schema_for_dimension(scales.size)
    red_atom_index = (
        atom_names.index("planned_red_light_cost")
        if "planned_red_light_cost" in atom_names
        else None
    )

    log_paths = iter_selection_log_paths(paths)
    if expected_logs is not None and len(log_paths) != expected_logs:
        raise ValueError(
            f"Expected {expected_logs} selection logs, found {len(log_paths)}."
        )
    if not log_paths:
        raise ValueError("No selection logs were found.")

    total_records = 0
    total_candidates = 0
    all_infeasible_records = 0
    outcome_candidates = 0
    log_reports = []
    for log_path in log_paths:
        summary_path = log_path.with_name("camp_validation_summary.json")
        if not summary_path.is_file():
            raise ValueError(f"Missing completed-run summary for {log_path}.")
        validation_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(validation_summary, dict):
            raise ValueError(f"{summary_path} must contain a JSON object.")
        advance_mode = validation_summary.get("advance_mode")
        if expected_advance_mode is not None and advance_mode != expected_advance_mode:
            raise ValueError(
                f"{summary_path} uses advance_mode={advance_mode!r}, "
                f"expected {expected_advance_mode!r}."
            )
        records = json.loads(log_path.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            raise ValueError(f"{log_path} must contain a nonempty JSON list.")
        for record_idx, record in enumerate(records):
            _validate_record_schema(
                log_path,
                record_idx,
                record,
                schema_version=schema_version,
                atom_names=atom_names,
            )
            atoms = np.asarray(record.get("atoms"), dtype=np.float64)
            expected_shape = (expected_candidates, scales.size)
            if atoms.shape != expected_shape:
                raise ValueError(
                    f"{log_path} record {record_idx} has atoms shape "
                    f"{atoms.shape}, expected {expected_shape}."
                )
            if not np.all(np.isfinite(atoms)) or np.any(atoms < 0.0):
                raise ValueError(
                    f"{log_path} record {record_idx} has invalid atom values."
                )
            feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
            if feasible.shape != (expected_candidates,):
                raise ValueError(
                    f"{log_path} record {record_idx} has invalid feasible_mask."
                )
            outcomes = record.get("candidate_closed_loop_outcomes")
            if not isinstance(outcomes, list) or len(outcomes) != expected_candidates:
                raise ValueError(
                    f"{log_path} record {record_idx} has incomplete outcomes."
                )
            for candidate_idx, outcome in enumerate(outcomes):
                if (
                    not isinstance(outcome, dict)
                    or not REQUIRED_OUTCOME_FIELDS.issubset(outcome)
                ):
                    raise ValueError(
                        f"{log_path} record {record_idx} candidate "
                        f"{candidate_idx} has incomplete outcome fields."
                    )
                if not np.isfinite(float(outcome["value"])):
                    raise ValueError("Outcome values must be finite.")
            if red_atom_index is not None:
                _validate_red_light_provenance(
                    log_path,
                    record_idx,
                    record,
                    atoms[:, red_atom_index],
                    expected_candidates,
                )

            total_records += 1
            total_candidates += expected_candidates
            outcome_candidates += len(outcomes)
            all_infeasible_records += int(not feasible.any())
        log_reports.append(
            {
                "selection_log": str(log_path),
                "validation_summary": str(summary_path),
                "records": len(records),
                "selection_log_sha256": _sha256(log_path),
                "validation_summary_sha256": _sha256(summary_path),
                "advance_mode": advance_mode,
            }
        )

    return {
        "audit": "dp_camp_training_dataset_v1",
        "passed": True,
        "schema": {
            "version": schema_version,
            "atom_names": list(atom_names),
            "num_atoms": scales.size,
        },
        "counts": {
            "logs": len(log_paths),
            "records": total_records,
            "candidates": total_candidates,
            "all_infeasible_records": all_infeasible_records,
        },
        "checks": {
            "completed_run_summaries": True,
            "exact_candidate_and_atom_shapes": True,
            "finite_nonnegative_atoms": True,
            "exact_schema_metadata": True,
            "complete_closed_loop_outcomes": True,
            "red_light_atom_matches_online_dp_reward": red_atom_index is not None,
            "outcome_candidate_coverage": (
                outcome_candidates / total_candidates if total_candidates else 0.0
            ),
            "expected_advance_mode": expected_advance_mode,
            "advance_mode_verified": expected_advance_mode is not None,
        },
        "logs": log_reports,
    }


def _validate_record_schema(
    log_path: Path,
    record_idx: int,
    record: dict[str, Any],
    *,
    schema_version: str,
    atom_names: tuple[str, ...],
) -> None:
    if (
        record.get("atom_schema_version") != schema_version
        or tuple(record.get("atom_names") or ()) != atom_names
    ):
        raise ValueError(
            f"{log_path} record {record_idx} does not match {schema_version}."
        )


def _validate_red_light_provenance(
    log_path: Path,
    record_idx: int,
    record: dict[str, Any],
    atom_values: np.ndarray,
    expected_candidates: int,
) -> None:
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != expected_candidates:
        raise ValueError(
            f"{log_path} record {record_idx} lacks complete DP rewards."
        )
    expected = np.asarray(
        [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in rewards],
        dtype=np.float64,
    )
    if not np.allclose(atom_values, expected, atol=1e-10, rtol=1e-10):
        raise ValueError(
            f"{log_path} record {record_idx} red-light atom provenance mismatch."
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    inputs = list(args.root) + list(args.selection_log)
    if not inputs:
        raise SystemExit("Provide at least one --root or --selection_log.")
    report = audit_training_dataset(
        inputs,
        atom_scales=load_dp_camp_atom_scales(args.atom_scales),
        expected_logs=args.expected_logs,
        expected_candidates=args.expected_candidates,
        expected_advance_mode=args.expected_advance_mode,
    )
    report["artifacts"] = {
        "atom_scales": str(args.atom_scales),
        "atom_scales_sha256": _sha256(args.atom_scales),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"Dataset audit passed: {report['counts']['logs']} logs, "
        f"{report['counts']['records']} records -> {args.output_json}"
    )


if __name__ == "__main__":
    main()
