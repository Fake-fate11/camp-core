from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup.py"
)
HEAD = "eb198eb5371129b1de5bce163e5bdd1f3187dd73"
RESULT_REVIEW_ROOT_SHA = "eb9591b30cff2eb23ef34185c2015c2d7279d1272ea94bfbcf5cb66c6c633eaa"
PLAN_ROOT_SHA = "5a0253063e4165506653f897a983a096b3df457d30b09a3524f8c57c4986c343"
STATIC_REVIEW_ROOT_SHA = "02f34f0b614c956a611fa961c3c7b087a896d24acc6406ad18c386a846f5a71f"
PREFLIGHT_ROOT_SHA = "557be13a6f47f85a17e3b8326e7431f424b0c7c8e70fc9871cea441e99ccb1a3"
CORPUS_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"
ARTIFACT_PREFIX = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_split_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_split_execution_materializes_reviewed_scene_split(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    split = report["split_execution"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["split_execution_only"] is True
    assert decision["split_execution_executed"] is True
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert split["records"] == 10000
    assert split["scenes"] == 50
    assert split["unique_samples"] == 10000
    assert split["scene_counts"] == {"calibration": 10, "holdout": 10, "train": 30}
    assert split["record_counts"] == {"calibration": 2156, "holdout": 1581, "train": 6263}
    assert split["scene_assignments"]["train"][:2] == ["scene-0000", "scene-0001"]
    assert split["scene_assignments"]["train"][-1] == "scene-0029"
    assert split["scene_assignments"]["calibration"] == [f"scene-{index:04d}" for index in range(30, 40)]
    assert split["scene_assignments"]["holdout"] == [f"scene-{index:04d}" for index in range(40, 50)]
    assert split["scene_zero_overlap"] is True
    assert split["sample_zero_overlap"] is True
    assert split["record_level_hard_split_executed"] is False
    assert split["k_values"] == [8]
    assert split["candidate_count_values"] == [8]
    assert split["dp_head_values"] == [module.FIXED_DP_HEAD]
    assert split["candidate_tensor_mutated_count"] == 0
    assert split["output_root_absent_at_start"] is True
    assert _line_count(fixture["output_dir"] / module.SPLIT_JSONL_NAMES["train"]) == 6263
    assert _line_count(fixture["output_dir"] / module.SPLIT_JSONL_NAMES["calibration"]) == 2156
    assert _line_count(fixture["output_dir"] / module.SPLIT_JSONL_NAMES["holdout"]) == 1581
    assert (fixture["output_dir"] / "split_manifest.json").is_file()
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REPORT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_split_execution_rejects_existing_output_root(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, output_root_exists=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "output_root_absent" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_split_execution_rejects_mutated_candidate_tensor(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, mutated_candidate=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "candidate_tensor_not_mutated" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_split_execution_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    for text in (audit, status):
        assert ARTIFACT_PREFIX in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_train_scenes=30" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_calibration_scenes=10" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_holdout_scenes=10" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_sample_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_candidate_tensor_mutated_count=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_execution_performance_claimed=False" in text
        assert RESULT_REVIEW_ROOT_SHA in text
        assert PLAN_ROOT_SHA in text
        assert STATIC_REVIEW_ROOT_SHA in text
        assert PREFLIGHT_ROOT_SHA in text
        assert CORPUS_ROOT_SHA in text
        assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    output_root_exists: bool = False,
    mutated_candidate: bool = False,
) -> dict:
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
    result_review = _artifact(tmp_path / "result_review", RESULT_REVIEW_ROOT_SHA)
    split_plan = _artifact(tmp_path / "split_plan", PLAN_ROOT_SHA)
    static_review = _artifact(tmp_path / "static_review", STATIC_REVIEW_ROOT_SHA)
    preflight = _artifact(tmp_path / "preflight", PREFLIGHT_ROOT_SHA)
    corpus = _artifact(tmp_path / "corpus", CORPUS_ROOT_SHA)
    records = _records(module, mutated_candidate=mutated_candidate)
    _write(
        corpus / "records.jsonl",
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
    )
    _write_json(corpus / "scene_distribution.json", _scene_distribution())
    _write_json(result_review / module.SOURCE_RESULT_REVIEW_JSON_NAME, _result_review_payload(module))
    _write_json(split_plan / module.SOURCE_PLAN_JSON_NAME, _split_plan_payload(module))
    _write_json(static_review / module.SOURCE_STATIC_REVIEW_JSON_NAME, _static_review_payload(module))
    _write_json(preflight / module.SOURCE_PREFLIGHT_JSON_NAME, _preflight_payload(module))
    for root, md_name in (
        (result_review, module.SOURCE_RESULT_REVIEW_MD_NAME),
        (split_plan, module.SOURCE_PLAN_MD_NAME),
        (static_review, module.SOURCE_STATIC_REVIEW_MD_NAME),
        (preflight, module.SOURCE_PREFLIGHT_MD_NAME),
    ):
        _write(root / md_name, "# source\n")
    for root in (result_review, split_plan, static_review, preflight, corpus):
        _write(root / "HEADS", f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n")
        _write(root / "COMMAND", "command\n")
        _rewrite_manifest(root)
    output_dir = tmp_path / "out"
    if output_root_exists:
        output_dir.mkdir()
    return {
        "source_result_review_artifact_dir": result_review,
        "source_result_review_json": result_review / module.SOURCE_RESULT_REVIEW_JSON_NAME,
        "source_result_review_sha256s": result_review / "SHA256SUMS",
        "source_result_review_root_sha256s": result_review / "ROOT_SHA256SUMS",
        "source_plan_artifact_dir": split_plan,
        "source_plan_json": split_plan / module.SOURCE_PLAN_JSON_NAME,
        "source_plan_sha256s": split_plan / "SHA256SUMS",
        "source_plan_root_sha256s": split_plan / "ROOT_SHA256SUMS",
        "source_static_review_artifact_dir": static_review,
        "source_static_review_json": static_review / module.SOURCE_STATIC_REVIEW_JSON_NAME,
        "source_static_review_sha256s": static_review / "SHA256SUMS",
        "source_static_review_root_sha256s": static_review / "ROOT_SHA256SUMS",
        "source_preflight_artifact_dir": preflight,
        "source_preflight_json": preflight / module.SOURCE_PREFLIGHT_JSON_NAME,
        "source_preflight_sha256s": preflight / "SHA256SUMS",
        "source_preflight_root_sha256s": preflight / "ROOT_SHA256SUMS",
        "source_corpus_artifact_dir": corpus,
        "source_records_jsonl": corpus / "records.jsonl",
        "source_corpus_sha256s": corpus / "SHA256SUMS",
        "source_corpus_root_sha256s": corpus / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": output_dir,
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_result_review_root_sha256": RESULT_REVIEW_ROOT_SHA,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "expected_preflight_root_sha256": PREFLIGHT_ROOT_SHA,
        "expected_corpus_root_sha256": CORPUS_ROOT_SHA,
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


def _records(module, *, mutated_candidate: bool) -> list[dict]:
    records = []
    record_index = 0
    for scene_id, count in _counts_by_scene().items():
        for scene_record_index in range(count):
            sample_id = f"{scene_id}_{scene_record_index:06d}"
            records.append(
                {
                    "record_index": record_index,
                    "scene_id": scene_id,
                    "sample_id": sample_id,
                    "source_scene_id": scene_id,
                    "source_sample_id": sample_id,
                    "DP_HEAD": module.FIXED_DP_HEAD,
                    "K": 8,
                    "candidate_count": 8,
                    "candidate_tensor_shape": [8, 80, 4],
                    "candidate_tensor_sha256": f"{record_index:064x}",
                    "candidate_tensor_unchanged_by_camp": not (mutated_candidate and record_index == 0),
                }
            )
            record_index += 1
    return records


def _scene_distribution() -> dict:
    return {
        "distinct_scene_count": 50,
        "max_records_per_scene": 463,
        "scene_counts": _counts_by_scene(),
    }


def _result_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_RESULT_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_RESULT_REVIEW_READY_STATUS,
        "final_decision": {
            **_no_forbidden_fields(),
            "passed": True,
            "authorized_next_work": module.SOURCE_RESULT_REVIEW_AUTHORIZED_NEXT_WORK,
            "result_review_only": True,
        },
        "heads": {"dp_head": module.FIXED_DP_HEAD, "required_dp_head": module.FIXED_DP_HEAD},
        "record_review": {
            "record_count": 10000,
            "distinct_scene_count": 50,
            "unique_sample_count": 10000,
            "k_values": [8],
            "candidate_count_values": [8],
            "dp_heads": [module.FIXED_DP_HEAD],
            "candidate_tensor_mutated_count": 0,
            "failure_count": 0,
        },
        "source_artifact": {"root_sha256": CORPUS_ROOT_SHA},
    }


def _split_plan_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.SOURCE_PLAN_READY_STATUS,
        "authorized_next_work": module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
        "source_corpus_artifact": {"root_sha256": CORPUS_ROOT_SHA},
        "heads": {"dp_head": module.FIXED_DP_HEAD, "required_dp_head": module.FIXED_DP_HEAD},
        "split_plan": _split_contract(module),
        "final_decision": {
            **_no_forbidden_fields(),
            "passed": True,
            "authorized_next_work": module.SOURCE_PLAN_AUTHORIZED_NEXT_WORK,
            "split_plan_only": True,
            "split_executed": False,
        },
    }


def _static_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_STATIC_REVIEW_READY_STATUS,
        "authorized_next_work": module.SOURCE_STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
        "source_plan_artifact": {"root_sha256": PLAN_ROOT_SHA},
        "heads": {"dp_head": module.FIXED_DP_HEAD, "required_dp_head": module.FIXED_DP_HEAD},
        "plan_review": _split_contract(module),
        "final_decision": {
            **_no_forbidden_fields(),
            "passed": True,
            "authorized_next_work": module.SOURCE_STATIC_REVIEW_AUTHORIZED_NEXT_WORK,
            "static_review_only": True,
            "split_executed": False,
        },
    }


def _preflight_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_PREFLIGHT_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_static_review_artifact": {"root_sha256": STATIC_REVIEW_ROOT_SHA},
        "source_plan_artifact": {"root_sha256": PLAN_ROOT_SHA},
        "source_corpus_artifact": {"root_sha256": CORPUS_ROOT_SHA},
        "heads": {"dp_head": module.FIXED_DP_HEAD, "required_dp_head": module.FIXED_DP_HEAD},
        "preflight": {
            **_split_contract(module),
            "execution_output_root_absent": True,
        },
        "final_decision": {
            **_no_forbidden_fields(),
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "preflight_only": True,
            "split_execution_executed": False,
        },
    }


def _split_contract(module) -> dict:
    return {
        "records": 10000,
        "source_records": 10000,
        "scenes": 50,
        "source_scene_count": 50,
        "unique_samples": 10000,
        "source_unique_sample_count": 10000,
        "scene_assignments": _assignments(),
        "planned_scene_counts": {"calibration": 10, "holdout": 10, "train": 30},
        "planned_record_counts": {"calibration": 2156, "holdout": 1581, "train": 6263},
        "scene_zero_overlap": True,
        "sample_zero_overlap": True,
        "record_level_hard_split_executed": False,
        "k_values": [8],
        "candidate_count_values": [8],
        "dp_head_values": [module.FIXED_DP_HEAD],
        "candidate_tensor_mutated_count": 0,
        "followup_policy": {
            "training": "train split only",
            "paired_eval_primary": "calibration+holdout",
        },
    }


def _no_forbidden_fields() -> dict:
    return {
        "candidate_generation_executed": False,
        "training_executed": False,
        "paired_evaluation_executed": False,
        "performance_claimed": False,
        "promotion_executed": False,
        "deployment_executed": False,
        "dp_modified": False,
        "candidate_tensor_modified": False,
        "fake_candidate_tensor_generated": False,
    }


def _artifact(path: Path, root_sha: str) -> Path:
    path.mkdir(parents=True)
    _write(path / "ROOT_SHA256SUMS", f"{root_sha}  {path.name}\n")
    return path


def _rewrite_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}\n")
    (root / "SHA256SUMS").write_text("".join(rows), encoding="utf-8")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
