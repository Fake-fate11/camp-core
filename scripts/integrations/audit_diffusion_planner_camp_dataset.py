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
    select_perfect_tracker_command_dominating_candidate,
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

LEXICOGRAPHIC_STAGE_ORDER = (
    "progress",
    "planned_red",
    "jerk",
    "lateral",
)
LEXICOGRAPHIC_COUNT_ORDER = ("base",) + LEXICOGRAPHIC_STAGE_ORDER
PERFECT_TRACKER_COMMAND_METADATA = {
    "schema_version": "perfect_tracker_command_shadow_v2",
    "enabled": True,
    "selection_effect": False,
    "tracker_class": "scenario_generation.mpc_tracker.PerfectTracker",
    "reference_postprocessing": (
        "scenario_generation.mpc_tracker.postprocess_reference"
    ),
    "candidate_frame": "ego",
    "max_speed_mps": 20.0,
    "velocity_smooth_window": 8,
    "stop_threshold_mps": 0.3,
    "restart_speed_threshold_mps": 0.1,
    "restart_plan_speed_threshold_mps": 0.5,
    "fields": [
        "candidate_perfect_tracker_reference_first_xy",
        "candidate_perfect_tracker_reference_first_heading_rad",
        "candidate_perfect_tracker_first_step_reach_m",
        "candidate_perfect_tracker_tail_average_speed_mps",
        "candidate_perfect_tracker_restart_push",
        "candidate_perfect_tracker_target_speed_mps",
        "candidate_perfect_tracker_acceleration_mps2",
        "candidate_perfect_tracker_jerk_magnitude_mps3",
        "candidate_perfect_tracker_yaw_rate_magnitude_rps",
        "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2",
    ],
}
PERFECT_TRACKER_COMMAND_POSTSELECTION_METADATA = {
    "enabled": True,
    "selection_effect": True,
    "baseline": "camp_selected_index",
    "required_nonworse": [
        "base_feasibility",
        "perfect_tracker_target_speed",
        "dp_progress",
        "planned_red",
        "perfect_tracker_command_jerk",
        "perfect_tracker_command_lateral_acceleration",
    ],
    "required_strict_improvement": [
        "perfect_tracker_command_jerk",
        "perfect_tracker_command_lateral_acceleration",
    ],
    "order": [
        "perfect_tracker_command_jerk",
        "perfect_tracker_command_lateral_acceleration",
        "camp_score",
        "candidate_index",
    ],
    "epsilons": {
        "target_speed_mps": 0.0,
        "progress_m": 0.0,
        "planned_red": 0.0,
        "jerk_mps3": 0.0,
        "lateral_acceleration_mps2": 0.0,
    },
    "new_fallback_possible": False,
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
        "--expected_lateral_comfort_horizon_steps",
        type=int,
        default=None,
        help=(
            "Require every record and completed-run summary to use this "
            "effective lateral-comfort shadow horizon."
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
    parser.add_argument(
        "--expected_lexicographic_progress_epsilon_m",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--expected_lexicographic_red_epsilon",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--expected_lexicographic_jerk_epsilon",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--expected_lexicographic_lateral_epsilon",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--expected_candidate_reference_blend_steps",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--require_perfect_tracker_command_shadow",
        action="store_true",
        help=(
            "Require and independently recompute the outcome-free "
            "PerfectTracker command shadow in every record."
        ),
    )
    parser.add_argument(
        "--require_perfect_tracker_command_postselection",
        action="store_true",
        help=(
            "Require and independently recompute the nonempty "
            "PerfectTracker command postselection in every record."
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
    expected_lateral_comfort_horizon_steps: int | None = None,
    closed_loop_outcome_policy: str = "required",
    expected_lexicographic_preselection: dict[str, float] | None = None,
    expected_candidate_reference_blend_steps: int | None = None,
    require_perfect_tracker_command_shadow: bool = False,
    require_perfect_tracker_command_postselection: bool = False,
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
    expected_lexicographic = _validate_expected_lexicographic_config(
        expected_lexicographic_preselection
    )
    if expected_candidate_reference_blend_steps is not None:
        if (
            isinstance(expected_candidate_reference_blend_steps, bool)
            or not isinstance(
                expected_candidate_reference_blend_steps,
                (int, np.integer),
            )
            or int(expected_candidate_reference_blend_steps) < 1
        ):
            raise ValueError(
                "expected_candidate_reference_blend_steps must be a "
                "positive integer."
            )
        expected_candidate_reference_blend_steps = int(
            expected_candidate_reference_blend_steps
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
    if expected_lateral_comfort_horizon_steps is not None:
        if isinstance(expected_lateral_comfort_horizon_steps, bool) or not isinstance(
            expected_lateral_comfort_horizon_steps,
            (int, np.integer),
        ):
            raise ValueError(
                "expected_lateral_comfort_horizon_steps must be a positive "
                "integer."
            )
        if int(expected_lateral_comfort_horizon_steps) <= 0:
            raise ValueError(
                "expected_lateral_comfort_horizon_steps must be a positive "
                "integer."
            )
        expected_lateral_comfort_horizon_steps = int(
            expected_lateral_comfort_horizon_steps
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
    lexicographic_stage_records = 0
    perfect_tracker_command_records = 0
    perfect_tracker_command_postselection_records = 0
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
        if expected_lateral_comfort_horizon_steps is not None:
            shadow_metadata = validation_summary.get(
                "camp_shadow_lateral_comfort"
            )
            if (
                not isinstance(shadow_metadata, dict)
                or not _matches_expected_positive_integer(
                    shadow_metadata.get("effective_horizon_steps"),
                    expected_lateral_comfort_horizon_steps,
                )
            ):
                raise ValueError(
                    f"{summary_path} does not certify lateral-comfort shadow "
                    f"horizon {expected_lateral_comfort_horizon_steps}."
                )
        if expected_lexicographic is not None:
            _validate_lexicographic_summary(
                summary_path,
                validation_summary.get("camp_lexicographic_preselection"),
                expected_lexicographic,
            )
        if expected_candidate_reference_blend_steps is not None:
            _validate_candidate_reference_blend_summary(
                summary_path,
                validation_summary.get("candidate_reference_blend"),
                expected_candidate_reference_blend_steps,
            )
        perfect_tracker_preprocessing = None
        if (
            require_perfect_tracker_command_shadow
            or require_perfect_tracker_command_postselection
        ):
            if advance_mode != "perfect":
                raise ValueError(
                    f"{summary_path} uses advance_mode={advance_mode!r}; "
                    "PerfectTracker command shadow requires 'perfect'."
                )
            perfect_tracker_preprocessing = (
                _validate_perfect_tracker_command_summary(
                    summary_path,
                    validation_summary.get(
                        "camp_shadow_perfect_tracker_command"
                    ),
                )
            )
        if require_perfect_tracker_command_postselection:
            if advance_mode != "perfect":
                raise ValueError(
                    f"{summary_path} uses advance_mode={advance_mode!r}; "
                    "PerfectTracker command postselection requires 'perfect'."
                )
            _validate_perfect_tracker_command_postselection_summary(
                summary_path,
                validation_summary.get(
                    "camp_perfect_tracker_command_postselection"
                ),
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
            if expected_lateral_comfort_horizon_steps is not None:
                actual_horizon = record.get(
                    "candidate_lateral_comfort_horizon_steps"
                )
                if not _matches_expected_positive_integer(
                    actual_horizon,
                    expected_lateral_comfort_horizon_steps,
                ):
                    raise ValueError(
                        f"{log_path} record {record_idx} uses lateral-comfort "
                        f"shadow horizon {actual_horizon!r}, expected "
                        f"{expected_lateral_comfort_horizon_steps}."
                    )
            if expected_lexicographic is not None:
                _validate_lexicographic_stage_counts(
                    log_path,
                    record_idx,
                    record.get("lexicographic_stage_counts"),
                    expected_candidates=expected_candidates,
                    final_feasible_count=int(feasible.sum()),
                )
                lexicographic_stage_records += 1
            if expected_candidate_reference_blend_steps is not None:
                _validate_candidate_reference_blend_record(
                    log_path,
                    record_idx,
                    record,
                    expected_candidates=expected_candidates,
                    expected_steps=expected_candidate_reference_blend_steps,
                )
            if require_perfect_tracker_command_shadow:
                _validate_perfect_tracker_command_record(
                    log_path,
                    record_idx,
                    record,
                    expected_candidates=expected_candidates,
                    expected_preprocessing=perfect_tracker_preprocessing,
                )
                perfect_tracker_command_records += 1
            if require_perfect_tracker_command_postselection:
                if not require_perfect_tracker_command_shadow:
                    _validate_perfect_tracker_command_record(
                        log_path,
                        record_idx,
                        record,
                        expected_candidates=expected_candidates,
                        expected_preprocessing=perfect_tracker_preprocessing,
                    )
                _validate_perfect_tracker_command_postselection_record(
                    log_path,
                    record_idx,
                    record,
                    expected_candidates=expected_candidates,
                )
                perfect_tracker_command_postselection_records += 1
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
            "expected_lateral_comfort_horizon_steps": (
                expected_lateral_comfort_horizon_steps
            ),
            "lateral_comfort_horizon_verified": (
                expected_lateral_comfort_horizon_steps is not None
            ),
            "expected_lexicographic_preselection": expected_lexicographic,
            "lexicographic_preselection_verified": (
                expected_lexicographic is not None
            ),
            "lexicographic_stage_records": lexicographic_stage_records,
            "expected_candidate_reference_blend_steps": (
                expected_candidate_reference_blend_steps
            ),
            "candidate_reference_blend_verified": (
                expected_candidate_reference_blend_steps is not None
            ),
            "perfect_tracker_command_shadow_required": (
                require_perfect_tracker_command_shadow
            ),
            "perfect_tracker_command_shadow_verified": (
                require_perfect_tracker_command_shadow
            ),
            "perfect_tracker_command_records": perfect_tracker_command_records,
            "perfect_tracker_command_postselection_required": (
                require_perfect_tracker_command_postselection
            ),
            "perfect_tracker_command_postselection_verified": (
                require_perfect_tracker_command_postselection
            ),
            "perfect_tracker_command_postselection_records": (
                perfect_tracker_command_postselection_records
            ),
        },
        "candidate_fields": candidate_field_reports,
        "logs": log_reports,
    }


def _validate_expected_lexicographic_config(
    config: dict[str, float] | None,
) -> dict[str, float] | None:
    if config is None:
        return None
    expected_keys = {
        "progress_epsilon_m",
        "planned_red_epsilon",
        "jerk_epsilon",
        "lateral_epsilon",
    }
    if not isinstance(config, dict) or set(config) != expected_keys:
        raise ValueError(
            "expected_lexicographic_preselection must contain exactly "
            f"{sorted(expected_keys)}."
        )
    normalized = {}
    for key in sorted(expected_keys):
        value = config[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float, np.integer, np.floating))
            or not np.isfinite(value)
            or value < 0.0
        ):
            raise ValueError(
                "Expected lexicographic epsilons must be finite and nonnegative."
            )
        normalized[key] = float(value)
    return normalized


def _validate_lexicographic_summary(
    summary_path: Path,
    metadata: Any,
    expected: dict[str, float],
) -> None:
    if not isinstance(metadata, dict):
        raise ValueError(
            f"{summary_path} does not certify lexicographic preselection."
        )
    if (
        metadata.get("enabled") is not True
        or metadata.get("selection_effect") is not True
        or metadata.get("order") != list(LEXICOGRAPHIC_STAGE_ORDER)
    ):
        raise ValueError(
            f"{summary_path} has invalid lexicographic preselection metadata."
        )
    for key, expected_value in expected.items():
        actual = metadata.get(key)
        if (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or not np.isfinite(actual)
            or not np.isclose(
                float(actual),
                expected_value,
                atol=1e-12,
                rtol=1e-12,
            )
        ):
            raise ValueError(
                f"{summary_path} lexicographic {key}={actual!r}, "
                f"expected {expected_value!r}."
            )


def _validate_lexicographic_stage_counts(
    log_path: Path,
    record_idx: int,
    counts: Any,
    *,
    expected_candidates: int,
    final_feasible_count: int,
) -> None:
    if not isinstance(counts, dict) or set(counts) != set(
        LEXICOGRAPHIC_COUNT_ORDER
    ):
        raise ValueError(
            f"{log_path} record {record_idx} has invalid lexicographic "
            "stage-count fields."
        )
    ordered_counts = []
    for stage in LEXICOGRAPHIC_COUNT_ORDER:
        value = counts[stage]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, np.integer))
            or not 0 <= int(value) <= expected_candidates
        ):
            raise ValueError(
                f"{log_path} record {record_idx} has invalid lexicographic "
                f"{stage} count {value!r}."
            )
        ordered_counts.append(int(value))
    if any(
        next_count > current_count
        for current_count, next_count in zip(
            ordered_counts,
            ordered_counts[1:],
        )
    ):
        raise ValueError(
            f"{log_path} record {record_idx} lexicographic stage counts "
            "must be monotonically nonincreasing."
        )
    base_count = ordered_counts[0]
    if base_count == 0 and any(ordered_counts[1:]):
        raise ValueError(
            f"{log_path} record {record_idx} has candidates after an empty "
            "lexicographic base set."
        )
    if base_count > 0 and any(count < 1 for count in ordered_counts[1:]):
        raise ValueError(
            f"{log_path} record {record_idx} lexicographic preselection "
            "emptied a nonempty base set."
        )
    if final_feasible_count > ordered_counts[-1]:
        raise ValueError(
            f"{log_path} record {record_idx} final feasible count exceeds "
            "the lexicographic lateral-stage count."
        )


