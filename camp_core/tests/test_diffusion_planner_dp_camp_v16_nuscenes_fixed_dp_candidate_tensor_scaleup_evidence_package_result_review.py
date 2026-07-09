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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result.py"
)
CURRENT_HEAD = "7c68ea4a621311b54d81d09d2af5e7dad8c2307f"
PACKAGE_HEAD = "c8ca8e14a20c00e63450afeeca08d3aa170815be"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PACKAGE_ROOT_SHA = "f1c2a80b7efa4929e4100e09815a455af50b040403cc0e35a292ce44d11b3d15"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_"
    "7c68ea4a62_20260709T234843CST"
)
REVIEW_ROOT_SHA = "cba791fbfcac0c9bee5889eaae95deafb2560ec8361df7c2d61f3c7de2cd5206"
REVIEW_ROOT_SHA256SUMS_SHA = "c74977e9a2280fd927e7b8b6299cf0679d614a8e02e8d83b3695e50474b5ebeb"
REVIEW_JSON_SHA = "6d91789a6e0634b2c2d6d0807fe087f75413cb934478f08e62c290292fc5e314"
REVIEW_MD_SHA = "1e933fa60955b2923a171ea56471df8824802ca9d6bff7201d9c5d45f79960ee"
REVIEW_HEADS_SHA = "e8a297d3385d58a8e701eb6371b343eff1f9bfb90b13444737ed3782abd17e58"
REVIEW_COMMAND_SHA = "4b494d3ceff3b5f14b572dd67fe3bef87193f8ae02fedfb2c6828425f3df3dec"
REVIEW_COMMAND_SHELL_SHA = "e7a37e05208fc478e1fb48af36683ea4ed766fe9bb8887cb94b77b132bdeecaa"
REVIEW_STDOUT_SHA = "3b02b45dc21b7aab9576ae83bc2f0e3df9ef0863f288f1730718cd579fe5eb9f"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
NEXT_WORK_TARGET = "v16_nuscenes_fixed_dp_candidate_tensor_claim_boundary_plan_only"
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
    spec = importlib.util.spec_from_file_location("v16_scaleup_evidence_package_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_evidence_package_result_review_accepts_package(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["scaleup_evidence_package_result_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert decision["dp_modified"] is False
    assert decision["candidate_tensor_modified"] is False
    assert review["source_artifact_count"] == 8
    assert review["source_artifact_ids"] == SOURCE_IDS
    assert review["package_unreviewed_files"] == []
    assert review["package_manifest_has_source_paths"] is True
    assert review["package_manifest_has_source_root_sha"] is True
    assert review["source_index_has_file_list_and_sha"] is True
    assert review["camp_head_chain_recorded"] is True
    assert review["dp_head_fixed"] == DP_HEAD
    assert review["no_claim_boundary"] == {
        "descriptive_paired_metrics_only": True,
        "no_camp_over_dp_claim": True,
        "no_performance_claim": True,
        "no_promotion_or_deployment": True,
        "no_safety_claim": True,
    }
    assert review["package_report"]["records"] == 10000
    assert review["package_report"]["scenes"] == 50
    assert review["package_report"]["split_rows"] == {"calibration": 2156, "holdout": 1581, "train": 6263}
    assert review["package_report"]["paired_eval_rows"] == 3737
    assert review["package_report"]["metrics_summary"] == _metrics()
    assert review["recommended_next_path"] == {
        "allowed_next_gates": ["claim-boundary plan", "32k expansion plan"],
        "direct_claim_allowed": False,
    }
    assert review["direct_claim_allowed"] is False
    assert review["candidate_tensor_unmodified"] is True
    assert review["k_candidate_count"] == [8, 8]
    assert review["train_rows_in_primary_eval"] == 0
    assert review["affine_simplex_preserved"] is True
    assert review["source_final_decisions_no_claim_promotion_deploy"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_evidence_package_result_review_rejects_unreviewed_package_file(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    _write(fixture["source_package_artifact_dir"] / "unreviewed.txt", "not in SHA256SUMS\n")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "package_has_no_unreviewed_files" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_evidence_package_result_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")
    current_v16 = status.split("## Current V15 Status", maxsplit=1)[0]

    for text in (audit, current_v16):
        assert REVIEW_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_source_package_root_sha256="
            f"{PACKAGE_ROOT_SHA}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_check_count=111" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_source_artifact_count=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_records=10000" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_scenes=50" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_paired_eval_rows=3737" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_better_tie_worse=[3365,359,13]" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_mean_delta={MEAN_DELTA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_ci95_high={CI95_HIGH}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_non_top1_selection_rate={NON_TOP1_SELECTION_RATE}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_oracle_gap_closed={ORACLE_GAP_CLOSED}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_no_performance_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_no_safety_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_no_camp_over_dp_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_no_promotion_or_deployment=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_result_review_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_performance_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_safety_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_camp_over_dp_claimed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_promotion_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_deployment_executed=False" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_camp_head={CURRENT_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_root_sha256={REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_root_sha256s_sha256={REVIEW_ROOT_SHA256SUMS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_report_json_sha256={REVIEW_JSON_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_report_md_sha256={REVIEW_MD_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_heads_sha256={REVIEW_HEADS_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_command_sha256={REVIEW_COMMAND_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_command_shell_sha256={REVIEW_COMMAND_SHELL_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_stdout_sha256={REVIEW_STDOUT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_stderr_sha256={REVIEW_STDERR_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_result_review_run_exit_sha256={REVIEW_RUN_EXIT_SHA}" in text

    assert f"current_v16_status={module.READY_STATUS}" in current_v16
    assert f"current_v16_artifact={REVIEW_ARTIFACT}" in current_v16
    assert f"next_work_target={NEXT_WORK_TARGET}" in current_v16


def _write_fixture(tmp_path: Path, module) -> dict:
    package = tmp_path / "package"
    package.mkdir()
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
    source_artifacts = [_write_source_artifact(tmp_path / source_id, source_id) for source_id in SOURCE_IDS]
    source_index = {"source_artifacts": [_source_index_item(item) for item in source_artifacts]}
    manifest = _manifest_payload(source_index["source_artifacts"])
    _write_json(package / module.PACKAGE_MANIFEST_JSON_NAME, manifest)
    _write_json(package / module.SOURCE_INDEX_JSON_NAME, source_index)
    _write(package / module.PACKAGE_REPORT_MD_NAME, _package_report_text())
    for name, content in {
        "HEADS": f"CAMP_HEAD={PACKAGE_HEAD}\nCAMP_ORIGIN_MAIN={PACKAGE_HEAD}\nDP_HEAD={DP_HEAD}\n",
        "COMMAND": "construct package\n",
        "COMMAND.shell": "construct package shell\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(package / name, content)
    _write_sha_manifest(package)
    _write(package / "ROOT_SHA256SUMS", f"{PACKAGE_ROOT_SHA}  SHA256SUMS\n")
    return {
        "source_package_artifact_dir": package,
        "package_manifest_json": package / module.PACKAGE_MANIFEST_JSON_NAME,
        "package_report_md": package / module.PACKAGE_REPORT_MD_NAME,
        "source_index_json": package / module.SOURCE_INDEX_JSON_NAME,
        "package_sha256s": package / "SHA256SUMS",
        "package_root_sha256s": package / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": CURRENT_HEAD,
        "current_camp_origin_main": CURRENT_HEAD,
        "current_dp_head": DP_HEAD,
        "expected_package_root_sha256": PACKAGE_ROOT_SHA,
        "enabled": True,
    }


def _write_source_artifact(path: Path, source_id: str) -> dict:
    path.mkdir()
    summary_name = f"{source_id}.json"
    _write_json(path / summary_name, _summary_payload(source_id))
    _write(path / "rows.jsonl", "{\"ok\": true}\n")
    _write_json(path / "split_metrics.json", {"source_id": source_id})
    _write_json(path / "latency.json", {"count": 1})
    _write_json(path / "model_config_timing.json", {"source_id": source_id})
    _write(path / "train.log", "ok\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={PACKAGE_HEAD}\nCAMP_ORIGIN_MAIN={PACKAGE_HEAD}\nDP_HEAD={DP_HEAD}\n",
        "COMMAND": f"source {source_id}\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(path / name, content)
    _write_sha_manifest(path)
    root_sha = _sha256(path / "SHA256SUMS")
    _write(path / "ROOT_SHA256SUMS", f"{root_sha}  SHA256SUMS\n")
    return {"id": source_id, "path": path, "root_sha256": root_sha}


def _summary_payload(source_id: str) -> dict:
    payload = {
        "final_decision": {
            "passed": True,
            "performance_claimed": False,
            "safety_claimed": False,
            "camp_over_dp_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
        "id": source_id,
    }
    if source_id == "scaleup_training_result_review":
        payload["training_result_review"] = {
            "approved_atoms_only": True,
            "candidate_tensor_mutated_count": 0,
            "score_expression": "score_k(w)=a_k^T w",
            "source_dp_head": DP_HEAD,
            "train_candidate_count_values": [8],
            "train_k_values": [8],
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
        }
    if source_id == "scaleup_paired_evaluation_result_review":
        payload["paired_evaluation_result_review"] = {
            "approved_atoms_only": True,
            "candidate_count_values": [8],
            "candidate_tensor_mutated_count": 0,
            "dp_head_values": [DP_HEAD],
            "k_values": [8],
            "primary_eval_rows": 3737,
            "primary_metrics": _metrics(),
            "score_expression": "score_k(w)=a_k^T w",
            "selected_index_out_of_range_count": 0,
            "train_rows_in_primary_eval": 0,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
        }
    return payload


def _source_index_item(item: dict) -> dict:
    files = []
    for raw in (item["path"] / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        sha, rel = raw.split(maxsplit=1)
        files.append({"observed_sha256": sha, "path": rel, "sha256": sha})
    return {
        "expected_root_sha256": item["root_sha256"],
        "failed_sha256s": [],
        "files": files,
        "heads": {"CAMP_HEAD": PACKAGE_HEAD, "DP_HEAD": DP_HEAD},
        "id": item["id"],
        "path": str(item["path"]),
        "root_matches_expected": True,
        "root_sha256": item["root_sha256"],
        "sha256s_verified": True,
    }


def _manifest_payload(source_index: list[dict]) -> dict:
    return {
        "authorizes_claim": False,
        "authorizes_deployment": False,
        "authorizes_promotion": False,
        "camp_head_chain": [item["heads"]["CAMP_HEAD"] for item in source_index],
        "camp_head_chain_recorded": True,
        "dp_head_fixed": DP_HEAD,
        "no_claim_boundary": _no_claim_boundary(),
        "package_report": {
            "metrics_summary": _metrics(),
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
        "schema_version": "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_evidence_package_v1",
        "source_artifact_count": 8,
        "source_artifacts": [
            {
                "file_count": len(item["files"]),
                "id": item["id"],
                "path": item["path"],
                "root_sha256": item["root_sha256"],
            }
            for item in source_index
        ],
    }


def _metrics() -> dict:
    return {
        "better_tie_worse": {"better": 3365, "tie": 359, "worse": 13},
        "ci95": {"high": CI95_HIGH, "low": CI95_LOW},
        "mean_delta": MEAN_DELTA,
        "non_top1_selection_rate": NON_TOP1_SELECTION_RATE,
        "oracle_gap_closed": ORACLE_GAP_CLOSED,
    }


def _no_claim_boundary() -> dict:
    return {
        "descriptive_paired_metrics_only": True,
        "no_camp_over_dp_claim": True,
        "no_performance_claim": True,
        "no_promotion_or_deployment": True,
        "no_safety_claim": True,
    }


def _package_report_text() -> str:
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Scale-Up Evidence Package",
            "- Package report: 10000 records / 50 scenes.",
            "- Split rows: train 6263, calibration 2156, holdout 1581.",
            "- Package report: `{'paired_eval_rows': 3737}`.",
            "- Metrics: better/tie/worse 3365/359/13; mean delta -0.01762098077036227.",
            "- Claim boundary: no performance, safety, CAMP-over-DP, promotion, or deployment.",
            "- Recommended next path: claim-boundary plan or 32k expansion plan; direct claim not allowed.",
            "",
        ]
    )


def _write_sha_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.iterdir()):
        if file_path.is_file() and file_path.name not in {"SHA256SUMS", "ROOT_SHA256SUMS"}:
            rows.append(f"{_sha256(file_path)}  {file_path.name}\n")
    _write(path / "SHA256SUMS", "".join(rows))


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
