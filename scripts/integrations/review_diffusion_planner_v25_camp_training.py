#!/usr/bin/env python3
"""Independently validate V25 strict convex Static/Scene training evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_context import (  # noqa: E402
    CONTEXT_SCHEMA_VERSION,
    PHI_DIMENSION,
    RAW_FEATURE_COUNT,
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (  # noqa: E402
    ATOM_NAMES,
    DEFAULT_LABEL_SEVERITY,
)


SCHEMA_VERSION = "camp_dp_v25_strict_convex_training_review_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
MODELS = {
    "CAMP-Static14D": ("static14d", "static", 14),
    "CAMP-Scene14D": ("scene14d", "scene", 14),
    "CAMP-Static9D": ("static9d", "static", 9),
    "CAMP-Scene9D": ("scene9d", "scene", 9),
}
FROZEN_TRAINING_CONFIG = (
    ROOT / "configs" / "integrations" / "diffusion_planner_v25_training_v1.json"
)
FROZEN_TRAINING_CONFIG_SHA256 = (
    "939a4cf4275daa205cad0aaf5aef25cfb65e5f9cc412e389191cae14d5044422"
)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _numeric(value: np.ndarray, shape: tuple[int, ...], name: str) -> np.ndarray:
    raw = np.asarray(value)
    if raw.shape != shape or raw.dtype.kind not in "fiu" or raw.dtype.kind == "b":
        raise ValueError(f"{name} numeric shape/type drifted")
    result = raw.astype(np.float64, copy=False)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be finite")
    return result


def _bool(value: np.ndarray, shape: tuple[int, ...], name: str) -> np.ndarray:
    result = np.asarray(value)
    if result.shape != shape or result.dtype != np.bool_:
        raise ValueError(f"{name} bool shape/type drifted")
    return result


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values, kind="mergesort")
    ordered = values[order]
    mass = weights[order]
    index = int(
        np.searchsorted(np.cumsum(mass), q * float(np.sum(mass)), side="left")
    )
    return float(ordered[min(index, ordered.size - 1)])


def _context_scaler(
    raw: np.ndarray, source: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    q05 = np.empty(RAW_FEATURE_COUNT, dtype=np.float64)
    q95 = np.empty(RAW_FEATURE_COUNT, dtype=np.float64)
    for index in range(RAW_FEATURE_COUNT):
        mask = source[:, index]
        if not np.any(mask):
            q05[index], q95[index] = 0.0, 1.0
            continue
        q05[index] = _weighted_quantile(raw[mask, index], weights[mask], 0.05)
        q95[index] = _weighted_quantile(raw[mask, index], weights[mask], 0.95)
        q95[index] = max(q95[index], q05[index] + 1e-6)
    return q05, q95


def _scene_phi(
    raw: np.ndarray,
    source: np.ndarray,
    q05: np.ndarray,
    q95: np.ndarray,
) -> np.ndarray:
    unit = np.clip((raw - q05) / (q95 - q05), 0.0, 1.0)
    phi = np.zeros((raw.shape[0], PHI_DIMENSION), dtype=np.float64)
    phi[:, 0] = 1.0
    phi[:, 1::2] = np.where(source, unit, 0.0)
    phi[:, 2::2] = np.where(source, 1.0 - unit, 0.0)
    phi /= 1.0 + np.sum(source, axis=1, keepdims=True)
    return phi


def _array_sha(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(b"\0")
    digest.update(",".join(str(item) for item in array.shape).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes())
    return digest.hexdigest()


def _leave_one_corridor_stability(
    train_weights: np.ndarray,
    selected: np.ndarray,
    record_weights: np.ndarray,
    corridor_ids: tuple[str, ...],
) -> dict[str, Any]:
    global_weight = np.sum(record_weights[:, None] * train_weights, axis=0)
    global_selection = np.bincount(
        selected, weights=record_weights, minlength=8
    ).astype(np.float64)
    corridor_array = np.asarray(corridor_ids)
    rows: list[dict[str, Any]] = []
    weight_shifts: list[float] = []
    selection_shifts: list[float] = []
    for corridor_id in sorted(set(corridor_ids)):
        keep = corridor_array != corridor_id
        excluded = float(np.sum(record_weights[~keep]))
        remaining = float(np.sum(record_weights[keep]))
        if remaining <= 0.0:
            rows.append(
                {
                    "cluster_id": corridor_id,
                    "excluded_record_weight": excluded,
                    "remaining_record_weight": remaining,
                    "status": "descriptive_only_single_cluster",
                    "mean_weight_l1_shift": None,
                    "selection_distribution_l1_shift": None,
                }
            )
            continue
        local = record_weights[keep] / remaining
        leave_weight = np.sum(local[:, None] * train_weights[keep], axis=0)
        leave_selection = np.bincount(
            selected[keep], weights=local, minlength=8
        ).astype(np.float64)
        weight_shift = float(np.sum(np.abs(leave_weight - global_weight)))
        selection_shift = float(np.sum(np.abs(leave_selection - global_selection)))
        weight_shifts.append(weight_shift)
        selection_shifts.append(selection_shift)
        rows.append(
            {
                "cluster_id": corridor_id,
                "excluded_record_weight": excluded,
                "remaining_record_weight": remaining,
                "status": "computed",
                "mean_weight_l1_shift": weight_shift,
                "selection_distribution_l1_shift": selection_shift,
            }
        )
    return {
        "analysis_kind": "postfit_cluster_exclusion_descriptive",
        "model_refit_performed": False,
        "interpretation": (
            "descriptive reweighting of fixed fitted outputs; "
            "not leave-cluster-out retraining stability"
        ),
        "cluster_unit": "corridor",
        "cluster_count": len(set(corridor_ids)),
        "record_count": len(corridor_ids),
        "rows": rows,
        "mean_weight_l1_shift_max": max(weight_shifts) if weight_shifts else None,
        "mean_weight_l1_shift_median": float(np.median(weight_shifts)) if weight_shifts else None,
        "selection_distribution_l1_shift_max": max(selection_shifts) if selection_shifts else None,
        "selection_distribution_l1_shift_median": (
            float(np.median(selection_shifts)) if selection_shifts else None
        ),
        "ticks_or_seeds_treated_as_independent_clusters": False,
    }


def review(artifact: Path, expected_root: str) -> dict[str, Any]:
    root = Path(artifact).resolve()
    seal = verify_complete_seal(root, expected_root, label="V25 CAMP training")
    expected_files = {
        "COMMAND",
        "HEADS",
        "model_parameters.npz",
        "model_registry.json",
        "model_reports.json",
        "report.json",
        "runtime_atom_scales.json",
        "static14d_runtime_weights.npy",
        "run.exit",
    }
    if set(seal["manifest_paths"]) != expected_files or (root / "run.exit").read_bytes() != b"0\n":
        raise ValueError("training artifact inventory/exit drifted")
    report = _json(root / "report.json")
    model_reports = _json(root / "model_reports.json")
    registry = _json(root / "model_registry.json")
    config_payload = _json(FROZEN_TRAINING_CONFIG)
    scene_contract = config_payload.get("scene_contract")
    audit_contract = config_payload.get("train_only_atom_audit_contract")
    label_contract = (
        audit_contract.get("causal_policy_distillation")
        if type(audit_contract) is dict
        else None
    )
    if (
        type(audit_contract) is not dict
        or audit_contract.get("scale_estimator")
        != "positive_support_block_weighted_inverse_empirical_q95"
        or audit_contract.get("scale_quantile") != 0.95
        or audit_contract.get("minimum_positive_candidate_rows") != 128
        or audit_contract.get("minimum_positive_semantic_blocks") != 20
        or type(label_contract) is not dict
        or label_contract.get("severity_14d") != DEFAULT_LABEL_SEVERITY.tolist()
        or label_contract.get("physical_penalty") != 100.0
        or label_contract.get("margin_multiplier") != 0.1
        or label_contract.get("margin_clip") != 2.0
        or label_contract.get("eligibility") != "source_valid_candidate_set"
        or label_contract.get("tie_break") != "lowest_candidate_index"
        or label_contract.get("closed_loop_outcome_consumed") is not False
        or label_contract.get("fresh_b2_consumed") is not False
        or label_contract.get("identity_fields_used_as_label_or_feature") is not False
        or type(scene_contract) is not dict
        or set(scene_contract)
        != {
            "context_schema_version",
            "no_v2i_phase_remaining_available",
            "phi",
            "theta_constraint",
            "runtime_projection",
            "softmax",
        }
        or scene_contract.get("context_schema_version") != CONTEXT_SCHEMA_VERSION
        or scene_contract.get("no_v2i_phase_remaining_available") is not False
        or scene_contract.get("phi") != "availability_masked_complement_lift"
        or scene_contract.get("theta_constraint") != "column_simplex"
        or scene_contract.get("runtime_projection") is not False
        or scene_contract.get("softmax") is not False
    ):
        raise ValueError("frozen Scene14D context-v2 contract drifted")
    if (
        report.get("schema_version") != "camp_dp_v25_strict_convex_training_artifact_v1"
        or report.get("status") != "passed_strict_convex_training"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("all_models_converged") is not True
        or report.get("all_solver_status_optimal") is not True
        or report.get("same_rows_labels_scales_and_block_weights") is not True
        or report.get("selection_eligibility") != "source_valid_candidate_set"
        or report.get("physical_feasible_mask_consumed_by_training") is not False
        or report.get("v24_rows_consumed_by_main_2x2") is not False
        or report.get("v24_without_raw_context_excluded_from_main_fair_comparison")
        is not True
        or report.get("static14d_full_v24_augmented_role")
        != "auxiliary_only_not_primary_method"
        or type(report.get("atom_audit_status_counts")) is not dict
        or set(report["atom_audit_status_counts"]) != {"PASS", "WARN", "FAIL"}
        or any(
            type(report["atom_audit_status_counts"][key]) is not int
            for key in report["atom_audit_status_counts"]
        )
        or sum(report["atom_audit_status_counts"].values()) != 14
        or report["atom_audit_status_counts"]["FAIL"] != 0
        or report.get("atom_audit_warn_policy")
        != "retain_all_14_atoms_and_report_preregistered_9d_group_and_minus_atom_ablations"
        or report.get("atom_audit_fail_policy") != "block_training_before_solver"
        or report.get("calibration_executed") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("outcome_fields_consumed") != []
        or model_reports != report.get("model_reports")
        or registry.get("fresh_or_outcome_consumed") is not False
        or Path(str(report.get("training_config"))).resolve()
        != FROZEN_TRAINING_CONFIG.resolve()
        or report.get("training_config_sha256")
        != FROZEN_TRAINING_CONFIG_SHA256
        or _sha256(FROZEN_TRAINING_CONFIG) != FROZEN_TRAINING_CONFIG_SHA256
        or report.get("training_config_payload") != config_payload
    ):
        raise ValueError("training report/registry contract drifted")
    audit_artifact = Path(str(report["atom_audit_artifact"]))
    audit_root = str(report["atom_audit_root_sha256"])
    audit_review = Path(str(report["atom_audit_review_artifact"]))
    audit_review_root = str(report["atom_audit_review_root_sha256"])
    verify_complete_seal(audit_artifact, audit_root, label="training atom audit")
    verify_complete_seal(audit_review, audit_review_root, label="training atom audit review")
    audit_report = _json(audit_artifact / "report.json")
    audit_review_report = _json(audit_review / "report.json")
    if (
        audit_report.get("atom_audit_status_counts")
        != report["atom_audit_status_counts"]
        or audit_review_report.get("atom_audit_status_counts")
        != report["atom_audit_status_counts"]
        or audit_report.get("atom_audit_status_scope")
        != "sealed_train_only_empirical_support_and_candidate_distinction_not_static_formula_or_source_correctness"
        or audit_review_report.get("atom_audit_status_scope")
        != audit_report.get("atom_audit_status_scope")
        or audit_report.get("static_correctness_prerequisite")
        != "formula_source_schema_clip_and_mask_failures_must_be_rejected_upstream"
        or audit_review_report.get("static_correctness_prerequisite")
        != audit_report.get("static_correctness_prerequisite")
        or audit_report.get("training_config_sha256")
        != FROZEN_TRAINING_CONFIG_SHA256
        or audit_report.get("training_config_payload") != config_payload
        or audit_report.get("train_only_atom_audit_contract")
        != audit_contract
        or audit_review_report.get("training_config_sha256")
        != FROZEN_TRAINING_CONFIG_SHA256
        or audit_report.get("fixed_dp_head") != FIXED_DP_HEAD
        or audit_review_report.get("fixed_dp_head") != FIXED_DP_HEAD
    ):
        raise ValueError("training did not preserve reviewed atom status authority")
    if report.get("model_parameters_sha256") != _sha256(root / "model_parameters.npz"):
        raise ValueError("model parameter archive SHA drifted")
    runtime_assets = report.get("runtime_assets")
    expected_runtime_assets = {
        "atom_scales": {
            "relative_path": "runtime_atom_scales.json",
            "sha256": _sha256(root / "runtime_atom_scales.json"),
            "model_scope": ["CAMP-Static14D", "CAMP-Scene14D"],
        },
        "static14d_weights": {
            "relative_path": "static14d_runtime_weights.npy",
            "sha256": _sha256(root / "static14d_runtime_weights.npy"),
            "model_scope": ["CAMP-Static14D"],
        },
    }
    if runtime_assets != expected_runtime_assets:
        raise ValueError("sealed runtime asset authority drifted")
    with np.load(audit_artifact / "training_rows.npz", allow_pickle=False) as rows:
        atoms14 = np.asarray(rows["normalized_atoms_14d"])
        raw_context = np.asarray(rows["raw_context"])
        context_source = np.asarray(rows["context_source_complete"])
        oracle = np.asarray(rows["oracle_indices"])
        margins = np.asarray(rows["margins"])
        source = np.asarray(rows["source_valid_mask"])
        weights = np.asarray(rows["record_weights"])
        corridor_values = np.asarray(rows["corridor_ids"])
        training_scales = np.asarray(rows["training_scales"])
    n = int(atoms14.shape[0])
    atoms14 = _numeric(atoms14, (n, 8, 14), "normalized_atoms_14d")
    raw_context = _numeric(raw_context, (n, RAW_FEATURE_COUNT), "raw_context")
    context_source = _bool(
        context_source, (n, RAW_FEATURE_COUNT), "context_source_complete"
    )
    phase_remaining_index = RAW_FEATURE_NAMES.index(
        "traffic_signal_phase_remaining_s"
    )
    if np.any(context_source[:, phase_remaining_index]):
        raise ValueError("no-V2I training exposed phase_remaining")
    margins = _numeric(margins, (n, 8), "margins")
    source = _bool(source, (n, 8), "source_valid")
    weights = _numeric(weights, (n,), "record_weights")
    if (
        corridor_values.shape != (n,)
        or corridor_values.dtype.kind != "U"
        or any(not str(item) for item in corridor_values.tolist())
    ):
        raise ValueError("training corridor cluster ids drifted")
    corridor_ids = tuple(str(item) for item in corridor_values.tolist())
    training_scales = _numeric(training_scales, (14,), "training_scales")
    if (
        oracle.shape != (n,)
        or oracle.dtype.kind not in "iu"
        or np.any(~np.any(source, axis=1))
        or np.any(weights <= 0.0)
        or not np.isclose(weights.sum(), 1.0, rtol=0.0, atol=1e-12)
    ):
        raise ValueError("training source labels/weights drifted")
    q05, q95 = _context_scaler(raw_context, context_source, weights)
    static_phi = np.zeros((n, PHI_DIMENSION), dtype=np.float64)
    static_phi[:, 0] = 1.0
    scene_phi = _scene_phi(raw_context, context_source, q05, q95)
    with np.load(root / "model_parameters.npz", allow_pickle=False) as archive:
        params = {key: archive[key] for key in archive.files}
    expected_keys = {
        "schema_version",
        "context_feature_names",
        "context_q05",
        "context_q95",
        "training_scales_14d",
    }
    for name, (key, mode, _atom_count) in MODELS.items():
        expected_keys.update(
            {
                f"{key}_theta",
                f"{key}_selected_indices",
                f"{key}_selection_margins",
                f"{key}_train_violations",
                f"{key}_cut_mask",
            }
        )
        if mode == "static":
            expected_keys.add(f"{key}_runtime_weights")
    if set(params) != expected_keys:
        raise ValueError("model parameter archive keyset drifted")
    if (
        params["schema_version"].shape != ()
        or str(params["schema_version"].item())
        != "camp_dp_v25_trained_model_parameters_v1"
        or params["context_feature_names"].tolist() != list(RAW_FEATURE_NAMES)
        or not np.array_equal(params["context_q05"], q05)
        or not np.array_equal(params["context_q95"], q95)
        or not np.array_equal(params["training_scales_14d"], training_scales)
    ):
        raise ValueError("context scaler/training scale parameter drifted")
    runtime_scales = _json(root / "runtime_atom_scales.json")
    runtime_scale_values = _numeric(
        np.asarray(runtime_scales.get("scales")),
        (14,),
        "runtime atom scales",
    )
    if runtime_scales != {
        "schema_version": "camp_dp_v25_runtime_atom_scales_v1",
        "atom_schema_version": "dp_camp_v10_14d",
        "atom_names": list(ATOM_NAMES),
        "scales": runtime_scale_values.tolist(),
        "scale_source": "sealed_train_only_block_weighted_positive_support",
        "calibration_or_fresh_consumed": False,
    } or not np.array_equal(runtime_scale_values, training_scales):
        raise ValueError("runtime atom scales differ from reviewed training scales")
    verified_models: dict[str, Any] = {}
    for name, (key, mode, atom_count) in MODELS.items():
        atoms = atoms14[:, :, :atom_count]
        phi = static_phi if mode == "static" else scene_phi
        theta = _numeric(params[f"{key}_theta"], (atom_count, PHI_DIMENSION), f"{name}.theta")
        if np.any(theta < 0.0) or not np.allclose(
            theta.sum(axis=0), 1.0, rtol=0.0, atol=1e-10
        ):
            raise ValueError(f"{name} theta violates column simplex")
        context_weights = phi @ theta.T
        if np.any(context_weights < 0.0) or not np.allclose(
            context_weights.sum(axis=1), 1.0, rtol=0.0, atol=1e-10
        ):
            raise ValueError(f"{name} runtime weights require forbidden projection")
        scores = np.einsum("nkr,nr->nk", atoms, context_weights)
        eligible_scores = np.where(source, scores, np.inf)
        selected = np.argmin(eligible_scores, axis=1).astype(np.int64)
        sorted_scores = np.sort(eligible_scores, axis=1)
        selection_margins = sorted_scores[:, 1] - sorted_scores[:, 0]
        selection_margins[np.sum(source, axis=1) < 2] = 0.0
        oracle_atoms = atoms[np.arange(n), oracle]
        candidate_values = margins + np.einsum(
            "nkr,nr->nk", oracle_atoms[:, None, :] - atoms, context_weights
        )
        candidate_values[~source] = -np.inf
        full_violations = np.maximum(np.max(candidate_values, axis=1), 0.0)
        cuts = _bool(params[f"{key}_cut_mask"], (n, 8), f"{name}.cut_mask")
        if np.any(~np.any(cuts, axis=1)):
            raise ValueError(f"{name} has a training row without a cut")
        restricted_values = np.where(cuts, candidate_values, -np.inf)
        restricted_violations = np.maximum(np.max(restricted_values, axis=1), 0.0)
        independent_gap = float(np.max(full_violations - restricted_violations))
        stored_selected = np.asarray(params[f"{key}_selected_indices"])
        stored_margins = _numeric(
            params[f"{key}_selection_margins"], (n,), f"{name}.selection_margins"
        )
        stored_violations = _numeric(
            params[f"{key}_train_violations"], (n,), f"{name}.train_violations"
        )
        model_report = model_reports.get(name)
        expected_cluster_stability = _leave_one_corridor_stability(
            context_weights,
            selected,
            weights,
            corridor_ids,
        )
        if (
            type(model_report) is not dict
            or stored_selected.shape != (n,)
            or stored_selected.dtype.kind not in "iu"
            or not np.array_equal(stored_selected, selected)
            or not np.array_equal(stored_margins, selection_margins)
            or not np.array_equal(stored_violations, full_violations)
            or independent_gap > 1e-6 + 1e-12
            or model_report.get("solver_name") != "CLARABEL"
            or model_report.get("solver_status") != "optimal"
            or model_report.get("converged") is not True
            or model_report.get("final_master_gap", np.inf) > 1e-6 + 1e-12
            or model_report.get("theta_sha256") != _array_sha(theta)
            or model_report.get("selected_index_sha256") != _array_sha(selected)
            or model_report.get("runtime_projection") is not False
            or model_report.get("softmax") is not False
            or model_report.get("selection_eligibility")
            != "source_valid_candidate_set"
            or model_report.get("physical_feasible_mask_consumed_by_training")
            is not False
            or model_report.get(
                "theta_column_interpretation_limited_by_redundant_context_lift"
            )
            is not True
            or model_report.get("cluster_ids_used_as_model_features") is not False
            or model_report.get("v24_rows_consumed_by_main_2x2") is not False
            or model_report.get(
                "v24_without_raw_context_excluded_from_main_fair_comparison"
            )
            is not True
            or model_report.get("static14d_full_v24_augmented_role")
            != "auxiliary_only_not_primary_method"
            or model_report.get("leave_one_corridor_stability")
            != expected_cluster_stability
            or model_report.get("outcome_or_fresh_consumed") is not False
        ):
            raise ValueError(f"{name} independent score/cut/selection review failed")
        if mode == "static" and not np.array_equal(
            params[f"{key}_runtime_weights"], theta[:, 0]
        ):
            raise ValueError(f"{name} runtime static weight drifted")
        verified_models[name] = {
            "atom_count": atom_count,
            "independent_master_gap": independent_gap,
            "selected_nonzero_count": int(np.sum(selected != 0)),
        }
    static_runtime = _numeric(
        np.load(root / "static14d_runtime_weights.npy", allow_pickle=False),
        (14,),
        "Static14D runtime weights",
    )
    if not np.array_equal(static_runtime, params["static14d_theta"][:, 0]):
        raise ValueError("Static14D sealed runtime weights differ from Theta column 0")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_strict_convex_training_review",
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(root),
        "reviewed_root_sha256": seal["root_sha256"],
        "snapshot_count": n,
        "selection_eligibility": "source_valid_candidate_set",
        "physical_feasible_mask_consumed_by_training": False,
        "models": verified_models,
        "phase_remaining_available_count": int(
            np.sum(context_source[:, phase_remaining_index])
        ),
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_bytes(
        (json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.artifact, args.root_sha256)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={_json(args.artifact / 'report.json')['camp_head']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 CAMP training review")
        print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))
    except BaseException as exc:
        _write_json(args.output_dir / "failure.json", {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)})
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="failed V25 CAMP training review")
        raise


if __name__ == "__main__":
    main()
