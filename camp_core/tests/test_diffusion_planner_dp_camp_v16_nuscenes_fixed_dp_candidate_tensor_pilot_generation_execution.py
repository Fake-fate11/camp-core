from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "execute_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation.py"
)
HEAD = "0cef62e13be3b62602277118d9eb51ab5b4ef78d"
ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_candidates_"
    "mini_train_d799ada8_20260708T013202CST"
)
JSON_SHA = "65a416dc0a7ce0fdcf4e568380687ff65c289782551a0256a570d5a0268dddbe"
MD_SHA = "239ffe278c5abf2598604314b3fd09d262378133432597ed8f08dbe54f1c93a4"
RECORDS_JSONL_SHA = "890bf586e68fd0e21e278c07cb77dfd4cddb7be24b0b85154b81adab358969a1"
SHA256SUMS_SHA = "03425fdd1b79026166f381e255445a2db6e6ebd5fc33a909f5ac4daf0e70897b"
ROOT_SHA = "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432"
ROOT_SHA256SUMS_SHA = "ff05c972f9ab9f492e698a5776b6cf1c49c64ef44cd65a8a56045e0bb151fac3"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_candidate_tensor_pilot_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_candidate_tensor_pilot_generation_execution_accepts_1024_gate(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert report["runner"]["target_records"] == 1024
    assert report["runner"]["k"] == 8
    assert report["runner"]["candidate_count"] == 8
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REPORT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_candidate_tensor_pilot_generation_execution_maps_mini_train_split() -> None:
    module = _load_module()

    assert module._trajdata_split("mini_train") == "nusc_mini-mini_train"
    assert module._trajdata_split("mini_val") == "nusc_mini-mini_val"


def test_v16_candidate_tensor_pilot_generation_execution_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    assert f"current_v16_status={module.READY_STATUS}" in audit
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in audit
    for text in (audit, status):
        assert ARTIFACT in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_records=1024" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_k=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_candidate_count=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_split=mini_train" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_execution_failed_checks=[]" in text
        assert JSON_SHA in text
        assert MD_SHA in text
        assert RECORDS_JSONL_SHA in text
        assert SHA256SUMS_SHA in text
        assert ROOT_SHA in text
        assert ROOT_SHA256SUMS_SHA in text


def _write_fixture(tmp_path: Path, module) -> dict:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_PREFLIGHT_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_artifacts = {}
    for name in module.SOURCE_ARTIFACT_KEYS:
        artifact = tmp_path / name
        artifact.mkdir()
        _write(artifact / "SHA256SUMS", "")
        _write(artifact / "ROOT_SHA256SUMS", f"{name:0<64}  {name}\n")
        source_artifacts[name] = artifact
    metadata_root = tmp_path / "nuScenes"
    metadata_root.mkdir()
    trajdata_cache_dir = tmp_path / "trajdata_cache"
    trajdata_cache_dir.mkdir()
    return {
        "output_dir": tmp_path / "out",
        "metadata_root": metadata_root,
        "trajdata_cache_dir": trajdata_cache_dir,
        "dp_repo": tmp_path / "Diffusion-Planner",
        "checkpoint": _write(tmp_path / "Diffusion-Planner" / "checkpoint.pth", "fake"),
        "args_json": _write(tmp_path / "Diffusion-Planner" / "args.json", "{}"),
        "source_artifacts": source_artifacts,
        "v16_audit_md": audit,
        "current_status_md": status,
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "target_records": 1024,
        "k": 8,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
