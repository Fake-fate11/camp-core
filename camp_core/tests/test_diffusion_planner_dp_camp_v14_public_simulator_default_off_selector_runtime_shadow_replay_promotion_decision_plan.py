import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_default_off_selector_runtime_shadow_replay_promotion_decision.py"
)
CAMP_HEAD = "3c1ce56f8792469db684a8c58b1d1c148259df7c"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_runtime_promotion_plan", SCRIPT_PATH)
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


def _runtime_result_review(module) -> dict:
    return {
        "schema_version": "dp_camp_v14_public_simulator_default_off_shadow_selector_runtime_shadow_replay_result_review_v1",
        "analysis": {
            "candidate_generation_executed_by_review": False,
            "training_executed_by_review": False,
            "replay_executed_by_review": False,
            "dp_modified_by_review": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "heads": {
            "current_dp_head": module.FIXED_DP_HEAD,
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
            "executed_top1_records": 3,
            "selected_index_matches_executed_index_records": 3,
            "shadow_selected_index_nonzero_records": 2,
            "shadow_selected_index_differs_from_executed_index_records": 2,
            "feasible_records": 3,
            "used_fallback_records": 0,
            "max_affine_score_error": 1e-16,
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
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "promotion_decision_plan_authorized_next": True,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
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
            "raw_affine_score_comparison": {
                "better_records": 2,
                "tie_records": 1,
                "worse_records": 0,
                "uncomparable_records": 0,
            },
        },
        "final_decision": {
            "passed": True,
            "status": module.SOURCE_DELTA_REVIEW_STATUS,
            "failed_checks": [],
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "static_objective_delta_supported": True,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _fixture(tmp_path: Path, module, *, wrong_eof: bool = False, worse_records: int = 0) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.AUTHORIZED_CURRENT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_DELTA_REVIEW_STATUS}",
                f"next_work_target={next_work}",
                "default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_passed=True",
                "default_off_shadow_selector_runtime_shadow_vs_top1_delta_review_static_objective_delta_supported=True",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_DELTA_REVIEW_STATUS}",
                f"next_work_target={next_work}",
                "static masked-objective delta",
                "",
            ]
        ),
    )
    result_json = _write_json(
        tmp_path / "runtime_result_review.json",
        _runtime_result_review(module),
    )
    delta_json = _write_json(
        tmp_path / "shadow_vs_top1_delta_review.json",
        _delta_review(module, worse_records=worse_records),
    )
    expected_counts = {
        "selection_log_count": 1,
        "validation_summary_count": 1,
        "replay_summary_count": 1,
        "records": 3,
        "shadow_selected_index_nonzero_records": 2,
        "shadow_selected_index_differs_from_executed_index_records": 2,
        "executed_top1_records": 3,
        "selected_index_matches_executed_index_records": 3,
        "default_off_selector_records": 3,
        "feasible_records": 3,
        "used_fallback_records": 0,
        "selection_score_better_records": 2,
        "selection_score_tie_records": 1,
        "selection_score_worse_records": 0,
        "selection_score_uncomparable_records": 0,
        "shadow_diff_selection_score_better_records": 2,
        "shadow_diff_selection_score_worse_records": 0,
    }
    return {
        "runtime_result_review_json": result_json,
        "shadow_vs_top1_delta_review_json": delta_json,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "plan",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
        "expected_counts": expected_counts,
    }


def test_runtime_promotion_decision_plan_passes_as_planning_only(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["recommendation"] == "do_not_promote_from_current_evidence_alone"
    assert decision["immediate_action"] == "build_runtime_promotion_evidence_package_preflight_only"
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert report["shadow_vs_top1_delta_review_summary"]["static_objective_delta_supported"] is True
    assert (kwargs["output_dir"] / "runtime_promotion_decision_plan.json").is_file()
    assert (kwargs["output_dir"] / "runtime_promotion_decision_plan.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_runtime_promotion_decision_plan_requires_explicit_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "planning_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "explicit_planning_authorization_missing"
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_runtime_promotion_decision_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_runtime_promotion_decision_plan_rejects_worse_delta(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, worse_records=1)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "delta_selection_score_worse_records" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "shadow_vs_top1_delta_contract_failure"
    assert report["final_decision"]["deployment_authorized"] is False
