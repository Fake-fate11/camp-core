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
    / "review_diffusion_planner_dp_camp_v14_public_simulator_post_closeout_promotion_evidence_acquisition_objective_3200_candidate_index_actual_safetycost_online_selector_activation_execution_result.py"
)
SOURCE_HEAD = "e" * 40
CURRENT_HEAD = "f" * 40


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "v14_candidate_index_actual_safetycost_online_selector_activation_execution_result_review",
        SCRIPT_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_candidate_index_actual_safetycost_online_selector_activation_execution_result_review_passes(
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
    assert decision["online_selector_activation_execution_reviewed_by_this_gate"] is True
    assert decision["online_selector_activation_execution_executed_by_review"] is False
    assert decision["dp_modification"] is False
    assert decision["closed_loop_outcomes_used_for_online_selector"] is False
    assert report["reviewed_activation_state"]["online_selector_enabled"] is True
    assert report["reviewed_online_runtime_manifest"]["executed_output_policy"] == module.EXECUTED_OUTPUT_POLICY
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_candidate_index_actual_safetycost_online_selector_activation_execution_result_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]


def test_candidate_index_actual_safetycost_online_selector_activation_execution_result_review_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert "audit_latest_next_work" in report["final_decision"]["failed_checks"]
    assert "status_doc_latest_next_work" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "v14_eof_contract_mismatch"


def test_candidate_index_actual_safetycost_online_selector_activation_execution_result_review_rejects_source_gap(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_decision_updates={"online_selector_activation_execution": False},
    )

    report = module.build_report(**fixture)

    assert "source_online_selector_activation_execution" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_online_selector_activation_execution_contract_failure"


def test_candidate_index_actual_safetycost_online_selector_activation_execution_result_review_rejects_activation_state_gap(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        activation_updates={"candidate_tensor_mutation_authorized": True},
    )

    report = module.build_report(**fixture)

    assert "activation_state_candidate_mutation_false" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "online_selector_activation_runtime_contract_failure"


