from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_smoke.py"
)
HEAD = "5c6f9a74444f692e9e261c85f7c60f8f6662a5b7"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_nuscenes_smoke_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_nuscenes_smoke_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    smoke = report["smoke_preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert smoke["records"]["target_records"] == 256
    assert smoke["candidate_generation"]["k"] == 8
    assert smoke["candidate_generation"]["candidate_count"] == 8
    assert smoke["candidate_generation"]["execute_in_this_gate"] is False
    assert smoke["candidate_generation"]["authorized_next_gate"] == module.AUTHORIZED_NEXT_WORK
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()


def test_v16_nuscenes_smoke_preflight_requires_enable(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "smoke_preflight_enabled" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_smoke_preflight_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_smoke_preflight" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_smoke_preflight" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_smoke_preflight_rejects_non_k8_source(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, k=16)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_static_review_k8" in report["final_decision"]["failed_checks"]


def test_v16_nuscenes_smoke_preflight_requires_bridge(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, bridge=False)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "camp_nuscenes_bridge_available" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    next_work: str | None = None,
    k: int = 8,
    bridge: bool = True,
) -> dict:
    source = module.SOURCE_REVIEW_MODULE
    artifact = tmp_path / "smoke_preflight_plan_static_review"
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
    source_json = artifact / source.REVIEW_JSON_NAME
    source_md = artifact / source.REVIEW_MD_NAME
    _write_json(source_json, _source_payload(module, k=k))
    source_md.write_text("# Smoke Preflight Plan Static Review\n", encoding="utf-8")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run smoke preflight plan static review\n",
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
    camp_repo = tmp_path / "camp"
    if bridge:
        _write(camp_repo / "camp_core" / "data_interfaces" / "nuscenes_trajdata_bridge.py", "")
    dp_repo = tmp_path / "Diffusion-Planner"
    dp_repo.mkdir()
    nuscenes_root = tmp_path / "nuScenes"
    nuscenes_root.mkdir()
    return {
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": source_json,
        "source_static_review_md": source_md,
        "source_static_review_sha256s": artifact / "SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "nuscenes_root": nuscenes_root,
        "camp_repo_root": camp_repo,
        "dp_repo": dp_repo,
        "candidate_output_root": tmp_path / "candidate_outputs",
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "enabled": True,
    }


def _source_payload(module, *, k: int) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_MODULE.SCHEMA_VERSION,
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
        "smoke_contract": {
            "k": k,
            "candidate_count": k,
            "must_record_candidate_tensor_shape_hash": True,
        },
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
