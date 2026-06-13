#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
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
    DP_CAMP_ATOM_NAMES_V9,
    DP_CAMP_ATOM_NAMES_V10,
    atom_schema_for_dimension,
)
from camp_core.integrations.diffusion_planner_coverage import (  # noqa: E402
    iter_selection_log_paths,
)


LOG_NAME = "camp_selection_log.json"
SUMMARY_NAME = "camp_validation_summary.json"
DEFAULT_HORIZON_STEPS = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a dp_camp_v10_14d training-log view by appending the "
            "audited online 30-step DP-prior jerk-excess shadow to v9 atoms."
        )
    )
    parser.add_argument("--root", type=Path, action="append", default=[])
    parser.add_argument("--selection_log", type=Path, action="append", default=[])
    parser.add_argument("--output_root", type=Path, required=True)
    parser.add_argument(
        "--expected_horizon_steps",
        type=int,
        default=DEFAULT_HORIZON_STEPS,
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing existing augmented camp_selection_log.json files.",
    )
    return parser.parse_args()


def augment_record(
    record: dict[str, Any],
    *,
    log_path: Path,
    record_idx: int,
    expected_horizon_steps: int = DEFAULT_HORIZON_STEPS,
) -> dict[str, Any]:
    source_version, source_names = atom_schema_for_dimension(
        len(DP_CAMP_ATOM_NAMES_V9)
    )
    target_version, target_names = atom_schema_for_dimension(
        len(DP_CAMP_ATOM_NAMES_V10)
    )
    if (
        record.get("atom_schema_version") != source_version
        or tuple(record.get("atom_names") or ()) != source_names
    ):
        raise ValueError(
            f"{log_path} record {record_idx} must use {source_version} "
            "before v10 augmentation."
        )

    atoms = np.asarray(record.get("atoms"), dtype=np.float64)
    if atoms.ndim != 2 or atoms.shape[1] != len(source_names):
        raise ValueError(
            f"{log_path} record {record_idx} has atoms shape {atoms.shape}; "
            f"expected [K,{len(source_names)}]."
        )
    if not np.all(np.isfinite(atoms)) or np.any(atoms < 0.0):
        raise ValueError(f"{log_path} record {record_idx} has invalid v9 atoms.")

    horizon_steps = record.get(
        "candidate_dp_prior_comfort_excess_horizon_steps"
    )
    if (
        isinstance(horizon_steps, bool)
        or not isinstance(horizon_steps, int)
        or horizon_steps != expected_horizon_steps
    ):
        raise ValueError(
            f"{log_path} record {record_idx} uses comfort-shadow horizon "
            f"{horizon_steps!r}, expected {expected_horizon_steps}."
        )

    jerk_excess = np.asarray(
        record.get("candidate_dp_prior_jerk_excess_cost"),
        dtype=np.float64,
    ).reshape(-1)
    if jerk_excess.shape != (atoms.shape[0],):
        raise ValueError(
            f"{log_path} record {record_idx} has jerk-excess shape "
            f"{jerk_excess.shape}; expected ({atoms.shape[0]},)."
        )
    if not np.all(np.isfinite(jerk_excess)) or np.any(jerk_excess < 0.0):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid jerk-excess costs."
        )
    if abs(float(jerk_excess[0])) > 1e-12:
        raise ValueError(
            f"{log_path} record {record_idx} jerk-excess candidate 0 "
            "must be zero."
        )

    augmented = copy.deepcopy(record)
    augmented["source_atom_schema_version"] = source_version
    augmented["source_atom_names"] = list(source_names)
    augmented["source_selection_scores_schema_version"] = source_version
    augmented["atom_schema_version"] = target_version
    augmented["atom_names"] = list(target_names)
    augmented["atoms"] = np.concatenate(
        [atoms, jerk_excess.reshape(-1, 1)],
        axis=1,
    ).tolist()
    augmented["dp_prior_jerk_excess_used_as_atom"] = False
    augmented["offline_augmentation"] = {
        "name": "dp_camp_v10_dp_prior_jerk_excess_from_h30_shadow",
        "source_field": "candidate_dp_prior_jerk_excess_cost",
        "target_atom": "dp_prior_jerk_excess_cost",
        "horizon_steps": expected_horizon_steps,
        "source_log": str(log_path),
        "no_closed_loop_label_source": True,
        "selection_scores_remain_source_v9": True,
    }
    for stale_field in (
        "normalized_atoms",
        "selection_normalized_atoms",
        "weights",
        "selection_weights",
    ):
        augmented.pop(stale_field, None)
    return augmented


def augment_records(
    records: list[dict[str, Any]],
    *,
    log_path: Path,
    expected_horizon_steps: int = DEFAULT_HORIZON_STEPS,
) -> list[dict[str, Any]]:
    if not records:
        raise ValueError(f"{log_path} is empty.")
    return [
        augment_record(
            record,
            log_path=log_path,
            record_idx=record_idx,
            expected_horizon_steps=expected_horizon_steps,
        )
        for record_idx, record in enumerate(records)
    ]


