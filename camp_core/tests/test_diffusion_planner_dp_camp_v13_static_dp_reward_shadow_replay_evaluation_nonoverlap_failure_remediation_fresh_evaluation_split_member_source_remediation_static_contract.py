from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_member_source_remediation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    BLOCKED_FINAL_DECISION_FLAGS,
    FIXED_DP_HEAD,
    PASS_STATUS,
    PLAN_READY_STATUS,
    PLAN_SCHEMA_VERSION,
    REJECT_STATUS,
    ZERO_INTERSECTION_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "ced90ea3368f3ce91e0b7ba83fed3a4502a25ac5"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_plan_ready"
)


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    path.write_text(
        "\n".join(
            [
                f"current_v13_status={LATEST_STATUS}",
                f"next_work_target={target}",
                "fresh_evaluation_split_member_source_remediation_plan_passed=True",
                "fresh_evaluation_split_member_source_remediation_static_contract_review_authorized_next=True",
                "fresh_evaluation_split_evaluation_authorized_next=False",
                "data_preparation_authorized_next=False",
                "training_preflight_authorized_next=False",
                "training_execution_authorized_by_current_boundary=False",
                "runtime_shadow_selector_execution_authorized=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_generation_by_camp_authorized_by_current_boundary=False",
                "trajectory_modification_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "formal_seed_11_12_13_execution_authorized=False",
                "reference_blend_authorized=False",
                "guidance_authorized=False",
                "postprocess_or_postselection_authorized=False",
                "closed_loop_outcome_authorized=False",
                "online_selector_change_authorized=False",
                "executed_trajectory_change_authorized=False",
                "selector_promotion_authorized=False",
                "atom_promotion_authorized=False",
                "deployment_authorized=False",
                "deployable_checkpoint_claim_authorized=False",
                "safety_benefit_claim_authorized=False",
                "camp_over_dp_top1_claim_authorized=False",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _plan_payload(
    *,
    required_candidate_count: int = 0,
    training_execution_authorized: bool = False,
    root_zero_is_not_sufficient: bool = True,
    rejected_overlap_is_not_holdout: bool = True,
) -> dict[str, Any]:
    required = {
        key: 0
        for key in ZERO_INTERSECTION_KEYS
    }
    required["candidate_tensor_hash_intersection_count"] = required_candidate_count
    required.update(
        {
            "candidate_tensor_hash_registry_required": True,
            "path_signature_registry_required": True,
            "record_identity_hash_registry_required": True,
            "split_manifest_root_registry_required": True,
            "training_registry_must_be_loaded": True,
            "recovered_prior_registry_must_be_loaded": True,
            "rejected_source_registry_must_be_loaded": True,
            "zero_intersection_preflight_required_before_evaluation": True,
        }
    )
    decision_flags = {flag: False for flag in BLOCKED_FINAL_DECISION_FLAGS}
    decision_flags["training_execution_authorized_next"] = training_execution_authorized
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "read_only_inputs": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "member_source_remediation_plan": {
            "failure_attribution": {
                "canonical_failure_class": "candidate_tensor_hash_overlap_with_training_registry",
                "candidate_tensor_hash_intersection_count": 2140,
                "path_signature_intersection_count": 32,
                "record_identity_intersection_count": 3200,
                "split_manifest_root_intersection_count": 0,
                "root_zero_is_not_sufficient": root_zero_is_not_sufficient,
                "failed_checks_empty_is_not_pass": True,
            },
            "rejected_source_constraints": {
                "rejected_overlap_artifact_is_not_evaluation_holdout": rejected_overlap_is_not_holdout,
                "source_builder_did_not_select_fresh_members": True,
                "candidate_path_record_overlap_requires_member_source_replacement": True,
                "do_not_relabel_overlapping_members_as_fresh": True,
            },
            "required_fresh_member_source_contract": required,
            "next_gate_requirements": {
                "next_gate": "fresh_evaluation_split_member_source_remediation_static_contract_review_only",
                "review_must_reject_missing_registry_inputs": True,
                "review_must_reject_split_root_only_acceptance": True,
                "review_must_reject_reusing_rejected_overlap_source": True,
                "review_must_reject_any_action_authorization_leak": True,
                "review_must_preserve_fixed_dp_head": FIXED_DP_HEAD,
                "review_must_preserve_score_affine": "score_k(w)=a_k^T w",
            },
            "boundary": {
                "plan_only": True,
                "fresh_member_selection_execution_authorized": False,
                "evaluation_execution_authorized": False,
                "fixed_dp_candidate_generation_authorized": False,
                "replay_authorized": False,
                "training_authorized": False,
                "dp_modification_authorized": False,
            },
        },
        "final_decision": {
            "status": PLAN_READY_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "member_source_remediation_static_contract_review_authorized_next": True,
            **decision_flags,
        },
    }


def _plan(path: Path, **overrides: Any) -> Path:
    return _write_json(path, _plan_payload(**overrides))


def _report(tmp_path: Path, *, target: str = AUTHORIZED_CURRENT_WORK, **overrides: Any) -> dict:
    return build_report(
        member_source_remediation_plan_json=_plan(tmp_path / "member_source_plan.json", **overrides),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_member_source_remediation_static_contract_accepts_plan(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["member_source_remediation_implementation_plan_authorized_next"] is True
    assert decision["fresh_member_selection_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"
    assert report["static_contract_review"]["failure_attribution_contract"][
        "candidate_tensor_hash_intersection_count"
    ] == 2140


def test_member_source_remediation_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_static_contract_rejects_missing_zero_contract(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, required_candidate_count=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_zero_intersection_contracts_present" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_remediation_static_contract_rejects_action_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, training_execution_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "blocked_final_decision_flags_false" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_remediation_static_contract_rejects_root_only_or_holdout_reuse(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        root_zero_is_not_sufficient=False,
        rejected_overlap_is_not_holdout=False,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "root_zero_marked_insufficient" in report["final_decision"]["failed_checks"]
    assert "rejected_overlap_not_holdout" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path / "member_source_plan.json")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "out" / "static_contract_review.json"
    output_md = tmp_path / "out" / "static_contract_review.md"

    exit_code = main(
        [
            "--member_source_remediation_plan_json",
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
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert "four-way zero intersection" in output_md.read_text(encoding="utf-8")
