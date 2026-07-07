from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_matrix_execution_preflight_static_contract.py"
)
HEAD = "bd80ed0fe3f8dacda5de5d9ba9c22c45b597b26d"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_matrix_preflight_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_matrix_execution_preflight_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["reviewed_matrix_execution_preflight"] is True
    assert decision["matrix_execution_preflight_executed"] is False
    assert decision["matrix_execution_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v15_matrix_execution_preflight_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_preflight_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_preflight_static_review_rejects_training_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, source_updates={"training_executed": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_training_not_executed" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    source_updates: dict | None = None,
) -> dict:
    preflight = module.PREFLIGHT_MODULE
    artifact = tmp_path / "source_preflight"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")
    timing = _timing_payload()
    source_json = artifact / preflight.PREFLIGHT_JSON_NAME
    source_md = artifact / preflight.PREFLIGHT_MD_NAME
    timing_json = artifact / preflight.TIMING_JSON_NAME
    timing_md = artifact / preflight.TIMING_MD_NAME
    _write_json(source_json, _source_preflight_payload(module, timing, source_updates=source_updates))
    source_md.write_text("# Matrix Preflight\n", encoding="utf-8")
    _write_json(timing_json, timing)
    timing_md.write_text("# Timing\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run matrix preflight\n",
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
                preflight.PREFLIGHT_JSON_NAME,
                preflight.PREFLIGHT_MD_NAME,
                preflight.TIMING_JSON_NAME,
                preflight.TIMING_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_preflight_artifact_dir": artifact,
        "source_preflight_json": source_json,
        "source_preflight_md": source_md,
        "source_timing_json": timing_json,
        "source_timing_md": timing_md,
        "source_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_preflight_payload(module, timing: dict, *, source_updates: dict | None = None) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "matrix_execution_preflight_executed": True,
        "matrix_execution_executed": False,
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
        "schema_version": module.PREFLIGHT_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
        "matrix_execution_preflight": {
            "combination_count": 576,
            "timing_contract": timing,
        },
        "timing_contract": timing,
    }


def _timing_payload() -> dict:
    return {
        "timing_required": True,
        "training_executed_by_this_gate": False,
        "selector_evaluation_executed_by_this_gate": False,
        "instrumentation_changes_selector_behavior": False,
        "offline_training_required_fields": [
            "training_start_timestamp",
            "training_end_timestamp",
            "training_wall_clock_seconds",
            "training_command",
            "training_sample_count",
            "training_artifact_sha256",
            "training_model_sha256",
            "training_config_sha256",
            "training_log_sha256",
        ],
        "online_selector_latency_required_fields": ["count", "mean", "median", "p95", "p99", "max"],
        "fallback_latency_required_fields": ["count", "mean", "median", "p95", "p99", "max"],
        "gpu_model_required": False,
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
