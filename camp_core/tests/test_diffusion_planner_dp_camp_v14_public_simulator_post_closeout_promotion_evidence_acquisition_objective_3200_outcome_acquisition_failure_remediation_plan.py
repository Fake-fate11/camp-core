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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_failure_remediation.py"
)
RUNTIME_REPLAY_SCRIPT = ROOT / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
SHADOW_PREFLIGHT_SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_shadow_selected_closed_loop_outcome_evaluation.py"
)
CURRENT_HEAD = "a" * 40
SOURCE_HEAD = "b" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_objective_3200_outcome_acquisition_failure_remediation_plan",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_failure_remediation_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    failure = report["source_failed_execution_summary"]
    capability = report["runner_capability_inventory"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_acquisition_failure_remediation_plan_ready"] is True
    assert decision["objective_3200_outcome_acquisition_failure_remediation_plan_static_review_authorized"] is True
    assert decision["candidate_index_replay_harness_static_review_authorized"] is True
    assert decision["direct_candidate_index_replay_execution_authorized"] is False
    assert decision["direct_outcome_acquisition_execution_authorized"] is False
    assert decision["run_level_32_downgrade_selected"] is False
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert failure["runtime_record_count"] == 3200
    assert failure["paired_record_key_count"] == 3200
    assert failure["candidate_closed_loop_outcome_records"] == 0
    assert failure["missing_candidate_closed_loop_outcome_records"] == 3200
    assert capability["runtime_script_has_collect_closed_loop_flag"] is True
    assert capability["runtime_script_has_candidate_index_replay_flag"] is False
    assert [item["name"] for item in report["remediation_plan"]] == list(
        module.EXPECTED_REMEDIATION_PLAN_ITEMS
    )
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_failure_remediation_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "remediation_plan_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_objective_3200_failure_remediation_plan_authorization_missing"
    )


def test_failure_remediation_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_failure_remediation_plan_rejects_non_missing_source_failure(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(
        tmp_path,
        module,
        candidate_outcome_records=3200,
        missing_outcome_records=0,
        objective_satisfied=True,
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_execution_candidate_outcome_records" in report["final_decision"]["failed_checks"]
    assert "source_execution_missing_outcome_records" in report["final_decision"]["failed_checks"]
    assert "source_execution_satisfied_false" in report["final_decision"]["failed_checks"]


def _fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    candidate_outcome_records: int = 0,
    missing_outcome_records: int = 3200,
    objective_satisfied: bool = False,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_FAILURE_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_acquisition_execution_failed=True",
            "requires_user_decision=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    artifact = tmp_path / "failed_execution_artifact"
    execution_dir = artifact / "execution"
    failed_json = _write_json(
        execution_dir / "failed_execution.json",
        _source_execution_report(
            module,
            candidate_outcome_records=candidate_outcome_records,
            missing_outcome_records=missing_outcome_records,
            objective_satisfied=objective_satisfied,
        ),
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

    return {
        "failed_execution_artifact_dir": artifact,
        "failed_execution_json": failed_json,
        "failed_execution_md": failed_md,
        "failed_execution_sha256s": failed_sha,
        "runtime_replay_script_py": RUNTIME_REPLAY_SCRIPT,
        "shadow_outcome_preflight_script_py": SHADOW_PREFLIGHT_SCRIPT,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_execution_report(
    module,
    *,
    candidate_outcome_records: int,
    missing_outcome_records: int,
    objective_satisfied: bool,
) -> dict[str, Any]:
    decision = {
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
        "candidate_closed_loop_outcome_records": candidate_outcome_records,
        "missing_candidate_closed_loop_outcome_records": missing_outcome_records,
        "paired_record_key_count": module.EXPECTED_PAIRED_RECORD_KEYS,
        "objective_3200_outcome_acquisition_satisfied": objective_satisfied,
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
    }
    return {
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
            "candidate_closed_loop_outcome_records": candidate_outcome_records,
            "missing_candidate_closed_loop_outcome_records": missing_outcome_records,
            "objective_3200_outcome_acquisition_satisfied": objective_satisfied,
        },
        "candidate_outcome_source_summary": {
            "record_count": module.OBJECTIVE_REQUIRED_RECORDS,
            "candidate_closed_loop_outcome_records": candidate_outcome_records,
            "missing_candidate_closed_loop_outcome_records": missing_outcome_records,
        },
        "no_go_report": {"failures": ["candidate_closed_loop_outcome_records_missing"]},
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
    for file in files:
        name = file.name if relative_to is None else file.relative_to(relative_to).as_posix()
        lines.append(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {name}")
    return _write(path, "\n".join(lines) + "\n")
