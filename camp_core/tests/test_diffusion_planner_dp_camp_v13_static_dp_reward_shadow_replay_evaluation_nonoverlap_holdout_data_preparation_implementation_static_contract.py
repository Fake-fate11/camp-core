from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_BUILDER_SCRIPT,
    FUTURE_BUILDER_TEST,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "51c261131702582cad831c1e8308405f88b2b0e1"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _implementation_plan(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": (
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_holdout_data_preparation_implementation_plan_v1"
        ),
        "analysis": {
            "plan_only": True,
            "data_preparation_execution": False,
            "fixed_dp_candidate_generation_execution": False,
            "training_execution": False,
            "replay_execution": False,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "source_summary": {
            "status": (
                "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                "nonoverlap_holdout_data_preparation_static_contract_review_complete"
            ),
            "authorized_next_work": (
                "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
                "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
                "nonoverlap_holdout_data_preparation_implementation_plan_only"
            ),
            "target_holdout_selection_logs": 128,
            "target_holdout_records": 12800,
            "minimum_holdout_selection_logs": 32,
            "minimum_holdout_records": 3200,
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "candidate_generation_by_camp_forbidden": True,
            "dp_modification_forbidden": True,
            "executed_trajectory_must_remain_dp_top1": True,
            "nonnegative_simplex_weights_only": True,
            "score_expression": "score_k(w)=a_k^T w",
        },
        "implementation_plan": {
            "status": "plan_ready_no_implementation",
            "implementation_performed_by_this_gate": False,
            "future_builder_script": FUTURE_BUILDER_SCRIPT,
            "future_builder_test": FUTURE_BUILDER_TEST,
            "future_builder_inputs": [
                "source static contract review json",
                "prior training summary json path from source plan",
                "rejected evaluation registry paths from source plan",
                "non-formal route/seed candidate manifest",
            ],
            "future_builder_outputs": [
                "holdout_candidate_request_manifest.json",
                "nonoverlap_exclusion_registry_manifest.json",
                "holdout_preparation_runbook.sh",
                "expected_holdout_artifact_manifest.json",
                "SHA256SUMS",
            ],
            "future_builder_scope": {
                "materialize_holdout_request_manifest": True,
                "materialize_exclusion_registry_manifest": True,
                "materialize_validation_runbook": True,
                "materialize_expected_output_manifest": True,
                "modify_dp": False,
                "run_fixed_dp_candidate_generation": False,
                "run_replay": False,
                "train_camp": False,
            },
            "future_static_review_requirements": [
                "confirm builder is manifest-only and does not invoke DP",
                "confirm builder rejects formal seeds 11/12/13",
                "confirm builder requires target 128 logs and 12800 records",
                "confirm builder carries zero-intersection registry requirements forward",
                "confirm builder keeps CAMP candidate generation forbidden",
                "confirm builder keeps score_k(w)=a_k^T w and nonnegative simplex boundaries",
            ],
            "not_authorized_by_this_plan": {
                "data_preparation": True,
                "implementation": True,
                "training_preflight": True,
                "training_execution": True,
                "replay_execution": True,
                "fixed_dp_candidate_generation": True,
                "candidate_generation_by_camp": True,
                "dp_modification": True,
                "promotion": True,
                "deployment": True,
                "safety_claim": True,
                "camp_over_dp_top1_claim": True,
            },
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                "nonoverlap_holdout_data_preparation_implementation_plan_ready"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "implementation_plan_ready": True,
            "implementation_static_contract_review_authorized_next": True,
            "data_preparation_authorized_next": False,
            "implementation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "selector_promotion_authorized": False,
            "atom_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write(path, json.dumps(payload))


def _implementation_plan_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "nonoverlap_holdout_data_preparation_implementation_plan_only",
                "nonoverlap_holdout_data_preparation_implementation_static_contract_review_only",
                FUTURE_BUILDER_SCRIPT,
                "implementation_performed_by_this_gate",
                "plan_ready_no_implementation",
                "",
            ]
        ),
    )


def _implementation_plan_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "def test_holdout_implementation_plan_rejects_source_data_preparation_auth(): pass",
                "def test_holdout_implementation_plan_rejects_missing_zero_intersection_contract(): pass",
                "def test_holdout_implementation_plan_rejects_dp_head_drift(): pass",
                "",
            ]
        ),
    )


def _audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_implementation_plan_ready",
                f"next_work_target={current_work}",
                "data_preparation_authorized_by_current_boundary=False",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _report(tmp_path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        implementation_plan_json=_implementation_plan(tmp_path / "implementation_plan.json"),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_holdout_implementation_static_contract_review_authorizes_only_builder_implementation(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_static_contract_review_complete"] is True
    assert decision["builder_implementation_authorized_next"] is True
    assert decision["data_preparation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["atom_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert plan["future_builder_script"] == FUTURE_BUILDER_SCRIPT
    assert plan["future_builder_test"] == FUTURE_BUILDER_TEST
    assert plan["materialize_holdout_request_manifest"] is True
    assert plan["scope_run_fixed_dp_candidate_generation"] is False
    assert report["source_summary"]["score_expression"] == "score_k(w)=a_k^T w"


def test_holdout_implementation_static_contract_review_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_holdout_implementation_static_contract_review_rejects_source_data_preparation_auth(
    tmp_path: Path,
) -> None:
    def authorize_data_preparation(payload: dict[str, Any]) -> None:
        payload["final_decision"]["data_preparation_authorized_next"] = True

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=authorize_data_preparation,
        ),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "data_preparation_authorized_next" in report["final_decision"]["failed_checks"]


def test_holdout_implementation_static_contract_review_rejects_fixed_dp_generation_scope(
    tmp_path: Path,
) -> None:
    def authorize_generation(payload: dict[str, Any]) -> None:
        payload["implementation_plan"]["future_builder_scope"][
            "run_fixed_dp_candidate_generation"
        ] = True

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=authorize_generation,
        ),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_plan_scope_run_fixed_dp_candidate_generation" in report[
        "final_decision"
    ]["failed_checks"]


def test_holdout_implementation_static_contract_review_rejects_missing_zero_intersection_contract(
    tmp_path: Path,
) -> None:
    def remove_zero_intersection(payload: dict[str, Any]) -> None:
        payload["source_summary"]["train_eval_candidate_tensor_intersection_must_be_zero"] = False

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=remove_zero_intersection,
        ),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "train_eval_candidate_tensor_intersection_must_be_zero"
        in report["final_decision"]["failed_checks"]
    )


def test_holdout_implementation_static_contract_review_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_plan_json=_implementation_plan(tmp_path / "implementation_plan.json"),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_holdout_implementation_static_contract_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "implementation_static_contract_review.json"
    output_md = tmp_path / "implementation_static_contract_review.md"

    exit_code = main(
        [
            "--implementation_plan_json",
            str(_implementation_plan(tmp_path / "implementation_plan.json")),
            "--implementation_plan_script_py",
            str(_implementation_plan_script(tmp_path / "plan.py")),
            "--implementation_plan_test_py",
            str(_implementation_plan_test(tmp_path / "test_plan.py")),
            "--v13_audit_md",
            str(_audit(tmp_path / "audit.md")),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["builder_implementation_authorized_next"] is True
    assert "read-only" in output_md.read_text(encoding="utf-8")
