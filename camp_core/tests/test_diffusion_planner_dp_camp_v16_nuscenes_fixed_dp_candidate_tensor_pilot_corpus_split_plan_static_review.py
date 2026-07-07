from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_contract.py"
)
HEAD = "c19026cec7f610a38fde0c4e615a71840222781e"
PLAN_ROOT_SHA = "0d76e240e8a77579afb7c95af26fcd542c6beb6f7c533a7b7e04169fbfe4735d"
ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_"
    "6c1fcb35_20260708T033308CST"
)
REVIEW_CAMP_HEAD = "6c1fcb35e4ffaff7945eb66e5887edc7d9df7e5e"
JSON_SHA = "3458e762feb66b3e27dd9b6d34e4f6122843d299b094b56737cf31974451c0a3"
MD_SHA = "3fdbc2a9b08b1d3954a822eec8417da67836d95c89b1df7963f51def87af9bc0"
SHA256SUMS_SHA = "78170cd33e6aad01836368507340285af5398ba040453773e4edf13e0959367a"
ROOT_SHA256SUMS_SHA = "1b4663b2a96127b34508833a3d03c7b152f865b2426d5bd696c389c2abb77458"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_corpus_split_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_corpus_split_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["plan_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["records"] == 1024
    assert review["target_record_counts"] == {"calibration": 205, "holdout": 205, "train": 614}
    assert review["split_unit"] == "scene_id_primary_sample_id_fallback"
    assert review["scene_overlap_allowed"] is False
    assert review["sample_overlap_allowed"] is False
    assert review["candidate_tensor_sha_overlap_allowed"] is False
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_corpus_split_plan_static_review_rejects_bad_holdout(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, holdout_records=0)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "split_holdout_records_205" in report["final_decision"]["failed_checks"]


def test_v16_pilot_corpus_split_plan_static_review_is_recorded() -> None:
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
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_records=1024" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_train_records=614" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_calibration_records=205" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_holdout_records=205" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_check_count=47" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_failed_checks=[]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_plan_static_review_camp_head={REVIEW_CAMP_HEAD}" in text
        assert JSON_SHA in text
        assert MD_SHA in text
        assert SHA256SUMS_SHA in text
        assert ROOT_SHA256SUMS_SHA in text
        assert PLAN_ROOT_SHA in text


def _write_fixture(tmp_path: Path, module, *, holdout_records: int = 205) -> dict:
    plan = module.PLAN_MODULE
    artifact = tmp_path / "split_plan"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_text = "\n".join(
        [
            f"current_v16_status={plan.READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_json = artifact / plan.PLAN_JSON_NAME
    source_md = artifact / plan.PLAN_MD_NAME
    _write_json(source_json, _source_payload(module, holdout_records=holdout_records))
    _write(source_md, "# Split Plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run split plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    sha_names = (
        plan.PLAN_JSON_NAME,
        plan.PLAN_MD_NAME,
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
    _write(artifact / "ROOT_SHA256SUMS", f"{PLAN_ROOT_SHA}  {artifact.name}\n")
    return {
        "source_plan_artifact_dir": artifact,
        "source_plan_json": source_json,
        "source_plan_md": source_md,
        "source_plan_sha256s": artifact / "SHA256SUMS",
        "source_plan_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module, *, holdout_records: int) -> dict:
    plan = module.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": plan.READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "split_plan_only": True,
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
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "source_result_review_artifact": {
            "path": "/root/autodl-tmp/result_review",
            "root_sha256": "bcb25cbc189c274845d94bc7963c683fd88c523be8243356f37481bae933d99e",
            "pilot_execution_root_sha256": "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432",
        },
        "split_plan": {
            "source_records": 1024,
            "ratios": {"calibration": 0.2, "holdout": 0.2, "train": 0.6},
            "target_record_counts": {
                "calibration": 205,
                "holdout": holdout_records,
                "train": 614,
            },
            "assignment_policy": {
                "split_unit": "scene_id_primary_sample_id_fallback",
                "stable_sort_key": "sha256(split_salt + scene_id_or_sample_id)",
            },
            "zero_overlap_requirements": {
                "scene_overlap_allowed": False,
                "sample_overlap_allowed": False,
                "candidate_tensor_sha_overlap_allowed": False,
                "adapter_input_sha_overlap_allowed": False,
                "record_identity_overlap_allowed": False,
            },
            "holdout_policy": {
                "training_from_holdout_authorized": False,
                "calibration_from_holdout_authorized": False,
            },
            "expansion_preconditions": {
                "10k": ["pilot_split_execution_result_review_passed"],
                "32k": ["10k_corpus_result_review_passed"],
            },
        },
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
