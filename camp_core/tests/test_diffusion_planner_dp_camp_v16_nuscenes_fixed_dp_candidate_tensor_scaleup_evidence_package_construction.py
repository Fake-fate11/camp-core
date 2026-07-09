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
    / "construct_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package.py"
)
HEAD = "c8ca8e14a20c00e63450afeeca08d3aa170815be"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PLAN_ROOT_SHA = "7060bdad14e75ef508ff36b44bec3c1220a653fa7cb86700b61f99e24ed9aeae"
STATIC_REVIEW_ROOT_SHA = "ffe4c76f25a99c8d1df95b3193741203eaf2a3170cd98144cf43a4550ec359c3"
PACKAGE_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_"
    "c8ca8e14a2_20260709T233119CST"
)
PACKAGE_ROOT_SHA = "f1c2a80b7efa4929e4100e09815a455af50b040403cc0e35a292ce44d11b3d15"
PACKAGE_ROOT_SHA256SUMS_SHA = "faf25f911c320e575671cee0a4e6aa8284820cde8c76a5ce09730a342301558a"
PACKAGE_MANIFEST_SHA = "08da696e10c8462c133befd54fbe3d5952d3160d5b9cd55b1ad583708677fd21"
PACKAGE_REPORT_SHA = "ce912dd6ce7914c98fd8df60e3b4c1e26380fb0be4429392fe3b72df8602596d"
PACKAGE_SOURCE_INDEX_SHA = "59cffa1c8786c2212a4eba7b6e1406972269fe61a681d3fc89547e76da40134c"
PACKAGE_HEADS_SHA = "b529b55b0ba0fab1c13f46ae77ed06ab19cb62daf440e14f8d83b13ed1e28ddd"
PACKAGE_COMMAND_SHA = "db58b9fec9d622c29356e184dfaf1df93a22035ebb7f2f755e0cba18d638334a"
PACKAGE_COMMAND_SHELL_SHA = "bdb3ef55ab9c919479d84c534676998f65522468fe6814436c60ac3732c2a6c0"
PACKAGE_STDOUT_SHA = "613b4a6036aa5fb1409ea5cecf8368cf35090afa12a1ae3774b008e2bb2e34dd"
PACKAGE_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PACKAGE_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_only"
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
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_construction", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_evidence_package_construction_passes(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    manifest = report["package_manifest"]
    source_index = report["source_index"]
    package_report = manifest["package_report"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["evidence_package_constructed"] is True
    assert decision["evidence_package_constructed_by_this_gate"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert manifest["source_artifact_count"] == 8
    assert [item["id"] for item in source_index["source_artifacts"]] == SOURCE_IDS
    assert all(item["sha256s_verified"] for item in source_index["source_artifacts"])
    assert all(item["root_matches_expected"] for item in source_index["source_artifacts"])
    assert all(item["files"] for item in source_index["source_artifacts"])
    assert manifest["dp_head_fixed"] == DP_HEAD
    assert manifest["camp_head_chain_recorded"] is True
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
    assert package_report["recommended_next_path"] == {
        "allowed_next_gates": ["claim-boundary plan", "32k expansion plan"],
        "direct_claim_allowed": False,
    }
    assert (fixture["output_dir"] / module.PACKAGE_MANIFEST_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PACKAGE_REPORT_MD_NAME).is_file()
    assert (fixture["output_dir"] / module.SOURCE_INDEX_JSON_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_evidence_package_construction_rejects_source_sha_failure(
    tmp_path: Path,
) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, corrupt_source_id="scaleup_split_execution")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "source_artifact_scaleup_split_execution_sha_verified" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_evidence_package_construction_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert PACKAGE_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_source_plan_root_sha256={PLAN_ROOT_SHA}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_source_static_review_root_sha256="
            f"{STATIC_REVIEW_ROOT_SHA}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_check_count=153" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_source_artifact_count=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_source_artifact_ids=[scaleup_corpus_generation,scaleup_corpus_result_review,scaleup_split_execution,scaleup_split_result_review,scaleup_training_execution,scaleup_training_result_review,scaleup_paired_evaluation_execution,scaleup_paired_evaluation_result_review]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_paired_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_better_tie_worse=[3365,359,13]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_mean_delta={MEAN_DELTA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_ci95_high={CI95_HIGH}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_non_top1_selection_rate={NON_TOP1_SELECTION_RATE}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_oracle_gap_closed={ORACLE_GAP_CLOSED}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_no_performance_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_no_safety_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_no_camp_over_dp_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_no_promotion_or_deployment=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_evidence_package_constructed=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_safety_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_camp_over_dp_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_deployment_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_camp_head={HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_root_sha256={PACKAGE_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_root_sha256s_sha256={PACKAGE_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_manifest_sha256={PACKAGE_MANIFEST_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_report_md_sha256={PACKAGE_REPORT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_source_index_sha256={PACKAGE_SOURCE_INDEX_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_heads_sha256={PACKAGE_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_command_sha256={PACKAGE_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_command_shell_sha256={PACKAGE_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_stdout_sha256={PACKAGE_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_stderr_sha256={PACKAGE_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_run_exit_sha256={PACKAGE_RUN_EXIT_SHA}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={PACKAGE_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16
    latest_audit_target = audit.rsplit("next_work_target=", maxsplit=1)[1].splitlines()[0]
    assert latest_audit_target == NEXT_WORK_TARGET


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
    _write_json(path / summary_name, {"id": source_id})
    _write(path / "rows.jsonl", "{\"ok\": true}\n")
    _write_json(path / "split_metrics.json", {"source_id": source_id})
    _write_json(path / "latency.json", {"count": 1})
    _write_json(path / "model_config_timing.json", {"source_id": source_id})
    _write(path / "train.log", "ok\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": f"source {source_id}\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(path / name, content)
    sha_names = (
        summary_name,
        "rows.jsonl",
        "split_metrics.json",
        "latency.json",
        "model_config_timing.json",
        "train.log",
        "HEADS",
        "COMMAND",
        "stdout.txt",
        "stderr.txt",
        "run.exit",
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
                "training_executed": False,
            },
            "heads": {
                "camp_head": HEAD,
                "camp_origin_main": HEAD,
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
                    "sources": source_artifacts,
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
                "required_files": list(module.PLAN_MODULE.REQUIRED_FILES),
                "source_artifacts": source_artifacts,
            },
            "schema_version": module.PLAN_MODULE.SCHEMA_VERSION,
            "status": module.PLAN_MODULE.READY_STATUS,
        },
    )
    _write(path / module.PLAN_MODULE.PLAN_MD_NAME, "# plan\n")
    _write_common_files(path, module)
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
                "camp_over_dp_claimed": False,
                "deployment_executed": False,
                "evidence_package_constructed": False,
                "passed": True,
                "performance_claimed": False,
                "promotion_executed": False,
                "safety_claimed": False,
                "static_review_only": True,
                "status": module.SOURCE_STATIC_REVIEW_STATUS,
                "training_executed": False,
            },
            "schema_version": module.SOURCE_STATIC_REVIEW_SCHEMA_VERSION,
            "status": module.SOURCE_STATIC_REVIEW_STATUS,
        },
    )
    _write(path / module.SOURCE_STATIC_REVIEW_MD_NAME, "# static review\n")
    _write_common_files(path, module)
    _write_sha_manifest(path)
    _write(path / "ROOT_SHA256SUMS", f"{STATIC_REVIEW_ROOT_SHA}  SHA256SUMS\n")
    return path


def _write_common_files(path: Path, module) -> None:
    for name, content in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "command\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(path / name, content)


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
