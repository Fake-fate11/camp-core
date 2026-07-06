from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition.py"
)
SOURCE_REVIEW_HEAD = "a" * 40
SOURCE_PLAN_HEAD = "b" * 40
CURRENT_HEAD = "c" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_objective_3200_outcome_acquisition_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    objective = report["objective_3200_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_acquisition_preflight_ready"] is True
    assert decision["objective_3200_outcome_acquisition_preflight_static_review_authorized"] is True
    assert decision["direct_acquisition_execution_authorized"] is False
    assert decision["direct_replay_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert objective["objective_required_records"] == 3200
    assert objective["runtime_record_count"] == 3200
    assert objective["candidate_closed_loop_outcome_records"] == 0
    assert objective["missing_candidate_closed_loop_outcome_records"] == 3200
    assert objective["requires_acquisition_execution"] is True
    assert [item["item"] for item in report["preflight_items"]] == list(
        module.EXPECTED_PREFLIGHT_ITEMS
    )
    assert report["planned_outputs"] == list(module.EXPECTED_PLANNED_OUTPUTS)
    assert report["no_go_register"] == list(module.PREFLIGHT_NO_GO)
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_objective_3200_outcome_acquisition_preflight_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "acquisition_preflight_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_objective_3200_outcome_acquisition_preflight_authorization_missing"
    )


def test_objective_3200_outcome_acquisition_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_objective_3200_outcome_acquisition_preflight_rejects_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_review_decision_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_static_review_camp_over_dp_top1_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_objective_3200_outcome_acquisition_preflight_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_static_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "source_static_review_root_md_sha" in report["final_decision"][
        "failed_checks"
    ]
    assert "source_static_review_nested_md_sha" in report["final_decision"][
        "failed_checks"
    ]


