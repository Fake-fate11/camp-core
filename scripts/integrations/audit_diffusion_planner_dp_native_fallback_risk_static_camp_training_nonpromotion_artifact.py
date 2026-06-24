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

from scripts.integrations.train_diffusion_planner_dp_native_fallback_risk_static_camp import (  # noqa: E402
    COMPLETE_STATUS as TRAINING_COMPLETE_STATUS,
    TRAINING_SCHEMA_VERSION,
)
from scripts.integrations.validate_dp_native_fallback_risk_training_sufficiency_preflight import (  # noqa: E402
    APPROVED_ATOM_NAMES,
    APPROVED_ATOM_SCHEMA,
)


AUDIT_SCHEMA_VERSION = "dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_v1"
DISABLED_STATUS = "dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_default_off_disabled"
COMPLETE_STATUS = "dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_complete"
REJECT_STATUS = "dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_rejected"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"

SOURCE_TRAINING_TRUE_FLAGS = (
    "training_authorized",
    "training_execution_authorized",
    "training_executed",
    "camp_retraining_authorized_now",
    "fallback_risk_training_authorized_now",
    "fixed_dp_candidate_reranking_only",
    "fallback_only_training",
)

FORBIDDEN_SOURCE_FLAGS = (
    "replay_execution_authorized",
    "candidate_generation_authorized",
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
    "feasible_ranking_master_change_authorized",
    "hard_feasibility_relaxation_authorized",
    "all_infeasible_records_added_to_feasible_training",
    "production_selector_change_authorized",
    "online_selector_change_authorized",
)

