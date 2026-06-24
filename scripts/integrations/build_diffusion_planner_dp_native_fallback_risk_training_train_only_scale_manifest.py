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

from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
)


DATASET_SCHEMA_VERSION = "dp_native_fallback_risk_training_data_v1"
SPLIT_MANIFEST_SCHEMA_VERSION = "dp_native_fallback_risk_training_split_manifest_v1"
SCALE_MANIFEST_SCHEMA_VERSION = "dp_native_fallback_risk_training_train_only_scale_manifest_v1"
DISABLED_STATUS = "dp_native_fallback_risk_training_train_only_scale_manifest_builder_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_train_only_scale_manifest_builder_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_train_only_scale_manifest_builder_rejected"
SCALE_POLICY = "train_only_positive_finite_p95_or_one_v1"
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
FORBIDDEN_SCALE_FEATURE_FLAGS = (
    "selected_index_used_as_feature",
    "candidate_rank_used_as_feature",
    "closed_loop_outcome_used_as_feature",
    "learned_weights_used_as_feature",
    "selected_index_scale_feature",
    "candidate_rank_scale_feature",
    "closed_loop_outcome_scale_feature",
    "learned_weights_scale_feature",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only builder for DP-native fallback-risk "
            "train-only atom scale manifests."
        )
    )
    parser.add_argument("--dataset_json", type=Path, required=True)
    parser.add_argument("--expected_dataset_sha256", required=True)
    parser.add_argument("--training_split_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_split_manifest_sha256", required=True)
    parser.add_argument("--validator_output_sha256", required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_training_train_only_scale_manifest_builder",
        action="store_true",
        help="Explicit opt-in required before reading dataset or split JSON.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_scale_manifest_report(
        dataset_json=args.dataset_json,
        expected_dataset_sha256=args.expected_dataset_sha256,
        training_split_manifest_json=args.training_split_manifest_json,
        expected_split_manifest_sha256=args.expected_split_manifest_sha256,
        validator_output_sha256=args.validator_output_sha256,
        enabled=args.enable_default_off_fallback_risk_training_train_only_scale_manifest_builder,
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


def build_scale_manifest_report(
    *,
    dataset_json: Path,
    expected_dataset_sha256: str,
    training_split_manifest_json: Path,
    expected_split_manifest_sha256: str,
    validator_output_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": SCALE_MANIFEST_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_training_train_only_scale_manifest_builder_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "read_only": True,
            "scale_policy": SCALE_POLICY,
            "fit_scope": "split_manifest_training_groups_only",
            "validation_groups_excluded": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
        },
        "source_paths": {
            "dataset_json": str(dataset_json),
            "training_split_manifest_json": str(training_split_manifest_json),
        },
        "source_hashes": {},
        "source_dataset_sha256": None,
        "source_split_manifest_sha256": None,
        "validator_output_sha256": validator_output_sha256,
        "fit_groups": [],
        "excluded_validation_groups": [],
        "fit_seeds": [],
        "formal_eval_artifact_included": False,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "scale_policy": SCALE_POLICY,
        "atom_scales": {},
        "fit_record_counts": {
            "training_records_seen": 0,
            "validation_records_seen": 0,
            "fit_records_used": 0,
        },
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
    _validate_sha_literal(expected_split_manifest_sha256, "expected_split_manifest_sha256", errors)
    _validate_sha_literal(validator_output_sha256, "validator_output_sha256", errors)

    dataset = _load_json(dataset_json, "dataset_json", errors)
    split = _load_json(training_split_manifest_json, "training_split_manifest_json", errors)
    if dataset_json.is_file():
        dataset_sha = _sha256_file(dataset_json)
        report["source_hashes"]["dataset_json"] = dataset_sha
        report["source_dataset_sha256"] = dataset_sha
        if _is_sha256(expected_dataset_sha256) and dataset_sha != expected_dataset_sha256:
            errors.append("dataset_sha256_mismatch")
    if training_split_manifest_json.is_file():
        split_sha = _sha256_file(training_split_manifest_json)
        report["source_hashes"]["training_split_manifest_json"] = split_sha
        report["source_split_manifest_sha256"] = split_sha
        if _is_sha256(expected_split_manifest_sha256) and split_sha != expected_split_manifest_sha256:
            errors.append("split_manifest_sha256_mismatch")

    records = _validate_dataset(dataset, errors)
    train, validation = _validate_split(split, errors)
    report["fit_groups"] = list(split.get("training_groups") or [])
    report["excluded_validation_groups"] = list(split.get("validation_groups") or [])
    report["fit_seeds"] = list(split.get("seeds") or [])

    atom_values: dict[str, list[float]] = {name: [] for name in APPROVED_ATOM_NAMES}
    seen_groups: set[str] = set()
    training_records_seen = 0
    validation_records_seen = 0
    fit_records_used = 0
    for index, record in enumerate(records):
        group = _group_id(record)
        if group is None:
            errors.append(f"record_{index}:group_key_invalid")
            continue
        seen_groups.add(group)
        if group not in train and group not in validation:
            errors.append(f"record_{index}:dataset_record_not_in_split_manifest")
        if group in validation:
            validation_records_seen += 1
        if group not in train:
            continue
        training_records_seen += 1
        record_errors = _collect_record_atom_values(record, atom_values)
        errors.extend(f"record_{index}:{error}" for error in record_errors)
        if not record_errors:
            fit_records_used += 1
    report["fit_record_counts"] = {
        "training_records_seen": training_records_seen,
        "validation_records_seen": validation_records_seen,
        "fit_records_used": fit_records_used,
    }

    if train - seen_groups:
        errors.append("missing_training_groups")
    if validation - seen_groups:
        errors.append("missing_validation_groups")

    report["atom_scales"] = {
        atom: (_nearest_rank_p95(values) if values else 1.0)
        for atom, values in atom_values.items()
    }
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def _load_json(path: Path, name: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{name}_unreadable:{type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{name}_not_object")
        return {}
    return payload


def _validate_dataset(payload: dict[str, Any], errors: list[str]) -> list[dict[str, Any]]:
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("dataset_schema_version_mismatch")
    records = payload.get("records")
    if not isinstance(records, list):
        errors.append("dataset_records_not_list")
        records = []
    decision = payload.get("final_decision")
    if isinstance(decision, dict):
        if decision.get("passed") is not True:
            errors.append("dataset_final_decision_not_passed")
        for flag in FORBIDDEN_FLAGS + ("training_authorized",):
            if flag in decision and decision.get(flag) is not False:
                errors.append(f"dataset_final_decision_{flag}_not_false")
    elif "final_decision" in payload:
        errors.append("dataset_final_decision_not_object")
    for field in ("training_sufficiency_claim", "deployable_checkpoint_claim"):
        if payload.get(field) not in (None, False):
            errors.append(f"{field}_leak")
    valid_records = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record_{index}:record_not_object")
            continue
        valid_records.append(record)
    return valid_records


def _validate_split(payload: dict[str, Any], errors: list[str]) -> tuple[set[str], set[str]]:
    if payload.get("schema_version") not in (SPLIT_MANIFEST_SCHEMA_VERSION, None):
        errors.append("split_manifest_schema_version_mismatch")
    if tuple(payload.get("group_key_fields") or ()) != ("source_log", "run_id", "record_index"):
        errors.append("split_group_key_invalid")
    train = _string_set(payload.get("training_groups"), "training_groups", errors)
    validation = _string_set(payload.get("validation_groups"), "validation_groups", errors)
    if not train:
        errors.append("training_groups_empty")
    if not validation:
        errors.append("validation_groups_empty")
    if train & validation:
        errors.append("training_validation_overlap")
    seeds = _int_set(payload.get("seeds"), "split_seeds", errors)
    if seeds & FORMAL_SEEDS:
        errors.append("formal_seed_in_split")
    if payload.get("formal_eval_artifact_included") is not False:
        errors.append("formal_eval_artifact_included")
    decision = payload.get("final_decision")
    if isinstance(decision, dict):
        if decision.get("passed") is not True:
            errors.append("split_final_decision_not_passed")
        for flag in FORBIDDEN_FLAGS + ("training_authorized",):
            if flag in decision and decision.get(flag) is not False:
                errors.append(f"split_final_decision_{flag}_not_false")
    elif "final_decision" in payload:
        errors.append("split_final_decision_not_object")
    return train, validation


def _collect_record_atom_values(
    record: dict[str, Any],
    atom_values: dict[str, list[float]],
) -> list[str]:
    errors: list[str] = []
    for flag in FORBIDDEN_SCALE_FEATURE_FLAGS:
        if record.get(flag) not in (None, False):
            errors.append(f"{flag}_leak")
    if record.get("seed") in FORMAL_SEEDS:
        errors.append("formal_seed_record_leak")
    if record.get("formal_eval_artifact_included") not in (None, False):
        errors.append("formal_eval_artifact_record_leak")
    if record.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("atom_schema_mismatch")
    if tuple(record.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("atom_names_mismatch")
    rows = record.get("atoms")
    if not isinstance(rows, list) or not rows:
        errors.append("atoms_not_nonempty_list")
        return errors
    record_atom_values: dict[str, list[float]] = {name: [] for name in APPROVED_ATOM_NAMES}
    for row_index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(APPROVED_ATOM_NAMES):
            errors.append(f"atoms_{row_index}_dimension_mismatch")
            continue
        for atom, value in zip(APPROVED_ATOM_NAMES, row):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                errors.append(f"{atom}_not_finite_numeric")
                continue
            if float(value) < 0.0:
                errors.append(f"{atom}_negative")
                continue
            if float(value) > 0.0:
                record_atom_values[atom].append(float(value))
    if not errors:
        for atom, values in record_atom_values.items():
            atom_values[atom].extend(values)
    return errors


def _group_id(record: dict[str, Any]) -> str | None:
    values = []
    for field in ("source_log", "run_id", "record_index"):
        value = record.get(field)
        if value in (None, ""):
            return None
        values.append(str(value))
    return "|".join(values)


def _nearest_rank_p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])


def _string_set(value: Any, field: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{field}_not_string_list")
        return set()
    return set(value)


def _int_set(value: Any, field: str, errors: list[str]) -> set[int]:
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        errors.append(f"{field}_not_int_list")
        return set()
    return set(value)


def _validate_sha_literal(value: Any, field: str, errors: list[str]) -> None:
    if not _is_sha256(value):
        errors.append(f"{field}_invalid")


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "scale_manifest_builder_output_written": bool(enabled and passed),
        "training_authorized": False,
        "fallback_dataset_training_sufficiency_claim": False,
        "camp_retraining_authorized_now": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP Native Fallback Risk Training Train-Only Scale Manifest",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"scale_policy={report['scale_policy']}",
        f"fit_groups={len(report['fit_groups'])}",
        f"excluded_validation_groups={len(report['excluded_validation_groups'])}",
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "```",
        "",
        "This builder only reads existing dataset and split manifests when "
        "explicitly enabled. It does not run replay, generate candidates, train "
        "CAMP, modify DP, promote a selector or atom, or claim safety benefit.",
        "",
    ]
    if decision["errors"]:
        lines.extend(["## Errors", "", "```text"])
        lines.extend(str(error) for error in decision["errors"])
        lines.extend(["```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
