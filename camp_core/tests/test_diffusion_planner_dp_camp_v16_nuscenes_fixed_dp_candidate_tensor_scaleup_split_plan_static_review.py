from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    ROOT
    / "scripts"
    / "integrations"
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_contract.py"
)
HEAD = "24f95fee929035ef2d8483fa5baf71d3ed530f1d"
PLAN_ROOT_SHA = "5a0253063e4165506653f897a983a096b3df457d30b09a3524f8c57c4986c343"
ARTIFACT_PREFIX = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_split_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_split_plan_static_review_passes(tmp_path: Path) -> None:
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
    assert decision["split_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["records"] == 10000
    assert review["scenes"] == 50
    assert review["planned_scene_counts"] == {"calibration": 10, "holdout": 10, "train": 30}
    assert review["planned_record_counts"] == {"calibration": 2156, "holdout": 1581, "train": 6263}
    assert review["scene_zero_overlap"] is True
    assert review["sample_zero_overlap"] is True
    assert review["record_level_hard_split_executed"] is False
    assert review["k_values"] == [8]
    assert review["candidate_count_values"] == [8]
    assert review["candidate_tensor_mutated_count"] == 0
    assert review["followup_policy"]["training"] == "train split only"
    assert review["followup_policy"]["paired_eval_primary"] == "calibration+holdout"
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_split_plan_static_review_rejects_record_level_hard_split(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, record_level_hard_split=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "record_level_hard_split_not_executed" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_split_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    for text in (audit, status):
        assert ARTIFACT_PREFIX in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_train_scenes=30" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_calibration_scenes=10" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_holdout_scenes=10" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_scene_zero_overlap=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_split_plan_static_review_sample_zero_overlap=True" in text
        assert PLAN_ROOT_SHA in text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    record_level_hard_split: bool = False,
) -> dict:
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
    _write_json(source_json, _source_payload(module, record_level_hard_split=record_level_hard_split))
    _write(source_md, "# Scale-up split plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run split plan\n",
    }.items():
        _write(artifact / name, content)
    sha_names = (
        plan.PLAN_JSON_NAME,
        plan.PLAN_MD_NAME,
        "HEADS",
        "COMMAND",
    )
    _write(
        artifact / "SHA256SUMS",
        "".join(f"{_sha256(artifact / name)}  {name}\n" for name in sha_names),
    )
    _write(artifact / "ROOT_SHA256SUMS", f"{PLAN_ROOT_SHA}  SHA256SUMS\n")
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


def _source_payload(module, *, record_level_hard_split: bool) -> dict:
    plan = module.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": plan.READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "split_plan_only": True,
            "split_executed": False,
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
        "split_plan": {
            "source_records": 10000,
            "source_scene_count": 50,
            "source_unique_sample_count": 10000,
            "target_ratio": "60/20/20",
            "target_scene_counts": {"calibration": 10, "holdout": 10, "train": 30},
            "planned_scene_counts": {"calibration": 10, "holdout": 10, "train": 30},
            "planned_record_counts": {"calibration": 2156, "holdout": 1581, "train": 6263},
            "scene_zero_overlap": True,
            "sample_zero_overlap": True,
            "record_level_hard_split_executed": record_level_hard_split,
            "record_count_exact_60_20_20_required": False,
            "k_values": [8],
            "candidate_count_values": [8],
            "dp_head_values": [module.FIXED_DP_HEAD],
            "candidate_tensor_mutated_count": 0,
            "followup_policy": {
                "training": "train split only",
                "paired_eval_primary": "calibration+holdout",
                "claim": "blocked until result review and scale sufficiency checks",
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
