from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result.py"
)
HEAD = "d20cf7d1596759df3f681b4da451fea46646ed32"
SOURCE_ROOT_SHA = "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_"
    "9152f8d4_20260708T031326CST"
)
REVIEW_CAMP_HEAD = "9152f8d4b1b86857355f960999147fa4b5d5649b"
SOURCE_CAMP_HEAD = "d799ada87f9ac384f08c978c40282771e024a9d2"
REVIEW_JSON_SHA = "65909eba2e5d8a6ccd30eba6fa31a34b0aebfca3bb0f917e84f42c1b45c7da11"
REVIEW_MD_SHA = "9e306770f6cd6aa0ca82efba5a053e1e95c84494931a12f98b612f65a50c3797"
REVIEW_SHA256SUMS_SHA = "2b52f7238c0b2ae0d48ef44c6721cb37c800c73989a6ec853c8752c18af9ba80"
REVIEW_ROOT_SHA = "bcb25cbc189c274845d94bc7963c683fd88c523be8243356f37481bae933d99e"
REVIEW_ROOT_SHA256SUMS_SHA = "18fe845a513a2cf3674879aee58e11433093f08b23f6848acafcc0a097f0b897"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_generation_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_generation_result_review_passes_1024_records(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert report["record_review"]["record_count"] == 1024
    assert report["record_review"]["candidate_count_values"] == [8]
    assert report["record_review"]["candidate_tensor_shapes"] == [[8, 80, 4]]
    assert report["timing_summary"]["source_wall_clock_seconds"] == 5516.609977
    assert report["source_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_generation_result_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    for text in (audit, status):
        assert REVIEW_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_check_count=59" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_records=1024" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_k=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_candidate_count=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_failed_checks=[]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_camp_head={REVIEW_CAMP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_result_review_source_camp_head={SOURCE_CAMP_HEAD}" in text
        assert REVIEW_JSON_SHA in text
        assert REVIEW_MD_SHA in text
        assert REVIEW_SHA256SUMS_SHA in text
        assert REVIEW_ROOT_SHA in text
        assert REVIEW_ROOT_SHA256SUMS_SHA in text
        assert SOURCE_ROOT_SHA in text


def _write_fixture(tmp_path: Path, module) -> dict:
    artifact = tmp_path / "source_execution"
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
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    records = [_record(module, index) for index in range(1024)]
    records_path = artifact / "records.jsonl"
    records_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
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
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "record_count": 1024,
        "records_jsonl": str(records_path),
        "runner": {
            "target_records": 1024,
            "k": 8,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
        "wall_clock_seconds": 5516.609977,
    }
    _write_json(artifact / module.SOURCE_JSON_NAME, summary)
    _write(artifact / module.SOURCE_MD_NAME, "# Pilot execution\n")
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run pilot execution\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, text)
    (artifact / "candidates").mkdir()
    for index in range(1024):
        _write(artifact / "candidates" / f"candidate_tensor_{index:06d}.npz", f"candidate-{index}\n")
    sha_names = [
        "COMMAND",
        "HEADS",
        "records.jsonl",
        "run.exit",
        "stderr.txt",
        "stdout.txt",
        module.SOURCE_JSON_NAME,
        module.SOURCE_MD_NAME,
    ] + [f"candidates/candidate_tensor_{index:06d}.npz" for index in range(1024)]
    (artifact / "SHA256SUMS").write_text(
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
        encoding="utf-8",
    )
    (artifact / "ROOT_SHA256SUMS").write_text(f"{SOURCE_ROOT_SHA}  {artifact.name}\n", encoding="utf-8")
    return {
        "source_artifact_dir": artifact,
        "source_summary_json": artifact / module.SOURCE_JSON_NAME,
        "source_records_jsonl": records_path,
        "source_sha256s": artifact / "SHA256SUMS",
        "source_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "enabled": True,
    }


def _record(module, index: int) -> dict:
    return {
        "record_index": index,
        "split": "mini_train",
        "scene_id": f"scene-{index:04d}",
        "sample_id": f"scene-{index:04d}_{index:06d}",
        "DP_HEAD": module.FIXED_DP_HEAD,
        "CAMP_HEAD": HEAD,
        "K": 8,
        "candidate_count": 8,
        "adapter_input_shape": {"ego_agent_past": [31, 3]},
        "adapter_input_sha256": f"{index:064x}",
        "candidate_tensor_shape": [8, 80, 4],
        "candidate_tensor_sha256": f"{255 - index:064x}",
        "candidate_tensor_unchanged_by_camp": True,
        "candidate_npz": f"candidates/candidate_tensor_{index:06d}.npz",
        "candidate_npz_sha256": "unused",
        "dp_top1_index": 0,
        "exporter_command": ["python", "exporter.py"],
        "exporter_exit": 0,
        "exporter_stdout": "{}\n",
        "exporter_stderr": "",
        "wall_clock_seconds": 1.0 + index / 1000,
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
