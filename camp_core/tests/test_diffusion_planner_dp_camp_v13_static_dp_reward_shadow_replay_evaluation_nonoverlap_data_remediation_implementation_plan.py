from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_data_remediation_implementation_plan import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_RESULT_READINESS_SCRIPT,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "66d310a5d9fd2191d934adfd5187928e839f8edf"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _source_review(path: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": (
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_data_remediation_static_contract_review_v1"
        ),
        "analysis": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "contract_summary": {
            "split_manifest_required": True,
            "candidate_tensor_hash_registry_required": True,
            "path_signature_registry_required": True,
            "record_identity_hash_registry_required": True,
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "train_eval_path_signature_intersection_must_be_zero": True,
            "result_readiness_must_compare_against_all_training_summary_selection_logs": True,
            "formal_seeds_11_12_13_excluded": True,
            "new_nonoverlap_source_root_required": True,
            "reuse_of_diagnosed_prior_eval_root_for_holdout_forbidden": True,
            "reuse_of_training_summary_selection_logs_for_holdout_forbidden": True,
            "minimum_holdout_records": 3200,
            "minimum_holdout_selection_logs": 32,
            "expected_candidate_count": 8,
            "expected_atom_count": 14,
            "fixed_dp_candidate_generation_requires_later_explicit_preflight": True,
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                "nonoverlap_data_remediation_static_contract_review_complete"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "implementation_plan_authorized_next": True,
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
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_data_remediation_static_contract_review_complete",
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
        static_contract_review_json=_source_review(tmp_path / "static_review.json"),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_nonoverlap_implementation_plan_ready_but_does_not_implement(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_ready"] is True
    assert decision["implementation_static_contract_review_authorized_next"] is True
    assert decision["implementation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["future_result_readiness_script"] == FUTURE_RESULT_READINESS_SCRIPT
    assert (
        plan["future_result_readiness_acceptance"]["candidate_operation"]
        == "fixed DP candidate reranking only"
    )
    assert plan["future_result_readiness_acceptance"]["score_expression"] == "score_k(w)=a_k^T w"


def test_nonoverlap_implementation_plan_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_nonoverlap_implementation_plan_rejects_source_implementation_auth(
    tmp_path: Path,
) -> None:
    def authorize_implementation(payload: dict[str, Any]) -> None:
        payload["final_decision"]["implementation_authorized_next"] = True

    report = build_report(
        static_contract_review_json=_source_review(
            tmp_path / "static_review.json",
            mutation=authorize_implementation,
        ),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_authorized_next" in report["final_decision"]["failed_checks"]


def test_nonoverlap_implementation_plan_rejects_source_training_preflight_auth(
    tmp_path: Path,
) -> None:
    def authorize_training_preflight(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_preflight_authorized_next"] = True

    report = build_report(
        static_contract_review_json=_source_review(
            tmp_path / "static_review.json",
            mutation=authorize_training_preflight,
        ),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "training_preflight_authorized_next" in report["final_decision"]["failed_checks"]


def test_nonoverlap_implementation_plan_rejects_missing_zero_intersection_contract(
    tmp_path: Path,
) -> None:
    def remove_zero_intersection(payload: dict[str, Any]) -> None:
        payload["contract_summary"]["train_eval_candidate_tensor_intersection_must_be_zero"] = False

    report = build_report(
        static_contract_review_json=_source_review(
            tmp_path / "static_review.json",
            mutation=remove_zero_intersection,
        ),
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


def test_nonoverlap_implementation_plan_rejects_dp_head_drift(tmp_path: Path) -> None:
    report = build_report(
        static_contract_review_json=_source_review(tmp_path / "static_review.json"),
        result_readiness_py=_result_readiness(tmp_path / "result_readiness.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_nonoverlap_implementation_plan_main_writes_outputs(tmp_path: Path) -> None:
    output_json = tmp_path / "implementation_plan.json"
    output_md = tmp_path / "implementation_plan.md"

    exit_code = main(
        [
            "--static_contract_review_json",
            str(_source_review(tmp_path / "static_review.json")),
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
    assert payload["implementation_plan"]["implementation_performed_by_this_gate"] is False
    assert "plan-only" in output_md.read_text(encoding="utf-8")
