from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation.py"
)
HEAD = "319df88ec876aa7e3c392dbeb824a06fce6f2c2b"
SMOKE_ROOT_SHA = "55a55c99b65ddc24b816f60ad886c7044b3fedf60f5e0be4aa84a9df972b487f"
REVIEW_ROOT_SHA = "a0247461cf7870ab1cd124b2da680e7a63f9bf72646b1c8ce1de2a08e521625c"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_candidate_tensor_pilot_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_candidate_tensor_pilot_generation_plan_prefers_1024_records(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["dp_modified"] is False
    assert report["pilot_plan"]["selected_target_records"] == 1024
    assert report["pilot_plan"]["alternate_target_records"] == 2048
    assert report["timing_estimates"]["1024"]["wall_clock_hours"] == 1.51317
    assert report["timing_estimates"]["2048"]["wall_clock_hours"] == 3.026341
    assert report["inputs"]["source_smoke_review_artifact"] == str(
        fixture["source_review_artifact_dir"].resolve()
    )
    assert report["inputs"]["exporter_script"].endswith(
        "run_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_exporter.py"
    )
    assert report["inputs"]["nuscenes_source_root"] == "/autodl-pub/data/nuScenes"
    assert report["inputs"]["dp_fixed_head"] == module.FIXED_DP_HEAD
    assert "records == target_records" in report["pass_conditions"]
    assert "avoid duplicate sample ids within pilot" in report["split_provenance_requirements"]
    assert "output root exists" in report["stop_conditions"]
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_candidate_tensor_pilot_generation_plan_rejects_wrong_eof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_pilot_plan" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, next_work: str | None = None) -> dict:
    smoke_artifact = tmp_path / "smoke_retry"
    review_artifact = tmp_path / "smoke_result_review"
    smoke_artifact.mkdir()
    review_artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    _write(smoke_artifact / "ROOT_SHA256SUMS", f"{SMOKE_ROOT_SHA}  {smoke_artifact.name}\n")
    _write(review_artifact / "ROOT_SHA256SUMS", f"{REVIEW_ROOT_SHA}  {review_artifact.name}\n")
    review_json = review_artifact / module.SOURCE_REVIEW_JSON_NAME
    _write_json(
        review_json,
        {
            "schema_version": module.SOURCE_REVIEW_SCHEMA_VERSION,
            "status": module.SOURCE_READY_STATUS,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "source_artifact": {"root_sha256": SMOKE_ROOT_SHA, "path": str(smoke_artifact)},
            "record_review": {
                "record_count": 256,
                "candidate_count_values": [8],
                "k_values": [8],
                "dp_heads": [module.FIXED_DP_HEAD],
                "failure_count": 0,
            },
            "timing_summary": {
                "source_wall_clock_seconds": 1498.016563,
                "per_record_seconds": {"count": 256, "min": 5.084872, "mean": 5.31974, "max": 5.836636},
            },
            "final_decision": {
                "passed": True,
                "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
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
        },
    )
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run result review\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
    }.items():
        _write(review_artifact / name, text)
    sha_names = [
        module.SOURCE_REVIEW_JSON_NAME,
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
    ]
    _write(
        review_artifact / "SHA256SUMS",
        "".join(f"{_sha256(review_artifact / name)}  {name}\n" for name in sha_names),
    )
    return {
        "source_smoke_artifact_dir": smoke_artifact,
        "source_smoke_root_sha256s": smoke_artifact / "ROOT_SHA256SUMS",
        "source_review_artifact_dir": review_artifact,
        "source_review_json": review_json,
        "source_review_sha256s": review_artifact / "SHA256SUMS",
        "source_review_root_sha256s": review_artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_smoke_root_sha256": SMOKE_ROOT_SHA,
        "expected_review_root_sha256": REVIEW_ROOT_SHA,
        "enabled": True,
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
