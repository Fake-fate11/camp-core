from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_member_source_remediation_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    BLOCKED_SOURCE_FLAGS,
    EXPECTED_FUTURE_BUILDER_SCRIPT,
    EXPECTED_FUTURE_BUILDER_TEST,
    FIXED_DP_HEAD,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_BEHAVIOR,
    REQUIRED_STATIC_REVIEW_REQUIREMENTS,
    SOURCE_PLAN_READY_STATUS,
    SOURCE_PLAN_SCHEMA_VERSION,
    ZERO_INTERSECTION_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "f54758214df3474e59063bca0baea48a8d0fef00"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_remediation_implementation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _implementation_plan(path: Path, *, mutation: Any | None = None) -> Path:
    decision_flags = {flag: False for flag in BLOCKED_SOURCE_FLAGS}
    payload: dict[str, Any] = {
        "schema_version": SOURCE_PLAN_SCHEMA_VERSION,
        "implementation_plan": {
            "implementation_performed_by_this_gate": False,
            "future_builder_script": EXPECTED_FUTURE_BUILDER_SCRIPT,
            "future_builder_test": EXPECTED_FUTURE_BUILDER_TEST,
            "future_artifacts": [
                "fresh_evaluation_split_member_source_manifest.json",
                "fresh_evaluation_split_member_source_nonoverlap_report.json",
                "fresh_evaluation_split_member_source_preflight_inputs.json",
                "SHA256SUMS.txt",
            ],
            "required_future_builder_behavior": list(REQUIRED_BEHAVIOR),
            "required_zero_intersections": {key: 0 for key in ZERO_INTERSECTION_KEYS},
            "required_registry_inputs": {
                "candidate_tensor_hash_registry_required": True,
                "path_signature_registry_required": True,
                "record_identity_hash_registry_required": True,
                "split_manifest_root_registry_required": True,
                "training_registry_must_be_loaded": True,
                "recovered_prior_registry_must_be_loaded": True,
                "rejected_source_registry_must_be_loaded": True,
            },
            "source_failure_to_remediate": {
                "candidate_tensor_hash_intersection_count": 2140,
                "path_signature_intersection_count": 32,
                "record_identity_intersection_count": 3200,
                "split_manifest_root_intersection_count": 0,
                "root_zero_is_not_sufficient": True,
            },
            "math_boundary": {
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
                "master_problem_remains_convex": True,
            },
            "next_gate": (
                "fresh_evaluation_split_member_source_remediation_"
                "implementation_static_contract_review_only"
            ),
        },
        "future_static_contract_review_requirements": list(
            REQUIRED_STATIC_REVIEW_REQUIREMENTS
        ),
        "forbidden_paths": [
            "implementation_code_edit_by_this_gate",
            "fresh_member_selection_by_this_gate",
            "fresh_split_preflight_execution_by_this_gate",
            "evaluation_execution_by_this_gate",
            "replay_execution_by_this_gate",
            "fixed_dp_candidate_generation_execution_by_this_gate",
            "camp_candidate_generation_or_trajectory_modification",
            "diffusion_planner_code_config_or_weight_change",
            "selector_or_atom_promotion",
            "deployment_or_deployable_checkpoint_claim",
            "safety_benefit_or_camp_over_dp_top1_claim",
        ],
        "final_decision": {
            "status": SOURCE_PLAN_READY_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "member_source_remediation_implementation_plan_ready": True,
            "member_source_remediation_implementation_static_contract_review_authorized_next": True,
            **decision_flags,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _plan_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "required_zero_intersections",
                "fail_closed_when_any_required_registry_is_missing_empty_or_unreadable",
                "reject_split_root_only_acceptance",
                "implementation_static_contract_review_only",
                "",
            ]
        ),
    )


def _plan_test(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "def test_rejects_wrong_audit_target(): pass",
                "def test_rejects_source_action_leak(): pass",
                "def test_rejects_missing_zero_contract(): pass",
                "def test_rejects_root_only_or_holdout_reuse(): pass",
                "def test_rejects_dp_head_drift(): pass",
                "",
            ]
        ),
    )


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    return _write(
        path,
        "\n".join(
            [
                f"current_v13_status={LATEST_STATUS}",
                f"next_work_target={target}",
                "implementation_authorized_next=False",
                "fresh_member_selection_execution_authorized_next=False",
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
        implementation_plan_json=_implementation_plan(tmp_path / "implementation_plan.json"),
        implementation_plan_script_py=_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_member_source_remediation_implementation_static_review_authorizes_only_implementation(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["member_source_remediation_implementation_authorized_next"] is True
    assert decision["implementation_authorized_next"] is True
    assert decision["fresh_member_selection_execution_authorized_next"] is False
    assert decision["fresh_evaluation_split_evaluation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["static_contract_review"]["required_zero_intersections"][
        "record_identity_intersection_count"
    ] == 0
    assert report["static_contract_review"]["source_failure_to_remediate"][
        "record_identity_intersection_count"
    ] == 3200


def test_member_source_remediation_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_implementation_static_review_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def authorize_replay(payload: dict[str, Any]) -> None:
        payload["final_decision"]["replay_execution_authorized_next"] = True

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=authorize_replay,
        ),
        implementation_plan_script_py=_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_blocked_action_flags_false" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_remediation_implementation_static_review_rejects_missing_behavior(
    tmp_path: Path,
) -> None:
    def remove_record_identity(payload: dict[str, Any]) -> None:
        payload["implementation_plan"]["required_future_builder_behavior"].remove(
            "prove_zero_record_identity_intersection"
        )

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=remove_record_identity,
        ),
        implementation_plan_script_py=_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_behavior_present" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_implementation_static_review_rejects_missing_zero_contract(
    tmp_path: Path,
) -> None:
    def remove_zero(payload: dict[str, Any]) -> None:
        payload["implementation_plan"]["required_zero_intersections"][
            "candidate_tensor_hash_intersection_count"
        ] = 1

    report = build_report(
        implementation_plan_json=_implementation_plan(
            tmp_path / "implementation_plan.json",
            mutation=remove_zero,
        ),
        implementation_plan_script_py=_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "zero_intersection_contract_preserved" in report["final_decision"][
        "failed_checks"
    ]


def test_member_source_remediation_implementation_static_review_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = build_report(
        implementation_plan_json=_implementation_plan(tmp_path / "implementation_plan.json"),
        implementation_plan_script_py=_plan_script(tmp_path / "plan.py"),
        implementation_plan_test_py=_plan_test(tmp_path / "test_plan.py"),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_implementation_static_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "static_review.json"
    output_md = tmp_path / "static_review.md"

    exit_code = main(
        [
            "--implementation_plan_json",
            str(_implementation_plan(tmp_path / "implementation_plan.json")),
            "--implementation_plan_script_py",
            str(_plan_script(tmp_path / "plan.py")),
            "--implementation_plan_test_py",
            str(_plan_test(tmp_path / "test_plan.py")),
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
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert "Required Behavior" in output_md.read_text(encoding="utf-8")
