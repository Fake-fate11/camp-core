from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_implementation_static_contract import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    EXPECTED_FUTURE_BUILDER_SCRIPT,
    EXPECTED_FUTURE_BUILDER_TEST,
    FIXED_DP_HEAD,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_BEHAVIOR,
    SOURCE_PLAN_READY_STATUS,
    SOURCE_PLAN_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "439a582827d4265e30ef7e5a20a44ba1f6eec2df"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_implementation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _implementation_plan(path: Path, *, mutation: Any | None = None) -> Path:
    payload: dict[str, Any] = {
        "schema_version": SOURCE_PLAN_SCHEMA_VERSION,
        "implementation_plan": {
            "implementation_performed_by_this_gate": False,
            "future_builder_script": EXPECTED_FUTURE_BUILDER_SCRIPT,
            "future_builder_test": EXPECTED_FUTURE_BUILDER_TEST,
            "required_future_builder_behavior": list(REQUIRED_BEHAVIOR),
            "future_scope_contract": {
                "selection_log_count": 32,
                "record_count": 3200,
                "candidate_count": 8,
                "atom_count": 14,
            },
            "math_boundary": {
                "candidate_operation": "fixed DP candidate reranking only",
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
            },
        },
        "final_decision": {
            "status": SOURCE_PLAN_READY_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "fresh_evaluation_split_implementation_plan_ready": True,
            "fresh_evaluation_split_implementation_static_contract_review_authorized_next": True,
            "implementation_authorized_next": False,
            "data_preparation_authorized_next": False,
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


def _plan_script(path: Path) -> Path:
    return _write(
        path,
        "\n".join(
            [
                "fresh_evaluation_split_implementation_plan_only",
                "fresh_evaluation_split_implementation_static_contract_review_only",
                "source_blocked_action_flags_false",
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
                "def test_rejects_scope_drift(): pass",
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


def test_fresh_evaluation_split_implementation_static_review_authorizes_only_implementation(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == PASS_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["fresh_evaluation_split_implementation_authorized_next"] is True
    assert decision["implementation_authorized_next"] is True
    assert decision["data_preparation_authorized_next"] is False
    assert decision["training_preflight_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert report["static_contract_review"]["future_scope_contract"]["record_count"] == 3200
    assert (
        report["static_contract_review"]["math_boundary"]["score_expression"]
        == "score_k(w)=a_k^T w"
    )


def test_fresh_evaluation_split_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latest_audit_target_authorizes_static_review" in report["final_decision"][
        "failed_checks"
    ]


def test_fresh_evaluation_split_implementation_static_review_rejects_source_action_leak(
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


def test_fresh_evaluation_split_implementation_static_review_rejects_missing_behavior(
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


def test_fresh_evaluation_split_implementation_static_review_rejects_dp_head_drift(
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
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fresh_evaluation_split_implementation_static_review_main_writes_outputs(
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
    assert payload["final_decision"]["implementation_authorized_next"] is True
    assert PASS_STATUS in output_md.read_text(encoding="utf-8")
