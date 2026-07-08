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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package.py"
)
HEAD = "7ec6fc5bface2b08f7e4c2ca114e21f74416c01f"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_ROOT_SHA = "8a98546c81835f8a0234413901ec9e042f6b447fd3f0444d526521df7aa19ac4"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_evidence_package_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_evidence_package_plan_lists_sources_and_boundaries(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["pilot_evidence_package_plan"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evidence_package_plan_only"] is True
    assert decision["evidence_package_constructed"] is False
    assert decision["scale_up_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert [artifact["id"] for artifact in plan["source_artifacts"]] == [
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
    assert all(artifact["sha256s_verified"] for artifact in plan["source_artifacts"])
    assert all(artifact["root_matches_expected"] for artifact in plan["source_artifacts"])
    assert set(plan["required_files"]) == {
        "JSON summaries",
        "rows JSONL",
        "split metrics",
        "latency JSON",
        "model/weights/config/timing/log",
        "HEADS/COMMAND/stdout/stderr",
        "SHA256SUMS/ROOT_SHA256SUMS",
    }
    assert plan["no_claim_boundary"] == {
        "smoke_only": True,
        "scene_count": 4,
        "calibration_rows": 14,
        "holdout_rows": 147,
        "no_performance_claim": True,
        "no_safety_claim": True,
        "no_camp_over_dp_claim": True,
        "no_promotion_or_deployment": True,
    }
    assert plan["pass_checks"]["all_source_artifact_sha_verified"] is True
    assert plan["pass_checks"]["dp_head_fixed"] == DP_HEAD
    assert plan["pass_checks"]["camp_head_chain_recorded"] is True
    assert plan["pass_checks"]["no_dp_modification"] is True
    assert plan["pass_checks"]["no_candidate_tensor_mutation"] is True
    assert plan["pass_checks"]["k_candidate_count"] == [8, 8]
    assert plan["pass_checks"]["no_train_leakage_into_primary_eval"] is True
    assert plan["pass_checks"]["affine_simplex_checks_preserved"] is True
    assert plan["recommended_next_path"] == {
        "next_gate": "scale-up plan",
        "increase_scene_diversity": True,
        "target_records": 10000,
        "pilot_result_usable_for_claim": False,
    }
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_evidence_package_plan_rejects_unverified_source_artifact(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    artifacts = json.loads(fixture["source_artifact_manifest_json"].read_text(encoding="utf-8"))
    artifacts["artifacts"][0]["expected_root_sha256"] = "0" * 64
    fixture["source_artifact_manifest_json"].write_text(json.dumps(artifacts, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "all_source_artifact_sha_verified" in report["final_decision"]["failed_checks"]


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
    _write(source / module.SOURCE_MD_NAME, "# Paired evaluation result review\n")
    _write_common_files(source, module)
    _write_manifest(source, SOURCE_ROOT_SHA)
    manifest = _source_artifact_manifest(tmp_path, module)
    manifest_path = tmp_path / "source_artifacts.json"
    _write_json(manifest_path, {"artifacts": manifest})
    return {
        "source_result_review_artifact_dir": source,
        "source_result_review_json": source / module.SOURCE_JSON_NAME,
        "source_result_review_sha256s": source / "SHA256SUMS",
        "source_result_review_root_sha256s": source / "ROOT_SHA256SUMS",
        "source_artifact_manifest_json": manifest_path,
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
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "paired_evaluation_result_review": {
            "primary_eval_rows": 161,
            "calibration_rows": 14,
            "holdout_rows": 147,
            "train_reporting_only_rows": 863,
            "train_rows_in_primary_eval": 0,
            "k_values": [8],
            "candidate_count_values": [8],
            "dp_head_values": [module.FIXED_DP_HEAD],
            "candidate_tensor_missing_hash_count": 0,
            "candidate_tensor_mutated_count": 0,
            "score_expression": module.SCORE_EXPRESSION,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "approved_atoms_only": True,
            "smoke_only_result": True,
            "no_performance_claim": True,
            "no_safety_claim": True,
            "no_camp_over_dp_claim": True,
            "no_promotion": True,
            "no_deployment": True,
            "recommended_next_gate": module.AUTHORIZED_CURRENT_WORK,
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "result_review_only": True,
            "paired_evaluation_executed_by_review": False,
            "training_executed": False,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _source_artifact_manifest(tmp_path: Path, module) -> list[dict]:
    ids = [
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
    rows = []
    for index, artifact_id in enumerate(ids):
        artifact = tmp_path / artifact_id
        artifact.mkdir()
        _write(artifact / f"{artifact_id}.json", "{}\n")
        _write(artifact / "records.jsonl", "{}\n")
        _write_common_files(artifact, module)
        root = f"{index + 1:064x}"
        _write_manifest(artifact, root)
        rows.append(
            {
                "id": artifact_id,
                "path": str(artifact),
                "expected_root_sha256": root,
                "phase": artifact_id.rsplit("_", 1)[-1],
            }
        )
    return rows


def _write_common_files(artifact: Path, module) -> None:
    _write(artifact / "HEADS", f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n")
    _write(artifact / "COMMAND", "command\n")
    _write(artifact / "stdout.txt", "ok\n")
    _write(artifact / "stderr.txt", "")
    _write(artifact / "run.exit", "0\n")


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
