from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.review_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_static_contract import (
    AUDIT_BLOCKED_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    FUTURE_OUTPUTS,
    PASS_STATUS,
    REJECT_STATUS,
    REQUIRED_SOURCE_INPUTS,
    SCHEMA_VERSION,
    SOURCE_PLAN_READY_STATUS,
    SOURCE_PLAN_SCHEMA_VERSION,
    ZERO_INTERSECTION_KEYS,
    build_report,
    main,
)


CAMP_HEAD = "8bcebc331f778a3a0daae07c453054a5ec34347b"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_materialization_plan_ready"
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
        "fresh_evaluation_split_member_source_materialization_plan_ready=True",
        "materialization_static_contract_review_authorized_next=True",
        *[f"{flag}=False" for flag in AUDIT_BLOCKED_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _source_plan(
    *,
    materialization_execution_authorized: bool = False,
    missing_source_input: bool = False,
    missing_future_output: bool = False,
    candidate_overlap_required: int = 0,
    split_root_zero_alone_is_insufficient: bool = True,
) -> dict[str, Any]:
    source_inputs = list(REQUIRED_SOURCE_INPUTS)
    future_outputs = list(FUTURE_OUTPUTS)
    if missing_source_input:
        source_inputs.pop()
    if missing_future_output:
        future_outputs.pop()
    zero = {key: 0 for key in ZERO_INTERSECTION_KEYS}
    zero["candidate_tensor_hash_intersection_count"] = candidate_overlap_required
    return {
        "schema_version": SOURCE_PLAN_SCHEMA_VERSION,
        "analysis": {
            "plan_only": True,
            "candidate_operation": "fixed DP candidate reranking only",
            "score_expression": "score_k(w)=a_k^T w",
        },
        "materialization_plan": {
            "plan_ready_no_inputs_materialized": True,
            "materialization_performed_by_this_gate": False,
            "source_rejected_validation_preflight": True,
            "future_materializer_script": (
                "scripts/integrations/materialize_diffusion_planner_dp_camp_v13_"
                "fresh_evaluation_split_member_source_inputs.py"
            ),
            "future_materializer_test": (
                "camp_core/tests/test_diffusion_planner_dp_camp_v13_"
                "fresh_evaluation_split_member_source_materializer.py"
            ),
            "missing_inputs_to_materialize": source_inputs,
            "future_outputs": future_outputs,
            "required_zero_intersections": zero,
            "candidate_member_manifest_contract": {
                "each_member_has_candidate_tensor_hashes": True,
                "each_member_has_path_signatures": True,
                "each_member_has_record_identity_hashes": True,
                "formal_seeds_11_12_13_excluded": True,
                "full36_excluded": True,
                "source_members_are_not_relabelled_from_rejected_overlap_artifact": True,
            },
            "registry_materialization_contract": {
                "training_registries_loaded_before_selection": True,
                "recovered_prior_registry_loaded_before_selection": True,
                "rejected_overlap_source_registry_loaded_before_selection": True,
                "missing_empty_or_unreadable_registry_fails_closed": True,
                "split_root_zero_alone_is_insufficient": split_root_zero_alone_is_insufficient,
            },
            "future_materializer_contract": [
                "read only already materialized candidate-member and registry inputs",
                "do not run DP or generate candidates in the materializer gate",
                "fail closed if any required source input is missing, empty, or unreadable",
                "require zero candidate/path/record/split-root intersections before preflight can pass",
            ],
            "math_boundary": {
                "score_expression": "score_k(w)=a_k^T w",
                "nonnegative_simplex_weights_only": True,
                "master_problem_remains_convex": True,
                "executed_trajectory_remains_dp_top1": True,
            },
        },
        "final_decision": {
            "status": SOURCE_PLAN_READY_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "materialization_static_contract_review_authorized_next": True,
            "materialization_execution_authorized_next": materialization_execution_authorized,
            "member_source_builder_execution_authorized_next": False,
            "fresh_member_selection_execution_authorized_next": False,
            "fresh_evaluation_split_evaluation_authorized_next": False,
            "data_preparation_authorized_next": False,
            "training_preflight_authorized_next": False,
            "training_execution_authorized_next": False,
            "replay_execution_authorized_next": False,
            "fixed_dp_candidate_generation_authorized_next": False,
            "candidate_generation_by_camp_authorized": False,
            "trajectory_generation_by_camp_authorized": False,
            "trajectory_modification_by_camp_authorized": False,
            "dp_modification_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _script_source() -> str:
    return "\n".join(
        [
            "missing_inputs_to_materialize",
            "future_outputs",
            "required_zero_intersections",
            "split_root_zero_alone_is_insufficient",
            "materialization_static_contract_review_only",
            "score_k(w)=a_k^T w",
        ]
    )


def _test_source() -> str:
    return """
def test_fresh_member_source_materialization_plan_rejects_wrong_audit_target(): pass
def test_fresh_member_source_materialization_plan_rejects_source_action_leak(): pass
def test_fresh_member_source_materialization_plan_rejects_source_failure_drift(): pass
def test_fresh_member_source_materialization_plan_rejects_missing_contract_terms(): pass
"""


def _inputs(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    dp_head: str = FIXED_DP_HEAD,
    **plan_kwargs: Any,
) -> dict[str, Any]:
    return {
        "materialization_plan_json": _write_json(
            tmp_path / "materialization_plan.json",
            _source_plan(**plan_kwargs),
        ),
        "materialization_plan_script_py": _write(
            tmp_path / "materialization_plan.py",
            _script_source(),
        ),
        "materialization_plan_test_py": _write(
            tmp_path / "test_materialization_plan.py",
            _test_source(),
        ),
        "v13_audit_md": _audit(tmp_path / "audit.md", target=target),
        "current_camp_head": CAMP_HEAD,
        "current_camp_origin_main": CAMP_HEAD,
        "current_dp_head": dp_head,
    }


def _report(tmp_path: Path, **kwargs: Any) -> dict[str, Any]:
    return build_report(**_inputs(tmp_path, **kwargs))


def test_fresh_member_source_materialization_static_contract_accepts_plan(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == PASS_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["materialization_static_contract_review_passed"] is True
    assert decision["materialization_implementation_plan_authorized_next"] is True
    assert decision["materialization_execution_authorized_next"] is False
    assert decision["member_source_builder_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"
    assert len(report["static_contract_review"]["required_contract_groups"]) == 7


def test_fresh_member_source_materialization_static_contract_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_static_contract_rejects_action_leak(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, materialization_execution_authorized=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_blocks_materialization_execution_authorized_next" in report[
        "final_decision"
    ]["failed_checks"]


def test_fresh_member_source_materialization_static_contract_rejects_missing_contracts(
    tmp_path: Path,
) -> None:
    report = _report(
        tmp_path,
        missing_source_input=True,
        missing_future_output=True,
        candidate_overlap_required=1,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "all_required_source_inputs_listed" in report["final_decision"]["failed_checks"]
    assert "all_future_outputs_listed" in report["final_decision"]["failed_checks"]
    assert "all_zero_intersections_required" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_static_contract_rejects_root_only_acceptance(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, split_root_zero_alone_is_insufficient=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "split_root_zero_alone_insufficient" in report["final_decision"][
        "failed_checks"
    ]


def test_fresh_member_source_materialization_static_contract_rejects_dp_head_drift(
    tmp_path: Path,
) -> None:
    report = _report(tmp_path, dp_head="0" * 40)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_static_contract_main_writes_outputs(
    tmp_path: Path,
) -> None:
    paths = _inputs(tmp_path)
    output_json = tmp_path / "out" / "materialization_static_contract_review.json"
    output_md = tmp_path / "out" / "materialization_static_contract_review.md"

    exit_code = main(
        [
            "--materialization_plan_json",
            str(paths["materialization_plan_json"]),
            "--materialization_plan_script_py",
            str(paths["materialization_plan_script_py"]),
            "--materialization_plan_test_py",
            str(paths["materialization_plan_test_py"]),
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
    assert "static review authorizes only" in output_md.read_text(encoding="utf-8")
