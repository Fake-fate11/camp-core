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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_execution_result.py"
)
SOURCE_HEAD = "a" * 40
CURRENT_HEAD = "b" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_replay_outcome_acquisition_execution_result_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_replay_outcome_acquisition_execution_result_review_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    summary = report["source_execution_summary"]
    gap = report["evidence_gap_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["candidate_index_execution_reviewed_by_this_gate"] is True
    assert decision["candidate_index_replay_executed_by_this_gate"] is False
    assert decision["outcome_acquisition_executed_by_this_gate"] is False
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["actual_safetycost_evidence_gap_closure_plan_authorized"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert summary["candidate_closed_loop_outcome_records"] == 4
    assert summary["candidate_tensor_mutation_records"] == 0
    assert gap["claim_supported_by_this_review"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_replay_outcome_acquisition_execution_result_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_execution_result_review_authorization_missing"
    )


def test_candidate_index_replay_outcome_acquisition_execution_result_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_replay_outcome_acquisition_execution_result_review_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"safety_benefit_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_execution_decision_safety_benefit_claim_authorized" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False


def test_candidate_index_replay_outcome_acquisition_execution_result_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_execution_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "nested_execution_md_sha" in report["final_decision"]["failed_checks"]
    assert "root_report_md_sha" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_EXECUTION_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_replay_outcome_acquisition_execution_passed=True",
            "objective_3200_candidate_index_replay_outcome_acquisition_execution_result_review_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "online_selector_change_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    artifact = tmp_path / "source_execution_artifact"
    report_dir = artifact / "report"
    source_json = _write_json(
        report_dir / module.SOURCE_EXECUTION_JSON_NAME,
        _source_execution_report(module, source_decision_updates=source_decision_updates),
    )
    source_md = _write(report_dir / module.SOURCE_EXECUTION_MD_NAME, "# execution\n")
    source_sha = _write_sha256s(report_dir / "SHA256SUMS", [source_json, source_md])
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
    launcher_stdout = _write(artifact / "launcher.stdout", "")
    launcher_stderr = _write(artifact / "launcher.stderr", "")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, launcher_stdout, launcher_stderr, stdout, stderr, run_exit, source_json, source_md, source_sha],
        relative_to=artifact,
    )

    return {
        "source_execution_artifact_dir": artifact,
        "source_execution_json": source_json,
        "source_execution_md": source_md,
        "source_execution_sha256s": source_sha,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "expected_record_count": 4,
        "expected_selection_log_count": 2,
        "enabled": True,
    }


def _source_execution_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_EXECUTION_STATUS,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "candidate_index_replay_execution_executed_by_this_gate": True,
        "outcome_acquisition_executed_by_this_gate": True,
        "candidate_closed_loop_outcome_records": 4,
        "missing_candidate_closed_loop_outcome_records": 0,
        "objective_required_records": 4,
        "paired_record_key_count": 4,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "schema_version": module.SOURCE_EXECUTION_SCHEMA,
        "final_decision": decision,
        "analysis": {
            "candidate_generation": False,
            "candidate_tensor_modification": False,
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
            "dp_modification": False,
            "training_execution": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "online_selector_change": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "strict_pairing_summary": {
            "objective_required_records": 4,
            "paired_record_key_count": 4,
            "candidate_closed_loop_outcome_records": 4,
            "missing_candidate_closed_loop_outcome_records": 0,
            "source_runtime_record_count": 4,
            "candidate_index_record_count": 4,
            "candidate_index_replay_payload_records": 4,
            "unpaired_source_record_key_count": 0,
            "unpaired_candidate_record_key_count": 0,
            "paired_record_key_sha256": "d" * 64,
            "actual_safetycost_v1_available": False,
            "actual_safetycost_v1_claim_rule_evaluable": False,
        },
        "candidate_index_outcome_summary": {
            "record_count": 4,
            "unique_record_key_count": 4,
            "duplicate_record_key_count": 0,
            "selection_log_count": 2,
            "validation_summary_count": 2,
            "candidate_closed_loop_outcome_records": 4,
            "missing_candidate_closed_loop_outcome_records": 0,
            "candidate_index_replay_payload_records": 4,
            "unique_candidate_tensor_hash_count": 4,
            "candidate_tensor_mutation_records": 0,
            "reference_blend_records": 0,
            "full36_path_records": 0,
            "formal_seed_records": 0,
            "closed_loop_training_or_online_input_records": 0,
            "non_affine_score_records": 0,
            "non_simplex_weight_records": 0,
        },
        "execution": {"attempted": True, "commands_executed": 2, "runbook_exit_code": 0},
        "no_go_report": {"failed_count": 0, "failures": []},
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write_sha256s(path: Path, paths: list[Path], *, relative_to: Path | None = None) -> Path:
    lines = []
    for item in paths:
        name = item.name if relative_to is None else item.relative_to(relative_to).as_posix()
        lines.append(f"{_sha256(item)}  {name}")
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
