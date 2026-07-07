from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_offline_training_execution_result.py"
)
HEAD = "76924a8e4d957d4fb119252aae8d8d621cd02c2d"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_offline_training_execution_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_offline_training_execution_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["reviewed_offline_training_execution"] is True
    assert decision["source_training_executed"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v15_offline_training_execution_result_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_offline_training_execution_result_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_review" in report["final_decision"]["failed_checks"]


def test_v15_offline_training_execution_result_review_rejects_missing_training(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, decision_updates={"training_executed": False})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_training_executed" in report["final_decision"]["failed_checks"]


def test_v15_offline_training_execution_result_review_rejects_performance_claim(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, decision_updates={"performance_claimed": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_performance_not_claimed" in report["final_decision"]["failed_checks"]


def test_v15_offline_training_execution_result_review_is_latest_status() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v15_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status_text = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    assert f"current_v15_status={module.READY_STATUS}" in audit_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit_text
    assert f"current_v15_status={module.READY_STATUS}" in status_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status_text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    decision_updates: dict | None = None,
) -> dict:
    execution = module.EXECUTION_MODULE
    artifact = tmp_path / "source_execution"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")

    config = _config_payload(execution)
    model = _model_payload(execution)
    _write_json(artifact / execution.CONFIG_JSON_NAME, config)
    _write_json(artifact / execution.MODEL_JSON_NAME, model)
    (artifact / execution.LOG_NAME).write_text("offline training log\n", encoding="utf-8")
    model_manifest = {
        "schema_version": "dp_camp_v15_offline_training_model_manifest_v1",
        "model_sha256": _sha256(artifact / execution.MODEL_JSON_NAME),
        "config_sha256": _sha256(artifact / execution.CONFIG_JSON_NAME),
        "log_sha256": _sha256(artifact / execution.LOG_NAME),
    }
    _write_json(artifact / execution.MODEL_MANIFEST_JSON_NAME, model_manifest)
    timing = _timing_payload(execution, artifact)
    manifest = _manifest_payload(execution, artifact)
    _write_json(artifact / execution.TIMING_JSON_NAME, timing)
    (artifact / execution.TIMING_MD_NAME).write_text("# Timing\n", encoding="utf-8")
    _write_json(artifact / execution.MANIFEST_JSON_NAME, manifest)
    execution_json = artifact / execution.EXECUTION_JSON_NAME
    execution_md = artifact / execution.EXECUTION_MD_NAME
    _write_json(
        execution_json,
        _execution_payload(module, timing, decision_updates=decision_updates),
    )
    execution_md.write_text("# Offline Training Execution\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run offline training execution\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")
    sha_path = artifact / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(
            f"{_sha256(artifact / name)}  {name}"
            for name in (
                "HEADS",
                "COMMAND",
                "stdout.txt",
                "stderr.txt",
                "run.exit",
                execution.EXECUTION_JSON_NAME,
                execution.EXECUTION_MD_NAME,
                execution.MANIFEST_JSON_NAME,
                execution.MODEL_MANIFEST_JSON_NAME,
                execution.MODEL_JSON_NAME,
                execution.CONFIG_JSON_NAME,
                execution.TIMING_JSON_NAME,
                execution.TIMING_MD_NAME,
                execution.LOG_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_execution_artifact_dir": artifact,
        "source_execution_json": execution_json,
        "source_execution_md": execution_md,
        "source_manifest_json": artifact / execution.MANIFEST_JSON_NAME,
        "source_model_manifest_json": artifact / execution.MODEL_MANIFEST_JSON_NAME,
        "source_model_json": artifact / execution.MODEL_JSON_NAME,
        "source_config_json": artifact / execution.CONFIG_JSON_NAME,
        "source_timing_json": artifact / execution.TIMING_JSON_NAME,
        "source_timing_md": artifact / execution.TIMING_MD_NAME,
        "source_log": artifact / execution.LOG_NAME,
        "source_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _execution_payload(module, timing: dict, *, decision_updates: dict | None = None) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "offline_training_execution_executed": True,
        "training_executed": True,
        "paired_evaluation_executed": False,
        "online_selector_latency_executed": False,
        "fallback_latency_executed": False,
        "performance_claimed": False,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "trajectory_modified": False,
    }
    if decision_updates:
        decision.update(decision_updates)
    return {
        "schema_version": module.EXECUTION_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
        "offline_training_timing": timing,
    }


def _config_payload(execution) -> dict:
    return {
        "label_source": "nonformal_matrix_coverage_only",
        "train_split_only": True,
        "performance_claim": False,
    }


def _model_payload(execution) -> dict:
    return {
        "atom_schema_version": execution.ATOM_SCHEMA_VERSION,
        "atom_names": list(execution.APPROVED_ATOM_NAMES),
        "score_expression": execution.SCORE_EXPRESSION,
        "train_row_count": 288,
        "label_source": "nonformal_matrix_coverage_only",
        "performance_claim": False,
        "trained_weights": [1.0 / len(execution.APPROVED_ATOM_NAMES)] * len(execution.APPROVED_ATOM_NAMES),
    }


def _timing_payload(execution, artifact: Path) -> dict:
    return {
        "offline_training": {
            "executed": True,
            "training_sample_count": 288,
            "training_wall_clock_seconds": 0.1,
            "training_artifact_sha256": _sha256(artifact / execution.MODEL_MANIFEST_JSON_NAME),
            "training_model_sha256": _sha256(artifact / execution.MODEL_JSON_NAME),
            "training_config_sha256": _sha256(artifact / execution.CONFIG_JSON_NAME),
            "training_log_sha256": _sha256(artifact / execution.LOG_NAME),
        },
        "online_selector_latency": {"executed": False},
        "fallback_latency": {"executed": False},
        "instrumentation_changes_selector_behavior": False,
    }


def _manifest_payload(execution, artifact: Path) -> dict:
    return {
        "training_executed": True,
        "training_inputs": {
            "train_row_count": 288,
            "zero_overlap_duplicate_count": 0,
        },
        "paired_evaluation_executed": False,
        "performance_claim": False,
        "blocked_inputs": {"Full36": False, "formal_seeds_11_12_13": False},
        "mutations": {
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
