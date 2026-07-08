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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result.py"
)
CURRENT_HEAD = "e04f605d34d5bd7487058e80a702a1d3bf7e8840"
PACKAGE_HEAD = "6a63445be503d873bb7e968b39d1b9ad5264685f"
DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
PACKAGE_ROOT_SHA = "1e1faff126d415b0f55af260f2aedacb8bb8ac60d72323b5c12366f1dec01211"
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_"
    "406ad9ceeb_20260708T165135CST"
)
REVIEW_CAMP_HEAD = "406ad9ceebf19f9f7b956bdb96b735db983be210"
REVIEW_ROOT_SHA = "fba6f194e3df38ad5ff80c1b2a62458f199871bb10a0518d8fc4450273d6d24b"
REVIEW_ROOT_SHA256SUMS_SHA = "003564496204a7d2b9f25c11d7201189c880acd8728fb057778938a7cd43f37f"
REVIEW_JSON_SHA = "218f0a7a85a55f4db49481e4a21df3483b28a57bb78d2c132aa4fe5b93d1cbcf"
REVIEW_MD_SHA = "d1e32333e3c82b4b9cb5295f5ff2a94a464c9df8f609218499d01a2f6d1397c6"
REVIEW_HEADS_SHA = "f50a23053140c7abd1331e0ef39da11586d92ffe7779cc0e0a5b083f54994011"
REVIEW_COMMAND_SHA = "3ce15e710ff86b5603e36e893f542dd9c40cffa55572861279900c889b62cbf7"
REVIEW_COMMAND_SHELL_SHA = "dde9b884bb69fd0e554c494f1b08aec2087684f1e607453c6cc993aed61fd4fe"
REVIEW_STDOUT_SHA = "b0147546c9a290c72de1c7c0d6ccc0e7c6d390dece4623c181d88cc87d9ea291"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
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
    spec = importlib.util.spec_from_file_location("v16_pilot_evidence_package_result_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_evidence_package_result_review_accepts_package(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    review = report["pilot_evidence_package_result_review"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["result_review_only"] is True
    assert decision["scale_up_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert decision["promotion_executed"] is False
    assert decision["deployment_executed"] is False
    assert decision["dp_modified"] is False
    assert decision["candidate_tensor_modified"] is False
    assert review["source_artifact_count"] == 10
    assert review["source_artifact_ids"] == SOURCE_IDS
    assert review["package_unreviewed_files"] == []
    assert review["package_manifest_has_source_paths"] is True
    assert review["package_manifest_has_source_root_sha"] is True
    assert review["source_index_has_file_list_and_sha"] is True
    assert review["camp_head_chain_recorded"] is True
    assert review["dp_head_fixed"] == DP_HEAD
    assert review["no_claim_boundary"]["smoke_only"] is True
    assert review["no_claim_boundary"]["scene_count"] == 4
    assert review["no_claim_boundary"]["calibration_rows"] == 14
    assert review["no_claim_boundary"]["holdout_rows"] == 147
    assert review["smoke_metrics_summary"]["primary_eval_rows"] == 161
    assert review["smoke_metrics_summary"]["better_tie_worse"] == {"better": 158, "tie": 3, "worse": 0}
    assert review["smoke_metrics_summary"]["mean_delta"] == -0.0729566626154565
    assert review["smoke_metrics_summary"]["ci95"] == {
        "high": -0.03979996775908021,
        "low": -0.10611335747183279,
    }
    assert review["smoke_metrics_summary"]["oracle_gap_closed"] == 0.9993321161828008
    assert review["k_candidate_count"] == [8, 8]
    assert review["train_rows_in_primary_eval"] == 0
    assert review["affine_simplex_preserved"] is True
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_evidence_package_result_review_rejects_unreviewed_package_file(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    _write(fixture["source_package_artifact_dir"] / "unreviewed.txt", "not in SHA256SUMS\n")

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "package_has_no_unreviewed_files" in report["final_decision"]["failed_checks"]


def test_v16_pilot_evidence_package_result_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert REVIEW_ARTIFACT in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_status={module.READY_STATUS}" in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_check_count=125" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_source_artifact_count=10" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_smoke_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_scene_count=4" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_calibration_rows=14" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_holdout_rows=147" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_no_performance_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_no_safety_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_no_camp_over_dp_claim=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_no_promotion_or_deployment=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_scale_up_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_dp_modified=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_candidate_tensor_modified=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_k_candidate_count=[8,8]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_train_rows_in_primary_eval=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_affine_simplex_preserved=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_primary_eval_rows=161" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_better_tie_worse=158/3/0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_mean_delta=-0.0729566626154565" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_ci95=[-0.10611335747183279,-0.03979996775908021]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_oracle_gap_closed=0.9993321161828008" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_camp_head={REVIEW_CAMP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_dp_head={DP_HEAD}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_package_root_sha256={PACKAGE_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_root_sha256={REVIEW_ROOT_SHA}" in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_result_review_root_sha256s_sha256={REVIEW_ROOT_SHA256SUMS_SHA}" in text
        for digest in (
            REVIEW_JSON_SHA,
            REVIEW_MD_SHA,
            REVIEW_HEADS_SHA,
            REVIEW_COMMAND_SHA,
            REVIEW_COMMAND_SHELL_SHA,
            REVIEW_STDOUT_SHA,
            REVIEW_STDERR_SHA,
            REVIEW_RUN_EXIT_SHA,
        ):
            assert digest in text
    assert f"current_v16_status={module.READY_STATUS}" in status
    assert f"next_work_target={module.AUTHORIZED_NEXT_WORK}" in status


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
    _write(path / "array_summary.json", "[1, 2, 3]\n")
    _write(path / "rows.jsonl", "{\"ok\": true}\n")
    _write_json(path / "split_metrics.json", {"source_id": source_id})
    _write_json(path / "latency.json", {"count": 1})
    _write_json(path / "model.json", {"source_id": source_id})
    for name, content in {
        "HEADS": f"CAMP_HEAD={PACKAGE_HEAD}\nCAMP_ORIGIN_MAIN={PACKAGE_HEAD}\nDP_HEAD={DP_HEAD}\n",
        "COMMAND": f"source {source_id}\n",
        "stdout.txt": "{}\n",
        "stderr.txt": "",
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
    if source_id == "training_result_review":
        payload["training_result_review"] = {
            "approved_atoms_only": True,
            "candidate_tensor_mutated_count": 0,
            "score_expression": SCORE_EXPRESSION,
            "source_dp_head": DP_HEAD,
            "train_candidate_count_values": [8],
            "train_k_values": [8],
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
        }
    if source_id == "paired_evaluation_result_review":
        payload["paired_evaluation_result_review"] = {
            "approved_atoms_only": True,
            "candidate_count_values": [8],
            "candidate_tensor_mutated_count": 0,
            "dp_head_values": [DP_HEAD],
            "k_values": [8],
            "primary_eval_rows": 161,
            "primary_metrics": _smoke_metrics(),
            "score_expression": SCORE_EXPRESSION,
            "selected_index_out_of_range_count": 0,
            "smoke_only_result": True,
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
        "authorizes_scale_up_execution": False,
        "camp_head_chain": [item["heads"]["CAMP_HEAD"] for item in source_index],
        "dp_head_fixed": DP_HEAD,
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
        "recommended_next_path": {
            "increase_scene_diversity": True,
            "next_gate": "scale-up plan",
            "pilot_result_usable_for_claim": False,
            "target_records": 10000,
        },
        "schema_version": "dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_evidence_package_v1",
        "smoke_metrics_summary": _smoke_metrics(),
        "source_artifact_count": 10,
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


def _smoke_metrics() -> dict:
    return {
        "better_tie_worse": {"better": 158, "tie": 3, "worse": 0},
        "ci95": {"high": -0.03979996775908021, "low": -0.10611335747183279},
        "mean_delta": -0.0729566626154565,
        "oracle_gap_closed": 0.9993321161828008,
        "primary_eval_rows": 161,
    }


def _package_report_text() -> str:
    return "\n".join(
        [
            "# V16 nuScenes Fixed-DP Pilot Evidence Package",
            "- Scope: smoke-only, 4 scenes, calibration `14`, holdout `147`.",
            "- Claim boundary: no performance, safety, CAMP-over-DP, promotion, deployment, or scale-up execution.",
            "- Paired eval summary: primary rows 161; better/tie/worse 158/3/0; mean delta -0.0729566626154565.",
            "- Recommended next path: scale-up plan, increase scene diversity, target records 10000.",
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
