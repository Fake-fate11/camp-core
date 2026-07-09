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
    / "review_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_contract.py"
)
HEAD = "12fba87c205ac5a2940c5bd8450d70502f7e7f3f"
PLAN_HEAD = "7dfa1b3d13ae0acb6667d9d2591315ab8ed4301f"
PLAN_ROOT_SHA = "990992937869aca189cb71d9832a435575c01091a924e136df1850bc164f549b"
SPLIT_REVIEW_ROOT_SHA = "1322556d790e25527818d38e77cf5240bb6fd68678563190a6ad0f88cbc70d0e"
SPLIT_EXECUTION_ROOT_SHA = "b8bb06e6f83ae59d8d08a8f400e58870971d42472d836fc10288327b19ac2456"
SCALEUP_CORPUS_ROOT_SHA = "42dd60dd9dcb74015658acdb333f22a64e48bbfd48084bb65ecd767bd7e86ba0"
PLAN_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_"
    "7dfa1b3d13_20260709T150711CST"
)
REVIEW_ARTIFACT = (
    "/root/autodl-tmp/"
    "camp_dp_v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_"
    "12fba87c20_20260709T152321CST"
)
REVIEW_JSON_SHA = "54bdab55a197606ee2dc648713c73f72711005884d86ba8b90a84a4aeed52c62"
REVIEW_MD_SHA = "7f2c3fcd1cc77ee8b52f57e13814897b97ead09e950ca391b5acd67bd15823af"
REVIEW_SHA256SUMS_SHA = "da8b55d6e897f9aa6fb852d8b40d578960e6b6d07373673311c8dd82fd4b3706"
REVIEW_ROOT_SHA256SUMS_SHA = "3faeeba94d46b3292928dad970bea80ea1db1202169b592ebd1bb258580ed623"
REVIEW_HEADS_SHA = "8c3aec8235014c3d52f22adf7daaf07651cf7190ca618d74ab976c889f1b4002"
REVIEW_COMMAND_SHA = "39d83413170e3fa81bf029044116878e0d15e54efa39bb1cd7aea76be48c8bb2"
REVIEW_STDOUT_SHA = "aef27a6b0f3989e3f3a13d19b4a8e3bfaa21b37f6b136ce76054c0de27a0352a"
REVIEW_STDERR_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
REVIEW_RUN_EXIT_SHA = "9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_scaleup_training_preflight_plan_static_review", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_scaleup_training_preflight_plan_static_review_passes(tmp_path: Path) -> None:
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
    assert review["train_records"] == 6263
    assert review["calibration_records"] == 2156
    assert review["holdout_records"] == 1581
    assert review["training_splits"] == ["train"]
    assert review["forbidden_training_splits"] == ["calibration", "holdout"]
    assert review["calibration_records_used_for_training"] == 0
    assert review["holdout_records_used_for_training"] == 0
    assert review["score_expression"] == module.PLAN_MODULE.SCORE_EXPRESSION
    assert review["weights_nonnegative"] is True
    assert review["weights_sum_to_one"] is True
    assert review["approved_atoms_only"] is True
    assert review["nonnegative_simplex"] is True
    assert review["no_closed_loop_outcomes_as_training_input"] is True
    assert review["no_candidate_tensor_mutation"] is True
    assert review["no_dp_modification"] is True
    assert review["dp_head"] == module.FIXED_DP_HEAD
    assert review["candidate_tensor_schema"] == {
        "candidate_count": 8,
        "candidate_tensor_shape": [8, 80, 4],
        "k": 8,
    }
    assert review["planned_outputs"] == {
        "approved_atoms_check": "approved_atoms_check.json",
        "command": "COMMAND",
        "heads": "HEADS",
        "nonnegative_simplex_check": "nonnegative_simplex_check.json",
        "root_sha256s": "ROOT_SHA256SUMS",
        "sha256s": "SHA256SUMS",
        "static_camp_weights_model_artifact": "static_camp_weights_model.json",
        "stderr": "stderr.txt",
        "stdout": "stdout.txt",
        "timing_json": "scaleup_training_timing.json",
        "timing_md": "scaleup_training_timing.md",
        "training_config": "scaleup_training_config.json",
        "training_log": "scaleup_training.log",
    }
    for condition in (
        "split_overlap",
        "missing_candidate_hashes",
        "k_or_candidate_count_drift",
        "dp_head_mismatch",
        "calibration_or_holdout_leakage",
        "non_affine_score",
        "non_simplex_weights",
    ):
        assert condition in review["stop_conditions"]
    assert (fixture["output_dir"] / module.REVIEW_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.REVIEW_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_scaleup_training_preflight_plan_static_review_rejects_leakage(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module, calibration_used_for_training=1)

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "calibration_records_not_used_for_training" in report["final_decision"]["failed_checks"]


def test_v16_scaleup_training_preflight_plan_static_review_is_recorded() -> None:
    module = _load_module()
    audit = (ROOT / "docs" / "diffusion_planner_v16_iteration_audit.md").read_text(encoding="utf-8")
    status = (ROOT / "docs" / "diffusion_planner_current_status.md").read_text(encoding="utf-8")

    for text in (audit, status):
        assert REVIEW_ARTIFACT in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_status="
            f"{module.READY_STATUS}"
        ) in text
        assert (
            "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_authorized_next_work="
            f"{module.AUTHORIZED_NEXT_WORK}"
        ) in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_failed_checks=[]" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_train_records=6263" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_calibration_records=2156" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_holdout_records=1581" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_calibration_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_holdout_records_used_for_training=0" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_score_expression=score_k(w)=a_k^T w" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_weights_nonnegative=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_weights_sum_to_one=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_approved_atoms_only=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_no_closed_loop_outcomes_as_training_input=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_no_candidate_tensor_mutation=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_no_dp_modification=True" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_training_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_paired_evaluation_executed=False" in text
        assert "v16_nuscenes_fixed_dp_candidate_tensor_scaleup_training_preflight_plan_static_review_performance_claimed=False" in text
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
    _write(artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Scale-up training preflight plan\n")
    for name, content in {
        "HEADS": f"CAMP_HEAD={PLAN_HEAD}\nCAMP_ORIGIN_MAIN={PLAN_HEAD}\nDP_HEAD={module.FIXED_DP_HEAD}\n",
        "COMMAND": "run scale-up training preflight plan\n",
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
            "scaleup_corpus": {
                "path": module.PLAN_MODULE.SCALEUP_CORPUS_ARTIFACT,
                "root_sha256": SCALEUP_CORPUS_ROOT_SHA,
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
        "scaleup_training_preflight_plan": {
            "fixed_dp_head": module.FIXED_DP_HEAD,
            "training_scope": "scaleup_train_split_training_plan_only_no_performance_claim",
            "training_inputs": {
                "calibration_records_available": 2156,
                "calibration_records_used_for_training": calibration_used_for_training,
                "candidate_tensor_schema": {
                    "candidate_count": 8,
                    "candidate_tensor_shape": [8, 80, 4],
                    "k": 8,
                },
                "dp_head": module.FIXED_DP_HEAD,
                "forbidden_training_splits": ["calibration", "holdout"],
                "holdout_records_available": 1581,
                "holdout_records_used_for_training": 0,
                "scaleup_corpus_artifact": module.PLAN_MODULE.SCALEUP_CORPUS_ARTIFACT,
                "scaleup_corpus_root_sha256": SCALEUP_CORPUS_ROOT_SHA,
                "split_execution_artifact": "/root/autodl-tmp/split_execution",
                "split_execution_root_sha256": SPLIT_EXECUTION_ROOT_SHA,
                "split_result_review_artifact": "/root/autodl-tmp/split_result_review",
                "split_result_review_root_sha256": SPLIT_REVIEW_ROOT_SHA,
                "train_records": 6263,
                "training_splits": ["train"],
            },
            "math_contract": {
                "approved_atoms_only": True,
                "no_candidate_tensor_mutation": True,
                "no_closed_loop_outcomes_as_training_input": True,
                "no_dp_modification": True,
                "nonnegative_simplex": True,
                "score_expression": module.PLAN_MODULE.SCORE_EXPRESSION,
                "weights_nonnegative": True,
                "weights_sum_to_one": True,
            },
            "planned_outputs": {
                "approved_atoms_check": "approved_atoms_check.json",
                "command": "COMMAND",
                "heads": "HEADS",
                "nonnegative_simplex_check": "nonnegative_simplex_check.json",
                "root_sha256s": "ROOT_SHA256SUMS",
                "sha256s": "SHA256SUMS",
                "static_camp_weights_model_artifact": "static_camp_weights_model.json",
                "stderr": "stderr.txt",
                "stdout": "stdout.txt",
                "timing_json": "scaleup_training_timing.json",
                "timing_md": "scaleup_training_timing.md",
                "training_config": "scaleup_training_config.json",
                "training_log": "scaleup_training.log",
            },
            "stop_conditions": [
                "split_overlap",
                "missing_candidate_hashes",
                "k_or_candidate_count_drift",
                "dp_head_mismatch",
                "calibration_or_holdout_leakage",
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
            "promotion_executed": False,
            "scaleup_training_preflight_plan_executed": True,
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