def _validate_candidate_reference_blend_summary(
    summary_path: Path,
    metadata: Any,
    expected_steps: int,
) -> None:
    expected = {
        "enabled": True,
        "steps": expected_steps,
        "reference_candidate_index": 0,
        "weight_definition": "min(t / steps, 1)",
        "first_reference_xy_preserved": True,
        "selection_effect": True,
    }
    if not isinstance(metadata, dict) or metadata != expected:
        raise ValueError(
            f"{summary_path} does not certify candidate reference blend "
            f"steps={expected_steps}."
        )


def _validate_candidate_reference_blend_record(
    log_path: Path,
    record_idx: int,
    record: dict[str, Any],
    *,
    expected_candidates: int,
    expected_steps: int,
) -> None:
    if record.get("candidate_reference_blend_steps") != expected_steps:
        raise ValueError(
            f"{log_path} record {record_idx} does not use candidate "
            f"reference blend steps={expected_steps}."
        )
    first_xy = np.asarray(
        record.get("candidate_first_reference_xy"),
        dtype=np.float64,
    )
    if (
        first_xy.shape != (expected_candidates, 2)
        or not np.all(np.isfinite(first_xy))
        or not np.allclose(
            first_xy,
            first_xy[0:1],
            atol=1e-12,
            rtol=1e-12,
        )
    ):
        raise ValueError(
            f"{log_path} record {record_idx} does not preserve candidate "
            "first-reference xy."
        )
    step_reach = np.asarray(
        record.get("candidate_step_reach"),
        dtype=np.float64,
    ).reshape(-1)
    if (
        step_reach.shape != (expected_candidates,)
        or not np.all(np.isfinite(step_reach))
        or np.any(step_reach < 0.0)
        or not np.allclose(
            step_reach,
            step_reach[0],
            atol=1e-12,
            rtol=1e-12,
        )
    ):
        raise ValueError(
            f"{log_path} record {record_idx} does not preserve candidate "
            "step reach."
        )


