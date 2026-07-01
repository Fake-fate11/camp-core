from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "4396ce46550994c536dfa08383b49ee13635e2e5"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_rejected_executed_index_contract_violation"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _failed_report(path: Path, *, violations: int = 3) -> Path:
    return _write_json(
        path,
        {
            "final_decision": {
                "status": "dp_camp_v13_fresh_evaluation_split_evaluation_rejected",
                "passed": False,
                "failed_checks": ["evaluation_executed_index_violations_zero"]
                if violations
                else [],
                "authorized_next_work": None,
            },
            "evaluation": {
                "selection_log_count": 1,
                "record_count": 3,
                "executed_index_violations": violations,
                "online_selector_change_violations": 0,
                "closed_loop_outcome_records": 0,
                "shadow_differs_from_dp_top1_records": 0,
            },
            "clean_contract": {
                "passed": True,
                "records": 3,
                "failed_records": [],
            },
        },
    )


def _artifact(root: Path, *, violations: int = 3) -> Path:
    _failed_report(root / "fresh_evaluation_split_evaluation.json", violations=violations)
    records = [
        {
            "selected_index": 3,
            "executed_index": 3,
            "atoms": [[0.1] * 14 for _ in range(8)],
            "weights": [1 / 14] * 14,
            "scores": [0.1] * 8,
        },
        {
            "selected_index": 0,
            "executed_index": 0,
            "atoms": [[0.1] * 14 for _ in range(8)],
            "weights": [1 / 14] * 14,
            "scores": [0.1] * 8,
        },
        {
            "selected_index": 2,
            "executed_index": 2,
            "atoms": [[0.1] * 14 for _ in range(8)],
            "weights": [1 / 14] * 14,
            "scores": [0.1] * 8,
        },
    ]
    if violations == 0:
        for record in records:
            record["selected_index"] = 0
            record["executed_index"] = 0
            record["shadow_selected_index"] = 2
            record["default_off_shadow_selector"] = {
                "schema_version": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
                "enabled": True,
                "default_off": True,
                "candidate_operation": "fixed DP candidate reranking only",
                "executed_output_policy": "dp_top1",
                "score_expression": "score_k(w)=a_k^T w",
                "selection_effect": False,
                "online_selector_change": False,
            }
    _write_json(
        root / "evaluation_selection_logs" / "member_000" / "camp_selection_log.json",
        records,
    )
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"current_v13_status={LATEST_STATUS}",
                f"next_work_target={target}",
                *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
                "",
            ]
        ),
    )


def _report(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    violations: int = 3,
) -> dict[str, Any]:
    return build_report(
        failed_execution_artifact_dir=_artifact(tmp_path / "artifact", violations=violations),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_executed_index_contract_failure_remediation_plan_accepts_rejected_execution(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    summary = report["source_log_contract_summary"]
    plan = report["remediation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_authorized_next"] is True
    assert decision["fresh_evaluation_split_evaluation_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["failure_summary"]["executed_index_violations"] == 3
    assert summary["nonzero_executed_index_records"] == 2
    assert summary["missing_default_off_shadow_selector_records"] == 3
    assert plan["required_contracts"]["legacy_selection_logs_with_nonzero_executed_index_rejected"] is True
    assert plan["required_contracts"]["zero_overlap_four_registries_still_required"] is True
    assert plan["blocked_by_this_plan"]["training_execution"] is True
    assert plan["verification_requirements"]["score_expression_remains_affine"] == "score_k(w)=a_k^T w"


def test_executed_index_contract_failure_remediation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_executed_index_contract_failure_remediation_plan_rejects_without_violation(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, violations=0)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "failed_evaluation_executed_index_check_present"
        in report["final_decision"]["failed_checks"]
    )
    assert (
        "source_logs_have_nonzero_executed_index_records"
        in report["final_decision"]["failed_checks"]
    )


def test_executed_index_contract_failure_remediation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    artifact = _artifact(tmp_path / "artifact")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"

    exit_code = main(
        [
            "--failed_execution_artifact_dir",
            str(artifact),
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
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Executed-Index Failure Remediation Plan" in output_md.read_text(encoding="utf-8")
