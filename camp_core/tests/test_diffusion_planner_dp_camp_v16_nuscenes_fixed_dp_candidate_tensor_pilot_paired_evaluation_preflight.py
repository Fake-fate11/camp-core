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
    / "preflight_diffusion_planner_dp_camp_v16_nuscenes_fixed_dp_candidate_tensor_pilot_paired_evaluation.py"
)
HEAD = "1ee5d8dc13d987d5c01cd870db024df7ec2144fc"
PLAN_HEAD = "09e49fbffd4f6cb1144b6ad1bc26ce01af261f55"
STATIC_REVIEW_HEAD = "4fdd75507d2f616720aec9a1b20403e535d55769"
PLAN_ROOT_SHA = "c95c3c99cf0362fac33d6dea85541b55c5903a0c7317cde808b300cfc8dd4d97"
STATIC_REVIEW_ROOT_SHA = "3d2cfebbfa310219ad98cddcbf0f040049882bccacf51cb2c067e8b842b0ee68"
TRAINING_ROOT_SHA = "92ebe656b28a61b27a5317cf48e41f38a0c1f5d7f333323e2fdaeeb8c8dcd493"
SPLIT_ROOT_SHA = "18f1231c1c50841bde09527066f7845fe6b101c9978bf490457d8ce6c1867878"


def _load_module():
    spec = importlib.util.spec_from_file_location("v16_pilot_paired_eval_preflight", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v16_pilot_paired_eval_preflight_passes_without_eval(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)

    report = module.build_report(**fixture)
    module.write_outputs(fixture["output_dir"], report)

    decision = report["final_decision"]
    preflight = report["pilot_paired_evaluation_preflight"]
    assert decision["passed"] is True
    assert decision["status"] == module.READY_STATUS
    assert decision["authorized_next_work"] == module.AUTHORIZED_NEXT_WORK
    assert decision["preflight_only"] is True
    assert decision["evaluation_command_constructed"] is True
    assert decision["evaluation_executed"] is False
    assert decision["training_executed"] is False
    assert decision["performance_claimed"] is False
    assert decision["safety_claimed"] is False
    assert decision["camp_over_dp_claimed"] is False
    assert preflight["source_plan_root_sha256"] == PLAN_ROOT_SHA
    assert preflight["source_static_review_root_sha256"] == STATIC_REVIEW_ROOT_SHA
    assert preflight["source_training_root_sha256"] == TRAINING_ROOT_SHA
    assert preflight["primary_eval_rows"] == 161
    assert preflight["paired_rows_by_split"] == {
        "calibration": 14,
        "holdout": 147,
        "primary_eval_total": 161,
        "train_reporting_only": 863,
    }
    assert preflight["primary_eval_splits"] == ["calibration", "holdout"]
    assert preflight["reporting_only_splits"] == ["train"]
    assert preflight["scene_zero_overlap"] is True
    assert preflight["sample_zero_overlap"] is True
    assert preflight["k_values"] == [8]
    assert preflight["candidate_count_values"] == [8]
    assert preflight["missing_candidate_tensor_sha256"] == 0
    assert preflight["candidate_tensor_mutated_count"] == 0
    assert preflight["dp_head"] == module.FIXED_DP_HEAD
    assert preflight["score_expression"] == module.SCORE_EXPRESSION
    assert preflight["approved_atoms_only"] is True
    assert preflight["weights_nonnegative"] is True
    assert preflight["weights_sum_to_one"] is True
    assert set(preflight["metrics_planned"]) >= set(module.REQUIRED_METRICS)
    assert preflight["evaluation_output_root_absent_or_reserved"] is True
    assert "execute_diffusion_planner_dp_camp_v16" in " ".join(preflight["evaluation_command_template"])
    assert (fixture["output_dir"] / module.PREFLIGHT_JSON_NAME).is_file()
    assert (fixture["output_dir"] / module.PREFLIGHT_MD_NAME).is_file()
    assert (fixture["output_dir"] / "HEADS").is_file()
    assert (fixture["output_dir"] / "COMMAND").is_file()
    assert (fixture["output_dir"] / "SHA256SUMS").is_file()
    assert (fixture["output_dir"] / "ROOT_SHA256SUMS").is_file()


def test_v16_pilot_paired_eval_preflight_rejects_existing_output_root(tmp_path: Path) -> None:
    module = _load_module()
    fixture = _write_fixture(tmp_path, module)
    fixture["evaluation_output_root"].mkdir()

    report = module.build_report(**fixture)

    assert report["final_decision"]["passed"] is False
    assert "evaluation_output_root_absent" in report["final_decision"]["failed_checks"]


def _write_fixture(tmp_path: Path, module) -> dict:
    plan_artifact = tmp_path / "paired_eval_plan"
    review_artifact = tmp_path / "paired_eval_plan_static_review"
    training_artifact = tmp_path / "training_execution"
    split_artifact = tmp_path / "split_execution"
    for path in (plan_artifact, review_artifact, training_artifact, split_artifact):
        path.mkdir()
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
    records_by_split = _records_by_split(module)
    for name, rows in {
        "train_records.jsonl": records_by_split["train"],
        "calibration_records.jsonl": records_by_split["calibration"],
        "holdout_records.jsonl": records_by_split["holdout"],
    }.items():
        _write(split_artifact / name, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))

    _write_plan_artifact(plan_artifact, module)
    _write_static_review_artifact(review_artifact, module)
    _write_training_artifact(training_artifact, split_artifact, module, records_by_split["train"])
    return {
        "source_plan_artifact_dir": plan_artifact,
        "source_plan_json": plan_artifact / module.PLAN_MODULE.PLAN_JSON_NAME,
        "source_plan_sha256s": plan_artifact / "SHA256SUMS",
        "source_plan_root_sha256s": plan_artifact / "ROOT_SHA256SUMS",
        "source_static_review_artifact_dir": review_artifact,
        "source_static_review_json": review_artifact / module.SOURCE_REVIEW_JSON_NAME,
        "source_static_review_sha256s": review_artifact / "SHA256SUMS",
        "source_static_review_root_sha256s": review_artifact / "ROOT_SHA256SUMS",
        "source_training_artifact_dir": training_artifact,
        "source_training_json": training_artifact / module.TRAINING_JSON_NAME,
        "source_training_sha256s": training_artifact / "SHA256SUMS",
        "source_training_root_sha256s": training_artifact / "ROOT_SHA256SUMS",
        "v16_audit_md": audit,
        "current_status_md": current_status,
        "evaluation_output_root": tmp_path / "paired_eval_execution",
        "output_dir": tmp_path / "out",
        "current_camp_head": HEAD,
        "current_camp_origin_main": HEAD,
        "current_dp_head": module.FIXED_DP_HEAD,
        "expected_plan_root_sha256": PLAN_ROOT_SHA,
        "expected_static_review_root_sha256": STATIC_REVIEW_ROOT_SHA,
        "expected_training_root_sha256": TRAINING_ROOT_SHA,
        "python_executable": "python",
        "enabled": True,
    }


