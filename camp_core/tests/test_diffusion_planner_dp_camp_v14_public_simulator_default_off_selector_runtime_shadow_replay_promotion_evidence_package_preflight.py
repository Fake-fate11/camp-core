import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_evidence_package.py"
)
CAMP_HEAD = "602e7bbee6119372009a88430af078aa3b1a3338"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_runtime_promotion_evidence_package_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload) -> Path:
    return _write(path, json.dumps(payload, indent=2))


def _result_review(module) -> dict:
    return {
        "schema_version": "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_v1",
        "analysis": {
            "candidate_generation_executed_by_review": False,
            "training_executed_by_review": False,
            "replay_executed_by_review": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "heads": {
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "execution": {
            "selection_log_count": 1,
            "validation_summary_count": 1,
            "replay_summary_count": 1,
            "formal_seed_path_count": 0,
        },
        "records": {
            "record_count": 3,
            "default_off_selector_records": 3,
            "artifact_contract_ready_records": 3,
            "executed_top1_records": 3,
            "selected_index_matches_executed_index_records": 3,
            "shadow_selected_index_nonzero_records": 2,
            "shadow_selected_index_differs_from_executed_index_records": 2,
            "feasible_records": 3,
            "used_fallback_records": 0,
            "violation_counts": {
                "affine_score": 0,
                "atom_schema": 0,
                "closed_loop_outcomes": 0,
                "default_off_contract": 0,
                "executed_top1": 0,
                "guidance": 0,
                "postselection": 0,
                "reference_blend": 0,
                "selected_executed_mismatch": 0,
                "selection_score_mask": 0,
                "shape": 0,
            },
        },
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_RESULT_REVIEW_STATUS,
            "failed_checks": [],
            "authorized_next_work": module.PROMOTION_PLAN_CURRENT_WORK,
            "promotion_decision_plan_authorized_next": True,
            "score_expression": module.SCORE_EXPRESSION,
            "candidate_operation": "fixed DP candidate reranking only",
            "executed_output_policy": "dp_top1",
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
            "reference_blend_authorized": False,
            "guidance_authorized": False,
            "postprocess_or_postselection_authorized": False,
            "closed_loop_outcome_authorized": False,
        },
    }


def _delta_review(module, *, worse_records: int = 0) -> dict:
    return {
        "schema_version": "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_v1",
        "analysis": {
            "score_expression": module.SCORE_EXPRESSION,
            "claim_scope": (
                "Supports static objective delta only; does not prove safety, "
                "closed-loop outcome, deployability, or CAMP superiority over DP Top-1."
            ),
        },
        "heads": {
            "current_dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "records": {
            "selection_log_count": 1,
            "record_count": 3,
            "executed_top1_records": 3,
            "selected_matches_executed_records": 3,
            "shadow_selected_index_nonzero_records": 2,
            "shadow_selected_index_differs_from_executed_index_records": 2,
            "formal_seed_path_count": 0,
            "selection_score_comparison": {
                "better_records": 2,
                "tie_records": 1 - worse_records,
                "worse_records": worse_records,
                "uncomparable_records": 0,
            },
            "selection_score_comparison_among_shadow_diff_records": {
                "better_records": 2 - worse_records,
                "tie_records": 0,
                "worse_records": worse_records,
                "uncomparable_records": 0,
            },
        },
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_DELTA_REVIEW_STATUS,
            "failed_checks": [],
            "authorized_next_work": module.PROMOTION_PLAN_CURRENT_WORK,
            "static_objective_delta_supported": True,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "candidate_generation_authorized": False,
            "training_authorized": False,
            "replay_execution_authorized": False,
            "dp_modification_authorized": False,
        },
    }


