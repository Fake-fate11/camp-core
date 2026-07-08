from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_result.py"
)
HEAD = "691d31c196cf94b9833df221977f1173762a8bc7"
SOURCE_ROOT_SHA = "18f1231c1c50841bde09527066f7845fe6b101c9978bf490457d8ce6c1867878"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_corpus_split_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_corpus_split_result_review_passes_scene_pure_split(tmp_path: Path) -> None:
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
    assert review["total_records"] == 1024
    assert review["counts"] == {"calibration": 14, "holdout": 147, "train": 863}
    assert review["scene_assignments"] == {
        "calibration": ["scene-0061"],
        "holdout": ["scene-0757"],
        "train": ["scene-0553", "scene-0655"],
    }
    assert review["scene_zero_overlap"] is True
    assert review["sample_zero_overlap"] is True
    assert review["k_values"] == [8]
    assert review["candidate_count_values"] == [8]
    assert review["dp_head_values"] == [module.FIXED_DP_HEAD]
    assert review["candidate_tensor_mutated_count"] == 0
    assert review["performance_claim_supported"] is False
    assert report["source_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").read_text(encoding="utf-8").split()[1] == "SHA256SUMS"


def test_v16_pilot_corpus_split_result_review_rejects_sample_overlap(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, duplicate_sample=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "sample_zero_overlap" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, duplicate_sample: bool = False) -> dict:
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

    split_records = {
        "train": [
            _record(module, "train", "scene-0553", index)
            for index in range(495)
        ]
        + [
            _record(module, "train", "scene-0655", 495 + index)
            for index in range(368)
        ],
        "calibration": [
            _record(module, "calibration", "scene-0061", 863 + index)
            for index in range(14)
        ],
        "holdout": [
            _record(module, "holdout", "scene-0757", 877 + index)
            for index in range(147)
        ],
    }
    if duplicate_sample:
        split_records["holdout"][0]["sample_id"] = split_records["train"][0]["sample_id"]

    manifest = {
        "split_policy": "scene_level_greedy_imbalance_tolerant_smoke_split",
        "pilot_split_classification": "imbalance_tolerant_smoke_split",
        "performance_claim_supported": False,
        "record_level_hard_split_executed": False,
        "scene_assignments": {
            "train": ["scene-0553", "scene-0655"],
            "calibration": ["scene-0061"],
            "holdout": ["scene-0757"],
        },
        "counts": {split: len(records) for split, records in split_records.items()},
        "scene_zero_overlap": True,
        "sample_zero_overlap": not duplicate_sample,
        "k_values": [8],
        "candidate_count_values": [8],
        "dp_head_values": [module.FIXED_DP_HEAD],
        "candidate_tensor_mutated_count": 0,
        "total_records": 1024,
    }
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
    for split, records in split_records.items():
        path = artifact / module.SPLIT_JSONL_NAMES[split]
        path.write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "split execution\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, text)
    sha_names = [
        module.SOURCE_JSON_NAME,
        module.SOURCE_MD_NAME,
        "split_manifest.json",
        module.SPLIT_JSONL_NAMES["train"],
        module.SPLIT_JSONL_NAMES["calibration"],
        module.SPLIT_JSONL_NAMES["holdout"],
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
    ]
    (artifact / "SHA256SUMS").write_text(
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
        encoding="utf-8",
    )
    (artifact / "ROOT_SHA256SUMS").write_text(f"{SOURCE_ROOT_SHA}  {artifact.name}\n", encoding="utf-8")
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


def _record(module, split: str, scene: str, index: int) -> dict:
    return {
        "record_index": index,
        "split": split,
        "scene_id": scene,
        "sample_id": f"{scene}_{index:06d}",
        "DP_HEAD": module.FIXED_DP_HEAD,
        "CAMP_HEAD": HEAD,
        "K": 8,
        "candidate_count": 8,
        "candidate_tensor_shape": [8, 80, 4],
        "candidate_tensor_sha256": f"{index:064x}",
        "candidate_tensor_unchanged_by_camp": True,
        "dp_top1_index": 0,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