def _write_plan_artifact(artifact: Path, module) -> None:
    _write_json(artifact / module.PLAN_MODULE.PLAN_JSON_NAME, _plan_payload(module))
    _write(artifact / module.PLAN_MODULE.PLAN_MD_NAME, "# Plan\n")
    _write_common_files(artifact, PLAN_HEAD, module.FIXED_DP_HEAD)
    _write_manifest(artifact, PLAN_ROOT_SHA)


def _write_static_review_artifact(artifact: Path, module) -> None:
    _write_json(artifact / module.SOURCE_REVIEW_JSON_NAME, _static_review_payload(module))
    _write(artifact / module.SOURCE_REVIEW_MD_NAME, "# Static review\n")
    _write_common_files(artifact, STATIC_REVIEW_HEAD, module.FIXED_DP_HEAD)
    _write_manifest(artifact, STATIC_REVIEW_ROOT_SHA)


def _write_training_artifact(artifact: Path, split_artifact: Path, module, train_rows: list[dict]) -> None:
    _write_json(artifact / module.TRAINING_JSON_NAME, _training_payload(module, split_artifact))
    _write(artifact / module.TRAINING_MD_NAME, "# Training execution\n")
    _write(artifact / "train_selection_log.json", json.dumps(train_rows, indent=2, sort_keys=True) + "\n")
    _write_common_files(artifact, "2f0448ad80abb5b858595c904d4bd6c2de3930a0", module.FIXED_DP_HEAD)
    for name in ("static_camp_weights_model.json", "pilot_training_config.json", "pilot_training_timing.json"):
        _write(artifact / name, "{}\n")
    _write_manifest(artifact, TRAINING_ROOT_SHA)


