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
    parse_selection_log_metadata,
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
    parser.add_argument(
        "--required_candidate_field",
        action="append",
        default=[],
        help="Require a finite nonnegative candidate array in every record.",
    )
    parser.add_argument(
        "--reference_zero_candidate_field",
        action="append",
        default=[],
        help="Also require candidate 0 to be zero for this candidate field.",
    )
    parser.add_argument(
        "--forbid_seed",
        type=int,
        action="append",
        default=[],
        help="Reject selection logs whose benchmark path uses this seed.",
    )
    parser.add_argument(
        "--expected_comfort_shadow_horizon_steps",
        type=int,
        default=None,
        help=(
            "Require every record and completed-run summary to use this "
            "effective DP-prior comfort-shadow horizon."
        ),
    )
    parser.add_argument(
        "--closed_loop_outcome_policy",
        choices=("required", "optional", "forbidden"),
        default="required",
        help=(
            "Controls candidate_closed_loop_outcomes validation. Training and "
            "label audits should keep the default 'required'. Deployable "
            "latency audits should use 'forbidden' to certify that no collected "
            "counterfactual outcome payload was stored."
        ),
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
    required_candidate_fields: tuple[str, ...] = (),
    reference_zero_candidate_fields: tuple[str, ...] = (),
    forbidden_seeds: frozenset[int] = frozenset(),
    expected_comfort_shadow_horizon_steps: int | None = None,
    closed_loop_outcome_policy: str = "required",
) -> dict[str, Any]:
    scales = np.asarray(atom_scales, dtype=np.float64).reshape(-1)
    if scales.size == 0 or not np.all(np.isfinite(scales)) or np.any(scales <= 0.0):
        raise ValueError("atom_scales must contain finite positive values.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    if closed_loop_outcome_policy not in {"required", "optional", "forbidden"}:
        raise ValueError(
            "closed_loop_outcome_policy must be 'required', 'optional', "
            "or 'forbidden'."
        )
    if expected_comfort_shadow_horizon_steps is not None:
        if isinstance(expected_comfort_shadow_horizon_steps, bool) or not isinstance(
            expected_comfort_shadow_horizon_steps,
            (int, np.integer),
        ):
            raise ValueError(
                "expected_comfort_shadow_horizon_steps must be a positive "
                "integer."
            )
        if int(expected_comfort_shadow_horizon_steps) <= 0:
            raise ValueError(
                "expected_comfort_shadow_horizon_steps must be a positive "
                "integer."
            )
        expected_comfort_shadow_horizon_steps = int(
            expected_comfort_shadow_horizon_steps
        )
    required_fields = tuple(dict.fromkeys(required_candidate_fields))
    reference_zero_fields = tuple(dict.fromkeys(reference_zero_candidate_fields))
    unknown_reference_fields = set(reference_zero_fields) - set(required_fields)
    if unknown_reference_fields:
        raise ValueError(
            "reference_zero_candidate_fields must also be required fields: "
            f"{sorted(unknown_reference_fields)}."
        )
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
    outcome_records = 0
    outcome_candidates = 0
    candidate_field_reports = {
        field: {
            "records": 0,
            "candidates": 0,
            "records_with_variation": 0,
            "reference_zero_records": 0,
        }
        for field in required_fields
    }
    log_reports = []
    for log_path in log_paths:
        metadata = parse_selection_log_metadata(log_path)
        summary_path = log_path.with_name("camp_validation_summary.json")
        if not summary_path.is_file():
            raise ValueError(f"Missing completed-run summary for {log_path}.")
        validation_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(validation_summary, dict):
            raise ValueError(f"{summary_path} must contain a JSON object.")
        summary_seed = _validation_summary_seed(summary_path, validation_summary)
        if metadata.seed is not None and metadata.seed != summary_seed:
            raise ValueError(
                f"{summary_path} benchmark seed {summary_seed} does not match "
                f"selection-log path seed {metadata.seed}."
            )
        if summary_seed in forbidden_seeds:
            raise ValueError(
                f"{log_path} uses forbidden seed {summary_seed}."
            )
        advance_mode = validation_summary.get("advance_mode")
        if expected_advance_mode is not None and advance_mode != expected_advance_mode:
            raise ValueError(
                f"{summary_path} uses advance_mode={advance_mode!r}, "
                f"expected {expected_advance_mode!r}."
            )
        if expected_comfort_shadow_horizon_steps is not None:
            shadow_metadata = validation_summary.get(
                "camp_shadow_dp_prior_comfort_excess"
            )
            if (
                not isinstance(shadow_metadata, dict)
                or not _matches_expected_positive_integer(
                    shadow_metadata.get("effective_horizon_steps"),
                    expected_comfort_shadow_horizon_steps,
                )
            ):
                raise ValueError(
                    f"{summary_path} does not certify comfort-shadow horizon "
                    f"{expected_comfort_shadow_horizon_steps}."
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
            outcomes = _validate_closed_loop_outcomes(
                log_path,
                record_idx,
                record,
                expected_candidates=expected_candidates,
                policy=closed_loop_outcome_policy,
            )
            if red_atom_index is not None:
                _validate_red_light_provenance(
                    log_path,
                    record_idx,
                    record,
                    atoms[:, red_atom_index],
                    expected_candidates,
                )
            if expected_comfort_shadow_horizon_steps is not None:
                actual_horizon = record.get(
                    "candidate_dp_prior_comfort_excess_horizon_steps"
                )
                if not _matches_expected_positive_integer(
                    actual_horizon,
                    expected_comfort_shadow_horizon_steps,
                ):
                    raise ValueError(
                        f"{log_path} record {record_idx} uses comfort-shadow "
                        f"horizon {actual_horizon!r}, expected "
                        f"{expected_comfort_shadow_horizon_steps}."
                    )
            for field in required_fields:
                values = _validate_candidate_field(
                    log_path,
                    record_idx,
                    record,
                    field=field,
                    expected_candidates=expected_candidates,
                    require_reference_zero=field in reference_zero_fields,
                )
                field_report = candidate_field_reports[field]
                field_report["records"] += 1
                field_report["candidates"] += expected_candidates
                field_report["records_with_variation"] += int(
                    float(np.ptp(values)) > 1e-12
                )
                field_report["reference_zero_records"] += int(
                    abs(float(values[0])) <= 1e-12
                )

            total_records += 1
            total_candidates += expected_candidates
            outcome_records += int(len(outcomes) == expected_candidates)
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
                "seed": summary_seed,
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
            "closed_loop_outcome_policy": closed_loop_outcome_policy,
            "complete_closed_loop_outcomes": (
                outcome_candidates == total_candidates
            ),
            "closed_loop_outcomes_required": (
                closed_loop_outcome_policy == "required"
            ),
            "closed_loop_outcomes_forbidden": (
                closed_loop_outcome_policy == "forbidden"
            ),
            "closed_loop_outcome_records": outcome_records,
            "red_light_atom_matches_online_dp_reward": red_atom_index is not None,
            "outcome_candidate_coverage": (
                outcome_candidates / total_candidates if total_candidates else 0.0
            ),
            "expected_advance_mode": expected_advance_mode,
            "advance_mode_verified": expected_advance_mode is not None,
            "forbidden_seeds": sorted(forbidden_seeds),
            "forbidden_seed_check": bool(forbidden_seeds),
            "summary_seed_provenance_verified": True,
            "expected_comfort_shadow_horizon_steps": (
                expected_comfort_shadow_horizon_steps
            ),
            "comfort_shadow_horizon_verified": (
                expected_comfort_shadow_horizon_steps is not None
            ),
        },
        "candidate_fields": candidate_field_reports,
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


def _validate_closed_loop_outcomes(
    log_path: Path,
    record_idx: int,
    record: dict[str, Any],
    *,
    expected_candidates: int,
    policy: str,
) -> list[dict[str, Any]]:
    has_outcomes = "candidate_closed_loop_outcomes" in record
    outcomes = record.get("candidate_closed_loop_outcomes")
    if policy == "forbidden":
        if has_outcomes and outcomes is not None:
            raise ValueError(
                f"{log_path} record {record_idx} contains forbidden collected "
                "candidate_closed_loop_outcomes."
            )
        return []
    if not has_outcomes:
        if policy == "required":
            raise ValueError(
                f"{log_path} record {record_idx} has incomplete outcomes."
            )
        return []
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
    return outcomes


def _matches_expected_positive_integer(value: Any, expected: int) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
        and value == expected
    )


