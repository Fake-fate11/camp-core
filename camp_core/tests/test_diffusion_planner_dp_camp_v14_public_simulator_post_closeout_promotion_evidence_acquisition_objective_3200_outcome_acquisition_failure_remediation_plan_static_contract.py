from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_failure_remediation_plan_static_contract.py"
)
PLAN_SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_failure_remediation.py"
)
PLAN_TEST = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_failure_remediation_plan.py"
)
RUNTIME_REPLAY_SCRIPT = ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
SHADOW_PREFLIGHT_SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_shadow_selected_closed_loop_outcome_evaluation.py"
)
CURRENT_HEAD = "c" * 40
SOURCE_HEAD = "d" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_objective_3200_outcome_acquisition_failure_remediation_plan_static_review",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_failure_remediation_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    summary = report["source_plan_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_acquisition_failure_remediation_plan_static_review_passed"] is True
    assert decision[
        "objective_3200_outcome_acquisition_candidate_index_replay_harness_preflight_plan_authorized"
    ] is True
    assert decision["direct_candidate_index_replay_execution_authorized"] is False
    assert decision["direct_outcome_acquisition_execution_authorized"] is False
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert summary["candidate_closed_loop_outcome_records"] == 0
    assert summary["missing_candidate_closed_loop_outcome_records"] == 3200
    assert summary["candidate_index_replay_flag_present"] is False
    assert summary["remediation_plan_item_count"] == len(module.PLAN_MODULE.EXPECTED_REMEDIATION_PLAN_ITEMS)
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_failure_remediation_plan_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_objective_3200_failure_remediation_plan_static_review_authorization_missing"
    )


