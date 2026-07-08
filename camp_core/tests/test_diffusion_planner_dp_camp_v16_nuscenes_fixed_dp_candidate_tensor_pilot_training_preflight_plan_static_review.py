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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_contract.py"
)
HEAD = "9f739c60c00a97bdee6c0b0949d89a9dba740db3"
PLAN_HEAD = "fe753b8e418bf0f72ee3cbcc5371f92c2ce24656"
PLAN_ROOT_SHA = "bc0c5b63a26dd035fcfd74a74df6465df173597278aacc95f77dd5ad8d86f2aa"
SPLIT_REVIEW_ROOT_SHA = "028e40a2bf2c9c4fc9300660371079656a931e1dce8d3e9fc8c0a51a84f3d1e2"
SPLIT_EXECUTION_ROOT_SHA = "18f1231c1c50841bde09527066f7845fe6b101c9978bf490457d8ce6c1867878"
PILOT_CORPUS_ROOT_SHA = "57779ea5d6aa2d9f1e7a5962cbbd551238ec1500136bd82e972714d479da7432"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_"
    "fe753b8e_20260708T100801CST"
)
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_"
    "ae7963b7_20260708T103348CST"
)
REVIEW_JSON_SHA = "18241632a44e19ce67caf57fb3e48c2aed81a2ffcfc8204c7582d30fd1214922"
REVIEW_MD_SHA = "416113122a90902c084a40340616e5a942904e915c15e2dbd80d88960223792f"
REVIEW_SHA256SUMS_SHA = "0a73622f95790703a8a1512c46ae8be93dbd99c1932fda912069ee870e5dd188"
REVIEW_ROOT_SHA256SUMS_SHA = "53e762d0923dbcb9b6fc1741161c0e12afbe005ddd10a61cb08c14aa559d12dc"
REVIEW_HEADS_SHA = "229c32be687909a6030979685c00413d3301eadf6c96f69bd72f6569061d71d7"
REVIEW_COMMAND_SHA = "4e9d49423819b9cf5c0b026153daf57300d30d54a2f7a593553efb765b3925b6"
REVIEW_STDOUT_SHA = "350de8c56f1c34932527d74d6894d1f4af76200b09ac56e03b627e9145a4fc45"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_training_preflight_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_training_preflight_plan_static_review_passes(tmp_path: Path) -> None:
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
    assert decision["training_executed"] is False
    assert decision["paired_evaluation_executed"] is False
    assert decision["performance_claimed"] is False
    assert review["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert review["train_records"] == 863
    assert review["calibration_records"] == 14
    assert review["holdout_records"] == 147
    assert review["calibration_records_used_for_training"] == 0
    assert review["holdout_records_used_for_training"] == 0
    assert review["score_expression"] == module.PLAN_MODULE.SCORE_EXPRESSION
    assert review["weights_nonnegative"] is True
    assert review["weights_sum_to_one"] is True
    assert review["approved_atoms_only"] is True
    assert review["nonnegative_simplex"] is True
    assert review["dp_head"] == module.FIXED_DP_HEAD
    assert review["candidate_tensor_schema"] == {
        "candidate_count": 8,
        "candidate_tensor_shape": [8, 80, 4],
        "k": 8,
    }
    assert review["planned_outputs"] == {
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
    assert "split_overlap" in review["stop_conditions"]
    assert "missing_candidate_tensor_hashes" in review["stop_conditions"]
    assert "dp_head_mismatch" in review["stop_conditions"]
    assert "non_affine_score" in review["stop_conditions"]
    assert "non_simplex_weights" in review["stop_conditions"]
    assert "calibration_or_holdout_training_use" in review["stop_conditions"]
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_training_preflight_plan_static_review_rejects_leakage(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, calibration_used_for_training=1)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "calibration_records_not_used_for_training" in report["final_decision"]["failed_checks"]


def test_v16_pilot_training_preflight_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert REVIEW_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_check_count=78" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_train_records=863" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_calibration_records=14" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_holdout_records=147" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_k=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_candidate_count=8" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_pilot_training_preflight_plan_static_review_performance_claimed=False" in text
        assert PLAN_ROOT_SHA in text
        assert REVIEW_JSON_SHA in text
        assert REVIEW_MD_SHA in text
        assert REVIEW_SHA256SUMS_SHA in text
        assert REVIEW_ROOT_SHA256SUMS_SHA in text
        assert REVIEW_HEADS_SHA in text
        assert REVIEW_COMMAND_SHA in text
        assert REVIEW_STDOUT_SHA in text
        assert REVIEW_STDERR_SHA in text
        assert REVIEW_RUN_EXIT_SHA in text


def _write_fixture(
    tmp_path: Path,
    module,
    *,
    calibration_used_for_training: int = 0,
) -> dict:
    artifact = tmp_path / "training_preflight_plan"
    artifact.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
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
    _write_json(
        source_json,
        _source_payload(module, calibration_used_for_training=calibration_used_for_training),
    )
    _write(artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Pilot training preflight plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={PLAN_HEAD}\nCAMP_ORIGIN_MAIN={PLAN_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run pilot training preflight plan\n",
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


def _source_payload(module, *, calibration_used_for_training: int) -> dict:
    return {
        "schema_version": module.SOURCE_PLAN_SCHEMA_VERSION,
        "status": module.PLAN_MODULE.READY_STATUS,
        "authorized_current_work": module.PLAN_MODULE.AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
        "source_artifacts": {
            "pilot_corpus": {
                "path": module.PLAN_MODULE.PILOT_CORPUS_ARTIFACT,
                "root_sha256": PILOT_CORPUS_ROOT_SHA,
            },
            "split_execution": {
                "path": "/root/autodl-tmp/split_execution",
                "root_sha256": SPLIT_EXECUTION_ROOT_SHA,
            },
            "split_result_review": {
                "path": "/root/autodl-tmp/split_result_review",
                "root_sha256": SPLIT_REVIEW_ROOT_SHA,
            },
        },
        "heads": {
            "camp_head": PLAN_HEAD,
            "camp_origin_main": PLAN_HEAD,
            "dp_head": module.FIXED_DP_HEAD,
            "required_dp_head": module.FIXED_DP_HEAD,
        },
        "pilot_training_preflight_plan": {
            "fixed_dp_head": module.FIXED_DP_HEAD,
            "training_scope": "pilot_smoke_training_only_no_performance_claim",
            "training_inputs": {
                "calibration_records_available": 14,
                "calibration_records_used_for_training": calibration_used_for_training,
                "candidate_tensor_schema": {
                    "candidate_count": 8,
                    "candidate_tensor_shape": [8, 80, 4],
                    "k": 8,
                },
                "dp_head": module.FIXED_DP_HEAD,
                "forbidden_training_splits": ["calibration", "holdout"],
                "holdout_records_available": 147,
                "holdout_records_used_for_training": 0,
                "pilot_corpus_artifact": module.PLAN_MODULE.PILOT_CORPUS_ARTIFACT,
                "pilot_corpus_root_sha256": PILOT_CORPUS_ROOT_SHA,
                "split_execution_artifact": "/root/autodl-tmp/split_execution",
                "split_execution_root_sha256": SPLIT_EXECUTION_ROOT_SHA,
                "split_result_review_artifact": "/root/autodl-tmp/split_result_review",
                "split_result_review_root_sha256": SPLIT_REVIEW_ROOT_SHA,
                "train_records": 863,
                "training_splits": ["train"],
            },
            "math_contract": {
                "approved_atoms_only": True,
                "nonnegative_simplex": True,
                "score_expression": module.PLAN_MODULE.SCORE_EXPRESSION,
                "weights_nonnegative": True,
                "weights_sum_to_one": True,
            },
            "planned_outputs": {
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
            },
            "stop_conditions": [
                "split_overlap",
                "missing_candidate_tensor_hashes",
                "k_or_candidate_count_not_8",
                "dp_head_mismatch",
                "calibration_or_holdout_training_use",
                "non_affine_score",
                "non_simplex_weights",
            ],
        },
        "final_decision": {
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "candidate_tensor_modified": False,
            "deployment_executed": False,
            "dp_modified": False,
            "fake_candidate_tensor_generated": False,
            "paired_evaluation_executed": False,
            "passed": True,
            "performance_claimed": False,
            "pilot_training_preflight_plan_executed": True,
            "promotion_executed": False,
            "training_executed": False,
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