def _promotion_plan(
    module,
    *,
    result_sha: str,
    delta_sha: str,
    selector_promotion_authorized: bool = False,
) -> dict:
    return {
        "schema_version": "dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision_plan_v1",
        "source_hashes": {
            "runtime_result_review_json": result_sha,
            "shadow_vs_top1_delta_review_json": delta_sha,
        },
        "runtime_result_review_summary": {
            "records": 3,
            "shadow_selected_index_nonzero_records": 2,
        },
        "shadow_vs_top1_delta_review_summary": {
            "static_objective_delta_supported": True,
            "selection_score_worse_records": 0,
        },
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_PLAN_STATUS,
            "failed_checks": [],
            "authorized_current_work": module.PROMOTION_PLAN_CURRENT_WORK,
            "authorized_next_work": module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
            "evidence_package_preflight_authorized": True,
            "recommendation": "do_not_promote_from_current_evidence_alone",
            "immediate_action": "build_runtime_promotion_evidence_package_preflight_only",
            "score_expression": module.SCORE_EXPRESSION,
            "selector_promotion_authorized": selector_promotion_authorized,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "training_authorized": False,
            "training_execution_authorized": False,
            "candidate_generation_authorized": False,
            "replay_execution_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "executed_trajectory_change_authorized": False,
        },
    }


