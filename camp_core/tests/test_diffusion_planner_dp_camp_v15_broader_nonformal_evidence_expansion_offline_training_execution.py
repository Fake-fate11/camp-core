from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_offline_training.py"
)
HEAD = "d4a115525e293ec987b0f3f0030d769c14d3a3a0"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_offline_training_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_offline_training_execution_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    timing = report["offline_training_timing"]["offline_training"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["offline_training_execution_executed"] is True
    assert decision["training_executed"] is True
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["full36_used"] is False
    assert decision["formal_seed_11_12_13_used"] is False
    assert timing["training_sample_count"] == 288
    assert timing["training_model_sha256"] == _sha256(fixture["output_dir"] / module.MODEL_JSON_NAME)
    assert report["offline_training_model"]["nonnegative_simplex"] is True
    assert (fixture["output_dir"] / module.MANIFEST_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.TIMING_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.MODEL_MANIFEST_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.LOG_NAME).is_file()


def test_v15_offline_training_execution_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "offline_training_execution_enabled" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["training_executed"] is False


def test_v15_offline_training_execution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_execution" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_execution" in report["final_decision"]["failed_checks"]


def test_v15_offline_training_execution_rejects_source_mutation_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, static_updates={"candidate_tensor_modified": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_candidate_tensor_not_modified" in report["final_decision"]["failed_checks"]


def test_v15_offline_training_execution_rejects_matrix_overlap(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, zero_updates={"duplicate_count": 1})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "matrix_zero_overlap_duplicate_count" in report["final_decision"]["failed_checks"]


def test_v15_offline_training_execution_is_recorded_in_audit() -> None:
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
    static_updates: dict | None = None,
    zero_updates: dict | None = None,
) -> dict:
    static_artifact = tmp_path / "source_static_review"
    matrix_artifact = tmp_path / "source_matrix_execution"
    static_artifact.mkdir()
    matrix_artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")

    static = module.STATIC_REVIEW_MODULE
    static_json = static_artifact / static.REVIEW_JSON_NAME
    static_md = static_artifact / static.REVIEW_MD_NAME
    _write_json(static_json, _static_review_payload(module, static_updates=static_updates))
    static_md.write_text("# Offline Training Preflight Static Review\n", encoding="utf-8")
    _write_support_files(static_artifact, "run offline training preflight static review\n", module)
    static_sha = _write_sha256s(
        static_artifact,
        ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", static.REVIEW_JSON_NAME, static.REVIEW_MD_NAME),
    )

    matrix = module.MATRIX_MODULE
    rows = matrix._matrix_rows(HEAD, module.FIXED_DP_HEAD)
    split = matrix._split_manifest(rows)
    zero = matrix._zero_overlap_validation(rows)
    if zero_updates:
        zero.update(zero_updates)
    scenario = matrix._scenario_bucket_manifest(rows)
    matrix_json = matrix_artifact / matrix.EXECUTION_JSON_NAME
    matrix_md = matrix_artifact / matrix.EXECUTION_MD_NAME
    rows_jsonl = matrix_artifact / matrix.MATRIX_ROWS_JSONL_NAME
    split_json = matrix_artifact / matrix.SPLIT_MANIFEST_NAME
    zero_json = matrix_artifact / matrix.ZERO_OVERLAP_VALIDATION_NAME
    scenario_json = matrix_artifact / matrix.SCENARIO_BUCKET_MANIFEST_NAME
    _write_json(matrix_json, _matrix_execution_payload(module))
    matrix_md.write_text("# Matrix Execution\n", encoding="utf-8")
    rows_jsonl.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    _write_json(split_json, split)
    _write_json(zero_json, zero)
    _write_json(scenario_json, scenario)
    _write_json(matrix_artifact / matrix.TIMING_JSON_NAME, matrix._timing_report())
    (matrix_artifact / matrix.TIMING_MD_NAME).write_text("# Timing\n", encoding="utf-8")
    _write_support_files(matrix_artifact, "run matrix execution\n", module)
    matrix_sha = _write_sha256s(
        matrix_artifact,
        (
            "HEADS",
            "COMMAND",
            "stdout.txt",
            "stderr.txt",
            "run.exit",
            matrix.EXECUTION_JSON_NAME,
            matrix.EXECUTION_MD_NAME,
            matrix.MATRIX_ROWS_JSONL_NAME,
            matrix.SPLIT_MANIFEST_NAME,
            matrix.ZERO_OVERLAP_VALIDATION_NAME,
            matrix.SCENARIO_BUCKET_MANIFEST_NAME,
            matrix.TIMING_JSON_NAME,
            matrix.TIMING_MD_NAME,
        ),
    )

    return {
        "source_static_review_artifact_dir": static_artifact,
        "source_static_review_json": static_json,
        "source_static_review_md": static_md,
        "source_static_review_sha256s": static_sha,
        "source_matrix_execution_artifact_dir": matrix_artifact,
        "source_matrix_execution_json": matrix_json,
        "source_matrix_rows_jsonl": rows_jsonl,
        "source_matrix_split_manifest_json": split_json,
        "source_matrix_zero_overlap_validation_json": zero_json,
        "source_matrix_scenario_bucket_manifest_json": scenario_json,
        "source_matrix_sha256s": matrix_sha,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _static_review_payload(module, *, static_updates: dict | None = None) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "reviewed_offline_training_preflight": True,
        "offline_training_preflight_executed": False,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "full36_used": False,
        "formal_seed_11_12_13_used": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "trajectory_modified": False,
    }
    if static_updates:
        decision.update(static_updates)
    return {
        "schema_version": module.STATIC_REVIEW_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
    }


def _matrix_execution_payload(module) -> dict:
    return {
        "schema_version": module.MATRIX_MODULE.SCHEMA_VERSION,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.MATRIX_MODULE.AUTHORIZED_NEXT_WORK,
            "matrix_execution_executed": True,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
    }


def _write_support_files(artifact: Path, command: str, module) -> None:
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": command,
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_sha256s(artifact: Path, names: tuple[str, ...]) -> Path:
    sha_path = artifact / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(f"{_sha256(artifact / name)}  {name}" for name in names) + "\n",
        encoding="utf-8",
    )
    return sha_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
