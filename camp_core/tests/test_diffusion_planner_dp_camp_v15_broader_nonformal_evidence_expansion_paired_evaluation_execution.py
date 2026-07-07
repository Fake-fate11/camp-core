from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_paired_evaluation.py"
)
HEAD = "c5b60fc70a60427f5fa83d95377f0ca886f9d2ce"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_paired_evaluation_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_paired_evaluation_execution_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["paired_evaluation_execution_executed"] is True
    assert decision["paired_evaluation_executed"] is True
    assert decision["training_executed"] is False
    assert decision["source_training_executed"] is True
    assert decision["online_selector_latency_executed"] is True
    assert decision["fallback_latency_executed"] is True
    assert decision["performance_claimed"] is False
    assert report["paired_evaluation"]["row_count"] == 2
    assert report["paired_evaluation"]["evaluation_splits"] == ["calibration", "holdout"]
    assert report["split_metrics"]["calibration"]["row_count"] == 1
    assert report["split_metrics"]["holdout"]["row_count"] == 1
    assert report["split_metrics"]["train"]["row_count"] == 0
    assert report["online_selector_latency"]["count"] == 2
    assert report["fallback_latency"]["count"] == 2
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PAIRED_ROWS_JSONL_NAME).is_file()
    assert (fixture["output_dir"] / module.ONLINE_LATENCY_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.FALLBACK_LATENCY_JSON_NAME).is_file()


def test_v15_paired_evaluation_execution_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "paired_evaluation_execution_enabled" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_execution" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_execution" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_rejects_source_mutation_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(
        tmp_path,
        module,
        source_static_updates={"candidate_tensor_modified": True},
    )

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_candidate_tensor_not_modified" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_rejects_non_simplex_model(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, model_updates={"trained_weights": [1.0, 1.0]})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "model_weights_nonnegative_simplex" in report["final_decision"]["failed_checks"]


