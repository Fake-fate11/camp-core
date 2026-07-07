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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation.py"
)
HEAD = "16f24ca9d59b6d905db72aad235111f966d0500d"
BLOCKER_ROOT_SHA = "2b9f7e5182b76d49bb506aab1f614d22be7caa684f371021307e96eeb37e9594"
BLOCKER_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_blocker_"
    "scene_granularity_15ca0298_20260708T034152CST"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_corpus_split_remediation", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_corpus_split_remediation_plans_scene_level_smoke_split(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["remediation_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["split_plan_remediation_only"] is True
    assert decision["split_execution_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert plan["split_policy"] == "scene_level_greedy_imbalance_tolerant_smoke_split"
    assert plan["split_unit"] == "scene_id"
    assert plan["exact_record_count_targets_rejected"] is True
    assert plan["record_level_split_executed"] is False
    assert plan["scene_zero_overlap"] is True
    assert plan["sample_zero_overlap"] is True
    assert plan["scene_counts"] == {
        "scene-0061": 14,
        "scene-0553": 495,
        "scene-0655": 368,
        "scene-0757": 147,
    }
    assert plan["scene_assignments"] == {
        "calibration": ["scene-0061"],
        "holdout": ["scene-0757"],
        "train": ["scene-0553", "scene-0655"],
    }
    assert plan["actual_record_counts"] == {"calibration": 14, "holdout": 147, "train": 863}
    assert plan["actual_record_ratios"] == {
        "calibration": 0.013671875,
        "holdout": 0.1435546875,
        "train": 0.8427734375,
    }
    assert plan["larger_corpus_preconditions"] == {
        "minimum_scene_count_before_ratio_tracking": 30,
        "near_60_20_20_requires_scene_count_at_least": 30,
        "ten_k_generation_must_increase_scene_diversity": True,
    }
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_corpus_split_remediation_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_split_remediation" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, next_work: str | None = None) -> dict:
    artifact = tmp_path / "split_execution_blocker"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_json = artifact / module.SOURCE_JSON_NAME
    _write_json(source_json, _source_payload(module))
    records = tmp_path / "records.jsonl"
    _write_records(records)
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "read-only blocker probe\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
        module.SOURCE_MD_NAME: "# Split Execution Blocker\n",
    }.items():
        _write(artifact / name, content)
    sha_names = (
        module.SOURCE_JSON_NAME,
        module.SOURCE_MD_NAME,
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
    )
    _write(
        artifact / "SHA256SUMS",
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
    )
    _write(artifact / "ROOT_SHA256SUMS", f"{BLOCKER_ROOT_SHA}  {artifact.name}\n")
    return {
        "source_blocker_artifact_dir": artifact,
        "source_blocker_json": source_json,
        "source_blocker_sha256s": artifact / "SHA256SUMS",
        "source_blocker_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "candidate_records_jsonl": records,
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_blocker_root_sha256": BLOCKER_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module) -> dict:
    return {
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "camp_head": "15ca029874b2f84331e54543351db76bd88760fb",
        "camp_origin_main": "15ca029874b2f84331e54543351db76bd88760fb",
        "candidate_generation_executed": False,
        "candidate_records_jsonl": "/root/autodl-tmp/records.jsonl",
        "candidate_tensor_modified": False,
        "current_work": "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_train_calibration_holdout_split_execution_only",
        "dp_head": module.FIXED_DP_HEAD,
        "dp_modified": False,
        "duplicate_sample_count": 0,
        "paired_evaluation_executed": False,
        "possible_scene_subset_record_counts": [
            0,
            14,
            147,
            161,
            368,
            382,
            495,
            509,
            515,
            529,
            642,
            656,
            863,
            877,
            1010,
            1024,
        ],
        "record_count": 1024,
        "record_level_exact_split_would_violate_scene_zero_overlap": True,
        "scene_record_counts_desc": [495, 368, 147, 14],
        "scene_zero_overlap_exact_614_205_205_executable": False,
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "source_preflight_artifact": "/root/autodl-tmp/preflight",
        "split_execution_executed": False,
        "status": module.SOURCE_READY_STATUS,
        "stop_condition": "train_calibration_holdout_scene_zero_overlap_conflicts_with_target_record_counts",
        "target_counts_reachable_with_scene_zero_overlap": False,
        "target_record_counts": {"calibration": 205, "holdout": 205, "train": 614},
        "training_executed": False,
        "unique_sample_count": 1024,
        "unique_scene_count": 4,
    }


def _write_records(path: Path) -> None:
    scenes = [
        ("scene-0553", 495),
        ("scene-0655", 368),
        ("scene-0757", 147),
        ("scene-0061", 14),
    ]
    index = 0
    with path.open("w", encoding="utf-8") as handle:
        for scene, count in scenes:
            for _ in range(count):
                record = {"scene_id": scene, "sample_id": f"sample-{index:04d}"}
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                index += 1


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