ANALYSIS_FALSE_FIELDS = (
    "replay_executed",
    "candidate_generation_executed",
    "diffusion_planner_executed",
    "diffusion_planner_modified",
    "trajectory_generation_executed",
    "trajectory_rewrite_executed",
    "postprocess_postselection_executed",
    "selector_promotion_executed",
    "atom_promotion_executed",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Default-off read-only audit for post-training non-promotion "
            "fallback-risk static CAMP artifacts."
        )
    )
    parser.add_argument("--training_summary_json", type=Path, required=True)
    parser.add_argument("--expected_training_summary_sha256", required=True)
    parser.add_argument("--weights_json", type=Path, required=True)
    parser.add_argument("--expected_weights_json_sha256", required=True)
    parser.add_argument("--weights_npy", type=Path, required=True)
    parser.add_argument("--expected_weights_npy_sha256", required=True)
    parser.add_argument("--atom_scales_json", type=Path, required=True)
    parser.add_argument("--expected_atom_scales_json_sha256", required=True)
    parser.add_argument("--training_commit", required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_default_off_fallback_risk_static_camp_training_nonpromotion_artifact_audit",
        action="store_true",
        help="Explicit opt-in required before reading trained CAMP artifacts.",
    )
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_fallback_risk_static_camp_training_nonpromotion_artifact(
        training_summary_json=args.training_summary_json,
        expected_training_summary_sha256=args.expected_training_summary_sha256,
        weights_json=args.weights_json,
        expected_weights_json_sha256=args.expected_weights_json_sha256,
        weights_npy=args.weights_npy,
        expected_weights_npy_sha256=args.expected_weights_npy_sha256,
        atom_scales_json=args.atom_scales_json,
        expected_atom_scales_json_sha256=args.expected_atom_scales_json_sha256,
        training_commit=args.training_commit,
        current_camp_head=args.current_camp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_default_off_fallback_risk_static_camp_training_nonpromotion_artifact_audit,
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


def audit_fallback_risk_static_camp_training_nonpromotion_artifact(
    *,
    training_summary_json: Path,
    expected_training_summary_sha256: str,
    weights_json: Path,
    expected_weights_json_sha256: str,
    weights_npy: Path,
    expected_weights_npy_sha256: str,
    atom_scales_json: Path,
    expected_atom_scales_json_sha256: str,
    training_commit: str,
    current_camp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
) -> dict[str, Any]:
    report = _empty_report(
        enabled=enabled,
        training_commit=training_commit,
        current_camp_head=current_camp_head,
        required_dp_head=required_dp_head,
    )
    if not enabled:
        return report

    errors: list[str] = []
    expected_hashes = {
        "training_summary_json": expected_training_summary_sha256,
        "weights_json": expected_weights_json_sha256,
        "weights_npy": expected_weights_npy_sha256,
        "atom_scales_json": expected_atom_scales_json_sha256,
    }
    for name, value in expected_hashes.items():
        _validate_sha_literal(value, f"expected_{name}_sha256", errors)
    for field, value in (
        ("training_commit", training_commit),
        ("current_camp_head", current_camp_head),
        ("required_dp_head", required_dp_head),
    ):
        _validate_git_sha_literal(value, field, errors)
    if required_dp_head != FIXED_DP_HEAD:
        errors.append("required_dp_head_not_fixed_tieriv_commit")

    path_by_name = {
        "training_summary_json": training_summary_json,
        "weights_json": weights_json,
        "weights_npy": weights_npy,
        "atom_scales_json": atom_scales_json,
    }
    payloads: dict[str, Any] = {}
    for name, path in path_by_name.items():
        actual = _sha256_file_if_present(path, name, errors)
        if actual is not None:
            report["source_hashes"][name] = actual
            if _is_sha256(expected_hashes[name]) and actual != expected_hashes[name]:
                errors.append(f"{name}_sha256_mismatch")
        if name.endswith("_json"):
            payloads[name] = _load_json(path, name, errors)

    weights_from_json = _validate_weights_json(payloads.get("weights_json"), errors)
    weights_from_npy = _validate_weights_npy(weights_npy, errors)
    scales = _validate_atom_scales(payloads.get("atom_scales_json"), errors)
    _validate_training_summary(
        payloads.get("training_summary_json"),
        expected_hashes,
        weights_from_json,
        weights_from_npy,
        scales,
        errors,
    )

    report["artifact_checks"] = {
        "training_summary_sha256_match": report["source_hashes"].get("training_summary_json")
        == expected_training_summary_sha256,
        "weights_json_sha256_match": report["source_hashes"].get("weights_json")
        == expected_weights_json_sha256,
        "weights_npy_sha256_match": report["source_hashes"].get("weights_npy")
        == expected_weights_npy_sha256,
        "atom_scales_json_sha256_match": report["source_hashes"].get("atom_scales_json")
        == expected_atom_scales_json_sha256,
        "weights_json_simplex_nonnegative": _is_simplex_nonnegative(weights_from_json),
        "weights_npy_simplex_nonnegative": _is_simplex_nonnegative(weights_from_npy),
        "weights_json_matches_npy": _vectors_close(weights_from_json, weights_from_npy),
        "atom_scales_strictly_positive": bool(scales) and all(value > 0.0 for value in scales),
        "atom_schema_version": APPROVED_ATOM_SCHEMA,
        "num_atoms": len(APPROVED_ATOM_NAMES),
        "score_expression": "score_k(w)=a_k^T w",
    }
    report["final_decision"] = _decision(
        status=REJECT_STATUS if errors else COMPLETE_STATUS,
        passed=not errors,
        enabled=True,
        errors=errors,
    )
    return report


def _empty_report(
    *,
    enabled: bool,
    training_commit: str,
    current_camp_head: str,
    required_dp_head: str,
) -> dict[str, Any]:
    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "analysis": {
            "name": "dp_native_fallback_risk_static_camp_training_nonpromotion_artifact_audit_v1",
            "default_off": True,
            "enabled": bool(enabled),
            "read_only_existing_training_artifacts": True,
            "fixed_dp_candidate_reranking_only": True,
            "fallback_only_training_artifact": True,
            "score_expression": "score_k(w)=a_k^T w",
            "diffusion_planner_fixed_head": required_dp_head,
            "training_commit": training_commit,
            "current_camp_head": current_camp_head,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "diffusion_planner_executed": False,
            "diffusion_planner_modified": False,
            "trajectory_generation_executed": False,
            "trajectory_rewrite_executed": False,
            "postprocess_postselection_executed": False,
            "selector_promotion_executed": False,
            "atom_promotion_executed": False,
            "deployment_executed": False,
        },
        "source_hashes": {},
        "artifact_checks": {},
        "final_decision": _decision(
            status=DISABLED_STATUS,
            passed=True,
            enabled=enabled,
            errors=[],
        ),
    }


