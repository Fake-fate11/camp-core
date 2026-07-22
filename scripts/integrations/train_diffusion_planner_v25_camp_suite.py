#!/usr/bin/env python3
"""Train the frozen fair V25 Static/Scene 14D suite and 9D ablations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
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
    RAW_FEATURE_NAMES,
)
from camp_core.integrations.diffusion_planner_v25_training import (  # noqa: E402
    MODEL_REGISTRY,
    train_v25_selector_suite,
)
from camp_core.integrations.diffusion_planner_v25_train_atom_audit import (  # noqa: E402
    ATOM_NAMES,
    DEFAULT_LABEL_SEVERITY,
)
from camp_core.outer_master.parametric_cvxpy_master import (  # noqa: E402
    V25ParametricMasterConfig,
)


SCHEMA_VERSION = "camp_dp_v25_strict_convex_training_artifact_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
AUDIT_STATUS = "passed_train_only_atom_audit_projection"
AUDIT_REVIEW_STATUS = "passed_independent_train_only_atom_audit_review"
MODEL_KEYS = {
    "CAMP-Static14D": "static14d",
    "CAMP-Scene14D": "scene14d",
    "CAMP-Static9D": "static9d",
    "CAMP-Scene9D": "scene9d",
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


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(
        (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()


def _tracked_dirty() -> bool:
    return bool(
        subprocess.check_output(
            ["git", "-C", str(ROOT), "status", "--short", "--untracked-files=no"],
            text=True,
        ).strip()
    )


def _config(path: Path) -> tuple[dict[str, Any], V25ParametricMasterConfig]:
    if (
        path.resolve() != FROZEN_TRAINING_CONFIG.resolve()
        or _sha256(path) != FROZEN_TRAINING_CONFIG_SHA256
    ):
        raise ValueError("V25 training config path/SHA drifted")
    payload = _json(path)
    if (
        payload.get("schema_version")
        != "camp_dp_v25_strict_convex_training_config_v1"
        or payload.get("model_registry") != list(MODEL_REGISTRY)
        or payload.get("primary_methods")
        != ["CAMP-Static14D", "CAMP-Scene14D"]
        or payload.get("paper_subset_ablations")
        != ["CAMP-Static9D", "CAMP-Scene9D"]
        or payload.get("candidate_count") != 8
        or payload.get("normalized_atom_clip") != 10.0
        or payload.get("closed_loop_outcome_consumed") is not False
        or payload.get("fresh_b2_opened") is not False
    ):
        raise ValueError("V25 training config top-level contract drifted")
    scene = payload.get("scene_contract")
    static = payload.get("static_contract")
    audit = payload.get("train_only_atom_audit_contract")
    labels = (
        audit.get("causal_policy_distillation")
        if type(audit) is dict
        else None
    )
    master = payload.get("master")
    if (
        type(audit) is not dict
        or audit.get("scale_estimator")
        != "positive_support_block_weighted_inverse_empirical_q95"
        or audit.get("scale_quantile") != 0.95
        or audit.get("minimum_positive_candidate_rows") != 128
        or audit.get("minimum_positive_semantic_blocks") != 20
        or type(labels) is not dict
        or labels.get("severity_14d") != DEFAULT_LABEL_SEVERITY.tolist()
        or labels.get("physical_penalty") != 100.0
        or labels.get("margin_multiplier") != 0.1
        or labels.get("margin_clip") != 2.0
        or labels.get("eligibility") != "source_valid_candidate_set"
        or labels.get("tie_break") != "lowest_candidate_index"
        or labels.get("closed_loop_outcome_consumed") is not False
        or labels.get("fresh_b2_consumed") is not False
        or labels.get("identity_fields_used_as_label_or_feature") is not False
        or type(scene) is not dict
        or set(scene)
        != {
            "context_schema_version",
            "no_v2i_phase_remaining_available",
            "phi",
            "theta_constraint",
            "runtime_projection",
            "softmax",
        }
        or scene.get("context_schema_version") != CONTEXT_SCHEMA_VERSION
        or scene.get("no_v2i_phase_remaining_available") is not False
        or scene.get("phi") != "availability_masked_complement_lift"
        or scene.get("theta_constraint") != "column_simplex"
        or scene.get("runtime_projection") is not False
        or scene.get("softmax") is not False
        or type(static) is not dict
        or set(static) != {"phi", "runtime_weight", "weight_constraint"}
        or static.get("phi") != "intercept_one_only"
        or static.get("runtime_weight") != "theta_column_0"
        or type(master) is not dict
        or set(master)
        != {
            "alpha",
            "l2_reg",
            "bt_anchor_reg",
            "max_iter",
            "tolerance",
            "solver",
            "solver_options",
            "bt_iterations",
            "bt_learning_rate",
            "bt_l2_reg",
            "bt_max_pairs",
        }
        or type(master.get("solver_options")) is not dict
    ):
        raise ValueError("V25 training config mathematical contract drifted")
    config = V25ParametricMasterConfig(
        alpha=float(master["alpha"]),
        l2_reg=float(master["l2_reg"]),
        bt_anchor_reg=float(master["bt_anchor_reg"]),
        max_iter=int(master["max_iter"]),
        tolerance=float(master["tolerance"]),
        solver=str(master["solver"]),
        solver_options=tuple(master["solver_options"].items()),
        bt_iterations=int(master["bt_iterations"]),
        bt_learning_rate=float(master["bt_learning_rate"]),
        bt_l2_reg=float(master["bt_l2_reg"]),
        bt_max_pairs=int(master["bt_max_pairs"]),
    )
    config.validate()
    return payload, config


def _cut_mask(rows: tuple[tuple[int, ...], ...], count: int) -> np.ndarray:
    if len(rows) != count:
        raise ValueError("cut rows do not match training record count")
    result = np.zeros((count, 8), dtype=np.bool_)
    for record_index, candidates in enumerate(rows):
        for candidate_index in candidates:
            if not 0 <= candidate_index < 8:
                raise ValueError("cut index is outside fixed K=8")
            result[record_index, candidate_index] = True
    return result


def train(
    *,
    atom_audit_artifact: Path,
    atom_audit_root_sha256: str,
    atom_audit_review_artifact: Path,
    atom_audit_review_root_sha256: str,
    training_config: Path,
    output_dir: Path,
) -> str:
    if _tracked_dirty():
        raise ValueError("CAMP tracked worktree must be clean")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    started = time.perf_counter()
    try:
        verify_complete_seal(
            atom_audit_artifact, atom_audit_root_sha256, label="V25 atom audit"
        )
        verify_complete_seal(
            atom_audit_review_artifact,
            atom_audit_review_root_sha256,
            label="V25 atom audit review",
        )
        audit_report = _json(atom_audit_artifact / "report.json")
        review_report = _json(atom_audit_review_artifact / "report.json")
        config_payload, solver_config = _config(training_config)
        audit_status_counts = audit_report.get("atom_audit_status_counts")
        if (
            audit_report.get("status") != AUDIT_STATUS
            or review_report.get("status") != AUDIT_REVIEW_STATUS
            or Path(str(review_report.get("reviewed_artifact"))).resolve()
            != atom_audit_artifact.resolve()
            or review_report.get("reviewed_root_sha256") != atom_audit_root_sha256
            or review_report.get("fresh_b2_opened") is not False
            or review_report.get("outcome_fields_consumed") != []
            or audit_report.get("fixed_dp_head") != FIXED_DP_HEAD
            or review_report.get("fixed_dp_head") != FIXED_DP_HEAD
            or type(audit_status_counts) is not dict
            or set(audit_status_counts) != {"PASS", "WARN", "FAIL"}
            or any(type(audit_status_counts[key]) is not int for key in audit_status_counts)
            or sum(audit_status_counts.values()) != 14
            or audit_status_counts["FAIL"] != 0
            or review_report.get("atom_audit_status_counts") != audit_status_counts
            or audit_report.get("atom_audit_status_scope")
            != "sealed_train_only_empirical_support_and_candidate_distinction_not_static_formula_or_source_correctness"
            or review_report.get("atom_audit_status_scope")
            != audit_report.get("atom_audit_status_scope")
            or audit_report.get("static_correctness_prerequisite")
            != "formula_source_schema_clip_and_mask_failures_must_be_rejected_upstream"
            or review_report.get("static_correctness_prerequisite")
            != audit_report.get("static_correctness_prerequisite")
            or audit_report.get("training_config_sha256")
            != FROZEN_TRAINING_CONFIG_SHA256
            or audit_report.get("training_config_payload") != config_payload
            or audit_report.get("train_only_atom_audit_contract")
            != config_payload.get("train_only_atom_audit_contract")
            or review_report.get("training_config_sha256")
            != FROZEN_TRAINING_CONFIG_SHA256
        ):
            raise ValueError("atom audit/review authority drifted")
        with np.load(atom_audit_artifact / "training_rows.npz", allow_pickle=False) as archive:
            atoms = archive["normalized_atoms_14d"]
            raw_context = archive["raw_context"]
            context_source = archive["context_source_complete"]
            oracle = archive["oracle_indices"]
            margins = archive["margins"]
            source = archive["source_valid_mask"]
            record_weights = archive["record_weights"]
            corridor_ids = archive["corridor_ids"]
            training_scales = archive["training_scales"]
        suite = train_v25_selector_suite(
            atoms,
            raw_context,
            context_source,
            oracle,
            margins,
            source,
            record_weights,
            stability_cluster_ids=tuple(str(item) for item in corridor_ids.tolist()),
            config=solver_config,
        )
        parameter_arrays: dict[str, np.ndarray] = {
            "schema_version": np.asarray("camp_dp_v25_trained_model_parameters_v1"),
            "context_feature_names": np.asarray(RAW_FEATURE_NAMES),
            "context_q05": suite["CAMP-Scene14D"].context_scaler.q05,
            "context_q95": suite["CAMP-Scene14D"].context_scaler.q95,
            "training_scales_14d": np.asarray(training_scales, dtype=np.float64),
        }
        model_reports: dict[str, Any] = {}
        for name, model in suite.items():
            key = MODEL_KEYS[name]
            parameter_arrays[f"{key}_theta"] = model.theta
            parameter_arrays[f"{key}_selected_indices"] = model.selected_indices
            parameter_arrays[f"{key}_selection_margins"] = model.selection_margins
            parameter_arrays[f"{key}_train_violations"] = model.result.train_violations
            parameter_arrays[f"{key}_cut_mask"] = _cut_mask(
                model.result.cut_indices_per_scene, atoms.shape[0]
            )
            if model.mode == "static":
                parameter_arrays[f"{key}_runtime_weights"] = model.theta[:, 0]
            model_reports[name] = model.report
        np.savez_compressed(output_dir / "model_parameters.npz", **parameter_arrays)
        model_parameter_sha = _sha256(output_dir / "model_parameters.npz")
        runtime_scales = {
            "schema_version": "camp_dp_v25_runtime_atom_scales_v1",
            "atom_schema_version": "dp_camp_v10_14d",
            "atom_names": list(ATOM_NAMES),
            "scales": np.asarray(training_scales, dtype=np.float64).tolist(),
            "scale_source": "sealed_train_only_block_weighted_positive_support",
            "calibration_or_fresh_consumed": False,
        }
        _write_json(output_dir / "runtime_atom_scales.json", runtime_scales)
        static_runtime_weights = np.asarray(
            suite["CAMP-Static14D"].theta[:, 0], dtype=np.float64
        )
        np.save(output_dir / "static14d_runtime_weights.npy", static_runtime_weights)
        registry = {
            "schema_version": "camp_dp_v25_model_registry_v1",
            "models": [
                {
                    "name": name,
                    "parameter_prefix": MODEL_KEYS[name],
                    "mode": MODEL_REGISTRY[name][0],
                    "active_atom_indices": list(MODEL_REGISTRY[name][1]),
                    "primary_method": name.endswith("14D"),
                    "paper_subset_ablation": name.endswith("9D"),
                }
                for name in MODEL_REGISTRY
            ],
            "candidate0_semantics": "operational_default_alias_from_same_forward",
            "fresh_or_outcome_consumed": False,
        }
        _write_json(output_dir / "model_registry.json", registry)
        _write_json(output_dir / "model_reports.json", model_reports)
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "passed_strict_convex_training",
            "camp_head": _git_head(),
            "fixed_dp_head": FIXED_DP_HEAD,
            "atom_audit_artifact": str(atom_audit_artifact.resolve()),
            "atom_audit_root_sha256": atom_audit_root_sha256,
            "atom_audit_review_artifact": str(atom_audit_review_artifact.resolve()),
            "atom_audit_review_root_sha256": atom_audit_review_root_sha256,
            "atom_audit_status_counts": audit_status_counts,
            "atom_audit_warn_policy": (
                "retain_all_14_atoms_and_report_preregistered_9d_group_and_minus_atom_ablations"
            ),
            "atom_audit_fail_policy": "block_training_before_solver",
            "training_config": str(training_config.resolve()),
            "training_config_sha256": _sha256(training_config),
            "training_config_payload": config_payload,
            "model_parameters_sha256": model_parameter_sha,
            "runtime_assets": {
                "atom_scales": {
                    "relative_path": "runtime_atom_scales.json",
                    "sha256": _sha256(output_dir / "runtime_atom_scales.json"),
                    "model_scope": ["CAMP-Static14D", "CAMP-Scene14D"],
                },
                "static14d_weights": {
                    "relative_path": "static14d_runtime_weights.npy",
                    "sha256": _sha256(
                        output_dir / "static14d_runtime_weights.npy"
                    ),
                    "model_scope": ["CAMP-Static14D"],
                },
            },
            "model_reports": model_reports,
            "total_offline_wall_seconds": float(time.perf_counter() - started),
            "solver_wall_seconds_sum": float(
                sum(model.result.wall_seconds for model in suite.values())
            ),
            "all_models_converged": all(
                model.result.converged for model in suite.values()
            ),
            "all_solver_status_optimal": all(
                model.result.solver_status == "optimal" for model in suite.values()
            ),
            "same_rows_labels_scales_and_block_weights": True,
            "selection_eligibility": "source_valid_candidate_set",
            "physical_feasible_mask_consumed_by_training": False,
            "v24_rows_consumed_by_main_2x2": False,
            "v24_without_raw_context_excluded_from_main_fair_comparison": True,
            "static14d_full_v24_augmented_role": "auxiliary_only_not_primary_method",
            "calibration_executed": False,
            "fresh_b2_opened": False,
            "outcome_fields_consumed": [],
        }
        _write_json(output_dir / "report.json", report)
        (output_dir / "HEADS").write_text(
            f"camp_head={report['camp_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (output_dir / "run.exit").write_text("0\n", encoding="ascii")
        return seal_artifact(output_dir, label="V25 strict convex training")
    except BaseException as exc:
        _write_json(output_dir / "failure.json", {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)})
        (output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(output_dir, label="failed V25 strict convex training")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atom-audit-artifact", type=Path, required=True)
    parser.add_argument("--atom-audit-root-sha256", required=True)
    parser.add_argument("--atom-audit-review-artifact", type=Path, required=True)
    parser.add_argument("--atom-audit-review-root-sha256", required=True)
    parser.add_argument("--training-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = train(**vars(args))
    print(json.dumps({"status": "passed", "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
