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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_contract.py"
)
CURRENT_HEAD = "da6b93bd2dbe71cb77a5c94958450e02c56e059d"
SOURCE_PLAN_HEAD = "547e856d6f2ef891ff591000c0e7ce9a094bb03c"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_ROOT_SHA = "7060bdad14e75ef508ff36b44bec3c1220a653fa7cb86700b61f99e24ed9aeae"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_"
    "da6b93bd2d_20260709T230726CST"
)
REVIEW_ROOT_SHA = "ffe4c76f25a99c8d1df95b3193741203eaf2a3170cd98144cf43a4550ec359c3"
REVIEW_ROOT_SHA256SUMS_SHA = "c8b6456fea532f578d358105f9f297c96a6e372c07bda19b663242587561c9a2"
REVIEW_JSON_SHA = "f8273f47d0c0ceb8438158f2dabdf9fd06047cfe462102663b188879cc10d826"
REVIEW_MD_SHA = "4279d221a8bb23b55f332a319a7ecca84055ae45f26b77bf5e811418fff63dfd"
REVIEW_HEADS_SHA = "afaa751488aa1669a375e79a5f10df70e0aff172fa24a20c82d32f7318e00a98"
REVIEW_COMMAND_SHA = "2be6a6d8daa396ba7e4fa3a844ec7958cf087f1552c92227eaafc40e383671d5"
REVIEW_COMMAND_SHELL_SHA = "56ac3994cf5eb34beed40101ad20f9f9de56a32ee196559379e99c1d5540cc01"
REVIEW_STDOUT_SHA = "a87b5944a945b7220563e106394929273a8e5728fc1f681902259f7d6b1bc87d"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_construction_only"
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
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_evidence_package_plan_static_review_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["plan_static_review"]
    manifest = review["package_manifest"]
    package_report = review["package_report"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["static_review_only"] is True
    assert decision["evidence_package_constructed"] is False
    assert decision["scale_up_executed"] is False
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["source_artifact_ids"] == SOURCE_IDS
    assert review["required_files"] == list(module.PLAN_MODULE.REQUIRED_FILES)
    assert [source["id"] for source in manifest["sources"]] == SOURCE_IDS
    assert all(source["path"] and source["root_sha256"] and source["files"] for source in manifest["sources"])
    assert manifest["camp_head_chain_recorded"] is True
    assert manifest["dp_head_fixed"] == DP_HEAD
    assert manifest["no_claim_boundary"] == {
        "descriptive_paired_metrics_only": True,
        "no_camp_over_dp_claim": True,
        "no_performance_claim": True,
        "no_promotion_or_deployment": True,
        "no_safety_claim": True,
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
    assert review["pass_checks"] == {
        "affine_simplex_checks_preserved": True,
        "all_source_artifact_sha_verified": True,
        "camp_head_chain_recorded": True,
        "candidate_tensor_unmodified": True,
        "dp_head_fixed": DP_HEAD,
        "k_candidate_count": [8, 8],
        "no_train_leakage_into_primary_eval": True,
    }
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_evidence_package_plan_static_review_rejects_missing_required_file(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, required_files=["JSON summaries"])

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "required_file_rows JSONL" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_evidence_package_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert REVIEW_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_source_plan_root_sha256="
            f"{PLAN_ROOT_SHA}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_check_count=142" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_source_artifact_ids=[scaleup_corpus_generation,scaleup_corpus_result_review,scaleup_split_execution,scaleup_split_result_review,scaleup_training_execution,scaleup_training_result_review,scaleup_paired_evaluation_execution,scaleup_paired_evaluation_result_review]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_required_files=[JSON summaries,rows JSONL,split manifests/metrics,latency JSON,model/weights/config/timing/log,HEADS/COMMAND/stdout/stderr,SHA256SUMS/ROOT_SHA256SUMS]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_paired_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_better_tie_worse=[3365,359,13]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_mean_delta={MEAN_DELTA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_ci95_high={CI95_HIGH}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_non_top1_selection_rate={NON_TOP1_SELECTION_RATE}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_oracle_gap_closed={ORACLE_GAP_CLOSED}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_no_performance_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_no_safety_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_no_camp_over_dp_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_no_promotion_or_deployment=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_all_source_artifact_sha_verified=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_candidate_tensor_unmodified=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_k_candidate_count=[8,8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_no_train_leakage_into_primary_eval=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_affine_simplex_checks_preserved=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_recommended_next_path=[claim-boundary plan,32k expansion plan],direct_claim_allowed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_static_review_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_evidence_package_constructed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_scale_up_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_safety_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_camp_over_dp_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_deployment_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_camp_head={CURRENT_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_root_sha256={REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_root_sha256s_sha256={REVIEW_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_report_json_sha256={REVIEW_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_report_md_sha256={REVIEW_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_heads_sha256={REVIEW_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_command_sha256={REVIEW_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_command_shell_sha256={REVIEW_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_stdout_sha256={REVIEW_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_stderr_sha256={REVIEW_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_plan_static_review_run_exit_sha256={REVIEW_RUN_EXIT_SHA}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={REVIEW_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16

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
    _write(artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Scale-up evidence package plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={SOURCE_PLAN_HEAD}\nCAMP_ORIGIN_MAIN={SOURCE_PLAN_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "scale-up evidence package plan\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(artifact / name, content)
    _write_manifest(artifact, PLAN_ROOT_SHA)
    return {
        "source_plan_artifact_dir": artifact,
        "source_plan_json": source_json,
        "source_plan_md": artifact / module.PLAN_MODULE.PLAN_MD_NAME,
        "source_plan_sha256s": artifact / "SHA256SUMS",
        "source_plan_root_sha256s": artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
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
            "camp_head": SOURCE_PLAN_HEAD,
            "camp_origin_main": SOURCE_PLAN_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "scaleup_evidence_package_plan": {
            "forbidden_work": [
                "construct_evidence_package",
                "new_training",
                "new_paired_evaluation",
                "performance_claim",
                "safety_claim",
                "camp_over_dp_claim",
                "promotion",
                "deployment",
            ],
            "package_manifest": {
                "camp_head_chain_recorded": True,
                "dp_head_fixed": module.FIXED_DP_HEAD,
                "no_claim_boundary": {
                    "descriptive_paired_metrics_only": True,
                    "no_camp_over_dp_claim": True,
                    "no_performance_claim": True,
                    "no_promotion_or_deployment": True,
                    "no_safety_claim": True,
                },
                "sources": [
                    {
                        "files": [{"path": f"{artifact_id}.json", "sha256": f"{index + 1:064x}"}],
                        "heads": {
                            "CAMP_HEAD": SOURCE_PLAN_HEAD,
                            "CAMP_ORIGIN_MAIN": SOURCE_PLAN_HEAD,
                            "DP_HEAD": module.FIXED_DP_HEAD,
                        },
                        "id": artifact_id,
                        "path": f"/tmp/{artifact_id}",
                        "root_sha256": f"{index + 1:064x}",
                    }
                    for index, artifact_id in enumerate(SOURCE_IDS)
                ],
            },
            "package_report": {
                "metrics_summary": {
                    "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
                    "ci95": {"high": CI95_HIGH, "low": CI95_LOW},
                    "mean_delta": MEAN_DELTA,
                    "non_top1_selection_rate": NON_TOP1_SELECTION_RATE,
                    "oracle_gap_closed": ORACLE_GAP_CLOSED,
                },
                "no_camp_over_dp_claim": True,
                "no_performance_claim": True,
                "no_safety_claim": True,
                "paired_eval_rows": 3737,
                "recommended_next_path": {
                    "allowed_next_gates": ["claim-boundary plan", "32k expansion plan"],
                    "direct_claim_allowed": False,
                },
                "records": 10000,
                "scenes": 50,
                "split_rows": {"calibration": 2156, "holdout": 1581, "train": 6263},
            },
            "pass_checks": {
                "affine_simplex_checks_preserved": True,
                "all_source_artifact_sha_verified": True,
                "camp_head_chain_recorded": True,
                "candidate_tensor_unmodified": True,
                "dp_head_fixed": module.FIXED_DP_HEAD,
                "k_candidate_count": [8, 8],
                "no_train_leakage_into_primary_eval": True,
            },
            "required_files": required_files or list(module.PLAN_MODULE.REQUIRED_FILES),
            "source_artifacts": [
                {
                    "failed_sha256s": [],
                    "id": artifact_id,
                    "root_matches_expected": True,
                    "sha256s_verified": True,
                }
                for artifact_id in SOURCE_IDS
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
