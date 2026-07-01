from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_failure_remediation_implementation_static_contract import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    EXPECTED_FUTURE_INPUT_MATERIALIZER_SCRIPT,
    EXPECTED_FUTURE_INPUT_MATERIALIZER_TEST,
    FIXED_DP_HEAD,
    FUTURE_OUTPUTS,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_IMPLEMENTATION_CONTRACTS,
    REQUIRED_MEMBER_FIELDS,
    REQUIRED_PLAN_SCRIPT_TERMS,
    REQUIRED_PLAN_TEST_TERMS,
    SCHEMA_VERSION,
    SOURCE_PLAN_READY_STATUS,
    SOURCE_PLAN_SCHEMA_VERSION,
    ZERO_INTERSECTION_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "db131c048ee3afcc85cc568a174a3cdc864713d6"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_failure_remediation_implementation_"
    "plan_ready"
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_STATUS}",
        "fresh_evaluation_split_member_source_materialization_failure_remediation_implementation_plan_ready=True",
        "materialization_failure_remediation_implementation_static_contract_review_authorized_next=True",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _source_plan(
    *,
    mutation: Any | None = None,
    missing_contract: bool = False,
) -> dict[str, Any]:
    contracts = list(REQUIRED_IMPLEMENTATION_CONTRACTS)
    if missing_contract:
        contracts.pop()
    decision = {
        "status": SOURCE_PLAN_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "materialization_failure_remediation_implementation_plan_ready": True,
        "materialization_failure_remediation_implementation_static_contract_review_authorized_next": True,
        "implementation_execution_authorized_next": False,
        "input_materialization_execution_authorized_next": False,
        "materialization_execution_authorized_next": False,
        "member_source_builder_execution_authorized_next": False,
        "validation_preflight_authorized_next": False,
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
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    payload = {
        "schema_version": SOURCE_PLAN_SCHEMA_VERSION,
        "final_decision": decision,
        "implementation_plan": {
            "future_input_materializer_script": EXPECTED_FUTURE_INPUT_MATERIALIZER_SCRIPT,
            "future_input_materializer_test": EXPECTED_FUTURE_INPUT_MATERIALIZER_TEST,
            "future_outputs": list(FUTURE_OUTPUTS),
            "required_member_fields": list(REQUIRED_MEMBER_FIELDS),
            "required_implementation_contracts": contracts,
            "required_zero_intersections_after_materialization": {
                key: 0 for key in ZERO_INTERSECTION_KEYS
            },
            "candidate_member_source_strategy": {
                "must_reject_if_no_existing_member_source_evidence": True,
                "must_not_synthesize_identity_hashes": True,
                "must_not_use_rejected_overlap_artifact_as_holdout": True,
            },
            "training_split_root_registry_strategy": {
                "must_write_nonempty_training_split_root_registry": True,
                "split_root_zero_alone_is_insufficient": True,
            },
            "math_boundary": {
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
                "master_problem_remains_convex": True,
                "executed_trajectory_remains_dp_top1": True,
            },
        },
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
    plan_mutation: Any | None = None,
    missing_contract: bool = False,
    missing_script_term: str | None = None,
    missing_test_term: str | None = None,
) -> dict[str, Any]:
    plan = _write_json(
        tmp_path / "implementation_plan.json",
        _source_plan(mutation=plan_mutation, missing_contract=missing_contract),
    )
    return {
        "implementation_plan_json": plan,
        "expected_implementation_plan_sha256": _sha256(plan),
        "implementation_plan_script_py": _write(
            tmp_path / "implementation_plan.py",
            _script_source(missing_term=missing_script_term),
        ),
        "implementation_plan_test_py": _write(
            tmp_path / "test_implementation_plan.py",
            _test_source(missing_term=missing_test_term),
        ),
        "v13_audit_md": _audit(tmp_path / "audit.md", target=target),
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(
        **_inputs(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_materialization_failure_remediation_implementation_static_review_passes(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert (
        decision[
            "materialization_failure_remediation_implementation_static_contract_review_passed"
        ]
        is True
    )
    assert decision["materialization_failure_remediation_implementation_authorized_next"] is True
    assert decision["implementation_execution_authorized_next"] is False
    assert decision["input_materialization_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert set(FUTURE_OUTPUTS) <= set(review["future_outputs"])
    assert set(REQUIRED_MEMBER_FIELDS) <= set(review["required_member_fields"])
    assert set(REQUIRED_IMPLEMENTATION_CONTRACTS) <= set(
        review["required_implementation_contracts"]
    )
    assert review["candidate_member_source_strategy"][
        "must_not_synthesize_identity_hashes"
    ] is True
    assert review["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert review["math_boundary"]["master_problem_remains_convex"] is True


def test_materialization_failure_remediation_implementation_static_review_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["training_execution_authorized_next"] is False


def test_materialization_failure_remediation_implementation_static_review_rejects_source_leak(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["input_materialization_execution_authorized_next"] = True

    report = _report(tmp_path, plan_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_blocks_input_materialization_execution_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_materialization_failure_remediation_implementation_static_review_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    inputs["expected_implementation_plan_sha256"] = "0" * 64

    report = build_report(
        **inputs,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "implementation_plan_sha256" in report["final_decision"]["failed_checks"]


def test_materialization_failure_remediation_implementation_static_review_rejects_missing_contract(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, missing_contract=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "review_lists_contracts" in report["final_decision"]["failed_checks"]


def test_materialization_failure_remediation_implementation_static_review_rejects_missing_script_term(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        missing_script_term="must_not_synthesize_identity_hashes",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "plan_script_terms_present" in report["final_decision"]["failed_checks"]


def test_materialization_failure_remediation_implementation_static_review_main_writes_outputs(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    output_json = tmp_path / "out" / "static_review.json"
    output_md = tmp_path / "out" / "static_review.md"

    exit_code = main(
        [
            "--implementation_plan_json",
            str(inputs["implementation_plan_json"]),
            "--expected_implementation_plan_sha256",
            inputs["expected_implementation_plan_sha256"],
            "--implementation_plan_script_py",
            str(inputs["implementation_plan_script_py"]),
            "--implementation_plan_test_py",
            str(inputs["implementation_plan_test_py"]),
            "--v13_audit_md",
            str(inputs["v13_audit_md"]),
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
    assert "Required Contracts" in output_md.read_text(encoding="utf-8")
