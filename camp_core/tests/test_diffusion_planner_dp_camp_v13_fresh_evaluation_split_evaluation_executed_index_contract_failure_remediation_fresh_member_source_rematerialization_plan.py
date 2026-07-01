from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fresh_evaluation_split_evaluation_executed_index_contract_failure_remediation_fresh_member_source_rematerialization import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    LATEST_AUDIT_STATUS,
    POST_REVIEW_SCHEMA_VERSION,
    POST_REVIEW_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_PLAN_STEPS,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "5153e7cef8650342b893632d82ca84bacfabe5e0"


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _post_review(root: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "schema_version": POST_REVIEW_SCHEMA_VERSION,
        "static_contract_review": {
            "source_path_file_required": True,
            "default_off_shadow_selector_schema_required": "dp_camp_v13_default_off_shadow_selector_runtime_v1",
            "selected_index_must_remain_dp_top1_zero": True,
            "executed_index_must_remain_dp_top1_zero": True,
            "shadow_selected_index_required_for_camp_choice": True,
            "legacy_non_default_off_selection_logs_rejected": True,
            "score_expression": "score_k(w)=a_k^T w",
        },
        "final_decision": {
            "status": POST_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "authorized_next_work": AUTHORIZED_CURRENT_WORK,
            "fresh_evaluation_split_evaluation_execution_authorized_next": False,
            "training_execution_authorized_next": False,
            "dp_modification_authorized": False,
        },
    }
    if mutation is not None:
        mutation(payload)
    return _write_json(root / "post_implementation_static_contract_review.json", payload)


def _audit(
    path: Path,
    *,
    target: str = AUTHORIZED_CURRENT_WORK,
    training_leak: bool = False,
) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "fresh_member_source_rematerialization_plan_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        value = training_leak and flag == "training_execution_authorized_by_current_boundary"
        lines.append(f"{flag}={value}")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, audit_target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    artifact = tmp_path / "post_review"
    _post_review(artifact)
    return build_report(
        post_review_artifact_dir=artifact,
        v13_audit_md=_audit(tmp_path / "audit.md", target=audit_target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_rematerialization_plan_passes(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["rematerialization_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["rematerialization_plan_ready"] is True
    assert decision["rematerialization_implementation_authorized_next"] is True
    assert decision["fresh_member_source_materialization_execution_authorized_next"] is False
    assert decision["fresh_evaluation_split_evaluation_execution_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert sorted(plan["required_steps"]) == sorted(REQUIRED_PLAN_STEPS)
    assert plan["rejected_legacy_evaluation_member_source_reusable_as_holdout"] is False
    assert plan["requires_executed_index_zero"] is True
    assert plan["authorized_next_gate"] == AUTHORIZED_NEXT_WORK


def test_rematerialization_plan_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _build(tmp_path, audit_target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_rematerialization_plan_rejects_failed_post_review(tmp_path: Path) -> None:
    artifact = tmp_path / "post_review"

    def fail(payload: dict[str, Any]) -> None:
        payload["final_decision"]["passed"] = False

    _post_review(artifact, mutation=fail)
    report = build_report(
        post_review_artifact_dir=artifact,
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "post_review_passed" in report["final_decision"]["failed_checks"]


def test_rematerialization_plan_rejects_training_leak(tmp_path: Path) -> None:
    artifact = tmp_path / "post_review"
    _post_review(artifact)
    report = build_report(
        post_review_artifact_dir=artifact,
        v13_audit_md=_audit(tmp_path / "audit.md", training_leak=True),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "audit_blocks_training_execution_authorized_by_current_boundary"
        in report["final_decision"]["failed_checks"]
    )


def test_rematerialization_plan_main_writes_outputs(tmp_path: Path) -> None:
    artifact = tmp_path / "post_review"
    _post_review(artifact)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"

    exit_code = main(
        [
            "--post_review_artifact_dir",
            str(artifact),
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
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "fresh member-source rematerialization" in output_md.read_text(
        encoding="utf-8"
    ).lower()
