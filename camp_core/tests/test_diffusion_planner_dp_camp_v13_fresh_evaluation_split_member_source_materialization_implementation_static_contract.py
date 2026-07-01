from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_implementation_static_contract import (
    AUDIT_BLOCKED_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    EXPECTED_FUTURE_MATERIALIZER_SCRIPT,
    EXPECTED_FUTURE_MATERIALIZER_TEST,
    FIXED_DP_HEAD,
    FUTURE_OUTPUTS,
    FUTURE_STATIC_REVIEW_REQUIREMENTS,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_FUTURE_BEHAVIOR,
    REQUIRED_PLAN_SCRIPT_TERMS,
    REQUIRED_PLAN_TEST_TERMS,
    REQUIRED_SOURCE_INPUTS,
    SCHEMA_VERSION,
    SOURCE_BLOCKED_FLAGS,
    SOURCE_PLAN_READY_STATUS,
    SOURCE_PLAN_SCHEMA_VERSION,
    ZERO_INTERSECTION_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "90bd249548a25ed6d7dcc1f45d61efde099e2f3b"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_implementation_plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fresh_evaluation_split_member_source_materialization_implementation_plan_ready=True",
        "materialization_implementation_static_contract_review_authorized_next=True",
        *[f"{flag}=False" for flag in AUDIT_BLOCKED_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _source_plan(
    *,
    mutation: Any | None = None,
    missing_required_behavior: bool = False,
    missing_static_review_requirement: bool = False,
    nonzero_intersection: bool = False,
) -> dict[str, Any]:
    behavior = list(REQUIRED_FUTURE_BEHAVIOR)
    requirements = list(FUTURE_STATIC_REVIEW_REQUIREMENTS)
    if missing_required_behavior:
        behavior.pop()
    if missing_static_review_requirement:
        requirements.pop()
    zero = {key: 0 for key in ZERO_INTERSECTION_KEYS}
    if nonzero_intersection:
        zero["record_identity_intersection_count"] = 1
    decision = {
        "status": SOURCE_PLAN_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "materialization_implementation_plan_ready": True,
        "materialization_implementation_static_contract_review_authorized_next": True,
        **{flag: False for flag in SOURCE_BLOCKED_FLAGS},
        "implementation_executed": False,
        "materialization_executed": False,
        "member_source_builder_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }
    payload = {
        "schema_version": SOURCE_PLAN_SCHEMA_VERSION,
        "implementation_plan": {
            "implementation_performed_by_this_gate": False,
            "materialization_performed_by_this_gate": False,
            "future_materializer_script": EXPECTED_FUTURE_MATERIALIZER_SCRIPT,
            "future_materializer_test": EXPECTED_FUTURE_MATERIALIZER_TEST,
            "required_source_inputs": list(REQUIRED_SOURCE_INPUTS),
            "future_outputs": list(FUTURE_OUTPUTS),
            "required_future_materializer_behavior": behavior,
            "future_static_contract_review_requirements": requirements,
            "required_zero_intersections": zero,
            "required_registry_inputs": {
                "candidate_member_source_manifest_required": True,
                "training_candidate_tensor_hash_registry_required": True,
                "training_path_signature_registry_required": True,
                "training_record_identity_registry_required": True,
                "training_split_manifest_root_registry_required": True,
                "recovered_prior_registry_required": True,
                "rejected_overlap_source_registry_required": True,
            },
            "math_boundary": {
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
                "master_problem_remains_convex": True,
                "executed_trajectory_remains_dp_top1": True,
            },
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _script_source(*, missing_term: str | None = None) -> str:
    terms = [term for term in REQUIRED_PLAN_SCRIPT_TERMS if term != missing_term]
    return "\n".join(terms)


def _test_source(*, missing_term: str | None = None) -> str:
    terms = [term for term in REQUIRED_PLAN_TEST_TERMS if term != missing_term]
    return "\n".join(f"def {term}(): pass" for term in terms)


def _inputs(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    dp_head: str = FIXED_DP_HEAD,
    plan_mutation: Any | None = None,
    missing_required_behavior: bool = False,
    missing_static_review_requirement: bool = False,
    nonzero_intersection: bool = False,
    missing_script_term: str | None = None,
    missing_test_term: str | None = None,
) -> dict[str, Any]:
    return {
        "materialization_implementation_plan_json": _write_json(
            tmp_path / "materialization_implementation_plan.json",
            _source_plan(
                mutation=plan_mutation,
                missing_required_behavior=missing_required_behavior,
                missing_static_review_requirement=missing_static_review_requirement,
                nonzero_intersection=nonzero_intersection,
            ),
        ),
        "materialization_implementation_plan_script_py": _write(
            tmp_path / "implementation_plan.py",
            _script_source(missing_term=missing_script_term),
        ),
        "materialization_implementation_plan_test_py": _write(
            tmp_path / "test_implementation_plan.py",
            _test_source(missing_term=missing_test_term),
        ),
        "v13_audit_md": _audit(tmp_path / "audit.md", target=target),
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": dp_head,
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(**_inputs(tmp_path, **kwargs))


def test_fresh_member_source_materialization_implementation_static_review_passes(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["implementation_static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["materialization_implementation_static_contract_review_passed"] is True
    assert decision["materialization_implementation_authorized_next"] is True
    assert decision["implementation_execution_authorized_next"] is False
    assert decision["materialization_execution_authorized_next"] is False
    assert decision["member_source_builder_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["trajectory_modification_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert len(review["required_contract_groups"]) == 7
    assert set(REQUIRED_SOURCE_INPUTS) <= set(review["required_source_inputs"])
    assert set(FUTURE_OUTPUTS) <= set(review["future_outputs"])
    assert all(review["required_zero_intersections"][key] == 0 for key in ZERO_INTERSECTION_KEYS)
    assert review["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"


def test_fresh_member_source_materialization_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_implementation_static_review_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_authorized_next"] = True

    report = _report(tmp_path, plan_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_blocks_fixed_dp_candidate_generation_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_fresh_member_source_materialization_implementation_static_review_rejects_missing_contracts(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        missing_required_behavior=True,
        missing_static_review_requirement=True,
        nonzero_intersection=True,
        missing_script_term="REQUIRED_FUTURE_BEHAVIOR",
        missing_test_term="test_fresh_member_source_materialization_implementation_plan_rejects_missing_contracts",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_lists_required_behavior" in report["final_decision"]["failed_checks"]
    assert "source_lists_static_review_requirements" in report["final_decision"]["failed_checks"]
    assert "source_requires_zero_intersections" in report["final_decision"]["failed_checks"]
    assert "plan_script_terms_present" in report["final_decision"]["failed_checks"]
    assert "plan_test_terms_present" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_implementation_static_review_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_implementation_static_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    paths = _inputs(tmp_path)
    output_json = tmp_path / "out" / "implementation_static_review.json"
    output_md = tmp_path / "out" / "implementation_static_review.md"

    exit_code = main(
        [
            "--materialization_implementation_plan_json",
            str(paths["materialization_implementation_plan_json"]),
            "--materialization_implementation_plan_script_py",
            str(paths["materialization_implementation_plan_script_py"]),
            "--materialization_implementation_plan_test_py",
            str(paths["materialization_implementation_plan_test_py"]),
            "--v13_audit_md",
            str(paths["v13_audit_md"]),
            "--current_camp_head",
            str(paths["current_camp_head"]),
            "--current_camp_origin_main",
            str(paths["current_camp_origin_main"]),
            "--current_dp_head",
            str(paths["current_dp_head"]),
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["final_decision"]["status"] == PASS_STATUS
    assert payload["final_decision"]["materialization_execution_authorized_next"] is False
    assert "does not materialize inputs" in output_md.read_text(encoding="utf-8")
