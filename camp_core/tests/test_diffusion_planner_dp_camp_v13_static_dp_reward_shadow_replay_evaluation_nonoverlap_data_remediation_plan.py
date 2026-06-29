from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_data_remediation import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    DIAGNOSED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "648298a212c4da4dc9e502c48113bb5e77ebc0dc"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _diagnosis(path: Path, *, passed: bool = True) -> Path:
    return _write(
        path,
        json.dumps(
            {
                "final_decision": {
                    "status": DIAGNOSED_STATUS if passed else f"{DIAGNOSED_STATUS}_incomplete",
                    "passed": passed,
                    "failed_checks": [] if passed else ["matched_evaluation_record_count"],
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
                "current_v13_status=static_dp_reward_eval_plus_prior_training_artifact_shadow_replay_evaluation_overlap_failure_diagnosed",
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


def _report(tmp_path: Path, *, diagnosis_passed: bool = True, current_work: str = AUTHORIZED_CURRENT_WORK) -> dict:
    return build_report(
        overlap_failure_diagnosis_json=_diagnosis(
            tmp_path / "overlap_failure_diagnosis.json",
            passed=diagnosis_passed,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", current_work=current_work),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_nonoverlap_data_remediation_plan_accepts_diagnosed_overlap_failure(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_authorized_next"] is True
    assert decision["training_preflight_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert report["remediation_plan"]["required_contracts"]["candidate_tensor_hash_registry_required"] is True
    assert report["remediation_plan"]["required_contracts"]["train_eval_candidate_tensor_intersection_must_be_zero"] is True
    assert report["remediation_plan"]["future_preflight_requirements"]["new_nonoverlap_source_root_required"] is True
    assert report["remediation_plan"]["blocked_by_this_plan"]["candidate_generation_execution"] is True
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"


def test_nonoverlap_data_remediation_plan_rejects_wrong_audit_scope(tmp_path: Path) -> None:
    report = _report(tmp_path, current_work="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_gate_authorized_in_audit" in report["final_decision"]["failed_checks"]


def test_nonoverlap_data_remediation_plan_rejects_failed_diagnosis(tmp_path: Path) -> None:
    report = _report(tmp_path, diagnosis_passed=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "diagnosis_status_passed" in report["final_decision"]["failed_checks"]
    assert "diagnosis_status_expected" in report["final_decision"]["failed_checks"]


def test_nonoverlap_data_remediation_plan_main_writes_outputs(tmp_path: Path) -> None:
    diagnosis = _diagnosis(tmp_path / "overlap_failure_diagnosis.json")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"

    exit_code = main(
        [
            "--overlap_failure_diagnosis_json",
            str(diagnosis),
            "--v13_audit_md",
            str(audit),
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
