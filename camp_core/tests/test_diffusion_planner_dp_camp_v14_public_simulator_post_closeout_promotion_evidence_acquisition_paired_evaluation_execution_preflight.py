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
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution.py"
)
ARTIFACT_HEAD = "a" * 40
CURRENT_HEAD = "b" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_passes(
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
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_ready"
        ]
        is True
    )
    assert (
        decision[
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_static_review_authorized"
        ]
        is True
    )
    assert decision["paired_evaluation_executed_by_this_gate"] is False
    assert decision["paired_evaluation_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert [item["name"] for item in report["evidence_locks"]] == list(
        module.EXPECTED_EVIDENCE_LOCKS
    )
    assert [item["name"] for item in report["required_input_manifests"]] == list(
        module.EXPECTED_REQUIRED_INPUT_MANIFESTS
    )
    assert [item["name"] for item in report["preflight_plan"]] == list(
        module.EXPECTED_PREFLIGHT_ITEMS
    )
    assert {item["executes_paired_evaluation"] for item in report["preflight_plan"]} == {
        False
    }
    assert [item["name"] for item in report["future_outputs"]] == list(
        module.EXPECTED_FUTURE_OUTPUTS
    )
    assert report["runtime_result_summary"]["record_count"] == module.EXPECTED_RECORD_COUNT
    assert report["delta_review_summary"]["static_objective_delta_supported"] is True
    assert report["readiness_result_summary"]["direct_promotion_recommendation"] is False
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "execution_preflight_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_paired_evaluation_execution_preflight_authorization_missing"
    )


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_eof_authorizes_execution_preflight" in report[
        "final_decision"
    ]["failed_checks"]
    assert "status_doc_latest_eof_authorizes_execution_preflight" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"safety_benefit_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_review_decision_safety_benefit_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_rejects_runtime_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        runtime_decision_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "runtime_result_review_camp_claim_false" in report["final_decision"][
        "failed_checks"
    ]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_rejects_delta_claim_scope_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        delta_analysis_updates={"claim_scope": "CAMP is better than DP Top-1"},
    )

    report = module.build_report(**fixture)

    assert "delta_review_claim_scope" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["execution_plan_static_review_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "artifact_review_md_root_sha" in report["final_decision"]["failed_checks"]
    assert "source_review_md_nested_sha" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    runtime_decision_updates: dict[str, Any] | None = None,
    delta_analysis_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = tmp_path / "execution_plan_static_review_artifact"
    review_dir = artifact / "review"
    docs = tmp_path / "docs"
    current_next = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_REVIEW_STATUS}",
            f"next_work_target={current_next}",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_static_review_passed=True",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_authorized=True",
            "paired_evaluation_executed_by_current_gate=False",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    safety_score_doc = _write(
        docs / "dp_camp_safety_score_v1.md",
        "\n".join(
            [
                "SafetyCost_v1",
                "ci95_high(DeltaSafetyCost_v1) < 0",
                "hard_gate_passed == true",
                "no paired run uses seeds `11`, `12`, or `13`",
                "",
            ]
        ),
    )
    review_json = _write_json(
        review_dir / module.SOURCE_REVIEW_JSON_NAME,
        _source_review_payload(module, source_decision_updates=source_decision_updates),
    )
    review_md = _write(review_dir / module.SOURCE_REVIEW_MD_NAME, "# Review\n")
    review_sha256s = _write_sha256sums(review_dir / "SHA256SUMS", [review_json, review_md])
    command = _write(artifact / "COMMAND", "static review command\n")
    heads = _write(
        artifact / "HEADS",
        "\n".join(
            [
                f"CAMP_HEAD={ARTIFACT_HEAD}",
                f"CAMP_ORIGIN_MAIN={ARTIFACT_HEAD}",
                f"DP_HEAD={module.FIXED_DP_HEAD}",
                "",
            ]
        ),
    )
    stdout = _write(artifact / "stdout.txt", "ok\n")
    stderr = _write(artifact / "stderr.txt", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256sums(
        artifact / "SHA256SUMS",
        [command, heads, stdout, stderr, run_exit, review_json, review_md, review_sha256s],
        relative_to=artifact,
    )
    runtime_result_review = _write_json(
        tmp_path / "runtime_result_review.json",
        _runtime_result_review_payload(module, decision_updates=runtime_decision_updates),
    )
    shadow_delta_review = _write_json(
        tmp_path / "shadow_delta_review.json",
        _shadow_delta_review_payload(module, analysis_updates=delta_analysis_updates),
    )
    readiness_result_review = _write_json(
        tmp_path / "readiness_result_review.json",
        _readiness_result_review_payload(module),
    )
    return {
        "execution_plan_static_review_artifact_dir": artifact,
        "execution_plan_static_review_json": review_json,
        "execution_plan_static_review_md": review_md,
        "execution_plan_static_review_sha256s": review_sha256s,
        "runtime_result_review_json": runtime_result_review,
        "shadow_delta_review_json": shadow_delta_review,
        "readiness_result_review_json": readiness_result_review,
        "safety_score_doc": safety_score_doc,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_review_payload(
    module,
    *,
    source_decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.SOURCE_REVIEW_STATUS,
        "passed": True,
        "failure_class": None,
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_plan_static_review_passed": True,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_execution_preflight_authorized": True,
        "paired_evaluation_executed_by_this_gate": False,
        "previous_no_promotion_closeout_preserved": True,
        "direct_promotion_recommendation": False,
        "recommendation": "plan_paired_evaluation_execution_preflight_only",
        "score_expression": module.SCORE_EXPRESSION,
    }
    for action in module.BLOCKED_ACTIONS:
        decision[action] = False
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    if source_decision_updates:
        decision.update(source_decision_updates)
    analysis = {
        "current_camp_head": ARTIFACT_HEAD,
        "current_camp_origin_main": ARTIFACT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "paired_evaluation_execution": False,
        "score_expression": module.SCORE_EXPRESSION,
    }
    for flag in module.ANALYSIS_FALSE_FLAGS:
        analysis[flag] = False
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA,
        "analysis": analysis,
        "source_plan_summary": {
            "status": module.SOURCE_REVIEW_MODULE.SOURCE_PLAN_STATUS,
            "passed": True,
            "authorized_next_work": module.SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
            "plan_check_count": module.EXPECTED_SOURCE_PLAN_CHECK_COUNT,
            "failed_check_count": 0,
            "paired_evaluation_executed_by_this_gate": False,
        },
        "contract_summary": {
            "required_input_count": module.EXPECTED_SOURCE_REQUIRED_INPUT_COUNT,
            "execution_plan_count": module.EXPECTED_SOURCE_EXECUTION_PLAN_COUNT,
            "planned_output_count": module.EXPECTED_SOURCE_PLANNED_OUTPUT_COUNT,
            "no_go_count": module.EXPECTED_SOURCE_NO_GO_COUNT,
        },
        "review_checks": [{"name": f"check_{i}", "passed": True} for i in range(150)],
        "final_decision": decision,
    }


def _runtime_result_review_payload(
    module,
    *,
    decision_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = {
        "status": module.RUNTIME_RESULT_REVIEW_STATUS,
        "passed": True,
        "failed_checks": [],
        "failure_class": None,
        "executed_output_policy": "dp_top1",
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": module.SCORE_EXPRESSION,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": "runtime_result_review_v1",
        "heads": {
            "current_dp_head": module.FIXED_DP_HEAD,
            "artifact_dp_head": module.FIXED_DP_HEAD,
        },
        "analysis": {
            "result_review_only": True,
            "training_executed_by_review": False,
            "replay_executed_by_review": False,
            "candidate_generation_executed_by_review": False,
        },
        "records": {
            "record_count": module.EXPECTED_RECORD_COUNT,
            "executed_top1_records": module.EXPECTED_RECORD_COUNT,
            "default_off_selector_records": module.EXPECTED_RECORD_COUNT,
            "artifact_contract_ready_records": module.EXPECTED_RECORD_COUNT,
            "shadow_selected_index_differs_from_executed_index_records": module.EXPECTED_SHADOW_DIFF_RECORDS,
            "violation_counts": {"selected_executed_mismatch": 0},
        },
        "execution": {
            "selection_log_count": module.EXPECTED_SELECTION_LOG_COUNT,
            "formal_seed_path_count": 0,
        },
        "final_decision": decision,
    }


def _shadow_delta_review_payload(
    module,
    *,
    analysis_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    claim_scope = (
        "Supports static objective delta only; does not prove safety, closed-loop "
        "outcome, deployability, or CAMP superiority over DP Top-1."
    )
    analysis = {
        "claim_scope": claim_scope,
        "candidate_operation": "fixed DP candidate reranking only",
        "score_expression": module.SCORE_EXPRESSION,
    }
    if analysis_updates:
        analysis.update(analysis_updates)
    return {
        "schema_version": "shadow_delta_review_v1",
        "analysis": analysis,
        "records": {
            "record_count": module.EXPECTED_RECORD_COUNT,
            "selection_log_count": module.EXPECTED_SELECTION_LOG_COUNT,
            "shadow_selected_index_differs_from_executed_index_records": module.EXPECTED_SHADOW_DIFF_RECORDS,
            "formal_seed_path_count": 0,
            "candidate_operation_records": module.EXPECTED_RECORD_COUNT,
            "score_expression_records": module.EXPECTED_RECORD_COUNT,
        },
        "source_result_review": {
            "passed": True,
            "record_count": module.EXPECTED_RECORD_COUNT,
            "selection_log_count": module.EXPECTED_SELECTION_LOG_COUNT,
        },
        "final_decision": {
            "status": module.DELTA_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "failure_class": None,
            "static_objective_delta_supported": True,
            "replay_execution_authorized": False,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _readiness_result_review_payload(module) -> dict[str, Any]:
    return {
        "schema_version": "readiness_result_review_v1",
        "source_execution_summary": {
            "passed": True,
            "metrics_manifest_count": 6,
            "no_go_summary_count": module.EXPECTED_SOURCE_NO_GO_COUNT,
            "evidence_matrix_count": 6,
        },
        "source_static_review_summary": {"passed": True},
        "final_decision": {
            "status": module.READINESS_RESULT_REVIEW_STATUS,
            "passed": True,
            "failed_checks": [],
            "failure_class": None,
            "direct_promotion_recommendation": False,
            "followup_requires_explicit_user_decision": True,
            "evaluation_runbook_execution_authorized": False,
            "selector_promotion_authorized": False,
            "deployment_authorized": False,
            "safety_benefit_claim_authorized": False,
            "camp_over_dp_top1_claim_authorized": False,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_sha256sums(
    path: Path,
    files: list[Path],
    *,
    relative_to: Path | None = None,
) -> Path:
    lines = []
    for file in files:
        name = file.name if relative_to is None else file.relative_to(relative_to).as_posix()
        lines.append(f"{_sha256(file)}  {name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
