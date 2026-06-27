from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_shadow_selector_artifact_manifest import (
    APPROVED_ATOM_NAMES,
    ATOM_SCHEMA_VERSION,
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    EXPECTED_ATOM_COUNT,
    EXPECTED_CANDIDATE_COUNT,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    SCORE_EXPRESSION,
    build_report,
    main,
)


CAMP_HEAD = "3f599da6987367bb9bb4a4c60fd3e910cd988deb"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _base_weights() -> np.ndarray:
    return np.full((EXPECTED_ATOM_COUNT,), 1.0 / EXPECTED_ATOM_COUNT, dtype=np.float64)


def _write_artifacts(
    tmp_path: Path,
    *,
    weights: np.ndarray | None = None,
    training_summary_hash_override: str | None = None,
    audit_missing_scope: bool = False,
) -> dict[str, Path]:
    if weights is None:
        weights = _base_weights()
    weights_npy = tmp_path / "offline_weights_dp_fallback_risk_static.npy"
    np.save(weights_npy, weights)
    weights_json = _write_json(
        tmp_path / "offline_weights_dp_fallback_risk_static.json",
        {
            "atom_schema_version": ATOM_SCHEMA_VERSION,
            "atom_names": list(APPROVED_ATOM_NAMES),
            "weights": weights.tolist(),
            "score_expression": SCORE_EXPRESSION,
            "fallback_only": True,
            "selector_promotion_executed": False,
            "source_hashes": {},
        },
    )
    atom_scales = _write_json(
        tmp_path / "atom_scales_dp_fallback_risk_static.json",
        {
            "atom_schema_version": ATOM_SCHEMA_VERSION,
            "atom_names": list(APPROVED_ATOM_NAMES),
            "scales": [1.0 for _ in APPROVED_ATOM_NAMES],
            "source_scale_manifest_sha256": "1" * 64,
        },
    )
    fallback_master = _write_json(
        tmp_path / "fallback_master_config.json",
        {
            "schema_version": "dp_native_fallback_risk_fallback_master_config_v1",
            "fallback_only": True,
            "feasible_branch_records_allowed": False,
            "all_infeasible_records_added_to_feasible_training": False,
            "all_infeasible_records_relabelled_feasible": False,
            "hard_feasibility_relaxation_authorized": False,
            "feasible_ranking_master_change_authorized": False,
            "score_expression": SCORE_EXPRESSION,
            "atoms_fixed_nonnegative": True,
            "fallback_label_is_deployed_atom": False,
            "margins_nonnegative": True,
            "simplex_cvar_l2_convex": True,
        },
    )
    weights_npy_sha = _sha(weights_npy)
    if training_summary_hash_override is not None:
        weights_npy_sha = training_summary_hash_override
    training_summary = _write_json(
        tmp_path / "training_summary.json",
        {
            "schema_version": "dp_native_fallback_risk_static_camp_training_v1",
            "analysis": {
                "replay_executed": False,
                "candidate_generation_executed": False,
                "diffusion_planner_modified": False,
                "trajectory_rewrite_executed": False,
            },
            "training": {
                "score_expression": SCORE_EXPRESSION,
                "training_records": 11262,
                "validation_records": 2796,
                "num_candidates": EXPECTED_CANDIDATE_COUNT,
                "num_atoms": EXPECTED_ATOM_COUNT,
                "atom_schema_version": ATOM_SCHEMA_VERSION,
                "atom_names": list(APPROVED_ATOM_NAMES),
                "weights_sum": float(np.sum(weights)),
                "weights_min": float(np.min(weights)),
                "weights_max": float(np.max(weights)),
            },
            "output_artifacts": {
                "weights_npy": str(weights_npy),
                "weights_json": str(weights_json),
                "atom_scales_json": str(atom_scales),
                "training_summary_json": str(tmp_path / "training_summary.json"),
                "weights_npy_sha256": weights_npy_sha,
                "weights_json_sha256": _sha(weights_json),
                "atom_scales_json_sha256": _sha(atom_scales),
            },
            "final_decision": {
                "status": "dp_native_fallback_risk_static_camp_training_complete",
                "passed": True,
                "enabled": True,
                "errors": [],
                "training_executed": True,
                "fixed_dp_candidate_reranking_only": True,
                "fallback_only_training": True,
                "replay_execution_authorized": False,
                "candidate_generation_authorized": False,
                "formal_seeds_11_12_13_authorized": False,
                "dp_modification_authorized": False,
                "selector_promotion_authorized": False,
                "atom_promotion_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
            },
        },
    )
    current_scope = (
        "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only"
    )
    if audit_missing_scope:
        current_scope = "next_work_target=old_scope"
    audit = tmp_path / "audit.md"
    audit.write_text(
        "\n".join(
            [
                current_scope,
                "artifact_manifest_plan_authorized=True",
                "artifact_manifest_materialization_authorized=False",
                "runtime_shadow_selector_execution_authorized=False",
                "candidate_generation_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "current_v13_training_authorized_by_user=True",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "training_summary_json": training_summary,
        "atom_scales_json": atom_scales,
        "static_weights_npy": weights_npy,
        "static_weights_json": weights_json,
        "fallback_master_config_json": fallback_master,
        "v13_audit_md": audit,
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(
        **_write_artifacts(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        user_camp_training_authorized=True,
        enabled=True,
    )


def test_artifact_manifest_plan_ready_without_materializing_runtime_manifest(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["artifact_manifest_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["artifact_manifest_plan_ready"] is True
    assert decision["artifact_manifest_static_contract_review_authorized"] is True
    assert decision["artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["training_executed"] is False
    assert decision["user_camp_training_authorized"] is True
    assert decision["training_task_may_start_without_extra_user_authorization"] is True
    assert plan["materialized_by_this_gate"] is False
    assert plan["required_runtime_entries"]["atom_scales"]["logical_name"] == "atom_scales"
    assert plan["required_runtime_entries"]["static_weights"]["logical_name"] == "static_weights"
    assert "--camp_shadow_artifact_manifest <future_runtime_manifest_json>" in plan["planned_runner_args"]


def test_artifact_manifest_plan_is_default_off_and_does_not_read_missing_inputs(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.json"
    report = build_report(
        training_summary_json=missing,
        atom_scales_json=missing,
        static_weights_npy=missing,
        static_weights_json=missing,
        fallback_master_config_json=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["plan_checks"] == []


def test_artifact_manifest_plan_rejects_weight_simplex_drift(tmp_path: Path) -> None:
    weights = _base_weights()
    weights[0] = -0.1
    report = _report(tmp_path, weights=weights)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "static_weights_npy_simplex" in report["final_decision"]["failed_checks"]
    assert "static_weights_json_simplex" in report["final_decision"]["failed_checks"]


def test_artifact_manifest_plan_rejects_training_summary_hash_mismatch(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, training_summary_hash_override="0" * 64)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_output_weights_npy_sha256" in report["final_decision"]["failed_checks"]


def test_artifact_manifest_plan_rejects_audit_boundary_drift(tmp_path: Path) -> None:
    report = _report(tmp_path, audit_missing_scope=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "audit_current_scope_authorizes_manifest_plan_only"
        in report["final_decision"]["failed_checks"]
    )


def test_artifact_manifest_plan_cli_writes_plan_not_runtime_manifest(
    tmp_path: Path,
) -> None:
    paths = _write_artifacts(tmp_path)
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"

    exit_code = main(
        [
            "--training_summary_json",
            str(paths["training_summary_json"]),
            "--atom_scales_json",
            str(paths["atom_scales_json"]),
            "--static_weights_npy",
            str(paths["static_weights_npy"]),
            "--static_weights_json",
            str(paths["static_weights_json"]),
            "--fallback_master_config_json",
            str(paths["fallback_master_config_json"]),
            "--v13_audit_md",
            str(paths["v13_audit_md"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--user_camp_training_authorized",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--enable_v13_default_off_shadow_selector_artifact_manifest_plan",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"].endswith("_artifact_manifest_plan_v1")
    assert payload["artifact_manifest_plan"]["runtime_manifest_schema_version"] == (
        "dp_camp_v13_default_off_shadow_selector_runtime_v1"
    )
    assert payload["artifact_manifest_plan"]["materialized_by_this_gate"] is False
    assert payload["final_decision"]["artifact_manifest_materialization_authorized"] is False
    assert "plan-only" in output_md.read_text(encoding="utf-8")
