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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup.py"
)
HEAD = "851e03435ca5775adbae7f2e78e3d1844a2a883d"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_ROOT_SHA = "fba6f194e3df38ad5ff80c1b2a62458f199871bb10a0518d8fc4450273d6d24b"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_plan_targets_policies_and_boundaries(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["scaleup_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["scaleup_plan_only"] is True
    assert decision["scale_up_executed"] is False
    assert decision["candidate_generation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert plan["baseline"]["pilot_records"] == 1024
    assert plan["baseline"]["pilot_distinct_scenes"] == 4
    assert plan["selected_stage"] == {
        "target_records": 10000,
        "minimum_distinct_scenes": 30,
        "k": 8,
        "candidate_count": 8,
        "estimated_wall_clock_hours": 14.8,
        "max_records_per_scene": 334,
    }
    assert plan["optional_stages"] == [
        {
            "target_records": 32000,
            "minimum_distinct_scenes": 90,
            "k": 8,
            "candidate_count": 8,
            "estimated_wall_clock_hours": 47.3,
            "max_records_per_scene": 356,
        },
        {
            "target_records": 100000,
            "minimum_distinct_scenes": 90,
            "k": 8,
            "candidate_count": 8,
            "estimated_wall_clock_hours": 147.8,
            "condition": "only if runtime and cost are acceptable after the 32k review",
        },
    ]
    assert plan["source_selection_policy"] == {
        "prefer_more_scenes_over_more_records_per_scene": True,
        "cap_records_per_scene": True,
        "keep_scene_ids_unique": True,
        "keep_sample_ids_unique": True,
        "avoid_four_scene_imbalance_repeat": True,
    }
    assert plan["split_policy"] == {
        "scene_level_zero_overlap": True,
        "target_ratio": "60/20/20",
        "apply_ratio_only_when_scene_count_sufficient": True,
        "record_level_leakage_allowed": False,
    }
    assert plan["pass_checks"] == {
        "dp_head_fixed": DP_HEAD,
        "no_dp_modification": True,
        "no_candidate_tensor_mutation": True,
        "k_candidate_count": [8, 8],
        "failure_count": 0,
        "minimum_distinct_scenes": 30,
        "source_artifact_sha_verified": True,
    }
    assert set(plan["stop_conditions"]) == {
        "output root exists",
        "DP HEAD mismatch",
        "records shortfall",
        "scene count shortfall",
        "candidate tensor mutation",
        "fake/synthetic candidate tensor",
        "runtime/cost too high",
    }
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_plan_rejects_unverified_source_artifact(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["expected_source_root_sha256"] = "0" * 64

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_result_review_root_sha256" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module) -> dict:
    source = tmp_path / "source_result_review"
    source.mkdir()
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
    _write_json(source / module.SOURCE_JSON_NAME, _source_payload(module))
    _write(source / module.SOURCE_MD_NAME, "# Evidence package result review\n")
    _write(source / "HEADS", f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={DP_HEAD}\n")
    _write(source / "COMMAND", "review package\n")
    _write(source / "stdout.txt", "{}\n")
    _write(source / "stderr.txt", "")
    _write(source / "run.exit", "0\n")
    _write_manifest(source, SOURCE_ROOT_SHA)
    return {
        "source_result_review_artifact_dir": source,
        "source_result_review_json": source / module.SOURCE_JSON_NAME,
        "source_result_review_sha256s": source / "SHA256SUMS",
        "source_result_review_root_sha256s": source / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": DP_HEAD,
        "expected_source_root_sha256": SOURCE_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "passed": True,
            "result_review_only": True,
            "scale_up_executed": False,
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
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": DP_HEAD,
            "required_dp_head": DP_HEAD,
        },
        "pilot_evidence_package_result_review": {
            "source_artifact_count": 10,
            "no_claim_boundary": {
                "calibration_rows": 14,
                "holdout_rows": 147,
                "scene_count": 4,
                "smoke_only": True,
            },
            "smoke_metrics_summary": {
                "primary_eval_rows": 161,
                "better_tie_worse": {"better": 158, "tie": 3, "worse": 0},
                "mean_delta": -0.0729566626154565,
                "ci95": {"low": -0.10611335747183279, "high": -0.03979996775908021},
                "oracle_gap_closed": 0.9993321161828008,
            },
            "k_candidate_count": [8, 8],
            "all_source_artifact_sha_verified": True,
            "all_source_dp_heads_fixed": True,
            "candidate_tensor_unmodified": True,
            "train_rows_in_primary_eval": 0,
            "affine_simplex_preserved": True,
        },
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
