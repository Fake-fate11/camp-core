import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_evidence_package.py"
)
CAMP_HEAD = "5af0f201afc6991a67d7189823429a29f871a5de"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_promotion_evidence_package_preflight",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _promotion_plan(module) -> dict:
    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_trained_default_off_shadow_replay_"
            "evaluation_promotion_decision_plan_v1"
        ),
        "final_decision": {
            "status": module.SOURCE_PLAN_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
            "evidence_package_preflight_authorized": True,
            "recommendation": "do_not_promote_from_current_evidence_alone",
            "score_expression": module.SCORE_EXPRESSION,
            "selector_promotion_authorized": False,
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
        "source_summary": {
            "selection_log_count": 32,
            "validation_summary_count": 32,
            "replay_summary_count": 32,
            "records_total": 3200,
            "route_count": 16,
            "seed_count": 4,
            "shadow_selected_index_nonzero_records": 2832,
            "executed_top1_records": 3200,
            "selected_index_matches_executed_index_records": 3200,
            "training_records": 2914,
            "dropped_records_without_feasible_candidate": 286,
            "num_candidates": 8,
            "num_atoms": 9,
            "first_loss": 2.0419425862497667,
            "last_loss": 2.036233432086801,
        },
    }


def _result_review(module) -> dict:
    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_trained_default_off_shadow_"
            "replay_evaluation_result_review_v1"
        ),
        "execution": {
            "selection_log_count": 32,
            "validation_summary_count": 32,
            "replay_summary_count": 32,
        },
        "records": {
            "records_total": 3200,
            "route_count": 16,
            "seed_count": 4,
            "selected_index_matches_executed_index_records": 3200,
            "shadow_selected_index_nonzero_records": 2832,
            "executed_top1_records": 3200,
            "selection_effect_true_count": 0,
            "online_change_true_count": 0,
            "candidate_reference_blend_steps_nonzero": 0,
            "candidate_closed_loop_outcome_weights_nonzero": 0,
            "candidate_closed_loop_outcomes_nonzero": 0,
            "formal_seed_path_count": 0,
            "camp_provenance_forbidden_effect_count": 0,
            "weights_bad_count": 0,
            "atom_schema_bad_count": 0,
            "candidate_count_bad_count": 0,
        },
        "final_decision": {
            "status": module.SOURCE_RESULT_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": (
                "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
                "shadow_replay_evaluation_promotion_decision_plan_only_after_explicit_"
                "user_authorization"
            ),
            "score_expression": module.SCORE_EXPRESSION,
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
        },
    }


def _training_summary() -> dict:
    return {
        "dp_native_training_data_contract": "fixed_dp_candidate_tensor",
        "num_records": 2914,
        "dropped_records_without_feasible_candidate": 286,
        "num_candidates": 8,
        "num_atoms": 9,
        "atom_schema_version": "camp_legacy_v1_9d",
        "oracle_match_rate": 0.22786547700754975,
        "feasible_candidate_rate": 0.9781228551818806,
        "trained_weights": [0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
    }


def _training_review(module) -> dict:
    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_fixed_dp_candidate_training_artifact_"
            "static_contract_review_v1"
        ),
        "final_decision": {
            "status": module.SOURCE_TRAINING_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": (
                "public_simulator_fixed_dp_candidate_generation_trained_default_off_"
                "shadow_replay_evaluation_preflight"
            ),
            "score_expression": module.SCORE_EXPRESSION,
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
        },
        "artifact_review": {
            "weights_sum": 1.0,
            "weights_nonnegative": True,
            "weights_file_matches_summary": True,
            "scales_all_positive_finite": True,
        },
        "training_summary": _training_summary(),
    }


def _fixture(tmp_path: Path, module, *, wrong_eof: bool = False) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                "## Older Section",
                "next_work_target=old_gate",
                "## Current Section",
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
    plan = _write(
        tmp_path / "promotion_decision_plan.json",
        json.dumps(_promotion_plan(module), indent=2),
    )
    result_review = _write(
        tmp_path / "result_review_report.json",
        json.dumps(_result_review(module), indent=2),
    )
    training_review = _write(
        tmp_path / "training_artifact_static_contract_report.json",
        json.dumps(_training_review(module), indent=2),
    )
    training_summary = _write(
        tmp_path / "training_summary.json",
        json.dumps(_training_summary(), indent=2),
    )
    weights = tmp_path / "offline_weights_dp_static.npy"
    weights.write_bytes(b"dummy-npy")
    atom_scales = _write(
        tmp_path / "atom_scales_dp_static.json",
        json.dumps(
            {
                "atom_schema_version": "camp_legacy_v1_9d",
                "scales": [1.0] * 9,
            },
            indent=2,
        ),
    )
    shadow_sha = _write(tmp_path / "shadow_execution_SHA256SUMS", "abc  file\n")
    return {
        "promotion_decision_plan_json": plan,
        "result_review_json": result_review,
        "training_artifact_static_review_json": training_review,
        "training_summary_json": training_summary,
        "offline_weights_npy": weights,
        "atom_scales_json": atom_scales,
        "shadow_execution_sha256s": shadow_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "preflight",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_v14_promotion_evidence_package_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["default_off_shadow_selector_contract_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert len(report["artifact_manifest"]) == 7
    assert report["source_summary"]["records_total"] == 3200
    assert report["source_summary"]["training_records"] == 2914
    assert report["static_integration_contract"]["status"] == "preflight_ready_contract_pinned"
    assert report["static_integration_contract"]["simplex_master_convex"] is True
    assert report["static_integration_contract"]["cvar_master_convex"] is True
    assert report["static_integration_contract"]["l2_master_convex"] is True
    assert (kwargs["output_dir"] / "promotion_evidence_package_preflight.json").is_file()
    assert (kwargs["output_dir"] / "promotion_evidence_package_preflight.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_promotion_evidence_package_preflight_requires_enable(tmp_path: Path) -> None:
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


def test_v14_promotion_evidence_package_preflight_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"
