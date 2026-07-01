from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_CONTRACTS,
    REQUIRED_IMPLEMENTATION,
    REQUIRED_VERIFICATION,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "dbfb5d30cf775c42023ae06a93de2580e20d2c96"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_evaluation_executed_index_contract_failure_remediation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _plan_artifact(root: Path, *, mutation: Any | None = None) -> Path:
    decision_false_flags = {
        "training_preflight_authorized_next": False,
        "training_execution_authorized_next": False,
        "replay_execution_authorized_next": False,
        "fixed_dp_candidate_generation_authorized_next": False,
        "candidate_generation_by_camp_authorized": False,
        "trajectory_generation_by_camp_authorized": False,
        "trajectory_modification_by_camp_authorized": False,
        "dp_modification_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    payload = {
        "schema_version": (
            "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
            "contract_failure_remediation_plan_v1"
        ),
        "analysis": {
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
            "nonnegative_simplex_weights_only": True,
            "master_problem_remains_convex": True,
        },
        "failure_summary": {
            "executed_index_violations": 2935,
        },
        "source_log_contract_summary": {
            "missing_default_off_shadow_selector_records": 3200,
            "nonzero_executed_index_records": 2935,
        },
        "remediation_plan": {
            "required_contracts": {name: True for name in REQUIRED_CONTRACTS},
            "implementation_requirements": {
                name: True for name in REQUIRED_IMPLEMENTATION
            },
            "verification_requirements": {
                name: True for name in REQUIRED_VERIFICATION
            }
            | {
                "score_expression_remains_affine": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
                "simplex_cvar_l2_master_remains_convex": True,
            },
        },
        "final_decision": {
            "status": (
                "dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_"
                "contract_failure_remediation_plan_ready"
            ),
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "static_contract_review_authorized_next": True,
            **decision_false_flags,
        },
    }
    if mutation is not None:
        mutation(payload)
    _write_json(root / "executed_index_contract_failure_remediation_plan.json", payload)
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
    plan_mutation: Any | None = None,
    target: str = AUTHORIZED_CURRENT_WORK,
) -> dict[str, Any]:
    return build_report(
        plan_artifact_dir=_plan_artifact(tmp_path / "plan", mutation=plan_mutation),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_executed_index_remediation_static_contract_review_passes_plan(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_authorized_next"] is True
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert all(review["required_contracts"][name] is True for name in REQUIRED_CONTRACTS)
    assert (
        review["implementation_requirements"][
            "add_strict_default_off_member_source_filter_before_selection"
        ]
        is True
    )
    assert review["future_allowed_scope"]["implementation_only"] is True
    assert review["future_allowed_scope"]["training"] is False
    assert review["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert review["math_boundary"]["master_problem_remains_convex"] is True


def test_executed_index_remediation_static_contract_review_rejects_wrong_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_executed_index_remediation_static_contract_review_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["remediation_plan"]["required_contracts"][
            "executed_index_must_remain_dp_top1_zero"
        ] = False

    report = _report(tmp_path, plan_mutation=mutate)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "required_contract_executed_index_must_remain_dp_top1_zero"
        in report["final_decision"]["failed_checks"]
    )


def test_executed_index_remediation_static_contract_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    plan = _plan_artifact(tmp_path / "plan")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"

    exit_code = main(
        [
            "--plan_artifact_dir",
            str(plan),
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
    assert "Static Contract Review" in output_md.read_text(encoding="utf-8")
