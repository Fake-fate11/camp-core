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
    / "plan_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight.py"
)
HEAD = "d8409258df161e41ed0d38362613217e19c882cf"
SPLIT_REVIEW_ROOT_SHA = "028e40a2bf2c9c4fc9300660371079656a931e1dce8d3e9fc8c0a51a84f3d1e2"
SPLIT_EXECUTION_ROOT_SHA = "18f1231c1c50841bde09527066f7845fe6b101c9978bf490457d8ce6c1867878"
PILOT_CORPUS_ROOT_SHA = "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_"
    "fe753b8e_20260708T100801CST"
)
PLAN_CAMP_HEAD = "fe753b8e418bf0f72ee3cbcc5371f92c2ce24656"
PLAN_JSON_SHA = "03d5a4e80e44814395b6d876c7170321e1480db2ff62b8b98536d0e3851e5445"
PLAN_MD_SHA = "3a304d3be6b77a36489a4a22fb28e094b1720e34b93e73eb4d4033be89655930"
PLAN_SHA256SUMS_SHA = "bc0c5b63a26dd035fcfd74a74df6465df173597278aacc95f77dd5ad8d86f2aa"
PLAN_ROOT_SHA256SUMS_SHA = "888d25f3b1584dec22c6d8c9a63da1e6cd0cc49feea41d9ae98847a0da203d21"
PLAN_HEADS_SHA = "021d4da25ee4c175808008ee46b5ea95b29d65970db2daa004d4a03269248ff2"
PLAN_COMMAND_SHA = "bf36817d904206d4d5250ad65664deaa215ef765344db8a1a08b8d9b43156330"
PLAN_STDOUT_SHA = "d8b44aca6cd15df894649d1e39721bfce5db0c0c9229b0a812803ca0a62c558d"
PLAN_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
PLAN_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"
PILOT_CORPUS_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_generation_candidates_"
    "mini_train_d799ada8_20260708T013202CST"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_training_preflight_plan", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_training_preflight_plan_uses_train_split_only(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    plan = report["pilot_training_preflight_plan"]
    inputs = plan["training_inputs"]
    output_plan = plan["planned_outputs"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert inputs["train_records"] == 863
    assert inputs["calibration_records_used_for_training"] == 0
    assert inputs["holdout_records_used_for_training"] == 0
    assert inputs["training_splits"] == ["train"]
    assert inputs["forbidden_training_splits"] == ["calibration", "holdout"]
    assert inputs["split_result_review_root_sha256"] == SPLIT_REVIEW_ROOT_SHA
    assert inputs["split_execution_root_sha256"] == SPLIT_EXECUTION_ROOT_SHA
    assert inputs["pilot_corpus_root_sha256"] == PILOT_CORPUS_ROOT_SHA
    assert inputs["pilot_corpus_artifact"] == PILOT_CORPUS_ARTIFACT
    assert inputs["candidate_tensor_schema"] == {
        "candidate_count": 8,
        "candidate_tensor_shape": [8, 80, 4],
        "k": 8,
    }
    assert plan["training_scope"] == "pilot_smoke_training_only_no_performance_claim"
    assert plan["math_contract"]["score_expression"] == "score_k(w)=a_k^T w"
    assert plan["math_contract"]["weights_nonnegative"] is True
    assert plan["math_contract"]["weights_sum_to_one"] is True
    assert plan["math_contract"]["approved_atoms_only"] is True
    assert output_plan == {
        "affine_scoring_check": "affine_scoring_check.json",
        "approved_atoms_check": "approved_atoms_check.json",
        "command": "COMMAND",
        "heads": "HEADS",
        "nonnegative_simplex_check": "nonnegative_simplex_check.json",
        "sha256s": "SHA256SUMS",
        "static_camp_weights_model_artifact": "static_camp_weights_model.json",
        "stderr": "stderr.txt",
        "stdout": "stdout.txt",
        "timing_json": "pilot_training_timing.json",
        "timing_md": "pilot_training_timing.md",
        "training_config": "pilot_training_config.json",
    }
    assert (fixture["output_dir"] / module.PLAN_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PLAN_MD_NAME).is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").read_text(encoding="utf-8").split()[1] == "SHA256SUMS"


def test_v16_pilot_training_preflight_plan_rejects_holdout_training_use(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, holdout_used_for_training=1)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "holdout_records_not_used_for_training" in report["final_decision"]["failed_checks"]


def test_v16_pilot_training_preflight_plan_rejects_non_affine_score(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["score_expression"] = "score_k(w)=nonlinear(a_k,w)"

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "score_expression_affine" in report["final_decision"]["failed_checks"]


def test_v16_pilot_training_preflight_plan_rejects_missing_candidate_hash(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, missing_train_hash=True)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "candidate_tensor_hashes_present" in report["final_decision"]["failed_checks"]


def test_v16_pilot_training_preflight_plan_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(
        encoding="utf-8"
    )
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(
        encoding="utf-8"
    )

    for text in (audit, status):
        assert PLAN_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert f"v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_camp_head={PLAN_CAMP_HEAD}" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_check_count=69" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_train_records=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_performance_claimed=False" in text
        assert PLAN_JSON_SHA in text
        assert PLAN_MD_SHA in text
        assert PLAN_SHA256SUMS_SHA in text
        assert PLAN_ROOT_SHA256SUMS_SHA in text
        assert PLAN_HEADS_SHA in text
        assert PLAN_COMMAND_SHA in text
        assert PLAN_STDOUT_SHA in text
        assert PLAN_STDERR_SHA in text
        assert PLAN_RUN_EXIT_SHA in text
        assert SPLIT_REVIEW_ROOT_SHA in text
        assert SPLIT_EXECUTION_ROOT_SHA in text
        assert PILOT_CORPUS_ROOT_SHA in text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    holdout_used_for_training: int = 0,
    missing_train_hash: bool = False,
) -> dict:
    split_review = tmp_path / "split_result_review"
    split_execution = tmp_path / "split_execution"
    docs = tmp_path / "docs"
    split_review.mkdir()
    split_execution.mkdir()
    doc_text = "\n".join(
        [
            f"current_v16_status={module.SOURCE_READY_STATUS}",
            f"next_work_target={module.AUTHORIZED_CURRENT_WORK}",
            "",
        ]
    )
    audit = _write(docs / "diffusion_planner_v16_iteration_audit.md", doc_text)
    current_status = _write(docs / "diffusion_planner_current_status.md", doc_text)

    split_execution_json = split_execution / module.SPLIT_EXECUTION_JSON_NAME
    _write_json(split_execution_json, _split_execution_payload(module))
    _write(split_execution / module.SPLIT_EXECUTION_MD_NAME, "# Split execution\n")
    _write(split_execution / "split_manifest.json", "{}\n")
    records_by_split = _records_by_split(module)
    if missing_train_hash:
        del records_by_split["train"][0]["candidate_tensor_sha256"]
    for name, records in {
        "train_records.jsonl": records_by_split["train"],
        "calibration_records.jsonl": records_by_split["calibration"],
        "holdout_records.jsonl": records_by_split["holdout"],
    }.items():
        (split_execution / name).write_text(
            "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
            encoding="utf-8",
        )
    _write_source_artifact_files(split_execution, module.FIXED_DP_HEAD)
    _write_manifest(split_execution, SPLIT_EXECUTION_ROOT_SHA)

    review_json = split_review / module.SOURCE_REVIEW_JSON_NAME
    _write_json(
        review_json,
        _split_review_payload(
            module,
            split_execution,
            holdout_used_for_training=holdout_used_for_training,
        ),
    )
    _write(split_review / module.SOURCE_REVIEW_MD_NAME, "# Split result review\n")
    _write_source_artifact_files(split_review, module.FIXED_DP_HEAD)
    _write_manifest(split_review, SPLIT_REVIEW_ROOT_SHA)

    return {
        "source_split_result_review_artifact_dir": split_review,
        "source_split_result_review_json": review_json,
        "source_split_result_review_sha256s": split_review / "SHA256SUMS",
        "source_split_result_review_root_sha256s": split_review / "ROOT_SHA256SUMS",
        "source_split_execution_artifact_dir": split_execution,
        "source_split_execution_json": split_execution_json,
        "source_train_records_jsonl": split_execution / "train_records.jsonl",
        "source_calibration_records_jsonl": split_execution / "calibration_records.jsonl",
        "source_holdout_records_jsonl": split_execution / "holdout_records.jsonl",
        "source_split_execution_sha256s": split_execution / "SHA256SUMS",
        "source_split_execution_root_sha256s": split_execution / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_split_result_review_root_sha256": SPLIT_REVIEW_ROOT_SHA,
        "expected_split_execution_root_sha256": SPLIT_EXECUTION_ROOT_SHA,
        "score_expression": "score_k(w)=a_k^T w",
        "enabled": True,
    }


def _split_review_payload(module, split_execution: Path, *, holdout_used_for_training: int) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_artifact": {
            "path": str(split_execution),
            "root_sha256": SPLIT_EXECUTION_ROOT_SHA,
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "split_result_review": {
            "candidate_count_values": [8],
            "candidate_tensor_mutated_count": 0,
            "counts": {"calibration": 14, "holdout": 147, "train": 863},
            "dp_head_values": [module.FIXED_DP_HEAD],
            "k_values": [8],
            "performance_claim_supported": False,
            "pilot_split_classification": "imbalance_tolerant_smoke_split",
            "record_level_hard_split_executed": False,
            "sample_zero_overlap": True,
            "scene_assignments": {
                "calibration": ["scene-0061"],
                "holdout": ["scene-0757"],
                "train": ["scene-0553", "scene-0655"],
            },
            "scene_zero_overlap": True,
            "split_policy": "scene_level_greedy_imbalance_tolerant_smoke_split",
            "total_records": 1024,
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "candidate_generation_executed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "holdout_records_used_for_training": holdout_used_for_training,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "result_review_only": True,
            "split_execution_executed": False,
            "training_executed": False,
        },
    }


