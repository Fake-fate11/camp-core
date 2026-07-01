from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_failure_remediation_implementation_plan import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_OUTPUTS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_IMPLEMENTATION_CONTRACTS,
    REQUIRED_MEMBER_FIELDS,
    SCHEMA_VERSION,
    SOURCE_PLAN_READY_STATUS,
    SOURCE_PLAN_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "2933fa9107736aa38e0d2b92f808c6303a4921e7"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_failure_remediation_plan_ready"
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
        "fresh_evaluation_split_member_source_materialization_failure_remediation_plan_ready=True",
        "candidate_member_source_manifest_missing=True",
        "training_split_manifest_root_registry_missing=True",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _source_plan(*, mutation: Any | None = None) -> dict[str, Any]:
    decision = {
        "status": SOURCE_PLAN_READY_STATUS,
        "passed": True,
        "failed_checks": [],
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "materialization_failure_remediation_implementation_plan_authorized_next": True,
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
        "materialization_rejection_summary": {
            "candidate_member_source_manifest_structures_found": 0,
            "candidate_member_count": 0,
            "training_split_manifest_root_count": 0,
        },
        "remediation_plan": {
            "next_gate": (
                "fresh_evaluation_split_member_source_materialization_"
                "failure_remediation_implementation_plan_only"
            ),
        },
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _inputs(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    source_mutation: Any | None = None,
) -> dict[str, Any]:
    source = _write_json(
        tmp_path / "failure_remediation_plan.json",
        _source_plan(mutation=source_mutation),
    )
    return {
        "failure_remediation_plan_json": source,
        "expected_failure_remediation_plan_sha256": _sha256(source),
        "v13_audit_md": _audit(tmp_path / "audit.md", target=target),
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(
        **_inputs(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_materialization_failure_remediation_implementation_plan_ready(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["implementation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["materialization_failure_remediation_implementation_plan_ready"] is True
    assert (
        decision[
            "materialization_failure_remediation_implementation_static_contract_review_authorized_next"
        ]
        is True
    )
    assert decision["implementation_execution_authorized_next"] is False
    assert decision["input_materialization_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert set(FUTURE_OUTPUTS) <= set(plan["future_outputs"])
    assert set(REQUIRED_MEMBER_FIELDS) <= set(plan["required_member_fields"])
    assert set(REQUIRED_IMPLEMENTATION_CONTRACTS) <= set(
        plan["required_implementation_contracts"]
    )
    assert (
        plan["candidate_member_source_strategy"][
            "must_reject_if_no_existing_member_source_evidence"
        ]
        is True
    )
    assert plan["training_split_root_registry_strategy"][
        "must_write_nonempty_training_split_root_registry"
    ] is True
    assert plan["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["math_boundary"]["master_problem_remains_convex"] is True


def test_materialization_failure_remediation_implementation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["training_execution_authorized_next"] is False


def test_materialization_failure_remediation_implementation_plan_rejects_source_action_leak(
    tmp_path: Path,
) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_authorized_next"] = True

    report = _report(tmp_path, source_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_blocks_fixed_dp_candidate_generation_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_materialization_failure_remediation_implementation_plan_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    inputs["expected_failure_remediation_plan_sha256"] = "0" * 64

    report = build_report(
        **inputs,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_plan_sha256" in report["final_decision"]["failed_checks"]


def test_materialization_failure_remediation_implementation_plan_rejects_missing_failure_evidence(
    tmp_path: Path,
) -> None:
    def drift(payload: dict[str, Any]) -> None:
        payload["materialization_rejection_summary"]["candidate_member_count"] = 4

    report = _report(tmp_path, source_mutation=drift)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_candidate_member_count_zero" in report["final_decision"]["failed_checks"]


def test_materialization_failure_remediation_implementation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    inputs = _inputs(tmp_path)
    output_json = tmp_path / "out" / "implementation_plan.json"
    output_md = tmp_path / "out" / "implementation_plan.md"

    exit_code = main(
        [
            "--failure_remediation_plan_json",
            str(inputs["failure_remediation_plan_json"]),
            "--expected_failure_remediation_plan_sha256",
            inputs["expected_failure_remediation_plan_sha256"],
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
    assert payload["final_decision"]["status"] == READY_STATUS
    assert "Required Implementation Contracts" in output_md.read_text(encoding="utf-8")
