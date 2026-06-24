#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension  # noqa: E402
from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_data import (  # noqa: E402
    COMPLETE_STATUS as BUILDER_COMPLETE_STATUS,
    DATASET_SCHEMA_VERSION,
)
from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    CANDIDATE_GENERATION_SCHEMA_VERSION,
    PROVENANCE_SCHEMA_VERSION,
)


VALIDATOR_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_validator_v1"
DISABLED_STATUS = "dp_native_fallback_risk_training_data_validator_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_data_validator_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_data_validator_rejected"

ALLOWED_ORACLE_POLICIES = (
    ("red", "lane", "quality"),
    ("lane", "red", "quality"),
    ("quality", "red", "lane"),
)

FORBIDDEN_FLAGS = (
    "replay_execution_authorized",
    "candidate_generation_authorized",
    "camp_training_authorized",
    "camp_retraining_authorized",
    "Full36_authorized",
    "formal_seeds_11_12_13_authorized",
    "dp_modification_authorized",
    "reference_blend_authorized",
    "guidance_authorized",
    "postprocess_postselection_authorized",
    "closed_loop_outcome_online_input_authorized",
    "selector_promotion_authorized",
    "atom_promotion_authorized",
    "deployable_checkpoint_claim_authorized",
    "safety_benefit_claim_authorized",
    "camp_over_dp_top1_claim_authorized",
    "production_selector_change_authorized",
    "online_selector_change_authorized",
    "feasible_ranking_master_change_authorized",
    "hard_feasibility_relaxation_authorized",
    "all_infeasible_records_added_to_feasible_training",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only validator for DP-native fallback-risk "
            "training dataset artifacts."
        )
    )
    parser.add_argument("--dataset_json", type=Path, required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_training_data_validator",
        action="store_true",
        help="Explicit opt-in required before reading the dataset JSON.",
    )
    parser.add_argument(
        "--no_source_log_readback",
        action="store_true",
        help=(
            "Diagnostic mode only. Acceptance requires source-log readback, so "
            "this flag makes the validator reject after structural checks."
        ),
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_fallback_risk_training_data(
        dataset_json=args.dataset_json,
        enabled=args.enable_default_off_fallback_risk_training_data_validator,
        source_log_readback=not args.no_source_log_readback,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def validate_fallback_risk_training_data(
    *,
    dataset_json: Path,
    enabled: bool = False,
    source_log_readback: bool = True,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": VALIDATOR_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_training_data_validator_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "read_only": True,
            "source_log_readback_required_for_acceptance": True,
            "source_log_readback_enabled": bool(source_log_readback),
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
        },
        "source_paths": {
            "dataset_json": str(dataset_json),
        },
        "source_hashes": {},
        "record_counts": {
            "records_checked": 0,
            "failed_records": 0,
        },
        "failed_records": [],
        "final_decision": _decision(
            status=DISABLED_STATUS,
            passed=True,
            enabled=False,
            errors=[],
        ),
    }
    if not enabled:
        return report

    errors: list[str] = []
    if not source_log_readback:
        errors.append("source_log_readback_required_for_acceptance")
    try:
        payload = json.loads(dataset_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"dataset_json_unreadable:{type(exc).__name__}")
        payload = {}
    if dataset_json.is_file():
        report["source_hashes"]["dataset_json"] = _sha256_file(dataset_json)
    if not isinstance(payload, dict):
        errors.append("dataset_payload_not_object")
        payload = {}

    errors.extend(_validate_top_level(payload, report))
    source_hashes = payload.get("source_hashes")
    if not isinstance(source_hashes, dict):
        source_hashes = {}
    records = payload.get("records")
    if isinstance(records, list):
        for record_index, record in enumerate(records):
            report["record_counts"]["records_checked"] += 1
            record_errors = _validate_record(
                record=record,
                source_hashes=source_hashes,
                source_log_readback=source_log_readback,
            )
            if record_errors:
                _add_failed(report, record_index, record_errors)
    report["record_counts"]["failed_records"] = len(report["failed_records"])
    errors.extend(
        f"record_{item['record_index']}:{error}"
        for item in report["failed_records"]
        for error in item["errors"]
    )
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def _validate_top_level(payload: dict[str, Any], report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("dataset_schema_version_mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
        errors.append("records_not_list")
        records = []
    counts = payload.get("record_counts")
    if not isinstance(counts, dict):
        errors.append("record_counts_missing")
        counts = {}
    if counts.get("records_built") != len(records):
        errors.append("records_built_count_mismatch")
    if counts.get("records_built") != counts.get("records_without_feasible_candidate"):
        errors.append("records_built_without_feasible_count_mismatch")
    if counts.get("failed_records") != 0:
        errors.append("builder_failed_records_nonzero")
    failed_records = payload.get("failed_records")
    if failed_records not in ([], None):
        errors.append("failed_records_nonempty")
    source_hashes = payload.get("source_hashes")
    if not isinstance(source_hashes, dict) or not source_hashes:
        errors.append("source_hashes_missing")
    elif isinstance(records, list):
        for record in records:
            if isinstance(record, dict) and record.get("source_log") not in source_hashes:
                errors.append("source_hash_missing_for_record")
                break
    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("final_decision_missing")
        decision = {}
    if decision.get("status") != BUILDER_COMPLETE_STATUS:
        errors.append("final_decision_status_invalid")
    if decision.get("passed") is not True:
        errors.append("final_decision_not_passed")
    if decision.get("enabled") is not True:
        errors.append("final_decision_not_enabled")
    if decision.get("errors") not in ([], None):
        errors.append("final_decision_errors_nonempty")
    for flag in FORBIDDEN_FLAGS + ("training_authorized",):
        if decision.get(flag) is not False:
            errors.append(f"final_decision_{flag}_not_false")
    return errors


def _validate_record(
    *,
    record: Any,
    source_hashes: dict[str, Any],
    source_log_readback: bool,
) -> list[str]:
    if not isinstance(record, dict):
        return ["record_not_object"]
    errors: list[str] = []
    if record.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("record_schema_version_mismatch")
    candidate_count = _strict_int(record.get("candidate_count"), "candidate_count", errors)
    if candidate_count is None or candidate_count < 1:
        errors.append("candidate_count_invalid")
        candidate_count = 0
    selected_index = _index(record.get("selected_index"), candidate_count, "selected_index", errors)
    _index(record.get("oracle_index"), candidate_count, "oracle_index", errors)
    oracle_policy = record.get("oracle_policy")
    if not isinstance(oracle_policy, list) or tuple(oracle_policy) not in ALLOWED_ORACLE_POLICIES:
        errors.append("oracle_policy_invalid")
    errors.extend(_validate_costs(record.get("costs"), candidate_count))
    errors.extend(_validate_numbers(record.get("margins"), candidate_count, "margins"))
    errors.extend(_validate_atoms(record, candidate_count, prefix="record"))
    if not _is_hex_sha(record.get("source_artifact_sha256")):
        errors.append("source_artifact_sha256_invalid")
    if "record_identity_hash" not in record:
        errors.append("record_identity_hash_missing")
    elif not _is_hex_sha(record.get("record_identity_hash")):
        errors.append("record_identity_hash_invalid")
    elif record.get("record_identity_hash") != _record_identity_hash(record):
        errors.append("record_identity_hash_mismatch")
    for field, expected in (
        ("training_authorized", False),
        ("selected_index_used_as_feature", False),
        ("candidate_rank_used_as_feature", False),
        ("fallback_label_is_not_a_deployed_atom", True),
    ):
        if record.get(field) is not expected:
            errors.append(f"{field}_invalid")
    if source_log_readback:
        errors.extend(
            _validate_source_readback(
                record=record,
                source_hashes=source_hashes,
                candidate_count=candidate_count,
                selected_index=selected_index,
            )
        )
    return errors


def _validate_source_readback(
    *,
    record: dict[str, Any],
    source_hashes: dict[str, Any],
    candidate_count: int,
    selected_index: int | None,
) -> list[str]:
    errors: list[str] = []
    source_log = record.get("source_log")
    source_sha = record.get("source_log_sha256")
    if not isinstance(source_log, str) or not source_log:
        return ["source_log_missing"]
    if not _is_hex_sha(source_sha):
        errors.append("source_log_sha256_invalid")
    source_path = Path(source_log)
    if not source_path.is_file():
        errors.append("source_log_missing_on_disk")
        return errors
    actual_sha = _sha256_file(source_path)
    if source_sha != actual_sha or source_hashes.get(source_log) != source_sha:
        errors.append("source_log_hash_mismatch")
    try:
        source_records = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append("source_log_unreadable")
        return errors
    if not isinstance(source_records, list):
        errors.append("source_log_not_list")
        return errors
    source_index = _strict_int(record.get("record_index"), "record_index", errors)
    if source_index is None or source_index < 0 or source_index >= len(source_records):
        errors.append("source_record_missing")
        return errors
    source_record = source_records[source_index]
    if not isinstance(source_record, dict):
        errors.append("source_record_not_object")
        return errors
    feasible = source_record.get("feasible_mask")
    if not isinstance(feasible, list) or not all(isinstance(item, bool) for item in feasible):
        errors.append("source_feasible_mask_non_bool")
    elif any(feasible):
        errors.append("source_feasible_mask_any_true")
    rewards = source_record.get("dp_candidate_rewards")
    if not isinstance(rewards, list) or len(rewards) != candidate_count:
        errors.append("source_candidate_count_mismatch")
    if source_record.get("selected_index") != selected_index:
        errors.append("source_selected_index_mismatch")
    errors.extend(_validate_generation(source_record.get("candidate_generation_contract"), candidate_count))
    errors.extend(
        _validate_provenance(
            source_record.get("camp_candidate_tensor_provenance"),
            candidate_count,
            selected_index,
        )
    )
    errors.extend(_validate_atoms(source_record, candidate_count, prefix="source"))
    return errors


def _validate_generation(contract: Any, candidate_count: int) -> list[str]:
    if not isinstance(contract, dict):
        return ["source_candidate_generation_contract_missing"]
    errors: list[str] = []
    if contract.get("schema_version") != CANDIDATE_GENERATION_SCHEMA_VERSION:
        errors.append("source_candidate_generation_schema_mismatch")
    if contract.get("num_candidates") != candidate_count:
        errors.append("source_candidate_generation_count_mismatch")
    if contract.get("reference_blend_steps") is not None:
        errors.append("source_reference_blend_enabled")
    if contract.get("guidance_enabled") is not False:
        errors.append("source_guidance_enabled")
    if contract.get("changes_diffusion_planner_weights") is not False:
        errors.append("source_dp_weight_change_enabled")
    return errors


def _validate_provenance(
    payload: Any,
    candidate_count: int,
    selected_index: int | None,
) -> list[str]:
    if not isinstance(payload, dict):
        return ["source_provenance_missing"]
    errors: list[str] = []
    if payload.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        errors.append("source_provenance_schema_mismatch")
    for field in (
        "payload_valid",
        "pre_post_tensor_hash_equal",
        "selected_index_in_range",
        "no_candidate_row_append",
        "no_coordinate_heading_speed_rewrite_by_camp",
    ):
        if payload.get(field) is not True:
            errors.append(f"source_provenance_{field}_not_true")
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
        if payload.get(field) is not False:
            errors.append(f"source_provenance_{field}_not_false")
    if payload.get("candidate_count") != candidate_count:
        errors.append("source_provenance_candidate_count_mismatch")
    if payload.get("post_selector_candidate_count") != candidate_count:
        errors.append("source_provenance_post_selector_candidate_count_mismatch")
    if payload.get("selected_index") != selected_index:
        errors.append("source_provenance_selected_index_mismatch")
    return errors


def _validate_atoms(record: dict[str, Any], candidate_count: int, *, prefix: str) -> list[str]:
    atoms = record.get("atoms")
    normalized = record.get("normalized_atoms")
    if not isinstance(atoms, list) or len(atoms) != candidate_count:
        return [f"{prefix}_atoms_candidate_count_mismatch"]
    atom_dim = len(atoms[0]) if atoms and isinstance(atoms[0], list) else 0
    errors: list[str] = []
    try:
        version, names = atom_schema_for_dimension(atom_dim)
    except ValueError:
        version, names = "", ()
        errors.append(f"{prefix}_atom_schema_dimension_not_approved")
    if record.get("atom_schema_version") != version:
        errors.append(f"{prefix}_atom_schema_version_mismatch")
    if tuple(record.get("atom_names") or ()) != tuple(names):
        errors.append(f"{prefix}_atom_names_mismatch")
    errors.extend(_validate_matrix(atoms, candidate_count, atom_dim, f"{prefix}_atoms"))
    errors.extend(_validate_matrix(normalized, candidate_count, atom_dim, f"{prefix}_normalized_atoms"))
    return errors


def _validate_costs(value: Any, candidate_count: int) -> list[str]:
    if not isinstance(value, list) or len(value) != candidate_count:
        return ["costs_count_mismatch"]
    errors: list[str] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, dict):
            errors.append(f"costs_{row_index}_not_object")
            continue
        for field in ("red", "lane", "quality"):
            errors.extend(_validate_number(row.get(field), f"costs_{row_index}_{field}"))
    return errors


def _validate_numbers(value: Any, count: int, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) != count:
        return [f"{field}_count_mismatch"]
    errors: list[str] = []
    for index, item in enumerate(value):
        errors.extend(_validate_number(item, f"{field}_{index}"))
    return errors


def _validate_number(value: Any, field: str) -> list[str]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return [f"{field}_not_numeric"]
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        return [f"{field}_not_finite_nonnegative"]
    return []


def _validate_matrix(value: Any, rows: int, cols: int, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) != rows:
        return [f"{field}_row_count_mismatch"]
    errors: list[str] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, list) or len(row) != cols:
            errors.append(f"{field}_{row_index}_shape_mismatch")
            continue
        for col_index, item in enumerate(row):
            errors.extend(_validate_number(item, f"{field}_{row_index}_{col_index}"))
    return errors


def _strict_int(value: Any, field: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{field}_not_int")
        return None
    return int(value)


def _index(value: Any, candidate_count: int, field: str, errors: list[str]) -> int | None:
    index = _strict_int(value, field, errors)
    if index is None:
        return None
    if index < 0 or index >= candidate_count:
        errors.append(f"{field}_out_of_range")
    return index


def _is_hex_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def _add_failed(report: dict[str, Any], record_index: int, errors: list[str]) -> None:
    report["failed_records"].append(
        {
            "record_index": int(record_index),
            "errors": sorted(set(errors)),
        }
    )


def _decision(
    *,
    status: str,
    passed: bool,
    enabled: bool,
    errors: list[str],
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "errors": sorted(set(errors)),
        "validator_output_written": bool(enabled and passed),
        "training_authorized": False,
        "fallback_dataset_training_sufficiency_claim": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record_identity_hash(record: dict[str, Any]) -> str:
    identity = {
        "source_log": record.get("source_log"),
        "source_log_sha256": record.get("source_log_sha256"),
        "run_id": record.get("run_id"),
        "record_index": record.get("record_index"),
    }
    return _sha256_text(json.dumps(identity, sort_keys=True, separators=(",", ":")))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["record_counts"]
    lines = [
        "# DP Native Fallback Risk Training Data Validation",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"records_checked={counts['records_checked']}",
        f"failed_records={counts['failed_records']}",
        "training_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "```",
        "",
        "This validator only reads an existing fallback-risk dataset and, for "
        "acceptance, its referenced source logs. It does not run replay, "
        "generate candidates, train CAMP, modify DP, promote a selector or "
        "atom, or claim safety benefit.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
