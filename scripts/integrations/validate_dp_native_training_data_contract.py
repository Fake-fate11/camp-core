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

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402


PROVENANCE_SCHEMA_VERSION = "dp_native_candidate_tensor_provenance_payload_v1"
CANDIDATE_GENERATION_SCHEMA_VERSION = "dp_candidate_generation_contract_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate existing CAMP selection logs against the clean DP-native "
            "training-data contract. This tool is read-only and does not run "
            "replay, generate labels, train CAMP, or modify DP."
        )
    )
    parser.add_argument("--selection_log", type=Path, action="append", required=True)
    parser.add_argument("--output_json", type=Path, default=None)
    parser.add_argument("--output_md", type=Path, default=None)
    return parser.parse_args(argv)


def _records_from_path(path: Path) -> tuple[Path, list[dict[str, Any]]]:
    log_path = path / "camp_selection_log.json" if path.is_dir() else path
    if not log_path.is_file():
        raise FileNotFoundError(f"Selection log not found: {log_path}")
    records = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{log_path} must contain a JSON list.")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError(f"{log_path} must contain JSON object records.")
    return log_path, records


def _as_numeric_array(value: Any, *, field: str, errors: list[str]) -> np.ndarray:
    try:
        return np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        errors.append(f"{field}_not_numeric")
        return np.asarray([], dtype=np.float64)


def _is_false(value: Any) -> bool:
    return value is False


