from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.integrations.plan_diffusion_planner_dp_camp_v13_fresh_evaluation_split_member_source_materialization_plan import (
    AUDIT_FALSE_FLAGS,
    AUTHORIZED_CURRENT_WORK,
    AUTHORIZED_NEXT_WORK,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    REQUIRED_BUILDER_TERMS,
    REQUIRED_PREFLIGHT_TERMS,
    REQUIRED_SOURCE_INPUTS,
    SCHEMA_VERSION,
    SOURCE_EXECUTION_FALSE_FLAGS,
    SOURCE_FAILURE_CLASS,
    SOURCE_FALSE_FLAGS,
    SOURCE_VALIDATION_REJECT_STATUS,
    SOURCE_VALIDATION_SCHEMA_VERSION,
    build_report,
    main,
)


CAMP_HEAD = "a2321eab180246169f6e443d4a262ddb64834bbd"
LATEST_STATUS = (
    "static_dp_reward_eval_plus_prior_nonoverlap_remediation_training_artifact_"
    "shadow_replay_evaluation_nonoverlap_failure_remediation_fresh_evaluation_"
    "split_member_source_validation_preflight_rejected_missing_materialized_source"
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
        "member_source_materialization_plan_authorized_next=True",
        *[f"{flag}=False" for flag in AUDIT_FALSE_FLAGS],
        f"next_work_target={target}",
        "",
    ]
    return _write(path, "\n".join(lines))


def _validation_payload(*, mutation: Any | None = None) -> dict[str, Any]:
    decision = {
        "status": SOURCE_VALIDATION_REJECT_STATUS,
        "passed": False,
        "failure_class": SOURCE_FAILURE_CLASS,
        "authorized_next_work": AUTHORIZED_CURRENT_WORK,
        "member_source_materialization_plan_authorized_next": True,
        "failed_checks": [
            "member_source_manifest_json_exists",
            "nonoverlap_report_json_exists",
            "preflight_inputs_json_exists",
            "sha256sums_txt_exists",
        ],
        **{flag: False for flag in SOURCE_FALSE_FLAGS},
        **{flag: False for flag in SOURCE_EXECUTION_FALSE_FLAGS},
    }
    payload = {
        "schema_version": SOURCE_VALIDATION_SCHEMA_VERSION,
        "final_decision": decision,
        "member_source_summary": {"selected_member_count": 0},
    }
    if mutation is not None:
        mutation(payload)
    return payload


def _inputs(tmp_path: Path, *, validation_mutation: Any | None = None, target: str = AUTHORIZED_CURRENT_WORK) -> dict[str, Path]:
    return {
        "validation_preflight_json": _write_json(
            tmp_path / "validation_preflight.json",
            _validation_payload(mutation=validation_mutation),
        ),
        "member_source_builder_script_py": _write(
            tmp_path / "builder.py",
            "\n".join(REQUIRED_BUILDER_TERMS),
        ),
        "validation_preflight_script_py": _write(
            tmp_path / "preflight.py",
            "\n".join(REQUIRED_PREFLIGHT_TERMS),
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


def test_fresh_member_source_materialization_plan_ready_but_does_not_materialize(tmp_path: Path) -> None:
    report = _report(tmp_path)
    decision = report["final_decision"]
    plan = report["materialization_plan"]

    assert report["schema_version"] == SCHEMA_VERSION
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["materialization_plan_ready"] is True
    assert decision["materialization_static_contract_review_authorized_next"] is True
    assert decision["materialization_execution_authorized_next"] is False
    assert decision["member_source_builder_execution_authorized_next"] is False
    assert decision["fixed_dp_candidate_generation_authorized_next"] is False
    assert decision["training_execution_authorized_next"] is False
    assert decision["replay_execution_authorized_next"] is False
    assert decision["candidate_generation_by_camp_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert plan["materialization_performed_by_this_gate"] is False
    assert set(REQUIRED_SOURCE_INPUTS) <= set(plan["missing_inputs_to_materialize"])
    assert plan["required_zero_intersections"]["record_identity_intersection_count"] == 0
    assert plan["candidate_member_manifest_contract"]["formal_seeds_11_12_13_excluded"] is True
    assert plan["registry_materialization_contract"]["split_root_zero_alone_is_insufficient"] is True
    assert plan["math_boundary"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["math_boundary"]["master_problem_remains_convex"] is True


def test_fresh_member_source_materialization_plan_rejects_wrong_audit_target(tmp_path: Path) -> None:
    report = _report(tmp_path, target="old_gate")

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["fixed_dp_candidate_generation_authorized_next"] is False


def test_fresh_member_source_materialization_plan_rejects_source_action_leak(tmp_path: Path) -> None:
    def leak(payload: dict[str, Any]) -> None:
        payload["final_decision"]["fixed_dp_candidate_generation_authorized_next"] = True

    report = _report(tmp_path, validation_mutation=leak)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert (
        "source_blocks_fixed_dp_candidate_generation_authorized_next"
        in report["final_decision"]["failed_checks"]
    )


def test_fresh_member_source_materialization_plan_rejects_source_failure_drift(tmp_path: Path) -> None:
    def drift(payload: dict[str, Any]) -> None:
        payload["final_decision"]["passed"] = True
        payload["final_decision"]["failure_class"] = None

    report = _report(tmp_path, validation_mutation=drift)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_passed_false" in report["final_decision"]["failed_checks"]
    assert "source_failure_class_missing" in report["final_decision"]["failed_checks"]


def test_fresh_member_source_materialization_plan_rejects_missing_contract_terms(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    paths["member_source_builder_script_py"].write_text("missing terms", encoding="utf-8")

    report = build_report(
        **paths,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any(
        check.startswith("builder_contains_")
        for check in report["final_decision"]["failed_checks"]
    )


def test_fresh_member_source_materialization_plan_main_writes_outputs(tmp_path: Path) -> None:
    paths = _inputs(tmp_path)
    output_json = tmp_path / "out" / "materialization_plan.json"
    output_md = tmp_path / "out" / "materialization_plan.md"

    exit_code = main(
        [
            "--validation_preflight_json",
            str(paths["validation_preflight_json"]),
            "--member_source_builder_script_py",
            str(paths["member_source_builder_script_py"]),
            "--validation_preflight_script_py",
            str(paths["validation_preflight_script_py"]),
            "--v13_audit_md",
            str(paths["v13_audit_md"]),
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
    assert payload["materialization_plan"]["materialization_performed_by_this_gate"] is False
    assert "plan-only gate does not materialize inputs" in output_md.read_text(
        encoding="utf-8"
    )