def _plan_payload(module) -> dict:
    review = _training_review(module)
    return {
        "schema_version": module.PLAN_MODULE.SCHEMA_VERSION,
        "status": module.PLAN_MODULE.READY_STATUS,
        "authorized_next_work": module.SOURCE_CURRENT_WORK,
        "heads": {"camp_head": PLAN_HEAD, "dp_head": module.FIXED_DP_HEAD},
        "source_artifact": {"path": "/training_result_review", "root_sha256": "40f42"},
        "training_result_review": review,
        "paired_evaluation_preflight_plan": _paired_plan(module),
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.SOURCE_CURRENT_WORK,
            "paired_evaluation_preflight_plan_only": True,
            "evaluation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
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


def _static_review_payload(module) -> dict:
    return {
        "schema_version": module.SOURCE_REVIEW_SCHEMA_VERSION,
        "status": module.SOURCE_READY_STATUS,
        "source_plan_artifact": {"root_sha256": PLAN_ROOT_SHA},
        "heads": {"camp_head": STATIC_REVIEW_HEAD, "source_camp_head": PLAN_HEAD, "dp_head": module.FIXED_DP_HEAD},
        "plan_static_review": {
            "source_plan_root_sha256": PLAN_ROOT_SHA,
            **_paired_plan(module),
        },
        "final_decision": {
            "passed": True,
            "authorized_next_work": module.AUTHORIZED_CURRENT_WORK,
            "static_review_only": True,
            "evaluation_executed": False,
            "training_executed": False,
            "paired_evaluation_executed": False,
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


def _training_payload(module, split_artifact: Path) -> dict:
    return {
        "schema_version": module.TRAINING_SCHEMA_VERSION,
        "status": module.TRAINING_READY_STATUS,
        "heads": {"camp_head": "2f0448ad80abb5b858595c904d4bd6c2de3930a0", "dp_head": module.FIXED_DP_HEAD},
        "source_artifacts": {
            "split_execution": {
                "path": str(split_artifact),
                "root_sha256": SPLIT_ROOT_SHA,
                "sha256s_verified": True,
                "failed_sha256s": [],
            }
        },
        "pilot_training_execution": {
            "train_records": 863,
            "calibration_records": 14,
            "holdout_records": 147,
            "calibration_records_used_for_training": 0,
            "holdout_records_used_for_training": 0,
            "record_summary": {
                "scene_zero_overlap": True,
                "sample_zero_overlap": True,
                "train_k_values": [8],
                "train_candidate_count_values": [8],
                "train_dp_head_values": [module.FIXED_DP_HEAD],
                "train_candidate_tensor_mutated_count": 0,
            },
            "score_expression": module.SCORE_EXPRESSION,
        },
        "static_camp_model": {
            "approved_atoms_only": True,
            "weights_nonnegative": True,
            "weights_sum_to_one": True,
            "score_expression": module.SCORE_EXPRESSION,
        },
        "final_decision": {
            "passed": True,
            "training_executed": True,
            "paired_evaluation_executed": False,
            "performance_claimed": False,
            "promotion_executed": False,
            "deployment_executed": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "fake_candidate_tensor_generated": False,
        },
    }


def _training_review(module) -> dict:
    return {
        "train_records": 863,
        "calibration_records": 14,
        "holdout_records": 147,
        "calibration_records_used_for_training": 0,
        "holdout_records_used_for_training": 0,
        "scene_zero_overlap": True,
        "sample_zero_overlap": True,
        "train_k_values": [8],
        "train_candidate_count_values": [8],
        "source_dp_head": module.FIXED_DP_HEAD,
        "candidate_tensor_mutated_count": 0,
        "score_expression": module.SCORE_EXPRESSION,
        "approved_atoms_only": True,
        "weights_nonnegative": True,
        "weights_sum_to_one": True,
    }


def _paired_plan(module) -> dict:
    return {
        "primary_eval_splits": ["calibration", "holdout"],
        "reporting_only_splits": ["train"],
        "paired_rows_by_split": {
            "calibration": 14,
            "holdout": 147,
            "primary_eval_total": 161,
            "train_reporting_only": 863,
        },
        "comparison": {
            "camp_selection": "camp_selected_fixed_dp_candidate",
            "baseline": "dp_top1",
            "candidate_source": "fixed_dp_candidate_tensor",
        },
        "metrics_planned": list(module.REQUIRED_METRICS),
        "pilot_eval_smoke_only": True,
        "claims": {
            "performance_claim_allowed": False,
            "safety_claim_allowed": False,
            "camp_over_dp_claim_allowed": False,
        },
        "pass_fail_conditions": {
            "no_train_leakage_into_primary_eval": True,
            "k": 8,
            "candidate_count": 8,
            "dp_head_fixed": module.FIXED_DP_HEAD,
            "candidate_tensor_hashes_present": True,
            "no_candidate_mutation": True,
            "affine_simplex_checks_pass": True,
        },
    }


def _records_by_split(module) -> dict[str, list[dict]]:
    return {
        "train": [_record(module, "train", i) for i in range(863)],
        "calibration": [_record(module, "calibration", i) for i in range(14)],
        "holdout": [_record(module, "holdout", i) for i in range(147)],
    }


def _record(module, split: str, index: int) -> dict:
    return {
        "split": split,
        "scene_id": f"{split}_scene_{index}",
        "sample_id": f"{split}_sample_{index}",
        "K": 8,
        "candidate_count": 8,
        "DP_HEAD": module.FIXED_DP_HEAD,
        "candidate_tensor_sha256": f"{split}_{index:04x}",
        "candidate_tensor_unchanged_by_camp": True,
    }


def _write_common_files(artifact: Path, camp_head: str, dp_head: str) -> None:
    _write(artifact / "HEADS", f"CAMP_HEAD={camp_head}\nCAMP_ORIGIN_MAIN={camp_head}\nDP_HEAD={dp_head}\n")
    _write(artifact / "COMMAND", "command\n")
    _write(artifact / "COMMAND.shell", "command shell\n")
    _write(artifact / "stdout.txt", "{}\n")
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
