from __future__ import annotations

import json
from pathlib import Path

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FRESHNESS_REQUIREMENTS,
    PASS_STATUS,
    PLAN_READY_STATUS,
    PLAN_SCHEMA_VERSION,
    REJECT_STATUS,
    build_report,
    main,
)


CAMP_HEAD = "7002ae900d624da9d46276c7c984d3a48f22d9d8"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _plan(
    path: Path,
    *,
    missing_freshness: str | None = None,
    training_preflight_authorized: bool = False,
) -> Path:
    freshness = {name: True for name in FRESHNESS_REQUIREMENTS}
    if missing_freshness:
        freshness[missing_freshness] = False
    return _write(
        path,
        json.dumps(
            {
                "schema_version": PLAN_SCHEMA_VERSION,
                "analysis": {
                    "plan_only": True,
                    "read_only_inputs": True,
                    "candidate_operation": "fixed DP candidate reranking only",
                    "score_expression": "score_k(w)=a_k^T w",
                },
                "fresh_evaluation_split_plan": {
                    "objective": "define a future fresh evaluation split",
                    "future_scope_contract": {
                        "selection_log_count": 32,
                        "record_count": 3200,
                        "candidate_count": 8,
                        "atom_count": 14,
                        "routes_minimum": 4,
                        "seeds_minimum": 2,
                        "route_traffic_light_buckets_minimum": 8,
                        "formal_seeds_11_12_13_excluded": True,
                        "full36_excluded": True,
                    },
                    "freshness_requirements": freshness,
                    "forbidden_sources": {
                        "current_failed_shadow_replay_evaluation_output": True,
                        "any_selection_log_in_76c2_training_manifest": True,
                        "recovered_prior_c92_registry_records": True,
                        "route_seed_npc_spawn_tl_static_shadow_signature_already_in_training": True,
                    },
                    "runtime_boundary": {
                        "fixed_dp_head_required": FIXED_DP_HEAD,
                        "default_off_shadow_selector_required": True,
                        "selection_effect_must_be_false": True,
                        "executed_output_policy_must_remain_dp_top1": True,
                        "candidate_generation_by_camp_forbidden": True,
                        "camp_trajectory_generation_or_modification_forbidden": True,
                        "reference_blend_guidance_postselection_forbidden": True,
                        "closed_loop_outcome_as_input_forbidden": True,
                        "score_expression": "score_k(w)=a_k^T w",
                        "nonnegative_simplex_weights_only": True,
                    },
                    "minimum_acceptance_before_execution": {
                        "next_gate": "fresh_evaluation_split_static_contract_review_only",
                        "implementation_or_preflight_not_authorized_by_this_plan": True,
                        "static_review_must_reject_missing_registry_checks": True,
                        "static_review_must_reject_any_action_authorization_leak": True,
                        "static_review_must_reject_formal_seed_or_full36_scope": True,
                    },
                    "source_static_review": {
                        "status": (
                            "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                            "nonoverlap_failure_remediation_static_contract_review_passed"
                        ),
                        "record_identity_intersection_count": 3200,
                        "candidate_tensor_eval_hashes_in_previous_rate": 1.0,
                    },
                },
                "final_decision": {
                    "status": PLAN_READY_STATUS,
                    "passed": True,
                    "failed_checks": [],
                    "authorized_next_work": AUTHORIZED_CURRENT_WORK,
                    "fresh_evaluation_split_static_contract_review_authorized_next": True,
                    "implementation_authorized_next": False,
                    "training_preflight_authorized_next": training_preflight_authorized,
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
                },
            }
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"current_v13_status={LATEST_STATUS}",
                f"next_work_target={target}",
                "training_execution_authorized_by_current_boundary=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _report(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    missing_freshness: str | None = None,
    training_preflight_authorized: bool = False,
) -> dict:
    return build_report(
        fresh_evaluation_split_plan_json=_plan(
            tmp_path / "fresh_split_plan.json",
            missing_freshness=missing_freshness,
            training_preflight_authorized=training_preflight_authorized,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fresh_evaluation_split_static_contract_accepts_plan(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_implementation_plan_authorized_next"] is True
    assert decision["implementation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"
    assert report["static_contract_review"]["future_scope_contract"]["record_count"] == 3200


def test_fresh_evaluation_split_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latest_audit_target_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_fresh_evaluation_split_static_contract_rejects_missing_freshness(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        missing_freshness="load_recovered_missing_prior_registry",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_freshness_requirements_present" in report["final_decision"][
        "failed_checks"
    ]


def test_fresh_evaluation_split_static_contract_rejects_action_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, training_preflight_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "blocked_final_decision_flags_false" in report["final_decision"][
        "failed_checks"
    ]


def test_fresh_evaluation_split_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    plan = _plan(tmp_path / "fresh_split_plan.json")
    audit = _audit(tmp_path / "audit.md")
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"

    exit_code = main(
        [
            "--fresh_evaluation_split_plan_json",
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
    assert json.loads(output_json.read_text(encoding="utf-8"))["final_decision"][
        "status"
    ] == PASS_STATUS
    assert PASS_STATUS in output_md.read_text(encoding="utf-8")
