from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_plan_static_contract.py"
)
HEAD = "a33ba395914179fd849faeb61ee0b6e4f886fdba"
PLAN_ROOT_SHA = "0ca5ff5106f79a2faff9651f3c6c59f9fedc74f2c87db984f3d0fe78e806fff5"
SMOKE_ROOT_SHA = "55a55c99b65ddc24b816f60ad886c7044b3fedf60f5e0be4aa84a9df972b487f"
REVIEW_ROOT_SHA = "a0247461cf7870ab1cd124b2da680e7a63f9bf72646b1c8ce1de2a08e521625c"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_candidate_tensor_pilot_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_candidate_tensor_pilot_generation_plan_static_review_passes(
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
    assert decision["static_review_only"] is True
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert report["plan_review"]["source_plan_root_sha256"] == fixture["expected_plan_root_sha256"]
    assert report["plan_review"]["selected_target_records"] == 1024
    assert report["plan_review"]["k"] == 8
    assert report["plan_review"]["candidate_count"] == 8
    assert report["plan_review"]["per_record_mean_seconds"] == 5.31974
    assert report["plan_review"]["wall_clock_hours_1024"] == 1.51317
    assert report["plan_review"]["source_smoke_artifact"].endswith("smoke_execution_retry")
    assert report["plan_review"]["source_review_artifact"].endswith("smoke_execution_result_review")
    assert "JSONL records" in report["plan_review"]["output_contract"]
    assert "records == target_records" in report["plan_review"]["pass_conditions"]
    assert "DP HEAD mismatch" in report["plan_review"]["stop_conditions"]
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_candidate_tensor_pilot_generation_plan_static_review_requires_enable(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["enabled"] = False

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "static_review_enabled" in report["final_decision"]["failed_checks"]


def test_v16_candidate_tensor_pilot_generation_plan_static_review_rejects_wrong_target(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, selected_target_records=2048)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "plan_selected_target_records_1024" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    selected_target_records: int = 1024,
) -> dict:
    plan = module.PLAN_MODULE
    artifact = tmp_path / "pilot_generation_plan"
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
    v16_audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_json = artifact / plan.PLAN_JSON_NAME
    source_md = artifact / plan.PLAN_MD_NAME
    _write_json(source_json, _source_payload(module, selected_target_records=selected_target_records))
    _write(source_md, "# Pilot Generation Plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run pilot generation plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    sha_names = (
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
        plan.PLAN_JSON_NAME,
        plan.PLAN_MD_NAME,
    )
    sha_path = _write(
        artifact / "SHA256SUMS",
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
    )
    return {
        "source_plan_artifact_dir": artifact,
        "source_plan_json": source_json,
        "source_plan_md": source_md,
        "source_plan_sha256s": artifact / "SHA256SUMS",
        "v16_audit_md": v16_audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": _sha256(sha_path),
        "enabled": True,
    }


def _source_payload(module, *, selected_target_records: int) -> dict:
    plan = module.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
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
        "inputs": {
            "source_smoke_review_artifact": "/root/autodl-tmp/smoke_execution_result_review",
            "exporter_script": plan.EXPORTER_SCRIPT,
            "nuscenes_source_root": plan.NUSCENES_SOURCE_ROOT,
            "dp_fixed_head": module.FIXED_DP_HEAD,
        },
        "source_artifacts": {
            "smoke_artifact": "/root/autodl-tmp/smoke_execution_retry",
            "smoke_root_sha256": SMOKE_ROOT_SHA,
            "source_smoke_review_artifact": "/root/autodl-tmp/smoke_execution_result_review",
            "review_root_sha256": REVIEW_ROOT_SHA,
        },
        "pilot_plan": {
            "selected_target_records": selected_target_records,
            "alternate_target_records": 2048,
            "k": 8,
            "candidate_count": 8,
            "plan_only": True,
        },
        "timing_estimates": {
            "1024": {
                "target_records": 1024,
                "per_record_mean_seconds": 5.31974,
                "wall_clock_seconds": 5447.41376,
                "wall_clock_hours": 1.51317,
            }
        },
        "outputs": [
            "JSON summary",
            "JSONL records",
            "candidate tensor hashes",
            "HEADS",
            "COMMAND",
            "stdout",
            "stderr",
            "SHA256SUMS",
        ],
        "pass_conditions": [
            "records == target_records",
            "K == 8",
            "candidate_count == 8",
            "DP_HEAD fixed",
            "failure_count == 0",
            "all dp_top1_index in [0,7]",
            "all candidate_tensor_sha256 present",
        ],
        "stop_conditions": [
            "output root exists",
            "DP HEAD mismatch",
            "records shortfall",
            "any fake/synthetic candidate tensor",
            "any DP/candidate/trajectory mutation",
        ],
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
