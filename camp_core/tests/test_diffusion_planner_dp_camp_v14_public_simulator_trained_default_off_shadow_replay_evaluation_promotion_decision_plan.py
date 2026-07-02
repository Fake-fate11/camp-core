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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_trained_default_off_shadow_replay_evaluation_promotion_decision.py"
)
CAMP_HEAD = "10aa9db7bc003bb82a2eb92accdca4d6ed87b189"


def _load_module():
    spec = importlib.util.spec_from_file_location("v14_promotion_decision_plan", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _result_review(module) -> dict:
    return {
        "schema_version": (
            "dp_camp_v14_public_simulator_trained_default_off_shadow_"
            "replay_evaluation_result_review_v1"
        ),
        "analysis": {
            "score_expression": module.SCORE_EXPRESSION,
        },
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
            "candidate_counts": {"8": 3200},
            "atom_schema_versions": {"camp_legacy_v1_9d": 3200},
        },
        "final_decision": {
            "status": module.SOURCE_READY_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": module.SOURCE_AUTHORIZED_NEXT_WORK,
            "promotion_decision_plan_authorized_next": True,
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
            "score_expression": module.SCORE_EXPRESSION,
        },
    }


def _fixture(tmp_path: Path, module, *, wrong_eof: bool = False) -> dict:
    docs = tmp_path / "docs"
    next_work = "wrong_gate" if wrong_eof else module.SOURCE_AUTHORIZED_NEXT_WORK
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "\n".join(
            [
                f"current_v14_status={module.SOURCE_READY_STATUS}",
                f"next_work_target={next_work}",
                "camp_training_executed=True",
                "trained_default_off_shadow_replay_evaluation_result_review_passed=True",
                "v14_public_simulator_fixed_dp_candidate_training_execution_num_records=2914",
                "v14_public_simulator_fixed_dp_candidate_training_execution_dropped_records_without_feasible_candidate=286",
                "v14_public_simulator_fixed_dp_candidate_training_execution_num_atoms=9",
                "v14_public_simulator_fixed_dp_candidate_training_execution_first_loss=2.0419425862497667",
                "v14_public_simulator_fixed_dp_candidate_training_execution_last_loss=2.036233432086801",
                "v14_public_simulator_fixed_dp_candidate_training_execution_oracle_match_rate=0.22786547700754975",
                "v14_public_simulator_fixed_dp_candidate_training_execution_feasible_candidate_rate=0.9781228551818806",
                "",
            ]
        ),
    )
    current_status = _write(
        docs / "diffusion_planner_current_status.md",
        "\n".join([module.SOURCE_READY_STATUS, module.SOURCE_AUTHORIZED_NEXT_WORK, ""]),
    )
    result_review = _write(
        tmp_path / "result_review_report.json",
        json.dumps(_result_review(module), indent=2),
    )
    return {
        "result_review_json": result_review,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "plan",
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def test_v14_promotion_decision_plan_passes_as_planning_only(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)

    report = module.build_report(**kwargs)
    module.write_outputs(kwargs["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["recommendation"] == "do_not_promote_from_current_evidence_alone"
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["replay_execution_authorized"] is False
    assert decision["candidate_generation_authorized"] is False
    assert report["source_summary"]["records_total"] == 3200
    assert report["source_summary"]["training_records"] == 2914
    assert report["source_summary"]["score_expression"] == module.SCORE_EXPRESSION
    assert (kwargs["output_dir"] / "promotion_decision_plan.json").is_file()
    assert (kwargs["output_dir"] / "promotion_decision_plan.md").is_file()
    assert (kwargs["output_dir"] / "SHA256SUMS").is_file()


def test_v14_promotion_decision_plan_requires_explicit_enable(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module)
    kwargs["enabled"] = False

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "planning_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_planning_authorization_missing"
    )
    assert report["final_decision"]["selector_promotion_authorized"] is False


def test_v14_promotion_decision_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    kwargs = _fixture(tmp_path, module, wrong_eof=True)

    report = module.build_report(**kwargs)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"
