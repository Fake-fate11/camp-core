from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_static_dp_reward_shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_split_member_source_remediation import (
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    SOURCE_FAILURE_CLASS,
    build_report,
    main,
)


CAMP_HEAD = "72069e1088f466efd6080e89cdffccb91009b54b"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_preflight_rejected"
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
                "fresh_evaluation_split_preflight_passed=False",
                "fresh_evaluation_split_member_source_remediation_plan_authorized_next=True",
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
                f"next_work_target={target}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _fixtures(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    preflight_passed: bool = False,
) -> dict[str, Path]:
    artifact = tmp_path / "artifact"
    source = tmp_path / "source"
    builder = _write_json(
        source / "fresh_evaluation_split_manifest_builder_report.json",
        {
            "schema_version": "dp_camp_v13_fresh_evaluation_split_manifest_builder_v1",
            "final_decision": {
                "status": "dp_camp_v13_fresh_evaluation_split_manifest_builder_complete",
                "passed": True,
            },
        },
    )
    scope = _write_json(
        source / "fresh_evaluation_split_scope_manifest.json",
        {
            "schema_version": "dp_camp_v13_fresh_evaluation_split_scope_manifest_v1",
            "target_selection_log_count": 32,
            "target_record_count": 3200,
            "fresh_split_members_selected_by_this_builder": False,
        },
    )
    registry_report = _write_json(
        source / "fresh_evaluation_split_nonoverlap_registry_report.json",
        {
            "schema_version": "dp_camp_v13_fresh_evaluation_split_nonoverlap_registry_report_v1",
            "future_zero_intersection_preflight_required": True,
        },
    )
    source_registry = _write_json(
        source / "registry_manifest.json",
        {
            "schema_version": "dp_camp_v13_current_source_result_review_source_registry_manifest_v1",
            "evaluation_candidate_hash_count": 3200,
        },
    )
    status = (
        "dp_camp_v13_fresh_evaluation_split_preflight_passed"
        if preflight_passed
        else "dp_camp_v13_fresh_evaluation_split_preflight_rejected"
    )
    preflight = _write_json(
        artifact / "fresh_evaluation_split_preflight.json",
        {
            "schema_version": "dp_camp_v13_fresh_evaluation_split_preflight_v1",
            "inputs": {
                "manifest_builder_json": str(builder),
                "scope_manifest_json": str(scope),
                "nonoverlap_registry_report_json": str(registry_report),
                "sha256sums_txt": str(source / "SHA256SUMS.txt"),
            },
            "source_registry_manifest": str(source_registry),
            "manifest_summary": {
                "builder_status": "dp_camp_v13_fresh_evaluation_split_manifest_builder_complete",
                "fresh_split_members_selected_by_builder": False,
            },
            "preflight_result": {
                "all_required_intersections_zero": preflight_passed,
                "candidate_tensor_hash_intersection_count": 0 if preflight_passed else 2140,
                "path_signature_intersection_count": 0 if preflight_passed else 32,
                "record_identity_intersection_count": 0 if preflight_passed else 3200,
                "split_manifest_root_intersection_count": 0,
            },
            "final_decision": {
                "status": status,
                "passed": preflight_passed,
                "failed_checks": [],
                "failure_class": None if preflight_passed else SOURCE_FAILURE_CLASS,
                "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            },
        },
    )
    return {
        "preflight": preflight,
        "audit": _audit(tmp_path / "audit.md", target=target),
    }


def _build(
    tmp_path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    preflight_passed: bool = False,
) -> dict[str, Any]:
    paths = _fixtures(tmp_path, target=target, preflight_passed=preflight_passed)
    return build_report(
        fresh_evaluation_split_preflight_json=paths["preflight"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_member_source_remediation_plan_accepts_rejected_overlap_preflight(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["member_source_remediation_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["member_source_remediation_static_contract_review_authorized_next"] is True
    assert decision["fresh_evaluation_split_evaluation_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert plan["failure_attribution"]["candidate_tensor_hash_intersection_count"] == 2140
    assert plan["failure_attribution"]["path_signature_intersection_count"] == 32
    assert plan["failure_attribution"]["record_identity_intersection_count"] == 3200
    assert plan["failure_attribution"]["split_manifest_root_intersection_count"] == 0
    assert plan["failure_attribution"]["root_zero_is_not_sufficient"] is True
    assert plan["rejected_source_constraints"][
        "rejected_overlap_artifact_is_not_evaluation_holdout"
    ] is True
    assert plan["required_fresh_member_source_contract"][
        "candidate_tensor_hash_intersection_count"
    ] == 0
    assert report["analysis"]["score_expression"] == "score_k(w)=a_k^T w"


def test_member_source_remediation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["fresh_evaluation_split_evaluation_authorized_next"] is False


def test_member_source_remediation_plan_rejects_passed_preflight(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, preflight_passed=True)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "preflight_status_rejected" in report["final_decision"]["failed_checks"]
    assert "preflight_passed_false" in report["final_decision"]["failed_checks"]
    assert "candidate_overlap_nonzero" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_plan_rejects_dp_drift(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    report = build_report(
        fresh_evaluation_split_preflight_json=paths["preflight"],
        v13_audit_md=paths["audit"],
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_member_source_remediation_plan_main_writes_outputs(tmp_path: Path) -> None:
    paths = _fixtures(tmp_path)
    output_json = tmp_path / "out" / "member_source_remediation_plan.json"
    output_md = tmp_path / "out" / "member_source_remediation_plan.md"

    exit_code = main(
        [
            "--fresh_evaluation_split_preflight_json",
            str(paths["preflight"]),
            "--v13_audit_md",
            str(paths["audit"]),
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
    assert "zero split-root intersection alone is insufficient" in output_md.read_text(
        encoding="utf-8"
    )
