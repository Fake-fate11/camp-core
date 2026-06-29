from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_data_remediation_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_IMPLEMENTATION_STATIC_CONTRACT_TEST,
    FUTURE_RESULT_READINESS_SCRIPT,
    FUTURE_RESULT_READINESS_TEST,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "9f3af496282cebb018b0697bc98bed192041af8a"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _implementation_plan(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": (
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_data_remediation_implementation_plan_v1"
        ),
        "source_summary": {
            "status": (
                "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                "nonoverlap_data_remediation_static_contract_review_complete"
            ),
            "authorized_next_work": (
                "dp_camp_v13_current_source_large_default_off_shadow_selector_static_"
                "dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_"
                "nonoverlap_data_remediation_implementation_plan_only"
            ),
            "split_manifest_required": True,
            "candidate_tensor_hash_registry_required": True,
            "path_signature_registry_required": True,
            "record_identity_hash_registry_required": True,
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "train_eval_path_signature_intersection_must_be_zero": True,
            "result_readiness_must_compare_against_all_training_summary_selection_logs": True,
            "formal_seeds_11_12_13_excluded": True,
            "minimum_holdout_records": 3200,
            "minimum_holdout_selection_logs": 32,
            "expected_candidate_count": 8,
            "expected_atom_count": 14,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "implementation_plan": {
            "status": "plan_ready_no_implementation",
            "implementation_performed_by_this_gate": False,
            "future_result_readiness_script": FUTURE_RESULT_READINESS_SCRIPT,
            "future_result_readiness_test": FUTURE_RESULT_READINESS_TEST,
            "future_implementation_static_contract_test": FUTURE_IMPLEMENTATION_STATIC_CONTRACT_TEST,
            "future_cli_extensions": [
                "--split_manifest_json for explicit train/holdout split evidence",
                "--candidate_tensor_hash_registry_json for train/eval candidate tensor hashes",
                "--path_signature_registry_json for train/eval route/seed/npc signatures",
                "--record_identity_hash_registry_json for same-signature step identity checks",
            ],
            "required_future_changes": [
                "load split_manifest_json as a structured JSON object",
                "require train and holdout selection-log roots to be disjoint",
                "require candidate_tensor_hash train/eval intersection count to be zero",
                "require path_signature train/eval intersection count to be zero",
                "require record_identity_hash train/eval intersection count to be zero",
                "compare evaluation hashes against every training_summary.selection_logs entry",
                "reject formal seeds 11/12/13 in both train and holdout manifests",
                "reject reuse of the diagnosed prior evaluation root for holdout",
                "reject reuse of training-summary selection logs for holdout",
                "preserve default-off shadow selector validation and fixed DP Top-1 execution",
                "preserve affine score contract score_k(w)=a_k^T w",
            ],
            "future_result_readiness_acceptance": {
                "minimum_holdout_records": 3200,
                "minimum_holdout_selection_logs": 32,
                "expected_candidate_count": 8,
                "expected_atom_count": 14,
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": "score_k(w)=a_k^T w",
            },
            "not_authorized_by_this_plan": {
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
                "nonoverlap_data_remediation_implementation_plan_ready"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "implementation_plan_ready": True,
            "implementation_static_contract_review_authorized_next": True,
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
                AUTHORIZED_CURRENT_WORK,
                "--split_manifest_json",
                "--candidate_tensor_hash_registry_json",
                "--path_signature_registry_json",
                "--record_identity_hash_registry_json",
                "plan_ready_no_implementation",
                "implementation_performed_by_this_gate",
                "",
            ]
        ),
    )


def _implementation_plan_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "def test_nonoverlap_implementation_plan_rejects_source_implementation_auth(): pass",
                "def test_nonoverlap_implementation_plan_rejects_source_training_preflight_auth(): pass",
                "def test_nonoverlap_implementation_plan_rejects_missing_zero_intersection_contract(): pass",
                "def test_nonoverlap_implementation_plan_rejects_dp_head_drift(): pass",
                "",
            ]
        ),
    )


def _result_readiness(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "parser.add_argument('--previous_training_summary_json')",
                "def _compare_candidate_tensor_hashes(): pass",
                "max_previous_overlap_rate = 0.0",
                "",
            ]
        ),
    )


def _audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_data_remediation_implementation_plan_ready",
                f"next_work_target={current_work}",
                "implementation_authorized_by_current_boundary=False",
                "static_dp_reward_training_preflight_authorized_by_current_boundary=False",
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
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_nonoverlap_implementation_static_contract_review_authorizes_only_implementation(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["planned_implementation"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_static_contract_review_complete"] is True
    assert decision["implementation_authorized_next"] is True
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert plan["status"] == "plan_ready_no_implementation"
    assert plan["future_result_readiness_script"] == FUTURE_RESULT_READINESS_SCRIPT
    assert plan["future_result_readiness_test"] == FUTURE_RESULT_READINESS_TEST
    assert plan["future_implementation_static_contract_test"] == FUTURE_IMPLEMENTATION_STATIC_CONTRACT_TEST
    assert plan["candidate_operation"] == "fixed DP candidate reranking only"
    assert plan["score_expression"] == "score_k(w)=a_k^T w"


def test_nonoverlap_implementation_static_contract_review_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_nonoverlap_implementation_static_contract_review_rejects_source_implementation_auth(
    tmp_path: Path,
) -> None:
    def authorize_implementation(payload: dict[str, Any]) -> None:
        payload["final_decision"]["implementation_authorized_next"] = True

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=authorize_implementation,
        ),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_authorized_next" in report["final_decision"]["failed_checks"]


def test_nonoverlap_implementation_static_contract_review_rejects_missing_zero_intersection_contract(
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
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
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


def test_nonoverlap_implementation_static_contract_review_rejects_missing_future_cli_arg(
    tmp_path: Path,
) -> None:
    def remove_record_identity_cli(payload: dict[str, Any]) -> None:
        payload["implementation_plan"]["future_cli_extensions"] = [
            item
            for item in payload["implementation_plan"]["future_cli_extensions"]
            if "--record_identity_hash_registry_json" not in item
        ]

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=remove_record_identity_cli,
        ),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planned_future_cli_arg_record_identity_hash_registry_json" in report[
        "final_decision"
    ]["failed_checks"]


def test_nonoverlap_implementation_static_contract_review_rejects_missing_required_future_change(
    tmp_path: Path,
) -> None:
    def remove_formal_seed_rejection(payload: dict[str, Any]) -> None:
        payload["implementation_plan"]["required_future_changes"] = [
            item
            for item in payload["implementation_plan"]["required_future_changes"]
            if "formal seeds 11/12/13" not in item
        ]

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=remove_formal_seed_rejection,
        ),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "planned_future_change_formal_seeds_11_12_13" in report["final_decision"][
        "failed_checks"
    ]


def test_nonoverlap_implementation_static_contract_review_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_plan_json=_implementation_plan(tmp_path / "implementation_plan.json"),
        implementation_plan_script_py=_implementation_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_implementation_plan_test(tmp_path / "test_plan.py"),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_nonoverlap_implementation_static_contract_review_main_writes_outputs(
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
            "--result_readiness_py",
            str(_result_readiness(tmp_path / "result_readiness.py")),
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
    assert payload["final_decision"]["implementation_authorized_next"] is True
    assert "read-only" in output_md.read_text(encoding="utf-8")