def test_objective_3200_outcome_acquisition_preflight_rejects_satisfied_objective(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        candidate_records=3200,
        missing_records=0,
        existing_artifacts_satisfy=True,
        requires_acquisition_plan=False,
    )

    report = module.build_report(**fixture)

    assert "candidate_closed_loop_outcome_records" in report["final_decision"][
        "failed_checks"
    ]
    assert "missing_candidate_closed_loop_outcome_records" in report["final_decision"][
        "failed_checks"
    ]
    assert "source_plan_existing_artifacts_satisfy_objective" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_review_decision_updates: dict[str, Any] | None = None,
    source_plan_decision_updates: dict[str, Any] | None = None,
    candidate_records: int = 0,
    missing_records: int = 3200,
    existing_artifacts_satisfy: bool = False,
    requires_acquisition_plan: bool = True,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_acquisition_plan_static_review_passed=True",
            "objective_3200_outcome_acquisition_preflight_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source_plan_report = _source_plan_report(
        module,
        source_plan_decision_updates=source_plan_decision_updates,
        candidate_records=candidate_records,
        missing_records=missing_records,
        existing_artifacts_satisfy=existing_artifacts_satisfy,
        requires_acquisition_plan=requires_acquisition_plan,
    )
    source_review_report = _source_review_report(
        module,
        source_review_decision_updates=source_review_decision_updates,
        candidate_records=candidate_records,
        missing_records=missing_records,
    )

    plan_artifact = tmp_path / "source_plan_artifact"
    plan_dir = plan_artifact / "plan"
    plan_json = _write_json(plan_dir / module.SOURCE_PLAN_JSON_NAME, source_plan_report)
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# plan\n")
    plan_sha = _write_sha256s(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    plan_heads = _write(
        plan_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_PLAN_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_PLAN_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    plan_command = _write(plan_artifact / "COMMAND", "python plan.py\n")
    plan_stdout = _write(plan_artifact / "stdout", "{}\n")
    plan_stderr = _write(plan_artifact / "stderr", "")
    plan_run_exit = _write(plan_artifact / "run.exit", "0\n")
    _write_sha256s(
        plan_artifact / "SHA256SUMS",
        [
            plan_heads,
            plan_command,
            plan_stdout,
            plan_stderr,
            plan_run_exit,
            plan_json,
            plan_md,
            plan_sha,
        ],
        relative_to=plan_artifact,
    )

    review_artifact = tmp_path / "source_static_review_artifact"
    review_dir = review_artifact / "review"
    review_json = _write_json(review_dir / module.SOURCE_REVIEW_JSON_NAME, source_review_report)
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# review\n")
    review_sha = _write_sha256s(review_dir / "SHA256SUMS", [review_json, review_md])
    review_heads = _write(
        review_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_REVIEW_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_REVIEW_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    review_command = _write(review_artifact / "COMMAND", "python review.py\n")
    review_stdout = _write(review_artifact / "stdout", "{}\n")
    review_stderr = _write(review_artifact / "stderr", "")
    review_run_exit = _write(review_artifact / "run.exit", "0\n")
    _write_sha256s(
        review_artifact / "SHA256SUMS",
        [
            review_heads,
            review_command,
            review_stdout,
            review_stderr,
            review_run_exit,
            review_json,
            review_md,
            review_sha,
        ],
        relative_to=review_artifact,
    )

    return {
        "source_static_review_artifact_dir": review_artifact,
        "source_static_review_json": review_json,
        "source_static_review_md": review_md,
        "source_static_review_sha256s": review_sha,
        "source_acquisition_plan_artifact_dir": plan_artifact,
        "source_acquisition_plan_json": plan_json,
        "source_acquisition_plan_md": plan_md,
        "source_acquisition_plan_sha256s": plan_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_record_count": module.OBJECTIVE_REQUIRED_RECORDS,
        "expected_existing_delta_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
        "enabled": True,
    }


def _source_review_report(
    module,
    *,
    source_review_decision_updates: dict[str, Any] | None,
    candidate_records: int,
    missing_records: int,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_outcome_acquisition_plan_static_review_passed": True,
        "objective_3200_outcome_acquisition_preflight_authorized": True,
        "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_closed_loop_outcome_records": candidate_records,
        "missing_candidate_closed_loop_outcome_records": missing_records,
        "direct_replay_execution_authorized": False,
        "direct_acquisition_execution_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
    }
    if source_review_decision_updates:
        decision.update(source_review_decision_updates)
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": {
            "static_review_only": True,
            "read_only": True,
            "outcome_acquisition_executed": False,
            "closed_loop_replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "source_plan_summary": {
            "plan_step_count": len(module.EXPECTED_PLAN_STEPS),
            "no_go_count": len(module.EXPECTED_NO_GO),
            "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
            "candidate_closed_loop_outcome_records": candidate_records,
            "missing_candidate_closed_loop_outcome_records": missing_records,
        },
        "final_decision": decision,
    }


def _source_plan_report(
    module,
    *,
    source_plan_decision_updates: dict[str, Any] | None,
    candidate_records: int,
    missing_records: int,
    existing_artifacts_satisfy: bool,
    requires_acquisition_plan: bool,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_PLAN_STATUS,
        "authorized_next_work": module.SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
        "objective_3200_outcome_acquisition_plan_ready": True,
        "objective_3200_outcome_acquisition_plan_static_review_authorized": True,
        "direct_replay_execution_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
        "training_authorized": False,
        "training_execution_authorized": False,
        "candidate_generation_authorized": False,
        "dp_modification_authorized": False,
        "online_selector_change_authorized": False,
        "executed_trajectory_change_authorized": False,
        "training_executed_by_this_gate": False,
        "replay_executed_by_this_gate": False,
        "candidate_generation_executed_by_this_gate": False,
        "dp_modified_by_this_gate": False,
        "promotion_executed_by_this_gate": False,
        "deployment_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
    }
    if source_plan_decision_updates:
        decision.update(source_plan_decision_updates)
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "outcome_acquisition_executed": False,
            "closed_loop_replay_execution": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "objective_gap_summary": {
            "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
            "runtime_record_count": module.OBJECTIVE_REQUIRED_RECORDS,
            "existing_delta_count": module.EXISTING_RUN_LEVEL_PAIR_TARGET,
            "candidate_closed_loop_outcome_records": candidate_records,
            "missing_candidate_closed_loop_outcome_records": missing_records,
            "existing_artifacts_satisfy_objective": existing_artifacts_satisfy,
            "requires_acquisition_plan": requires_acquisition_plan,
        },
        "acquisition_plan": [{"step": step} for step in module.EXPECTED_PLAN_STEPS],
        "no_go_register": list(module.EXPECTED_NO_GO),
        "final_decision": decision,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    return _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_sha256s(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    lines = []
    for file_path in files:
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        name = file_path.name if relative_to is None else file_path.relative_to(relative_to).as_posix()
        lines.append(f"{digest}  {name}")
    return _write(path, "\n".join(lines) + "\n")