def _is_hex_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _validate_candidate_generation_contract(
    contract: Any,
    *,
    candidate_count: int,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(contract, dict):
        return ["candidate_generation_contract_missing"]
    if contract.get("schema_version") != CANDIDATE_GENERATION_SCHEMA_VERSION:
        errors.append("candidate_generation_contract_schema_mismatch")
    if int(contract.get("num_candidates", -1)) != int(candidate_count):
        errors.append("candidate_generation_contract_candidate_count_mismatch")
    if contract.get("noise_strategy") != "iid":
        errors.append("candidate_generation_contract_noise_strategy_not_iid")
    if contract.get("reference_blend_steps") is not None:
        errors.append("candidate_generation_contract_reference_blend_enabled")
    if bool(contract.get("guidance_enabled")):
        errors.append("candidate_generation_contract_guidance_enabled")
    if bool(contract.get("changes_diffusion_planner_weights")):
        errors.append("candidate_generation_contract_changes_dp_weights")
    return errors


def _validate_tensor_stage(stage: Any, *, field: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(stage, dict):
        return [f"{field}_missing"]
    if not _is_hex_sha256(stage.get("sha256")):
        errors.append(f"{field}_sha256_missing_or_invalid")
    shape = stage.get("shape")
    if (
        not isinstance(shape, list)
        or not shape
        or any(not isinstance(dim, int) or dim < 0 for dim in shape)
    ):
        errors.append(f"{field}_shape_invalid")
    if not isinstance(stage.get("dtype"), str) or not stage.get("dtype"):
        errors.append(f"{field}_dtype_missing")
    if stage.get("hash_input") != "contiguous_candidate_tensor_bytes":
        errors.append(f"{field}_hash_input_mismatch")
    if stage.get("nan_policy") != "preserve_tensor_bytes":
        errors.append(f"{field}_nan_policy_mismatch")
    return errors


def _validate_provenance_payload(
    payload: Any,
    *,
    candidate_count: int,
    selected_index: int,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["camp_candidate_tensor_provenance_missing"]
    if payload.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        errors.append("provenance_schema_mismatch")
    for field in (
        "selection_effect",
        "candidate_generation_effect",
        "candidate_tensor_mutation_effect",
        "candidate_generation_authorized",
        "trajectory_rewrite_authorized",
        "dp_modification_authorized",
        "outcome_label_input",
        "closed_loop_outcome_fields_read",
    ):
        if not _is_false(payload.get(field)):
            errors.append(f"provenance_{field}_not_false")
    for field in (
        "payload_valid",
        "pre_post_tensor_hash_equal",
        "selected_index_in_range",
        "no_candidate_row_append",
        "no_coordinate_heading_speed_rewrite_by_camp",
        "reference_blend_stage_hash_separated",
    ):
        if payload.get(field) is not True:
            errors.append(f"provenance_{field}_not_true")
    if int(payload.get("candidate_count", -1)) != int(candidate_count):
        errors.append("provenance_candidate_count_mismatch")
    if int(payload.get("post_selector_candidate_count", -1)) != int(candidate_count):
        errors.append("provenance_post_selector_candidate_count_mismatch")
    if int(payload.get("selected_index", -1)) != int(selected_index):
        errors.append("provenance_selected_index_mismatch")
    errors.extend(
        _validate_tensor_stage(
            payload.get("pre_camp_scoring_tensor"),
            field="pre_camp_scoring_tensor",
        )
    )
    errors.extend(
        _validate_tensor_stage(
            payload.get("post_camp_selector_tensor"),
            field="post_camp_selector_tensor",
        )
    )
    return errors


def _validate_outcome_labels(
    outcomes: Any,
    *,
    candidate_count: int,
) -> list[str]:
    if outcomes is None:
        return []
    if not isinstance(outcomes, list):
        return ["candidate_closed_loop_outcomes_not_list"]
    errors: list[str] = []
    if len(outcomes) != candidate_count:
        errors.append("candidate_closed_loop_outcomes_count_mismatch")
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, dict):
            errors.append(f"candidate_closed_loop_outcome_{index}_not_object")
            continue
        if outcome.get("candidate_index", index) != index:
            errors.append(f"candidate_closed_loop_outcome_{index}_index_mismatch")
    return errors


def validate_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    atoms = _as_numeric_array(record.get("atoms"), field="atoms", errors=errors)
    if atoms.ndim != 2:
        errors.append("atoms_shape_not_k_by_r")
        candidate_count = 0
        atom_dim = 0
    else:
        candidate_count = int(atoms.shape[0])
        atom_dim = int(atoms.shape[1])
        if candidate_count < 1:
            errors.append("candidate_count_empty")
        if not np.all(np.isfinite(atoms)):
            errors.append("atoms_not_finite")
        if np.any(atoms < 0.0):
            errors.append("atoms_negative")
    try:
        expected_version, expected_names = atom_schema_for_dimension(atom_dim)
    except ValueError:
        expected_version, expected_names = "", ()
        errors.append("atom_schema_dimension_not_approved")
    if record.get("atom_schema_version") != expected_version:
        errors.append("atom_schema_version_mismatch")
    if tuple(record.get("atom_names") or ()) != tuple(expected_names):
        errors.append("atom_names_mismatch")

    feasible = np.asarray(record.get("feasible_mask"), dtype=bool).reshape(-1)
    if feasible.shape != (candidate_count,):
        errors.append("feasible_mask_candidate_count_mismatch")

    try:
        selected_index = int(record.get("selected_index"))
    except (TypeError, ValueError):
        selected_index = -1
        errors.append("selected_index_not_int")
    if selected_index < 0 or selected_index >= candidate_count:
        errors.append("selected_index_out_of_range")

    errors.extend(
        _validate_candidate_generation_contract(
            record.get("candidate_generation_contract"),
            candidate_count=candidate_count,
        )
    )
    errors.extend(
        _validate_provenance_payload(
            record.get("camp_candidate_tensor_provenance"),
            candidate_count=candidate_count,
            selected_index=selected_index,
        )
    )
    errors.extend(
        _validate_outcome_labels(
            record.get("candidate_closed_loop_outcomes"),
            candidate_count=candidate_count,
        )
    )
    return errors


def validate_logs(paths: list[Path]) -> dict[str, Any]:
    record_count = 0
    failed_records: list[dict[str, Any]] = []
    loaded_logs: list[str] = []
    for path in paths:
        log_path, records = _records_from_path(path)
        loaded_logs.append(str(log_path))
        for record_index, record in enumerate(records):
            record_count += 1
            errors = validate_record(record)
            if errors:
                failed_records.append(
                    {
                        "log_path": str(log_path),
                        "record_index": int(record_index),
                        "errors": sorted(set(errors)),
                    }
                )
    passed = not failed_records and record_count > 0
    return {
        "schema_version": "clean_dp_native_training_data_contract_validator_v1",
        "selection_logs": loaded_logs,
        "records": int(record_count),
        "failed_records": failed_records,
        "passed": bool(passed),
        "read_only": True,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "future_training_input_contract_satisfied": bool(passed),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Clean DP Native Training Data Contract Validation",
        "",
        f"- Passed: `{report['passed']}`",
        f"- Records: `{report['records']}`",
        f"- Failed records: `{len(report['failed_records'])}`",
        f"- Replay executed: `{report['replay_executed']}`",
        f"- Candidate generation executed: `{report['candidate_generation_executed']}`",
        f"- Training execution authorized: `{report['training_execution_authorized']}`",
        "",
        "## Selection Logs",
        "",
    ]
    lines.extend(f"- `{path}`" for path in report["selection_logs"])
    if report["failed_records"]:
        lines.extend(["", "## Failed Records", ""])
        for row in report["failed_records"]:
            lines.append(
                f"- `{row['log_path']}` record `{row['record_index']}`: "
                + ", ".join(f"`{error}`" for error in row["errors"])
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_logs(args.selection_log)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
