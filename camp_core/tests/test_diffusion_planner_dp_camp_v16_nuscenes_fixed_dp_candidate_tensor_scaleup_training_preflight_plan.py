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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight.py"
)
HEAD = "7dfa1b3d13ae0acb6667d9d2591315ab8ed4301f"
SPLIT_REVIEW_ROOT_SHA = "1322556d790e25527818d38e77cf5240bb6fd68678563190a6ad0f88cbc70d0e"
SPLIT_EXECUTION_ROOT_SHA = "b8bb06e6f83ae59d8d08a8f400e58870971d42472d836fc10288327b19ac2456"
SCALEUP_CORPUS_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_"
    "7dfa1b3d13_20260709T150711CST"
)
PLAN_CAMP_HEAD = "7dfa1b3d13ae0acb6667d9d2591315ab8ed4301f"
PLAN_JSON_SHA = "f33e80b44df840cf7855d8599ab219513446d1e59d3d77d0ecaeaccceff968d5"
PLAN_MD_SHA = "43cea2f32994c5b01f7c4828b65c94d898c2fd7096feceab75e476cb5c563fbf"
PLAN_SHA256SUMS_SHA = "990992937869aca189cb71d9832a435575c01091a924e136df1850bc164f549b"
PLAN_ROOT_SHA256SUMS_SHA = "2bc5ee89f1a028514746044b4c08bfb1f1e29a9ac3d8ceb067e5598664e4480c"
PLAN_HEADS_SHA = "59740ad93f7573cfb5372611faa6a85b8616f5cd44dc53b01f6c4ea128a0db4a"
PLAN_COMMAND_SHA = "e7e7c00746d5347ca52e205df0f42a2ead43880ddce2c6f0f9acc0aebb727f17"
PLAN_STDOUT_SHA = "5059b05a8645aac83589252cbfefe744a006240b7dd87bc2875fe393b12df2e8"
PLAN_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PLAN_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
SCALEUP_CORPUS_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_candidates_retry_b882659c70_"
    "20260708T185012CST"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_training_preflight_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_training_preflight_plan_uses_train_split_only(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["scaleup_training_preflight_plan"]
    inputs = plan["training_inputs"]
    output_plan = plan["planned_outputs"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["scaleup_training_preflight_plan_executed"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert inputs["train_records"] == 6263
    assert inputs["calibration_records_available"] == 2156
    assert inputs["holdout_records_available"] == 1581
    assert inputs["calibration_records_used_for_training"] == 0
    assert inputs["holdout_records_used_for_training"] == 0
    assert inputs["training_splits"] == ["train"]
    assert inputs["forbidden_training_splits"] == ["calibration", "holdout"]
    assert inputs["split_result_review_root_sha256"] == SPLIT_REVIEW_ROOT_SHA
    assert inputs["split_execution_root_sha256"] == SPLIT_EXECUTION_ROOT_SHA
    assert inputs["scaleup_corpus_root_sha256"] == SCALEUP_CORPUS_ROOT_SHA
    assert inputs["scaleup_corpus_artifact"] == SCALEUP_CORPUS_ARTIFACT
    assert inputs["candidate_tensor_schema"] == {
        "candidate_count": 8,
        "candidate_tensor_shape": [8, 80, 4],
        "k": 8,
    }
    assert plan["training_scope"] == "scaleup_train_split_training_plan_only_no_performance_claim"
    assert plan["math_contract"] == {
        "approved_atoms_only": True,
        "no_candidate_tensor_mutation": True,
        "no_closed_loop_outcomes_as_training_input": True,
        "no_dp_modification": True,
        "nonnegative_simplex": True,
        "score_expression": "score_k(w)=a_k^T w",
        "weights_nonnegative": True,
        "weights_sum_to_one": True,
    }
    assert output_plan == {
        "approved_atoms_check": "approved_atoms_check.json",
        "command": "COMMAND",
        "heads": "HEADS",
        "nonnegative_simplex_check": "nonnegative_simplex_check.json",
        "root_sha256s": "ROOT_SHA256SUMS",
        "sha256s": "SHA256SUMS",
        "static_camp_weights_model_artifact": "static_camp_weights_model.json",
        "stderr": "stderr.txt",
        "stdout": "stdout.txt",
        "timing_json": "scaleup_training_timing.json",
        "timing_md": "scaleup_training_timing.md",
        "training_config": "scaleup_training_config.json",
        "training_log": "scaleup_training.log",
    }
    assert plan["stop_conditions"] == [
        "split_overlap",
        "missing_candidate_hashes",
        "k_or_candidate_count_drift",
        "dp_head_mismatch",
        "calibration_or_holdout_leakage",
        "non_affine_score",
        "non_simplex_weights",
    ]
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").read_text(encoding="utf-8").split()[1] == "SHA256SUMS"


def test_v16_scaleup_training_preflight_plan_rejects_holdout_training_use(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, holdout_used_for_training=1)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_review_holdout_records_used_for_training_false" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_plan_rejects_non_affine_score(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["score_expression"] = "score_k(w)=nonlinear(a_k,w)"

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "score_expression_affine" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_plan_rejects_missing_candidate_hash(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, missing_train_hash=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "candidate_tensor_hashes_present" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_plan_rejects_sample_overlap(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, duplicate_sample=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "sample_zero_overlap" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_plan_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    for text in (audit, status):
        assert PLAN_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_camp_head={PLAN_CAMP_HEAD}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_calibration_records_available=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_holdout_records_available=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_no_closed_loop_outcomes_as_training_input=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_performance_claimed=False" in text
        assert PLAN_JSON_SHA in text
        assert PLAN_MD_SHA in text
        assert PLAN_SHA256SUMS_SHA in text
        assert PLAN_ROOT_SHA256SUMS_SHA in text
        assert PLAN_HEADS_SHA in text
        assert PLAN_COMMAND_SHA in text
        assert PLAN_STDOUT_SHA in text
        assert PLAN_STDERR_SHA in text
        assert PLAN_RUN_EXIT_SHA in text
        assert SPLIT_REVIEW_ROOT_SHA in text
        assert SPLIT_EXECUTION_ROOT_SHA in text
        assert SCALEUP_CORPUS_ROOT_SHA in text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    holdout_used_for_training: int = 0,
    missing_train_hash: bool = False,
    duplicate_sample: bool = False,
) -> dict:
    split_review = tmp_path / "split_result_review"
    split_execution = tmp_path / "split_execution"
    docs = tmp_path / "docs"
    split_review.mkdir()
    split_execution.mkdir()
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
    if missing_train_hash:
        del records_by_split["train"][0]["candidate_tensor_sha256"]

    split_execution_json = split_execution / module.SPLIT_EXECUTION_JSON_NAME
    _write_json(split_execution_json, _split_execution_payload(module))
    _write(split_execution / module.SPLIT_EXECUTION_MD_NAME, "# Split execution\n")
    _write_json(split_execution / "split_manifest.json", _split_manifest(module))
    for name, records in {
        "train_records.jsonl": records_by_split["train"],
        "calibration_records.jsonl": records_by_split["calibration"],
        "holdout_records.jsonl": records_by_split["holdout"],
    }.items():
        (split_execution / name).write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )
    _write_source_artifact_files(split_execution, module.FIXED_DP_HEAD)
    _write_manifest(split_execution, SPLIT_EXECUTION_ROOT_SHA)

    review_json = split_review / module.SOURCE_REVIEW_JSON_NAME
    _write_json(
        review_json,
        _split_review_payload(
            module,
            split_execution,
            holdout_used_for_training=holdout_used_for_training,
        ),
    )
    _write(split_review / module.SOURCE_REVIEW_MD_NAME, "# Split result review\n")
    _write_source_artifact_files(split_review, module.FIXED_DP_HEAD)
    _write_manifest(split_review, SPLIT_REVIEW_ROOT_SHA)

    return {
        "source_split_result_review_artifact_dir": split_review,
        "source_split_result_review_json": review_json,
        "source_split_result_review_sha256s": split_review / "SHA256SUMS",
        "source_split_result_review_root_sha256s": split_review / "ROOT_SHA256SUMS",
        "source_split_execution_artifact_dir": split_execution,
        "source_split_execution_json": split_execution_json,
        "source_train_records_jsonl": split_execution / "train_records.jsonl",
        "source_calibration_records_jsonl": split_execution / "calibration_records.jsonl",
        "source_holdout_records_jsonl": split_execution / "holdout_records.jsonl",
        "source_split_execution_sha256s": split_execution / "SHA256SUMS",
        "source_split_execution_root_sha256s": split_execution / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_split_result_review_root_sha256": SPLIT_REVIEW_ROOT_SHA,
        "expected_split_execution_root_sha256": SPLIT_EXECUTION_ROOT_SHA,
        "score_expression": "score_k(w)=a_k^T w",
        "enabled": True,
    }


def _split_review_payload(module, split_execution: Path, *, holdout_used_for_training: int) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_artifact": {
            "path": str(split_execution),
            "root_sha256": SPLIT_EXECUTION_ROOT_SHA,
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "split_result_review": {
            "candidate_count_values": [8],
            "candidate_tensor_mutated_count": 0,
            "record_counts": {"calibration": 2156, "holdout": 1581, "train": 6263},
            "scene_counts": {"calibration": 10, "holdout": 10, "train": 30},
            "dp_head_values": [module.FIXED_DP_HEAD],
            "k_values": [8],
            "record_level_hard_split_executed": False,
            "records": 10000,
            "sample_zero_overlap": True,
            "scene_zero_overlap": True,
            "scenes": 50,
            "unique_samples": 10000,
            "unassigned_record_count": 0,
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "calibration_records_used_for_training": 0,
            "candidate_generation_executed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "holdout_records_used_for_training": holdout_used_for_training,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "result_review_only": True,
            "split_execution_executed": False,
            "training_executed": False,
        },
    }


def _split_execution_payload(module) -> dict:
    return {
        "schema_version": module.SPLIT_EXECUTION_SCHEMA_VERSION,
        "status": module.SPLIT_EXECUTION_READY_STATUS,
        "source_artifacts": {
            "corpus": {
                "path": SCALEUP_CORPUS_ARTIFACT,
                "root_sha256": SCALEUP_CORPUS_ROOT_SHA,
            }
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "split_execution": {
            "candidate_count_values": [8],
            "record_counts": {"calibration": 2156, "holdout": 1581, "train": 6263},
            "dp_head_values": [module.FIXED_DP_HEAD],
            "k_values": [8],
        },
        "final_decision": {
            "authorized_next_work": module.SOURCE_CURRENT_WORK,
            "candidate_generation_executed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "split_execution_executed": True,
            "training_executed": False,
        },
    }


def _split_manifest(module) -> dict:
    return {
        "candidate_count_values": [8],
        "candidate_tensor_mutated_count": 0,
        "dp_head_values": [module.FIXED_DP_HEAD],
        "k_values": [8],
        "record_counts": {"calibration": 2156, "holdout": 1581, "train": 6263},
        "records": 10000,
        "sample_zero_overlap": True,
        "scene_counts": {"calibration": 10, "holdout": 10, "train": 30},
        "scene_zero_overlap": True,
    }


def _records_by_split(module, *, duplicate_sample: bool) -> dict[str, list[dict]]:
    records = {"train": [], "calibration": [], "holdout": []}
    record_index = 0
    for split, scene_prefix, count in [
        ("train", "scene-train", 6263),
        ("calibration", "scene-calibration", 2156),
        ("holdout", "scene-holdout", 1581),
    ]:
        for index in range(count):
            sample_id = f"{scene_prefix}-{index // 250:04d}_{index:06d}"
            if duplicate_sample and split == "holdout" and index == 0:
                sample_id = "scene-train-0000_000000"
            records[split].append(_record(module, split, scene_prefix, index, record_index, sample_id))
            record_index += 1
    return records


def _record(module, split: str, scene_prefix: str, index: int, record_index: int, sample_id: str) -> dict:
    return {
        "candidate_count": 8,
        "candidate_tensor_sha256": f"{record_index:064x}",
        "candidate_tensor_shape": [8, 80, 4],
        "candidate_tensor_unchanged_by_camp": True,
        "DP_HEAD": module.FIXED_DP_HEAD,
        "K": 8,
        "sample_id": sample_id,
        "scene_id": f"{scene_prefix}-{index // 250:04d}",
        "source_sample_id": sample_id,
        "source_scene_id": f"{scene_prefix}-{index // 250:04d}",
        "split": split,
    }


def _write_source_artifact_files(root: Path, dp_head: str) -> None:
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={dp_head}\n",
        "COMMAND": "source command\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(root / name, text)


def _write_manifest(root: Path, root_sha: str) -> None:
    names = sorted(path.name for path in root.iterdir() if path.is_file() and path.name != "ROOT_SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in names if name != "SHA256SUMS"),
        encoding="utf-8",
    )
    (root / "ROOT_SHA256SUMS").write_text(f"{root_sha}  SHA256SUMS\n", encoding="utf-8")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
