#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


PREFLIGHT_SCHEMA_VERSION = "dp_native_fallback_risk_training_sufficiency_preflight_v1"
DISABLED_STATUS = "dp_native_fallback_risk_training_sufficiency_preflight_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_training_sufficiency_preflight_complete"
REJECT_STATUS = "dp_native_fallback_risk_training_sufficiency_preflight_rejected"

EXPECTED_VALIDATED_DATASET_SHA256 = (
    "79e8ddd27b06f6d377819c64dace333e0e36af088505fe784bfee24f89f956c0"
)
EXPECTED_VALIDATED_FALLBACK_RECORDS = 15
EXPECTED_VALIDATOR_STATUS = "dp_native_fallback_risk_training_data_validator_complete"
APPROVED_ATOM_SCHEMA = "dp_camp_v10_14d"
APPROVED_ATOM_NAMES = (
    "jerk_early",
    "jerk_late",
    "jerk_full",
    "rms_acceleration",
    "speed_limit_margin_0_0",
    "speed_limit_margin_0_5",
    "speed_limit_margin_1_0",
    "lane_deviation",
    "clearance",
    "progress_shortfall",
    "planned_red_light_cost",
    "planned_lateral_acceleration_cost",
    "red_stopping_margin_cost",
    "dp_prior_jerk_excess_cost",
)
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
            "Default-off read-only preflight for fallback-risk training "
            "sufficiency manifests."
        )
    )
    parser.add_argument("--validated_dataset_summary_json", type=Path, required=True)
    parser.add_argument("--training_split_manifest_json", type=Path, required=True)
    parser.add_argument("--train_only_scale_manifest_json", type=Path, required=True)
    parser.add_argument("--fallback_master_config_json", type=Path, required=True)
    parser.add_argument("--training_command_plan_json", type=Path, required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_training_sufficiency_preflight",
        action="store_true",
        help="Explicit opt-in required before reading any manifest.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_training_sufficiency_preflight(
        validated_dataset_summary_json=args.validated_dataset_summary_json,
        training_split_manifest_json=args.training_split_manifest_json,
        train_only_scale_manifest_json=args.train_only_scale_manifest_json,
        fallback_master_config_json=args.fallback_master_config_json,
        training_command_plan_json=args.training_command_plan_json,
        enabled=args.enable_default_off_fallback_risk_training_sufficiency_preflight,
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


def validate_training_sufficiency_preflight(
    *,
    validated_dataset_summary_json: Path,
    training_split_manifest_json: Path,
    train_only_scale_manifest_json: Path,
    fallback_master_config_json: Path,
    training_command_plan_json: Path,
    enabled: bool = False,
) -> dict[str, Any]:
    source_paths = {
        "validated_dataset_summary_json": str(validated_dataset_summary_json),
        "training_split_manifest_json": str(training_split_manifest_json),
        "train_only_scale_manifest_json": str(train_only_scale_manifest_json),
        "fallback_master_config_json": str(fallback_master_config_json),
        "training_command_plan_json": str(training_command_plan_json),
    }
    report: dict[str, Any] = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_training_sufficiency_preflight_v1",
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
        "source_paths": source_paths,
        "source_hashes": {},
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
    payloads: dict[str, Any] = {}
    path_by_name = {
        "validated_dataset": validated_dataset_summary_json,
        "split_manifest": training_split_manifest_json,
        "scale_manifest": train_only_scale_manifest_json,
        "fallback_master_config": fallback_master_config_json,
        "training_command_plan": training_command_plan_json,
    }
    for name, path in path_by_name.items():
        payload, load_errors = _load_json(path, name)
        payloads[name] = payload
        errors.extend(load_errors)
        if path.is_file():
            report["source_hashes"][name] = _sha256_file(path)

    _validate_dataset(payloads.get("validated_dataset"), errors)
    _validate_split(payloads.get("split_manifest"), errors)
    _validate_scales(
        payloads.get("scale_manifest"),
        payloads.get("split_manifest"),
        errors,
    )
    _validate_master(payloads.get("fallback_master_config"), errors)
    _validate_command_plan(payloads.get("training_command_plan"), errors)
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def _load_json(path: Path, name: str) -> tuple[Any, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"{name}_unreadable:{type(exc).__name__}"]


def _validate_dataset(dataset: Any, errors: list[str]) -> None:
    if not isinstance(dataset, dict):
        errors.append("validated_dataset_not_object")
        return
    if dataset.get("sha256") != EXPECTED_VALIDATED_DATASET_SHA256:
        errors.append("validated_dataset_sha_mismatch")
    if dataset.get("records") != EXPECTED_VALIDATED_FALLBACK_RECORDS:
        errors.append("validated_fallback_record_count_mismatch")
    if dataset.get("validator_status") != EXPECTED_VALIDATOR_STATUS:
        errors.append("validator_status_not_complete")
    if dataset.get("validator_passed") is not True:
        errors.append("validator_not_passed")
    for field in ("training_sufficiency_claim", "deployable_checkpoint_claim"):
        if dataset.get(field) is not False:
            errors.append(f"{field}_leak")


def _validate_split(split: Any, errors: list[str]) -> None:
    if not isinstance(split, dict):
        errors.append("split_manifest_not_object")
        return
    if tuple(split.get("group_key_fields") or ()) != (
        "source_log",
        "run_id",
        "record_index",
    ):
        errors.append("split_group_key_invalid")
    train = _string_set(split.get("training_groups"), "training_groups", errors)
    validation = _string_set(split.get("validation_groups"), "validation_groups", errors)
    if not train or not validation:
        errors.append("split_train_or_validation_empty")
    if train & validation:
        errors.append("split_train_validation_overlap")
    seeds = _int_set(split.get("seeds"), "split_seeds", errors)
    if seeds & FORMAL_SEEDS:
        errors.append("formal_seed_in_development_split")
    if split.get("formal_eval_artifact_included") is not False:
        errors.append("formal_eval_artifact_in_development_split")


def _validate_scales(scales: Any, split: Any, errors: list[str]) -> None:
    if not isinstance(scales, dict):
        errors.append("scale_manifest_not_object")
        return
    if not isinstance(split, dict):
        errors.append("scale_manifest_without_split")
        return
    fit_groups = _string_set(scales.get("fit_groups"), "scale_fit_groups", errors)
    train = _string_set(split.get("training_groups"), "training_groups", errors)
    validation = _string_set(split.get("validation_groups"), "validation_groups", errors)
    if fit_groups != train:
        errors.append("scale_fit_groups_not_training_only")
    if fit_groups & validation:
        errors.append("scale_fit_validation_leak")
    fit_seeds = _int_set(scales.get("fit_seeds"), "scale_fit_seeds", errors)
    if fit_seeds & FORMAL_SEEDS:
        errors.append("scale_fit_formal_seed_leak")
    if scales.get("formal_eval_artifact_included") is not False:
        errors.append("scale_fit_formal_eval_leak")
    if scales.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("scale_atom_schema_mismatch")
    if tuple(scales.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("scale_atom_names_mismatch")
    values = scales.get("atom_scales")
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


def _validate_master(master: Any, errors: list[str]) -> None:
    if not isinstance(master, dict):
        errors.append("fallback_master_config_not_object")
        return
    if master.get("fallback_only") is not True:
        errors.append("fallback_master_not_isolated")
    for flag in (
        "feasible_branch_records_allowed",
        "all_infeasible_records_added_to_feasible_training",
        "all_infeasible_records_relabelled_feasible",
        "hard_feasibility_relaxation_authorized",
        "feasible_ranking_master_change_authorized",
    ):
        if master.get(flag) is not False:
            errors.append(f"{flag}_leak")
    if master.get("score_expression") != "score_k(w)=a_k^T w":
        errors.append("score_expression_not_affine")
    if master.get("atoms_fixed_nonnegative") is not True:
        errors.append("atoms_not_fixed_nonnegative")
    if master.get("fallback_label_is_deployed_atom") is not False:
        errors.append("fallback_label_promoted_to_atom")
    if master.get("margins_nonnegative") is not True:
        errors.append("margins_not_nonnegative")
    if master.get("simplex_cvar_l2_convex") is not True:
        errors.append("convex_master_boundary_missing")


def _validate_command_plan(command: Any, errors: list[str]) -> None:
    if not isinstance(command, dict):
        errors.append("training_command_plan_not_object")
        return
    if command.get("training_command_authorization") is not False:
        errors.append("training_command_authorization_leak")
    for flag in FORBIDDEN_FLAGS:
        if command.get(flag) is not False:
            errors.append(f"{flag}_leak")
    if command.get("post_training_nonpromotion_plan_required") is not True:
        errors.append("post_training_nonpromotion_plan_missing")
    if command.get("development_holdout_acceptance_gate_required") is not True:
        errors.append("development_holdout_acceptance_gate_missing")


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
        "preflight_output_written": bool(enabled and passed),
        "ready_for_future_training_authorization": bool(enabled and passed),
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


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP Native Fallback Risk Training Sufficiency Preflight",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"ready_for_future_training_authorization={decision['ready_for_future_training_authorization']}",
        "training_authorized=False",
        "camp_retraining_authorized_now=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "fallback_dataset_training_sufficiency_claim=False",
        "```",
        "",
        "This preflight only reads existing JSON manifests and emits a report. "
        "It does not run replay, generate candidates, train CAMP, modify DP, "
        "promote a selector or atom, or claim safety benefit.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
