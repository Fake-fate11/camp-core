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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_contract.py"
)
PLAN_SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight.py"
)
PLAN_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan.py"
)
SOURCE_HEAD = "3" * 40
CURRENT_HEAD = "4" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    summary = report["source_plan_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert (
        decision[
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_passed"
        ]
        is True
    )
    assert (
        decision[
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_authorized"
        ]
        is True
    )
    assert decision["actual_safetycost_delta_materialization_executed_by_this_gate"] is False
    assert decision["candidate_index_replay_executed_by_this_gate"] is False
    assert decision["outcome_acquisition_executed_by_this_gate"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert summary["plan_check_count"] == 66
    assert summary["required_input_count"] == 10
    assert summary["candidate_closed_loop_outcome_records"] == 4
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_delta_preflight_plan_static_review_authorization_missing"
    )


def test_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_rejects_source_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"safety_benefit_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_plan_decision_safety_benefit_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["safety_benefit_claim_authorized"] is False


def test_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["delta_materialization_preflight_plan_md"].write_text(
        "# drift\n",
        encoding="utf-8",
    )

    report = module.build_report(**fixture)

    assert "nested_plan_md_sha" in report["final_decision"]["failed_checks"]
    assert "root_plan_md_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "artifact_hash_contract_failure"


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
            f"current_v14_status={module.SOURCE_PLAN_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_ready=True",
            "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_authorized=True",
            "actual_safetycost_delta_materialization_executed_by_current_gate=False",
            "candidate_index_replay_executed_by_current_gate=False",
            "outcome_acquisition_executed_by_current_gate=False",
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

    artifact = tmp_path / "source_plan_artifact"
    plan_dir = artifact / "plan"
    plan_json = _write_json(
        plan_dir / module.SOURCE_PLAN_JSON_NAME,
        _source_plan_report(module, source_decision_updates=source_decision_updates),
    )
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# plan\n")
    plan_sha = _write_sha256s(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    heads = _write(
        artifact / "HEADS",
        (
            f"CAMP_HEAD={SOURCE_HEAD}\n"
            f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}\n"
            f"DP_HEAD={module.FIXED_DP_HEAD}\n"
        ),
    )
    command = _write(artifact / "COMMAND", "python plan.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, plan_json, plan_md, plan_sha],
        relative_to=artifact,
    )

    return {
        "delta_materialization_preflight_plan_artifact_dir": artifact,
        "delta_materialization_preflight_plan_json": plan_json,
        "delta_materialization_preflight_plan_md": plan_md,
        "delta_materialization_preflight_plan_sha256s": plan_sha,
        "delta_materialization_preflight_plan_script_py": PLAN_SCRIPT_PATH,
        "delta_materialization_preflight_plan_test_py": PLAN_TEST_PATH,
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


def _source_plan_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_PLAN_STATUS,
        "failure_class": None,
        "failed_checks": [],
        "check_count": 66,
        "failed_check_count": 0,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_ready": True,
        "objective_3200_candidate_index_actual_safetycost_delta_materialization_preflight_plan_static_review_authorized": True,
        "actual_safetycost_delta_materialization_executed_by_this_gate": False,
        "candidate_index_replay_executed_by_this_gate": False,
        "outcome_acquisition_executed_by_this_gate": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    if source_decision_updates:
        decision.update(source_decision_updates)

    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "plan_only": True,
            "read_only": True,
            "candidate_index_actual_safetycost_delta_materialization_preflight_plan_only": True,
            "actual_safetycost_delta_materialization_executed": False,
            "candidate_index_replay_execution": False,
            "outcome_acquisition_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "candidate_tensor_modification": False,
            "online_selector_change": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "safety_or_camp_over_dp_claim": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "source_static_review_summary": {
            "objective_required_records": 4,
            "paired_record_key_count": 4,
            "candidate_closed_loop_outcome_records": 4,
            "missing_candidate_closed_loop_outcome_records": 0,
            "selection_log_count": 2,
            "no_go_failed_count": 0,
        },
        "delta_materialization_preflight_summary": {
            "actual_safetycost_v1_available": False,
            "actual_safetycost_v1_claim_rule_evaluable": False,
            "next_evidence_need": "materialize SafetyCost_v1 deltas from paired candidate-index closed-loop outcomes",
            "delta_materialization_executed_by_this_gate": False,
            "claim_supported_by_this_plan": False,
            "promotion_supported_by_this_plan": False,
        },
        "required_inputs": [{"name": name} for name in module.PLAN_MODULE.EXPECTED_REQUIRED_INPUTS],
        "preflight_plan": [
            {"name": name, "materializes_safetycost_deltas": False}
            for name in module.PLAN_MODULE.EXPECTED_PREFLIGHT_ITEMS
        ],
        "planned_outputs": [{"name": name} for name in module.PLAN_MODULE.EXPECTED_PLANNED_OUTPUTS],
        "no_go_register": [{"name": name} for name in module.PLAN_MODULE.EXPECTED_NO_GO],
        "plan_checks": [{"name": f"check_{idx}", "passed": True} for idx in range(66)],
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