def _training_summary(module) -> dict:
    return {
        "num_records": 3,
        "dropped_records_without_feasible_candidate": 0,
        "num_candidates": 8,
        "num_atoms": 9,
        "atom_schema_version": "camp_legacy_v1_9d",
        "trained_weights": [0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        "dp_native_training_data_contract": {
            "schema_version": "clean_dp_native_training_data_contract_validator_v1",
            "passed": True,
            "read_only": True,
            "records": 3,
            "selection_logs": ["selection_log.json"],
            "future_training_input_contract_satisfied": True,
            "candidate_generation_executed": False,
            "replay_executed": False,
            "dp_modification_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _training_review(module) -> dict:
    return {
        "schema_version": "dp_camp_v14_public_simulator_fixed_dp_candidate_training_artifact_static_contract_review_v1",
        "training_summary": _training_summary(module),
        "artifact_review": {
            "weights_sum": 1.0,
            "weights_nonnegative": True,
            "weights_file_matches_summary": True,
            "scales_all_positive_finite": True,
        },
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_TRAINING_REVIEW_STATUS,
            "failed_checks": [],
            "score_expression": module.SCORE_EXPRESSION,
            "training_executed_by_review": False,
            "replay_executed": False,
            "candidate_generation_executed": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "deployable_checkpoint_claim_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "online_selector_change_authorized": False,
            "reference_blend_authorized": False,
            "guidance_authorized": False,
            "postprocess_or_postselection_authorized": False,
            "closed_loop_outcome_authorized": False,
        },
    }


def _runtime_manifest(module, *, scales_sha: str, weights_sha: str) -> dict:
    authorizations = {
        "atom_promotion_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "candidate_generation_authorized": False,
        "default_off_shadow_selector_runtime_execution_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "deployment_authorized": False,
        "dp_modification_authorized": False,
        "executed_trajectory_change_authorized": False,
        "online_selector_change_authorized": False,
        "replay_execution_authorized": False,
        "runtime_artifact_manifest_materialization_authorized": False,
        "safety_benefit_claim_authorized": False,
        "selector_promotion_authorized": False,
        "training_authorized": False,
        "training_executed": False,
        "training_execution_authorized": False,
    }
    return {
        "schema_version": module.SOURCE_RUNTIME_MANIFEST_SCHEMA,
        "manifest_role": "default_off_shadow_selector_runtime_artifact_manifest",
        "source_scope": "public_simulator_fixed_dp_candidate_tensor",
        "default_off": True,
        "fail_closed": True,
        "selection_effect": False,
        "online_selector_change": False,
        "selector_mode": "static",
        "candidate_operation": "fixed DP candidate reranking only",
        "executed_output_policy": "dp_top1",
        "required_candidate_count": 8,
        "atom_count": 9,
        "atom_schema_version": "camp_legacy_v1_9d",
        "score_expression": module.SCORE_EXPRESSION,
        "required_dp_head": module.FIXED_DP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "artifacts": {
            "atom_scales": {
                "logical_name": "atom_scales",
                "required": True,
                "sha256": scales_sha,
            },
            "static_weights": {
                "logical_name": "static_weights",
                "required": True,
                "sha256": weights_sha,
            },
        },
        "authorizations": authorizations,
    }


def _fixture(
    tmp_path: Path,
    module,
    *,
    wrong_eof: bool = False,
    worse_records: int = 0,
    selector_promotion_authorized: bool = False,
) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_PLAN_STATUS}",
                f"next_work_target={next_work}",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_PLAN_STATUS}",
                f"next_work_target={module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK}",
                "",
            ]
        ),
    )
    result_review = _write_json(
        tmp_path / "runtime_result_review.json",
        _result_review(module),
    )
    delta_review = _write_json(
        tmp_path / "shadow_vs_top1_delta_review.json",
        _delta_review(module, worse_records=worse_records),
    )
    training_review = _write_json(
        tmp_path / "training_artifact_static_contract_report.json",
        _training_review(module),
    )
    training_summary = _write_json(
        tmp_path / "training_summary.json",
        _training_summary(module),
    )
    weights = tmp_path / "offline_weights_dp_static.npy"
    weights.write_bytes(b"dummy weights")
    atom_scales = _write_json(
        tmp_path / "atom_scales_dp_static.json",
        {"atom_schema_version": "camp_legacy_v1_9d", "scales": [1.0] * 9},
    )
    runtime_manifest = _write_json(
        tmp_path / "runtime_manifest.json",
        _runtime_manifest(
            module,
            scales_sha=module._sha256(atom_scales),
            weights_sha=module._sha256(weights),
        ),
    )
    promotion_plan = _write_json(
        tmp_path / "runtime_promotion_decision_plan.json",
        _promotion_plan(
            module,
            result_sha=module._sha256(result_review),
            delta_sha=module._sha256(delta_review),
            selector_promotion_authorized=selector_promotion_authorized,
        ),
    )
    execution_sha = _write(tmp_path / "runtime_execution_SHA256SUMS", "abc  file\n")
    expected_counts = {
        "selection_log_count": 1,
        "validation_summary_count": 1,
        "replay_summary_count": 1,
        "records": 3,
        "default_off_selector_records": 3,
        "artifact_contract_ready_records": 3,
        "shadow_selected_index_nonzero_records": 2,
        "shadow_selected_index_differs_from_executed_index_records": 2,
        "executed_top1_records": 3,
        "selected_index_matches_executed_index_records": 3,
        "feasible_records": 3,
        "used_fallback_records": 0,
        "selection_score_better_records": 2,
        "selection_score_tie_records": 1,
        "selection_score_worse_records": 0,
        "selection_score_uncomparable_records": 0,
        "shadow_diff_selection_score_better_records": 2,
        "shadow_diff_selection_score_worse_records": 0,
        "training_records": 3,
        "dropped_records_without_feasible_candidate": 0,
        "num_candidates": 8,
        "num_atoms": 9,
    }
    return {
        "runtime_promotion_decision_plan_json": promotion_plan,
        "runtime_result_review_json": result_review,
        "shadow_vs_top1_delta_review_json": delta_review,
        "runtime_manifest_json": runtime_manifest,
        "training_artifact_static_review_json": training_review,
        "training_summary_json": training_summary,
        "offline_weights_npy": weights,
        "atom_scales_json": atom_scales,
        "runtime_shadow_execution_sha256s": execution_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "preflight",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
        "expected_counts": expected_counts,
    }


def test_runtime_promotion_evidence_package_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evidence_package_static_review_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert report["source_summary"]["records"] == 3
    assert report["source_summary"]["selection_score_worse_records"] == 0
    assert len(report["artifact_manifest"]) == 9
    assert report["static_integration_contract"]["default_off"] is True
    assert report["static_integration_contract"]["fail_closed"] is True
    assert (kwargs["output_dir"] / "runtime_promotion_evidence_package_preflight.json").is_file()
    assert (kwargs["output_dir"] / "runtime_promotion_evidence_package_preflight.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_promotion_evidence_package_preflight_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "preflight_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_preflight_authorization_missing"
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_runtime_promotion_evidence_package_preflight_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_promotion_evidence_package_preflight_rejects_delta_worse_records(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, worse_records=1)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "delta_review_selection_score_worse" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "source_delta_review_contract_failure"
    )


def test_runtime_promotion_evidence_package_preflight_rejects_promotion_authorization(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, selector_promotion_authorized=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "promotion_plan_selector_promotion_authorized" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "source_promotion_plan_contract_failure"
    )
