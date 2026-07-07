from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v15_broader_nonformal_evidence_expansion_preflight_static_contract.py"
)
HEAD = "3ba3075efe00bf7052f95e15531775d6ae1cb36c"


def _load_module():
    spec = importlib.util.spec_from_file_location("v15_preflight_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v15_preflight_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["full36_used"] is False
    assert decision["formal_seed_11_12_13_used"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v15_preflight_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v15_preflight_static_review_rejects_hash_drift(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["source_report_md"].write_text("# drift\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "artifact_sha_v15_broader_nonformal_evidence_expansion_plan_preflight.md" in report["final_decision"]["failed_checks"]


def test_v15_preflight_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_v15_preflight_static_review_is_latest_status() -> None:
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
    plan = module.PLAN_MODULE
    artifact = tmp_path / "source_artifact"
    artifact.mkdir()
    output_dir = tmp_path / "review"
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    v15_audit = docs / "diffusion_planner_v15_iteration_audit.md"
    current_status = docs / "diffusion_planner_current_status.md"
    doc_text = f"next_work_target={next_target}\n"
    v15_audit.write_text(doc_text, encoding="utf-8")
    current_status.write_text(doc_text, encoding="utf-8")

    report = _source_report(plan)
    source_json = artifact / plan.REPORT_JSON_NAME
    source_md = artifact / plan.REPORT_MD_NAME
    timing_json = artifact / "timing.json"
    timing_md = artifact / "timing.md"
    _write_json(source_json, report)
    source_md.write_text("# Preflight\n", encoding="utf-8")
    timing_json.write_text(
        json.dumps(
            {
                "training_executed": False,
                "online_selector_evaluation_executed": False,
                "timing_instrumentation_changes_selector_behavior": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    timing_md.write_text("# Timing\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={plan.FIXED_DP_HEAD}\n",
        "COMMAND": "run preflight\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")
    sha_path = artifact / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(
            f"{_sha256(artifact / name)}  {name}"
            for name in plan.ARTIFACT_LAYOUT
            if name != "SHA256SUMS"
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_artifact_dir": artifact,
        "source_report_json": source_json,
        "source_report_md": source_md,
        "source_sha256s": sha_path,
        "v15_audit_md": v15_audit,
        "current_status_md": current_status,
        "output_dir": output_dir,
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": plan.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_report(plan) -> dict:
    return {
        "schema_version": plan.SCHEMA_VERSION,
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": plan.FIXED_DP_HEAD,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": plan.AUTHORIZED_NEXT_WORK,
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
