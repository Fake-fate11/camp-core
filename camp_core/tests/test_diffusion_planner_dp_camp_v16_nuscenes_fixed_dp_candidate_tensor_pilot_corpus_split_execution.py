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
    / "split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus.py"
)
HEAD = "28a0bce0f4dc8db8534024fdca82f52671a03d20"
PILOT_ROOT_SHA = "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432"
BLOCKER_ROOT_SHA = "2b9f7e5182b76d49bb506aab1f614d22be7caa684f371021307e96eeb37e9594"
REMEDIATION_ROOT_SHA = "0a56b12cc11549868337decf07ae3c1af497a8c04c2c9880f25e5683af897111"
REVIEW_ROOT_SHA = "6c00f75285d8fd73a72246fb2e57d614b500e0b423b38a8c8db865ca27f7e8d3"
ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_"
    "f24e3e1e_20260708T085439CST"
)
SPLIT_CAMP_HEAD = "f24e3e1ea229b675f0b4e6ffcbbb6f04be412c39"
JSON_SHA = "531ecfe7c81ee57bcf33b7bcc5d72e529434724c1f13293037cc9fa8f78133c6"
MD_SHA = "cda40525111c26cdb9da15c01f964f2a256a80b3add6c010d782823e02ee729e"
MANIFEST_SHA = "53d75c7baf762baf6a68ce4f62fb47e6d7a8f676dcf258a4b966b6c78146798e"
TRAIN_JSONL_SHA = "007bd97b8e3c959d31b4023b9c9f1feb655a5c6b42b0fbb8323cccc5d9cb516a"
CALIBRATION_JSONL_SHA = "77a3500af1111d8daec9592be882c412f265a1021c5648d10dd3282f1d227e4e"
HOLDOUT_JSONL_SHA = "7677a53cfed9798f9107053f61e282b7076af6c88316524f4f80d9fd000c275e"
SHA256SUMS_SHA = "18f1231c1c50841bde09527066f7845fe6b101c9978bf490457d8ce6c1867878"
ROOT_SHA256SUMS_SHA = "c3cb4c3e863c87ae1904eeeb707d0772ae47d870ca1584e005c733ec91771926"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_corpus_split_execution", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_corpus_split_execution_writes_scene_level_manifests(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    split = report["split_execution"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["split_execution_executed"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert split["split_policy"] == "scene_level_greedy_imbalance_tolerant_smoke_split"
    assert split["pilot_split_classification"] == "imbalance_tolerant_smoke_split"
    assert split["performance_claim_supported"] is False
    assert split["record_level_hard_split_executed"] is False
    assert split["counts"] == {"calibration": 14, "holdout": 147, "train": 863}
    assert split["scene_assignments"] == {
        "calibration": ["scene-0061"],
        "holdout": ["scene-0757"],
        "train": ["scene-0553", "scene-0655"],
    }
    assert split["scene_zero_overlap"] is True
    assert split["sample_zero_overlap"] is True
    assert split["k_values"] == [8]
    assert split["candidate_count_values"] == [8]
    assert split["dp_head_values"] == [module.FIXED_DP_HEAD]
    assert split["candidate_tensor_mutated_count"] == 0
    assert _line_count(fixture["output_dir"] / module.SPLIT_JSONL_NAMES["train"]) == 863
    assert _line_count(fixture["output_dir"] / module.SPLIT_JSONL_NAMES["calibration"]) == 14
    assert _line_count(fixture["output_dir"] / module.SPLIT_JSONL_NAMES["holdout"]) == 147
    assert (fixture["output_dir"] / module.REPORT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REPORT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_corpus_split_execution_rejects_bad_k(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, bad_k=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "records_all_k_8" in report["final_decision"]["failed_checks"]


def test_v16_pilot_corpus_split_execution_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    for text in (audit, status):
        assert ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_camp_head={SPLIT_CAMP_HEAD}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_check_count=46" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_train_records=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_calibration_records=14" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_holdout_records=147" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_sample_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_k_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_candidate_count_values=[8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_candidate_tensor_mutated_count=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_execution_performance_claim_supported=False" in text
        assert JSON_SHA in text
        assert MD_SHA in text
        assert MANIFEST_SHA in text
        assert TRAIN_JSONL_SHA in text
        assert CALIBRATION_JSONL_SHA in text
        assert HOLDOUT_JSONL_SHA in text
        assert SHA256SUMS_SHA in text
        assert ROOT_SHA256SUMS_SHA in text
        assert PILOT_ROOT_SHA in text
        assert BLOCKER_ROOT_SHA in text
        assert REMEDIATION_ROOT_SHA in text
        assert REVIEW_ROOT_SHA in text


def _write_fixture(tmp_path: Path, module, bad_k: bool = False) -> dict:
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
    pilot = _artifact(tmp_path / "pilot", PILOT_ROOT_SHA)
    records = pilot / "records.jsonl"
    _write_records(records, module, bad_k=bad_k)
    _rewrite_manifest(pilot)
    blocker = _artifact(tmp_path / "blocker", BLOCKER_ROOT_SHA)
    remediation = _artifact(tmp_path / "remediation", REMEDIATION_ROOT_SHA)
    review = _artifact(tmp_path / "review", REVIEW_ROOT_SHA)
    remediation_json = remediation / module.REMEDIATION_JSON_NAME
    review_json = review / module.REMEDIATION_REVIEW_JSON_NAME
    _write_json(remediation_json, _remediation_payload(module))
    _write_json(review_json, _review_payload(module))
    _rewrite_manifest(remediation)
    _rewrite_manifest(review)
    return {
        "pilot_corpus_artifact_dir": pilot,
        "pilot_records_jsonl": records,
        "pilot_corpus_sha256s": pilot / "SHA256SUMS",
        "pilot_corpus_root_sha256s": pilot / "ROOT_SHA256SUMS",
        "split_blocker_artifact_dir": blocker,
        "split_blocker_sha256s": blocker / "SHA256SUMS",
        "split_blocker_root_sha256s": blocker / "ROOT_SHA256SUMS",
        "remediation_artifact_dir": remediation,
        "remediation_json": remediation_json,
        "remediation_sha256s": remediation / "SHA256SUMS",
        "remediation_root_sha256s": remediation / "ROOT_SHA256SUMS",
        "remediation_review_artifact_dir": review,
        "remediation_review_json": review_json,
        "remediation_review_sha256s": review / "SHA256SUMS",
        "remediation_review_root_sha256s": review / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_pilot_corpus_root_sha256": PILOT_ROOT_SHA,
        "expected_split_blocker_root_sha256": BLOCKER_ROOT_SHA,
        "expected_remediation_root_sha256": REMEDIATION_ROOT_SHA,
        "expected_remediation_review_root_sha256": REVIEW_ROOT_SHA,
        "enabled": True,
    }


def _remediation_payload(module) -> dict:
    return {
        "schema_version": module.REMEDIATION_SCHEMA_VERSION,
        "status": module.REMEDIATION_READY_STATUS,
        "authorized_next_work": module.SOURCE_CURRENT_WORK,
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
            "split_execution_executed": False,
            "training_executed": False,
        },
        "remediation_plan": _split_plan(module),
    }


def _review_payload(module) -> dict:
    return {
        "schema_version": module.REMEDIATION_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "candidate_generation_executed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "split_execution_executed": False,
            "training_executed": False,
        },
        "remediation_review": _split_plan(module),
    }


