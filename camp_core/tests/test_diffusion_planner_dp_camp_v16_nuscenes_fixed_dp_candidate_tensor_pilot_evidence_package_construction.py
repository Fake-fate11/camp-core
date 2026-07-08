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
    / "construct_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package.py"
)
HEAD = "fef60332af591f1931ff14ace32d1c7e21bb2964"
PLAN_ROOT_SHA = "93dbc0808e95c93d5ac3e73a97e6beaec1917219a98c7faaa21dbe4b7b6dbe0c"
STATIC_REVIEW_ROOT_SHA = "d235ad058fc9471575cf9f98cd3e7edc2c95a55b716212cfc591cebbb4e15f23"
SOURCE_IDS = [
    "smoke_corpus_generation",
    "smoke_corpus_generation_review",
    "pilot_corpus_generation",
    "pilot_corpus_generation_review",
    "split_execution",
    "split_result_review",
    "training_execution",
    "training_result_review",
    "paired_evaluation_execution",
    "paired_evaluation_result_review",
]


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_evidence_package_construction", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_evidence_package_construction_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    manifest = report["package_manifest"]
    source_index = report["source_index"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evidence_package_constructed"] is True
    assert decision["evidence_package_constructed_by_this_gate"] is True
    assert decision["scale_up_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert manifest["source_artifact_count"] == 10
    assert [item["id"] for item in source_index["source_artifacts"]] == SOURCE_IDS
    assert all(item["sha256s_verified"] for item in source_index["source_artifacts"])
    assert all(item["root_matches_expected"] for item in source_index["source_artifacts"])
    assert manifest["no_claim_boundary"] == {
        "calibration_rows": 14,
        "holdout_rows": 147,
        "no_camp_over_dp_claim": True,
        "no_performance_claim": True,
        "no_promotion_or_deployment": True,
        "no_safety_claim": True,
        "scene_count": 4,
        "smoke_only": True,
    }
    assert manifest["smoke_metrics_summary"] == {
        "better_tie_worse": {"better": 158, "tie": 3, "worse": 0},
        "ci95": {"high": -0.03979996775908021, "low": -0.10611335747183279},
        "latency_ms": {
            "max": 0.0818032,
            "mean": 0.0288966,
            "median": 0.0281599,
            "p95": 0.0314692,
            "p99": 0.03459,
        },
        "mean_delta": -0.0729566626154565,
        "oracle_gap_closed": 0.9993321161828008,
        "primary_eval_rows": 161,
    }
    assert manifest["recommended_next_path"] == {
        "increase_scene_diversity": True,
        "next_gate": "scale-up plan",
        "pilot_result_usable_for_claim": False,
        "target_records": 10000,
    }
    assert (fixture["output_dir"] / module.PACKAGE_MANIFEST_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PACKAGE_REPORT_MD_NAME).is_file()
    assert (fixture["output_dir"] / module.SOURCE_INDEX_JSON_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_evidence_package_construction_rejects_source_sha_failure(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, corrupt_source_id="split_execution")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_artifact_split_execution_sha_verified" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, *, corrupt_source_id: str | None = None) -> dict:
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_STATIC_REVIEW_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_artifacts = [
        _write_source_artifact(tmp_path / source_id, module, source_id, corrupt=source_id == corrupt_source_id)
        for source_id in SOURCE_IDS
    ]
    plan_artifact = _write_plan_artifact(tmp_path / "plan", module, source_artifacts)
    static_review_artifact = _write_static_review_artifact(tmp_path / "static_review", module)
    return {
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_artifact / module.PLAN_MODULE.PLAN_JSON_NAME,
        "source_plan_sha256s": plan_artifact / "SHA256SUMS",
        "source_plan_root_sha256s": plan_artifact / "ROOT_SHA256SUMS",
        "source_static_review_artifact_dir": static_review_artifact,
        "source_static_review_json": static_review_artifact / module.SOURCE_STATIC_REVIEW_JSON_NAME,
        "source_static_review_sha256s": static_review_artifact / "SHA256SUMS",
        "source_static_review_root_sha256s": static_review_artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "enabled": True,
    }


def _write_source_artifact(path: Path, module, source_id: str, *, corrupt: bool) -> dict:
    path.mkdir()
    summary_name = f"{source_id}.json"
    summary = {"id": source_id}
    if source_id == "paired_evaluation_result_review":
        summary["paired_evaluation_result_review"] = {
            "latency_summary": {
                "count": 161,
                "max": 0.0818032,
                "mean": 0.0288966,
                "median": 0.0281599,
                "p95": 0.0314692,
                "p99": 0.03459,
            },
            "primary_eval_rows": 161,
            "primary_metrics": {
                "better_tie_worse": {"better": 158, "tie": 3, "worse": 0},
                "ci95": {"high": -0.03979996775908021, "low": -0.10611335747183279},
                "mean_delta": -0.0729566626154565,
                "oracle_gap_closed": 0.9993321161828008,
            },
        }
    _write_json(path / summary_name, summary)
    _write(path / "rows.jsonl", "{\"ok\": true}\n")
    _write_json(path / "split_metrics.json", {"source_id": source_id})
    _write_json(path / "latency.json", {"count": 1})
    _write_json(path / "model.json", {"source_id": source_id})
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": f"construct source {source_id}\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
    }.items():
        _write(path / name, content)
    sha_names = (
        summary_name,
        "rows.jsonl",
        "split_metrics.json",
        "latency.json",
        "model.json",
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
    )
    rows = []
    for name in sha_names:
        digest = "0" * 64 if corrupt and name == summary_name else _sha256(path / name)
        rows.append(f"{digest}  {name}\n")
    _write(path / "SHA256SUMS", "".join(rows))
    root_sha = _sha256(path / "SHA256SUMS")
    _write(path / "ROOT_SHA256SUMS", f"{root_sha}  SHA256SUMS\n")
    return {
        "expected_root_sha256": root_sha,
        "id": source_id,
        "path": str(path),
        "phase": source_id,
    }


def _write_plan_artifact(path: Path, module, source_artifacts: list[dict]) -> Path:
    path.mkdir()
    _write_json(
        path / module.PLAN_MODULE.PLAN_JSON_NAME,
        {
            "final_decision": {
                "authorized_next_work": module.SOURCE_STATIC_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
                "evidence_package_constructed": False,
                "evidence_package_plan_only": True,
                "passed": True,
                "performance_claimed": False,
                "promotion_executed": False,
                "safety_claimed": False,
                "scale_up_executed": False,
            },
            "heads": {
                "camp_head": HEAD,
                "camp_origin_main": HEAD,
                "dp_head": module.FIXED_DP_HEAD,
                "required_dp_head": module.FIXED_DP_HEAD,
            },
            "pilot_evidence_package_plan": {
                "no_claim_boundary": {
                    "calibration_rows": 14,
                    "holdout_rows": 147,
                    "no_camp_over_dp_claim": True,
                    "no_performance_claim": True,
                    "no_promotion_or_deployment": True,
                    "no_safety_claim": True,
                    "scene_count": 4,
                    "smoke_only": True,
                },
                "recommended_next_path": {
                    "increase_scene_diversity": True,
                    "next_gate": "scale-up plan",
                    "pilot_result_usable_for_claim": False,
                    "target_records": 10000,
                },
                "required_files": list(module.PLAN_MODULE.REQUIRED_FILES),
                "source_artifacts": source_artifacts,
            },
            "schema_version": module.PLAN_MODULE.SCHEMA_VERSION,
            "status": module.PLAN_MODULE.READY_STATUS,
        },
    )
    _write(path / module.PLAN_MODULE.PLAN_MD_NAME, "# plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(path / name, content)
    _write_sha_manifest(path)
    _write(path / "ROOT_SHA256SUMS", f"{PLAN_ROOT_SHA}  SHA256SUMS\n")
    return path


def _write_static_review_artifact(path: Path, module) -> Path:
    path.mkdir()
    _write_json(
        path / module.SOURCE_STATIC_REVIEW_JSON_NAME,
        {
            "final_decision": {
                "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
                "evidence_package_constructed": False,
                "passed": True,
                "performance_claimed": False,
                "promotion_executed": False,
                "safety_claimed": False,
                "scale_up_executed": False,
                "status": module.SOURCE_STATIC_REVIEW_STATUS,
            },
            "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA_VERSION,
            "status": module.SOURCE_STATIC_REVIEW_STATUS,
        },
    )
    _write(path / module.SOURCE_STATIC_REVIEW_MD_NAME, "# static review\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "static review\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(path / name, content)
    _write_sha_manifest(path)
    _write(path / "ROOT_SHA256SUMS", f"{STATIC_REVIEW_ROOT_SHA}  SHA256SUMS\n")
    return path


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_sha_manifest(path: Path) -> None:
    sha_path = path / "SHA256SUMS"
    rows = []
    for file_path in sorted(path.iterdir()):
        if file_path.is_file() and file_path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(file_path)}  {file_path.name}\n")
    _write(sha_path, "".join(rows))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