def _validate_perfect_tracker_command_summary(
    summary_path: Path,
    metadata: Any,
) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        raise ValueError(
            f"{summary_path} does not certify the expected PerfectTracker "
            "command shadow."
        )
    preprocessing = metadata.get("candidate_preprocessing")
    metadata_without_preprocessing = dict(metadata)
    metadata_without_preprocessing.pop("candidate_preprocessing", None)
    if metadata_without_preprocessing != PERFECT_TRACKER_COMMAND_METADATA:
        raise ValueError(
            f"{summary_path} does not certify the expected PerfectTracker "
            "command shadow."
        )
    return _validate_perfect_tracker_candidate_preprocessing(
        preprocessing,
        label=f"{summary_path} PerfectTracker candidate preprocessing",
    )


def _validate_perfect_tracker_candidate_preprocessing(
    preprocessing: Any,
    *,
    label: str,
) -> dict[str, Any]:
    expected_keys = {
        "reference_implementation",
        "shadow_implementation",
        "application_stage",
        "savgol_enabled",
        "savgol_window",
        "savgol_order",
    }
    if not isinstance(preprocessing, dict) or set(preprocessing) != expected_keys:
        raise ValueError(f"{label} is invalid.")
    if (
        preprocessing["reference_implementation"]
        != "rlvr.grpo_sft_trainer._smooth_trajectory"
        or preprocessing["shadow_implementation"]
        != (
            "scripts.integrations.run_diffusion_planner_camp_replay."
            "_prepare_perfect_tracker_reference_candidates"
        )
        or preprocessing["application_stage"]
        != "replay_after_predict_before_advance_scene_mpc"
        or not isinstance(preprocessing["savgol_enabled"], bool)
    ):
        raise ValueError(f"{label} is invalid.")
    if preprocessing["savgol_enabled"]:
        window = preprocessing["savgol_window"]
        order = preprocessing["savgol_order"]
        if (
            isinstance(window, bool)
            or not isinstance(window, int)
            or window < 3
            or window % 2 == 0
            or isinstance(order, bool)
            or not isinstance(order, int)
            or order < 0
            or order + 2 > window
        ):
            raise ValueError(f"{label} has invalid Savitzky-Golay settings.")
    elif (
        preprocessing["savgol_window"] is not None
        or preprocessing["savgol_order"] is not None
    ):
        raise ValueError(f"{label} must omit disabled Savitzky-Golay settings.")
    return dict(preprocessing)


