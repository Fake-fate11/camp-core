from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split.py"
)
HEAD = "9391812877c8c6983d268e40ea22c53fbced4be9"
SOURCE_ROOT_SHA = "eb9591b30cff2eb23ef34185c2015c2d7279d1272ea94bfbcf5cb66c6c633eaa"
SOURCE_CORPUS_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_split_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_split_plan_uses_scene_level_60_20_20(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    split = report["split_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["split_plan_only"] is True
    assert decision["split_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert split["target_scene_counts"] == {"calibration": 10, "holdout": 10, "train": 30}
    assert split["planned_scene_counts"] == {"calibration": 10, "holdout": 10, "train": 30}
    assert split["planned_record_counts"] == {"calibration": 2000, "holdout": 2000, "train": 6000}
    assert split["scene_zero_overlap"] is True
    assert split["sample_zero_overlap"] is True
    assert split["record_level_hard_split_executed"] is False
    assert split["k_values"] == [8]
    assert split["candidate_count_values"] == [8]
    assert split["dp_head_values"] == [module.FIXED_DP_HEAD]
    assert split["candidate_tensor_mutated_count"] == 0
    assert split["followup_policy"]["training"] == "train split only"
    assert split["followup_policy"]["paired_eval_primary"] == "calibration+holdout"
    assert split["followup_policy"]["claim"] == "blocked until result review and scale sufficiency checks"
    assert report["source_result_review_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_split_plan_rejects_record_level_hard_split(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, record_level_split=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "record_level_hard_split_not_executed" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, record_level_split: bool = False) -> dict:
    review = tmp_path / "result_review"
    corpus = tmp_path / "source_corpus"
    docs = tmp_path / "docs"
    review.mkdir()
    corpus.mkdir()
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    records = [_record(module, index) for index in range(10000)]
    (corpus / "records.jsonl").write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    scene_distribution = {
        "distinct_scene_count": 50,
        "max_records_per_scene": 200,
        "scene_counts": {f"scene-{index:04d}": 200 for index in range(50)},
    }
    _write_json(corpus / "scene_distribution.json", scene_distribution)
    for path, text in {
        corpus / "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.json": "{}\n",
        corpus / "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_execution.md": "# source\n",
        corpus / "timing.json": "{}\n",
        corpus / "timing.md": "# timing\n",
        corpus / "HEADS": f"DP_HEAD={module.FIXED_DP_HEAD}\n",
        corpus / "COMMAND": "run source\n",
        corpus / "stdout.txt": "",
        corpus / "stderr.txt": "",
        corpus / "run.exit": "0\n",
    }.items():
        _write(path, text)
    _write_manifest(corpus, SOURCE_CORPUS_ROOT_SHA)
    _write_json(review / module.SOURCE_JSON_NAME, _review_payload(module, record_level_split))
    for path, text in {
        review / module.SOURCE_MD_NAME: "# review\n",
        review / "HEADS": f"DP_HEAD={module.FIXED_DP_HEAD}\n",
        review / "COMMAND": "review source\n",
        review / "stdout.txt": "{}\n",
        review / "stderr.txt": "",
        review / "run.exit": "0\n",
    }.items():
        _write(path, text)
    _write_manifest(review, SOURCE_ROOT_SHA)
    return {
        "source_result_review_artifact_dir": review,
        "source_result_review_json": review / module.SOURCE_JSON_NAME,
        "source_result_review_sha256s": review / "SHA256SUMS",
        "source_result_review_root_sha256s": review / "ROOT_SHA256SUMS",
        "source_corpus_artifact_dir": corpus,
        "source_records_jsonl": corpus / "records.jsonl",
        "source_scene_distribution_json": corpus / "scene_distribution.json",
        "source_corpus_sha256s": corpus / "SHA256SUMS",
        "source_corpus_root_sha256s": corpus / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "expected_source_corpus_root_sha256": SOURCE_CORPUS_ROOT_SHA,
        "enabled": True,
    }


def _record(module, index: int) -> dict:
    scene_index = index // 200
    return {
        "record_index": index,
        "scene_id": f"scene-{scene_index:04d}",
        "sample_id": f"scene-{scene_index:04d}_{index:06d}",
        "source_scene_id": f"scene-{scene_index:04d}",
        "source_sample_id": f"scene-{scene_index:04d}_{index:06d}",
        "DP_HEAD": module.FIXED_DP_HEAD,
        "K": 8,
        "candidate_count": 8,
        "candidate_tensor_shape": [8, 80, 4],
        "candidate_tensor_sha256": f"{index:064x}",
        "candidate_tensor_unchanged_by_camp": True,
    }


def _review_payload(module, record_level_split: bool) -> dict:
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "result_review_only": True,
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
        "heads": {"dp_head": module.FIXED_DP_HEAD, "required_dp_head": module.FIXED_DP_HEAD},
        "record_review": {
            "record_count": 10000,
            "distinct_scene_count": 50,
            "unique_sample_count": 10000,
            "k_values": [8],
            "candidate_count_values": [8],
            "candidate_tensor_shapes": [[8, 80, 4]],
            "dp_heads": [module.FIXED_DP_HEAD],
            "candidate_tensor_mutated_count": 0,
            "failure_count": 0,
        },
        "split_plan": {"record_level_hard_split_executed": record_level_split},
        "source_artifact": {"root_sha256": SOURCE_CORPUS_ROOT_SHA},
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_manifest(root: Path, root_sha: str) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}\n")
    (root / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")
    (root / "ROOT_SHA256SUMS").write_text(f"{root_sha}  {root.name}\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
