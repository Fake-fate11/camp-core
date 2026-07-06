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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result.py"
)
SOURCE_HEAD = "c" * 40
CURRENT_HEAD = "d" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_execution_result_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_actual_safetycost_delta_materialization_execution_result_review_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    summary = report["source_execution_summary"]
    claim = report["actual_safetycost_claim_rule_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.CLAIM_AUTHORIZATION_BOUNDARY_PLAN_WORK
    assert decision["candidate_index_actual_safetycost_delta_materialization_execution_reviewed_by_this_gate"] is True
    assert decision["actual_safetycost_delta_materialization_executed_by_this_gate"] is False
    assert decision["safety_benefit_claim_supported"] is True
    assert decision["camp_over_dp_top1_claim_supported"] is True
    assert decision["claim_authorization_boundary_plan_authorized"] is True
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert summary["paired_safetycost_v1_row_count"] == 4
    assert claim["claim_rule_passed"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_actual_safetycost_delta_materialization_execution_result_review_requires_enable(
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
        == "explicit_candidate_index_actual_safetycost_result_review_authorization_missing"
    )


def test_candidate_index_actual_safetycost_delta_materialization_execution_result_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_actual_safetycost_delta_materialization_execution_result_review_rejects_source_claim_leak(
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
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_candidate_index_actual_safetycost_delta_materialization_execution_result_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_execution_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "nested_execution_md_sha" in report["final_decision"]["failed_checks"]
    assert "root_report_md_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_hash_mismatch"


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
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_passed=True",
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_execution_result_review_authorized=True",
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

    source_artifact = _write_source_execution_artifact(
        tmp_path / "source_execution_artifact",
        module,
        source_decision_updates=source_decision_updates,
    )
    return {
        "source_execution_artifact_dir": source_artifact["artifact"],
        "source_execution_json": source_artifact["json"],
        "source_execution_md": source_artifact["md"],
        "source_execution_delta_jsonl": source_artifact["jsonl"],
        "source_execution_sha256s": source_artifact["sha256s"],
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


def _write_source_execution_artifact(
    artifact: Path,
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Path]:
    report_dir = artifact / "report"
    source_json = _write_json(
        report_dir / module.SOURCE_EXECUTION_JSON_NAME,
        _source_execution_report(module, source_decision_updates=source_decision_updates),
    )
    source_md = _write(report_dir / module.SOURCE_EXECUTION_MD_NAME, "# source execution\n")
    source_jsonl = _write(report_dir / module.SOURCE_DELTA_TABLE_JSONL_NAME, "{}\n{}\n{}\n{}\n")
    source_sha = _write_sha256s(report_dir / "SHA256SUMS", [source_json, source_md, source_jsonl])
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
    command = _write(artifact / "COMMAND", "python execute_delta.py\n")
    launcher_stdout = _write(artifact / "launcher.stdout", "")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, launcher_stdout, stdout, stderr, run_exit, source_json, source_md, source_jsonl, source_sha],
        relative_to=artifact,
    )
    return {
        "artifact": artifact,
        "json": source_json,
        "md": source_md,
        "jsonl": source_jsonl,
        "sha256s": source_sha,
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
        "actual_safetycost_delta_materialization_executed_by_this_gate": True,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "paired_safetycost_v1_row_count": 4,
        "same_as_top1_records": 1,
        "non_top1_shadow_selected_records": 3,
        "delta_better_records": 2,
        "delta_tie_records": 1,
        "delta_worse_records": 1,
        "actual_safetycost_v1_available": True,
        "actual_safetycost_v1_claim_rule_evaluable": True,
        "claim_rule_evaluable": True,
        "claim_rule_passed": True,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    if source_decision_updates:
        decision.update(source_decision_updates)
    delta_summary = {
        "count": 4,
        "mean": -0.5,
        "median": -0.5,
        "min": -2.0,
        "max": 1.0,
        "better_records": 2,
        "tie_records": 1,
        "worse_records": 1,
    }
    no_go = {"failed_count": 0, "failures": []}
    return {
        "schema_version": module.SOURCE_EXECUTION_SCHEMA,
        "analysis": {
            "candidate_generation": False,
            "candidate_tensor_modification": False,
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
            "deployment_executed": False,
            "dp_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": module.SCORE_EXPRESSION,
            "training_execution": False,
        },
        "delta_materialization_summary": {
            "record_count": 4,
            "selection_log_count": 2,
            "paired_safetycost_v1_row_count": 4,
            "actual_safetycost_v1_available": True,
            "actual_safetycost_v1_claim_rule_evaluable": True,
            "no_go_report": no_go,
            "delta_summary": delta_summary,
            "delta_bootstrap_ci95": {
                "mean": -0.5,
                "ci95_low": -0.9,
                "ci95_high": -0.1,
                "resamples": 10000,
            },
            "claim_rule": {
                "evaluable": True,
                "passed": True,
                "safety_benefit_claim_authorized": False,
                "camp_over_dp_top1_claim_authorized": False,
            },
        },
        "no_go_report": no_go,
        "final_decision": decision,
    }


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_sha256s(path: Path, files: list[Path], *, relative_to: Path | None = None) -> Path:
    lines = []
    for file in files:
        name = file.relative_to(relative_to).as_posix() if relative_to else file.name
        lines.append(f"{_sha256(file)}  {name}")
    return _write(path, "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
