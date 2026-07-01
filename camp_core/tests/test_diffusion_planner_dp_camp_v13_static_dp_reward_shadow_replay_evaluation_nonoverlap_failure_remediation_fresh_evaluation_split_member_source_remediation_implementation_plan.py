from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_member_source_remediation_implementation_plan import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    BLOCKED_SOURCE_FLAGS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_REGISTRY_KEYS,
    SOURCE_REVIEW_PASS_STATUS,
    SOURCE_REVIEW_SCHEMA_VERSION,
    ZERO_INTERSECTION_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "c6c036e6d92d563a4c933ca3570406bb358ac218"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_static_contract_review_passed"
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
                "fresh_evaluation_split_member_source_remediation_static_contract_review_passed=True",
                "fresh_evaluation_split_member_source_remediation_implementation_plan_authorized_next=True",
                "fresh_member_selection_execution_authorized_next=False",
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


def _source_payload(
    *,
    required_candidate_count: int = 0,
    training_execution_authorized: bool = False,
    root_zero_is_not_sufficient: bool = True,
    rejected_overlap_is_not_holdout: bool = True,
) -> dict[str, Any]:
    zero_required = {key: 0 for key in ZERO_INTERSECTION_KEYS}
    zero_required["candidate_tensor_hash_intersection_count"] = required_candidate_count
    registries = {key: True for key in REQUIRED_REGISTRY_KEYS}
    decision_flags = {flag: False for flag in BLOCKED_SOURCE_FLAGS}
    decision_flags["training_execution_authorized_next"] = training_execution_authorized
    return {
        "schema_version": SOURCE_REVIEW_SCHEMA_VERSION,
        "analysis": {
            "static_contract_review_only": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "static_contract_review": {
            "required_contract_groups": [
                "rejected_preflight_failure_attribution_contract",
                "four_way_zero_intersection_member_source_contract",
                "rejected_source_exclusion_contract",
                "split_root_only_rejection_contract",
                "fixed_dp_affine_simplex_boundary_contract",
                "no_action_authorization_beyond_implementation_plan_gate",
            ],
            "failure_attribution_contract": {
                "candidate_tensor_hash_intersection_count": 2140,
                "path_signature_intersection_count": 32,
                "record_identity_intersection_count": 3200,
                "split_manifest_root_intersection_count": 0,
                "root_zero_is_not_sufficient": root_zero_is_not_sufficient,
                "failed_checks_empty_is_not_pass": True,
            },
            "required_fresh_member_source_contract": zero_required,
            "required_registry_inputs": registries,
            "rejected_source_constraints": {
                "rejected_overlap_artifact_is_not_evaluation_holdout": rejected_overlap_is_not_holdout,
                "do_not_relabel_overlapping_members_as_fresh": True,
                "candidate_path_record_overlap_requires_member_source_replacement": True,
            },
            "next_gate_requirements": {
                "review_must_reject_missing_registry_inputs": True,
                "review_must_reject_split_root_only_acceptance": True,
                "review_must_reject_reusing_rejected_overlap_source": True,
                "review_must_reject_any_action_authorization_leak": True,
                "review_must_preserve_fixed_dp_head": FIXED_DP_HEAD,
                "review_must_preserve_score_affine": "score_k(w)=a_k^T w",
            },
        },
        "final_decision": {
            "status": SOURCE_REVIEW_PASS_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "member_source_remediation_implementation_plan_authorized_next": True,
            **decision_flags,
        },
    }


def _source(path: Path, **overrides: Any) -> Path:
    return _write_json(path, _source_payload(**overrides))


def _report(tmp_path: Path, *, target: str = AUTHORIZED_CURRENT_WORK, **overrides: Any) -> dict:
    return build_report(
        static_contract_review_json=_source(tmp_path / "static_review.json", **overrides),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_member_source_remediation_implementation_plan_ready_but_does_not_implement(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["member_source_remediation_implementation_plan_ready"] is True
    assert (
        decision[
            "member_source_remediation_implementation_static_contract_review_authorized_next"
        ]
        is True
    )
    assert decision["implementation_authorized_next"] is False
    assert decision["fresh_member_selection_execution_authorized_next"] is False
    assert decision["fresh_evaluation_split_evaluation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["required_zero_intersections"]["record_identity_intersection_count"] == 0
    assert plan["source_failure_to_remediate"]["record_identity_intersection_count"] == 3200
    assert plan["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["math_boundary"]["master_problem_remains_convex"] is True


def test_member_source_remediation_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_implementation_plan_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, training_execution_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_blocked_action_flags_false" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_remediation_implementation_plan_rejects_missing_zero_contract(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, required_candidate_count=1)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_zero_intersection_contracts_present" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_remediation_implementation_plan_rejects_root_only_or_holdout_reuse(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        root_zero_is_not_sufficient=False,
        rejected_overlap_is_not_holdout=False,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_root_zero_marked_insufficient" in report["final_decision"][
        "failed_checks"
    ]
    assert "source_rejected_overlap_not_holdout" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_remediation_implementation_plan_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        static_contract_review_json=_source(tmp_path / "static_review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "implementation_plan.json"
    output_md = tmp_path / "implementation_plan.md"

    exit_code = main(
        [
            "--static_contract_review_json",
            str(_source(tmp_path / "static_review.json")),
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
    assert "Required Future Builder Behavior" in output_md.read_text(encoding="utf-8")
