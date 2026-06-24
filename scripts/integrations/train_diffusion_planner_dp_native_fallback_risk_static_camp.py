#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

from camp_core.outer_master.robust_margin_master import (  # noqa: E402
    empirical_cvar,
    project_simplex_rows,
)
from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_data import (  # noqa: E402
    DATASET_SCHEMA_VERSION,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
    COMPLETE_STATUS as PREFLIGHT_COMPLETE_STATUS,
)


TRAINING_SCHEMA_VERSION = "dp_native_fallback_risk_static_camp_training_v1"
DISABLED_STATUS = "dp_native_fallback_risk_static_camp_training_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_static_camp_training_complete"
REJECT_STATUS = "dp_native_fallback_risk_static_camp_training_rejected"
FORMAL_SEEDS = {11, 12, 13}

DRY_RUN_FORBIDDEN_FLAGS = (
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
            "Default-off trainer for static CAMP fallback-risk reranking on "
            "fixed DP-native candidate artifacts."
        )
    )
    parser.add_argument("--dataset_json", type=Path, required=True)
    parser.add_argument("--expected_dataset_sha256", required=True)
    parser.add_argument("--training_split_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_split_manifest_sha256", required=True)
    parser.add_argument("--train_only_scale_manifest_json", type=Path, required=True)
    parser.add_argument("--expected_scale_manifest_sha256", required=True)
    parser.add_argument("--fallback_master_config_json", type=Path, required=True)
    parser.add_argument("--expected_master_config_sha256", required=True)
    parser.add_argument("--training_command_plan_json", type=Path, required=True)
    parser.add_argument("--expected_training_command_plan_sha256", required=True)
    parser.add_argument("--preflight_json", type=Path, required=True)
    parser.add_argument("--expected_preflight_sha256", required=True)
    parser.add_argument(
        "--enable_default_off_fallback_risk_static_camp_training",
        action="store_true",
        help="Explicit opt-in required before reading any training artifact.",
    )
    parser.add_argument(
        "--user_camp_retraining_authorized",
        action="store_true",
        help="Records the current user authorization for this non-promotion training run.",
    )
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--l2_reg", type=float, default=1e-3)
    parser.add_argument("--risk_type", choices=("mean", "cvar"), default="cvar")
    parser.add_argument("--alpha", type=float, default=0.8)
    parser.add_argument("--training_seed", type=int, default=23)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--output_summary_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = train_fallback_risk_static_camp(
        dataset_json=args.dataset_json,
        expected_dataset_sha256=args.expected_dataset_sha256,
        training_split_manifest_json=args.training_split_manifest_json,
        expected_split_manifest_sha256=args.expected_split_manifest_sha256,
        train_only_scale_manifest_json=args.train_only_scale_manifest_json,
        expected_scale_manifest_sha256=args.expected_scale_manifest_sha256,
        fallback_master_config_json=args.fallback_master_config_json,
        expected_master_config_sha256=args.expected_master_config_sha256,
        training_command_plan_json=args.training_command_plan_json,
        expected_training_command_plan_sha256=args.expected_training_command_plan_sha256,
        preflight_json=args.preflight_json,
        expected_preflight_sha256=args.expected_preflight_sha256,
        enabled=args.enable_default_off_fallback_risk_static_camp_training,
        user_authorized=args.user_camp_retraining_authorized,
        epochs=args.epochs,
        lr=args.lr,
        l2_reg=args.l2_reg,
        risk_type=args.risk_type,
        alpha=args.alpha,
        training_seed=args.training_seed,
        output_dir=args.output_dir,
    )
    args.output_summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 1 if report["final_decision"]["status"] == REJECT_STATUS else 0


