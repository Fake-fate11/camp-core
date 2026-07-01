from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_default_off_member_source_generation import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    LATEST_AUDIT_STATUS,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_PLAN_STEPS,
    SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "46e1393035607a7f03484ae6abfe89e30e14132a"


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _artifact(root: Path, *, mutation: Any | None = None) -> Path:
    payload = {
        "final_decision": {
            "status": "dp_camp_v13_fresh_evaluation_split_member_source_builder_rejected",
            "passed": False,
            "member_source_manifest_written": False,
            "failed_checks": ["fresh_member_source_candidates_after_filters_nonempty"],
        },
        "selection_summary": {
            "candidate_member_count": 32,
            "selected_member_count": 0,
            "rejected_member_count": 32,
            "rejected_default_off_contract_failed_count": 32,
            "zero_intersection_counts": {
                "candidate_tensor_hash_intersection_count": 0,
                "path_signature_intersection_count": 0,
                "record_identity_intersection_count": 0,
                "split_manifest_root_intersection_count": 0,
            },
        },
    }
    if mutation is not None:
        mutation(payload)
    _write_json(
        root / "rematerialized_outputs" / "member_source_builder_report.json",
        payload,
    )
    return root


def _audit(path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> Path:
    lines = [
        f"current_v13_status={LATEST_AUDIT_STATUS}",
        "fresh_member_source_rematerialization_default_off_member_source_generation_plan_authorized_next=True",
    ]
    for flag in AUDIT_FALSE_FLAGS:
        lines.append(f"{flag}=False")
    lines.extend([f"next_work_target={target}", ""])
    return _write(path, "\n".join(lines))


def _build(tmp_path: Path, *, target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Any]:
    return build_report(
        rematerialization_artifact_dir=_artifact(tmp_path / "artifact"),
        v13_audit_md=_audit(tmp_path / "audit.md", target=target),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )


def test_default_off_member_source_generation_plan_passes(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    plan = report["generation_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["static_contract_review_authorized_next"] is True
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["dp_modification_authorized"] is False
    assert sorted(plan["required_steps"]) == sorted(REQUIRED_PLAN_STEPS)
    assert plan["next_gate_is_static_contract_review_only"] is True
    assert plan["fixed_dp_candidate_generation_execution_authorized_now"] is False


def test_default_off_member_source_generation_plan_rejects_wrong_audit_target(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_default_off_member_source_generation_plan_requires_all_default_off_rejections(
    tmp_path: Path,
) -> None:
    def partial_default_off_failure(payload: dict[str, Any]) -> None:
        payload["selection_summary"]["rejected_default_off_contract_failed_count"] = 12

    report = build_report(
        rematerialization_artifact_dir=_artifact(
            tmp_path / "artifact",
            mutation=partial_default_off_failure,
        ),
        v13_audit_md=_audit(tmp_path / "audit.md"),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "all_rejections_are_default_off_contract"
        in report["final_decision"]["failed_checks"]
    )


def test_default_off_member_source_generation_plan_main_writes_outputs(
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"

    exit_code = main(
        [
            "--rematerialization_artifact_dir",
            str(_artifact(tmp_path / "artifact")),
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
    assert "static contract review" in output_md.read_text(encoding="utf-8")