def _split_plan(module) -> dict:
    return {
        "actual_record_counts": {"calibration": 14, "holdout": 147, "train": 863},
        "actual_record_ratios": {
            "calibration": 0.013671875,
            "holdout": 0.1435546875,
            "train": 0.8427734375,
        },
        "pilot_split_classification": "imbalance_tolerant_smoke_split",
        "record_level_split_executed": False,
        "sample_zero_overlap": True,
        "scene_assignments": module.EXPECTED_ASSIGNMENTS,
        "scene_zero_overlap": True,
        "split_policy": "scene_level_greedy_imbalance_tolerant_smoke_split",
        "split_unit": "scene_id",
    }


def _write_records(path: Path, module, bad_k: bool) -> None:
    index = 0
    with path.open("w", encoding="utf-8") as handle:
        for scene, count in {
            "scene-0553": 495,
            "scene-0655": 368,
            "scene-0757": 147,
            "scene-0061": 14,
        }.items():
            for _ in range(count):
                k = 7 if bad_k and index == 0 else 8
                record = {
                    "CAMP_HEAD": HEAD,
                    "DP_HEAD": module.FIXED_DP_HEAD,
                    "K": k,
                    "candidate_count": k,
                    "candidate_tensor_post_sha256": f"tensor-{index}",
                    "candidate_tensor_pre_sha256": f"tensor-{index}",
                    "candidate_tensor_sha256": f"tensor-{index}",
                    "candidate_tensor_unchanged_by_camp": True,
                    "record_index": index,
                    "sample_id": f"{scene}_{index:06d}",
                    "scene_id": scene,
                }
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                index += 1


def _artifact(path: Path, root_sha: str) -> Path:
    path.mkdir(parents=True)
    _write(path / "HEADS", f"CAMP_HEAD={HEAD}\n")
    _write(path / "COMMAND", "fixture\n")
    _write(path / "stdout.txt", "")
    _write(path / "stderr.txt", "")
    _write(path / "run.exit", "0\n")
    _rewrite_manifest(path)
    _write(path / "ROOT_SHA256SUMS", f"{root_sha}  {path.name}\n")
    return path


def _rewrite_manifest(path: Path) -> None:
    rows = []
    for item in sorted(path.iterdir()):
        if item.name in {"SHA256SUMS", "ROOT_SHA256SUMS"} or not item.is_file():
            continue
        rows.append(f"{_sha256(item)}  {item.name}\n")
    _write(path / "SHA256SUMS", "".join(rows))


def _line_count(path: Path) -> int:
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