def train_fallback_risk_static_camp(
    *,
    dataset_json: Path,
    expected_dataset_sha256: str,
    training_split_manifest_json: Path,
    expected_split_manifest_sha256: str,
    train_only_scale_manifest_json: Path,
    expected_scale_manifest_sha256: str,
    fallback_master_config_json: Path,
    expected_master_config_sha256: str,
    training_command_plan_json: Path,
    expected_training_command_plan_sha256: str,
    preflight_json: Path,
    expected_preflight_sha256: str,
    enabled: bool = False,
    user_authorized: bool = False,
    epochs: int = 400,
    lr: float = 0.05,
    l2_reg: float = 1e-3,
    risk_type: str = "cvar",
    alpha: float = 0.8,
    training_seed: int = 23,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        output_dir=output_dir,
        status=DISABLED_STATUS,
        passed=True,
        errors=[],
    )
    if not enabled:
        return report

    errors: list[str] = []
    if not user_authorized:
        errors.append("user_camp_retraining_authorization_missing")
    if training_seed in FORMAL_SEEDS:
        errors.append("training_seed_is_formal_seed")
    if epochs <= 0:
        errors.append("epochs_not_positive")
    if not math.isfinite(lr) or lr <= 0.0:
        errors.append("lr_not_positive")
    if not math.isfinite(l2_reg) or l2_reg < 0.0:
        errors.append("l2_reg_negative")
    if risk_type not in {"mean", "cvar"}:
        errors.append("risk_type_invalid")
    if not 0.0 <= float(alpha) < 1.0:
        errors.append("alpha_out_of_range")
    if errors:
        report["final_decision"] = _decision(
            status=REJECT_STATUS,
            passed=False,
            enabled=True,
            errors=errors,
            training_executed=False,
        )
        return report

    expected = {
        "dataset": expected_dataset_sha256,
        "split_manifest": expected_split_manifest_sha256,
        "scale_manifest": expected_scale_manifest_sha256,
        "fallback_master_config": expected_master_config_sha256,
        "training_command_plan": expected_training_command_plan_sha256,
        "preflight": expected_preflight_sha256,
    }
    for name, value in expected.items():
        _validate_sha_literal(value, f"expected_{name}_sha256", errors)

    paths = {
        "dataset": dataset_json,
        "split_manifest": training_split_manifest_json,
        "scale_manifest": train_only_scale_manifest_json,
        "fallback_master_config": fallback_master_config_json,
        "training_command_plan": training_command_plan_json,
        "preflight": preflight_json,
    }
    payloads: dict[str, Any] = {}
    for name, path in paths.items():
        payloads[name] = _load_json(path, name, errors)
        if path.is_file():
            actual = _sha256_file(path)
            report["source_hashes"][name] = actual
            if _is_sha256(expected[name]) and actual != expected[name]:
                errors.append(f"{name}_sha256_mismatch")

    records = _validate_dataset(payloads["dataset"], errors)
    train_groups, validation_groups = _validate_split(payloads["split_manifest"], errors)
    atom_scales = _validate_scales(
        payloads["scale_manifest"],
        train_groups,
        validation_groups,
        errors,
    )
    _validate_master(payloads["fallback_master_config"], errors)
    _validate_dry_run_command(payloads["training_command_plan"], errors)
    _validate_preflight(
        payloads["preflight"],
        report["source_hashes"],
        errors,
    )

    if errors:
        report["final_decision"] = _decision(
            status=REJECT_STATUS,
            passed=False,
            enabled=True,
            errors=errors,
            training_executed=False,
        )
        return report

    arrays = _arrays_from_records(records, train_groups, validation_groups, errors)
    if errors:
        report["final_decision"] = _decision(
            status=REJECT_STATUS,
            passed=False,
            enabled=True,
            errors=errors,
            training_executed=False,
        )
        return report

    weights, history = _train_simplex_hinge_cvar(
        arrays["train_atoms"],
        arrays["train_oracle"],
        arrays["train_margins"],
        epochs=int(epochs),
        lr=float(lr),
        l2_reg=float(l2_reg),
        risk_type=risk_type,
        alpha=float(alpha),
    )
    train_metrics = _metrics(
        arrays["train_atoms"],
        arrays["train_oracle"],
        arrays["train_margins"],
        weights,
        risk_type=risk_type,
        alpha=float(alpha),
    )
    validation_metrics = _metrics(
        arrays["validation_atoms"],
        arrays["validation_oracle"],
        arrays["validation_margins"],
        weights,
        risk_type=risk_type,
        alpha=float(alpha),
    )
    outputs = _write_training_artifacts(
        output_dir=Path(output_dir) if output_dir is not None else Path("models"),
        weights=weights,
        atom_scales=atom_scales,
        source_hashes=report["source_hashes"],
    )

    report.update(
        {
            "training": {
                "training_type": "dp_native_fallback_risk_static_candidate_reranking",
                "training_scope": "fallback_only_all_infeasible_fixed_dp_candidates",
                "score_expression": "score_k(w)=a_k^T w",
                "objective": "simplex_hinge_cvar_l2" if risk_type == "cvar" else "simplex_hinge_mean_l2",
                "risk_type": risk_type,
                "alpha": float(alpha),
                "epochs": int(epochs),
                "lr": float(lr),
                "l2_reg": float(l2_reg),
                "training_seed_recorded": int(training_seed),
                "training_records": int(arrays["train_atoms"].shape[0]),
                "validation_records": int(arrays["validation_atoms"].shape[0]),
                "num_candidates": int(arrays["train_atoms"].shape[1]),
                "num_atoms": int(arrays["train_atoms"].shape[2]),
                "atom_schema_version": APPROVED_ATOM_SCHEMA,
                "atom_names": list(APPROVED_ATOM_NAMES),
                "trained_weights": weights.tolist(),
                "weights_sum": float(np.sum(weights)),
                "weights_min": float(np.min(weights)),
                "weights_max": float(np.max(weights)),
                "history": history,
                "train_metrics": train_metrics,
                "validation_metrics": validation_metrics,
            },
            "output_artifacts": outputs,
        }
    )
    report["final_decision"] = _decision(
        status=COMPLETE_STATUS,
        passed=True,
        enabled=True,
        errors=[],
        training_executed=True,
    )
    return report


