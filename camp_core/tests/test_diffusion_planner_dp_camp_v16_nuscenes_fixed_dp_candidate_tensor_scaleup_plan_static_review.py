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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_plan_static_contract.py"
)
HEAD = "7bb1d49e38fa8fd54583655059944f3976fd3a95"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_ROOT_SHA = "5fc1583598944ad3953ba065b75542df194b99bbda7bf42e73cacae161d45bef"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["scaleup_plan_static_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["scale_up_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["selected_stage"] == {
        "candidate_count": 8,
        "estimated_wall_clock_hours": 14.8,
        "k": 8,
        "max_records_per_scene": 334,
        "minimum_distinct_scenes": 30,
        "target_records": 10000,
    }
    assert review["per_record_timing_seconds"] == 5.31974
    assert review["optional_stage_hours"] == {"32000": 47.3, "100000": 147.8}
    assert review["source_selection_policy"] == {
        "avoid_four_scene_imbalance_repeat": True,
        "cap_records_per_scene": True,
        "keep_sample_ids_unique": True,
        "keep_scene_ids_unique": True,
        "prefer_more_scenes_over_more_records_per_scene": True,
    }
    assert review["split_policy"] == {
        "apply_ratio_only_when_scene_count_sufficient": True,
        "record_level_leakage_allowed": False,
        "scene_level_zero_overlap": True,
        "target_ratio": "60/20/20",
    }
    assert review["pass_checks"]["dp_head_fixed"] == DP_HEAD
    assert review["pass_checks"]["k_candidate_count"] == [8, 8]
    assert review["pass_checks"]["failure_count"] == 0
    assert review["pass_checks"]["minimum_distinct_scenes"] == 30
    assert set(review["stop_conditions"]) == {
        "output root exists",
        "DP HEAD mismatch",
        "records shortfall",
        "scene count shortfall",
        "candidate tensor mutation",
        "fake/synthetic candidate tensor",
        "runtime/cost too high",
    }
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_plan_static_review_rejects_wrong_target(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, target_records=9999)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "target_records_10000" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, *, target_records: int = 10000) -> dict:
    plan_module = module.PLAN_MODULE
    artifact = tmp_path / "scaleup_plan"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={plan_module.READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_json = artifact / plan_module.PLAN_JSON_NAME
    source_md = artifact / plan_module.PLAN_MD_NAME
    _write_json(source_json, _source_payload(module, target_records=target_records))
    _write(source_md, "# Scale-up plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={DP_HEAD}\n",
        "COMMAND": "scaleup plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    _write_manifest(artifact, PLAN_ROOT_SHA)
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
        "current_dp_head": DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module, *, target_records: int) -> dict:
    return {
        "authorized_current_work": module.PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "camp_over_dp_claimed": False,
            "candidate_generation_executed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "safety_claimed": False,
            "scale_up_executed": False,
            "scaleup_plan_only": True,
            "training_executed": False,
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": DP_HEAD,
            "required_dp_head": DP_HEAD,
        },
        "scaleup_plan": {
            "per_record_timing_seconds": 5.31974,
            "selected_stage": {
                "candidate_count": 8,
                "estimated_wall_clock_hours": 14.8,
                "k": 8,
                "max_records_per_scene": 334,
                "minimum_distinct_scenes": 30,
                "target_records": target_records,
            },
            "optional_stages": [
                {
                    "candidate_count": 8,
                    "estimated_wall_clock_hours": 47.3,
                    "k": 8,
                    "max_records_per_scene": 356,
                    "minimum_distinct_scenes": 90,
                    "target_records": 32000,
                },
                {
                    "candidate_count": 8,
                    "condition": "only if runtime and cost are acceptable after the 32k review",
                    "estimated_wall_clock_hours": 147.8,
                    "k": 8,
                    "minimum_distinct_scenes": 90,
                    "target_records": 100000,
                },
            ],
            "source_selection_policy": {
                "avoid_four_scene_imbalance_repeat": True,
                "cap_records_per_scene": True,
                "keep_sample_ids_unique": True,
                "keep_scene_ids_unique": True,
                "prefer_more_scenes_over_more_records_per_scene": True,
            },
            "split_policy": {
                "apply_ratio_only_when_scene_count_sufficient": True,
                "record_level_leakage_allowed": False,
                "scene_level_zero_overlap": True,
                "target_ratio": "60/20/20",
            },
            "pass_checks": {
                "dp_head_fixed": DP_HEAD,
                "failure_count": 0,
                "k_candidate_count": [8, 8],
                "minimum_distinct_scenes": 30,
                "no_candidate_tensor_mutation": True,
                "no_dp_modification": True,
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
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.PLAN_MODULE.READY_STATUS,
    }


def _write_manifest(artifact: Path, root_sha: str) -> None:
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
