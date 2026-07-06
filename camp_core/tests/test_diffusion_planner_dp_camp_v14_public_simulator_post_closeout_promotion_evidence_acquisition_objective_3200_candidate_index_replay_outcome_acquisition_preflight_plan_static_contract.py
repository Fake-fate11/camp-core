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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_contract.py"
)
PLAN_SCRIPT = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight.py"
)
PLAN_TEST = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan.py"
)
CURRENT_HEAD = "e" * 40
SOURCE_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_passed"] is True
    assert decision["objective_3200_candidate_index_replay_outcome_acquisition_preflight_authorized"] is True
    assert decision["candidate_index_replay_harness_execution_authorized"] is False
    assert decision["direct_candidate_index_replay_execution_authorized"] is False
    assert decision["direct_outcome_acquisition_execution_authorized"] is False
    assert decision["actual_safetycost_v1_available"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert decision["objective_required_records"] == module.OBJECTIVE_REQUIRED_RECORDS
    assert decision["candidate_closed_loop_outcome_records"] == 0
    assert decision["missing_candidate_closed_loop_outcome_records"] == module.OBJECTIVE_REQUIRED_RECORDS
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]
    assert (
        report["final_decision"]["failure_class"]
        == "explicit_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_authorization_missing"
    )


def test_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    fixture["preflight_plan_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "root_plan_md_sha" in report["final_decision"]["failed_checks"]
    assert "nested_plan_md_sha" in report["final_decision"]["failed_checks"]


def test_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_rejects_claim(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _fixture(tmp_path, module)
    plan = json.loads(fixture["preflight_plan_json"].read_text(encoding="utf-8"))
    plan["final_decision"]["camp_over_dp_top1_claim_authorized"] = True
    fixture["preflight_plan_json"].write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_plan_camp_over_dp_top1_claim_authorized" in report["final_decision"]["failed_checks"]


def _fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_PLAN_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_passed=True",
            "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    artifact = _write_source_plan_artifact(tmp_path, module)
    return {
        "preflight_plan_artifact_dir": artifact,
        "preflight_plan_json": artifact / "plan" / module.SOURCE_PLAN_JSON_NAME,
        "preflight_plan_md": artifact / "plan" / module.SOURCE_PLAN_MD_NAME,
        "preflight_plan_sha256s": artifact / "plan" / "SHA256SUMS",
        "plan_script_py": PLAN_SCRIPT,
        "plan_test_py": PLAN_TEST,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "review",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_source_plan_artifact(tmp_path: Path, module) -> Path:
    artifact = tmp_path / "source_plan"
    plan_dir = artifact / "plan"
    plan_json = _write_json(plan_dir / module.SOURCE_PLAN_JSON_NAME, _source_plan_report(module))
    plan_md = _write(plan_dir / module.SOURCE_PLAN_MD_NAME, "# plan\n")
    plan_sha = _write_sha256s(plan_dir / "SHA256SUMS", [plan_json, plan_md])
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
    command = _write(artifact / "COMMAND", "python plan.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, plan_json, plan_md, plan_sha],
        relative_to=artifact,
    )
    return artifact


def _source_plan_report(module) -> dict[str, Any]:
    plan_module = module.PLAN_MODULE
    decision = {
        "passed": True,
        "status": module.SOURCE_PLAN_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_ready": True,
        "objective_3200_candidate_index_replay_outcome_acquisition_preflight_plan_static_review_authorized": True,
        "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_closed_loop_outcome_records": 0,
        "missing_candidate_closed_loop_outcome_records": module.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_index_replay_harness_implemented": True,
        "candidate_index_replay_harness_execution_authorized": False,
        "direct_candidate_index_replay_execution_authorized": False,
        "direct_outcome_acquisition_execution_authorized": False,
        "actual_safetycost_v1_available": False,
        "actual_safetycost_v1_claim_rule_evaluable": False,
        "selector_promotion_authorized": False,
        "deployment_authorized": False,
        "online_selector_change_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }
    for flag in module.FALSE_EXECUTION_FLAGS:
        decision[flag] = False
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA,
        "analysis": {
            "read_only": True,
            "plan_only": True,
            "candidate_index_replay_outcome_acquisition_preflight_plan_only": True,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "source_static_review_summary": {
            "status": plan_module.SOURCE_REVIEW_STATUS,
            "objective_required_records": module.OBJECTIVE_REQUIRED_RECORDS,
            "candidate_closed_loop_outcome_records": 0,
            "missing_candidate_closed_loop_outcome_records": module.OBJECTIVE_REQUIRED_RECORDS,
        },
        "outcome_acquisition_preflight_plan": [
            {"name": name} for name in module.EXPECTED_PREFLIGHT_PLAN_ITEMS
        ],
        "strict_pairing_and_metrics_protocol": {
            "required_rows": module.OBJECTIVE_REQUIRED_RECORDS,
            "pass_fail_criteria": ["exactly_3200_strict_pairs"],
        },
        "artifact_contract": {
            "next_gate": module.AUTHORIZED_CURRENT_WORK,
            "preflight_execution_authorized_by_this_gate": False,
            "replay_execution_authorized_by_this_gate": False,
            "outcome_acquisition_authorized_by_this_gate": False,
        },
        "no_go_register": [{"name": name} for name in module.EXPECTED_NO_GO],
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