def _validate_training_summary(
    summary: Any,
    expected_hashes: dict[str, str],
    weights_from_json: np.ndarray | None,
    weights_from_npy: np.ndarray | None,
    scales: list[float],
    errors: list[str],
) -> None:
    if not isinstance(summary, dict):
        errors.append("training_summary_not_object")
        return
    if summary.get("schema_version") != TRAINING_SCHEMA_VERSION:
        errors.append("training_summary_schema_version_mismatch")
    analysis = summary.get("analysis")
    if not isinstance(analysis, dict):
        errors.append("training_analysis_missing")
    else:
        for field in ("default_off", "reads_fixed_artifacts_only", "fallback_only"):
            if analysis.get(field) is not True:
                errors.append(f"training_analysis_{field}_not_true")
        for field in ANALYSIS_FALSE_FIELDS:
            if analysis.get(field) is not False:
                errors.append(f"training_analysis_{field}_not_false")

    training = summary.get("training")
    if not isinstance(training, dict):
        errors.append("training_block_missing")
    else:
        _validate_training_block(training, weights_from_json, weights_from_npy, scales, errors)

    outputs = summary.get("output_artifacts")
    if not isinstance(outputs, dict):
        errors.append("output_artifacts_missing")
    else:
        for artifact_name, expected_key in (
            ("weights_json_sha256", "weights_json"),
            ("weights_npy_sha256", "weights_npy"),
            ("atom_scales_json_sha256", "atom_scales_json"),
        ):
            if outputs.get(artifact_name) != expected_hashes[expected_key]:
                errors.append(f"output_artifacts_{artifact_name}_mismatch")

    decision = summary.get("final_decision")
    if not isinstance(decision, dict):
        errors.append("training_final_decision_missing")
        return
    if decision.get("status") != TRAINING_COMPLETE_STATUS:
        errors.append("training_final_decision_status_not_complete")
    if decision.get("passed") is not True:
        errors.append("training_final_decision_not_passed")
    if decision.get("errors") not in ([], None):
        errors.append("training_final_decision_errors_nonempty")
    for flag in SOURCE_TRAINING_TRUE_FLAGS:
        if decision.get(flag) is not True:
            errors.append(f"training_final_decision_{flag}_not_true")
    for flag in FORBIDDEN_SOURCE_FLAGS:
        if decision.get(flag) is not False:
            errors.append(f"training_final_decision_{flag}_not_false")


