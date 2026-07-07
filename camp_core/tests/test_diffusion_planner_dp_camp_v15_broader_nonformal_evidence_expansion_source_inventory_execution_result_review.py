from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_source_inventory_execution_result.py"
)
HEAD = "512fc660f2c80cdfbf78bb657fee2de631b694b4"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_source_inventory_execution_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_source_inventory_execution_result_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["reviewed_source_inventory_execution"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()


def test_v15_source_inventory_execution_result_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "result_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_source_inventory_execution_result_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_review" in report["final_decision"]["failed_checks"]


def test_v15_source_inventory_execution_result_review_is_latest_status() -> None:
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


def _write_fixture(tmp_path: Path, module, *, next_work: str | None = None) -> dict:
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
    inventory = _inventory_payload(module)
    paths = {
        execution.INVENTORY_JSON_NAME: inventory,
        execution.SPLIT_MANIFEST_NAME: inventory["split_manifest"],
        execution.ZERO_OVERLAP_PLAN_NAME: inventory["zero_overlap_plan"],
        execution.SCENARIO_BUCKET_MANIFEST_NAME: inventory["scenario_bucket_manifest"],
    }
    for name, payload in paths.items():
        _write_json(artifact / name, payload)
    (artifact / execution.INVENTORY_MD_NAME).write_text("# Inventory\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run source inventory\n",
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
                execution.INVENTORY_JSON_NAME,
                execution.INVENTORY_MD_NAME,
                execution.SPLIT_MANIFEST_NAME,
                execution.ZERO_OVERLAP_PLAN_NAME,
                execution.SCENARIO_BUCKET_MANIFEST_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_execution_artifact_dir": artifact,
        "source_inventory_json": artifact / execution.INVENTORY_JSON_NAME,
        "source_inventory_md": artifact / execution.INVENTORY_MD_NAME,
        "source_split_manifest": artifact / execution.SPLIT_MANIFEST_NAME,
        "source_zero_overlap_plan": artifact / execution.ZERO_OVERLAP_PLAN_NAME,
        "source_scenario_bucket_manifest": artifact / execution.SCENARIO_BUCKET_MANIFEST_NAME,
        "source_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _inventory_payload(module) -> dict:
    execution = module.EXECUTION_MODULE
    return {
        "schema_version": execution.SCHEMA_VERSION,
        "split_manifest": {"train": {}, "calibration": {}, "holdout": {}},
        "zero_overlap_plan": {"zero_overlap_keys": ["route", "seed", "npc_mode", "traffic_light_mode", "candidate_tensor_sha256", "record_id"]},
        "scenario_bucket_manifest": {
            "scenario_buckets": list(execution.PLAN_MODULE.SCENARIO_BUCKETS)
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "inventory_executed": True,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
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
