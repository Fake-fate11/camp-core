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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package.py"
)
HEAD = "547e856d6f2ef891ff591000c0e7ce9a094bb03c"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SOURCE_ROOT_SHA = "727ef240fb7803b5e479b5a1e5e86cf2ec0ca79e67d4f0894b44042743723f21"
PLAN_STATUS = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_ready"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_547e856d6f_20260709T214457CST"
)
PLAN_ROOT_SHA = "7060bdad14e75ef508ff36b44bec3c1220a653fa7cb86700b61f99e24ed9aeae"
PLAN_JSON_SHA = "1ba1dd2172aff96b971cd92d9db272c0d54b5e1c569fabbb58badad5ae950f94"
PLAN_MD_SHA = "0e4b9af27f00b9afaf973731bdff331d98f8bea24d4a309c173e655e53f43573"
PLAN_HEADS_SHA = "340a26dab4cebb077eef465a8c0e0c505ab3cf23d12a66813e42ef2e07f260aa"
PLAN_COMMAND_SHA = "c0d49c9d00108ea5b40385e523341c6917e40b810a91ad4c2815efac92283f36"
PLAN_COMMAND_SHELL_SHA = "de774d99935a64041bf85784e7bb1b84ee0b38b388e8a637fbfbc7fb01882d13"
PLAN_STDOUT_SHA = "f990f3f65e89733d66af2fb8c8da1839a9e2a79f90b8ebfc06a26877b203340b"
PLAN_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PLAN_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_only"
MEAN_DELTA = -0.01762098077036227
CI95_LOW = -0.021974139797953596
CI95_HIGH = -0.01326782174277094
NON_TOP1_SELECTION_RATE = 0.903933636606904
ORACLE_GAP_CLOSED = 0.9619006786247026
SOURCE_IDS = [
    "scaleup_corpus_generation",
    "scaleup_corpus_result_review",
    "scaleup_split_execution",
    "scaleup_split_result_review",
    "scaleup_training_execution",
    "scaleup_training_result_review",
    "scaleup_paired_evaluation_execution",
    "scaleup_paired_evaluation_result_review",
]


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_evidence_package_plan_lists_sources_manifest_and_boundaries(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["scaleup_evidence_package_plan"]
    package_manifest = plan["package_manifest"]
    package_report = plan["package_report"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evidence_package_plan_only"] is True
    assert decision["evidence_package_constructed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert [artifact["id"] for artifact in plan["source_artifacts"]] == SOURCE_IDS
    assert all(artifact["sha256s_verified"] for artifact in plan["source_artifacts"])
    assert all(artifact["root_matches_expected"] for artifact in plan["source_artifacts"])
    assert all(artifact["files"] for artifact in package_manifest["sources"])
    assert package_manifest["dp_head_fixed"] == DP_HEAD
    assert package_manifest["camp_head_chain_recorded"] is True
    assert package_manifest["no_claim_boundary"]["no_performance_claim"] is True
    assert set(plan["required_files"]) == {
        "JSON summaries",
        "rows JSONL",
        "split manifests/metrics",
        "latency JSON",
        "model/weights/config/timing/log",
        "HEADS/COMMAND/stdout/stderr",
        "SHA256SUMS/ROOT_SHA256SUMS",
    }
    assert package_report["records"] == 10000
    assert package_report["scenes"] == 50
    assert package_report["split_rows"] == {"calibration": 2156, "holdout": 1581, "train": 6263}
    assert package_report["paired_eval_rows"] == 3737
    assert package_report["metrics_summary"] == {
        "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
        "ci95": {"high": CI95_HIGH, "low": CI95_LOW},
        "mean_delta": MEAN_DELTA,
        "non_top1_selection_rate": NON_TOP1_SELECTION_RATE,
        "oracle_gap_closed": ORACLE_GAP_CLOSED,
    }
    assert package_report["no_performance_claim"] is True
    assert package_report["no_safety_claim"] is True
    assert package_report["no_camp_over_dp_claim"] is True
    assert package_report["recommended_next_path"] == {
        "allowed_next_gates": ["claim-boundary plan", "32k expansion plan"],
        "direct_claim_allowed": False,
    }
    assert plan["pass_checks"] == {
        "affine_simplex_checks_preserved": True,
        "all_source_artifact_sha_verified": True,
        "camp_head_chain_recorded": True,
        "candidate_tensor_unmodified": True,
        "dp_head_fixed": DP_HEAD,
        "k_candidate_count": [8, 8],
        "no_train_leakage_into_primary_eval": True,
    }
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_evidence_package_plan_rejects_unverified_source_artifact(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    manifest = json.loads(fixture["source_artifact_manifest_json"].read_text(encoding="utf-8"))
    manifest["artifacts"][0]["expected_root_sha256"] = "0" * 64
    fixture["source_artifact_manifest_json"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "all_source_artifact_sha_verified" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_evidence_package_plan_is_recorded_in_status_docs() -> None:
    current = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    current_v16 = current.split("## Current V15 Status", maxsplit=1)[0]

    for text in (current_v16, audit):
        assert f"current_v16_status={PLAN_STATUS}" in text
        assert f"current_v16_artifact={PLAN_ARTIFACT}" in text
        assert f"next_work_target={NEXT_WORK_TARGET}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_artifact={PLAN_ARTIFACT}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_root_sha256={PLAN_ROOT_SHA}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_check_count=71" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_source_artifact_ids=[scaleup_corpus_generation,scaleup_corpus_result_review,scaleup_split_execution,scaleup_split_result_review,scaleup_training_execution,scaleup_training_result_review,scaleup_paired_evaluation_execution,scaleup_paired_evaluation_result_review]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_required_files=[JSON summaries,rows JSONL,split manifests/metrics,latency JSON,model/weights/config/timing/log,HEADS/COMMAND/stdout/stderr,SHA256SUMS/ROOT_SHA256SUMS]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_paired_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_better_tie_worse=[3365,359,13]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_mean_delta={MEAN_DELTA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_ci95_high={CI95_HIGH}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_non_top1_selection_rate={NON_TOP1_SELECTION_RATE}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_oracle_gap_closed={ORACLE_GAP_CLOSED}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_no_performance_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_no_safety_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_no_camp_over_dp_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_no_promotion_or_deployment=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_all_source_artifact_sha_verified=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_k_candidate_count=[8,8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_no_train_leakage_into_primary_eval=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_affine_simplex_checks_preserved=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_recommended_next_path=[claim-boundary plan,32k expansion plan],direct_claim_allowed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_evidence_package_constructed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_deployment_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_report_json_sha256={PLAN_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_report_md_sha256={PLAN_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_heads_sha256={PLAN_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_command_sha256={PLAN_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_command_shell_sha256={PLAN_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_stdout_sha256={PLAN_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_stderr_sha256={PLAN_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_run_exit_sha256={PLAN_RUN_EXIT_SHA}" in text

    latest_audit_target = audit.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert latest_audit_target == NEXT_WORK_TARGET


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
    _write(source / module.SOURCE_MD_NAME, "# Scale-up paired evaluation result review\n")
    _write_common_files(source, module)
    _write_manifest(source, SOURCE_ROOT_SHA)
    manifest_path = tmp_path / "source_artifacts.json"
    _write_json(manifest_path, {"artifacts": _source_artifact_manifest(tmp_path, module)})
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
            "approved_atoms_only": True,
            "calibration_rows": 2156,
            "candidate_count_values": [8],
            "candidate_tensor_missing_hash_count": 0,
            "candidate_tensor_mutated_count": 0,
            "descriptive_paired_metrics_only": True,
            "dp_head_values": [module.FIXED_DP_HEAD],
            "holdout_rows": 1581,
            "k_values": [8],
            "latency_summary": {"count": 3737, "max": 0.34069595858454704},
            "primary_eval_rows": 3737,
            "primary_metrics": {
                "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
                "ci95": {"high": CI95_HIGH, "low": CI95_LOW},
                "mean_delta": MEAN_DELTA,
                "non_top1_selection_rate": NON_TOP1_SELECTION_RATE,
                "oracle_gap_closed": ORACLE_GAP_CLOSED,
            },
            "score_expression": module.SCORE_EXPRESSION,
            "train_reporting_only_rows": 6263,
            "train_rows_in_primary_eval": 0,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "candidate_tensor_modified": False,
            "camp_over_dp_claimed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed_by_review": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "result_review_only": True,
            "safety_claimed": False,
            "training_executed": False,
        },
    }


def _source_artifact_manifest(tmp_path: Path, module) -> list[dict]:
    rows = []
    for index, artifact_id in enumerate(SOURCE_IDS):
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