def _read_log(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list.")
    if not all(isinstance(record, dict) for record in payload):
        raise ValueError(f"{path} must contain JSON objects.")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _discover_inputs(
    roots: list[Path],
    selection_logs: list[Path],
) -> list[tuple[Path, Path | None]]:
    inputs: list[tuple[Path, Path | None]] = []
    for root in roots:
        root = Path(root)
        for log_path in iter_selection_log_paths([root]):
            inputs.append((log_path, root))
    for log_path in selection_logs:
        path = Path(log_path)
        if path.name != LOG_NAME:
            raise ValueError(f"Expected {LOG_NAME}, got {path}.")
        inputs.append((path, None))
    unique: dict[Path, tuple[Path, Path | None]] = {}
    for log_path, source_root in inputs:
        unique[log_path.resolve()] = (log_path, source_root)
    return [unique[key] for key in sorted(unique)]


def _relative_output_parent(
    log_path: Path,
    source_root: Path | None,
    index: int,
) -> Path:
    if source_root is not None:
        return log_path.parent.relative_to(source_root)
    return Path(f"log_{index:04d}") / log_path.parent.name


def _validate_summary_horizon(
    summary_path: Path,
    expected_horizon_steps: int,
) -> None:
    if not summary_path.is_file():
        raise ValueError(f"Missing completed-run summary for {summary_path}.")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metadata = summary.get("camp_shadow_dp_prior_comfort_excess")
    effective_horizon = (
        metadata.get("effective_horizon_steps")
        if isinstance(metadata, dict)
        else None
    )
    if (
        isinstance(effective_horizon, bool)
        or not isinstance(effective_horizon, int)
        or effective_horizon != expected_horizon_steps
    ):
        raise ValueError(
            f"{summary_path} does not certify comfort-shadow horizon "
            f"{expected_horizon_steps}."
        )


def augment_logs(
    inputs: list[tuple[Path, Path | None]],
    *,
    output_root: Path,
    expected_horizon_steps: int = DEFAULT_HORIZON_STEPS,
    overwrite: bool = False,
) -> dict[str, Any]:
    if not inputs:
        raise ValueError("No selection logs were found.")
    if (
        isinstance(expected_horizon_steps, bool)
        or not isinstance(expected_horizon_steps, int)
        or expected_horizon_steps <= 0
    ):
        raise ValueError("expected_horizon_steps must be a positive integer.")
    output_root = Path(output_root)
    reports = []
    total_records = 0
    target_version, target_names = atom_schema_for_dimension(
        len(DP_CAMP_ATOM_NAMES_V10)
    )
    for index, (log_path, source_root) in enumerate(inputs):
        source_summary = log_path.with_name(SUMMARY_NAME)
        _validate_summary_horizon(source_summary, expected_horizon_steps)
        output_parent = output_root / _relative_output_parent(
            log_path,
            source_root,
            index,
        )
        output_log = output_parent / LOG_NAME
        if output_log.exists() and not overwrite:
            raise FileExistsError(
                f"{output_log} already exists; pass --overwrite to replace it."
            )
        records = _read_log(log_path)
        augmented = augment_records(
            records,
            log_path=log_path,
            expected_horizon_steps=expected_horizon_steps,
        )
        output_parent.mkdir(parents=True, exist_ok=True)
        output_log.write_text(
            json.dumps(augmented, indent=2) + "\n",
            encoding="utf-8",
        )
        output_summary = output_parent / SUMMARY_NAME
        shutil.copy2(source_summary, output_summary)
        total_records += len(augmented)
        reports.append(
            {
                "source_log": str(log_path),
                "output_log": str(output_log),
                "records": len(augmented),
                "source_sha256": _sha256(log_path),
                "output_sha256": _sha256(output_log),
                "summary_copied": True,
            }
        )
    return {
        "augmentation": "dp_camp_v10_dp_prior_jerk_excess_from_h30_shadow",
        "schema": {
            "version": target_version,
            "atom_names": list(target_names),
            "num_atoms": len(target_names),
        },
        "source_schema": {
            "version": atom_schema_for_dimension(len(DP_CAMP_ATOM_NAMES_V9))[0],
            "atom_names": list(DP_CAMP_ATOM_NAMES_V9),
            "num_atoms": len(DP_CAMP_ATOM_NAMES_V9),
        },
        "counts": {
            "logs": len(reports),
            "records": total_records,
        },
        "logs": reports,
        "contract": {
            "source_field": "candidate_dp_prior_jerk_excess_cost",
            "target_atom": "dp_prior_jerk_excess_cost",
            "horizon_steps": expected_horizon_steps,
            "atom_is_current_tick_online_shadow_diagnostic": True,
            "closed_loop_outcomes_are_not_atom_inputs": True,
            "selection_scores_remain_source_v9": True,
        },
    }


def main() -> None:
    args = parse_args()
    inputs = _discover_inputs(args.root, args.selection_log)
    report = augment_logs(
        inputs,
        output_root=args.output_root,
        expected_horizon_steps=args.expected_horizon_steps,
        overwrite=args.overwrite,
    )
    manifest_path = args.output_root / "v10_jerk_excess_augmentation_manifest.json"
    args.output_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Augmented {report['counts']['logs']} logs and "
        f"{report['counts']['records']} records -> {args.output_root}"
    )


if __name__ == "__main__":
    main()