def _split_execution_payload(module) -> dict:
    return {
        "schema_version": module.SPLIT_EXECUTION_SCHEMA_VERSION,
        "status": module.SPLIT_EXECUTION_READY_STATUS,
        "source_artifacts": {
            "pilot_corpus": {
                "path": PILOT_CORPUS_ARTIFACT,
                "root_sha256": PILOT_CORPUS_ROOT_SHA,
            }
        },
        "heads": {
            "camp_head": HEAD,
            "camp_origin_main": HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "split_execution": {
            "candidate_count_values": [8],
            "counts": {"calibration": 14, "holdout": 147, "train": 863},
            "dp_head_values": [module.FIXED_DP_HEAD],
            "k_values": [8],
        },
        "final_decision": {
            "authorized_next_work": module.SOURCE_CURRENT_WORK,
            "candidate_generation_executed": False,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "promotion_executed": False,
            "split_execution_executed": True,
            "training_executed": False,
        },
    }


def _records_by_split(module) -> dict[str, list[dict]]:
    return {
        "train": [_record(module, "train", "scene-0553", index) for index in range(495)]
        + [_record(module, "train", "scene-0655", 495 + index) for index in range(368)],
        "calibration": [
            _record(module, "calibration", "scene-0061", 863 + index)
            for index in range(14)
        ],
        "holdout": [
            _record(module, "holdout", "scene-0757", 877 + index)
            for index in range(147)
        ],
    }


def _record(module, split: str, scene: str, index: int) -> dict:
    return {
        "candidate_count": 8,
        "candidate_tensor_sha256": f"{index:064x}",
        "candidate_tensor_shape": [8, 80, 4],
        "candidate_tensor_unchanged_by_camp": True,
        "DP_HEAD": module.FIXED_DP_HEAD,
        "K": 8,
        "sample_id": f"{scene}_{index:06d}",
        "scene_id": scene,
        "split": split,
    }


def _write_source_artifact_files(root: Path, dp_head: str) -> None:
    for name, text in {
        "HEADS": f"CAMP_HEAD={HEAD}\nCAMP_ORIGIN_MAIN={HEAD}\nDP_HEAD={dp_head}\n",
        "COMMAND": "source command\n",
        "stdout.txt": "ok\n",
        "stderr.txt": "",
        "run.exit": "0\n",
    }.items():
        _write(root / name, text)


def _write_manifest(root: Path, root_sha: str) -> None:
    names = sorted(path.name for path in root.iterdir() if path.is_file() and path.name != "ROOT_SHA256SUMS")
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(root / name)}  {name}\n" for name in names if name != "SHA256SUMS"),
        encoding="utf-8",
    )
    (root / "ROOT_SHA256SUMS").write_text(f"{root_sha}  SHA256SUMS\n", encoding="utf-8")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
