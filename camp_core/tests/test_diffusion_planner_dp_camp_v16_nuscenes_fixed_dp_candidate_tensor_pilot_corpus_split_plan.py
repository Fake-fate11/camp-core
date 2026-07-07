from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split.py"
)
HEAD = "b4a79adcd5deb1d295c27e404a88e05aad5799d2"
SOURCE_ROOT_SHA = "bcb25cbc189c274845d94bc7963c683fd88c523be8243356f37481bae933d99e"
PILOT_EXECUTION_ROOT_SHA = "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432"
ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_"
    "00653896_20260708T032727CST"
)
PLAN_CAMP_HEAD = "00653896db1b02d2e9203203954452896184b2bb"
JSON_SHA = "bbbac4162e442e4f1f6d6e44288293ae06001bc4030d14aea91a9e75ac5d2a2e"
MD_SHA = "aa5302ed5a5e39c29389e865b598baa47bec0561caf8a8b5671ac011fcce5237"
SHA256SUMS_SHA = "0d76e240e8a77579afb7c95af26fcd542c6beb6f7c533a7b7e04169fbfe4735d"
ROOT_SHA256SUMS_SHA = "292fdd3692dc2d2985941508546b96ed4be1ab14c583c8603732e6e97b85b9fa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_corpus_split_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_corpus_split_plan_defines_zero_overlap_policy(tmp_path: Path) -> None:
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
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert split["source_records"] == 1024
    assert split["ratios"] == {"calibration": 0.2, "holdout": 0.2, "train": 0.6}
    assert split["target_record_counts"] == {"calibration": 205, "holdout": 205, "train": 614}
    assert split["assignment_policy"]["split_unit"] == "scene_id_primary_sample_id_fallback"
    assert split["zero_overlap_requirements"]["scene_overlap_allowed"] is False
    assert split["zero_overlap_requirements"]["sample_overlap_allowed"] is False
    assert split["zero_overlap_requirements"]["candidate_tensor_sha_overlap_allowed"] is False
    assert split["holdout_policy"]["training_from_holdout_authorized"] is False
    assert "pilot_split_execution_result_review_passed" in split["expansion_preconditions"]["10k"]
    assert "10k_corpus_result_review_passed" in split["expansion_preconditions"]["32k"]
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_corpus_split_plan_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_split_plan" in report["final_decision"]["failed_checks"]


def test_v16_pilot_corpus_split_plan_cli_writes_outputs(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    assert module.main(_argv(fixture, module)) == 0
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_corpus_split_plan_is_recorded() -> None:
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
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_records=1024" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_train_records=614" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_calibration_records=205" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_holdout_records=205" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_check_count=34" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_failed_checks=[]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_camp_head={PLAN_CAMP_HEAD}" in text
        assert JSON_SHA in text
        assert MD_SHA in text
        assert SHA256SUMS_SHA in text
        assert ROOT_SHA256SUMS_SHA in text
        assert SOURCE_ROOT_SHA in text
        assert PILOT_EXECUTION_ROOT_SHA in text


def _write_fixture(tmp_path: Path, module, next_work: str | None = None) -> dict:
    artifact = tmp_path / "pilot_result_review"
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
    _write_json(source_json, _source_payload(module, artifact))
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run result review\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
        module.SOURCE_MD_NAME: "# Result Review\n",
    }.items():
        _write(artifact / name, content)
    sha_names = (
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
        module.SOURCE_JSON_NAME,
        module.SOURCE_MD_NAME,
    )
    _write(
        artifact / "SHA256SUMS",
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
    )
    _write(artifact / "ROOT_SHA256SUMS", f"{SOURCE_ROOT_SHA}  {artifact.name}\n")
    return {
        "source_result_review_artifact_dir": artifact,
        "source_result_review_json": source_json,
        "source_result_review_sha256s": artifact / "SHA256SUMS",
        "source_result_review_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "enabled": True,
    }


def _argv(fixture: dict, module) -> list[str]:
    return [
        "--source_result_review_artifact_dir",
        str(fixture["source_result_review_artifact_dir"]),
        "--source_result_review_json",
        str(fixture["source_result_review_json"]),
        "--source_result_review_sha256s",
        str(fixture["source_result_review_sha256s"]),
        "--source_result_review_root_sha256s",
        str(fixture["source_result_review_root_sha256s"]),
        "--v16_audit_md",
        str(fixture["v16_audit_md"]),
        "--current_status_md",
        str(fixture["current_status_md"]),
        "--output_dir",
        str(fixture["output_dir"]),
        "--current_camp_head",
        fixture["current_camp_head"],
        "--current_camp_origin_main",
        fixture["current_camp_origin_main"],
        "--current_dp_head",
        module.FIXED_DP_HEAD,
        "--expected_source_root_sha256",
        fixture["expected_source_root_sha256"],
        "--enable_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan",
    ]


def _source_payload(module, artifact: Path) -> dict:
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_artifact": {
            "path": "/root/autodl-tmp/pilot_generation_execution",
            "root_sha256": PILOT_EXECUTION_ROOT_SHA,
            "expected_root_sha256": PILOT_EXECUTION_ROOT_SHA,
            "sha256_entry_count": 4105,
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_camp_head": "d799ada87f9ac384f08c978c40282771e024a9d2",
        },
        "record_review": {
            "record_count": 1024,
            "candidate_count_values": [8],
            "candidate_tensor_shapes": [[8, 80, 4]],
            "candidate_tensor_mutated_count": 0,
            "dp_heads": [module.FIXED_DP_HEAD],
            "exporter_failure_count": 0,
            "failure_count": 0,
            "k_values": [8],
            "missing_adapter_input_sha256": 0,
            "missing_adapter_input_shape": 0,
            "missing_candidate_tensor_sha256": 0,
            "missing_scene_or_sample_id": 0,
            "top1_out_of_range": 0,
            "top1_values": [0],
        },
        "timing_summary": {
            "source_wall_clock_seconds": 5516.609977,
            "failure_count": 0,
            "per_record_seconds": {"count": 1024, "min": 4.874985, "mean": 5.002971, "max": 5.16236},
        },
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
        "source_artifact_path_for_fixture": str(artifact),
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
