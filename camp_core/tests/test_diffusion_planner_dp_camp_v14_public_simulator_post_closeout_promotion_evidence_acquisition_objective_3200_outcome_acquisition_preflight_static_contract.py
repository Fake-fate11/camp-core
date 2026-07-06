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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_static_contract.py"
)
PREFLIGHT_SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition.py"
)
PREFLIGHT_TEST_PATH = (
    ROOT
    / "camp_core"
    / "tests"
    / "test_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight.py"
)
SOURCE_HEAD = "d" * 40
CURRENT_HEAD = "e" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_post_closeout_promotion_evidence_acquisition_objective_3200_outcome_acquisition_preflight_static_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_objective_3200_outcome_acquisition_preflight_static_review_passes(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    summary = report["source_preflight_summary"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["objective_3200_outcome_acquisition_preflight_static_review_passed"] is True
    assert decision["objective_3200_outcome_acquisition_execution_authorized"] is True
    assert decision["direct_acquisition_execution_authorized"] is False
    assert decision["direct_replay_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert decision["safety_benefit_claim_authorized"] is False
    assert decision["camp_over_dp_top1_claim_authorized"] is False
    assert summary["objective_required_records"] == 3200
    assert summary["runtime_record_count"] == 3200
    assert summary["candidate_closed_loop_outcome_records"] == 0
    assert summary["missing_candidate_closed_loop_outcome_records"] == 3200
    assert summary["preflight_item_count"] == module.EXPECTED_PREFLIGHT_ITEM_COUNT
    assert summary["planned_output_count"] == module.EXPECTED_PLANNED_OUTPUT_COUNT
    assert summary["no_go_count"] == module.EXPECTED_NO_GO_COUNT
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_objective_3200_outcome_acquisition_preflight_static_review_requires_enable(
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
        == "explicit_objective_3200_outcome_acquisition_preflight_static_review_authorization_missing"
    )


def test_objective_3200_outcome_acquisition_preflight_static_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_objective_3200_outcome_acquisition_preflight_static_review_rejects_claim_leak(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"camp_over_dp_top1_claim_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_preflight_camp_over_dp_top1_claim_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["camp_over_dp_top1_claim_authorized"] is False


def test_objective_3200_outcome_acquisition_preflight_static_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["outcome_acquisition_preflight_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "root_preflight_md_sha" in report["final_decision"]["failed_checks"]
    assert "nested_preflight_md_sha" in report["final_decision"]["failed_checks"]


def test_objective_3200_outcome_acquisition_preflight_static_review_rejects_direct_execution(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"direct_acquisition_execution_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "source_preflight_direct_acquisition_execution_authorized" in report[
        "final_decision"
    ]["failed_checks"]
    assert report["final_decision"]["direct_acquisition_execution_authorized"] is False


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
            f"current_v14_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_outcome_acquisition_preflight_ready=True",
            "objective_3200_outcome_acquisition_preflight_static_review_authorized=True",
            "selector_promotion_authorized=False",
            "deployment_authorized=False",
            "safety_benefit_claim_authorized=False",
            "camp_over_dp_top1_claim_authorized=False",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    artifact = tmp_path / "source_preflight_artifact"
    preflight_dir = artifact / "preflight"
    preflight_json = _write_json(
        preflight_dir / module.SOURCE_PREFLIGHT_JSON_NAME,
        _source_preflight_report(module, source_decision_updates=source_decision_updates),
    )
    preflight_md = _write(preflight_dir / module.SOURCE_PREFLIGHT_MD_NAME, "# preflight\n")
    preflight_sha = _write_sha256s(preflight_dir / "SHA256SUMS", [preflight_json, preflight_md])
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
    command = _write(artifact / "COMMAND", "python preflight.py\n")
    stdout = _write(artifact / "stdout", "{}\n")
    stderr = _write(artifact / "stderr", "")
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, preflight_json, preflight_md, preflight_sha],
        relative_to=artifact,
    )

    return {
        "outcome_acquisition_preflight_artifact_dir": artifact,
        "outcome_acquisition_preflight_json": preflight_json,
        "outcome_acquisition_preflight_md": preflight_md,
        "outcome_acquisition_preflight_sha256s": preflight_sha,
        "outcome_acquisition_preflight_script_py": PREFLIGHT_SCRIPT_PATH,
        "outcome_acquisition_preflight_test_py": PREFLIGHT_TEST_PATH,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_preflight_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_PREFLIGHT_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_outcome_acquisition_preflight_ready": True,
        "objective_3200_outcome_acquisition_preflight_static_review_authorized": True,
        "objective_required_records": module.PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS,
        "runtime_record_count": module.PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS,
        "candidate_closed_loop_outcome_records": 0,
        "missing_candidate_closed_loop_outcome_records": module.PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS,
        "requires_acquisition_execution": True,
        "direct_acquisition_execution_authorized": False,
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
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA,
        "analysis": {
            "read_only": True,
            "objective_3200_outcome_acquisition_preflight_only": True,
            "outcome_acquisition_execution": False,
            "closed_loop_replay_execution": False,
            "training_execution": False,
            "candidate_generation": False,
            "dp_modification": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "objective_3200_summary": {
            "objective_required_records": module.PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS,
            "runtime_record_count": module.PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS,
            "candidate_closed_loop_outcome_records": 0,
            "missing_candidate_closed_loop_outcome_records": module.PREFLIGHT_MODULE.OBJECTIVE_REQUIRED_RECORDS,
            "requires_acquisition_execution": True,
        },
        "future_acquisition_execution_contract": {
            "future_execution_authorized_by_this_gate": False,
            "future_execution_requires_static_review": True,
            "candidate_source": "fixed_dp_candidate_tensor_only",
            "camp_action": "read_shadow_selected_index_and_select_existing_candidate_only",
        },
        "preflight_items": [{"item": item} for item in module.PREFLIGHT_MODULE.EXPECTED_PREFLIGHT_ITEMS],
        "planned_outputs": list(module.PREFLIGHT_MODULE.EXPECTED_PLANNED_OUTPUTS),
        "no_go_register": list(module.PREFLIGHT_MODULE.PREFLIGHT_NO_GO),
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
