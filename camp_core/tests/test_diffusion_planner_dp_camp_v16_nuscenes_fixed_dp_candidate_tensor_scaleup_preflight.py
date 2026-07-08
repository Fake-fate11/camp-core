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
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup.py"
)
HEAD = "22a0fa3c52647392db0abacd8a88bd21a0b3f6a1"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_ROOT_SHA = "5fc1583598944ad3953ba065b75542df194b99bbda7bf42e73cacae161d45bef"
REVIEW_ROOT_SHA = "682e1f3a40a5524072a76343ac29b59ac0dc41dbf3e40550d57b80156e68cd3b"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_preflight_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    preflight = report["scaleup_preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["scale_up_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert preflight["target_records"] == 10000
    assert preflight["minimum_distinct_scenes"] == 30
    assert preflight["k"] == 8
    assert preflight["candidate_count"] == 8
    assert preflight["max_records_per_scene"] == 334
    assert preflight["estimated_wall_clock_hours"] == 14.8
    assert preflight["source_selection_command_constructed"] is True
    assert preflight["source_selection_command_executed"] is False
    assert "10000" in " ".join(preflight["source_selection_command_template"])
    assert preflight["exporter_py_compile"] is True
    assert preflight["runner_py_compile"] is True
    assert "scene count shortfall" in preflight["stop_conditions"]
    assert "runtime/cost too high" in preflight["stop_conditions"]
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_preflight_rejects_existing_output_root(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["candidate_output_root"].mkdir()

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "candidate_output_root_absent" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_preflight_rejects_wrong_target(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, target_records=9999)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "target_records_10000" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_preflight_rejects_wrong_eof(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, next_work="wrong_gate")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "audit_authorizes_scaleup_preflight" in report["final_decision"]["failed_checks"]
    assert "status_authorizes_scaleup_preflight" in report["final_decision"]["failed_checks"]


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    target_records: int = 10000,
    next_work: str | None = None,
) -> dict:
    review_module = module.SOURCE_REVIEW_MODULE
    plan_module = review_module.PLAN_MODULE
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={review_module.READY_STATUS}",
            f"next_work_target={next_work or module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    plan_artifact = tmp_path / "scaleup_plan"
    review_artifact = tmp_path / "scaleup_plan_static_review"
    plan_artifact.mkdir()
    review_artifact.mkdir()
    plan_json = plan_artifact / plan_module.PLAN_JSON_NAME
    review_json = review_artifact / review_module.REVIEW_JSON_NAME
    _write_json(plan_json, _plan_payload(module, target_records=target_records))
    _write(plan_artifact / plan_module.PLAN_MD_NAME, "# Scale-up plan\n")
    _write_manifest(plan_artifact, PLAN_ROOT_SHA)
    _write_json(review_json, _review_payload(module, target_records=target_records))
    _write(review_artifact / review_module.REVIEW_MD_NAME, "# Scale-up plan static review\n")
    _write_manifest(review_artifact, REVIEW_ROOT_SHA)
    dp_repo = tmp_path / "Diffusion-Planner"
    dp_repo.mkdir()
    nuscenes_root = tmp_path / "nuScenes"
    _write(nuscenes_root / "README", "readable\n")
    return {
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_json,
        "source_plan_sha256s": plan_artifact / "SHA256SUMS",
        "source_plan_root_sha256s": plan_artifact / "ROOT_SHA256SUMS",
        "source_review_artifact_dir": review_artifact,
        "source_review_json": review_json,
        "source_review_sha256s": review_artifact / "SHA256SUMS",
        "source_review_root_sha256s": review_artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "nuscenes_root": nuscenes_root,
        "camp_repo_root": ROOT,
        "dp_repo": dp_repo,
        "candidate_output_root": tmp_path / "scaleup_candidates",
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_review_root_sha256": REVIEW_ROOT_SHA,
        "python_executable": "python",
        "enabled": True,
    }


def _plan_payload(module, *, target_records: int) -> dict:
    plan_module = module.SOURCE_REVIEW_MODULE.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": plan_module.READY_STATUS,
        "final_decision": {
            "authorized_next_work": module.SOURCE_REVIEW_MODULE.AUTHORIZED_CURRENT_WORK,
            "passed": True,
            "scaleup_plan_only": True,
            "scale_up_executed": False,
            "candidate_generation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
        "scaleup_plan": {
            "per_record_timing_seconds": 5.31974,
            "selected_stage": {
                "target_records": target_records,
                "minimum_distinct_scenes": 30,
                "k": 8,
                "candidate_count": 8,
                "estimated_wall_clock_hours": 14.8,
                "max_records_per_scene": 334,
            },
            "source_selection_policy": {
                "prefer_more_scenes_over_more_records_per_scene": True,
                "cap_records_per_scene": True,
                "keep_scene_ids_unique": True,
                "keep_sample_ids_unique": True,
            },
            "split_policy": {
                "scene_level_zero_overlap": True,
                "target_ratio": "60/20/20",
                "apply_ratio_only_when_scene_count_sufficient": True,
                "record_level_leakage_allowed": False,
            },
            "pass_checks": {
                "dp_head_fixed": DP_HEAD,
                "no_dp_modification": True,
                "no_candidate_tensor_mutation": True,
                "k_candidate_count": [8, 8],
                "failure_count": 0,
                "minimum_distinct_scenes": 30,
                "source_artifact_sha_verified": True,
            },
            "stop_conditions": [
                "output root exists",
                "DP HEAD mismatch",
                "records shortfall",
                "scene count shortfall",
                "candidate tensor mutation",
                "fake/synthetic candidate tensor",
                "runtime/cost too high",
            ],
        },
    }


def _review_payload(module, *, target_records: int) -> dict:
    review_module = module.SOURCE_REVIEW_MODULE
    return {
        "schema_version": review_module.SCHEMA_VERSION,
        "status": review_module.READY_STATUS,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "passed": True,
            "static_review_only": True,
            "scale_up_executed": False,
            "candidate_generation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
        "scaleup_plan_static_review": {
            "source_plan_root_sha256": PLAN_ROOT_SHA,
            "per_record_timing_seconds": 5.31974,
            "selected_stage": {
                "target_records": target_records,
                "minimum_distinct_scenes": 30,
                "k": 8,
                "candidate_count": 8,
                "estimated_wall_clock_hours": 14.8,
                "max_records_per_scene": 334,
            },
            "source_selection_policy": {
                "prefer_more_scenes_over_more_records_per_scene": True,
                "cap_records_per_scene": True,
                "keep_scene_ids_unique": True,
                "keep_sample_ids_unique": True,
            },
            "split_policy": {
                "scene_level_zero_overlap": True,
                "target_ratio": "60/20/20",
                "apply_ratio_only_when_scene_count_sufficient": True,
                "record_level_leakage_allowed": False,
            },
            "stop_conditions": [
                "output root exists",
                "DP HEAD mismatch",
                "records shortfall",
                "scene count shortfall",
                "fake/synthetic candidate tensor",
                "runtime/cost too high",
            ],
        },
    }


def _write_manifest(artifact: Path, root_sha: str) -> None:
    for name in ("HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit"):
        _write(artifact / name, f"{name}\n")
    rows = []
    for path in sorted(artifact.iterdir()):
        if path.is_file() and path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(path)}  {path.name}\n")
    _write(artifact / "SHA256SUMS", "".join(rows))
    _write(artifact / "ROOT_SHA256SUMS", f"{root_sha}  SHA256SUMS\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
