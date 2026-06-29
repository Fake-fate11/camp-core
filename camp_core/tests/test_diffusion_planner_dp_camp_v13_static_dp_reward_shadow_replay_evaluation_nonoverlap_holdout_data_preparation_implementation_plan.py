from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_implementation_plan import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_BUILDER_SCRIPT,
    READY_STATUS,
    REJECT_STATUS,
    TARGET_HOLDOUT_RECORDS,
    build_report,
    main,
)


CAMP_HEAD = "d39a7e4c6b14fc31fe6d3c14eb12764136b4c617"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _static_review(path: Path, *, mutation: Any | None = None) -> Path:
    payload: dict[str, Any] = {
        "schema_version": (
            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
            "nonoverlap_holdout_data_preparation_static_contract_review_v1"
        ),
        "contract_summary": {
            "source_plan_status": (
                "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                "nonoverlap_holdout_data_preparation_plan_ready"
            ),
            "target_holdout_records": 12800,
            "target_holdout_selection_logs": 128,
            "minimum_holdout_records": 3200,
            "minimum_holdout_selection_logs": 32,
            "train_eval_candidate_tensor_intersection_must_be_zero": True,
            "candidate_generation_by_camp_forbidden": True,
            "dp_modification_forbidden": True,
            "executed_trajectory_must_remain_dp_top1": True,
            "score_expression": "score_k(w)=a_k^T w",
            "nonnegative_simplex_weights_only": True,
        },
        "source_hashes": {
            "holdout_plan_json_sha256": "a" * 64,
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                "nonoverlap_holdout_data_preparation_static_contract_review_complete"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "implementation_plan_authorized_next": True,
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


def _audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_holdout_data_preparation_static_contract_review_complete",
                f"next_work_target={current_work}",
                "data_preparation_authorized_by_current_boundary=False",
                "static_dp_reward_training_preflight_authorized_by_current_boundary=False",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "safety_benefit_claim_authorized=False",
                "",
            ]
        ),
    )


def _report(tmp_path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        static_contract_review_json=_static_review(tmp_path / "static_review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_holdout_data_preparation_implementation_plan_accepts_static_review(
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
    assert decision["data_preparation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["future_builder_script"] == FUTURE_BUILDER_SCRIPT
    assert plan["future_builder_scope"]["run_fixed_dp_candidate_generation"] is False
    assert report["source_summary"]["target_holdout_records"] == TARGET_HOLDOUT_RECORDS


def test_holdout_data_preparation_implementation_plan_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_holdout_data_preparation_implementation_plan_rejects_data_preparation_auth(
    tmp_path: Path,
) -> None:
    def authorize_data_preparation(payload: dict[str, Any]) -> None:
        payload["final_decision"]["data_preparation_authorized_next"] = True

    report = build_report(
        static_contract_review_json=_static_review(
            tmp_path / "static_review.json",
            mutation=authorize_data_preparation,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "data_preparation_authorized_next" in report["final_decision"]["failed_checks"]


def test_holdout_data_preparation_implementation_plan_rejects_missing_zero_contract(
    tmp_path: Path,
) -> None:
    def remove_contract(payload: dict[str, Any]) -> None:
        payload["contract_summary"]["train_eval_candidate_tensor_intersection_must_be_zero"] = False

    report = build_report(
        static_contract_review_json=_static_review(
            tmp_path / "static_review.json",
            mutation=remove_contract,
        ),
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


def test_holdout_data_preparation_implementation_plan_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        static_contract_review_json=_static_review(tmp_path / "static_review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_holdout_data_preparation_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "implementation_plan.json"
    output_md = tmp_path / "implementation_plan.md"

    exit_code = main(
        [
            "--static_contract_review_json",
            str(_static_review(tmp_path / "static_review.json")),
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
    assert READY_STATUS in output_md.read_text(encoding="utf-8")