def _validation_summary_seed(
    summary_path: Path,
    validation_summary: dict[str, Any],
) -> int:
    benchmark = validation_summary.get("benchmark")
    seed = benchmark.get("seed") if isinstance(benchmark, dict) else None
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError(
            f"{summary_path} must contain an integer benchmark seed."
        )
    return seed


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


def _validate_candidate_field(
    log_path: Path,
    record_idx: int,
    record: dict[str, Any],
    *,
    field: str,
    expected_candidates: int,
    require_reference_zero: bool,
) -> np.ndarray:
    values = np.asarray(record.get(field), dtype=np.float64).reshape(-1)
    if values.shape != (expected_candidates,):
        raise ValueError(
            f"{log_path} record {record_idx} field {field!r} has shape "
            f"{values.shape}, expected ({expected_candidates},)."
        )
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError(
            f"{log_path} record {record_idx} field {field!r} must contain "
            "finite nonnegative values."
        )
    if require_reference_zero and abs(float(values[0])) > 1e-12:
        raise ValueError(
            f"{log_path} record {record_idx} field {field!r} candidate 0 "
            "must be zero."
        )
    return values


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
        required_candidate_fields=tuple(args.required_candidate_field),
        reference_zero_candidate_fields=tuple(
            args.reference_zero_candidate_field
        ),
        forbidden_seeds=frozenset(args.forbid_seed),
        expected_comfort_shadow_horizon_steps=(
            args.expected_comfort_shadow_horizon_steps
        ),
        closed_loop_outcome_policy=args.closed_loop_outcome_policy,
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
