from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_matrix.py"
)
HEAD = "ab921ba93f479f60036fb1d5ce1a665d97c25921"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_matrix_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_matrix_execution_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["matrix_execution_executed"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["full36_used"] is False
    assert decision["formal_seed_11_12_13_used"] is False
    assert report["matrix_execution"]["row_count"] == 576
    assert report["zero_overlap_validation"]["duplicate_count"] == 0
    assert report["timing"]["offline_training"]["executed"] is False
    assert (fixture["output_dir"] / module.EXECUTION_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.MATRIX_ROWS_JSONL_NAME).is_file()
    assert (fixture["output_dir"] / module.TIMING_JSON_NAME).is_file()


def test_v15_matrix_execution_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "matrix_execution_enabled" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_execution" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_execution" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_rejects_source_mutation_leak(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, source_updates={"candidate_tensor_modified": True})

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_candidate_tensor_not_modified" in report["final_decision"]["failed_checks"]


def test_v15_matrix_execution_is_recorded_in_audit() -> None:
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
    review = module.STATIC_REVIEW_MODULE
    artifact = tmp_path / "source_static_review"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")
    source_json = artifact / review.REVIEW_JSON_NAME
    source_md = artifact / review.REVIEW_MD_NAME
    _write_json(source_json, _source_review_payload(module, source_updates=source_updates))
    source_md.write_text("# Matrix Preflight Static Review\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run matrix preflight static review\n",
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
                review.REVIEW_JSON_NAME,
                review.REVIEW_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": source_json,
        "source_static_review_md": source_md,
        "source_static_review_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_review_payload(module, *, source_updates: dict | None = None) -> dict:
    decision = {
        "passed": True,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "reviewed_matrix_execution_preflight": True,
        "matrix_execution_preflight_executed": False,
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
        "schema_version": module.STATIC_REVIEW_MODULE.SCHEMA_VERSION,
        "final_decision": decision,
    }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
