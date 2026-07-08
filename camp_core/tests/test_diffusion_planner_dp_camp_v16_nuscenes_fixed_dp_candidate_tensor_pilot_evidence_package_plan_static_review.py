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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_plan_static_contract.py"
)
HEAD = "5415097e1c9a0ad422189a4b092bb9c55a26b46f"
PLAN_ROOT_SHA = "93dbc0808e95c93d5ac3e73a97e6beaec1917219a98c7faaa21dbe4b7b6dbe0c"
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
    spec = importlib.util.spec_from_file_location("v16_evidence_package_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_evidence_package_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["plan_static_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["evidence_package_constructed"] is False
    assert decision["scale_up_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["source_artifact_ids"] == SOURCE_IDS
    assert review["required_files"] == list(module.PLAN_MODULE.REQUIRED_FILES)
    assert review["no_claim_boundary"] == {
        "calibration_rows": 14,
        "holdout_rows": 147,
        "no_camp_over_dp_claim": True,
        "no_performance_claim": True,
        "no_promotion_or_deployment": True,
        "no_safety_claim": True,
        "scene_count": 4,
        "smoke_only": True,
    }
    assert review["pass_checks"] == {
        "affine_simplex_checks_preserved": True,
        "all_source_artifact_sha_verified": True,
        "camp_head_chain_recorded": True,
        "dp_head_fixed": module.FIXED_DP_HEAD,
        "k_candidate_count": [8, 8],
        "no_candidate_tensor_mutation": True,
        "no_dp_modification": True,
        "no_train_leakage_into_primary_eval": True,
    }
    assert review["recommended_next_path"] == {
        "increase_scene_diversity": True,
        "next_gate": "scale-up plan",
        "pilot_result_usable_for_claim": False,
        "target_records": 10000,
    }
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_evidence_package_plan_static_review_rejects_missing_required_file(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, required_files=["JSON summaries"])

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "required_file_rows JSONL" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module, *, required_files: list[str] | None = None) -> dict:
    artifact = tmp_path / "evidence_package_plan"
    artifact.mkdir()
    docs = tmp_path / "docs"
    doc_text = "\n".join(
        [
            f"current_v16_status={module.PLAN_MODULE.READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)
    source_json = artifact / module.PLAN_MODULE.PLAN_JSON_NAME
    _write_json(source_json, _source_payload(module, required_files=required_files))
    _write(artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Pilot evidence package plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "pilot evidence package plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    sha_names = (
        module.PLAN_MODULE.PLAN_JSON_NAME,
        module.PLAN_MODULE.PLAN_MD_NAME,
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
    _write(artifact / "ROOT_SHA256SUMS", f"{PLAN_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_plan_artifact_dir": artifact,
        "source_plan_json": source_json,
        "source_plan_md": artifact / module.PLAN_MODULE.PLAN_MD_NAME,
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


def _source_payload(module, *, required_files: list[str] | None) -> dict:
    return {
        "authorized_current_work": module.PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "camp_over_dp_claimed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "evidence_package_constructed": False,
            "evidence_package_plan_only": True,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "safety_claimed": False,
            "scale_up_executed": False,
            "training_executed": False,
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
            "source_camp_head": "bdf124e021457356a34406aeb3d81e53b2ef3be5",
        },
        "pilot_evidence_package_plan": {
            "forbidden_work": [
                "construct_evidence_package",
                "scale_up_execution",
                "training",
                "new_paired_evaluation",
                "performance_claim",
                "safety_claim",
                "camp_over_dp_claim",
                "promotion",
                "deployment",
            ],
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
            "pass_checks": {
                "affine_simplex_checks_preserved": True,
                "all_source_artifact_sha_verified": True,
                "camp_head_chain_recorded": True,
                "dp_head_fixed": module.FIXED_DP_HEAD,
                "k_candidate_count": [8, 8],
                "no_candidate_tensor_mutation": True,
                "no_dp_modification": True,
                "no_train_leakage_into_primary_eval": True,
            },
            "recommended_next_path": {
                "increase_scene_diversity": True,
                "next_gate": "scale-up plan",
                "pilot_result_usable_for_claim": False,
                "target_records": 10000,
            },
            "required_files": required_files or list(module.PLAN_MODULE.REQUIRED_FILES),
            "source_artifacts": [
                {
                    "id": source_id,
                    "root_matches_expected": True,
                    "sha256s_verified": True,
                }
                for source_id in SOURCE_IDS
            ],
        },
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.PLAN_MODULE.READY_STATUS,
    }


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