def test_failure_remediation_plan_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_failure_remediation_plan_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["failure_remediation_plan_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "root_plan_md_sha" in report["final_decision"]["failed_checks"]
    assert "nested_plan_md_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_hash_contract_failure"


def _fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
) -> dict[str, Any]:
    plan_artifact = _write_plan_artifact(tmp_path, module.PLAN_MODULE)
    docs = tmp_path / "static_review_docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PLAN_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_acquisition_failure_remediation_plan_ready=True",
            "objective_3200_outcome_acquisition_failure_remediation_plan_static_review_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    return {
        "failure_remediation_plan_artifact_dir": plan_artifact,
        "failure_remediation_plan_json": plan_artifact / "plan" / module.SOURCE_PLAN_JSON_NAME,
        "failure_remediation_plan_md": plan_artifact / "plan" / module.SOURCE_PLAN_MD_NAME,
        "failure_remediation_plan_sha256s": plan_artifact / "plan" / "SHA256SUMS",
        "plan_script_py": PLAN_SCRIPT,
        "plan_test_py": PLAN_TEST,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_plan_artifact(tmp_path: Path, plan_module) -> Path:
    source_docs = tmp_path / "source_docs"
    source_doc_text = "\n".join(
        [
            f"current_v14_status={plan_module.SOURCE_FAILURE_STATUS}",
            f"next_work_target={plan_module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_acquisition_execution_failed=True",
            "",
        ]
    )
    source_v14 = _write(source_docs / "diffusion_planner_v14_iteration_audit.md", source_doc_text)
    source_status = _write(source_docs / "diffusion_planner_current_status.md", source_doc_text)
    failed_artifact = _write_failed_execution_artifact(tmp_path, plan_module)
    plan_artifact = tmp_path / "failure_remediation_plan_artifact"
    plan_output = plan_artifact / "plan"
    report = plan_module.build_report(
        failed_execution_artifact_dir=failed_artifact,
        failed_execution_json=failed_artifact / "execution" / "failed_execution.json",
        failed_execution_md=failed_artifact / "execution" / "failed_execution.md",
        failed_execution_sha256s=failed_artifact / "execution" / "SHA256SUMS",
        runtime_replay_script_py=RUNTIME_REPLAY_SCRIPT,
        shadow_outcome_preflight_script_py=SHADOW_PREFLIGHT_SCRIPT,
        v14_audit_md=source_v14,
        current_status_md=source_status,
        output_dir=plan_output,
        current_camp_head=CURRENT_HEAD,
        current_camp_origin_main=CURRENT_HEAD,
        current_dp_head=plan_module.FIXED_DP_HEAD,
        required_dp_head=plan_module.FIXED_DP_HEAD,
        enabled=True,
    )
    plan_module.write_outputs(plan_output, report)
    heads = _write(
        plan_artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
                f"DP_HEAD={plan_module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    command = _write(plan_artifact / "COMMAND", "python plan.py\n")
    stdout = _write(plan_artifact / "stdout", "{}\n")
    stderr = _write(plan_artifact / "stderr", "")
    run_exit = _write(plan_artifact / "run.exit", "0\n")
    _write_sha256s(
        plan_artifact / "SHA256SUMS",
        [
            heads,
            command,
            stdout,
            stderr,
            run_exit,
            plan_output / plan_module.PLAN_JSON_NAME,
            plan_output / plan_module.PLAN_MD_NAME,
            plan_output / "SHA256SUMS",
        ],
        relative_to=plan_artifact,
    )
    return plan_artifact


def _write_failed_execution_artifact(tmp_path: Path, module) -> Path:
    artifact = tmp_path / "failed_execution_artifact"
    execution_dir = artifact / "execution"
    failed_json = _write_json(
        execution_dir / "failed_execution.json",
        {
            "schema_version": module.SOURCE_EXECUTION_SCHEMA,
            "analysis": {
                "objective_3200_outcome_acquisition_execution": True,
                "score_expression": module.SCORE_EXPRESSION,
                "replay_execution": False,
                "training_execution": False,
                "candidate_generation": False,
                "dp_modification": False,
            },
            "objective_3200_outcome_acquisition_summary": {
                "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
                "runtime_record_count": module.OBJECTIVE_REQUIRED_RECORDS,
                "candidate_source_record_count": module.OBJECTIVE_REQUIRED_RECORDS,
                "paired_record_key_count": module.EXPECTED_PAIRED_RECORD_KEYS,
                "candidate_closed_loop_outcome_records": 0,
                "missing_candidate_closed_loop_outcome_records": module.EXPECTED_MISSING_RECORDS,
                "objective_3200_outcome_acquisition_satisfied": False,
            },
            "candidate_outcome_source_summary": {
                "record_count": module.OBJECTIVE_REQUIRED_RECORDS,
                "candidate_closed_loop_outcome_records": 0,
                "missing_candidate_closed_loop_outcome_records": module.EXPECTED_MISSING_RECORDS,
            },
            "no_go_report": {"failures": ["candidate_closed_loop_outcome_records_missing"]},
            "final_decision": {
                "passed": False,
                "status": module.SOURCE_FAILURE_STATUS,
                "failure_class": "objective_3200_outcome_acquisition_execution_source_missing",
                "failed_checks": [
                    "candidate_outcome_record_count",
                    "candidate_missing_outcome_record_count",
                    "objective_3200_outcome_acquisition_satisfied",
                ],
                "authorized_next_work": None,
                "recommended_next_work": module.AUTHORIZED_CURRENT_WORK,
                "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
                "runtime_record_count": module.OBJECTIVE_REQUIRED_RECORDS,
                "candidate_closed_loop_outcome_records": 0,
                "missing_candidate_closed_loop_outcome_records": module.EXPECTED_MISSING_RECORDS,
                "paired_record_key_count": module.EXPECTED_PAIRED_RECORD_KEYS,
                "objective_3200_outcome_acquisition_satisfied": False,
                "actual_safetycost_v1_available": False,
                "actual_safetycost_v1_claim_rule_evaluable": False,
                "selector_promotion_authorized": False,
                "deployment_authorized": False,
                "online_selector_change_authorized": False,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
                "outcome_acquisition_executed_by_this_gate": True,
                "replay_executed_by_this_gate": False,
                "training_executed_by_this_gate": False,
                "candidate_generation_executed_by_this_gate": False,
                "dp_modified_by_this_gate": False,
            },
        },
    )
    failed_md = _write(execution_dir / "failed_execution.md", "# failed execution\n")
    failed_sha = _write_sha256s(execution_dir / "SHA256SUMS", [failed_json, failed_md])
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={SOURCE_HEAD}",
                f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    command = _write(artifact / "COMMAND", "python execute.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "1\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, failed_json, failed_md, failed_sha],
        relative_to=artifact,
    )
    return artifact


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
    for file in files:
        name = file.name if relative_to is None else file.relative_to(relative_to).as_posix()
        lines.append(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {name}")
    return _write(path, "\n".join(lines) + "\n")
