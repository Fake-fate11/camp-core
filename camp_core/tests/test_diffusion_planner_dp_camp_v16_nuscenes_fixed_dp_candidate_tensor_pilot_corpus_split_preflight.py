from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split.py"
)
HEAD = "2754def965f99a2bfce568504a5b30d3f6e839e2"
STATIC_REVIEW_ROOT_SHA = "78170cd33e6aad01836368507340285af5398ba040453773e4edf13e0959367a"
SOURCE_PLAN_ROOT_SHA = "0d76e240e8a77579afb7c95af26fcd542c6beb6f7c533a7b7e04169fbfe4735d"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_corpus_split_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_corpus_split_preflight_constructs_execution_contract(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    preflight = report["preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["preflight_only"] is True
    assert decision["split_execution_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert preflight["records"] == 1024
    assert preflight["target_record_counts"] == {"calibration": 205, "holdout": 205, "train": 614}
    assert preflight["execution_command"][0].endswith("split_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus.py")
    assert preflight["output_contract"] == [
        "JSON summary",
        "split manifests",
        "identity overlap report",
        "HEADS",
        "COMMAND",
        "stdout",
        "stderr",
        "SHA256SUMS",
    ]
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_corpus_split_preflight_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_split_preflight" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, next_work: str | None = None) -> dict:
    artifact = tmp_path / "split_plan_static_review"
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
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run static review\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
        module.SOURCE_MD_NAME: "# Static Review\n",
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
    _write(artifact / "ROOT_SHA256SUMS", f"{STATIC_REVIEW_ROOT_SHA}  {artifact.name}\n")
    return {
        "source_static_review_artifact_dir": artifact,
        "source_static_review_json": source_json,
        "source_static_review_sha256s": artifact / "SHA256SUMS",
        "source_static_review_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "candidate_records_jsonl": tmp_path / "records.jsonl",
        "enabled": True,
    }


def _source_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_plan_artifact": "/root/autodl-tmp/split_plan",
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "plan_review": {
            "source_plan_root_sha256": SOURCE_PLAN_ROOT_SHA,
            "records": 1024,
            "ratios": {"calibration": 0.2, "holdout": 0.2, "train": 0.6},
            "target_record_counts": {"calibration": 205, "holdout": 205, "train": 614},
            "split_unit": "scene_id_primary_sample_id_fallback",
            "scene_overlap_allowed": False,
            "sample_overlap_allowed": False,
            "candidate_tensor_sha_overlap_allowed": False,
            "adapter_input_sha_overlap_allowed": False,
            "training_from_holdout_authorized": False,
            "calibration_from_holdout_authorized": False,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "static_review_only": True,
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


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()