def _empty_report(
    *,
    enabled: bool,
    output_dir: Path | None,
    status: str,
    passed: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": TRAINING_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_static_camp_training_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "reads_fixed_artifacts_only": True,
            "fallback_only": True,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
            "trajectory_generation_executed": False,
            "trajectory_rewrite_executed": False,
            "postprocess_postselection_executed": False,
            "selector_promotion_executed": False,
            "atom_promotion_executed": False,
        },
        "source_hashes": {},
        "training": {},
        "output_artifacts": {
            "output_dir": str(output_dir) if output_dir is not None else None,
        },
        "final_decision": _decision(
            status=status,
            passed=passed,
            enabled=enabled,
            errors=errors,
            training_executed=False,
        ),
    }


def _load_json(path: Path, name: str, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{name}_unreadable:{type(exc).__name__}")
        return {}


def _validate_dataset(payload: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        errors.append("dataset_not_object")
        return []
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        errors.append("dataset_schema_version_mismatch")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        errors.append("dataset_records_not_nonempty_list")
        records = []
    counts = payload.get("record_counts")
    if not isinstance(counts, dict):
        errors.append("dataset_record_counts_missing")
    else:
        if counts.get("records_built") != len(records):
            errors.append("dataset_records_built_count_mismatch")
        if counts.get("records_built") != counts.get("records_without_feasible_candidate"):
            errors.append("dataset_records_not_all_fallback")
        if counts.get("failed_records") != 0:
            errors.append("dataset_failed_records_nonzero")
    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("dataset_final_decision_missing")
    else:
        if decision.get("passed") is not True:
            errors.append("dataset_final_decision_not_passed")
        for flag in DRY_RUN_FORBIDDEN_FLAGS + ("training_authorized",):
            if flag in decision and decision.get(flag) is not False:
                errors.append(f"dataset_final_decision_{flag}_not_false")
    return [record for record in records if isinstance(record, dict)]


def _validate_split(payload: Any, errors: list[str]) -> tuple[set[str], set[str]]:
    if not isinstance(payload, dict):
        errors.append("split_manifest_not_object")
        return set(), set()
    if tuple(payload.get("group_key_fields") or ()) != ("source_log", "run_id", "record_index"):
        errors.append("split_group_key_invalid")
    train = _string_set(payload.get("training_groups"), "training_groups", errors)
    validation = _string_set(payload.get("validation_groups"), "validation_groups", errors)
    if not train or not validation:
        errors.append("split_train_or_validation_empty")
    if train & validation:
        errors.append("split_train_validation_overlap")
    seeds = _int_set(payload.get("seeds"), "split_seeds", errors)
    if seeds & FORMAL_SEEDS:
        errors.append("formal_seed_in_development_split")
    if payload.get("formal_eval_artifact_included") is not False:
        errors.append("formal_eval_artifact_included")
    return train, validation


def _validate_scales(
    payload: Any,
    train: set[str],
    validation: set[str],
    errors: list[str],
) -> dict[str, float]:
    if not isinstance(payload, dict):
        errors.append("scale_manifest_not_object")
        return {}
    if payload.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("scale_atom_schema_mismatch")
    if tuple(payload.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("scale_atom_names_mismatch")
    fit_groups = _string_set(payload.get("fit_groups"), "scale_fit_groups", errors)
    if fit_groups != train:
        errors.append("scale_fit_groups_not_training_only")
    if fit_groups & validation:
        errors.append("scale_fit_validation_leak")
    fit_seeds = _int_set(payload.get("fit_seeds"), "scale_fit_seeds", errors)
    if fit_seeds & FORMAL_SEEDS:
        errors.append("scale_fit_formal_seed_leak")
    if payload.get("formal_eval_artifact_included") is not False:
        errors.append("scale_fit_formal_eval_leak")
    values = payload.get("atom_scales")
    if not isinstance(values, dict) or set(values) != set(APPROVED_ATOM_NAMES):
        errors.append("atom_scale_keys_mismatch")
        return {}
    scales: dict[str, float] = {}
    for name in APPROVED_ATOM_NAMES:
        value = values.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0.0:
            errors.append(f"atom_scale_{name}_not_strictly_positive")
        else:
            scales[name] = float(value)
    return scales


def _validate_master(payload: Any, errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("fallback_master_config_not_object")
        return
    if payload.get("fallback_only") is not True:
        errors.append("fallback_master_not_isolated")
    for flag in (
        "feasible_branch_records_allowed",
        "all_infeasible_records_added_to_feasible_training",
        "all_infeasible_records_relabelled_feasible",
        "hard_feasibility_relaxation_authorized",
        "feasible_ranking_master_change_authorized",
    ):
        if payload.get(flag) is not False:
            errors.append(f"{flag}_leak")
    if payload.get("score_expression") != "score_k(w)=a_k^T w":
        errors.append("score_expression_not_affine")
    if payload.get("atoms_fixed_nonnegative") is not True:
        errors.append("atoms_not_fixed_nonnegative")
    if payload.get("fallback_label_is_deployed_atom") is not False:
        errors.append("fallback_label_promoted_to_atom")
    if payload.get("margins_nonnegative") is not True:
        errors.append("margins_not_nonnegative")
    if payload.get("simplex_cvar_l2_convex") is not True:
        errors.append("convex_master_boundary_missing")


def _validate_dry_run_command(payload: Any, errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append("training_command_plan_not_object")
        return
    for flag in (
        "training_command_authorization",
        "training_execution_authorized",
        "training_authorized",
    ):
        if payload.get(flag) is not False:
            errors.append(f"dry_run_{flag}_not_false")
    for flag in DRY_RUN_FORBIDDEN_FLAGS:
        if payload.get(flag) is not False:
            errors.append(f"{flag}_leak")
    if payload.get("post_training_nonpromotion_plan_required") is not True:
        errors.append("post_training_nonpromotion_plan_missing")
    if payload.get("development_holdout_acceptance_gate_required") is not True:
        errors.append("development_holdout_acceptance_gate_missing")


def _validate_preflight(
    payload: Any,
    source_hashes: dict[str, str],
    errors: list[str],
) -> None:
    if not isinstance(payload, dict):
        errors.append("preflight_not_object")
        return
    decision = payload.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("preflight_final_decision_missing")
        return
    if decision.get("status") != PREFLIGHT_COMPLETE_STATUS:
        errors.append("preflight_status_not_complete")
    if decision.get("passed") is not True:
        errors.append("preflight_not_passed")
    if decision.get("errors") not in ([], None):
        errors.append("preflight_errors_nonempty")
    if decision.get("ready_for_future_training_authorization") is not True:
        errors.append("preflight_not_ready_for_training_authorization")
    if decision.get("training_authorized") is not False:
        errors.append("preflight_training_already_authorized")
    preflight_hashes = payload.get("source_hashes")
    if not isinstance(preflight_hashes, dict):
        errors.append("preflight_source_hashes_missing")
        return
    for name in (
        "split_manifest",
        "scale_manifest",
        "fallback_master_config",
        "training_command_plan",
    ):
        if preflight_hashes.get(name) != source_hashes.get(name):
            errors.append(f"preflight_{name}_hash_mismatch")


def _arrays_from_records(
    records: list[dict[str, Any]],
    train_groups: set[str],
    validation_groups: set[str],
    errors: list[str],
) -> dict[str, np.ndarray]:
    train_atoms: list[list[list[float]]] = []
    train_oracle: list[int] = []
    train_margins: list[list[float]] = []
    validation_atoms: list[list[list[float]]] = []
    validation_oracle: list[int] = []
    validation_margins: list[list[float]] = []
    seen_train: set[str] = set()
    seen_validation: set[str] = set()
    expected_shape: tuple[int, int] | None = None

    for index, record in enumerate(records):
        group = _group_id(record)
        if group is None:
            errors.append(f"record_{index}:group_key_invalid")
            continue
        if group not in train_groups and group not in validation_groups:
            errors.append(f"record_{index}:group_not_in_split")
            continue
        atoms = _matrix(record.get("normalized_atoms"), f"record_{index}:normalized_atoms", errors)
        margins = _vector(record.get("margins"), f"record_{index}:margins", errors)
        oracle = _strict_int(record.get("oracle_index"), f"record_{index}:oracle_index", errors)
        candidate_count = _strict_int(record.get("candidate_count"), f"record_{index}:candidate_count", errors)
        if not atoms or not margins or oracle is None or candidate_count is None:
            continue
        shape = (len(atoms), len(atoms[0]))
        if expected_shape is None:
            expected_shape = shape
        elif shape != expected_shape:
            errors.append(f"record_{index}:atom_shape_mismatch")
        if candidate_count != shape[0] or len(margins) != shape[0]:
            errors.append(f"record_{index}:candidate_count_mismatch")
        if shape[1] != len(APPROVED_ATOM_NAMES):
            errors.append(f"record_{index}:atom_dimension_mismatch")
        if record.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
            errors.append(f"record_{index}:atom_schema_version_mismatch")
        if tuple(record.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
            errors.append(f"record_{index}:atom_names_mismatch")
        if not 0 <= oracle < shape[0]:
            errors.append(f"record_{index}:oracle_index_out_of_range")
        if any(value < 0.0 for row in atoms for value in row):
            errors.append(f"record_{index}:normalized_atoms_negative")
        if any(value < 0.0 for value in margins):
            errors.append(f"record_{index}:margins_negative")
        if record.get("selected_index_used_as_feature") is not False:
            errors.append(f"record_{index}:selected_index_feature_leak")
        if record.get("candidate_rank_used_as_feature") is not False:
            errors.append(f"record_{index}:candidate_rank_feature_leak")
        if record.get("fallback_label_is_not_a_deployed_atom") is not True:
            errors.append(f"record_{index}:fallback_label_promoted_to_atom")
        if record.get("training_authorized") is not False:
            errors.append(f"record_{index}:input_record_training_authorized_not_false")
        if errors and any(error.startswith(f"record_{index}:") for error in errors):
            continue
        if group in train_groups:
            seen_train.add(group)
            train_atoms.append(atoms)
            train_oracle.append(int(oracle))
            train_margins.append(margins)
        else:
            seen_validation.add(group)
            validation_atoms.append(atoms)
            validation_oracle.append(int(oracle))
            validation_margins.append(margins)

    if seen_train != train_groups:
        errors.append("missing_training_groups")
    if seen_validation != validation_groups:
        errors.append("missing_validation_groups")
    if not train_atoms or not validation_atoms:
        errors.append("train_or_validation_arrays_empty")
    if errors:
        empty = np.zeros((0, 0, 0), dtype=np.float64)
        return {
            "train_atoms": empty,
            "train_oracle": np.zeros((0,), dtype=np.int64),
            "train_margins": np.zeros((0, 0), dtype=np.float64),
            "validation_atoms": empty,
            "validation_oracle": np.zeros((0,), dtype=np.int64),
            "validation_margins": np.zeros((0, 0), dtype=np.float64),
        }
    return {
        "train_atoms": np.asarray(train_atoms, dtype=np.float64),
        "train_oracle": np.asarray(train_oracle, dtype=np.int64),
        "train_margins": np.asarray(train_margins, dtype=np.float64),
        "validation_atoms": np.asarray(validation_atoms, dtype=np.float64),
        "validation_oracle": np.asarray(validation_oracle, dtype=np.int64),
        "validation_margins": np.asarray(validation_margins, dtype=np.float64),
    }


def _train_simplex_hinge_cvar(
    atoms: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    *,
    epochs: int,
    lr: float,
    l2_reg: float,
    risk_type: str,
    alpha: float,
) -> tuple[np.ndarray, list[dict[str, float]]]:
    num_atoms = atoms.shape[2]
    weights = np.full(num_atoms, 1.0 / float(num_atoms), dtype=np.float64)
    uniform = weights.copy()
    history: list[dict[str, float]] = []
    for epoch in range(1, int(epochs) + 1):
        losses, worst = _violations(atoms, oracle, margins, weights)
        risk, coefficients = _risk_and_coefficients(losses, risk_type=risk_type, alpha=alpha)
        grad = np.zeros(num_atoms, dtype=np.float64)
        for row, coeff in enumerate(coefficients):
            if coeff <= 0.0 or losses[row] <= 0.0:
                continue
            grad += coeff * (atoms[row, int(oracle[row])] - atoms[row, int(worst[row])])
        grad += 2.0 * float(l2_reg) * (weights - uniform)
        weights = project_simplex_rows(weights - float(lr) * grad)[0]
        if epoch == 1 or epoch == epochs or epoch % 50 == 0:
            history.append(
                {
                    "epoch": float(epoch),
                    "objective": float(risk + float(l2_reg) * np.sum((weights - uniform) ** 2)),
                    "risk": float(risk),
                    "mean_violation": float(np.mean(losses)),
                    "max_violation": float(np.max(losses)),
                    "oracle_match_rate": _oracle_match_rate(atoms, oracle, weights),
                }
            )
    return weights, history


def _violations(
    atoms: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    rows = np.arange(atoms.shape[0])
    oracle_atoms = atoms[rows, oracle]
    candidate_values = margins + np.einsum("nkr,r->nk", oracle_atoms[:, None, :] - atoms, weights)
    worst = np.argmax(candidate_values, axis=1)
    losses = np.maximum(candidate_values[rows, worst], 0.0)
    return losses, worst.astype(np.int64)


def _risk_and_coefficients(
    losses: np.ndarray,
    *,
    risk_type: str,
    alpha: float,
) -> tuple[float, np.ndarray]:
    if risk_type == "mean":
        return float(np.mean(losses)), np.full(losses.shape[0], 1.0 / losses.shape[0], dtype=np.float64)
    cvar, eta = empirical_cvar(losses, alpha)
    coeff = np.zeros(losses.shape[0], dtype=np.float64)
    tail = losses > eta + 1e-12
    if not tail.any():
        tail[np.argmax(losses)] = True
    coeff[tail] = 1.0 / ((1.0 - float(alpha)) * float(losses.shape[0]))
    return float(cvar), coeff


def _metrics(
    atoms: np.ndarray,
    oracle: np.ndarray,
    margins: np.ndarray,
    weights: np.ndarray,
    *,
    risk_type: str,
    alpha: float,
) -> dict[str, float]:
    if atoms.shape[0] == 0:
        return {
            "records": 0.0,
            "oracle_match_rate": float("nan"),
            "mean_violation": float("nan"),
            "cvar_violation": float("nan"),
            "max_violation": float("nan"),
        }
    losses, _ = _violations(atoms, oracle, margins, weights)
    cvar, eta = empirical_cvar(losses, alpha)
    return {
        "records": float(atoms.shape[0]),
        "oracle_match_rate": _oracle_match_rate(atoms, oracle, weights),
        "mean_violation": float(np.mean(losses)),
        "cvar_violation": float(cvar if risk_type == "cvar" else np.mean(losses)),
        "cvar_eta": float(eta),
        "max_violation": float(np.max(losses)),
    }


def _oracle_match_rate(atoms: np.ndarray, oracle: np.ndarray, weights: np.ndarray) -> float:
    scores = np.einsum("nkr,r->nk", atoms, weights)
    selected = np.argmin(scores, axis=1)
    return float(np.mean(selected == oracle))


def _write_training_artifacts(
    *,
    output_dir: Path,
    weights: np.ndarray,
    atom_scales: dict[str, float],
    source_hashes: dict[str, str],
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    weights_npy = output_dir / "offline_weights_dp_fallback_risk_static.npy"
    weights_json = output_dir / "offline_weights_dp_fallback_risk_static.json"
    scales_json = output_dir / "atom_scales_dp_fallback_risk_static.json"
    np.save(weights_npy, weights.astype(np.float64))
    weights_json.write_text(
        json.dumps(
            {
                "atom_schema_version": APPROVED_ATOM_SCHEMA,
                "atom_names": list(APPROVED_ATOM_NAMES),
                "weights": weights.tolist(),
                "score_expression": "score_k(w)=a_k^T w",
                "fallback_only": True,
                "selector_promotion_executed": False,
                "source_hashes": source_hashes,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    scales_json.write_text(
        json.dumps(
            {
                "atom_schema_version": APPROVED_ATOM_SCHEMA,
                "atom_names": list(APPROVED_ATOM_NAMES),
                "scales": [atom_scales[name] for name in APPROVED_ATOM_NAMES],
                "source_scale_manifest_sha256": source_hashes.get("scale_manifest"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "output_dir": str(output_dir),
        "weights_npy": str(weights_npy),
        "weights_json": str(weights_json),
        "atom_scales_json": str(scales_json),
        "weights_npy_sha256": _sha256_file(weights_npy),
        "weights_json_sha256": _sha256_file(weights_json),
        "atom_scales_json_sha256": _sha256_file(scales_json),
    }


def _decision(
    *,
    status: str,
    passed: bool,
    enabled: bool,
    errors: list[str],
    training_executed: bool,
) -> dict[str, Any]:
    training = bool(training_executed and passed)
    return {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "errors": sorted(set(errors)),
        "training_authorized": training,
        "training_execution_authorized": training,
        "training_executed": training,
        "camp_retraining_authorized_now": training,
        "fallback_risk_training_authorized_now": training,
        "fixed_dp_candidate_reranking_only": training,
        "fallback_only_training": training,
        "replay_execution_authorized": False,
        "candidate_generation_authorized": False,
        "Full36_authorized": False,
        "formal_seeds_11_12_13_authorized": False,
        "dp_modification_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postprocess_postselection_authorized": False,
        "closed_loop_outcome_online_input_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "feasible_ranking_master_change_authorized": False,
        "hard_feasibility_relaxation_authorized": False,
        "all_infeasible_records_added_to_feasible_training": False,
        "production_selector_change_authorized": False,
        "online_selector_change_authorized": False,
    }


def _group_id(record: dict[str, Any]) -> str | None:
    values = []
    for field in ("source_log", "run_id", "record_index"):
        value = record.get(field)
        if value in (None, ""):
            return None
        values.append(str(value))
    return "|".join(values)


def _matrix(value: Any, field: str, errors: list[str]) -> list[list[float]]:
    if not isinstance(value, list) or not value or not all(isinstance(row, list) and row for row in value):
        errors.append(f"{field}_not_nonempty_matrix")
        return []
    rows: list[list[float]] = []
    width: int | None = None
    for row_index, row in enumerate(value):
        parsed = []
        for item in row:
            if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
                errors.append(f"{field}_{row_index}_not_finite_numeric")
                return []
            parsed.append(float(item))
        if width is None:
            width = len(parsed)
        elif len(parsed) != width:
            errors.append(f"{field}_ragged")
            return []
        rows.append(parsed)
    return rows


def _vector(value: Any, field: str, errors: list[str]) -> list[float]:
    if not isinstance(value, list) or not value:
        errors.append(f"{field}_not_nonempty_vector")
        return []
    parsed = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            errors.append(f"{field}_not_finite_numeric")
            return []
        parsed.append(float(item))
    return parsed


def _strict_int(value: Any, field: str, errors: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(f"{field}_not_int")
        return None
    return int(value)


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
    training = report.get("training") or {}
    lines = [
        "# DP Native Fallback Risk Static CAMP Training",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"training_authorized={decision['training_authorized']}",
        f"training_execution_authorized={decision['training_execution_authorized']}",
        f"training_executed={decision['training_executed']}",
        f"camp_retraining_authorized_now={decision['camp_retraining_authorized_now']}",
        f"fallback_risk_training_authorized_now={decision['fallback_risk_training_authorized_now']}",
        f"fixed_dp_candidate_reranking_only={decision['fixed_dp_candidate_reranking_only']}",
        "score_k(w)=a_k^T w",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "hard_feasibility_relaxation_authorized=False",
        "all_infeasible_records_added_to_feasible_training=False",
        "```",
        "",
    ]
    if training:
        lines.extend(
            [
                "## Training Summary",
                "",
                "```text",
                f"training_type={training['training_type']}",
                f"training_scope={training['training_scope']}",
                f"objective={training['objective']}",
                f"risk_type={training['risk_type']}",
                f"training_records={training['training_records']}",
                f"validation_records={training['validation_records']}",
                f"num_candidates={training['num_candidates']}",
                f"num_atoms={training['num_atoms']}",
                f"weights_sum={training['weights_sum']}",
                f"weights_min={training['weights_min']}",
                f"weights_max={training['weights_max']}",
                f"train_oracle_match_rate={training['train_metrics']['oracle_match_rate']}",
                f"validation_oracle_match_rate={training['validation_metrics']['oracle_match_rate']}",
                "```",
                "",
            ]
        )
    if decision["errors"]:
        lines.extend(["## Errors", "", "```text"])
        lines.extend(str(error) for error in decision["errors"])
        lines.extend(["```", ""])
    lines.append(
        "This trainer only reads fixed, preflighted DP-native artifacts. It trains "
        "a fallback-only static CAMP reranker over existing DP candidate rows and "
        "does not execute DP, generate or modify trajectories, promote runtime "
        "selectors or atoms, or claim safety benefit."
    )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