def test_candidate_index_actual_safetycost_online_selector_activation_execution_result_review_rejects_hash_drift(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_execution_sha256s"].write_text("0" * 64 + f"  {module.SOURCE_EXECUTION_JSON_NAME}\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert "nested_execution_json_sha" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["failure_class"] == "source_artifact_hash_mismatch"


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_decision_updates: dict[str, Any] | None = None,
    activation_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v14_status={module.SOURCE_EXECUTION_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "objective_3200_candidate_index_actual_safetycost_online_selector_activation_result_review_authorized=True",
            "",
        ]
    )
    v14_audit = _write(docs / "diffusion_planner_v14_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source = _write_source_execution_artifact(
        tmp_path / "source_execution_artifact",
        module,
        source_decision_updates=source_decision_updates,
        activation_updates=activation_updates,
    )
    return {
        "source_execution_artifact_dir": source["artifact"],
        "source_execution_json": source["json"],
        "source_execution_md": source["md"],
        "source_activation_state_json": source["activation"],
        "source_online_runtime_manifest_json": source["manifest"],
        "source_execution_sha256s": source["sha256s"],
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_source_execution_artifact(
    artifact: Path,
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
    activation_updates: dict[str, Any] | None,
) -> dict[str, Path]:
    execution_dir = artifact / "execution"
    activation = _activation_state(module, activation_updates=activation_updates)
    manifest = _online_manifest(module, activation)
    execution_json = _write_json(execution_dir / module.SOURCE_EXECUTION_JSON_NAME, _source_execution_report(module, source_decision_updates=source_decision_updates))
    execution_md = _write(execution_dir / module.SOURCE_EXECUTION_MD_NAME, "# source execution\n")
    activation_json = _write_json(execution_dir / module.SOURCE_ACTIVATION_STATE_JSON_NAME, activation)
    manifest_json = _write_json(execution_dir / module.SOURCE_ONLINE_RUNTIME_MANIFEST_JSON_NAME, manifest)
    execution_sha = _write_sha256s(
        execution_dir / "SHA256SUMS",
        [execution_json, execution_md, activation_json, manifest_json],
    )
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
    run_exit = _write(artifact / "run.exit", "0\n")
    _write_sha256s(
        artifact / "SHA256SUMS",
        [heads, command, stdout, stderr, run_exit, execution_json, execution_md, activation_json, manifest_json, execution_sha],
        relative_to=artifact,
    )
    return {
        "artifact": artifact,
        "json": execution_json,
        "md": execution_md,
        "activation": activation_json,
        "manifest": manifest_json,
        "sha256s": execution_sha,
    }


def _source_execution_report(
    module,
    *,
    source_decision_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    decision = {
        "passed": True,
        "status": module.SOURCE_EXECUTION_STATUS,
        "failure_class": None,
        "failed_checks": [],
        "check_count": module.SOURCE_EXECUTION_CHECK_COUNT,
        "failed_check_count": 0,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "objective_3200_candidate_index_actual_safetycost_online_selector_activation_result_review_authorized": True,
        "source_static_review_passed": True,
        "online_selector_activation_execution": True,
        "online_selector_change_authorized": True,
        "dp_modification": False,
        "candidate_generation": False,
        "training_execution": False,
        "closed_loop_outcomes_used_for_training": False,
        "closed_loop_outcomes_used_for_online_selector": False,
    }
    if source_decision_updates:
        decision.update(source_decision_updates)
    return {
        "schema_version": module.SOURCE_EXECUTION_SCHEMA,
        "analysis": {
            "online_selector_activation_execution": decision["online_selector_activation_execution"],
            "selection_effect": True,
            "online_selector_change": True,
            "deployment_execution": False,
            "dp_modification": False,
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "final_decision": decision,
    }


def _activation_state(
    module,
    *,
    activation_updates: dict[str, Any] | None,
) -> dict[str, Any]:
    activation = {
        "schema_version": module.SOURCE_EXECUTION_SCHEMA,
        "online_selector_enabled": True,
        "runtime_switch_state": "online_enabled",
        "source_scope": module.SOURCE_SCOPE,
        "candidate_operation": "fixed DP candidate reranking only",
        "required_candidate_count": module.EXPECTED_CANDIDATE_COUNT,
        "score_expression": module.SCORE_EXPRESSION,
        "required_dp_head": module.FIXED_DP_HEAD,
        "fail_closed_fallback_policy": "dp_top1",
        "executed_output_policy": module.EXECUTED_OUTPUT_POLICY,
        "dp_modification_authorized": False,
        "candidate_tensor_mutation_authorized": False,
        "trajectory_generation_authorized": False,
        "trajectory_rewrite_authorized": False,
        "reference_blend_authorized": False,
        "guidance_authorized": False,
        "postselection_authorized": False,
        "closed_loop_outcomes_used_for_training": False,
        "closed_loop_outcomes_used_for_online_selector": False,
    }
    if activation_updates:
        activation.update(activation_updates)
    return activation


def _online_manifest(module, activation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": module.EXECUTION_MODULE.ONLINE_RUNTIME_MANIFEST_SCHEMA_VERSION,
        "source_scope": module.SOURCE_SCOPE,
        "default_off": False,
        "fail_closed": True,
        "selection_effect": True,
        "online_selector_change": True,
        "executed_output_policy": module.EXECUTED_OUTPUT_POLICY,
        "required_candidate_count": module.EXPECTED_CANDIDATE_COUNT,
        "score_expression": module.SCORE_EXPRESSION,
        "required_dp_head": module.FIXED_DP_HEAD,
        "activation_state": activation,
        "authorizations": {
            "online_selector_change_authorized": True,
            "selector_promotion_authorized": True,
            "deployment_authorized": True,
            "dp_modification_authorized": False,
            "candidate_generation_authorized": False,
            "training_execution_authorized": False,
            "closed_loop_outcomes_used_for_training": False,
            "closed_loop_outcomes_used_for_online_selector": False,
        },
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
