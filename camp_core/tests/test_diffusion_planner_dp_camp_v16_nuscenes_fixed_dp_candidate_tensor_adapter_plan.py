from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_adapter.py"
)
HEAD = "a3eb0e689ec4363c6497b15089404774c73eefbd"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_nuscenes_adapter_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_nuscenes_adapter_plan_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["adapter_execution_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert report["adapter_plan"]["input_mapping"]["ego_history"]["source"] == "AgentBatch.agent_hist"
    assert report["adapter_plan"]["input_mapping"]["route_like_information"]["adapter_boundary"] == "derived_from_vector_map_not_mission_route"
    assert report["adapter_plan"]["input_mapping"]["traffic_light_signal_context"]["adapter_boundary"] == "unknown_or_unavailable_no_safety_claim"
    assert report["adapter_plan"]["candidate_tensor_contract"]["immutable_after_dp"] is True
    assert report["adapter_plan"]["smoke"]["min_records"] == 100
    assert report["adapter_plan"]["smoke"]["max_records"] == 1000
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()


def test_v16_nuscenes_adapter_plan_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "adapter_plan_enabled" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_adapter_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_adapter_plan" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_adapter_plan" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_adapter_plan_rejects_missing_gap(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, drop_requirement="route_like_information")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_requires_route_like_information" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_adapter_plan_is_recorded() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status_text = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    assert f"current_v16_status={module.READY_STATUS}" in audit_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit_text
    assert f"current_v16_status={module.READY_STATUS}" in status_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status_text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    drop_requirement: str | None = None,
) -> dict:
    source = module.SOURCE_REVIEW_MODULE
    artifact = tmp_path / "source_static_review"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v16_status={source.READY_STATUS}",
            f"next_work_target={next_target}",
            "",
        ]
    )
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    requirements = list(source.ADAPTER_PLAN_REQUIREMENTS)
    if drop_requirement is not None:
        requirements.remove(drop_requirement)
    source_json = artifact / source.REVIEW_JSON_NAME
    source_md = artifact / source.REVIEW_MD_NAME
    _write_json(source_json, _source_payload(module, requirements))
    source_md.write_text("# Static Review\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run static review\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        (artifact / name).write_text(content, encoding="utf-8")
    (artifact / "SHA256SUMS").write_text(
        "\n".join(
            f"{_sha256(artifact / name)}  {name}"
            for name in (
                "HEADS",
                "COMMAND",
                "stdout.txt",
                "stderr.txt",
                "run.exit",
                source.REVIEW_JSON_NAME,
                source.REVIEW_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": source_json,
        "source_static_review_md": source_md,
        "source_static_review_sha256s": artifact / "SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_payload(module, requirements: list[str]) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_MODULE.SCHEMA_VERSION,
        "adapter_plan_requirements": requirements,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "static_review_only": True,
            "candidate_generation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
        },
        "smoke_plan": {"min_records": 100, "max_records": 1000},
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
