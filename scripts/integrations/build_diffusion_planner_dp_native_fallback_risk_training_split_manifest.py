#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
SPLIT_MANIFEST_SCHEMA_VERSION = "dp_native_fallback_risk_training_split_manifest_v1"
DISABLED_STATUS = "dp_native_fallback_risk_training_split_manifest_builder_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_split_manifest_builder_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_split_manifest_builder_rejected"
SPLIT_POLICY = "sha256(record_identity_hash + split_salt)"
SPLIT_SALT = "fallback_risk_training_split_v1"
VALIDATION_FRACTION_TARGET = 0.2
GROUP_KEY_FIELDS = ("source_log", "run_id", "record_index")
FORMAL_SEEDS = {11, 12, 13}

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
    "fallback_risk_training_authorized_now",
    "feasible_ranking_master_change_authorized",
    "hard_feasibility_relaxation_authorized",
    "all_infeasible_records_added_to_feasible_training",
    "production_selector_change_authorized",
    "online_selector_change_authorized",
)
FORBIDDEN_SPLIT_FEATURE_FLAGS = (
    "selected_index_used_as_feature",
    "candidate_rank_used_as_feature",
    "closed_loop_outcome_used_as_feature",
    "learned_weights_used_as_feature",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only builder for DP-native fallback-risk "
            "training split manifests."
        )
    )
    parser.add_argument("--dataset_json", type=Path, required=True)
    parser.add_argument("--expected_dataset_sha256", required=True)
    parser.add_argument("--validator_output_sha256", required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_training_split_manifest_builder",
        action="store_true",
        help="Explicit opt-in required before reading the dataset JSON.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_split_manifest_report(
        dataset_json=args.dataset_json,
        expected_dataset_sha256=args.expected_dataset_sha256,
        validator_output_sha256=args.validator_output_sha256,
        enabled=args.enable_default_off_fallback_risk_training_split_manifest_builder,
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


def build_split_manifest_report(
    *,
    dataset_json: Path,
    expected_dataset_sha256: str,
    validator_output_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SPLIT_MANIFEST_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_training_split_manifest_builder_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "read_only": True,
            "records_scope": "records_without_feasible_candidate_only",
            "split_policy": SPLIT_POLICY,
            "validation_fraction_target": VALIDATION_FRACTION_TARGET,
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
        "dataset_sha256": None,
        "validator_output_sha256": validator_output_sha256,
        "split_policy": SPLIT_POLICY,
        "split_salt": SPLIT_SALT,
        "validation_fraction_target": VALIDATION_FRACTION_TARGET,
        "group_key_fields": list(GROUP_KEY_FIELDS),
        "training_groups": [],
        "validation_groups": [],
        "record_assignments": [],
        "record_counts": {
            "accepted_records": 0,
            "training_records": 0,
            "validation_records": 0,
        },
        "seeds": [],
        "formal_eval_artifact_included": False,
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
    _validate_sha_literal(expected_dataset_sha256, "expected_dataset_sha256", errors)
    _validate_sha_literal(validator_output_sha256, "validator_output_sha256", errors)
    payload = _load_dataset(dataset_json, errors)
    if dataset_json.is_file():
        dataset_sha256 = _sha256_file(dataset_json)
        report["source_hashes"]["dataset_json"] = dataset_sha256
        report["dataset_sha256"] = dataset_sha256
        if _is_sha256(expected_dataset_sha256) and dataset_sha256 != expected_dataset_sha256:
            errors.append("dataset_sha256_mismatch")
    records = _validate_dataset_payload(payload, errors)
    if not errors:
        assignments = [_assignment(record) for record in records]
        training = sorted(
            item["group_id"] for item in assignments if item["split"] == "training"
        )
        validation = sorted(
            item["group_id"] for item in assignments if item["split"] == "validation"
        )
        if not training or not validation:
            errors.append("split_train_or_validation_empty")
        report["training_groups"] = training
        report["validation_groups"] = validation
        report["record_assignments"] = sorted(
            assignments,
            key=lambda item: item["record_identity_hash"],
        )
        report["record_counts"] = {
            "accepted_records": len(assignments),
            "training_records": len(training),
            "validation_records": len(validation),
        }

    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def _load_dataset(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"dataset_json_unreadable:{type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        errors.append("dataset_payload_not_object")
        return {}
    return payload


def _validate_dataset_payload(
    payload: dict[str, Any],
    errors: list[str],
) -> list[dict[str, Any]]:
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
    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("final_decision_missing")
        decision = {}
    if decision.get("passed") is not True:
        errors.append("final_decision_not_passed")
    if decision.get("enabled") is not True:
        errors.append("final_decision_not_enabled")
    if decision.get("errors") not in ([], None):
        errors.append("final_decision_errors_nonempty")
    for flag in FORBIDDEN_FLAGS + ("training_authorized",):
        if decision.get(flag) is not False:
            errors.append(f"final_decision_{flag}_not_false")

    source_hashes = payload.get("source_hashes")
    if not isinstance(source_hashes, dict) or not source_hashes:
        errors.append("source_hashes_missing")
        source_hashes = {}
    seen_group_keys: set[tuple[Any, ...]] = set()
    seen_hashes: set[str] = set()
    valid_records: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record_{index}:record_not_object")
            continue
        record_errors = _validate_record(
            record=record,
            source_hashes=source_hashes,
            seen_group_keys=seen_group_keys,
            seen_hashes=seen_hashes,
        )
        errors.extend(f"record_{index}:{error}" for error in record_errors)
        valid_records.append(record)
    return valid_records


def _validate_record(
    *,
    record: dict[str, Any],
    source_hashes: dict[str, Any],
    seen_group_keys: set[tuple[Any, ...]],
    seen_hashes: set[str],
) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("record_schema_version_mismatch")
    for field in (
        "source_log",
        "source_log_sha256",
        "run_id",
        "record_index",
        "candidate_count",
        "oracle_index",
    ):
        if field not in record:
            errors.append(f"{field}_missing")
    source_log = record.get("source_log")
    source_log_sha = record.get("source_log_sha256")
    if not isinstance(source_log, str) or not source_log:
        errors.append("source_log_invalid")
    elif source_hashes.get(source_log) != source_log_sha:
        errors.append("source_log_sha256_mismatch")
    if not _is_sha256(source_log_sha):
        errors.append("source_log_sha256_invalid")
    record_index = _strict_int(record.get("record_index"), "record_index", errors)
    candidate_count = _strict_int(record.get("candidate_count"), "candidate_count", errors)
    oracle_index = _strict_int(record.get("oracle_index"), "oracle_index", errors)
    if candidate_count is None or candidate_count < 1:
        errors.append("candidate_count_invalid")
        candidate_count = 0
    if oracle_index is None or oracle_index < 0 or oracle_index >= candidate_count:
        errors.append("oracle_index_invalid")
    group_key = tuple(record.get(field) for field in GROUP_KEY_FIELDS)
    if group_key in seen_group_keys:
        errors.append("group_key_collision")
    seen_group_keys.add(group_key)
    identity_hash = _record_identity_hash(record)
    if identity_hash in seen_hashes:
        errors.append("duplicate_record_identity")
    seen_hashes.add(identity_hash)
    if record.get("record_identity_hash") not in (None, identity_hash):
        errors.append("record_identity_hash_mismatch")
    for flag in FORBIDDEN_SPLIT_FEATURE_FLAGS:
        if record.get(flag) not in (None, False):
            errors.append(f"{flag}_leak")
    if record.get("training_authorized") is not False:
        errors.append("training_authorized_leak")
    if record.get("seed") in FORMAL_SEEDS:
        errors.append("formal_seed_in_split_manifest")
    if record.get("formal_eval_artifact_included") is not False and "formal_eval_artifact_included" in record:
        errors.append("formal_eval_artifact_record_included")
    if record_index is None:
        errors.append("record_index_invalid")
    return errors


def _assignment(record: dict[str, Any]) -> dict[str, Any]:
    identity_hash = _record_identity_hash(record)
    split_hash = _sha256_text(identity_hash + SPLIT_SALT)
    split_score = int(split_hash, 16) / float(1 << 256)
    split = "validation" if split_score < VALIDATION_FRACTION_TARGET else "training"
    return {
        "source_log": record["source_log"],
        "source_log_sha256": record["source_log_sha256"],
        "run_id": record["run_id"],
        "record_index": record["record_index"],
        "candidate_count": record["candidate_count"],
        "oracle_index": record["oracle_index"],
        "group_id": _group_id(record),
        "record_identity_hash": identity_hash,
        "split": split,
        "split_hash": split_hash,
    }


def _group_id(record: dict[str, Any]) -> str:
    return "|".join(str(record[field]) for field in GROUP_KEY_FIELDS)


def _record_identity_hash(record: dict[str, Any]) -> str:
    identity = {
        "source_log": record.get("source_log"),
        "source_log_sha256": record.get("source_log_sha256"),
        "run_id": record.get("run_id"),
        "record_index": record.get("record_index"),
    }
    return _sha256_text(json.dumps(identity, sort_keys=True, separators=(",", ":")))


def _strict_int(value: Any, field: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{field}_not_int")
        return None
    return int(value)


def _validate_sha_literal(value: Any, field: str, errors: list[str]) -> None:
    if not _is_sha256(value):
        errors.append(f"{field}_invalid")


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


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
        "split_manifest_written": bool(enabled and passed),
        "ready_for_future_preflight": bool(enabled and passed),
        "training_authorized": False,
        "fallback_dataset_training_sufficiency_claim": False,
        "camp_retraining_authorized_now": False,
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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    counts = report["record_counts"]
    lines = [
        "# DP Native Fallback Risk Training Split Manifest Builder",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"accepted_records={counts['accepted_records']}",
        f"training_records={counts['training_records']}",
        f"validation_records={counts['validation_records']}",
        "training_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "production_selector_change_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "```",
        "",
        "This builder only reads an existing validated fallback-risk dataset "
        "JSON after an explicit enable flag. It does not run replay, generate "
        "candidates, train CAMP, modify DP, promote a selector or atom, or "
        "claim safety benefit.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