def test_v15_paired_evaluation_execution_is_recorded_in_audit() -> None:
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
    source_static_updates: dict | None = None,
    model_updates: dict | None = None,
) -> dict:
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")

    static_artifact = _write_static_review_artifact(
        tmp_path / "source_static_review",
        module,
        source_static_updates=source_static_updates,
    )
    matrix_artifact = _write_matrix_artifact(tmp_path / "source_matrix", module)
    offline_artifact = _write_offline_training_artifact(
        tmp_path / "source_offline_training",
        module,
        model_updates=model_updates,
    )
    return {
        "source_static_review_artifact_dir": static_artifact,
        "source_static_review_json": static_artifact / module.STATIC_REVIEW_MODULE.REVIEW_JSON_NAME,
        "source_static_review_md": static_artifact / module.STATIC_REVIEW_MODULE.REVIEW_MD_NAME,
        "source_static_review_sha256s": static_artifact / "SHA256SUMS",
        "source_matrix_execution_artifact_dir": matrix_artifact,
        "source_matrix_execution_json": matrix_artifact / module.MATRIX_MODULE.EXECUTION_JSON_NAME,
        "source_matrix_rows_jsonl": matrix_artifact / module.MATRIX_MODULE.MATRIX_ROWS_JSONL_NAME,
        "source_matrix_split_manifest_json": matrix_artifact / module.MATRIX_MODULE.SPLIT_MANIFEST_NAME,
        "source_matrix_zero_overlap_validation_json": matrix_artifact / module.MATRIX_MODULE.ZERO_OVERLAP_VALIDATION_NAME,
        "source_matrix_scenario_bucket_manifest_json": matrix_artifact / module.MATRIX_MODULE.SCENARIO_BUCKET_MANIFEST_NAME,
        "source_matrix_sha256s": matrix_artifact / "SHA256SUMS",
        "source_offline_training_artifact_dir": offline_artifact,
        "source_offline_training_execution_json": offline_artifact / module.OFFLINE_TRAINING_MODULE.EXECUTION_JSON_NAME,
        "source_offline_training_manifest_json": offline_artifact / module.OFFLINE_TRAINING_MODULE.MANIFEST_JSON_NAME,
        "source_offline_training_model_manifest_json": offline_artifact / module.OFFLINE_TRAINING_MODULE.MODEL_MANIFEST_JSON_NAME,
        "source_offline_training_model_json": offline_artifact / module.OFFLINE_TRAINING_MODULE.MODEL_JSON_NAME,
        "source_offline_training_config_json": offline_artifact / module.OFFLINE_TRAINING_MODULE.CONFIG_JSON_NAME,
        "source_offline_training_timing_json": offline_artifact / module.OFFLINE_TRAINING_MODULE.TIMING_JSON_NAME,
        "source_offline_training_log": offline_artifact / module.OFFLINE_TRAINING_MODULE.LOG_NAME,
        "source_offline_training_sha256s": offline_artifact / "SHA256SUMS",
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write_static_review_artifact(
    artifact: Path,
    module,
    *,
    source_static_updates: dict | None = None,
) -> Path:
    artifact.mkdir()
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "reviewed_paired_evaluation_execution_preflight": True,
        "paired_evaluation_execution_preflight_executed": False,
        "training_executed": False,
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
    if source_static_updates:
        decision.update(source_static_updates)
    _write_json(
        artifact / module.STATIC_REVIEW_MODULE.REVIEW_JSON_NAME,
        {
            "schema_version": module.STATIC_REVIEW_MODULE.SCHEMA_VERSION,
            "final_decision": decision,
        },
    )
    (artifact / module.STATIC_REVIEW_MODULE.REVIEW_MD_NAME).write_text("# Static Review\n", encoding="utf-8")
    _write_wrapper_files(artifact, module)
    _write_sha256s(
        artifact,
        (
            "HEADS",
            "COMMAND",
            "stdout.txt",
            "stderr.txt",
            "run.exit",
            module.STATIC_REVIEW_MODULE.REVIEW_JSON_NAME,
            module.STATIC_REVIEW_MODULE.REVIEW_MD_NAME,
        ),
    )
    return artifact


def _write_matrix_artifact(artifact: Path, module) -> Path:
    artifact.mkdir()
    rows = _matrix_rows(module)
    _write_json(
        artifact / module.MATRIX_MODULE.EXECUTION_JSON_NAME,
        {
            "schema_version": module.MATRIX_MODULE.SCHEMA_VERSION,
            "final_decision": {
                "passed": True,
                "matrix_execution_executed": True,
                "training_executed": False,
                "paired_evaluation_executed": False,
                "full36_used": False,
                "formal_seed_11_12_13_used": False,
                "dp_modified": False,
                "candidate_tensor_modified": False,
                "trajectory_modified": False,
            },
            "matrix_execution": {"row_count": len(rows)},
        },
    )
    (artifact / module.MATRIX_MODULE.EXECUTION_MD_NAME).write_text("# Matrix\n", encoding="utf-8")
    (artifact / module.MATRIX_MODULE.MATRIX_ROWS_JSONL_NAME).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    _write_json(
        artifact / module.MATRIX_MODULE.SPLIT_MANIFEST_NAME,
        {"total_row_count": len(rows), "splits": {"train": {}, "calibration": {}, "holdout": {}}},
    )
    _write_json(
        artifact / module.MATRIX_MODULE.ZERO_OVERLAP_VALIDATION_NAME,
        {"duplicate_count": 0, "row_count": len(rows), "unique_key_count": len(rows)},
    )
    _write_json(
        artifact / module.MATRIX_MODULE.SCENARIO_BUCKET_MANIFEST_NAME,
        {"total_row_count": len(rows), "bucket_counts": {"normal": len(rows)}},
    )
    _write_wrapper_files(artifact, module)
    _write_sha256s(
        artifact,
        (
            "HEADS",
            "COMMAND",
            "stdout.txt",
            "stderr.txt",
            "run.exit",
            module.MATRIX_MODULE.EXECUTION_JSON_NAME,
            module.MATRIX_MODULE.EXECUTION_MD_NAME,
            module.MATRIX_MODULE.MATRIX_ROWS_JSONL_NAME,
            module.MATRIX_MODULE.SPLIT_MANIFEST_NAME,
            module.MATRIX_MODULE.ZERO_OVERLAP_VALIDATION_NAME,
            module.MATRIX_MODULE.SCENARIO_BUCKET_MANIFEST_NAME,
        ),
    )
    return artifact


def _write_offline_training_artifact(
    artifact: Path,
    module,
    *,
    model_updates: dict | None = None,
) -> Path:
    artifact.mkdir()
    atom_count = len(module.OFFLINE_TRAINING_MODULE.APPROVED_ATOM_NAMES)
    model = {
        "atom_names": list(module.OFFLINE_TRAINING_MODULE.APPROVED_ATOM_NAMES),
        "atom_schema_version": module.OFFLINE_TRAINING_MODULE.ATOM_SCHEMA_VERSION,
        "label_source": "nonformal_matrix_coverage_only",
        "performance_claim": False,
        "score_expression": module.OFFLINE_TRAINING_MODULE.SCORE_EXPRESSION,
        "trained_weights": [1.0 / atom_count] * atom_count,
    }
    if model_updates:
        model.update(model_updates)
    manifest = {"training_executed": True, "paired_evaluation_executed": False}
    model_manifest = {"model_json": module.OFFLINE_TRAINING_MODULE.MODEL_JSON_NAME}
    config = {"label_source": "nonformal_matrix_coverage_only", "performance_claim": False}
    timing = {
        "offline_training": {
            "executed": True,
            "training_sample_count": 1,
            "training_wall_clock_seconds": 0.01,
        },
        "online_selector_latency": {"executed": False, "count": 0},
        "fallback_latency": {"executed": False, "count": 0},
        "instrumentation_changes_selector_behavior": False,
    }
    log = "training log\n"
    _write_json(
        artifact / module.OFFLINE_TRAINING_MODULE.EXECUTION_JSON_NAME,
        {
            "schema_version": module.OFFLINE_TRAINING_MODULE.SCHEMA_VERSION,
            "final_decision": {
                "passed": True,
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
            },
            "offline_training_timing": timing,
        },
    )
    _write_json(artifact / module.OFFLINE_TRAINING_MODULE.MANIFEST_JSON_NAME, manifest)
    _write_json(artifact / module.OFFLINE_TRAINING_MODULE.MODEL_MANIFEST_JSON_NAME, model_manifest)
    _write_json(artifact / module.OFFLINE_TRAINING_MODULE.MODEL_JSON_NAME, model)
    _write_json(artifact / module.OFFLINE_TRAINING_MODULE.CONFIG_JSON_NAME, config)
    _write_json(artifact / module.OFFLINE_TRAINING_MODULE.TIMING_JSON_NAME, timing)
    (artifact / module.OFFLINE_TRAINING_MODULE.LOG_NAME).write_text(log, encoding="utf-8")
    (artifact / module.OFFLINE_TRAINING_MODULE.EXECUTION_MD_NAME).write_text("# Offline\n", encoding="utf-8")
    _write_wrapper_files(artifact, module)
    _write_sha256s(
        artifact,
        (
            "HEADS",
            "COMMAND",
            "stdout.txt",
            "stderr.txt",
            "run.exit",
            module.OFFLINE_TRAINING_MODULE.EXECUTION_JSON_NAME,
            module.OFFLINE_TRAINING_MODULE.EXECUTION_MD_NAME,
            module.OFFLINE_TRAINING_MODULE.MANIFEST_JSON_NAME,
            module.OFFLINE_TRAINING_MODULE.MODEL_MANIFEST_JSON_NAME,
            module.OFFLINE_TRAINING_MODULE.MODEL_JSON_NAME,
            module.OFFLINE_TRAINING_MODULE.CONFIG_JSON_NAME,
            module.OFFLINE_TRAINING_MODULE.TIMING_JSON_NAME,
            module.OFFLINE_TRAINING_MODULE.LOG_NAME,
        ),
    )
    return artifact


def _matrix_rows(module) -> list[dict]:
    return [
        _row(module, "train", "route_train", "seed_train"),
        _row(module, "calibration", "route_calibration", "seed_calibration"),
        _row(module, "holdout", "route_holdout", "seed_holdout"),
    ]


def _row(module, split: str, route: str, seed: str) -> dict:
    return {
        "camp_action": "rerank_or_select_only",
        "candidate_tensor_materialized_by_this_gate": False,
        "candidate_tensor_provenance_sha256": f"sha-{split}",
        "fixed_dp_head": module.FIXED_DP_HEAD,
        "npc_mode": "none",
        "record_id": f"row-{split}",
        "route": route,
        "scenario_bucket": "normal",
        "seed": seed,
        "split": split,
        "traffic_light_mode": "off",
    }


def _write_wrapper_files(artifact: Path, module) -> None:
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")


def _write_sha256s(artifact: Path, names: tuple[str, ...]) -> None:
    (artifact / "SHA256SUMS").write_text(
        "\n".join(f"{_sha256(artifact / name)}  {name}" for name in names) + "\n",
        encoding="utf-8",
    )


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
