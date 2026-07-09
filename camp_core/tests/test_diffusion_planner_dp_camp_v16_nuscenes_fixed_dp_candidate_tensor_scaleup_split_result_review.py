from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result.py"
)
HEAD = "e0da1f37b772d373d0752fb7d794268e1b4b1243"
SOURCE_ROOT_SHA = "b8bb06e6f83ae59d8d08a8f400e58870971d42472d836fc10288327b19ac2456"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_"
    "e0da1f37b7_20260709T143217CST"
)
REVIEW_JSON_SHA = "292f2fec934bbccc47b1b138cb35d794c3ad778bd79298cd6ae30167e74bfcd7"
REVIEW_MD_SHA = "ec968b49ec0b638a86fbabdfa2a101efc918c95be4eab6b1a254264cd2b7d0fa"
REVIEW_SHA256SUMS_SHA = "1322556d790e25527818d38e77cf5240bb6fd68678563190a6ad0f88cbc70d0e"
REVIEW_ROOT_SHA256SUMS_SHA = "da9e25c5ca9643b5bbffd0e41f903ceea40d4130cda65e1c3cf767537504f787"
REVIEW_HEADS_SHA = "f7f583333b6244e2287eac7321de18f12bf94b8c785df2ae891d220b9c207d24"
REVIEW_COMMAND_SHA = "0dd0055757f5ce95f438b58cd00276eaecb8464e68338997328d5c2017d03cfe"
REVIEW_STDOUT_SHA = "998e193dbdfba90bd6b2769480e501d5966a0810d329041cb83d16d2bbb78cc5"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_split_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_split_result_review_passes_scene_pure_split(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["split_result_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["split_execution_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert review["records"] == 10000
    assert review["scenes"] == 50
    assert review["unique_samples"] == 10000
    assert review["scene_counts"] == {"calibration": 10, "holdout": 10, "train": 30}
    assert review["record_counts"] == {"calibration": 2156, "holdout": 1581, "train": 6263}
    assert review["scene_zero_overlap"] is True
    assert review["sample_zero_overlap"] is True
    assert review["record_level_hard_split_executed"] is False
    assert review["k_values"] == [8]
    assert review["candidate_count_values"] == [8]
    assert review["dp_head_values"] == [module.FIXED_DP_HEAD]
    assert review["candidate_tensor_mutated_count"] == 0
    assert review["source_artifact_files_present"] is True
    assert report["source_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_split_result_review_rejects_sample_overlap(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, duplicate_sample=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "sample_zero_overlap" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_split_result_review_is_recorded() -> None:
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
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_check_count=" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_sample_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_k_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_candidate_count_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_candidate_tensor_mutated_count=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_result_review_performance_claimed=False" in text
        assert SOURCE_ROOT_SHA in text
        assert REVIEW_JSON_SHA in text
        assert REVIEW_MD_SHA in text
        assert REVIEW_SHA256SUMS_SHA in text
        assert REVIEW_ROOT_SHA256SUMS_SHA in text
        assert REVIEW_HEADS_SHA in text
        assert REVIEW_COMMAND_SHA in text
        assert REVIEW_STDOUT_SHA in text
        assert REVIEW_STDERR_SHA in text
        assert REVIEW_RUN_EXIT_SHA in text
        assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in text


def _write_fixture(tmp_path: Path, module, *, duplicate_sample: bool = False) -> dict:
    artifact = tmp_path / "source_split_execution"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    records_by_split = _records_by_split(module, duplicate_sample=duplicate_sample)
    manifest = _manifest(module, records_by_split, sample_overlap=duplicate_sample)
    source = {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "split_execution": manifest,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "split_execution_only": True,
            "split_execution_executed": True,
            "candidate_generation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }
    _write_json(artifact / module.SOURCE_JSON_NAME, source)
    _write_json(artifact / "split_manifest.json", manifest)
    _write(artifact / module.SOURCE_MD_NAME, "# Split execution\n")
    for split, records in records_by_split.items():
        _write(
            artifact / module.SPLIT_JSONL_NAMES[split],
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        )
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "split execution\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, text)
    _rewrite_manifest(artifact)
    return {
        "source_artifact_dir": artifact,
        "source_summary_json": artifact / module.SOURCE_JSON_NAME,
        "source_split_manifest_json": artifact / "split_manifest.json",
        "source_train_records_jsonl": artifact / module.SPLIT_JSONL_NAMES["train"],
        "source_calibration_records_jsonl": artifact / module.SPLIT_JSONL_NAMES["calibration"],
        "source_holdout_records_jsonl": artifact / module.SPLIT_JSONL_NAMES["holdout"],
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


def _assignments() -> dict[str, list[str]]:
    return {
        "train": [f"scene-{index:04d}" for index in range(30)],
        "calibration": [f"scene-{index:04d}" for index in range(30, 40)],
        "holdout": [f"scene-{index:04d}" for index in range(40, 50)],
    }


def _counts_by_scene() -> dict[str, int]:
    counts = {f"scene-{index:04d}": 200 for index in range(29)}
    counts["scene-0029"] = 463
    counts.update({f"scene-{index:04d}": 200 for index in range(30, 39)})
    counts["scene-0039"] = 356
    counts.update({f"scene-{index:04d}": 150 for index in range(40, 49)})
    counts["scene-0049"] = 231
    return counts


def _records_by_split(module, *, duplicate_sample: bool) -> dict[str, list[dict]]:
    assignments = _assignments()
    scene_to_split = {scene: split for split, scenes in assignments.items() for scene in scenes}
    records = {"train": [], "calibration": [], "holdout": []}
    record_index = 0
    for scene_id, count in _counts_by_scene().items():
        for scene_record_index in range(count):
            sample_id = f"{scene_id}_{scene_record_index:06d}"
            if duplicate_sample and scene_id == "scene-0040" and scene_record_index == 0:
                sample_id = "scene-0000_000000"
            records[scene_to_split[scene_id]].append(
                {
                    "record_index": record_index,
                    "scene_id": scene_id,
                    "sample_id": sample_id,
                    "source_scene_id": scene_id,
                    "source_sample_id": sample_id,
                    "DP_HEAD": module.FIXED_DP_HEAD,
                    "K": 8,
                    "candidate_count": 8,
                    "candidate_tensor_sha256": f"{record_index:064x}",
                    "candidate_tensor_unchanged_by_camp": True,
                }
            )
            record_index += 1
    return records


def _manifest(module, records_by_split: dict[str, list[dict]], *, sample_overlap: bool) -> dict:
    all_records = [record for records in records_by_split.values() for record in records]
    return {
        "records": len(all_records),
        "scenes": 50,
        "unique_samples": len({record["source_sample_id"] for record in all_records}),
        "scene_assignments": _assignments(),
        "scene_counts": {"calibration": 10, "holdout": 10, "train": 30},
        "record_counts": {split: len(records) for split, records in records_by_split.items()},
        "scene_zero_overlap": True,
        "sample_zero_overlap": not sample_overlap,
        "record_level_hard_split_executed": False,
        "k_values": [8],
        "candidate_count_values": [8],
        "dp_head_values": [module.FIXED_DP_HEAD],
        "candidate_tensor_mutated_count": 0,
        "unassigned_record_count": 0,
        "split_manifest_materialized": True,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "performance_claimed": False,
        "promotion_executed": False,
        "deployment_executed": False,
    }


def _rewrite_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}\n")
    (root / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")
    (root / "ROOT_SHA256SUMS").write_text(f"{SOURCE_ROOT_SHA}  {root.name}\n", encoding="utf-8")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
