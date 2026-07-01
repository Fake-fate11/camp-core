from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_implementation_plan import (
    AUDIT_BLOCKED_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    BLOCKED_SOURCE_FLAGS,
    EXPECTED_FUTURE_MATERIALIZER_SCRIPT,
    EXPECTED_FUTURE_MATERIALIZER_TEST,
    FIXED_DP_HEAD,
    FUTURE_OUTPUTS,
    FUTURE_STATIC_REVIEW_REQUIREMENTS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_FUTURE_BEHAVIOR,
    REQUIRED_REVIEW_SCRIPT_TERMS,
    REQUIRED_REVIEW_TEST_TERMS,
    REQUIRED_SOURCE_INPUTS,
    SCHEMA_VERSION,
    SOURCE_REVIEW_PASS_STATUS,
    SOURCE_REVIEW_SCHEMA_VERSION,
    ZERO_INTERSECTION_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "7c11625de8f353ed4035971ab13199efff44a28c"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_static_contract_review_passed"
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
        "fresh_evaluation_split_member_source_materialization_static_contract_review_passed=True",
        "materialization_implementation_plan_authorized_next=True",
        *[f"{flag}=False" for flag in AUDIT_BLOCKED_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _source_review(
    *,
    mutation: Any | None = None,
    future_script: str = EXPECTED_FUTURE_MATERIALIZER_SCRIPT,
    future_test: str = EXPECTED_FUTURE_MATERIALIZER_TEST,
    contract_group_count: int = 7,
) -> dict[str, Any]:
    decision = {
        "status": SOURCE_REVIEW_PASS_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "materialization_static_contract_review_passed": True,
        "materialization_implementation_plan_authorized_next": True,
        **{flag: False for flag in BLOCKED_SOURCE_FLAGS},
        "materialization_executed": False,
        "member_source_builder_executed": False,
        "fixed_dp_candidate_generation_executed": False,
        "replay_executed": False,
        "training_executed": False,
        "dp_modification_executed": False,
    }
    payload = {
        "schema_version": SOURCE_REVIEW_SCHEMA_VERSION,
        "static_contract_review": {
            "future_materializer_script": future_script,
            "future_materializer_test": future_test,
            "required_contract_groups": [f"group_{idx}" for idx in range(contract_group_count)],
        },
        "final_decision": decision,
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _script_source(*, missing_term: str | None = None) -> str:
    terms = [term for term in REQUIRED_REVIEW_SCRIPT_TERMS if term != missing_term]
    return "\n".join(terms)


def _test_source(*, missing_term: str | None = None) -> str:
    terms = [term for term in REQUIRED_REVIEW_TEST_TERMS if term != missing_term]
    return "\n".join(f"def {term}(): pass" for term in terms)


def _inputs(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    dp_head: str = FIXED_DP_HEAD,
    review_mutation: Any | None = None,
    future_script: str = EXPECTED_FUTURE_MATERIALIZER_SCRIPT,
    future_test: str = EXPECTED_FUTURE_MATERIALIZER_TEST,
    contract_group_count: int = 7,
    missing_script_term: str | None = None,
    missing_test_term: str | None = None,
) -> dict[str, Any]:
    return {
        "materialization_static_review_json": _write_json(
            tmp_path / "materialization_static_review.json",
            _source_review(
                mutation=review_mutation,
                future_script=future_script,
                future_test=future_test,
                contract_group_count=contract_group_count,
            ),
        ),
        "materialization_static_review_script_py": _write(
            tmp_path / "review_static_contract.py",
            _script_source(missing_term=missing_script_term),
        ),
        "materialization_static_review_test_py": _write(
            tmp_path / "test_review_static_contract.py",
            _test_source(missing_term=missing_test_term),
        ),
        "v13_audit_md": _audit(tmp_path / "audit.md", target=target),
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": dp_head,
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(**_inputs(tmp_path, **kwargs))


def test_fresh_member_source_materialization_implementation_plan_ready(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["materialization_implementation_plan_ready"] is True
    assert decision["materialization_implementation_static_contract_review_authorized_next"] is True
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
    assert plan["implementation_performed_by_this_gate"] is False
    assert plan["materialization_performed_by_this_gate"] is False
    assert set(REQUIRED_SOURCE_INPUTS) <= set(plan["required_source_inputs"])
    assert set(FUTURE_OUTPUTS) <= set(plan["future_outputs"])
    assert set(REQUIRED_FUTURE_BEHAVIOR) <= set(plan["required_future_materializer_behavior"])
    assert set(FUTURE_STATIC_REVIEW_REQUIREMENTS) <= set(
        plan["future_static_contract_review_requirements"]
    )
    assert all(plan["required_zero_intersections"][key] == 0 for key in ZERO_INTERSECTION_KEYS)
    assert plan["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["math_boundary"]["nonnegative_simplex_weights_only"] is True
    assert plan["math_boundary"]["master_problem_remains_convex"] is True


def test_fresh_member_source_materialization_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_implementation_plan_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["training_execution_authorized_next"] = True

    report = _report(tmp_path, review_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_blocks_training_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_fresh_member_source_materialization_implementation_plan_rejects_source_status_drift(
    tmp_path: Path,
) -> None:
    def drift(payload: dict[str, Any]) -> None:
        payload["final_decision"]["passed"] = False
        payload["final_decision"]["failed_checks"] = ["new_failure"]

    report = _report(tmp_path, review_mutation=drift)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_passed" in report["final_decision"]["failed_checks"]
    assert "source_failed_checks_empty" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_implementation_plan_rejects_missing_contracts(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        contract_group_count=6,
        missing_script_term="all_zero_intersections_required",
        missing_test_term="rejects_missing_contracts",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_review_has_contract_groups" in report["final_decision"]["failed_checks"]
    assert "source_review_script_terms_present" in report["final_decision"]["failed_checks"]
    assert "source_review_test_terms_present" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_implementation_plan_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    paths = _inputs(tmp_path)
    output_json = tmp_path / "out" / "materialization_implementation_plan.json"
    output_md = tmp_path / "out" / "materialization_implementation_plan.md"

    exit_code = main(
        [
            "--materialization_static_review_json",
            str(paths["materialization_static_review_json"]),
            "--materialization_static_review_script_py",
            str(paths["materialization_static_review_script_py"]),
            "--materialization_static_review_test_py",
            str(paths["materialization_static_review_test_py"]),
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["implementation_plan"]["implementation_performed_by_this_gate"] is False
    assert "does not implement or execute the materializer" in output_md.read_text(
        encoding="utf-8"
    )
