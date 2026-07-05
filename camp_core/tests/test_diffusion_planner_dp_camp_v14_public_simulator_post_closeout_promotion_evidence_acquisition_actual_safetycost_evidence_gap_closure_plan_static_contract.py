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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure_plan_static_contract.py"
)
PLAN_SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure.py"
)
PLAN_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure_plan.py"
)
SOURCE_HEAD = "8" * 40
CURRENT_HEAD = "9" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_actual_safetycost_evidence_gap_closure_plan_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_actual_safetycost_evidence_gap_closure_plan_static_review_passes(
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
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_static_review_passed"
        ]
        is True
    )
    assert decision["actual_safetycost_outcome_materialization_preflight_plan_authorized"] is True
    assert decision["actual_safetycost_outcome_materialization_executed_by_this_gate"] is False
    assert decision["paired_evaluation_executed_by_this_gate"] is False
    assert decision["source_plan_consumed_by_this_gate"] is True
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert report["source_plan_summary"]["plan_check_count"] == 71
    assert report["source_plan_summary"]["required_input_count"] == 8
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_actual_safetycost_evidence_gap_closure_plan_static_review_requires_enable(
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
        == "explicit_actual_safetycost_evidence_gap_closure_plan_static_review_authorization_missing"
    )


def test_actual_safetycost_evidence_gap_closure_plan_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_actual_safetycost_evidence_gap_closure_plan_static_review_rejects_source_claim_leak(
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


def test_actual_safetycost_evidence_gap_closure_plan_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["actual_safetycost_evidence_gap_closure_plan_md"].write_text(
        "# drift\n",
        encoding="utf-8",
    )

    report = module.build_report(**fixture)

    assert "nested_plan_md_sha" in report["final_decision"]["failed_checks"]
    assert "root_plan_md_sha" in report["final_decision"]["failed_checks"]


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
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_ready=True",
            "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_static_review_authorized=True",
            "actual_safetycost_outcome_materialization_executed_by_current_gate=False",
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

    artifact = tmp_path / "source_plan_artifact"
    plan_dir = artifact / "plan"
    plan_json = _write_json(
        plan_dir / module.SOURCE_PLAN_JSON_NAME,
        _source_plan_report(module, source_decision_updates=source_decision_updates),
    )
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# plan\n")
    plan_sha = _write_sha256s(plan_dir / "SHA256SUMS", [plan_json, plan_md])
    _write(
        artifact / "HEADS",
        (
            f"CAMP_HEAD={SOURCE_HEAD}\n"
            f"CAMP_ORIGIN_MAIN={SOURCE_HEAD}\n"
            f"DP_HEAD={module.FIXED_DP_HEAD}\n"
        ),
    )
    _write(artifact / "COMMAND", "python plan.py\n")
    _write(artifact / "stdout", "{}\n")
    _write(artifact / "stderr", "")
    _write(artifact / "run.exit", "0\n")
    _write_root_sha256s(artifact, [plan_json, plan_md, plan_sha])

    return {
        "actual_safetycost_evidence_gap_closure_plan_artifact_dir": artifact,
        "actual_safetycost_evidence_gap_closure_plan_json": plan_json,
        "actual_safetycost_evidence_gap_closure_plan_md": plan_md,
        "actual_safetycost_evidence_gap_closure_plan_sha256s": plan_sha,
        "actual_safetycost_evidence_gap_closure_plan_script_py": PLAN_SCRIPT_PATH,
        "actual_safetycost_evidence_gap_closure_plan_test_py": PLAN_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
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
        "failed_checks": [],
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_ready": True,
        "post_closeout_promotion_evidence_acquisition_paired_evaluation_actual_safetycost_evidence_gap_closure_plan_static_review_authorized": True,
        "actual_safetycost_outcome_materialization_executed_by_this_gate": False,
        "paired_evaluation_executed_by_this_gate": False,
        "source_result_review_consumed_by_this_gate": True,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
    }
    decision.update({name: False for name in module.BLOCKED_ACTIONS})
    decision.update({name: False for name in module.FALSE_EXECUTION_FLAGS})
    if source_decision_updates:
        decision.update(source_decision_updates)
    plan_module = module.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "final_decision": decision,
        "plan_checks": [
            {"name": f"check_{index}", "passed": True, "actual": True, "expected": True}
            for index in range(71)
        ],
        "required_inputs": [
            {"name": name, "requirement": "fixture"}
            for name in plan_module.EXPECTED_REQUIRED_INPUTS
        ],
        "closure_plan": [
            {"name": name, "status": "plan_only", "materializes_outcomes": False}
            for name in plan_module.EXPECTED_PLAN_ITEMS
        ],
        "planned_outputs": [
            {"name": name, "status": "planned_not_materialized"}
            for name in plan_module.EXPECTED_PLANNED_OUTPUTS
        ],
        "no_go_register": [
            {"name": name, "status": "predeclared_reject_condition"}
            for name in plan_module.EXPECTED_NO_GO
        ],
        "source_result_review_summary": {
            "schema_version": plan_module.SOURCE_REVIEW_SCHEMA,
            "status": plan_module.SOURCE_REVIEW_STATUS,
            "passed": True,
            "authorized_next_work": plan_module.AUTHORIZED_CURRENT_WORK,
            "paired_record_count": 3200,
            "unique_paired_run_key_count": 3200,
            "shadow_diff_records": 2832,
            "candidate_tensor_mutation_records": 0,
            "selection_score_worse_records": 0,
            "no_go_failed_count": 0,
        },
        "evidence_gap_closure_summary": {
            "actual_safetycost_v1_available": False,
            "actual_safetycost_v1_claim_rule_evaluable": False,
            "next_evidence_need": "paired shadow-selected run-level closed-loop outcome summaries",
            "planned_resolution": "preflight a future artifact",
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, payload: Any) -> Path:
    return _write(path, json.dumps(payload, indent=2) + "\n")


def _write_sha256s(path: Path, paths: list[Path]) -> Path:
    return _write(path, "\n".join(f"{_sha256(item)}  {item.name}" for item in paths) + "\n")


def _write_root_sha256s(root: Path, plan_paths: list[Path]) -> Path:
    paths = [
        root / "HEADS",
        root / "COMMAND",
        root / "stdout",
        root / "stderr",
        root / "run.exit",
        *plan_paths,
    ]
    lines = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        lines.append(f"{_sha256(path)}  ./{rel}")
    return _write(root / "SHA256SUMS", "\n".join(lines) + "\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
