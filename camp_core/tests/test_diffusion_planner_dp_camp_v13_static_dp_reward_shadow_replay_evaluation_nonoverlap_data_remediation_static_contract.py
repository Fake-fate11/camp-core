from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_data_remediation import (
    AUTHORIZED_CURRENT_WORK as PLAN_AUTHORIZED_CURRENT_WORK,
    DIAGNOSED_STATUS,
    build_report as build_plan_report,
)
from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_data_remediation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "2712185bd10ac648141ccdaabae3dbb9d26e2fc5"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _diagnosis(path: Path) -> Path:
    return _write(
        path,
        json.dumps(
            {
                "final_decision": {
                    "status": DIAGNOSED_STATUS,
                    "passed": True,
                    "failed_checks": [],
                },
                "diagnosis": {
                    "failure_class": "training_summary_includes_prior_evaluation_replay_logs_reused_by_current_evaluation",
                    "current_evaluation_is_not_independent_holdout": True,
                    "nonoverlap_data_required_before_training_preflight": True,
                },
                "path_provenance": {
                    "evaluation_selection_log_count": 32,
                    "previous_training_summary_selection_log_count": 64,
                    "evaluation_signatures_in_previous_count": 32,
                    "evaluation_signatures_missing_in_previous_count": 0,
                },
                "hash_provenance": {
                    "evaluation_record_count": 3200,
                    "matched_evaluation_record_count": 3200,
                    "same_signature_and_step_hash_match_records": 3200,
                    "matched_evaluation_record_rate": 1.0,
                },
            }
        ),
    )


def _audit(path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_nonoverlap_data_remediation_plan_ready",
                f"next_work_target={current_work}",
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


def _plan_audit(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_overlap_failure_diagnosed",
                f"next_work_target={PLAN_AUTHORIZED_CURRENT_WORK}",
                "",
            ]
        ),
    )


def _plan_json(
    tmp_path: Path,
    *,
    mutation: Any | None = None,
) -> Path:
    plan = build_plan_report(
        overlap_failure_diagnosis_json=_diagnosis(tmp_path / "overlap_failure_diagnosis.json"),
        v13_audit_md=_plan_audit(tmp_path / "plan_audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )
    if mutation is not None:
        mutation(plan)
    return _write(tmp_path / "nonoverlap_data_remediation_plan.json", json.dumps(plan))


def _report(tmp_path: Path, *, current_work: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        nonoverlap_plan_json=_plan_json(tmp_path),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_nonoverlap_data_remediation_static_contract_accepts_plan(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    contract = report["contract_summary"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_plan_authorized_next"] is True
    assert decision["implementation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert contract["source_static_contract_review_authorized_next"] is True
    assert contract["source_matched_evaluation_records"] == 3200
    assert contract["train_eval_candidate_tensor_intersection_must_be_zero"] is True
    assert contract["fixed_dp_candidate_generation_requires_later_explicit_preflight"] is True
    assert contract["blocked_deployment"] is True
    assert report["analysis"]["candidate_operation"] == "fixed DP candidate reranking only"
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"


def test_nonoverlap_data_remediation_static_contract_rejects_wrong_audit_scope(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_nonoverlap_data_remediation_static_contract_rejects_training_preflight_auth(
    tmp_path: Path,
) -> None:
    def authorize_training_preflight(plan: dict[str, Any]) -> None:
        plan["final_decision"]["training_preflight_authorized_next"] = True

    report = build_report(
        nonoverlap_plan_json=_plan_json(tmp_path, mutation=authorize_training_preflight),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_plan_does_not_authorize_training_preflight"
        in report["final_decision"]["failed_checks"]
    )


def test_nonoverlap_data_remediation_static_contract_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    def remove_zero_intersection(plan: dict[str, Any]) -> None:
        plan["remediation_plan"]["required_contracts"][
            "train_eval_candidate_tensor_intersection_must_be_zero"
        ] = False

    report = build_report(
        nonoverlap_plan_json=_plan_json(tmp_path, mutation=remove_zero_intersection),
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


def test_nonoverlap_data_remediation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--nonoverlap_plan_json",
            str(_plan_json(tmp_path)),
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
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"]["passed"] is True
    assert READY_STATUS in output_md.read_text(encoding="utf-8")
