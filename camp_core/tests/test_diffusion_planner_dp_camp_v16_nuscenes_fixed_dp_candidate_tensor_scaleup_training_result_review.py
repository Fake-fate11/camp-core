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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result.py"
)
HEAD = "7aec1e3b9ec3cd209a142b48986ed74b0386b31a"
SOURCE_HEAD = "b9a43b733712d38252a43415050ced20ade5edae"
SOURCE_ROOT_SHA = "70875a2691fcd45f6337c48db563b9623e9606adbc35c5fd1df9f7e68029f28e"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_"
    "7aec1e3b9e_20260709T172320CST"
)
REVIEW_JSON_SHA = "2c107cc76629befa0f38d15f0d9d0f3ab470383fd2b376704c9c52b72aea19bd"
REVIEW_MD_SHA = "89e7aed64033d5f3a42a45a54c4510674d480a957f061a2877393a86054b0562"
REVIEW_SHA256SUMS_SHA = "1063073e0b1f7088b142241f71a238711635865409ed5166e389b46299521429"
REVIEW_ROOT_SHA256SUMS_SHA = "3d3f2ace22c9da36baaed6e11e77cadf779cb10de5302bed80bdfd0fab25c848"
REVIEW_HEADS_SHA = "4a14438f761a7ae14dacd95b372cfaf8d3adca27bb00458814d04c667fde623c"
REVIEW_COMMAND_SHA = "5e432c1f9693156f07903561d0b4c95347c24b17ab1a17c4bf937ee84f0c433f"
REVIEW_STDOUT_SHA = "963cc9d78bcf0c6701918a0548fa75f7d9a50f17926212084d57f2c4812a6c04"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_training_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_training_result_review_passes_train_only_artifact(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["training_result_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["training_executed_by_review"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["train_records"] == 6263
    assert review["calibration_records_used_for_training"] == 0
    assert review["holdout_records_used_for_training"] == 0
    assert review["scene_zero_overlap"] is True
    assert review["sample_zero_overlap"] is True
    assert review["train_k_values"] == [8]
    assert review["train_candidate_count_values"] == [8]
    assert review["candidate_tensor_mutated_count"] == 0
    assert review["closed_loop_outcomes_used_for_training"] is False
    assert review["atom_schema_version"] == "camp_legacy_v1_9d"
    assert review["weights_nonnegative"] is True
    assert review["weights_sum_to_one"] is True
    assert review["approved_atoms_only"] is True
    assert review["score_expression"] == module.SCORE_EXPRESSION
    assert review["offline_training_wall_clock_seconds"] == 1.335207
    assert report["source_artifact"]["root_sha256"] == SOURCE_ROOT_SHA
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_training_result_review_rejects_holdout_leakage(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, holdout_used=1)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "holdout_not_used_for_training" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_result_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert REVIEW_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_check_count=65" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_sample_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_k_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_candidate_count_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_candidate_tensor_mutated_count=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_closed_loop_outcomes_used_for_training=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_atom_schema_version=camp_legacy_v1_9d" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_offline_training_wall_clock_seconds=1.335207" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_camp_head={HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_result_review_source_camp_head={SOURCE_HEAD}" in text
        assert REVIEW_JSON_SHA in text
        assert REVIEW_MD_SHA in text
        assert REVIEW_SHA256SUMS_SHA in text
        assert REVIEW_ROOT_SHA256SUMS_SHA in text
        assert REVIEW_HEADS_SHA in text
        assert REVIEW_COMMAND_SHA in text
        assert REVIEW_STDOUT_SHA in text
        assert REVIEW_STDERR_SHA in text
        assert REVIEW_RUN_EXIT_SHA in text
        assert SOURCE_ROOT_SHA in text
    assert f"current_v16_status={module.READY_STATUS}" in status
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status


def _write_fixture(tmp_path: Path, module, *, holdout_used: int = 0) -> dict:
    artifact = tmp_path / "source_training"
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
    source = _source_payload(module, holdout_used=holdout_used)
    _write_json(artifact / module.SOURCE_JSON_NAME, source)
    _write(artifact / module.SOURCE_MD_NAME, "# Scale-up training execution\n")
    for name, text in {
        "HEADS": f"CAMP_HEAD={SOURCE_HEAD}\nCAMP_ORIGIN_MAIN={SOURCE_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "training execution\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
        "static_camp_weights_model.json": json.dumps(source["static_camp_model"], sort_keys=True) + "\n",
        "scaleup_training_config.json": "{}\n",
        "scaleup_training_timing.json": "{}\n",
        "scaleup_training_timing.md": "# Timing\n",
        "scaleup_training.log": "{}\n",
        "training_log.jsonl": "{}\n",
    }.items():
        _write(artifact / name, text)
    _rewrite_manifest(artifact, module.REQUIRED_SOURCE_FILES)
    return {
        "source_artifact_dir": artifact,
        "source_summary_json": artifact / module.SOURCE_JSON_NAME,
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


def _source_payload(module, *, holdout_used: int) -> dict:
    weights = [
        0.1111668017583095,
        0.1111863821117415,
        0.11118261092321463,
        0.11112277680118221,
        0.11106111863252109,
        0.11106111863252109,
        0.11106111863252109,
        0.1110614747724733,
        0.11109659773551553,
    ]
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "heads": {
            "camp_head": SOURCE_HEAD,
            "camp_origin_main": SOURCE_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "scaleup_training_execution": {
            "train_records": 6263,
            "calibration_records": 2156,
            "holdout_records": 1581,
            "calibration_records_used_for_training": 0,
            "holdout_records_used_for_training": holdout_used,
            "record_summary": {
                "scene_zero_overlap": True,
                "sample_zero_overlap": True,
                "train_k_values": [8],
                "train_candidate_count_values": [8],
                "train_candidate_tensor_mutated_count": 0,
                "train_closed_loop_outcome_count": 0,
            },
            "atom_summary": {
                "atom_count": 9,
                "atom_schema_version": "camp_legacy_v1_9d",
                "canonical_schema": True,
            },
            "score_expression": module.SCORE_EXPRESSION,
            "training_executed": True,
            "training_start": "2026-07-09T08:08:03.793066+00:00",
            "training_end": "2026-07-09T08:08:05.128274+00:00",
            "offline_training_wall_clock_seconds": 1.335207,
        },
        "static_camp_model": {
            "atom_count": 9,
            "atom_schema_version": "camp_legacy_v1_9d",
            "approved_atoms_only": True,
            "score_expression": module.SCORE_EXPRESSION,
            "weights": weights,
            "weights_max": max(weights),
            "weights_min": min(weights),
            "weights_nonnegative": True,
            "weights_sum": 1.0,
            "weights_sum_to_one": True,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "training_executed": True,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
            "closed_loop_outcomes_used_for_training": False,
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rewrite_manifest(path: Path, files: tuple[str, ...]) -> None:
    sha_path = path / "SHA256SUMS"
    rows = []
    for name in files:
        if name in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            continue
        rows.append(f"{_sha256(path / name)}  {name}\n")
    sha_path.write_text("".join(rows), encoding="utf-8")
    (path / "ROOT_SHA256SUMS").write_text(f"{SOURCE_ROOT_SHA}  SHA256SUMS\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
