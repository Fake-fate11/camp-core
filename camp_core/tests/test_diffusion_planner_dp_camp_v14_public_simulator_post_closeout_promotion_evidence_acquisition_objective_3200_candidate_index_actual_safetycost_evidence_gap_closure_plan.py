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
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_evidence_gap_closure.py"
)
SOURCE_HEAD = "c" * 40
CURRENT_HEAD = "d" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_evidence_gap_closure_plan",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_actual_safetycost_evidence_gap_closure_plan_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert (
        decision[
            "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_ready"
        ]
        is True
    )
    assert (
        decision[
            "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_static_review_authorized"
        ]
        is True
    )
    assert decision["source_result_review_consumed_by_this_gate"] is True
    assert decision["actual_safetycost_delta_materialization_executed_by_this_gate"] is False
    assert decision["candidate_index_replay_executed_by_this_gate"] is False
    assert decision["outcome_acquisition_executed_by_this_gate"] is False
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["actual_safetycost_v1_claim_rule_evaluable"] is False
    assert decision["candidate_closed_loop_outcome_records"] == 4
    assert decision["missing_candidate_closed_loop_outcome_records"] == 0
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert [item["name"] for item in report["required_inputs"]] == list(
        module.EXPECTED_REQUIRED_INPUTS
    )
    assert [item["name"] for item in report["closure_plan"]] == list(
        module.EXPECTED_PLAN_ITEMS
    )
    assert {item["materializes_safetycost_deltas"] for item in report["closure_plan"]} == {False}
    assert [item["name"] for item in report["planned_outputs"]] == list(
        module.EXPECTED_PLANNED_OUTPUTS
    )
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_actual_safetycost_evidence_gap_closure_plan_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "candidate_index_actual_safetycost_evidence_gap_closure_plan_enabled" in report[
        "final_decision"
    ]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_actual_safetycost_evidence_gap_closure_plan_authorization_missing"
    )


def test_candidate_index_actual_safetycost_evidence_gap_closure_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_actual_safetycost_evidence_gap_closure_plan_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_result_review_decision_camp_over_dp_top1_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_candidate_index_actual_safetycost_evidence_gap_closure_plan_rejects_missing_outcomes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        summary_updates={
            "candidate_closed_loop_outcome_records": 3,
            "missing_candidate_closed_loop_outcome_records": 1,
        },
    )

    report = module.build_report(**fixture)

    failed = report["final_decision"]["failed_checks"]
    assert "source_candidate_closed_loop_outcome_records" in failed
    assert "source_missing_candidate_closed_loop_outcome_records" in failed
    assert (
        report["final_decision"]["failure_class"]
        == "source_candidate_index_evidence_gap_contract_failure"
    )


def test_candidate_index_actual_safetycost_evidence_gap_closure_plan_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_result_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "nested_result_review_md_sha" in report["final_decision"]["failed_checks"]
    assert "root_result_review_md_sha" in report["final_decision"]["failed_checks"]


def test_candidate_index_actual_safetycost_evidence_gap_closure_plan_accepts_root_without_nested_sha_entry(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, include_nested_sha_in_root=False)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is True
    assert (
        "root_result_review_sha256s_sha_optional"
        not in report["final_decision"]["failed_checks"]
    )


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    summary_updates: dict[str, Any] | None = None,
    include_nested_sha_in_root: bool = True,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_replay_outcome_acquisition_execution_result_review_passed=True",
            "objective_3200_candidate_index_actual_safetycost_evidence_gap_closure_plan_authorized=True",
            "actual_safetycost_v1_available=False",
            "actual_safetycost_v1_claim_rule_evaluable=False",
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

    artifact = tmp_path / "source_result_review_artifact"
    report_dir = artifact / "report"
    source_json = _write_json(
        report_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_result_review_report(
            module,
            source_decision_updates=source_decision_updates,
            summary_updates=summary_updates,
        ),
    )
    source_md = _write(report_dir / module.SOURCE_REVIEW_MD_NAME, "# result review\n")
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
    command = _write(artifact / "COMMAND", "python review.py\n")
    launcher_stdout = _write(artifact / "launcher.stdout", "")
    launcher_stderr = _write(artifact / "launcher.stderr", "")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    root_paths = [
        heads,
        command,
        launcher_stdout,
        launcher_stderr,
        stdout,
        stderr,
        run_exit,
        source_json,
        source_md,
    ]
    if include_nested_sha_in_root:
        root_paths.append(source_sha)
    _write_sha256s(artifact / "SHA256SUMS", root_paths, relative_to=artifact)

    return {
        "source_result_review_artifact_dir": artifact,
        "source_result_review_json": source_json,
        "source_result_review_md": source_md,
        "source_result_review_sha256s": source_sha,
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


def _source_result_review_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
    summary_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_REVIEW_STATUS,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "candidate_index_execution_reviewed_by_this_gate": True,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "actual_safetycost_evidence_gap_closure_plan_authorized": True,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    if source_decision_updates:
        decision.update(source_decision_updates)

    summary = {
        "objective_required_records": 4,
        "paired_record_key_count": 4,
        "candidate_closed_loop_outcome_records": 4,
        "missing_candidate_closed_loop_outcome_records": 0,
        "source_runtime_record_count": 4,
        "candidate_index_record_count": 4,
        "candidate_index_replay_payload_records": 4,
        "selection_log_count": 2,
        "no_go_failed_count": 0,
        "candidate_tensor_mutation_records": 0,
        "reference_blend_records": 0,
        "full36_path_records": 0,
        "formal_seed_records": 0,
        "closed_loop_training_or_online_input_records": 0,
        "non_affine_score_records": 0,
        "non_simplex_weight_records": 0,
    }
    if summary_updates:
        summary.update(summary_updates)

    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": {
            "result_review_only": True,
            "candidate_index_replay_executed_by_review": False,
            "outcome_acquisition_executed_by_review": False,
            "training_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
            "dp_modified_by_review": False,
            "promotion_executed_by_review": False,
            "deployment_executed_by_review": False,
            "online_selector_change_by_review": False,
            "safety_or_camp_over_dp_claim_by_review": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "source_execution_summary": summary,
        "evidence_gap_summary": {
            "actual_safetycost_v1_available": False,
            "actual_safetycost_v1_claim_rule_evaluable": False,
            "next_evidence_need": "materialize SafetyCost_v1 deltas from paired candidate-index closed-loop outcomes",
            "claim_supported_by_this_review": False,
            "promotion_supported_by_this_review": False,
        },
        "final_decision": decision,
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
