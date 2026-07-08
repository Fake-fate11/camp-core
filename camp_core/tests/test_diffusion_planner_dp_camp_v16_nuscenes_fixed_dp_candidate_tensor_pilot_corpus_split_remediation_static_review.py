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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_corpus_split_remediation_static_contract.py"
)
HEAD = "aac3ff7ae1544c393adbaadf9752ec923b5e0d55"
REMEDIATION_ROOT_SHA = "0a56b12cc11549868337decf07ae3c1af497a8c04c2c9880f25e5683af897111"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_split_remediation_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_corpus_split_remediation_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["remediation_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["split_execution_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert review["source_remediation_root_sha256"] == REMEDIATION_ROOT_SHA
    assert review["split_policy"] == "scene_level_greedy_imbalance_tolerant_smoke_split"
    assert review["split_unit"] == "scene_id"
    assert review["record_level_split_executed"] is False
    assert review["scene_zero_overlap"] is True
    assert review["sample_zero_overlap"] is True
    assert review["scene_assignments"] == {
        "calibration": ["scene-0061"],
        "holdout": ["scene-0757"],
        "train": ["scene-0553", "scene-0655"],
    }
    assert review["actual_record_counts"] == {"calibration": 14, "holdout": 147, "train": 863}
    assert review["pilot_split_classification"] == "imbalance_tolerant_smoke_split"
    assert review["four_scene_split_formal_performance_proof_authorized"] is False
    assert review["larger_corpus_preconditions"] == {
        "minimum_scene_count_before_ratio_tracking": 30,
        "near_60_20_20_requires_scene_count_at_least": 30,
        "ten_k_generation_must_increase_scene_diversity": True,
    }
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()


def test_v16_pilot_corpus_split_remediation_static_review_rejects_bad_policy(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, policy="record_level_exact_split")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "policy_is_scene_level_smoke_split" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, policy: str | None = None) -> dict:
    plan = module.PLAN_MODULE
    artifact = tmp_path / "split_plan_remediation"
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
    _write_json(source_json, _source_payload(module, policy=policy))
    _write(source_md, "# Split Remediation\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run remediation plan\n",
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
    _write(artifact / "ROOT_SHA256SUMS", f"{REMEDIATION_ROOT_SHA}  {artifact.name}\n")
    return {
        "source_remediation_artifact_dir": artifact,
        "source_remediation_json": source_json,
        "source_remediation_md": source_md,
        "source_remediation_sha256s": artifact / "SHA256SUMS",
        "source_remediation_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_remediation_root_sha256": REMEDIATION_ROOT_SHA,
        "enabled": True,
    }


def _source_payload(module, policy: str | None = None) -> dict:
    plan = module.PLAN_MODULE
    return {
        "schema_version": module.SOURCE_REMEDIATION_SCHEMA_VERSION,
        "status": plan.READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "candidate_generation_executed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "split_execution_executed": False,
            "split_plan_remediation_only": True,
            "training_executed": False,
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "remediation_plan": {
            "actual_record_counts": {"calibration": 14, "holdout": 147, "train": 863},
            "actual_record_ratios": {
                "calibration": 0.013671875,
                "holdout": 0.1435546875,
                "train": 0.8427734375,
            },
            "exact_record_count_targets_rejected": True,
            "larger_corpus_preconditions": {
                "minimum_scene_count_before_ratio_tracking": 30,
                "near_60_20_20_requires_scene_count_at_least": 30,
                "ten_k_generation_must_increase_scene_diversity": True,
            },
            "pilot_split_classification": "imbalance_tolerant_smoke_split",
            "record_level_split_executed": False,
            "sample_zero_overlap": True,
            "scene_assignments": {
                "calibration": ["scene-0061"],
                "holdout": ["scene-0757"],
                "train": ["scene-0553", "scene-0655"],
            },
            "scene_counts": {
                "scene-0061": 14,
                "scene-0553": 495,
                "scene-0655": 368,
                "scene-0757": 147,
            },
            "scene_zero_overlap": True,
            "source_records": 1024,
            "split_policy": policy or "scene_level_greedy_imbalance_tolerant_smoke_split",
            "split_unit": "scene_id",
        },
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
