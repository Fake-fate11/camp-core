from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory.py"
)
HEAD = "64b116d458469f8e0d3ed7225856027691afb629"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_nuscenes_source_inventory_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_nuscenes_source_inventory_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["dp_modified"] is False
    assert report["nuscenes_inventory"]["root_exists"] is True
    assert "Fulldatasetv1.0/Trainval" in report["nuscenes_inventory"]["split_or_archive_entries"]
    assert "Mapexpansion/nuScenes-map-expansion-v1.3.zip" in report["nuscenes_inventory"]["map_entries"]
    assert "CANbusexpansion/can_bus.zip" in report["nuscenes_inventory"]["can_bus_entries"]
    assert report["camp_bridge"]["nuscenes_trajdata_bridge"]["available"] is True
    assert "ego_history" in report["dp_input_requirements"]
    assert report["nuscenes_direct_fields"]["ego_history"]["direct"] is True
    assert report["adapter_gaps"]["route_like_information"]["requires_adapter"] is True
    assert report["adapter_gaps"]["route_like_information"]["affects_claim_boundary"] is True
    assert report["smoke_scale"]["max_records"] == 1000
    assert "HEADS" in report["artifact_layout"]
    assert "DP candidate generation latency" in report["timing_fields"]
    assert "missing_nuscenes_root" in report["no_go_conditions"]
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_nuscenes_source_inventory_preflight_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_inventory_preflight_enabled" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_source_inventory_preflight_rejects_missing_nuscenes_root(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["nuscenes_root"] = tmp_path / "missing_nuscenes"

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "nuscenes_root_exists" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_source_inventory_preflight_rejects_dp_drift(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["current_dp_head"] = "0" * 40

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_source_inventory_preflight_rejects_wrong_v15_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "v15_audit_closeout_complete" in report["final_decision"]["failed_checks"]
    assert "status_doc_closeout_complete" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_source_inventory_preflight_is_recorded() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status_text = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    assert f"current_v16_status={module.READY_STATUS}" in audit_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit_text
    assert "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_preflight" in status_text


def _write_fixture(tmp_path: Path, module, *, next_work: str | None = None) -> dict:
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.REQUIRED_V15_NEXT_WORK
    v15_text = "\n".join(
        [
            f"current_v15_status={module.REQUIRED_V15_STATUS}",
            f"next_work_target={next_target}",
            "",
        ]
    )
    v15_audit = _write(docs / "diffusion_planner_v15_iteration_audit.md", v15_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", v15_text)
    v14_audit = _write(
        docs / "diffusion_planner_v14_iteration_audit.md",
        "auditable_integration_complete=True\nv14 sealed evidence\n",
    )
    nuscenes_root = tmp_path / "nuScenes"
    _write(nuscenes_root / "Fulldatasetv1.0" / "Trainval" / ".keep", "")
    _write(nuscenes_root / "Fulldatasetv1.0" / "Mini" / ".keep", "")
    _write(nuscenes_root / "Fulldatasetv1.0" / "Test" / ".keep", "")
    _write(nuscenes_root / "Mapexpansion" / "nuScenes-map-expansion-v1.3.zip", "")
    _write(nuscenes_root / "CANbusexpansion" / "can_bus.zip", "")
    camp_root = tmp_path / "camp"
    _write(camp_root / "camp_core" / "camp_core" / "data_interfaces" / "nuscenes_trajdata_bridge.py", "")
    _write(camp_root / "adaptive-prediction" / "unified-av-data-loader" / "src" / "trajdata" / "data_structures" / "batch.py", "")
    _write(camp_root / "scripts" / "data_gen" / "cache_dataset.py", "")
    return {
        "v15_audit_md": v15_audit,
        "v14_audit_md": v14_audit,
        "current_status_md": current_status,
        "nuscenes_root": nuscenes_root,
        "camp_repo_root": camp_root,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "required_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