def _validate_training_block(
    training: dict[str, Any],
    weights_from_json: np.ndarray | None,
    weights_from_npy: np.ndarray | None,
    scales: list[float],
    errors: list[str],
) -> None:
    if training.get("training_type") != "dp_native_fallback_risk_static_candidate_reranking":
        errors.append("training_type_not_static_reranking")
    if training.get("training_scope") != "fallback_only_all_infeasible_fixed_dp_candidates":
        errors.append("training_scope_not_fallback_only")
    if training.get("score_expression") != "score_k(w)=a_k^T w":
        errors.append("training_score_expression_not_affine")
    if training.get("objective") not in {"simplex_hinge_cvar_l2", "simplex_hinge_mean_l2"}:
        errors.append("training_objective_not_simplex_hinge_l2")
    if training.get("risk_type") not in {"cvar", "mean"}:
        errors.append("training_risk_type_invalid")
    for field in ("training_records", "validation_records", "num_candidates"):
        value = training.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            errors.append(f"training_{field}_not_positive_int")
    if training.get("num_atoms") != len(APPROVED_ATOM_NAMES):
        errors.append("training_num_atoms_mismatch")
    if training.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("training_atom_schema_version_mismatch")
    if tuple(training.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("training_atom_names_mismatch")
    trained_weights = _vector(training.get("trained_weights"), "training_trained_weights", errors)
    if not _is_simplex_nonnegative(trained_weights):
        errors.append("training_trained_weights_not_simplex_nonnegative")
    if not _vectors_close(trained_weights, weights_from_json):
        errors.append("training_trained_weights_json_mismatch")
    if not _vectors_close(trained_weights, weights_from_npy):
        errors.append("training_trained_weights_npy_mismatch")
    for field in ("weights_sum", "weights_min", "weights_max"):
        value = training.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            errors.append(f"training_{field}_not_finite")
    if abs(float(training.get("weights_sum", float("nan"))) - 1.0) > 1e-8:
        errors.append("training_weights_sum_not_one")
    if float(training.get("weights_min", float("nan"))) < -1e-10:
        errors.append("training_weights_min_negative")
    if float(training.get("weights_max", float("nan"))) > 1.0 + 1e-10:
        errors.append("training_weights_max_above_one")
    if not scales:
        errors.append("training_atom_scales_unvalidated")


def _validate_weights_json(payload: Any, errors: list[str]) -> np.ndarray | None:
    if not isinstance(payload, dict):
        errors.append("weights_json_not_object")
        return None
    if payload.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("weights_json_atom_schema_version_mismatch")
    if tuple(payload.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("weights_json_atom_names_mismatch")
    if payload.get("score_expression") != "score_k(w)=a_k^T w":
        errors.append("weights_json_score_expression_not_affine")
    if payload.get("fallback_only") is not True:
        errors.append("weights_json_not_fallback_only")
    if payload.get("selector_promotion_executed") is not False:
        errors.append("weights_json_selector_promotion_executed_not_false")
    weights = _vector(payload.get("weights"), "weights_json_weights", errors)
    if not _is_simplex_nonnegative(weights):
        errors.append("weights_json_weights_not_simplex_nonnegative")
    return weights


def _validate_weights_npy(path: Path, errors: list[str]) -> np.ndarray | None:
    try:
        array = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        errors.append(f"weights_npy_unreadable:{type(exc).__name__}")
        return None
    if array.shape != (len(APPROVED_ATOM_NAMES),):
        errors.append("weights_npy_shape_mismatch")
        return None
    weights = array.astype(np.float64)
    if not np.all(np.isfinite(weights)):
        errors.append("weights_npy_not_finite")
    if not _is_simplex_nonnegative(weights):
        errors.append("weights_npy_not_simplex_nonnegative")
    return weights


def _validate_atom_scales(payload: Any, errors: list[str]) -> list[float]:
    if not isinstance(payload, dict):
        errors.append("atom_scales_json_not_object")
        return []
    if payload.get("atom_schema_version") != APPROVED_ATOM_SCHEMA:
        errors.append("atom_scales_json_atom_schema_version_mismatch")
    if tuple(payload.get("atom_names") or ()) != APPROVED_ATOM_NAMES:
        errors.append("atom_scales_json_atom_names_mismatch")
    scales = _vector(payload.get("scales"), "atom_scales_json_scales", errors)
    if len(scales) != len(APPROVED_ATOM_NAMES):
        errors.append("atom_scales_json_scale_count_mismatch")
    if any(value <= 0.0 for value in scales):
        errors.append("atom_scales_json_not_strictly_positive")
    return [float(value) for value in scales]


def _load_json(path: Path, name: str, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{name}_unreadable:{type(exc).__name__}")
        return {}


def _vector(value: Any, field: str, errors: list[str]) -> np.ndarray | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{field}_not_nonempty_vector")
        return None
    parsed = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            errors.append(f"{field}_not_finite_numeric")
            return None
        parsed.append(float(item))
    if len(parsed) != len(APPROVED_ATOM_NAMES):
        errors.append(f"{field}_dimension_mismatch")
        return None
    return np.asarray(parsed, dtype=np.float64)


def _is_simplex_nonnegative(weights: np.ndarray | None) -> bool:
    if weights is None or weights.shape != (len(APPROVED_ATOM_NAMES),):
        return False
    if not np.all(np.isfinite(weights)):
        return False
    return bool(np.min(weights) >= -1e-10 and abs(float(np.sum(weights)) - 1.0) <= 1e-8)


def _vectors_close(left: np.ndarray | None, right: np.ndarray | None) -> bool:
    if left is None or right is None:
        return False
    if left.shape != right.shape:
        return False
    return bool(np.allclose(left, right, rtol=1e-9, atol=1e-10))


def _validate_sha_literal(value: Any, field: str, errors: list[str]) -> None:
    if not _is_sha256(value):
        errors.append(f"{field}_invalid")


def _validate_git_sha_literal(value: Any, field: str, errors: list[str]) -> None:
    if not _is_git_sha(value):
        errors.append(f"{field}_invalid")


def _is_git_sha(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(char in "0123456789abcdef" for char in value.lower())


def _sha256_file_if_present(path: Path, name: str, errors: list[str]) -> str | None:
    try:
        return _sha256_file(path)
    except OSError as exc:
        errors.append(f"{name}_unreadable:{type(exc).__name__}")
        return None


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
    return {
        "status": status,
        "passed": bool(passed),
        "enabled": bool(enabled),
        "errors": sorted(set(errors)),
        "post_training_nonpromotion_artifact_audit_passed": bool(enabled and passed),
        "training_artifacts_nonpromotion": bool(enabled and passed),
        "fixed_dp_candidate_reranking_only": bool(enabled and passed),
        "fallback_only_training_artifact": bool(enabled and passed),
        "score_expression": "score_k(w)=a_k^T w",
        "training_authorized": False,
        "training_execution_authorized": False,
        "camp_retraining_authorized_now": False,
        "fallback_risk_training_authorized_now": False,
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
        "deployment_authorized": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    analysis = report["analysis"]
    checks = report.get("artifact_checks") or {}
    lines = [
        "# DP Native Fallback Risk Static CAMP Training Nonpromotion Artifact Audit",
        "",
        "```text",
        f"status={decision['status']}",
        f"passed={decision['passed']}",
        f"enabled={decision['enabled']}",
        f"post_training_nonpromotion_artifact_audit_passed={decision['post_training_nonpromotion_artifact_audit_passed']}",
        f"training_artifacts_nonpromotion={decision['training_artifacts_nonpromotion']}",
        f"fixed_dp_candidate_reranking_only={decision['fixed_dp_candidate_reranking_only']}",
        f"fallback_only_training_artifact={decision['fallback_only_training_artifact']}",
        f"score_expression={decision['score_expression']}",
        f"training_commit={analysis['training_commit']}",
        f"current_camp_head={analysis['current_camp_head']}",
        f"required_dp_head={analysis['diffusion_planner_fixed_head']}",
        "training_authorized=False",
        "training_execution_authorized=False",
        "camp_retraining_authorized_now=False",
        "fallback_risk_training_authorized_now=False",
        "replay_execution_authorized=False",
        "candidate_generation_authorized=False",
        "dp_modification_authorized=False",
        "selector_promotion_authorized=False",
        "atom_promotion_authorized=False",
        "deployable_checkpoint_claim_authorized=False",
        "safety_benefit_claim_authorized=False",
        "camp_over_dp_top1_claim_authorized=False",
        "deployment_authorized=False",
        "```",
        "",
    ]
    if checks:
        lines.extend(
            [
                "## Artifact Checks",
                "",
                "```text",
            ]
        )
        for key in sorted(checks):
            lines.append(f"{key}={checks[key]}")
        lines.extend(["```", ""])
    if decision["errors"]:
        lines.extend(["## Errors", "", "```text"])
        lines.extend(str(error) for error in decision["errors"])
        lines.extend(["```", ""])
    lines.append(
        "This audit only reads existing training artifacts. It does not execute "
        "Diffusion Planner, generate or rewrite trajectories, retrain CAMP, "
        "promote runtime selectors or atoms, deploy a checkpoint, or claim "
        "safety benefit."
    )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
