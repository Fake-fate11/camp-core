from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_result.py"
)
HEAD = "9dccb2df8ac1aa2070b7b4852f3911d01f66c7e4"
SOURCE_CAMP_HEAD = "b882659c70d4e38c37d246a60f5f09c6c0657eb0"
SOURCE_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_result_review_passes_10k_records(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert decision["dp_modified"] is False
    assert decision["candidate_tensor_modified"] is False
    assert decision["fake_candidate_tensor_generated"] is False
    assert report["record_review"]["record_count"] == 10000
    assert report["record_review"]["distinct_scene_count"] == 50
    assert report["record_review"]["unique_sample_count"] == 10000
    assert report["record_review"]["max_records_per_scene"] == 200
    assert report["record_review"]["scene_count_over_cap"] == 0
    assert report["record_review"]["candidate_count_values"] == [8]
    assert report["record_review"]["candidate_tensor_shapes"] == [[8, 80, 4]]
    assert report["record_review"]["failure_count"] == 0
    assert report["scene_distribution_review"]["distinct_scene_count"] == 50
    assert report["timing_summary"]["source_wall_clock_seconds"] == 59738.858347
    assert report["timing_summary"]["per_record_seconds"]["count"] == 10000
    assert report["source_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_result_review_rejects_duplicate_samples(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, duplicate_sample=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "records_unique_samples_10000" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_result_review_rejects_fake_candidate_tensor_provenance(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, fake_record=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "records_no_fake_or_synthetic_candidate_tensors" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    duplicate_sample: bool = False,
    fake_record: bool = False,
) -> dict:
    artifact = tmp_path / "scaleup_source"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    records = [_record(module, index, duplicate_sample, fake_record) for index in range(10000)]
    records_path = artifact / "records.jsonl"
    records_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    scene_counts = {f"scene-{index:04d}": 200 for index in range(50)}
    scene_distribution = {
        "distinct_scene_count": 50,
        "max_records_per_scene": 200,
        "scene_counts": scene_counts,
    }
    timing = {
        "wall_clock_seconds": 59738.858347,
        "per_record_seconds": {"count": 10000, "min": 5.0, "max": 10.0, "mean": 5.5},
    }
    summary = {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
        },
        "heads": {
            "camp_head": SOURCE_CAMP_HEAD,
            "camp_origin_main": SOURCE_CAMP_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "record_count": 10000,
        "runner": {
            "target_records": 10000,
            "minimum_distinct_scenes": 30,
            "max_records_per_scene": 334,
            "k": 8,
            "candidate_count": 8,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
        "scene_distribution": scene_distribution,
        "timing_summary": timing,
        "wall_clock_seconds": 59738.858347,
    }
    _write_json(artifact / module.SOURCE_JSON_NAME, summary)
    _write(artifact / module.SOURCE_MD_NAME, "# Scale-up execution\n")
    _write_json(artifact / "scene_distribution.json", scene_distribution)
    _write_json(artifact / "timing.json", timing)
    for name, text in {
        "timing.md": "# Timing\n",
        "HEADS": f"CAMP_HEAD={SOURCE_CAMP_HEAD}\nCAMP_ORIGIN_MAIN={SOURCE_CAMP_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run scaleup\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, text)
    sha_names = [
        "COMMAND",
        "HEADS",
        "records.jsonl",
        "run.exit",
        "scene_distribution.json",
        "stderr.txt",
        "stdout.txt",
        "timing.json",
        "timing.md",
        module.SOURCE_JSON_NAME,
        module.SOURCE_MD_NAME,
    ]
    (artifact / "SHA256SUMS").write_text(
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
        encoding="utf-8",
    )
    (artifact / "ROOT_SHA256SUMS").write_text(f"{SOURCE_ROOT_SHA}  {artifact.name}\n", encoding="utf-8")
    return {
        "source_artifact_dir": artifact,
        "source_summary_json": artifact / module.SOURCE_JSON_NAME,
        "source_records_jsonl": records_path,
        "source_scene_distribution_json": artifact / "scene_distribution.json",
        "source_timing_json": artifact / "timing.json",
        "source_sha256s": artifact / "SHA256SUMS",
        "source_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "enabled": True,
    }


def _record(module, index: int, duplicate_sample: bool, fake_record: bool) -> dict:
    scene_index = index // 200
    sample = "duplicate-sample" if duplicate_sample and index == 9999 else f"scene-{scene_index:04d}_{index:06d}"
    if duplicate_sample and index == 9999:
        sample = "scene-0000_000000"
    record = {
        "record_index": index,
        "split": "nusc_trainval-train",
        "source_split": "nusc_trainval-train",
        "scene_id": f"scene-{scene_index:04d}",
        "sample_id": sample,
        "source_scene_id": f"scene-{scene_index:04d}",
        "source_sample_id": sample,
        "DP_HEAD": module.FIXED_DP_HEAD,
        "CAMP_HEAD": SOURCE_CAMP_HEAD,
        "K": 8,
        "candidate_count": 8,
        "adapter_input_shape": {"ego_agent_past": [31, 3]},
        "adapter_input_sha256": f"{index:064x}",
        "candidate_tensor_shape": [8, 80, 4],
        "candidate_tensor_sha256": f"{255 - index:064x}",
        "candidate_tensor_unchanged_by_camp": True,
        "dp_top1_index": 0,
        "exporter_command": ["python", "exporter.py"],
        "exporter_exit": 0,
        "timing": {"wall_clock_seconds": 5.0},
        "wall_clock_seconds": 5.0,
    }
    if fake_record and index == 0:
        record["provenance"] = {"candidate_tensor_source": "synthetic"}
    return record


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
