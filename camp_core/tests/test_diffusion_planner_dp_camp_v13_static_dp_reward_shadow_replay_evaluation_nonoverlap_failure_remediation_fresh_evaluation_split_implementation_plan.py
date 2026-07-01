from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_implementation_plan import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_REVIEW_PASS_STATUS,
    SOURCE_REVIEW_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "40ca517c11021d1c0f375b624ba17a1a58aa49fe"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_static_contract_review_passed"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _source_review(path: Path, *, mutation: Any | None = None) -> Path:
    payload: dict[str, Any] = {
        "schema_version": SOURCE_REVIEW_SCHEMA_VERSION,
        "analysis": {
            "static_contract_review_only": True,
            "read_only_inputs": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "plan_summary": {
            "status": (
                "dp_camp_v13_static_dp_reward_shadow_replay_evaluation_"
                "nonoverlap_failure_remediation_fresh_evaluation_split_plan_ready"
            ),
            "source_record_identity_intersection_count": 3200,
            "source_candidate_tensor_eval_hashes_in_previous_rate": 1.0,
            "future_selection_log_count": 32,
            "future_record_count": 3200,
            "future_candidate_count": 8,
            "future_atom_count": 14,
        },
        "static_contract_review": {
            "required_contract_groups": [
                "future_scope_contract",
                "full_registry_nonoverlap_contract",
                "forbidden_source_exclusion_contract",
                "fixed_dp_default_off_runtime_boundary_contract",
                "affine_simplex_math_boundary_contract",
                "no_action_authorization_beyond_next_implementation_plan_gate",
            ],
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
            "math_boundary": {
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
            },
        },
        "final_decision": {
            "status": SOURCE_REVIEW_PASS_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "fresh_evaluation_split_implementation_plan_authorized_next": True,
            "implementation_authorized_next": False,
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
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write(path, json.dumps(payload))


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"current_v13_status={LATEST_STATUS}",
                f"next_work_target={target}",
                "implementation_authorized_next=False",
                "training_preflight_authorized_next=False",
                "replay_execution_authorized_by_current_boundary=False",
                "fixed_dp_candidate_generation_authorized_by_current_boundary=False",
                "candidate_generation_by_camp_authorized_by_current_boundary=False",
                "dp_modification_authorized_by_current_boundary=False",
                "",
            ]
        ),
    )


def _report(tmp_path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        static_contract_review_json=_source_review(tmp_path / "static_review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_fresh_evaluation_split_implementation_plan_ready_but_does_not_implement(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_implementation_plan_ready"] is True
    assert (
        decision[
            "fresh_evaluation_split_implementation_static_contract_review_authorized_next"
        ]
        is True
    )
    assert decision["implementation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["future_scope_contract"]["record_count"] == 3200


def test_fresh_evaluation_split_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latest_audit_target_authorizes_plan" in report["final_decision"][
        "failed_checks"
    ]


def test_fresh_evaluation_split_implementation_plan_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def authorize_replay(payload: dict[str, Any]) -> None:
        payload["final_decision"]["replay_execution_authorized_next"] = True

    report = build_report(
        static_contract_review_json=_source_review(
            tmp_path / "static_review.json",
            mutation=authorize_replay,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_blocked_action_flags_false" in report["final_decision"][
        "failed_checks"
    ]


def test_fresh_evaluation_split_implementation_plan_rejects_scope_drift(
    tmp_path: Path,
) -> None:
    def shrink_scope(payload: dict[str, Any]) -> None:
        payload["static_contract_review"]["future_scope_contract"]["record_count"] = 1600

    report = build_report(
        static_contract_review_json=_source_review(
            tmp_path / "static_review.json",
            mutation=shrink_scope,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "future_scope_counts_expected" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_implementation_plan_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        static_contract_review_json=_source_review(tmp_path / "static_review.json"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "implementation_plan.json"
    output_md = tmp_path / "implementation_plan.md"

    exit_code = main(
        [
            "--static_contract_review_json",
            str(_source_review(tmp_path / "static_review.json")),
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
