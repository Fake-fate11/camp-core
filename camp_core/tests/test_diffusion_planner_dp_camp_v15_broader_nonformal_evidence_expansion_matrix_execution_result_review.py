from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_matrix_execution_result.py"
)
HEAD = "2cfcce1a01d30135ec153d968f9e8ddbaf02bcea"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_matrix_execution_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_matrix_execution_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["reviewed_matrix_execution"] is True
    assert decision["matrix_execution_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v15_matrix_execution_result_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_result_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_review" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_result_review_rejects_training_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, source_updates={"training_executed": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_training_not_executed" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_result_review_is_recorded_in_audit() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v15_iteration_audit.md").read_text(
        encoding="utf-8"
    )

    assert f"current_v15_status={module.READY_STATUS}" in audit_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit_text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_updates: dict | None = None,
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
    payload = _source_execution_payload(module, source_updates=source_updates)
    files = {
        execution.EXECUTION_JSON_NAME: payload,
        execution.SPLIT_MANIFEST_NAME: payload["split_manifest"],
        execution.ZERO_OVERLAP_VALIDATION_NAME: payload["zero_overlap_validation"],
        execution.SCENARIO_BUCKET_MANIFEST_NAME: payload["scenario_bucket_manifest"],
        execution.TIMING_JSON_NAME: payload["timing"],
    }
    for name, value in files.items():
        _write_json(artifact / name, value)
    (artifact / execution.EXECUTION_MD_NAME).write_text("# Matrix Execution\n", encoding="utf-8")
    rows_path = artifact / execution.MATRIX_ROWS_JSONL_NAME
    rows_path.write_text(
        "".join(json.dumps({"record_id": f"v15-matrix-{index:04d}"}) + "\n" for index in range(576)),
        encoding="utf-8",
    )
    (artifact / execution.TIMING_MD_NAME).write_text("# Timing\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run matrix execution\n",
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
                execution.MATRIX_ROWS_JSONL_NAME,
                execution.SPLIT_MANIFEST_NAME,
                execution.ZERO_OVERLAP_VALIDATION_NAME,
                execution.SCENARIO_BUCKET_MANIFEST_NAME,
                execution.TIMING_JSON_NAME,
                execution.TIMING_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_execution_artifact_dir": artifact,
        "source_execution_json": artifact / execution.EXECUTION_JSON_NAME,
        "source_execution_md": artifact / execution.EXECUTION_MD_NAME,
        "source_rows_jsonl": rows_path,
        "source_split_manifest": artifact / execution.SPLIT_MANIFEST_NAME,
        "source_zero_overlap_validation": artifact / execution.ZERO_OVERLAP_VALIDATION_NAME,
        "source_scenario_bucket_manifest": artifact / execution.SCENARIO_BUCKET_MANIFEST_NAME,
        "source_timing_json": artifact / execution.TIMING_JSON_NAME,
        "source_timing_md": artifact / execution.TIMING_MD_NAME,
        "source_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_execution_payload(module, *, source_updates: dict | None = None) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "matrix_execution_executed": True,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "trajectory_modified": False,
    }
    if source_updates:
        decision.update(source_updates)
    return {
        "schema_version": module.EXECUTION_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
        "matrix_execution": {"row_count": 576},
        "split_manifest": {"total_row_count": 576},
        "zero_overlap_validation": {"duplicate_count": 0},
        "scenario_bucket_manifest": {"total_row_count": 576},
        "timing": {
            "offline_training": {"executed": False},
            "online_selector_latency": {"executed": False},
            "fallback_latency": {"executed": False},
        },
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