def _validate_perfect_tracker_command_postselection_summary(
    summary_path: Path,
    metadata: Any,
) -> None:
    if metadata != PERFECT_TRACKER_COMMAND_POSTSELECTION_METADATA:
        raise ValueError(
            f"{summary_path} does not certify the expected PerfectTracker "
            "command postselection."
        )


def _validate_perfect_tracker_command_postselection_record(
    log_path: Path,
    record_idx: int,
    record: dict[str, Any],
    *,
    expected_candidates: int,
) -> None:
    label = f"{log_path} record {record_idx} PerfectTracker postselection"
    feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
    if feasible.shape != (expected_candidates,):
        raise ValueError(f"{label} has invalid feasible_mask.")
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != expected_candidates:
        raise ValueError(f"{label} lacks complete DP rewards.")
    progress = np.asarray(
        [float(reward["progress"]) for reward in rewards],
        dtype=np.float64,
    )
    planned_red = np.asarray(
        [
            max(-float(reward.get("red_light", 0.0)), 0.0)
            for reward in rewards
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(progress)) or not np.all(
        np.isfinite(planned_red)
    ):
        raise ValueError(f"{label} has invalid DP reward fields.")
    baseline = record.get("camp_selected_index_before_tracker_postselection")
    final = record.get("selected_index")
    if (
        isinstance(baseline, bool)
        or not isinstance(baseline, int)
        or isinstance(final, bool)
        or not isinstance(final, int)
    ):
        raise ValueError(f"{label} has invalid selected indices.")
    expected_final, expected_stats = (
        select_perfect_tracker_command_dominating_candidate(
            baseline_selected_index=baseline,
            feasible_mask=feasible,
            selection_scores=np.asarray(
                record.get("selection_scores"),
                dtype=np.float64,
            ),
            candidate_progress=progress,
            candidate_planned_red_light_cost=planned_red,
            candidate_target_speed_mps=_finite_candidate_vector(
                record.get("candidate_perfect_tracker_target_speed_mps"),
                expected_candidates,
                label=f"{label} target speed",
                nonnegative=True,
            ),
            candidate_jerk_magnitude_mps3=_finite_candidate_vector(
                record.get(
                    "candidate_perfect_tracker_jerk_magnitude_mps3"
                ),
                expected_candidates,
                label=f"{label} jerk",
                nonnegative=True,
            ),
            candidate_lateral_acceleration_magnitude_mps2=(
                _finite_candidate_vector(
                    record.get(
                        "candidate_perfect_tracker_"
                        "lateral_acceleration_magnitude_mps2"
                    ),
                    expected_candidates,
                    label=f"{label} lateral acceleration",
                    nonnegative=True,
                )
            ),
        )
    )
    if final != expected_final:
        raise ValueError(f"{label} selected index does not match its formula.")
    if record.get("perfect_tracker_command_postselection") != expected_stats:
        raise ValueError(f"{label} stage statistics do not match their formula.")


def _validate_perfect_tracker_command_record(
    log_path: Path,
    record_idx: int,
    record: dict[str, Any],
    *,
    expected_candidates: int,
    expected_preprocessing: dict[str, Any] | None,
) -> None:
    label = f"{log_path} record {record_idx} PerfectTracker command shadow"
    if expected_preprocessing is None:
        raise ValueError(f"{label} lacks certified candidate preprocessing.")
    record_preprocessing = _validate_perfect_tracker_candidate_preprocessing(
        record.get("perfect_tracker_candidate_preprocessing"),
        label=f"{label} candidate preprocessing",
    )
    if record_preprocessing != expected_preprocessing:
        raise ValueError(
            f"{label} candidate preprocessing does not match its summary."
        )
    inputs = record.get("perfect_tracker_command_inputs")
    expected_input_keys = {
        "dt",
        "current_speed_mps",
        "current_longitudinal_acceleration_mps2",
        "max_speed_mps",
        "velocity_smooth_window",
        "stop_threshold_mps",
        "restart_speed_threshold_mps",
        "restart_plan_speed_threshold_mps",
    }
    if not isinstance(inputs, dict) or set(inputs) != expected_input_keys:
        raise ValueError(f"{label} has invalid command inputs.")
    numeric_inputs = {
        key: float(value)
        for key, value in inputs.items()
        if key != "velocity_smooth_window"
    }
    if not all(np.isfinite(value) for value in numeric_inputs.values()):
        raise ValueError(f"{label} has nonfinite command inputs.")
    if inputs["velocity_smooth_window"] != 8:
        raise ValueError(f"{label} has an invalid velocity smoothing window.")
    expected_constants = {
        "max_speed_mps": 20.0,
        "stop_threshold_mps": 0.3,
        "restart_speed_threshold_mps": 0.1,
        "restart_plan_speed_threshold_mps": 0.5,
    }
    for key, expected in expected_constants.items():
        if numeric_inputs[key] != expected:
            raise ValueError(f"{label} has invalid {key}.")
    dt = numeric_inputs["dt"]
    current_speed = numeric_inputs["current_speed_mps"]
    current_acceleration = numeric_inputs[
        "current_longitudinal_acceleration_mps2"
    ]
    if dt <= 0.0 or current_speed < 0.0:
        raise ValueError(f"{label} has an invalid dt or current speed.")

    first_xy = _finite_candidate_matrix(
        record.get("candidate_perfect_tracker_reference_first_xy"),
        expected_candidates,
        2,
        label=f"{label} first-reference xy",
    )
    tail_xy = _finite_candidate_matrix(
        record.get("candidate_perfect_tracker_postprocessed_tail_xy"),
        expected_candidates,
        2,
        label=f"{label} postprocessed-tail xy",
    )
    first_heading = _finite_candidate_vector(
        record.get(
            "candidate_perfect_tracker_reference_first_heading_rad"
        ),
        expected_candidates,
        label=f"{label} first-reference heading",
    )
    tail_average_speed = _finite_candidate_vector(
        record.get("candidate_perfect_tracker_tail_average_speed_mps"),
        expected_candidates,
        label=f"{label} tail-average speed",
        nonnegative=True,
    )
    target_speed = _finite_candidate_vector(
        record.get("candidate_perfect_tracker_target_speed_mps"),
        expected_candidates,
        label=f"{label} target speed",
        nonnegative=True,
    )
    acceleration = _finite_candidate_vector(
        record.get("candidate_perfect_tracker_acceleration_mps2"),
        expected_candidates,
        label=f"{label} acceleration",
    )
    jerk = _finite_candidate_vector(
        record.get("candidate_perfect_tracker_jerk_magnitude_mps3"),
        expected_candidates,
        label=f"{label} jerk magnitude",
        nonnegative=True,
    )
    yaw_rate = _finite_candidate_vector(
        record.get("candidate_perfect_tracker_yaw_rate_magnitude_rps"),
        expected_candidates,
        label=f"{label} yaw-rate magnitude",
        nonnegative=True,
    )
    lateral_acceleration = _finite_candidate_vector(
        record.get(
            "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2"
        ),
        expected_candidates,
        label=f"{label} lateral-acceleration magnitude",
        nonnegative=True,
    )
    restart_values = record.get("candidate_perfect_tracker_restart_push")
    if (
        not isinstance(restart_values, list)
        or len(restart_values) != expected_candidates
        or any(not isinstance(value, bool) for value in restart_values)
    ):
        raise ValueError(f"{label} has invalid restart flags.")
    restart_push = np.asarray(restart_values, dtype=bool)

    expected_step_reach = np.linalg.norm(first_xy, axis=1)
    logged_step_reach = _finite_candidate_vector(
        record.get("candidate_perfect_tracker_first_step_reach_m"),
        expected_candidates,
        label=f"{label} tracker first-step reach",
        nonnegative=True,
    )
    expected_tail_average_speed = np.linalg.norm(
        tail_xy,
        axis=1,
    ) / _record_horizon_time(record, dt)
    expected_restart = (
        current_speed < numeric_inputs["restart_speed_threshold_mps"]
    ) & (
        expected_tail_average_speed
        > numeric_inputs["restart_plan_speed_threshold_mps"]
    )
    expected_target = np.minimum(
        expected_step_reach / dt,
        numeric_inputs["max_speed_mps"],
    )
    expected_target[expected_restart] = np.maximum(
        expected_target[expected_restart],
        np.minimum(
            numeric_inputs["max_speed_mps"],
            expected_tail_average_speed[expected_restart],
        ),
    )
    expected_acceleration = (expected_target - current_speed) / dt
    expected_jerk = np.abs(expected_acceleration - current_acceleration) / dt
    wrapped_heading = np.arctan2(
        np.sin(first_heading),
        np.cos(first_heading),
    )
    expected_yaw_rate = np.abs(wrapped_heading) / dt
    expected_lateral_acceleration = expected_target * expected_yaw_rate

    checks = (
        ("first-step reach", logged_step_reach, expected_step_reach),
        ("tail-average speed", tail_average_speed, expected_tail_average_speed),
        ("target speed", target_speed, expected_target),
        ("acceleration", acceleration, expected_acceleration),
        ("jerk magnitude", jerk, expected_jerk),
        ("yaw-rate magnitude", yaw_rate, expected_yaw_rate),
        (
            "lateral-acceleration magnitude",
            lateral_acceleration,
            expected_lateral_acceleration,
        ),
    )
    for name, actual, expected in checks:
        if not np.allclose(actual, expected, atol=1e-9, rtol=1e-9):
            raise ValueError(f"{label} {name} does not match its formula.")
    if not np.array_equal(restart_push, expected_restart):
        raise ValueError(f"{label} restart flags do not match their formula.")


def _record_horizon_time(record: dict[str, Any], dt: float) -> float:
    horizon_steps = record.get("candidate_trajectory_horizon_steps")
    if (
        isinstance(horizon_steps, bool)
        or not isinstance(horizon_steps, (int, np.integer))
        or int(horizon_steps) < 1
    ):
        raise ValueError(
            "PerfectTracker command shadow requires a positive "
            "candidate_trajectory_horizon_steps."
        )
    return int(horizon_steps) * dt


def _finite_candidate_vector(
    values: Any,
    expected_candidates: int,
    *,
    label: str,
    nonnegative: bool = False,
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if (
        array.shape != (expected_candidates,)
        or not np.all(np.isfinite(array))
        or (nonnegative and np.any(array < 0.0))
    ):
        raise ValueError(f"{label} is invalid.")
    return array


def _finite_candidate_matrix(
    values: Any,
    expected_candidates: int,
    width: int,
    *,
    label: str,
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if (
        array.shape != (expected_candidates, width)
        or not np.all(np.isfinite(array))
    ):
        raise ValueError(f"{label} is invalid.")
    return array


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
    lexicographic_values = (
        args.expected_lexicographic_progress_epsilon_m,
        args.expected_lexicographic_red_epsilon,
        args.expected_lexicographic_jerk_epsilon,
        args.expected_lexicographic_lateral_epsilon,
    )
    if any(value is not None for value in lexicographic_values) and any(
        value is None for value in lexicographic_values
    ):
        raise ValueError(
            "All expected lexicographic epsilon arguments must be provided "
            "together."
        )
    expected_lexicographic = (
        {
            "progress_epsilon_m": args.expected_lexicographic_progress_epsilon_m,
            "planned_red_epsilon": args.expected_lexicographic_red_epsilon,
            "jerk_epsilon": args.expected_lexicographic_jerk_epsilon,
            "lateral_epsilon": args.expected_lexicographic_lateral_epsilon,
        }
        if all(value is not None for value in lexicographic_values)
        else None
    )
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
        expected_lateral_comfort_horizon_steps=(
            args.expected_lateral_comfort_horizon_steps
        ),
        closed_loop_outcome_policy=args.closed_loop_outcome_policy,
        expected_lexicographic_preselection=expected_lexicographic,
        expected_candidate_reference_blend_steps=(
            args.expected_candidate_reference_blend_steps
        ),
        require_perfect_tracker_command_shadow=(
            args.require_perfect_tracker_command_shadow
        ),
        require_perfect_tracker_command_postselection=(
            args.require_perfect_tracker_command_postselection
        ),
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
