from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_contract.py"
)
HEAD = "cfa83a49c8e067fd717a11aa43d91ac20e4f025f"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_nuscenes_source_inventory_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_nuscenes_source_inventory_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["dp_modified"] is False
    assert decision["candidate_tensor_modified"] is False
    assert "route_like_information" in report["adapter_plan_requirements"]
    assert "traffic_light_signal_context" in report["adapter_plan_requirements"]
    assert report["smoke_plan"]["min_records"] == 100
    assert report["smoke_plan"]["max_records"] == 1000
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_nuscenes_source_inventory_static_review_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_source_inventory_static_review_rejects_missing_adapter_gap(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, drop_gap="traffic_light_signal_context")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "adapter_gap_traffic_light_signal_context" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_source_inventory_static_review_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_static_review" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_static_review" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_source_inventory_static_review_is_recorded() -> None:
    module = _load_module()
    audit_text = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status_text = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    assert f"current_v16_status={module.READY_STATUS}" in audit_text
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit_text
    assert "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_source_inventory_static_review" in status_text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    drop_gap: str | None = None,
) -> dict:
    preflight = module.PREFLIGHT_MODULE
    artifact = tmp_path / "source_preflight"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    next_target = next_work or module.AUTHORIZED_CURRENT_WORK
    doc_text = "\n".join(
        [
            f"current_v16_status={preflight.READY_STATUS}",
            f"next_work_target={next_target}",
            "",
        ]
    )
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    source_json = artifact / preflight.PREFLIGHT_JSON_NAME
    source_md = artifact / preflight.PREFLIGHT_MD_NAME
    payload = _source_preflight_payload(module)
    if drop_gap is not None:
        payload["adapter_gaps"].pop(drop_gap)
    _write_json(source_json, payload)
    source_md.write_text("# Source Inventory Preflight\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run source inventory preflight\n",
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
                preflight.PREFLIGHT_JSON_NAME,
                preflight.PREFLIGHT_MD_NAME,
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source_preflight_artifact_dir": artifact,
        "source_preflight_json": source_json,
        "source_preflight_md": source_md,
        "source_preflight_sha256s": artifact / "SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_preflight_payload(module) -> dict:
    preflight = module.PREFLIGHT_MODULE
    return {
        "schema_version": preflight.SCHEMA_VERSION,
        "adapter_gaps": {
            name: {"requires_adapter": True}
            for name in (
                "route_like_information",
                "traffic_light_signal_context",
                "autoware_lane_tensor_format",
            )
        },
        "boundary": {
            "camp_action": "rerank_or_select_fixed_dp_candidates_only",
            "score": "score_k(w)=a_k^T w",
            "weights": "nonnegative_simplex",
        },
        "dp_input_requirements": list(preflight.DP_INPUT_REQUIREMENTS),
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
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
        "nuscenes_direct_fields": {
            name: {"direct": True}
            for name in (
                "ego_history",
                "ego_state",
                "neighbor_agents",
                "map_lane_context",
                "timestamps_sample_ids",
            )
        },
        "smoke_scale": {"min_records": 100, "max_records": 1000},
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
