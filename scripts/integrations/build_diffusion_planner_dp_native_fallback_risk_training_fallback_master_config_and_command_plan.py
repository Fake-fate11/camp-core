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
MASTER_CONFIG_SCHEMA_VERSION = "dp_native_fallback_risk_fallback_master_config_v1"
COMMAND_PLAN_SCHEMA_VERSION = "dp_native_fallback_risk_training_command_plan_v1"
DISABLED_STATUS = "dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder_rejected"
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only builder for fallback-only master config "
            "and dry-run command plan manifests."
        )
    )
    parser.add_argument("--dataset_json", type=Path, required=True)
    parser.add_argument("--expected_dataset_sha256", required=True)
    parser.add_argument("--training_split_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_split_manifest_sha256", required=True)
    parser.add_argument("--train_only_scale_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_scale_manifest_sha256", required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_training_master_command_builder",
        action="store_true",
        help="Explicit opt-in required before reading any input manifest.",
    )
    parser.add_argument("--output_master_config_json", type=Path, required=True)
    parser.add_argument("--output_training_command_plan_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_master_command_report(
        dataset_json=args.dataset_json,
        expected_dataset_sha256=args.expected_dataset_sha256,
        training_split_manifest_json=args.training_split_manifest_json,
        expected_split_manifest_sha256=args.expected_split_manifest_sha256,
        train_only_scale_manifest_json=args.train_only_scale_manifest_json,
        expected_scale_manifest_sha256=args.expected_scale_manifest_sha256,
        enabled=args.enable_default_off_fallback_risk_training_master_command_builder,
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    if report["final_decision"]["status"] == COMPLETE_STATUS:
        args.output_master_config_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_training_command_plan_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_master_config_json.write_text(
            json.dumps(report["fallback_master_config"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        args.output_training_command_plan_json.write_text(
            json.dumps(report["training_command_plan"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def build_master_command_report(
    *,
    dataset_json: Path,
    expected_dataset_sha256: str,
    training_split_manifest_json: Path,
    expected_split_manifest_sha256: str,
    train_only_scale_manifest_json: Path,
    expected_scale_manifest_sha256: str,
    enabled: bool = False,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": "dp_native_fallback_risk_training_master_command_builder_report_v1",
        "analysis": {
            "name": "dp_native_fallback_risk_training_fallback_master_config_and_command_plan_builder_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "read_only": True,
            "manifest_inputs_only": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "camp_training_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
        },
        "source_paths": {
            "dataset_json": str(dataset_json),
            "training_split_manifest_json": str(training_split_manifest_json),
            "train_only_scale_manifest_json": str(train_only_scale_manifest_json),
        },
        "source_hashes": {},
        "fallback_master_config": {},
        "training_command_plan": {},
        "final_decision": _decision(
            status=DISABLED_STATUS,
            passed=True,
            enabled=False,
            errors=[],
            outputs_written=False,
        ),
    }
    if not enabled:
        return report

    errors: list[str] = []
    _validate_sha_literal(expected_dataset_sha256, "expected_dataset_sha256", errors)
    _validate_sha_literal(expected_split_manifest_sha256, "expected_split_manifest_sha256", errors)
    _validate_sha_literal(expected_scale_manifest_sha256, "expected_scale_manifest_sha256", errors)

    dataset = _load_json(dataset_json, "dataset_json", errors)
    split = _load_json(training_split_manifest_json, "training_split_manifest_json", errors)
    scales = _load_json(train_only_scale_manifest_json, "train_only_scale_manifest_json", errors)

    dataset_sha = _record_sha(
        dataset_json,
        "dataset_json",
        expected_dataset_sha256,
        "dataset_sha256_mismatch",
        errors,
        report,
    )
    split_sha = _record_sha(
        training_split_manifest_json,
        "training_split_manifest_json",
        expected_split_manifest_sha256,
        "split_manifest_sha256_mismatch",
        errors,
        report,
    )
    scale_sha = _record_sha(
        train_only_scale_manifest_json,
        "train_only_scale_manifest_json",
        expected_scale_manifest_sha256,
        "scale_manifest_sha256_mismatch",
        errors,
        report,
    )

    _validate_dataset(dataset, errors)
    train, validation = _validate_split(split, errors)
    _validate_scales(scales, train, validation, dataset_sha, split_sha, errors)

    if not errors:
        report["fallback_master_config"] = _master_config(
            dataset_sha=dataset_sha,
            split_sha=split_sha,
            scale_sha=scale_sha,
        )
        report["training_command_plan"] = _command_plan(
            dataset_sha=dataset_sha,
            split_sha=split_sha,
            scale_sha=scale_sha,
        )
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
        outputs_written=not errors,
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


def _record_sha(
    path: Path,
    name: str,
    expected_sha: str,
    mismatch_error: str,
    errors: list[str],
    report: dict[str, Any],
) -> str:
    if not path.is_file():
        return ""
    actual = _sha256_file(path)
    report["source_hashes"][name] = actual
    if _is_sha256(expected_sha) and actual != expected_sha:
        errors.append(mismatch_error)
    return actual


def _validate_dataset(payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("dataset_schema_version_mismatch")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        errors.append("dataset_records_not_nonempty_list")
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
    return train, validation


def _validate_scales(
    payload: dict[str, Any],
    train: set[str],
    validation: set[str],
    dataset_sha: str,
    split_sha: str,
    errors: list[str],
) -> None:
    if payload.get("schema_version") != SCALE_MANIFEST_SCHEMA_VERSION:
        errors.append("scale_manifest_schema_version_mismatch")
    if dataset_sha and payload.get("source_dataset_sha256") != dataset_sha:
        errors.append("scale_source_dataset_sha256_mismatch")
    if split_sha and payload.get("source_split_manifest_sha256") != split_sha:
        errors.append("scale_source_split_manifest_sha256_mismatch")
    fit_groups = _string_set(payload.get("fit_groups"), "scale_fit_groups", errors)
    excluded_validation = _string_set(
        payload.get("excluded_validation_groups"),
        "scale_excluded_validation_groups",
        errors,
    )
    if fit_groups != train:
        errors.append("scale_fit_groups_not_training_only")
    if excluded_validation != validation:
        errors.append("scale_excluded_validation_groups_mismatch")
    if fit_groups & validation:
        errors.append("scale_fit_validation_leak")
    fit_seeds = _int_set(payload.get("fit_seeds"), "scale_fit_seeds", errors)
    if fit_seeds & FORMAL_SEEDS:
        errors.append("scale_fit_formal_seed_leak")
    if payload.get("formal_eval_artifact_included") is not False:
        errors.append("scale_fit_formal_eval_leak")
    if payload.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("scale_atom_schema_mismatch")
    if tuple(payload.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("scale_atom_names_mismatch")
    values = payload.get("atom_scales")
    if not isinstance(values, dict) or set(values) != set(APPROVED_ATOM_NAMES):
        errors.append("atom_scale_keys_mismatch")
        return
    for name, value in values.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0.0
        ):
            errors.append(f"atom_scale_{name}_not_strictly_positive")


def _master_config(*, dataset_sha: str, split_sha: str, scale_sha: str) -> dict[str, Any]:
    return {
        "schema_version": MASTER_CONFIG_SCHEMA_VERSION,
        "fallback_only": True,
        "feasible_branch_records_allowed": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "all_infeasible_records_relabelled_feasible": False,
        "hard_feasibility_relaxation_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "score_expression": "score_k(w)=a_k^T w",
        "atoms_fixed_nonnegative": True,
        "fallback_label_is_deployed_atom": False,
        "margins_nonnegative": True,
        "simplex_cvar_l2_convex": True,
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "atom_names": list(APPROVED_ATOM_NAMES),
        "source_dataset_sha256": dataset_sha,
        "source_split_manifest_sha256": split_sha,
        "source_scale_manifest_sha256": scale_sha,
    }


def _command_plan(*, dataset_sha: str, split_sha: str, scale_sha: str) -> dict[str, Any]:
    command: dict[str, Any] = {
        "schema_version": COMMAND_PLAN_SCHEMA_VERSION,
        "training_command_authorization": False,
        "training_execution_authorized": False,
        "training_authorized": False,
        "post_training_nonpromotion_plan_required": True,
        "development_holdout_acceptance_gate_required": True,
        "source_dataset_sha256": dataset_sha,
        "source_split_manifest_sha256": split_sha,
        "source_scale_manifest_sha256": scale_sha,
    }
    for flag in FORBIDDEN_FLAGS:
        command[flag] = False
    return command


def _decision(
    *,
    status: str,
    passed: bool,
    enabled: bool,
    errors: list[str],
    outputs_written: bool,
) -> dict[str, Any]:
    decision: dict[str, Any] = {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "errors": sorted(set(errors)),
        "master_config_output_written": bool(outputs_written),
        "training_command_plan_output_written": bool(outputs_written),
        "training_authorized": False,
        "training_execution_authorized": False,
        "fallback_dataset_training_sufficiency_claim": False,
        "camp_retraining_authorized_now": False,
    }
    for flag in FORBIDDEN_FLAGS:
        decision[flag] = False
    return decision


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


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP Native Fallback Risk Training Master Config And Command Plan",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"master_config_output_written={decision['master_config_output_written']}",
        f"training_command_plan_output_written={decision['training_command_plan_output_written']}",
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "```",
        "",
        "This builder only reads existing manifest JSON inputs when explicitly "
        "enabled. It does not run replay, generate candidates, train CAMP, "
        "modify DP, run the sufficiency preflight, promote a selector or atom, "
        "or claim safety benefit.",
        "",
    ]
    if decision["errors"]:
        lines.extend(["## Errors", "", "```text"])
        lines.extend(str(error) for error in decision["errors"])
        lines.extend(["```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
